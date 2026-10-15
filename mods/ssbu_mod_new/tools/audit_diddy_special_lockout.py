"""Audit donor Monkey Flip end flags and special availability (1.0.0).

Usage: toolchains/py312/python.exe tools/audit_diddy_special_lockout.py [--smoke]
Smoke asserts actual shipped NRO instructions; default pins the report in refs.
Read-only dumps through paths.toml. No donor work IDs are applied to recipients.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools/nro_decomp'), str(ROOT / 'tools')]
from nro_flatten import flatten
import nro_util as u
from status_table import table


def audit():
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    path = ROOT / cfg['dumps']['arc'] / 'prebuilt/nro/release/lua2cpp_diddy.nro'
    raw = path.read_bytes()
    img, meta = flatten(raw)
    rows = table(img, meta)
    expected = [('JUMP', 0xd830, 0x77fc, 'FIGHTER_DIDDY_INSTANCE_WORK_ID_FLAG_SPECIAL_S_INPUT_UNABLE'),
                ('KICK', 0xd8f0, 0x77f8, 'FIGHTER_DIDDY_INSTANCE_WORK_ID_FLAG_SPECIAL_INPUT_UNABLE'),
                ('STICK_ATTACK2', 0xdc00, 0x77f8, 'FIGHTER_DIDDY_INSTANCE_WORK_ID_FLAG_SPECIAL_INPUT_UNABLE')]
    plt = u.plt_map(img, meta['labels'], meta['text_end'])
    blocks = {}
    for name, address, offset, flag in expected:
        assert ('FIGHTER_DIDDY_STATUS_KIND_SPECIAL_S_' + name,
                'LUA_SCRIPT_STATUS_FUNC_STATUS_END', address) in rows
        assert u.const_name(offset) == flag
        instructions = list(u.disasm(img, address, 0xc0))
        assert any(i.mnemonic == 'mov' and i.op_str == f'w8, #{offset:#x}' for i in instructions)
        assert any(i.mnemonic == 'bl' and 'WorkModule__on_flag_impl' in
                   plt.get(int(i.op_str.lstrip('#'), 0), '') for i in instructions)
        blocks[name] = [{'offset': hex(i.address), 'instruction': f'{i.mnemonic} {i.op_str}'.strip(),
                         'import': plt.get(int(i.op_str.lstrip('#'), 0), '') if i.mnemonic == 'bl' else ''}
                        for i in instructions]
    callback = list(u.disasm(img, 0x7920, 0x2cc))
    for offset, name in [(0xb4, 'HI'), (0xc0, 'S'), (0xcc, 'LW')]:
        assert u.const_name(offset) == 'FIGHTER_STATUS_TRANSITION_TERM_ID_CONT_SPECIAL_' + name
        assert any(i.mnemonic == 'ldr' and i.op_str == f'w1, [x22, #{offset:#x}]' for i in callback)
    assert any(i.mnemonic == 'bl' and 'unable_transition_term' in
               plt.get(int(i.op_str.lstrip('#'), 0), '') for i in callback)
    return {'date': '2026-09-30', 'tier': 'B', 'tool_version': '1.0.0',
            'input': path.relative_to(ROOT).as_posix(), 'input_sha256': hashlib.sha256(raw).hexdigest(),
            'tool': 'tools/audit_diddy_special_lockout.py', 'end_blocks': blocks,
            'callback_0x7920': [f'{i.address:#x}: {i.mnemonic} {i.op_str}'.strip() for i in callback],
            'rules': ['JUMP end to FALL sets side-B input unable.',
                      'KICK/STICK_ATTACK2 end to FLIP_FALL sets general special input unable.',
                      'Availability callback disables HI/S/LW for general flag, S for side flag.'],
            'limitation': 'Ported refresh and callback integration require hardware tests; neutral-B is not disabled by this callback.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smoke', action='store_true')
    args = p.parse_args()
    report = audit()
    if not args.smoke:
        (ROOT / 'refs/diddy_monkey_flip/special_lockout.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: donor end flags and HI/S/LW availability instructions')
