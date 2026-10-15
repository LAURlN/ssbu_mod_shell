"""Merge pinned Snake sound tones into Pyra c06/c07 (v1.1.0).

--check smoke-tests serialized banks and exact sample preservation in scratch.
The fighter sequence table is required for a shippable build; a missing table
is never approximated. Output belongs in builds/ or scratch/. Offline only.
"""
import argparse
import json
import sys
import struct
import zlib
import tempfile
import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_hero_neutral_b_sound as codec

ROOT = codec.ROOT
DONOR = ROOT / 'refs/snake_grenade/arc/sound/bank/fighter/se_snake_c00'
SQB = ROOT / 'refs/snake_grenade/sequence/arc/sound/sequence/fighter/snake.sqb'
REQUIRED = {f'se_snake_special_n0{i}' for i in range(1, 5)} | {
    'se_snake_step_left_m', 'se_snake_step_right_m', 'se_snake_dash_stop',
    'se_snake_jump01', 'se_snake_landing02'}

def banks(output):
    reports = []
    donor = codec.audio_read(DONOR.with_suffix('.nus3audio').read_bytes())
    donor_chunks = dict(codec.bank_read(DONOR.with_suffix('.nus3bank').read_bytes()))
    donor_tones = codec.tones_read(donor_chunks[b'TONE'])
    donor_labels = codec.labels_read(DONOR.with_suffix('.tonelabel').read_bytes(), [n for n, _ in donor])
    required = REQUIRED
    selected = [i for i, (name, _) in enumerate(donor) if name.lower() in required]
    assert len(selected) == len(required)
    # These nine simple tones cover neutral-B and its hold movement. Do not transplant
    # unrelated Snake random groups using Hero's name-layout assumptions.
    for i in selected:
        assert codec.group_links(donor_tones[i], [n for n, _ in donor]) == []
    for slot in ('c06', 'c07'):
        dest = output / f'sound/bank/fighter/se_eflame_{slot}'
        # Append after the other move donors; never replace their assembled bank.
        recipient = dest if dest.with_suffix('.nus3audio').is_file() else codec.ARC / f'sound/bank/fighter/se_eflame_{slot}'
        input_hashes = {side + ext: codec.sha(path.with_suffix(ext).read_bytes())
                       for side, path in [('donor', DONOR), ('recipient', recipient)]
                       for ext in ('.nus3audio', '.nus3bank', '.tonelabel')}
        original = codec.audio_read(recipient.with_suffix('.nus3audio').read_bytes())
        chunks = codec.bank_read(recipient.with_suffix('.nus3bank').read_bytes())
        for tag in (b'GRP ', b'DTON', b'PACK'):
            assert dict(chunks)[tag] == donor_chunks[tag]
        tones = codec.tones_read(dict(chunks)[b'TONE'])
        entries = original + [donor[i] for i in selected]
        assert len({n for n, _ in entries}) == len(entries)
        mapping = {i: len(original) + j for j, i in enumerate(selected)}
        labels = codec.labels_read(recipient.with_suffix('.tonelabel').read_bytes(), [n for n, _ in original])
        labels += [(crc, mapping[value >> 8] << 8 | (value & 255))
                   for crc, value in donor_labels if value >> 8 in mapping]
        labels.sort()
        label_bytes = codec.pack(1) + codec.pack(len(labels)) + b''.join(struct.pack('<II', *pair) for pair in labels)
        codec.labels_read(label_bytes, [n for n, _ in entries])
        files = {'.nus3audio': codec.audio_write(entries), '.tonelabel': label_bytes,
            '.nus3bank': codec.bank_write([(tag, codec.tones_write(tones + [donor_tones[i] for i in selected])
                          if tag == b'TONE' else data) for tag, data in chunks])}
        for extension, content in files.items():
            path = dest.with_suffix(extension)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        assert codec.audio_read(files['.nus3audio']) == entries
        assert codec.tones_read(dict(codec.bank_read(files['.nus3bank']))[b'TONE']) == tones + [donor_tones[i] for i in selected]
        reports.append({'slot': slot, 'retained_tones': len(original), 'appended_names': sorted(required),
            'sample_bytes_verified': True, 'tone_records_verified': True,
            'input_hashes': input_hashes,
            'output_hashes': {ext: codec.sha(data) for ext, data in files.items()}})
    return reports

def build(output, check_only=False):
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / name) for name in ('scratch', 'builds'))
    if not check_only:
        assert SQB.is_file(), 'Dump required: sound/sequence/fighter/snake.sqb (dumps/MISSING.md)'
    reports = banks(output)
    record = {'tool_version': '1.1.0', 'date': '2026-09-30', 'evidence_tier': 'B',
        'hardware_validated': False, 'banks': reports, 'sequence_table_present': SQB.is_file()}
    if not check_only:
        existing = output / 'sound/sequence/fighter/eflame.sqb'
        recipient_path = existing if existing.is_file() else codec.ARC / 'sound/sequence/fighter/eflame.sqb'
        recipient_bytes = recipient_path.read_bytes()
        recipient = codec.sqb_read(recipient_bytes)
        source = codec.sqb_read(SQB.read_bytes())
        hashes = {len(name) << 32 | zlib.crc32(name.encode())
                  for name in REQUIRED}
        # Plain PLAY_SE keys may have no sequence records. Measure the donor
        # table rather than fabricating one or transplanting unrelated voices.
        donor = [entry for entry in source if int.from_bytes(entry[:8], 'little') in hashes]
        assert not ({entry[:8] for entry in recipient} & {entry[:8] for entry in donor})
        merged = codec.sqb_write(recipient + donor)
        assert codec.sqb_read(merged) == recipient + donor
        path = output / 'sound/sequence/fighter/eflame.sqb'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(merged)
        record['sqb_sha256'] = codec.sha(merged)
        record['recipient_sqb_sha256'] = codec.sha(recipient_bytes)
        record['donor_sqb_sha256'] = codec.sha(SQB.read_bytes())
        record['donor_sequence_count'] = len(source)
        record['appended_sequence_keys'] = [hex(int.from_bytes(entry[:8], 'little')) for entry in donor]
    (output / 'snake_neutral_b_sound.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PASS: both Pyra banks retain samples and append exact Snake tones; sequence present=' + str(SQB.is_file()))
    return record

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.check and not args.output:
        parser.error('choose --check or --output')
    if args.check and not args.output:
        parent = ROOT / 'scratch' / (str(datetime.date.today()) + '_codex_snake')
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            build(tmp, True)
    else:
        build(args.output, args.check)

if __name__ == '__main__':
    main()
