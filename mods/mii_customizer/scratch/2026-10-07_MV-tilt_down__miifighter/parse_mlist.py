#!/usr/bin/env python3
"""Dump motion_list.bin entries (kind, game, flags, anims, tail) and match names by hash40.

Usage: python parse_mlist.py <motion_list.bin> [name ...]
Run from the workspace root.
"""
import struct
import sys
import zlib


def hash40(s: str) -> int:
    return (len(s) << 32) | (zlib.crc32(s.encode('utf-8')) & 0xFFFFFFFF)


def parse(data: bytes):
    magic, path, count = struct.unpack_from('<QQQ', data, 0)
    off = 24
    out = []
    for i in range(count):
        start = off
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, off)
        off += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, off)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        t = data[tail:end]
        expr, snd, eff = struct.unpack_from('<QQQ', t, 0) if len(t) >= 24 else (0, 0, 0)
        unk, cancel = struct.unpack_from('<HH', t, 24) if len(t) >= 28 else (0, 0)
        out.append(dict(index=i, kind=kind, game=game, flags=flags, blend=blend,
                        n_anims=n_anims, anims=anims, size=size, expr=expr, snd=snd,
                        eff=eff, unk=unk, cancel=cancel, tail_len=len(t), start=start, end=end))
        off = end
    return magic, path, out


def main():
    src = sys.argv[1]
    names = sys.argv[2:]
    data = open(src, 'rb').read()
    magic, path, ents = parse(data)
    print(f"file={src} bytes={len(data)} count={len(ents)} end_offset={ents[-1]['end']} total={len(data)}")
    lookup = {hash40(n): n for n in names}
    lookup_game = {hash40('game_' + n.replace('_', '')): 'game_' + n.replace('_', '') for n in names}
    for e in ents:
        kname = lookup.get(e['kind'], '?')
        print(f"{e['index']:4d} kind=0x{e['kind']:010x} ({kname}) game=0x{e['game']:010x} "
              f"flags=0x{e['flags']:04x} blend={e['blend']} anims={e['n_anims']} size={e['size']} "
              f"cancel={e['cancel']} unk=0x{e['unk']:04x} tail_len={e['tail_len']}")
        if e['n_anims']:
            print(f"      anim0=0x{e['anims'][0]:010x} expr=0x{e['expr']:010x} snd=0x{e['snd']:010x} eff=0x{e['eff']:010x}")


if __name__ == '__main__':
    main()
