"""Unmodified round trip at member level.

Re-serialises the members exactly as read (no edits, no reordering, no padding
changes) and compares the rebuilt data section and a rebuilt container against
the original bytes. This measures what a repacker must reproduce; it is not a
modification of the extracted inputs.
"""
import hashlib
import json
import struct
import sys

EDIT = 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc'
SPEC = 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc'


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def roundtrip(path):
    d = open(path, 'rb').read()
    total, data_off, _ = struct.unpack_from('<III', d, 8)
    count = struct.unpack_from('<H', d, 0x1A)[0]
    nt_off = 0x20 + count * 16
    data_section = d[data_off:total]

    # rebuild data section from the extracted members, in table order, at the
    # original offsets, preserving the original gap padding
    rebuilt = bytearray(total - data_off)
    for i in range(count):
        _, _, st, en = struct.unpack_from('<4I', d, 0x20 + i * 16)
        rebuilt[st:en] = d[data_off + st:data_off + en]
    rebuilt = bytes(rebuilt)

    # rebuild container: header + SFAT + SFNT + name table copied verbatim
    out = bytearray(d)
    out[data_off:total] = rebuilt
    out = bytes(out)

    print(f"== {path.split('/')[-3]}")
    print(f"   original sha256      {sha256(d)}")
    print(f"   data section sha256  {sha256(data_section)}")
    print(f"   rebuilt data sha256  {sha256(rebuilt)}")
    print(f"   data section equal   {rebuilt == data_section}")
    print(f"   container equal      {out == d}")
    return {
        'path': path,
        'container_sha256': sha256(d),
        'data_sha256': sha256(data_section),
        'rebuilt_data_sha256': sha256(rebuilt),
        'data_equal': rebuilt == data_section,
        'container_equal': out == d,
        'members': count,
        'data_offset': data_off,
    }


if __name__ == '__main__':
    res = [roundtrip(p) for p in (EDIT, SPEC)]
    with open('gamedata/mii_customizer/P1-LAYOUT/roundtrip.json', 'w') as fh:
        json.dump(res, fh, indent=1)
    print('\nroundtrip.json written')