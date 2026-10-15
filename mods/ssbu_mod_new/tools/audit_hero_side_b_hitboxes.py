"""Compare fighter side-B ATTACK arguments against native NRO decompilation.

Version 1.0.0. Native registration and ATTACK-helper bytes are verified first.
Ghidra output is pinned in refs/brave_special_s/acmd_game.c; produced by
tools/nro_decomp/ghidra_scripts/DecompStatus.py and annotate_c.py. Static float
loads resolve from the NRO image, and hash40 low words compare against full
text-dump hash names. Checks all branches as multisets: this does NOT validate
branch scoping or frame timing. Those need their separate native review.
Smoke test: generate, then --check (no gameplay assets or package emitted).
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import tomllib
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/nro_decomp'), str(ROOT / 'src/pgwr/tools')]
import nro_flatten
import nro_util
from gen_acmd import split_functions
from audit_hero_side_b_acmd import generate as registrations


def hash40(name):
    return len(name) << 32 | zlib.crc32(name.encode())


def normalize(value, image):
    value = value.strip()
    if value.startswith('PTR_NIL_') or value == 'None': return None
    if value.startswith('Some('): return normalize(value[5:-1], image)
    match = re.fullmatch(r'Hash40::new\("([^"]+)"\)', value)
    if match: return hash40(match[1]) & 0xffffffff
    if value.startswith('DAT_'): return round(struct.unpack_from('<f', image, int(value[4:], 16))[0], 5)
    if value in ('true', 'false'): return value == 'true'
    if value.startswith('*'): return value[1:]
    if value.startswith('_'): return value[1:]
    if value.startswith('0x'): return int(value, 16)
    try: return round(float(value), 5)
    except ValueError: raise AssertionError('unrecovered native argument: ' + value)


def arguments(text):
    result, start, depth = [], 0, 0
    for offset, ch in enumerate(text):
        depth += (ch == '(') - (ch == ')')
        if ch == ',' and depth == 0:
            result.append(text[start:offset].strip()); start = offset + 1
    result.append(text[start:].strip())
    return result


def generate():
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    src = ROOT / cfg['dumps']['arc'] / 'prebuilt/nro/release/lua2cpp_brave.nro'
    flat, meta = nro_flatten.flatten(src.read_bytes())
    plt = nro_util.plt_map(flat, meta['labels'], meta['text_end'])
    # Native helper ends with ATTACK tail-call, not ret; don't scan into its neighbor.
    helper = list(nro_util.disasm(flat, 0x105960, 0x2e8))
    assert helper[-1].mnemonic == 'b'
    assert 'sv_animcmd6ATTACK' in plt[int(helper[-1].op_str[1:], 0)]
    assert sum(i.mnemonic == 'bl' and 'push_lua_stack' in plt.get(int(i.op_str[1:], 0), '')
               for i in helper) == 36
    cfile = ROOT / 'refs/brave_special_s/acmd_game.c'
    ctext = cfile.read_text()
    sections = {int(m[1], 16): m[2] for m in re.finditer(
        r'// ==== FUN_([0-9a-f]+).*?\n(.*?)(?=// ====|\Z)', ctext, re.S)}
    report = []
    for script, stem in [('game_specials1', 'SpecialS1'), ('game_specials2', 'SpecialS2'),
                         ('game_specials32', 'SpecialS32')]:
        rows = [r for r in registrations()['registrations'] if r['script'] == script]
        row = next(r for r in rows if int(r['implementation'], 16) < 0x180000)
        body = sections[int(row['implementation'], 16)]
        native = []
        for match in re.finditer(r'FUN_00105960\((.*?)\);', body, re.S):
            values = dict(re.findall(r'L2CValue::L2CValue\((aLStack_\w+),([^;]*?)\);', body[:match.start()]))
            aliases = dict(re.findall(r'\b(fVar\d+) = ([^;]*);', body[:match.start()]))
            args = arguments(match[1])
            assert len(args) == 37 and args[0] == 'param_2'
            native.append(tuple(normalize(aliases.get(values.get(arg, arg), values.get(arg, arg)), flat)
                                for arg in args[1:]))
        path = ROOT / cfg['dumps']['scripts'] / 'smashline-hdr/lua2cpp_brave/brave' / (stem + '.txt')
        dump = split_functions(path.read_text())[script]
        printed = []
        for line in dump.splitlines():
            if 'ATTACK(agent,' not in line: continue
            args = arguments(line.strip().removeprefix('ATTACK(').removesuffix(');'))
            assert len(args) == 37 and args[0] == 'agent'
            printed.append(tuple(normalize(arg, flat) for arg in args[1:]))
        assert Counter(native) == Counter(printed), (script, len(native), len(printed),
            list((Counter(native) - Counter(printed)).elements())[:1],
            list((Counter(printed) - Counter(native)).elements())[:1])
        report.append({'script': script, 'implementation': row['implementation'],
                       'dump': path.relative_to(ROOT).as_posix(),
                       'dump_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                       'native_attacks': [list(values) for values in native],
                       'all_branch_argument_multiset_equal': True})
    return {'date': '2026-09-30', 'tier': 'B', 'tool_version': '1.0.0',
            'input_nro_sha256': hashlib.sha256(src.read_bytes()).hexdigest(),
            'decompilation': cfile.relative_to(ROOT).as_posix(),
            'decompilation_sha256': hashlib.sha256(cfile.read_bytes()).hexdigest(),
            'attack_helper': {'start': '0x105960', 'end': '0x105c48',
                              'sha256': hashlib.sha256(flat[0x105960:0x105c48]).hexdigest()},
            'scripts': report, 'hardware_validated': False,
            'limitations': ['Frame timing and success/failure scoping are not checked by argument multiset equality.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = json.dumps(generate(), indent=2) + '\n'
    path = ROOT / 'refs/brave_special_s/hitbox_native_audit.json'
    if args.check: assert path.read_text() == text, 'stale hitbox audit'
    else: path.write_text(text)
    print('PASS: native fighter S1/S2/S32 hitbox argument multisets equal pinned text; timing/scoping checked separately')


if __name__ == '__main__': main()
