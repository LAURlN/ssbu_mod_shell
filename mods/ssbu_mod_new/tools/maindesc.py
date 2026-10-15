"""Print a fighter kind's native article descriptors from the 13.0.4 `main` image.

    toolchains/py312/python.exe tools/maindesc.py 0x1a        # G&W (FIGHTER_KIND_GAMEWATCH)

For each kind: the static fighter data record, its article-info block, and per article the global
weapon kind, the max count and the init / fini / extra callbacks (image offsets). Those offsets are
what `smashline::clone_weapon` copies onto the recipient, so the init callback is the native code
that runs when a cloned article is generated.

The per-kind table sits at `0x44bc18c`: an `i32` jump table whose targets are `adrp; add` pairs
yielding the kind's static fighter data (13.0.4 only; re-derive for another version).

2026-09-30: this file used to exec a scratch script against the pre-migration dump path and could not
run; rewritten on `tools/main_image.py`. Checked output: G&W is kind `0x1c` with nine descriptors,
`rescue` 0x78 init `0xa7f7b0`, `parachute` 0x79 init `0xa7fa90`, `normal_weapon` 0x7d init `0xa802a0`.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main_image import MainImage  # noqa: E402

STATIC_FIGHTER_DATA_TABLE = 0x44bc18c


def static_fighter_data(img: MainImage, kind: int) -> int:
    t = STATIC_FIGHTER_DATA_TABLE + img.i32(STATIC_FIGHTER_DATA_TABLE + 4 * kind)
    adrp, add = img.disasm(t, 8)
    return int(adrp.op_str.split('#')[1], 16) + int(add.op_str.split('#')[-1], 16)


def descriptors(img: MainImage, kind: int) -> list[dict]:
    sfd = static_fighter_data(img, kind)
    info = img.ptr(sfd + 8)
    out = []
    if info:
        base = img.ptr(info)
        count = struct.unpack_from('<Q', img.data, info + 8)[0]
        for i in range(count):
            a = base + i * 0x20
            wid, mx = struct.unpack_from('<ii', img.data, a)
            out.append({'index': i, 'weapon_kind': wid, 'max': mx, 'init': img.ptr(a + 8),
                        'fini': img.ptr(a + 16), 'extra': img.ptr(a + 24)})
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    img = MainImage()
    for kind in (int(x, 0) for x in sys.argv[1:]):
        sfd = static_fighter_data(img, kind)
        print(f'kind {kind:#x} static data {sfd:#x} id {img.i32(sfd):#x}')
        for d in descriptors(img, kind):
            print(f"   [{d['index']}] weapon {d['weapon_kind']:#x} max {d['max']} init {d['init']:#x} "
                  f"fini {d['fini']:#x} extra {d['extra']:#x}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
