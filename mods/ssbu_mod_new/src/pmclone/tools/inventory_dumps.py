"""Verify and snapshot local dump inputs; plan targeted archive acquisition.

No console writes or network operations. Existing edited snapshots are preserved.
This is an input inventory, not proof that all runtime dependencies are closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from prepare import ROOT, materialize, safe_relative, write_json
from prepare import relevant

sys.path.insert(0, str(Path(__file__).parent / 'python_deps'))
import lz4.block


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode_nso(raw):
    if len(raw) < 0x100 or raw[:4] != b'NSO0':
        raise ValueError('Invalid NSO header')
    flags = struct.unpack_from('<I', raw, 12)[0]
    segments, image = [], bytearray()
    for i, name in enumerate(('text', 'rodata', 'data')):
        offset, address, size = struct.unpack_from('<III', raw, 0x10 + 16 * i)
        compressed = bool(flags & (1 << i))
        stored_size = struct.unpack_from('<I', raw, 0x60 + 4 * i)[0] if compressed else size
        if address + size > 512 * 1024**2:
            raise ValueError('Unexpectedly large NSO segment')
        stored = raw[offset:offset + stored_size]
        if len(stored) != stored_size:
            raise ValueError('Truncated NSO segment')
        block = lz4.block.decompress(stored, uncompressed_size=size) if compressed else stored
        if len(block) != size:
            raise ValueError('Decompressed size mismatch')
        digest = hashlib.sha256(block).digest()
        expected = raw[0xa0 + 32 * i:0xc0 + 32 * i]
        enabled = bool(flags & (1 << (i + 3)))
        if enabled and digest != expected:
            raise ValueError('NSO segment hash mismatch: ' + name)
        if len(image) < address + size:
            image.extend(bytes(address + size - len(image)))
        image[address:address + size] = block
        segments.append(dict(name=name, offset=address, bytes=size, sha256=digest.hex(),
                             header_hash_enabled=enabled, header_hash_matches=digest == expected))
    return bytes(image), dict(build_id=raw[0x40:0x60].hex(), flags=flags, segments=segments,
                             bss_bytes=struct.unpack_from('<I', raw, 0x3c)[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exefs', type=Path, default=ROOT.parent /
        'Super Smash Bros. Ultimate 13.0.4 [01006A800016E800][v1966080][UPD]/Program #0/0')
    parser.add_argument('--export', type=Path, default=ROOT.parent / 'export')
    parser.add_argument('--index', type=Path, default=ROOT.parent /
        'mod_files/mgw_standalone/vendor/clone_pack_workbench/arc_index/arc_files.tsv')
    parser.add_argument('--verify-assets', action='store_true', help='Rehash all previously inventoried character assets too')
    args = parser.parse_args()
    rows = []
    for name in ('main', 'rtld', 'sdk', 'subsdk0', 'main.npdm'):
        source = args.exefs / name
        if not source.is_file():
            rows.append(dict(name=name, status='missing', source=str(source)))
            continue
        raw = source.read_bytes()
        destination = ROOT / 'reference/dumps/exefs' / name
        status = materialize(source, destination, raw)
        row = dict(name=name, source=str(source.resolve()), copy=destination.relative_to(ROOT).as_posix(),
                   bytes=len(raw), sha256=sha(raw), status=status, running_console_identity_verified=False)
        if name != 'main.npdm':
            image, meta = decode_nso(raw)
            row.update(meta)
            output = ROOT / 'reference/dumps/images' / (name + '.bin')
            # This output is derived, so compare it against the decoded bytes.
            row['image_status'] = materialize(source, output, image)
            row['image'] = output.relative_to(ROOT).as_posix()
            row['image_sha256'] = sha(image)
            row['image_bytes'] = len(image)
            if name == 'main':
                previous = ROOT.parent / 'references/mythra_gamewatch_feasibility/main_memory.bin'
                row['matches_existing_analysis_image'] = previous.is_file() and sha(previous.read_bytes()) == sha(image)
                if not row['matches_existing_analysis_image']:
                    raise ValueError('Main image differs from the native analysis input')
        rows.append(row)
    write_json('exefs-dumps.json', dict(files=rows, live_version_confirmation_pending=True))

    index = {p.replace('prebuilt:/', 'prebuilt/', 1) for p in args.index.read_text().splitlines() if p}
    token = re.compile(r'(?<![a-zA-Z0-9])(?:eflame|elight|element)(?![a-zA-Z0-9])')
    selected = {}
    def add(path, reason):
        safe_relative(path)
        selected.setdefault(path, []).append(reason)
    for p in index:
        if relevant(p) or (token.search(p) and not p.startswith(('stage/', 'ui/replace_patch/spirits/'))):
            add(p, 'Character identity appears in the archive path, including outside the original asset filter')
        if p.startswith('fighter/common/param/'):
            add(p, 'Shared fighter configuration; inspect character-specific rows and references')
    explicit = {
        'ui/param/menu/chara_icon_arrangement.prc': 'Character-select placement',
        'ui/param/database/ui_chara_db.prc': 'Character roster metadata',
        'ui/param/database/ui_layout_db.prc': 'UI layout routing',
        'ui/param/database/ui_mark_db.prc': 'Series icon routing',
        'ui/param/database/ui_series_db.prc': 'Series metadata',
        'ui/param/database/ui_gametitle_db.prc': 'Game-title metadata',
        'ui/param/database/ui_voice_db.prc': 'Voice routing',
        'ui/param/database/ui_profile_icon_db.prc': 'Character icon metadata',
        'ui/param/database/ui_fighter_spirit_aw_db.prc': 'Character/spirit references',
        'ui/param/standard/standard_common.prc': 'Classic-mode shared configuration',
        'ui/param/standard/standard_result.prc': 'Results configuration',
        'sound/config/config.nus3conf': 'Global sound bank configuration',
        'sound/sequence/fighter/common.sqb': 'Common sound sequence routing',
        'sound/sequence/fighter/kirby.sqb': 'Kirby copy behavior sound references',
    }
    for name in ('eflame', 'elight', 'element', 'common', 'kirby', 'item', 'ptrainer'):
        explicit['prebuilt/nro/release/lua2cpp_' + name + '.nro'] = 'Native module dependency and export reference'
    for p, reason in explicit.items():
        add(p, reason)
    assets = json.loads((ROOT / 'reports/assets.json').read_text())
    previous_hashes = {row['source']: row for row in assets['files']}
    # Keep hashes of all acquisition inputs, without duplicating the full asset set.
    archive_rows, missing, conflicts = [], [], []
    for p, reasons in sorted(selected.items()):
        source = args.export / p
        row = dict(path=p, reasons=reasons, source=str(source.resolve()), indexed=p in index)
        if not source.is_file():
            row['status'] = 'missing'
            missing.append(p)
        else:
            needs_snapshot = p in explicit or p.startswith('fighter/common/param/')
            previous = previous_hashes.get(p)
            if previous and not needs_snapshot and not args.verify_assets:
                size = source.stat().st_size
                row.update(bytes=size, previous_source_sha256=previous['source_sha256'],
                           status='present_previous_hash_not_reverified')
            else:
                raw = source.read_bytes()
                row.update(bytes=len(raw), sha256=sha(raw), status='present_hash_verified')
            # Shared config and module inputs get immutable research snapshots.
            # Character assets already have independent editable copies.
            if needs_snapshot:
                output = ROOT / 'reference/dumps/archive' / p
                row['snapshot_status'] = materialize(source, output, raw)
                row['snapshot'] = output.relative_to(ROOT).as_posix()
                if row['snapshot_status'] == 'conflict_preserved':
                    conflicts.append(p)
        archive_rows.append(row)
    report = dict(scope='Known character paths plus targeted shared dependencies; not full dependency closure',
                  index_sha256=sha(args.index.read_bytes()), files=archive_rows,
                  files_selected=len(archive_rows), missing_count=len(missing), conflicts=conflicts,
                  existing_prepared_files=assets['summary']['materialized_files'],
                  live_archive_comparison_pending=True)
    write_json('dump-inventory.json', report)
    write_json('dump-missing.json', missing)
    (ROOT / 'reports/dump-missing-paths.txt').write_text('\n'.join(missing) + '\n')
    # A fresh read into a separate folder can verify current archive provenance
    # without overwriting or merely reusing old exports.
    verify = ['prebuilt/nro/release/lua2cpp_' + n + '.nro' for n in ('eflame', 'elight', 'element', 'common')]
    verify += ['ui/param/database/ui_chara_db.prc', 'fighter/common/param/fighter_param.prc']
    write_json('dump-live-verification-paths.json', verify)
    print('Verified ExeFS inputs:', len(rows))
    print('Archive inputs:', len(archive_rows), '; missing:', len(missing), '; snapshot conflicts:', len(conflicts))
    print('Live console build ID confirmation and archive comparison remain pending.')


if __name__ == '__main__':
    main()
