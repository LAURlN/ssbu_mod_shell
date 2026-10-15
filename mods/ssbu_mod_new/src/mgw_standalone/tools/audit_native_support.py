"""Evidence for resource pointers, identity tables and path hooks in main."""
from inspect_native import data, md, ROOT, WORKSPACE
import struct
import re
import json
import zipfile

relocations = {}
mod = struct.unpack_from('<I', data, 4)[0]
dyn = mod + struct.unpack_from('<i', data, mod + 4)[0]
tags = {}
for offset in range(dyn, len(data), 16):
    tag, value = struct.unpack_from('<QQ', data, offset)
    if not tag: break
    tags[tag] = value
for offset in range(tags[7], tags[7] + tags[8], 24):
    dest, info, addend = struct.unpack_from('<QQq', data, offset)
    if info & 0xffffffff == 1027:
        relocations[dest] = addend

def string_at_slot(slot):
    pointer = relocations.get(slot, struct.unpack_from('<Q', data, slot)[0])
    if not 0 < pointer < len(data): return f'<invalid {pointer:#x}>'
    return data[pointer:data.index(0, pointer)].decode('utf8', errors='replace')

tables = []
for name, old, new, indices in [
    ('fighter_names', 0x4f81e20, 0x4f80e20, [0, 2, 28, 91]),
    ('weapon_names', 0x5186bd0, 0x5185bd0, [0x1e, 0x77, 0x78, 0x251]),
    ('weapon_owners', 0x5189240, 0x5188240, [0x1e, 0x77, 0x78, 0x251]),
]:
    row = dict(name=name, upstream=hex(old), corrected=hex(new), samples=[
        dict(index=i, upstream=string_at_slot(old+i*8), corrected=string_at_slot(new+i*8))
        for i in indices])
    tables.append(row)
    print(row)

path_hooks = []
for file in ('fighters.rs','weapons.rs'):
    with zipfile.ZipFile(ROOT/'downloads/smashline-v1.6.8-source.zip') as archive:
        entry = next(name for name in archive.namelist() if name.endswith('/src/cloning/'+file))
        text = archive.read(entry).decode('utf-8')
    for line in text.splitlines():
        if line.lstrip().startswith('//'): continue
        found = re.search(r'(0x[0-9a-f]+) - 0x40', line)
        if found:
            address = int(found[1],16)
            def show(at):
                return [f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in md.disasm(data[at:at+8],at)]
            row = dict(file=file, source=line.strip(), upstream=show(address-0x40), original=show(address))
            path_hooks.append(row)
            print(row)

globals_found = []
for start,end in [(0x22b0000,0x22bd000),(0x3530000,0x3560000)]:
    instructions = list(md.disasm(data[start:end],start))
    for n,i in enumerate(instructions):
        if i.mnemonic=='adrp' and ('#0x5326000' in i.op_str or '#0x5331000' in i.op_str):
            sequence = [f'{s.address:#x}: {s.mnemonic} {s.op_str}' for s in instructions[n:n+5]]
            globals_found.append(sequence)
            if any('#0xcd0]' in line or '#0xf28]' in line for line in sequence):print(sequence)
(ROOT/'native-support-audit.json').write_text(json.dumps(dict(tables=tables,path_hooks=path_hooks,global_references=globals_found),indent=2)+'\n')
