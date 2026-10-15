"""nus3audio / nus3bank / tonelabel / sqb readers and writers.

Copied unchanged from the reference repo (mods/ssbu_mod_new/tools/merge_hero_neutral_b_sound.py v1.0.0,
functions chunk .. sqb_write, and labels_read_partial from merge_pikachu_airb_sound.py) so the Cloud units do
not import from that repo. Encoded samples and tone records are copied as bytes; nothing is transcoded.
"""
import hashlib
import struct
import zlib

u32 = lambda data, offset: struct.unpack_from('<I', data, offset)[0]
pack = lambda n: struct.pack('<I', n)
sha = lambda data: hashlib.sha256(data).hexdigest()


def chunk(tag, payload):
    return tag + pack(len(payload)) + payload


def audio_read(data):
    assert data[:4] == b'NUS3' and data[8:12] == b'AUDI'
    assert u32(data, 4) + 8 == len(data)
    offset, chunks = 12, {}
    while offset < len(data):
        tag = data[offset:offset + 4]
        size = u32(data, offset + 4)
        assert tag not in chunks and offset + 8 + size <= len(data)
        chunks[tag] = data[offset + 8:offset + 8 + size]
        offset += 8 + size
    assert set(chunks) == {b'INDX', b'TNID', b'NMOF', b'ADOF', b'TNNM', b'JUNK', b'PACK'}
    count = u32(chunks[b'INDX'], 0)
    ids = list(struct.unpack('<' + 'I' * count, chunks[b'TNID']))
    assert ids == list(range(count)), 'Nonsequential donor tone ids need a separate mapping'
    result = []
    for i in range(count):
        name_offset = u32(chunks[b'NMOF'], i * 4)
        name = data[name_offset:data.index(b'\0', name_offset)].decode()
        start, size = struct.unpack_from('<II', chunks[b'ADOF'], i * 8)
        assert start + size <= len(data)
        result.append((name, data[start:start + size]))
    assert len({n for n, _ in result}) == count
    return result


def audio_write(entries):
    count = len(entries)
    prefix = chunk(b'INDX', pack(count)) + chunk(b'TNID', b''.join(pack(i) for i in range(count)))
    # Fixed-size offset chunks precede the name chunk; offsets are file-relative.
    name_start = 12 + len(prefix) + 8 + count * 4 + 8 + count * 8 + 8
    names, name_offsets = bytearray(), []
    for name, _ in entries:
        name_offsets.append(name_start + len(names))
        names += name.encode() + b'\0'
    prefix += chunk(b'NMOF', b''.join(pack(n) for n in name_offsets))
    name_chunk = chunk(b'TNNM', bytes(names))
    # PACK payload is 16-byte aligned, as in the donor files.
    before_junk = 12 + len(prefix) + 8 + count * 8 + len(name_chunk)
    padding = (-before_junk - 16) % 16
    audio_start = before_junk + 8 + padding + 8
    payload, offsets = bytearray(), []
    for _, encoded in entries:
        offsets.append((audio_start + len(payload), len(encoded)))
        payload += encoded
        payload += b'\0' * (-len(payload) % 16)
    body = prefix + chunk(b'ADOF', b''.join(struct.pack('<II', *o) for o in offsets))
    body += name_chunk + chunk(b'JUNK', b'\0' * padding) + chunk(b'PACK', bytes(payload))
    result = b'NUS3' + pack(4 + len(body)) + b'AUDI' + body
    assert audio_read(result) == entries
    return result


def bank_read(data):
    assert data[:4] == b'NUS3' and data[8:16] == b'BANKTOC '
    assert u32(data, 4) + 8 == len(data)
    count = u32(data, 20)
    assert u32(data, 16) == 4 + count * 8
    offset, result = 20 + u32(data, 16), []
    for i in range(count):
        tag = data[offset:offset + 4]
        size = u32(data, offset + 4)
        assert data[24 + i * 8:32 + i * 8] == tag + pack(size)
        result.append((tag, data[offset + 8:offset + 8 + size]))
        offset += 8 + size
    assert offset == len(data)
    return result


def bank_write(chunks):
    body = b'BANKTOC ' + pack(4 + len(chunks) * 8) + pack(len(chunks))
    body += b''.join(tag + pack(len(data)) for tag, data in chunks)
    body += b''.join(chunk(tag, data) for tag, data in chunks)
    result = b'NUS3' + pack(len(body)) + body
    assert bank_read(result) == chunks
    return result


def tones_read(payload):
    count = u32(payload, 0)
    entries = []
    for i in range(count):
        off, size = struct.unpack_from('<II', payload, 4 + i * 8)
        assert off >= 4 + count * 8 and off + size <= len(payload)
        entries.append(payload[off:off + size])
    assert 4 + count * 8 + sum(map(len, entries)) == len(payload)
    return entries


def tones_write(entries):
    offset, table = 4 + len(entries) * 8, bytearray()
    for data in entries:
        table += struct.pack('<II', offset, len(data))
        offset += len(data)
    result = pack(len(entries)) + table + b''.join(entries)
    assert tones_read(result) == entries
    return result


def group_links(tone, names):
    """Decode the measured donor type-3 rows; reject other group layouts.

    All seventeen Hero groups have 8+16*n payload bytes followed by a 20-byte
    tail. Their final row word resolves to the correspondingly named sample.
    This bounded parser preserves the opaque header, weights and tail.
    """
    name_at = 12 if u32(tone, 4) & 0x80000000 else 8
    size = tone[name_at]
    name = tone[name_at + 1:name_at + size].decode()
    assert name.lower() in {n.lower() for n in names}
    start = (name_at + 1 + size + 3) & ~3
    kind = u32(tone, start)
    if kind == 0:
        assert u32(tone, start + 4) == 8
        return []
    assert kind == 3, ('Unsupported donor tone kind', name, kind)
    count = u32(tone, start + 8)
    payload_size = u32(tone, start + 4)
    assert payload_size == 8 + 16 * count
    assert len(tone) == start + 8 + payload_size + 20
    links = []
    for row in range(count):
        at = start + 16 + 16 * row
        assert 0 <= struct.unpack_from('<f', tone, at + 4)[0] <= 1
        assert u32(tone, at + 8) in (1, 2)
        child = u32(tone, at + 12)
        assert child < len(names)
        parent = name.lower().replace('_rnd_', '_').removesuffix('_jp')
        assert names[child].lower().startswith(parent), (name, names[child])
        links.append(at + 12)
    return links


def rebase_groups(tones, names, offset):
    output, count = [], 0
    for tone in tones:
        copied = bytearray(tone)
        for at in group_links(tone, names):
            struct.pack_into('<I', copied, at, u32(tone, at) + offset)
            count += 1
        output.append(bytes(copied))
    return output, count


def labels_read(data, names):
    assert u32(data, 0) == 1 and u32(data, 4) == len(names)
    entries = list(struct.iter_unpack('<II', data[8:]))
    assert {value >> 8 for _, value in entries} == set(range(len(names)))
    for crc, value in entries:
        assert crc == zlib.crc32(names[value >> 8].lower().encode())
        assert value & 0xff == len(names[value >> 8].encode())
    return entries


def sqb_read(data):
    assert data[:4] == b'SQB\0'
    version, count = struct.unpack_from('<HH', data, 4)
    assert version == 1 and u32(data, 8) == count * 4
    base = 12 + count * 4
    offsets = list(struct.unpack_from('<' + 'I' * count, data, 12)) + [len(data) - base]
    assert offsets[0] == 0 and offsets == sorted(offsets)
    return [data[base + offsets[i]:base + offsets[i + 1]] for i in range(count)]


def sqb_write(entries):
    offsets, off = [], 0
    for entry in entries:
        offsets.append(off)
        off += len(entry)
    return b'SQB\0' + struct.pack('<HHI', 1, len(entries), 4 * len(entries)) + b''.join(map(pack, offsets)) + b''.join(entries)




def labels_read_partial(data, names):
    """labels_read, tolerating a bank whose label table does not name every tone."""
    assert u32(data, 0) == 1
    entries = list(struct.iter_unpack('<II', data[8:]))
    assert u32(data, 4) == len(entries)
    for crc, value in entries:
        assert 0 <= (value >> 8) < len(names), f'label points outside the bank: {value:#x}'
        assert crc == zlib.crc32(names[value >> 8].lower().encode())
        assert value & 0xff == len(names[value >> 8].encode())
    return entries
