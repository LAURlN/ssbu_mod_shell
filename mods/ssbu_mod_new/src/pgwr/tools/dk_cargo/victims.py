"""Pin roster victim motion dependencies from the local ARC, read-only.

No victim asset overrides are generated. Missing and empty entries stay explicit.
This extends the dependency capture; run audit.py afterwards to pin extra inputs.
"""
import json
import subprocess
import re
import audit
from audit import ROOT, WS, INPUT, OUT, h40, sha, motion_entries, cfg
from main_image import MainImage
from audit_mflip_capture_native import symbols


def run():
    sites = json.loads((OUT / 'native_message_sites.json').read_text())
    names = [n.removeprefix('fighter_kind_') for n in sites['thrown_row_names']]
    index_path = ROOT / 'dumps/decoded/arc_files.tsv'
    index = [x.split('\t')[0].strip() for x in index_path.read_text().splitlines()]
    paths = set(index)
    lists = [f'fighter/{n}/motion/body/c00/motion_list.bin' for n in names
             if f'fighter/{n}/motion/body/c00/motion_list.bin' in paths]
    exe = ROOT / 'builds/.cache/dk_cargo/arc-target/release/arc-extract.exe'
    wanted = [p for p in lists if not (INPUT / p).is_file()]
    if wanted:
        result = subprocess.run([str(exe), '--arc', 'gamedata/ssbu-13.0.4/data.arc',
                                 '--out', str(INPUT)] + wanted, cwd=WS,
                                capture_output=True, text=True)
        print('victim motion list extractor exit', result.returncode)
        if result.returncode:
            print(result.stderr)
        assert result.returncode == 0
    base_kinds = ['thrown_f', 'shouldered_donkey', 'thrown_f_donkey_f',
             'thrown_f_donkey_b', 'thrown_f_donkey_hi', 'thrown_f_donkey_lw']
    kinds = [n + suffix for n in base_kinds for suffix in ('', '_dx', '_girl')]
    # Include every table entry even when it names no local animation. Resolve
    # body variants later from measured add_body_type_hash semantics.
    matrix = {}
    for path in lists:
        p = INPUT / path
        directory, rows = motion_entries(p)
        filename_hashes = {}
        prefix = path.removesuffix('motion_list.bin')
        for arc_path in index:
            if arc_path.startswith(prefix) and arc_path.endswith('.nuanmb'):
                filename_hashes.setdefault(hex(h40(arc_path.rsplit('/', 1)[1])), []).append(arc_path)
        matrix[path] = {'input_sha256': sha(p.read_bytes()), 'directory_hash': directory,
                       'entries': {n: [{**r, 'resolved_clips':
                           [filename_hashes.get(a, []) for a in r['animations']]}
                           for r in rows if r['kind'] == hex(h40(n))] for n in kinds}}
    main = MainImage(WS / 'gamedata/ssbu-13.0.4/main.bin')
    labels = {a: n for n, a, size in symbols(main) if a}
    native = {}
    # body_type_hash has a five-case signed-offset jump table. Pin each target;
    # the raw CFG's br x10 alone would omit the CRC suffix constructions.
    jump_targets = [0x44bee14 + main.i32(0x44bee14 + i * 4) for i in range(5)]
    for a in (0x6e1b90, 0x1ffc3d0, 0x68daa0, 0x6df820, 0x49a4a0, *jump_targets):
        row, text = cfg(main.data, a, labels)
        (OUT / 'semantic_asm' / f'victim_support_{a:x}.asm').write_text(text)
        native[hex(a)] = row
    report = {'tier': 'B', 'runtime_verified': False, 'complete': False,
              'arc_index_sha256': sha(index_path.read_bytes()),
              'matrix': matrix, 'native_support': native,
              'body_hash_jump_table': {'at': '0x44bee14', 'targets': [hex(x) for x in jump_targets]},
              'without_motion_list': [n for n in names if f'fighter/{n}/motion/body/c00/motion_list.bin' not in paths]}
    constants = {n: int(v, 0) for n, v in re.findall(r'^\s+(FIGHTER_KIND_[A-Z0-9_]+): (0x[0-9a-fA-F]+),',
                         (OUT / 'lua_const.rs').read_text(), re.M)}
    mapping = []
    for row, name in enumerate(names):
        symbol = 'FIGHTER_KIND_' + name.upper()
        kind = constants.get(symbol)
        mapping.append({'param_row': row, 'name': name, 'symbol': symbol, 'fighter_kind': kind})
    assert all(x['fighter_kind'] is not None for x in mapping)
    assert len({x['fighter_kind'] for x in mapping}) == 94
    thrown = json.loads((OUT / 'fighter_param_thrown_cargo.json').read_text())['/fighter_param_thrown_donkey']
    offsets = {}
    for item in mapping:
        # Slice by labeled PRC row, not by assuming row == numeric kind.
        row = item['param_row']
        offsets[item['symbol']] = {d: thrown['offset_' + d][row*3:row*3+3]
                                  for d in ('f', 'b', 'hi', 'lw')}
        assert all(len(x) == 3 for x in offsets[item['symbol']].values())
    report['owned_thrown_offsets'] = {'row_mapping': mapping, 'values': offsets,
        'nana_alias': 'FIGHTER_KIND_POPO',
        'runtime_verified': False,
        'indexing_evidence': 'main+0x721118..0x721188; row labels independently mapped to pinned FIGHTER_KIND symbols'}
    templates = []
    for name, entries in matrix['fighter/donkey/motion/body/c00/motion_list.bin']['entries'].items():
        if name.startswith('thrown_f') and 'donkey' not in name:
            continue
        for entry in entries:
            for resolved in entry['resolved_clips']:
                assert len(resolved) == 1, (name, resolved)
                templates.append(resolved[0])
    templates = sorted(set(templates))
    assert len(templates) == 15
    wanted = [p for p in templates if not (INPUT / p).is_file()]
    if wanted:
        result = subprocess.run([str(exe), '--arc', 'gamedata/ssbu-13.0.4/data.arc',
                                 '--out', str(INPUT)] + wanted, cwd=WS, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    report['donor_pose_templates'] = [{'path': p, 'sha256': sha((INPUT/p).read_bytes())} for p in templates]
    (OUT / 'victim_roster_motion_matrix.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Pinned', len(matrix), 'victim lists; no asset overrides or runtime registrations')


if __name__ == '__main__':
    run()
