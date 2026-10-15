"""Resolve Hero fireball's native article descriptor from the 13.0.4 main dump.

Version 1.0.0. No hooks, builds, or console calls. Resolves RELATIVE relocations
before reading pointers, then disassembles the descriptor init function.
Usage: toolchains/py312/python.exe tools/audit_hero_fireball_native.py [--check]
Smoke test: generate then --check; assertions verify fighter and weapon ids.
Table method: tools/maindesc.py; ids: skyline-smash pinned 315e4e8bebb460ebb9f02f30f07b0f13883ba3d6.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'toolchains/python_tools'))
import capstone


def generate():
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    main = ROOT / cfg['dumps']['exefs'] / 'main.bin'
    data = main.read_bytes()
    u32 = lambda addr: struct.unpack_from('<I', data, addr)[0]
    mod = u32(4)
    assert data[mod:mod + 4] == b'MOD0'
    dyn = mod + struct.unpack_from('<i', data, mod + 4)[0]
    tags = {}
    while True:
        tag, value = struct.unpack_from('<qQ', data, dyn)
        dyn += 16
        if tag == 0:
            break
        tags[tag] = value
    relocations = {}
    for addr in range(tags[7], tags[7] + tags[8], 24):
        offset, info, add = struct.unpack_from('<QQq', data, addr)
        if info & 0xffffffff == 0x403:
            relocations[offset] = add
    ptr = lambda addr: relocations.get(addr, struct.unpack_from('<Q', data, addr)[0])
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    table = 0x44bc18c
    kind = 0x53
    addr = table + struct.unpack_from('<i', data, table + 4 * kind)[0]
    ins = list(md.disasm(data[addr:addr + 8], addr))
    assert len(ins) == 2 and ins[0].mnemonic == 'adrp' and ins[1].mnemonic == 'add'
    sfd = int(ins[0].op_str.split('#')[1], 0) + int(ins[1].op_str.split('#')[-1], 0)
    assert struct.unpack_from('<i', data, sfd)[0] == kind
    info = ptr(sfd + 8)
    descriptor_table = ptr(info)
    count = ptr(info + 8)
    assert 0 < count < 50
    entries = []
    for index in range(count):
        entry = descriptor_table + index * 0x20
        weapon, maximum = struct.unpack_from('<ii', data, entry)
        entries.append({'local_article_id': index, 'weapon_kind': weapon, 'maximum': maximum,
                        'init': hex(ptr(entry + 8)), 'fini': hex(ptr(entry + 16)), 'extra': hex(ptr(entry + 24))})
    fireball = [entry for entry in entries if entry['weapon_kind'] == 0x1f5]
    assert len(fireball) == 1, 'Hero fireball descriptor not uniquely resolved'
    init = int(fireball[0]['init'], 16)
    assert 0 < init < 0x39c8000
    instructions = list(md.disasm(data[init:init + 0x600], init))
    # Stop at the first RET; keep the bytes available in the dump as evidence.
    end = next((i + 1 for i, instruction in enumerate(instructions) if instruction.mnemonic == 'ret'), len(instructions))
    instructions = instructions[:end]
    # The owner WorkModule getter receives Hero's instance charge id C1.
    assert u32(0x85cfd0) == 0xf9402ad5  # ldr x21, [x22, #0x50]
    assert u32(0x85cff4) == 0x11030281  # add w1, w20, #0xc0; w20 = 0x10000001
    cloning = ROOT / 'src/mgw_standalone/smashline_1304/src/cloning/weapons.rs'
    clone_source = cloning.read_text(encoding='utf-8')
    assert 'new_descriptors.push(article);' in clone_source
    assert 'pub on_init_callback:' in clone_source
    assembly = '\n'.join(f'{i.address:#010x}: {i.mnemonic:8} {i.op_str}' for i in instructions) + '\n'
    report = {'date': '2026-09-30', 'evidence_tier': 'B',
              'tool': 'tools/audit_hero_fireball_native.py', 'tool_version': '1.0.0',
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'input': main.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(data).hexdigest(),
              'fighter_kind': kind, 'static_fighter_data': hex(sfd), 'descriptor_table': hex(descriptor_table),
              'articles': entries, 'fireball': fireball[0], 'disassembly_byte_count': end * 4,
              'constructor_bytes_sha256': hashlib.sha256(data[init:init + end * 4]).hexdigest(),
              'cloning_source': cloning.relative_to(ROOT).as_posix(),
              'cloning_source_sha256': hashlib.sha256(cloning.read_bytes()).hexdigest(),
              'owner_charge_read': {'work_id': '0x100000c1', 'module_load': '0x85cfd0',
                                    'id_setup': '0x85cff4', 'virtual_getter_call': '0x85d000'},
              'limitation': 'Static descriptor and disassembly only; foreign-owner safety requires tracing constructor callees.'}
    return {'fireball_native.json': json.dumps(report, indent=2) + '\n', 'fireball_init.asm': assembly}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    dest = ROOT / 'refs/brave_special_n'
    for name, content in generate().items():
        path = dest / name
        if args.check:
            assert path.read_text(encoding='utf-8') == content, f'stale {name}'
        else:
            dest.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
    print('Hero native fireball descriptor/disassembly audit OK')


if __name__ == '__main__':
    main()
