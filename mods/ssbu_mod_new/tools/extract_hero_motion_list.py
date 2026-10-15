"""Read Hero's missing body motion list over arc-network, with no console writes.

Version 1.0.0. Usage: toolchains/py312/python.exe tools/extract_hero_motion_list.py
Smoke test: append --check to validate the existing extraction/hash/entry layout.
ABI follows src/pmclone/tools/extract_missing.py. Machine values use paths.toml.
Dump is stored in refs/brave_special_n, matching the existing Cloud reference
procedure; dumps/ is never written. Refuses to overwrite an existing dump.
"""
import argparse
import ctypes as c
import hashlib
import json
from pathlib import Path
import struct
import tomllib
import zlib

ROOT = Path(__file__).resolve().parents[1]
ARC_PATH = 'fighter/brave/motion/body/c00/motion_list.bin'
DEST = ROOT / 'refs/brave_special_n/motion_list.bin'
REPORT = DEST.with_name('extraction.json')


def validate(data):
    assert len(data) >= 24, 'motion list truncated'
    h = lambda s: (len(s) << 32) | zlib.crc32(s.encode())
    assert struct.unpack_from('<Q', data)[0] == h('motion'), 'wrong motion-list magic'
    count = struct.unpack_from('<Q', data, 16)[0]
    assert 0 < count < 2000, f'implausible motion count: {count}'
    assert all(struct.pack('<Q', h(name)) in data for name in
               ('special_n_start', 'special_n_hold', 'special_n1', 'special_air_n1'))
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        data = DEST.read_bytes()
        count = validate(data)
        assert hashlib.sha256(data).hexdigest() == json.loads(REPORT.read_text())['sha256']
        print(f'Hero motion list check OK: {count} motions')
        return
    assert not DEST.exists() and not REPORT.exists(), 'existing extraction will not be overwritten'
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    lib = c.CDLL(cfg['toolchain']['arc_network_dll'])
    lib.arc_open_networked.argtypes, lib.arc_open_networked.restype = [c.c_char_p], c.c_void_p
    lib.arc_free.argtypes, lib.arc_free.restype = [c.c_void_p], None
    lib.arc_extract_file_regional.argtypes = [c.c_void_p, c.c_uint64, c.c_char_p, c.c_uint32]
    lib.arc_extract_file_regional.restype = c.c_uint8
    ip = cfg['switch']['arc_network_ip']
    print(f'Opening arc-network {ip}:43022 (read only)', flush=True)
    handle = lib.arc_open_networked(ip.encode('ascii'))
    assert handle, 'arc-network returned no handle'
    temp = ROOT / 'scratch/2026-09-30_codex/hero_motion_list.partial'
    temp.parent.mkdir(parents=True, exist_ok=True)
    assert not temp.exists(), 'inspect prior partial extraction first'
    try:
        key = (len(ARC_PATH) << 32) | zlib.crc32(ARC_PATH.encode())
        result = lib.arc_extract_file_regional(handle, key, str(temp).encode('utf-8'), 2)
        assert result == 0 and temp.is_file(), f'extract result {result}'
        data = temp.read_bytes()
        count = validate(data)
        DEST.parent.mkdir(parents=True, exist_ok=True)
        temp.rename(DEST)
        report = {'date': '2026-09-30', 'arc_path': ARC_PATH, 'region': 2,
                  'game_version': cfg['switch']['game_version'], 'ip': ip,
                  'method': 'tools/extract_hero_motion_list.py v1.0.0 / arc_extract_file_regional',
                  'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'motions': count}
        REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(f'Extracted {DEST.relative_to(ROOT)}: {len(data)} bytes, {count} motions, sha256 {report["sha256"]}')
    finally:
        lib.arc_free(handle)


if __name__ == '__main__':
    main()
