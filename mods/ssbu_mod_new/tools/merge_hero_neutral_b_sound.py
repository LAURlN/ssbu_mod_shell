"""Merge original Hero sound resources into Mythra c06/c07 (v1.0.0).

Keeps recipient bank identity/groups; copies complete donor tone records and
encoded audio without conversion. Rebuilds offset tables, rebases tone ids in
tonelabels, and appends intact Hero SQB records. Requires identical donor and
recipient GRP/DTON/PACK sections; incompatible banks fail rather than guess.
Output is restricted to scratch/ or builds/. --check performs parser round
trips and verifies matching audio/tone names and label index interpretation.
No offline check establishes in-game sound playback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tomllib
import zlib

ROOT = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((ROOT / 'paths.toml').read_text())
ARC = ROOT / CFG['dumps']['arc']
SQB = ROOT / 'refs/brave_special_n/sound/arc/sound/sequence/fighter/brave.sqb'
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


def merge_bank(donor, recipient, output):
    da = audio_read(donor.with_suffix('.nus3audio').read_bytes())
    ra = audio_read(recipient.with_suffix('.nus3audio').read_bytes())
    assert not ({n for n, _ in da} & {n for n, _ in ra})
    dc = bank_read(donor.with_suffix('.nus3bank').read_bytes())
    rc = bank_read(recipient.with_suffix('.nus3bank').read_bytes())
    dd, rd = dict(dc), dict(rc)
    for tag in (b'GRP ', b'DTON', b'PACK'):
        assert dd[tag] == rd[tag], ('Incompatible shared sound data', tag)
    dt, rt = tones_read(dd[b'TONE']), tones_read(rd[b'TONE'])
    assert len(dt) == len(da) and len(rt) == len(ra)
    dl = labels_read(donor.with_suffix('.tonelabel').read_bytes(), [n for n, _ in da])
    rl = labels_read(recipient.with_suffix('.tonelabel').read_bytes(), [n for n, _ in ra])
    entries = ra + da
    count = len(ra)
    appended, rebased_links = rebase_groups(dt, [n for n, _ in da], count)
    # Relocation must preserve the actual child name, not merely stay in range.
    for before, after in zip(dt, appended):
        for at in group_links(before, [n for n, _ in da]):
            assert entries[u32(after, at)][0] == da[u32(before, at)][0]
    new_labels = rl + [(crc, ((value >> 8) + count) << 8 | (value & 0xff)) for crc, value in dl]
    new_labels.sort()
    label_bytes = pack(1) + pack(len(new_labels)) + b''.join(struct.pack('<II', *p) for p in new_labels)
    labels_read(label_bytes, [n for n, _ in entries])
    files = {'.nus3audio': audio_write(entries),
             '.nus3bank': bank_write([(tag, tones_write(rt + appended) if tag == b'TONE' else data) for tag, data in rc]),
             '.tonelabel': label_bytes}
    for ext, data in files.items():
        path = output.with_suffix(ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return {'donor': donor.relative_to(ROOT).as_posix(), 'recipient': recipient.relative_to(ROOT).as_posix(),
            'retained_tones': len(ra), 'appended_tones': len(da), 'rebased_group_links': rebased_links,
            'input_hashes': {side + ext: sha(path.with_suffix(ext).read_bytes())
                            for side, path in [('donor', donor), ('recipient', recipient)]
                            for ext in ('.nus3audio', '.nus3bank', '.tonelabel')},
            'hash_lengths_preserved': True, 'file_hashes': {ext: sha(data) for ext, data in files.items()}}


def check():
    for folder, stem in [('fighter', 'se_brave_c00'), ('fighter', 'se_elight_c06'),
                         ('fighter_voice', 'vc_brave_c00'), ('fighter_voice', 'vc_elight_c06')]:
        path = ARC / 'sound/bank' / folder / stem
        audio = audio_read(path.with_suffix('.nus3audio').read_bytes())
        assert audio_read(audio_write(audio)) == audio
        labels_read(path.with_suffix('.tonelabel').read_bytes(), [n for n, _ in audio])
        bank = path.with_suffix('.nus3bank').read_bytes()
        assert bank_write(bank_read(bank)) == bank
        payload = dict(bank_read(bank))[b'TONE']
        assert tones_write(tones_read(payload)) == payload
        if 'brave' in stem:
            tones = tones_read(payload)
            rebased, _ = rebase_groups(tones, [n for n, _ in audio], 1000)
            for original, updated in zip(tones, rebased):
                restored = bytearray(updated)
                for at in group_links(original, [n for n, _ in audio]):
                    struct.pack_into('<I', restored, at, u32(updated, at) - 1000)
                assert bytes(restored) == original
    for path in (SQB, ARC / 'sound/sequence/fighter/elight.sqb'):
        data = path.read_bytes()
        assert sqb_write(sqb_read(data)) == data
    print('PASS: audio samples, bank chunks, tone records, labels and SQB round trips')


def build(output):
    check()
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / n) for n in ('builds', 'scratch'))
    reports = []
    for slot in ('c06', 'c07'):
        for folder, prefix in [('fighter', 'se'), ('fighter_voice', 'vc')]:
            directory = ARC / 'sound/bank' / folder
            reports.append(merge_bank(directory / f'{prefix}_brave_c00', directory / f'{prefix}_elight_{slot}',
                                      output / 'sound/bank' / folder / f'{prefix}_elight_{slot}'))
    recipient = sqb_read((ARC / 'sound/sequence/fighter/elight.sqb').read_bytes())
    donor = sqb_read(SQB.read_bytes())
    assert not ({e[:8] for e in recipient} & {e[:8] for e in donor})
    merged = sqb_write(recipient + donor)
    assert sqb_read(merged) == recipient + donor
    sequence = output / 'sound/sequence/fighter/elight.sqb'
    sequence.parent.mkdir(parents=True, exist_ok=True)
    sequence.write_bytes(merged)
    report = {'date': '2026-09-30', 'tool_version': '1.0.0', 'evidence_tier': 'B',
              'banks': reports, 'sqb_sha256': sha(merged), 'donor_sqb_sha256': sha(SQB.read_bytes()),
              'retained_sequences': len(recipient), 'appended_sequences': len(donor), 'hardware_validated': False}
    (output / 'hero_neutral_b_sound.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Merged original Hero sound banks for c06/c07 and preserved both sequence tables')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.check:
        check()
    elif args.output:
        build(args.output)
    else:
        parser.error('choose --check or --output')


if __name__ == '__main__':
    main()
