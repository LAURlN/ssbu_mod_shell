"""Pin Snake's common item-hold motion dependency and recovered status evidence (v1.0.0).

--check re-measures the shipped NRO and compares the JSON/assembly outputs.
--pin-decompile promotes the earlier Ghidra evidence after comparing flattened
inputs with the original NROs. Decompiler C is evidence, never executable code.
This audit identifies literal motion hashes, not runtime success or a cause.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_snake_neutral_b_assets as assets
ROOT = assets.ROOT
sys.path[:0] = [str(ROOT / 'tools/nro_decomp'), str(ROOT / 'toolchains/python_tools')]
import nro_flatten
import capstone

def sha(data):
    return hashlib.sha256(data).hexdigest()

def outputs():
    path = assets.ARC / 'prebuilt/nro/release/lua2cpp_common.nro'
    data = path.read_bytes()
    image, _ = nro_flatten.flatten(data)
    symbols, _, _ = nro_flatten.parse(data)
    symbol = next(s for s in symbols if s[0] == '_ZN7lua2cpp16L2CFighterCommon45sub_ftStatusUniqProcessShoot_initShoot_CommonEN3lib8L2CValueES2_')
    _, _, _, start, size = symbol
    assert (start, size) == (0x1d68d0, 5212)
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    instructions = list(md.disasm(image[start:start + size], start))
    names = ['item_shoot_legs_' + part for part in
             ('wait', 'walk_f', 'walk_b', 'dash_f', 'dash_b', 'brake_f', 'brake_b',
              'jump_squat', 'landing', 'slow_f', 'middle_f', 'fast_f', 'slow_b', 'middle_b', 'fast_b')]
    hashes = {assets.base.hash40(name): name for name in names}
    registers, found = {}, []
    for ins in instructions:
        match = re.fullmatch(r'([wx])(\d+), #(0x[0-9a-f]+|-?\d+)', ins.op_str)
        if ins.mnemonic in ('mov', 'movz') and match:
            registers[match[2]] = int(match[3], 0) & ((1 << 64) - 1)
        elif ins.mnemonic == 'movk':
            match = re.fullmatch(r'([wx])(\d+), #(0x[0-9a-f]+|\d+)(?:, lsl #(\d+))?', ins.op_str)
            if match and match[2] in registers:
                shift = int(match[4] or 0)
                value = (registers[match[2]] & ~(0xffff << shift)) | int(match[3], 0) << shift
                registers[match[2]] = value
                if value in hashes:
                    found.append({'pc': ins.address, 'name': hashes[value], 'hash40': hex(value)})
    assert 'item_shoot_legs_wait' in {entry['name'] for entry in found}
    record = {'tool_version': '1.0.0', 'date': '2026-09-30', 'evidence_tier': 'B',
        'hardware_validated': False, 'input': path.relative_to(ROOT).as_posix(), 'sha256': sha(data),
        'function': symbol[0], 'offset': start, 'size': size,
        'function_sha256': sha(image[start:start + size]), 'literal_motion_hashes': found,
        'lower_motion_dependencies': assets.lower_dependencies(),
        'remaining': 'Owned lower dispatch/ACMD translated; hardware test pending. See lower_translation_audit.json'}
    asm = '\n'.join(f'{i.address:#x}  {i.mnemonic} {i.op_str}' for i in instructions) + '\n'
    return {ROOT / 'refs/snake_grenade/common_motion_audit.json': json.dumps(record, indent=2) + '\n',
            ROOT / 'refs/snake_grenade/common_item_shoot_init.asm': asm}

def pin_decompile():
    scratch = ROOT / 'scratch/2026-09-30_claude_snakegren/snake_ghidra'
    source = assets.ARC / 'prebuilt/nro/release/lua2cpp_snake.nro'
    image, _ = nro_flatten.flatten(source.read_bytes())
    assert (scratch / 'nro.bin').read_bytes() == image
    dest = ROOT / 'refs/snake_grenade/status_1304'
    dest.mkdir(exist_ok=True)
    files = {}
    for name in ('special_n.c', 'special_n_helpers.c', 'special_n_helpers2.c', 'special_n_helpers3.c', 'status_table.txt'):
        data = (scratch / name).read_bytes()
        (dest / name).write_bytes(data)
        files[name] = sha(data)
    report = {'date': '2026-09-30', 'evidence_tier': 'B', 'hardware_validated': False,
        'source': source.relative_to(ROOT).as_posix(), 'source_sha256': sha(source.read_bytes()),
        'flattened_sha256': sha(image), 'tool': 'tools/nro_decomp/run_ghidra.sh; Ghidra 11.1.2; annotate_c.py',
        'promoted_by': 'tools/audit_snake_grenade_common.py --pin-decompile',
        'note': 'Earlier scratch decompilation; input matches current NRO. Confirm dropped Lua operands in assembly.',
        'output_sha256': files}
    (dest / 'SOURCE.json').write_text(json.dumps(report, indent=2) + '\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pin-decompile', action='store_true')
    args = parser.parse_args()
    if args.pin_decompile:
        assert not args.check
        pin_decompile()
    for path, content in outputs().items():
        if args.check:
            assert path.read_text() == content
        else:
            path.write_text(content)
    if args.check:
        path = ROOT / 'refs/snake_grenade/status_1304/SOURCE.json'
        report = json.loads(path.read_text())
        for name, digest in report['output_sha256'].items():
            assert sha((path.parent / name).read_bytes()) == digest
    print('PASS: common lower wait hash measured; dependencies and recovered status hashes pinned')

if __name__ == '__main__':
    main()
