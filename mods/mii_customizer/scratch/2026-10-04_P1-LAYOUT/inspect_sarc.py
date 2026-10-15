"""Read-only SARC inspector for the Mii editor layout archives.

Parses the SARC container, extracts members to a task-owned gamedata folder and
writes a manifest with hashes. It never writes a repacked archive.
"""
import hashlib
import json
import os
import struct
import sys

EDIT = 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc'
SPEC = 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc'
OUT = 'gamedata/mii_customizer/P1-LAYOUT/unpacked'


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def parse(path):
    d = open(path, 'rb').read()
    magic, hsz, ver_raw = struct.unpack_from('<4sHH', d, 0)
    ver_be = struct.unpack_from('>H', d, 6)[0]
    total, data_off, f10 = struct.unpack_from('<III', d, 8)
    assert magic == b'SARC', magic
    assert hsz == 0x14, hsz
    # the version word is stored big-endian (bytes ff fe -> BE 0xFFFE)
    assert ver_raw == 0xFEFF and ver_be == 0xFFFE, (hex(ver_raw), hex(ver_be))
    assert total == len(d), (total, len(d))
    assert d[0x14:0x18] == b'SFAT'
    sfat_hdr = struct.unpack_from('<H', d, 0x18)[0]
    count = struct.unpack_from('<H', d, 0x1A)[0]
    nt_off = 0x20 + count * 16
    assert d[nt_off:nt_off + 4] == b'SFNT', d[nt_off:nt_off + 4]
    nt_hdr = struct.unpack_from('<I', d, nt_off + 4)[0]
    name_base = nt_off + 8
    members = []
    for i in range(count):
        f0, f1, st, en = struct.unpack_from('<4I', d, 0x20 + i * 16)
        no = (f1 & 0xFFFFFF) * 4
        end = d.find(b'\x00', name_base + no)
        name = d[name_base + no:end].decode('ascii')
        blob = d[data_off + st:data_off + en]
        members.append({
            'index': i,
            'field0': f0,
            'name_off_field': f1,
            'name_off_bytes': no,
            'data_start': st,
            'data_end': en,
            'size': en - st,
            'name': name,
            'magic': blob[:4].decode('latin1'),
            'sha256': sha256(blob),
        })
    return {
        'path': path,
        'sha256': sha256(d),
        'size': len(d),
        'header': {
            'magic': magic.decode(),
            'header_size': hsz,
            'version_le_word': hex(ver_raw),
            'version': hex(ver_be),
            'size_field_0x08': total,
            'data_offset_0x0c': data_off,
            'field_0x10': hex(f10),
            'sfat_header_size': sfat_hdr,
            'member_count': count,
            'name_table_offset': nt_off,
            'name_table_header_field': nt_hdr,
        },
        'members': members,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    reports = []
    for src, tag in ((EDIT, 'make_mii_edit'), (SPEC, 'make_mii_special')):
        r = parse(src)
        root = os.path.join(OUT, tag)
        for m in r['members']:
            dst = os.path.join(root, *m['name'].split('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as fh:
                fh.write(open(src, 'rb').read()[0x2000 + m['data_start']:0x2000 + m['data_end']])
        reports.append(r)
        print(f"{tag}: {len(r['members'])} members -> {root}")
    with open('gamedata/mii_customizer/P1-LAYOUT/manifest.json', 'w') as fh:
        json.dump(reports, fh, indent=1)
    print('manifest written')


if __name__ == '__main__':
    main()