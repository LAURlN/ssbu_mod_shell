"""Recover side-B ACMD registrations directly from the pinned Brave 13.0.4 NRO.

Version 1.0.1. Tracks only literal script hashes and implementation addresses
at sv_set_function_hash calls in native factories, then unwraps the generated
variadic thunks. Duplicate script names in fighter/weapon classes stay distinct.
No ACMD arguments are guessed from text dumps. --check regenerates the pinned
JSON; this is a smoke test of registration recovery, not gameplay validation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tomllib
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools/nro_decomp')]
import nro_flatten
import nro_util


def hash40(name):
    return len(name) << 32 | zlib.crc32(name.encode())


def generate():
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    src = ROOT / cfg['dumps']['arc'] / 'prebuilt/nro/release/lua2cpp_brave.nro'
    blob = src.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    assert digest == 'dc5edcde314f0c461ba0ab08d9e9deef5ede9d5b4ed324141678b9966d43b7a2'
    flat, meta = nro_flatten.flatten(blob)
    plt = nro_util.plt_map(flat, meta['labels'], meta['text_end'])
    setter = next(a for a, name in plt.items() if 'sv_set_function_hash' in name)
    suffixes = [f'special{air}s{phase}' for air in ('', 'air')
                for phase in ('start', 'hold', '1', '2', '3', '32', 'holdm', 'holdmax')]
    names = {hash40(category + '_' + suffix): category + '_' + suffix
             for category in ('game', 'effect', 'sound', 'expression')
             for suffix in suffixes + ['regular']}
    regs, rows = {}, []
    for instruction in nro_util.disasm(flat, 0x4a6e0, 0x7900):
        args = instruction.op_str.split(', ')
        op = instruction.mnemonic
        if op == 'mov' and len(args) == 2 and args[1].startswith('#'):
            regs[args[0]] = int(args[1][1:], 0) & ((1 << 64) - 1)
        elif op == 'movk':
            shift = int(args[2].split('#')[1]) if len(args) == 3 else 0
            regs[args[0]] = ((regs.get(args[0], 0) & ~(65535 << shift))
                             | (int(args[1][1:], 0) << shift))
        elif op == 'adrp':
            regs[args[0]] = int(args[1][1:], 0)
        elif op == 'add' and len(args) == 3 and args[2].startswith('#'):
            regs[args[0]] = regs.get(args[1], 0) + int(args[2][1:], 0)
        elif op == 'bl' and int(args[0][1:], 0) == setter and regs.get('x2') in names:
            wrapper = regs['x1']
            body = list(nro_util.disasm(flat, wrapper, 0x90))
            short = body[7].mnemonic == 'bl' and body[8].mnemonic == 'sub' and body[8].op_str == 'sp, sp, #0x50'
            span = 0x20 if short else 0x90
            calls = [int(i.op_str[1:], 0) for i in nro_util.disasm(flat, wrapper, span)
                     if i.mnemonic == 'bl' and int(i.op_str[1:], 0) not in plt]
            assert (short and len(calls) == 1) or (len(calls) == 2 and calls[0] == calls[1]), hex(wrapper)
            rows.append({'script': names[regs['x2']], 'script_hash': hex(regs['x2']),
                         'registration': hex(instruction.address), 'wrapper': hex(wrapper),
                         'wrapper_size': span,
                         'wrapper_sha256': hashlib.sha256(flat[wrapper:wrapper + span]).hexdigest(),
                         'implementation': hex(calls[0])})
    assert any(row['script'] == 'game_specials3' for row in rows)
    assert sum(row['script'] == 'game_specials1' for row in rows) == 2
    s3 = next(row for row in rows if row['script'] == 'game_specials3')
    body = []
    for instruction in nro_util.disasm(flat, int(s3['implementation'], 16), 0x1000):
        body.append(instruction)
        if instruction.mnemonic == 'ret':
            break
    assert body[-1].mnemonic == 'ret'
    calls = [(i.address, int(i.op_str[1:], 0)) for i in body if i.mnemonic == 'bl']
    assert all(target in plt for _, target in calls), 'unexamined S3 local helper'
    assert not any('sv_animcmd6ATTACK' in plt[target] for _, target in calls)
    assert any('WorkModule__on_flag' in plt[target] for _, target in calls)
    constants = [nro_util.const_name(int(i.op_str.split('#')[1], 0))
                 for i in body if i.mnemonic == 'mov' and i.op_str.startswith('w8, #')]
    assert 'FIGHTER_BRAVE_STATUS_SPECIAL_S_FLAG_ACTIVATE_LIGHTNING' in constants
    instructions = {i.address: i for i in body}
    assert instructions[0x1155ac].op_str == 'w1, #0xa'
    assert instructions[0x1155b4].op_str == '#0x23a0e0'
    assert 'L2CValueC' in plt[0x23a0e0]
    assert instructions[0x1155dc].op_str == '#0x23b000'
    assert 'sv_animcmd5frame' in plt[0x23b000]
    aliases = [row for row in rows if row['script'] in ('game_specials3', 'game_specialairs3')]
    assert len(aliases) == 2 and {row['implementation'] for row in aliases} == {'0x115590'}
    start, end = body[0].address, body[-1].address + 4
    return {'date': '2026-09-30', 'tier': 'B', 'tool_version': '1.0.1',
            'tool': 'tools/audit_hero_side_b_acmd.py',
            'input': src.relative_to(ROOT).as_posix(), 'sha256': digest,
            'registrations': rows, 'hardware_validated': False,
            'attack3_game': {'implementation': hex(start), 'through_first_return': hex(end),
                            'sha256': hashlib.sha256(flat[start:end]).hexdigest(),
                            'direct_attack_calls': 0, 'local_helpers': [], 'activation_frame': 10,
                            'constants': constants,
                            'calls': [{'site': hex(site), 'import': plt[target]} for site, target in calls],
                            'reading': 'Native fighter S3 sets ACTIVATE_LIGHTNING; no direct ATTACK or local helper in this body.'},
            'limitations': ['Native ACMD arguments still require recovery from the implementations.',
                            'Duplicate script hashes belong to different native classes; do not collapse them.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    report = generate()
    text = json.dumps(report, indent=2) + '\n'
    dest = ROOT / 'refs/brave_special_s/acmd_native_registrations.json'
    if args.check:
        assert dest.read_text() == text, 'stale native registration audit'
    else:
        dest.write_text(text)
    print(f"PASS: {len(report['registrations'])} native side-B/regular ACMD registrations and variadic thunk targets")


if __name__ == '__main__':
    main()
