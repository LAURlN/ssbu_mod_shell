"""Second round-trip variant: sequential 4-byte-aligned repack.

Purpose: quantify what a minimal repacker changes. Writes only into the
task-owned gamedata/mii_customizer/P1-LAYOUT/repacked/ folder, never touches the
originals under gamedata/mii_customizer/P1-UI/.
"""
import hashlib
import json
import os
import struct

EDIT = 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc'
SPEC = 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc'
OUT = 'gamedata/mii_customizer/P1-LAYOUT/repacked'
KEY = 0x65


def sfat_hash(s):
    h = 0
    for ch in s:
        h = (h * KEY + ord(ch)) & 0xFFFFFFFF
    return h


def repack(path, tag, member_align):
    d = open(path, 'rb').read()
    total, data_off, third = struct.unpack_from('<III', d, 8)
    count = struct.unpack_from('<H', d, 0x1A)[0]
    sfat_hdr = struct.unpack_from('<H', d, 0x18)[0]
    nbase = 0x20 + count * 16 + 8
    members = []
    for i in range(count):
        f0, f1, st, en = struct.unpack_from('<4I', d, 0x20 + i * 16)
        no = (f1 & 0xFFFFFF) * 4
        e = d.find(b'\x00', nbase + no)
        members.append((d[nbase + no:e].decode('ascii'), d[data_off + st:data_off + en]))

    # keep original SFAT (hash) order
    files = sorted(members, key=lambda kv: sfat_hash(kv[0]))

    strtab = bytearray()
    stroff = {}
    for name, _ in files:
        stroff[name] = len(strtab)
        strtab += name.encode('ascii') + b'\x00'
        while len(strtab) % 4:
            strtab += b'\x00'

    data = bytearray()
    ranges = {}
    for name, blob in files:
        start = (len(data) + member_align - 1) & ~(member_align - 1)
        data += b'\x00' * (start - len(data))
        data += blob
        ranges[name] = (start, start + len(blob))

    nt_end = 0x14 + 0x0C + len(files) * 0x10 + 8 + len(strtab)
    new_data_off = (nt_end + 0x1FFF) & ~0x1FFF
    new_total = new_data_off + len(data)

    out = bytearray()
    out += b'SARC' + struct.pack('<HH', 0x14, 0xFEFF)
    out += struct.pack('<III', new_total, new_data_off, third)
    out += b'SFAT' + struct.pack('<HHI', sfat_hdr, len(files), KEY)
    for name, _ in files:
        s, e = ranges[name]
        out += struct.pack('<IIII', sfat_hash(name), (stroff[name] // 4) | 0x01000000, s, e)
    out += b'SFNT' + struct.pack('<HH', 8, 0)
    out += bytes(strtab)
    out += b'\x00' * (new_data_off - len(out))
    out += bytes(data)

    dst_dir = os.path.join(OUT, tag)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, 'layout.arc')
    with open(dst, 'wb') as fh:
        fh.write(out)

    # verify by re-parsing our own output
    r = open(dst, 'rb').read()
    r_count = struct.unpack_from('<H', r, 0x1A)[0]
    r_nbase = 0x20 + r_count * 16 + 8
    hashes = {}
    for i in range(r_count):
        f0, f1, st, en = struct.unpack_from('<4I', r, 0x20 + i * 16)
        no = (f1 & 0xFFFFFF) * 4
        e = r.find(b'\x00', r_nbase + no)
        nm = r[r_nbase + no:e].decode('ascii')
        hashes[nm] = hashlib.sha256(r[new_data_off + st:new_data_off + en]).hexdigest()
    orig_hashes = {n: hashlib.sha256(b).hexdigest() for n, b in members}

    same_hashes = hashes == orig_hashes
    print(f"== {tag} member_align={member_align:#x}")
    print(f"   wrote {dst}")
    print(f"   original size {total} sha {hashlib.sha256(d).hexdigest()}")
    print(f"   repacked size {new_total} sha {hashlib.sha256(r).hexdigest()}")
    print(f"   byte equal to original: {r == d}")
    print(f"   membership equal: {sorted(hashes) == sorted(orig_hashes)} ({len(hashes)} members)")
    print(f"   member hashes equal: {same_hashes}")
    return {
        'tag': tag, 'member_align': member_align,
        'original_sha256': hashlib.sha256(d).hexdigest(),
        'repacked_sha256': hashlib.sha256(r).hexdigest(),
        'original_size': total, 'repacked_size': new_total,
        'byte_equal': r == d,
        'membership_equal': sorted(hashes) == sorted(orig_hashes),
        'member_hashes_equal': same_hashes,
        'repacked_path': dst,
    }


if __name__ == '__main__':
    res = []
    for path, tag in ((EDIT, 'make_mii_edit'), (SPEC, 'make_mii_special')):
        res.append(repack(path, tag, 4))
    with open('gamedata/mii_customizer/P1-LAYOUT/repack_4byte.json', 'w') as fh:
        json.dump(res, fh, indent=1)
    print('\nrepack_4byte.json written')