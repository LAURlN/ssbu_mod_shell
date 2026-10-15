"""Measure the compiled pgwr capture guard's syscall ABI boundary (1.0.1).

Usage/smoke: toolchains/py312/python.exe tools/audit_pgwr_svc_guard.py --version 0.20.6
Verifies the linked C-ABI stub against the pinned runtime's five instructions,
and verifies the guard calls it rather than issuing an inline SVC. Writes a
versioned JSON/disassembly audit. Offline ABI measurement, not hardware proof.
1.0.1 resolves the named zero-size asm symbol instead of assuming unique bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from main_image import MainImage


def functions(blob):
    assert blob[:5] == b'\x7fELF\x02'
    offset = struct.unpack_from('<Q', blob, 40)[0]
    stride, count = struct.unpack_from('<HH', blob, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', blob, offset + i * stride) for i in range(count)]
    result = {}
    for section in sections:
        if section[1] not in (2, 11): continue
        strings = sections[section[6]]
        for position in range(section[4], section[4] + section[5], 24):
            name, info, _, _, address, size = struct.unpack_from('<IBBHQQ', blob, position)
            if info & 15 != 2: continue
            start = strings[4] + name
            name = blob[start:blob.index(b'\0', start)].decode()
            if not size:
                if name != 'pgwr_capture_query_memory': continue
                size = 20
            text = next((s for s in sections if s[1] == 1 and s[3] <= address < s[3] + s[5]), None)
            if text:
                start = text[4] + address - text[3]
                result[name] = (address, blob[start:start + size])
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', required=True)
    args = p.parse_args()
    path = ROOT / 'builds/.cache/pgwr-target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.so'
    blob = path.read_bytes()
    funcs = functions(blob)
    # The asm symbol has no .size directive, so find it through a matching symbol
    # parsed below if it is absent from the sized function table.
    if 'pgwr_capture_query_memory' not in funcs:
        # The linked stub sequence matches the pinned be3ef308 svc.s wrapper.
        raw = bytes.fromhex('e10f1ff8c10000d4e20741f8410000b9c0035fd6')
        assert blob.count(raw) == 1
        file_offset = blob.index(raw)
        # Translate file offset using PT_LOAD headers.
        phoff = struct.unpack_from('<Q', blob, 32)[0]
        phstride, phcount = struct.unpack_from('<HH', blob, 54)
        for i in range(phcount):
            typ, _, off, va, _, size, _, _ = struct.unpack_from('<IIQQQQQQ', blob, phoff + i * phstride)
            if typ == 1 and off <= file_offset < off + size:
                funcs['pgwr_capture_query_memory'] = (va + file_offset - off, raw)
                break
    address, code = funcs['pgwr_capture_query_memory']
    img = MainImage()
    stub = list(img.md.disasm(code[:20], address))
    assert [(i.mnemonic, i.op_str) for i in stub] == [
        ('str', 'x1, [sp, #-0x10]!'), ('svc', '#6'),
        ('ldr', 'x2, [sp], #0x10'), ('str', 'w1, [x2]'), ('ret', '')]
    guard_name, (guard_address, guard_code) = next((name, value) for name, value in funcs.items()
        if 'monkey_flip_capture' in name and name.endswith('6mapped'))
    guard = list(img.md.disasm(guard_code, guard_address))
    assert not any(i.mnemonic == 'svc' for i in guard)
    assert any(i.mnemonic == 'bl' and int(i.op_str.lstrip('#'), 0) == address for i in guard)
    report = {'date': '2026-09-30', 'tier': 'B', 'version': args.version,
        'tool': 'tools/audit_pgwr_svc_guard.py', 'tool_version': '1.0.1',
        'elf_sha256': hashlib.sha256(blob).hexdigest(),
        'stub_source': {'repo': 'https://github.com/hdr-development/smashline',
                        'commit': 'be3ef308ed8e479922da192a391e0684184af2af',
                        'path': 'crates/rtld/src/svc.s'},
        'guard_symbol': guard_name, 'stub_offset': hex(address),
        'stub': [f'{i.mnemonic} {i.op_str}'.strip() for i in stub],
        'guard': [f'{i.address:#x}: {i.mnemonic} {i.op_str}'.strip() for i in guard],
        'limitation': 'Establishes C-call boundary, not why the prior guard refused console events.'}
    out = ROOT / 'builds/pgwr' / args.version / 'capture_guard_audit.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: pinned five-instruction SVC stub and compiled guard call boundary')


if __name__ == '__main__':
    main()
