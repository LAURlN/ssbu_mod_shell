"""Build clone-specific portraits and import the portraits supplied by skins.

The supported BNTX inputs have one texture and a one-leaf dictionary. Their
container, texture and dictionary key share one string allocation. Costume
suffix changes also update that leaf's distinguishing bit, without moving any
image or relocation data.
"""
from pathlib import Path
import hashlib
import struct


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rename_portrait(data, old_name, new_name):
    old, new = old_name.encode('ascii'), new_name.encode('ascii')
    assert data[:8] == b'BNTX\0\0\0\0' and data[12:14] == b'\xff\xfe'
    assert data[32:36] == b'NX  '
    assert struct.unpack_from('<I', data, 36)[0] == 1, 'Expected one texture'
    assert len(new) <= len(old), 'New name would require relocation'
    container = struct.unpack_from('<I', data, 16)[0]
    array = struct.unpack_from('<Q', data, 40)[0]
    brti = struct.unpack_from('<Q', data, array)[0]
    assert data[brti:brti+4] == b'BRTI'
    texture = struct.unpack_from('<Q', data, brti+0x60)[0]
    dictionary = struct.unpack_from('<Q', data, 56)[0]
    assert data[dictionary:dictionary+4] == b'_DIC'
    assert struct.unpack_from('<I', data, dictionary+4)[0] == 1
    root_ref, root_left, root_right, root_key = struct.unpack_from('<IHHQ', data, dictionary+8)
    leaf_ref, leaf_left, leaf_right, key = struct.unpack_from('<IHHQ', data, dictionary+24)
    assert (root_ref,root_left,root_right) == (0xffffffff,1,0)
    assert leaf_left == 0 and leaf_right == 1
    assert struct.unpack_from('<H',data,root_key)[0] == 0
    assert new.endswith(b'_00'), 'Clone portrait names must use costume c00'
    assert container == texture+2 == key+2
    assert struct.unpack_from('<H',data,key)[0] == len(old)
    assert data[container:container+len(old)+1] == old+b'\0'
    # In a one-leaf ResDic, the leaf reference is the low set bit in the final
    # character that separates the texture key from the empty root. c06 uses
    # bit 1; c00 uses bit 4. Preserve the trie and update this discriminator.
    old_leaf_bit = (old[-1] & -old[-1]).bit_length()-1
    new_leaf_bit = (new[-1] & -new[-1]).bit_length()-1
    assert leaf_ref == old_leaf_bit, (old, leaf_ref, old_leaf_bit)
    result = bytearray(data)
    struct.pack_into('<H',result,key,len(new))
    struct.pack_into('<I',result,dictionary+24,new_leaf_bit)
    result[container:container+len(old)+1] = new + b'\0'*(len(old)+1-len(new))
    # Read back every name reference and verify the entire rest of the file,
    # including image data, dictionary links and relocation table, is identical.
    for pointer in (container,texture+2,key+2):
        assert result[pointer:result.index(0,pointer)] == new
    assert result[:key] == data[:key]
    assert result[dictionary+8:dictionary+24] == data[dictionary+8:dictionary+24]
    assert result[dictionary+28:] == data[dictionary+28:]
    string_end = container+len(old)+1
    assert result[string_end:dictionary+24] == data[string_end:dictionary+24]
    assert struct.unpack_from('<I',result,dictionary+24)[0] == new_leaf_bit
    assert old not in result[:4096]
    return bytes(result)


def build_ui(export_root: Path, pack: Path, config: dict):
    manifest=[]
    for donor, clone, tree, variants in (
        ('eflame_only','mgw_pyra','replace_patch',(0,1,2,3,4,5,6,10)),
        ('elight_only','mgw_mythra','replace_patch',(0,1,2,3,4,5,6,10)),
    ):
        for variant in variants:
            old=f'chara_{variant}_{donor}_00'
            new=f'chara_{variant}_{clone}_00'
            source=export_root/f'ui/{tree}/chara/chara_{variant}/{old}.bntx'
            group=f'ui/replace/chara/chara_{variant}'
            relative=f'{group}/{new}.bntx'
            original=source.read_bytes()
            updated=rename_portrait(original,old,new)
            target=pack/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(updated)
            # These are existing UI archive groups. Append only the clone files.
            config['new-dir-files'].setdefault(group,[]).append(relative)
            manifest.append({'source':str(source.relative_to(export_root)),
                'destination':relative,'source_sha256':sha(original),
                'output_sha256':sha(updated),'bytes':len(updated),
                'pixels_and_relocations_unchanged':True})
    assert len(manifest)==16
    return manifest


def import_skin_portraits(workspace: Path, pack: Path, config: dict,
                          generated_manifest: list):
    """Replace available c00 clone portraits with the user's skin portraits.

    Mythra's probe is an Elight-only fighter, so use the skin's ``only``
    portraits rather than the pair's ``first`` portraits. Several UI classes
    are absent from each source skin; those keep the already-built clone icon.
    """
    sources = (
        (workspace / 'skins_to_use/black_and_pink_mythra/mythra skin'
         / 'ui/replace_patch/chara', 'elight_only_06', 'mgw_mythra'),
    )
    generated = {item['destination']: item for item in generated_manifest}
    imported = []
    for source_root, source_suffix, clone in sources:
        expected_suffix = 'elight_only_06'
        source_files = sorted(source_root.rglob(f'chara_*_{expected_suffix}.bntx'))
        if not source_files:
            raise FileNotFoundError(f'No {clone} skin portraits found in {source_root}')
        variants = {int(source.name.split('_', 2)[1]) for source in source_files}
        expected_variants = {1, 2, 3, 4, 6}
        if variants != expected_variants:
            raise ValueError(
                f'Unexpected {clone} skin portrait variants: '
                f'expected {sorted(expected_variants)}, found {sorted(variants)}'
            )
        for source in source_files:
            variant = source.name.split('_', 2)[1]
            # The actual container key includes the chara index; the G&W mod
            # filename uses c05 while its embedded BNTX key is c00.
            original = source.read_bytes()
            container = struct.unpack_from('<I', original, 16)[0]
            embedded = original[container:original.index(0, container)].decode('ascii')
            expected_old = f'chara_{variant}_{source_suffix}'
            if embedded != expected_old:
                raise ValueError(f'{source}: expected internal key {expected_old}, found {embedded}')
            new_name = f'chara_{variant}_{clone}_00'
            output = rename_portrait(original, embedded, new_name)
            relative = f'ui/replace/chara/chara_{variant}/{new_name}.bntx'
            target = pack / relative
            if not target.is_file():
                raise FileNotFoundError(f'Generated clone portrait is missing: {target}')
            prior = target.read_bytes()
            target.write_bytes(output)
            if relative not in generated:
                raise ValueError(f'Skin portrait has no generated clone resource record: {relative}')
            item = generated[relative]
            item['generated_source'] = item['source']
            item['generated_source_sha256'] = item['source_sha256']
            generated[relative].update({
                'source': source.relative_to(workspace).as_posix(),
                'source_sha256': sha(original),
                'output_sha256': sha(output),
                'skin_portrait': True,
                'overwrote_generated_portrait_sha256': sha(prior),
                'pixels_and_relocations_unchanged': True,
            })
            imported.append({
                'source': source.relative_to(workspace).as_posix(),
                'destination': relative,
                'source_sha256': sha(original),
                'output_sha256': sha(output),
                'bytes': len(output),
                'embedded_source_name': embedded,
                'embedded_clone_name': new_name,
                'dictionary_leaf_bit_updated': True,
                'pixels_and_relocations_unchanged': True,
            })
    if not imported:
        raise ValueError('No skin portraits were imported')
    return imported
