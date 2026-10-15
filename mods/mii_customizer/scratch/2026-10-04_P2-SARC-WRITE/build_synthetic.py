"""Build a synthetic SARC, plus deliberately damaged variants, for sarc-layout tests.

Written independently of tools/sarc-layout/sarc_layout.py on purpose: if the
tool and its test data were produced by the same code, an encoder bug would
hide itself. Nothing here is a game file and nothing here touches the real
archives.
"""

import os
import struct
import sys

OUT = 'gamedata/mii_customizer/P2-SARC-WRITE/synthetic'

KEY = 0x65


def sarc_hash(name):
    h = 0
    for ch in name:
        h = (h * KEY + ord(ch)) & 0xFFFFFFFF
    return h


def build(entries, data_offset=0x200, field_0x10=0x123):
    """entries: list of (name, payload). Members are placed in the given order
    with deliberate gaps, and the table is sorted by name hash like the real
    archives.

    The layout mirrors the two real archives exactly:
      0x00 SARC, 0x04 u16 0x14, 0x06 BOM ff fe, 0x08 size, 0x0C data_offset,
      0x10 field, 0x14 SFAT, 0x18 sfat_header_size, 0x1A count, 0x1C key,
      0x20 entries, then SFNT and the name table.
    """
    assert data_offset >= 0x20 + len(entries) * 0x10 + 8
    out_name = []
    stroff = {}
    for name, _ in entries:
        stroff[name] = len(out_name)
        out_name += name.encode('ascii') + b'\x00'
        while len(out_name) % 4:
            out_name += b'\x00'

    ordered = sorted(entries, key=lambda kv: sarc_hash(kv[0]))

    # gap pattern: 16 before the first member, then 4, 12, 8 ... so the test
    # data contains non-uniform inter-member padding.
    data = bytearray()
    ranges = {}
    gaps = [0x10]
    for i, (name, blob) in enumerate(ordered):
        pad = gaps[i % len(gaps)]
        data += bytes([0xA5]) * pad          # non-zero filler, so gaps are visible
        start = len(data)
        data += blob
        ranges[name] = (start, start + len(blob))

    count = len(ordered)
    head = bytearray()
    head += b'SARC'
    head += struct.pack('<HH', 0x14, 0xFEFF)
    head += struct.pack('<I', 0)            # size_field, patched below
    head += struct.pack('<I', data_offset)
    head += struct.pack('<I', field_0x10)
    head += b'SFAT'
    head += struct.pack('<HHI', 0x0C, count, KEY)
    for name, _ in ordered:
        s, e = ranges[name]
        head += struct.pack('<IIII', sarc_hash(name), (stroff[name] // 4) | 0x01000000, s, e)
    head += b'SFNT'
    head += struct.pack('<I', 8)
    head += bytes(out_name)

    assert len(head) <= data_offset, 'synthetic head %d exceeds data_offset %d' % (len(head), data_offset)
    total = data_offset + len(data)
    struct.pack_into('<I', head, 8, total)
    return bytes(head) + bytes(data_offset - len(head)) + bytes(data), ordered


def main():
    os.makedirs(OUT, exist_ok=True)
    entries = [
        ('alpha.bin', b'AAAA' * 16),
        ('dir/beta.bin', bytes(range(256)) * 2),
        ('dir/gamma.bin', b'FLYT' + b'\x00' * 60),
        ('zeta.bin', b'z'),
        ('nested/deep/delta.bin', b'D' * 1000),
    ]
    raw, ordered = build(entries)
    with open(os.path.join(OUT, 'synthetic.arc'), 'wb') as fh:
        fh.write(raw)
    print('synthetic.arc %d bytes, %d members, order: %s'
          % (len(raw), len(ordered), [n for n, _ in ordered]))

    # Damaged variants, each supposed to be refused by the tool.
    variants = {}

    # 1. duplicate member names: entry 1 is pointed at entry 0's name offset
    dup = bytearray(raw)
    count = struct.unpack_from('<H', dup, 0x1A)[0]
    f0_0, f1_0, _s0, _e0 = struct.unpack_from('<IIII', dup, 0x20)
    struct.pack_into('<I', dup, 0x20 + 0x10 + 4, f1_0)
    variants['duplicate_names.arc'] = bytes(dup)

    # 2. out-of-bounds member range: last entry ends past the data section
    oob = bytearray(raw)
    struct.pack_into('<I', oob, 0x20 + (count - 1) * 0x10 + 12, len(raw) + 0x1000)
    variants['out_of_bounds.arc'] = bytes(oob)

    # 3. overlapping member ranges: entry 1 starts before entry 0 ends
    ov = bytearray(raw)
    _f0, _f1, s0, e0 = struct.unpack_from('<IIII', ov, 0x20)
    struct.pack_into('<I', ov, 0x20 + 0x10 + 8, s0 + 4)
    struct.pack_into('<I', ov, 0x20 + 0x10 + 12, e0 + 4)
    variants['overlap.arc'] = bytes(ov)

    # 4. traversal name in the name table. The zeta.bin slot holds 9 bytes of text
    # padded to 12, so an 11-character escaping name plus its NUL fits exactly
    # and every other name offset and the file length stay valid. The refusal
    # must be about the '..' component, not an incidental size mismatch.
    esc = bytearray(raw)
    _f0, f1z, _sz, _ez = struct.unpack_from('<IIII', esc, 0x20 + 0x10)
    zoff = (f1z & 0xFFFFFF) * 4
    base = 0x20 + count * 0x10 + 8
    old_nul = esc.find(b'\x00', base + zoff)
    old_slot = ((old_nul - (base + zoff)) + 1 + 3) & ~3
    new_name = ('../' * 3).encode() + b'ab\x00'   # 11 chars + NUL = 12 bytes
    assert len(new_name) == old_slot, (len(new_name), old_slot)
    esc[base + zoff:base + zoff + old_slot] = new_name
    assert len(esc) == len(raw), (len(esc), len(raw))
    variants['traversal_name.arc'] = bytes(esc)

    # 5. compressed container: Yaz0 header in front
    variants['compressed_yaz0.arc'] = b'Yaz0' + raw[4:]

    # 6. big-endian BOM: this format stores the bytes ff fe to mean "little". A
    # genuinely big-endian archive stores fe ff, so that is what goes here.
    be = bytearray(raw)
    struct.pack_into('>H', be, 0x06, 0xFEFF)
    assert be[6:8] == b'\xfe\xff', be[6:8]
    variants['big_endian.arc'] = bytes(be)

    # 7. truncated file: header size field disagrees with the real length
    tr = bytearray(raw)
    struct.pack_into('<I', tr, 8, len(raw) + 16)
    variants['truncated.arc'] = bytes(tr)

    # 8. damaged name hash on one entry
    bh = bytearray(raw)
    struct.pack_into('<I', bh, 0x20 + 0x10, 0xDEADBEEF)
    variants['bad_name_hash.arc'] = bytes(bh)

    for name, blob in variants.items():
        with open(os.path.join(OUT, name), 'wb') as fh:
            fh.write(blob)
        print('%-24s %d bytes' % (name, len(blob)))

    # Replacement payloads: one exactly the length of dir/beta.bin (512),
    # one one byte longer, one one byte shorter.
    beta_len = len(dict(entries)['dir/beta.bin'])
    same = (b'BETA-REPLACED-' * 64)[:beta_len]
    assert len(same) == beta_len
    with open(os.path.join(OUT, 'payload_same.bin'), 'wb') as fh:
        fh.write(same)
    with open(os.path.join(OUT, 'payload_grow.bin'), 'wb') as fh:
        fh.write(b'\x00' * (beta_len + 1))
    with open(os.path.join(OUT, 'payload_shrink.bin'), 'wb') as fh:
        fh.write(b'\x00' * (beta_len - 1))
    print('payloads written; dir/beta.bin is %d bytes' % beta_len)
    return 0


if __name__ == '__main__':
    sys.exit(main())