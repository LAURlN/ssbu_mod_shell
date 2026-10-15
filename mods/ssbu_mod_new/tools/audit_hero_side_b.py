"""Audit Hero side-B's reserved native dependencies without building or installing.

Version 1.1.0. Read-only inputs resolve through paths.toml. Writes tier-B JSON
and annotated instruction evidence under refs/brave_special_s. Smoke test:
run once, then --check; all instruction assertions and regenerated outputs must
match. No runtime hook, fighter cast, donor work access, or package is emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/nro_decomp')]
from main_image import MainImage
from maindesc import descriptors
import nro_flatten
import nro_util
import status_table

VERSION = '1.1.0'
DEST = ROOT / 'refs/brave_special_s'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate() -> dict[str, str]:
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    sys.path[:0] = [str(ROOT / 'src/mgw_swap/tools'), str(ROOT / 'src/mgw_swap/tools/vendor')]
    import ssbh_data_py as ssbh
    skeleton = ROOT / cfg['dumps']['arc'] / 'fighter/elight/model/body/c06/model.nusktb'
    clip = DEST / 'arc/fighter/brave/motion/body/c06/d01specials1.nuanmb'
    bones = {b.name for b in ssbh.skel_data.read_skel(str(skeleton)).bones}
    animated = {n.name for g in ssbh.anim_data.read_anim(str(clip)).groups
                if g.group_type == ssbh.anim_data.GroupType.Transform for n in g.nodes}
    missing = animated - bones
    assert (len(animated), len(animated & bones), len(missing)) == (125, 68, 57)
    other_missing = sorted(n for n in missing if not n.startswith(('S_Mantle', 'S_Skirt')))
    assert other_missing == ['Hilt', 'S_Waistbag1', 'Scabbard', 'Shield', 'ShieldB']
    nro = ROOT / cfg['dumps']['arc'] / 'prebuilt/nro/release/lua2cpp_brave.nro'
    donor = nro.read_bytes()
    assert sha(donor) == 'dc5edcde314f0c461ba0ab08d9e9deef5ede9d5b4ed324141678b9966d43b7a2'
    flat, meta = nro_flatten.flatten(donor)
    plt = nro_util.plt_map(flat, meta['labels'], meta['text_end'])
    all_rows = status_table.table(flat, meta)
    text = ''.join(f'{st} {co} {fn:#x}\n' for st, co, fn in all_rows)
    assert text.splitlines() == (DEST / 'status_table.txt').read_text().splitlines()
    rows = [(st, co, hex(fn)) for st, co, fn in all_rows
            if st == 'FIGHTER_STATUS_KIND_SPECIAL_S'
            or st.startswith('FIGHTER_BRAVE_STATUS_KIND_SPECIAL_S_')]
    assert len(rows) == 25

    setter = {i.address: i for i in nro_util.disasm(flat, 0x1a230, 0x114)}
    assert setter[0x1a250].op_str == 'w8, #0x42fc'
    assert nro_util.const_name(0x42fc) == 'FIGHTER_BRAVE_INSTANCE_WORK_ID_FLOAT_SP'
    assert nro_util.const_name(0x4300) == 'FIGHTER_BRAVE_INSTANCE_WORK_ID_FLOAT_MAX_SP'
    assert 'get_float' in plt[0x23a280]
    assert 'le' in plt[0x23a390]  # L2CValue operator<=
    assert 'on_flag' in plt[0x23a2a0] and 'off_flag' in plt[0x23a430]
    assert setter[0x1a2d4].op_str == 'w0, #0, #0x1a2fc'
    calls = nro_util.bl_callers(flat, meta['text_end'], 0x16db0)
    assert all(a in calls for a in (0xce38, 0xe830, 0xeab0, 0xed80))
    guard = {i.address: i for i in nro_util.disasm(flat, 0x28ce0, 0xb0)}
    assert guard[0x28d3c].op_str == 'w1, wzr'  # compare success against false
    assert 'eq' in plt[0x23a170]
    assert guard[0x28d6c].op_str == 'w21, #0, #0x29488'
    assert nro_util.const_name(0xc914) == 'FIGHTER_BRAVE_STATUS_SPECIAL_S_FLAG_SUCCESS_SP'
    third = next(nro_util.disasm(flat, 0x2ad40, 4))
    assert third.op_str == 'w8, #0xc958'
    assert nro_util.const_name(0xc958) == 'FIGHTER_BRAVE_STATUS_SPECIAL_S_WORK_INT_HOLD_FRAME'

    main = MainImage()
    assert sha(main.data) == 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
    desc = descriptors(main, 0x53)
    spark, lightning = desc[1], desc[2]
    assert (spark['weapon_kind'], spark['init']) == (0x1f6, 0x85d580)
    assert (lightning['weapon_kind'], lightning['init']) == (0x1f7, 0x85dad0)
    spans = [('spark_initializer', 0x85d580, 0x85dad0),
             ('lightning_initializer', 0x85dad0, 0x85e040),
             ('spark_class_callback', 0x33cbb20, 0x33cbbfc),
             ('lightning_map_collection', 0x33cabd0, 0x33cb1d8)]
    ins = {i.address: f'{i.mnemonic} {i.op_str}' for _, a, b in spans
           for i in main.disasm(a, b - a)}
    expected = {
        0x85d5ec: 'ldr x20, [x21, #0x50]',
        0x85d5f4: 'ldp x22, x0, [x21, #0x38]',
        0x85d604: 'cmp w0, #0x1e7', 0x85d60c: 'cmp w0, #0x1e8',
        0x85d614: 'cmp w0, #0x1ea',
        0x85d8cc: 'mov w24, #0xc3', 0x85d8d0: 'movk w24, #0x1000, lsl #16',
        0x85db40: 'ldr x22, [x20, #0x50]',
        0x85dcd0: 'mov w1, #0xe', 0x85dcd4: 'movk w1, #0x100, lsl #16',
        0x85dd2c: 'mov w24, #0xc', 0x85dd30: 'movk w24, #0x1100, lsl #16',
        0x33cbb38: 'adrp x8, #0x52bb000',
        0x33cbb3c: 'ldr x8, [x8, #0x3b0]',
        0x33cbb40: 'ldr x21, [x8, #0x1298]',
        0x33cbb74: 'ldr s0, [x21, #0x23c]',
    }
    for address, instruction in expected.items():
        assert ins[address] == instruction, (hex(address), ins[address], instruction)
    assert main.ptr(0x51b2298) == 0x33cbb20
    lightning_plt = next(a for a, name in plt.items()
                         if 'WeaponSpecializer_BraveLightning19exec_map_collection' in name)
    caller = next(nro_util.disasm(flat, 0x45768, 4))
    assert caller.mnemonic == 'bl' and int(caller.op_str.lstrip('#'), 0) == lightning_plt
    assert ins[0x33cae08] == 'mov w25, #0x15'
    assert ins[0x33cae0c] == 'movk w25, #0x2100, lsl #16'
    required_motions = [f'fighter/brave/motion/{article}/c{slot:02d}/motion_list.bin'
                        for article in ('spark', 'lightning') for slot in (0, 6, 7)]
    arc_index = set((ROOT / 'dumps/decoded/arc_files.tsv').read_text().splitlines())
    assert all(path in arc_index for path in required_motions)
    missing_motions = [path for path in required_motions
                       if not (ROOT / cfg['dumps']['arc'] / path).is_file()
                       and not any((ROOT / 'refs').glob('**/' + path))]
    article_motions = {}
    if not missing_motions:
        from build_hero_neutral_b_assets import base
        for article, names in [('spark', ('special_s1', 'special_s2', 'special_s32')),
                               ('lightning', ('regular',))]:
            paths = [next((ROOT / 'refs').glob('**/fighter/brave/motion/' + article
                                              + f'/c{slot:02d}/motion_list.bin'))
                     for slot in (0, 6, 7)]
            assert all(p.read_bytes() == paths[0].read_bytes() for p in paths)
            magic, path_hash, entries = base.parse_mlist(paths[0])
            assert base.encode_mlist(magic, path_hash, entries) == paths[0].read_bytes()
            assert set(entries) == {base.hash40(name) for name in names}
            assert all(not entry['animations'] for entry in entries.values())
            article_motions[article] = {
                'inputs': {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in paths},
                'c00_c06_c07_byte_equal': True,
                'entries': [{'motion': name, 'motion_hash': hex(base.hash40(name)),
                             'game_script_hash': hex(entries[base.hash40(name)]['game_script']),
                             'animation_hashes': [], 'flags': entries[base.hash40(name)]['flags'],
                             'tail_hex': entries[base.hash40(name)]['raw'][24:].hex()}
                            for name in names]}
    clone = ROOT / 'src/mgw_standalone/smashline_1304/src/cloning/weapons.rs'
    api = ROOT / 'src/mgw_standalone/smashline_1304/src/api.rs'
    clone_text = clone.read_text()
    assert 'new_descriptors.push(article);' in clone_text
    assert 'pub on_init_callback:' in clone_text
    export = api.read_text().split('pub extern "C" fn smashline_clone_weapon(', 1)[1].split(') -> i32', 1)[0]
    assert 'use_original_code: bool' in export and 'callback' not in export

    listing = ['# Generated by tools/audit_hero_side_b.py v' + VERSION,
               '# Tier B: instruction bytes, not hardware behavior.']
    for name, start, end in spans:
        listing += [f'\n# main {name} {start:#x}..{end:#x} sha256={sha(main.data[start:end])}']
        listing += [f'{i.address:#010x} {i.mnemonic:8} {i.op_str}'
                    for i in main.disasm(start, end - start)]
    for name, start, end in [('sp_setter', 0x1a230, 0x1a344),
                             ('spark_success_guard', 0x28ce0, 0x28d90),
                             ('hold_exec', 0x58f0, 0x5b00)]:
        listing += [f'\n# brave NRO {name} {start:#x}..{end:#x}']
        for i in nro_util.disasm(flat, start, end - start):
            extra = ''
            if i.mnemonic == 'bl':
                extra = ' ; ' + plt.get(int(i.op_str.lstrip('#'), 0), 'local helper')
            if i.mnemonic == 'mov' and i.op_str.startswith('w8, #'):
                extra = ' ; ' + str(nro_util.const_name(int(i.op_str.split('#')[1], 0)))
            listing.append(f'{i.address:#010x} {i.mnemonic:8} {i.op_str}{extra}')

    report = {
        'date': '2026-09-30', 'tier': 'B', 'tool': 'tools/audit_hero_side_b.py',
        'tool_version': VERSION, 'tool_sha256': sha(Path(__file__).read_bytes()),
        'inputs': {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in
                   (nro, main.path, clone, api, skeleton, clip,
                    ROOT / cfg['dumps']['arc'] / 'fighter/brave/param/vl.prc',
                    ROOT / 'dumps/decoded/arc_files.tsv')},
        'skeleton_recheck': {'animated': 125, 'matched': 68, 'missing': 57,
                             'mantle_missing': 12, 'skirt_missing': 40,
                             'other_missing': other_missing},
        'status_rows': rows, 'status_table_reproduced': True,
        'sp_setter': {'helper': '0x1a230', 'caller': '0x16db0',
                      'reads': ['FIGHTER_BRAVE_INSTANCE_WORK_ID_FLOAT_SP',
                                'FIGHTER_BRAVE_INSTANCE_WORK_ID_FLOAT_MAX_SP'],
                      'comparison': 'amount <= SP: set passed flag; otherwise clear',
                      'attack_call_sites': ['0xe830', '0xeab0', '0xed80'],
                      'neutral_b_control': '0xce38'},
        'spark_guard': {'helper': '0x28ce0', 'branch': '0x28d6c',
                        'reading': 'success == false branches to epilogue 0x29488; success true continues'},
        'third_brief_address': {'address': '0x2ad40', 'constant': 'HOLD_FRAME, not SUCCESS_SP'},
        'native_descriptors': {'spark': spark, 'lightning': lightning},
        'native_spans': [{'name': n, 'start': hex(a), 'end': hex(b),
                          'sha256': sha(main.data[a:b])} for n, a, b in spans],
        'owner_reads': {
            'spark': {'status_comparisons': ['0x1e7', '0x1e8', '0x1ea'],
                      'log_group_id': '0x100000c3'},
            'lightning': {'offset_x_id': '0x0100000e', 'team_no_id': '0x1100000c',
                          'owner_id': '0x1100000d'}},
        'spark_class_callback': {'vtable_slot': '0x51b2298', 'function': '0x33cbb20',
                                 'manager_read': 'main+0x33cbb40 -> Hero slot +0x1298',
                                 'field_offsets': ['0x23c', '0x240', '0x24c', '0x250',
                                                   '0x254', '0x25c', '0x260', '0x264']},
        'lightning_map_collection': {
            'function': '0x33cabd0', 'nro_call_site': '0x45768',
            'owner_flag_argument': '0x21000015',
            'route': 'An owned weapon script can call an owned copy; this caller does not itself require another hook.'},
        'missing_article_motion_lists': missing_motions,
        'article_motion_lists': article_motions,
        'authorized_hook_sites': ['0x85d580', '0x85dad0', '0x33cbb20'],
        'blocker': ('Exact spark/lightning article motion lists are missing; request extraction under AGENTS rule 2.'
                    if missing_motions else 'Requested c00/c06/c07 article motion lists are present; owned move implementation and full dependency coverage remain pending.'),
        'scope': 'Mana remains excluded; no gauge read in recipient code is proposed.',
        'hardware_validated': False,
        'limitations': ['No new hardware run or failure cause established.',
                        'Native callback coverage is incomplete; more hooks may be required after full audit.',
                        'Class callback field names have not been decoded here.',
                        'Clone callback retention is pinned local source evidence, not a new console observation.'],
    }
    return {'native_dependency_audit.json': json.dumps(report, indent=2) + '\n',
            'native_dependency_audit.asm.txt': '\n'.join(listing) + '\n'}


def main_cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, text in generate().items():
        path = DEST / name
        if args.check:
            assert path.read_text() == text, f'stale {path.relative_to(ROOT)}'
        else:
            path.write_text(text)
    print('PASS: donor status table, SP setter/guard, retained native initializers and parameter read')


if __name__ == '__main__':
    main_cli()
