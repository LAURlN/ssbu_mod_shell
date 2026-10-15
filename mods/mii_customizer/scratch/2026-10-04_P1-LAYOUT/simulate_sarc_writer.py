"""Simulate the jam1garner/sarc crate writer's exact byte layout on the two
game archives, to test whether that crate can reproduce them byte-for-byte.

Reproduces, per src/writer.rs:
  header  : "SARC" | u16 0x14 | u16 0xFEFF(LE-written) | u32 file_size
            | u32 data_offset | u16 0x0100 | 2 pad bytes
  SFAT    : "SFAT" | u16 0x0C | u16 count | u32 0x65 | count * 16 bytes
            entries sorted by sfat_hash, each (hash, (off/4)|0x01000000, start, end)
  SFNT    : "SFNT" | u16 0x08 | u16 0 | names cstr padded to 4 bytes, sorted by hash
  data    : each member start aligned up to 0x2000
This is a measurement only; it writes nothing.
"""
import hashlib
import json
import struct

KEY = 0x65


def sfat_hash(s):
    h = 0
    for ch in s:
        h = (h * KEY + ord(ch)) & 0xFFFFFFFF
    return h


def simulate(path, member_align):
    d = open(path, 'rb').read()
    total, data_off, _third = struct.unpack_from('<III', d, 8)
    count = struct.unpack_from('<H', d, 0x1A)[0]
    nt_off = 0x20 + count * 16
    nbase = nt_off + 8
    members = []
    for i in range(count):
        f0, f1, st, en = struct.unpack_from('<4I', d, 0x20 + i * 16)
        no = (f1 & 0xFFFFFF) * 4
        end = d.find(b'\x00', nbase + no)
        name = d[nbase + no:end].decode('ascii')
        members.append((name, d[data_off + st:data_off + en]))

    files = sorted(members, key=lambda kv: sfat_hash(kv[0]))

    strtab = bytearray()
    stroff = {}
    for name, _ in files:
        stroff[name] = len(strtab)
        strtab += name.encode() + b'\x00'
        while len(strtab) % 4:
            strtab += b'\x00'

    data = bytearray()
    ranges = {}
    for name, blob in files:
        start = (len(data) + member_align - 1) & ~(member_align - 1)
        data += b'\x00' * (start - len(data))
        data += blob
        ranges[name] = (start, len(data))

    nt_len = len(strtab)
    pad_to = 0x14 + 0x0C + len(files) * 0x10 + 8 + nt_len
    new_data_off = (pad_to + 0x1FFF) & ~0x1FFF
    new_total = new_data_off + len(data)

    out = bytearray()
    out += b'SARC'
    out += struct.pack('<H', 0x14)
    out += struct.pack('<H', 0xFEFF)
    out += struct.pack('<I', new_total)
    out += struct.pack('<I', new_data_off)
    out += struct.pack('<H', 0x0100)
    out += b'\x00\x00'
    out += b'SFAT'
    out += struct.pack('<HHI', 0x0C, len(files), KEY)
    for name, _ in files:
        s, e = ranges[name]
        out += struct.pack('<IIII', sfat_hash(name), (stroff[name] // 4) | 0x01000000, s, e)
    out += b'SFNT'
    out += struct.pack('<HH', 8, 0)
    out += bytes(strtab)
    out += b'\x00' * (new_data_off - len(out))
    out += bytes(data)

    print(f"== {path.split('/')[-3]} member_align={member_align:#x}")
    print(f"   original : size {total:>8} data_offset {data_off:#x} sha {hashlib.sha256(d).hexdigest()}")
    print(f"   simulated: size {new_total:>8} data_offset {new_data_off:#x} sha {hashlib.sha256(bytes(out)).hexdigest()}")
    print(f"   byte equal: {bytes(out) == d}")
    # do the individual member payloads survive?
    ok = True
    for name, blob in members:
        s, e = ranges[name]
        if bytes(data[s:e]) != blob:
            ok = False
            print(f"   member payload changed: {name}")
    print(f"   all member payloads preserved: {ok}")
    print(f"   membership preserved: {sorted(m[0] for m in members) == sorted(ranges)}")
    return {
        'path': path,
        'member_align': member_align,
        'original_sha256': hashlib.sha256(d).hexdigest(),
        'simulated_sha256': hashlib.sha256(bytes(out)).hexdigest(),
        'byte_equal': bytes(out) == d,
        'original_size': total,
        'simulated_size': new_total,
        'members_preserved': ok,
        'membership_preserved': sorted(m[0] for m in members) == sorted(ranges),
    }


if __name__ == '__main__':
    paths = (
        'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc',
        'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc')
    res = [simulate(p, a) for a in (0x2000, 4) for p in paths]
    with open('gamedata/mii_customizer/P1-LAYOUT/sarc_writer_simulation.json', 'w') as fh:
        json.dump(res, fh, indent=1)
    print('\nsimulation json written')