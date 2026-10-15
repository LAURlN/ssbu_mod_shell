#!/usr/bin/env python3
"""Largest stack frames in a plugin NRO.

The plugin's `main` runs on a 64 KiB Skyline thread stack (session 4, 2026-10-07: a 325 KiB
frame in `main` crashed the boot before the first log line). This scans the NRO for
`sub sp, sp, #imm` (both the plain and the `lsl #12` form, adding adjacent pairs) and fails
when one frame exceeds the limit.

usage: python tools/stack-frames/stack_frames.py <file.nro> [--limit BYTES] [--top N]
exit 0: every frame is within the limit; 1: a frame exceeds it; 2: bad arguments.
"""
import struct
import sys

# 0.6.0 ran on the console with a largest frame of 19584 bytes (tier A); stay near that.
DEFAULT_LIMIT = 24 * 1024


def frames(data):
    words = struct.unpack_from('<%dI' % (len(data) // 4), data, 0)
    out = []
    i = 0
    while i < len(words):
        w = words[i]
        # SUB (immediate), 64-bit, Rn = Rd = SP
        if (w & 0xFF8003FF) == 0xD10003FF:
            start = i
            size = 0
            while i < len(words) and (words[i] & 0xFF8003FF) == 0xD10003FF:
                imm = (words[i] >> 10) & 0xFFF
                size += imm << 12 if (words[i] >> 22) & 1 else imm
                i += 1
            out.append((size, start * 4))
            continue
        i += 1
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    limit, top = DEFAULT_LIMIT, 8
    if '--limit' in argv:
        limit = int(argv[argv.index('--limit') + 1], 0)
    if '--top' in argv:
        top = int(argv[argv.index('--top') + 1], 0)
    data = open(argv[1], 'rb').read()
    found = sorted(frames(data), reverse=True)
    print('%s: %d frame allocations, limit %d bytes' % (argv[1], len(found), limit))
    for size, off in found[:top]:
        print('  %8d bytes at file offset 0x%x%s' % (size, off, '  OVER LIMIT' if size > limit else ''))
    over = [f for f in found if f[0] > limit]
    print('FAIL: %d frame(s) over the limit' % len(over) if over else 'OK')
    return 1 if over else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
