"""Merge R.O.B.'s down-tilt sounds into Pyra c06/c07 (v1.0.0).

Plays the donor's own sounds for `acmd::robot_attack_lw3` instead of stand-ins (AGENTS.md rule 17):
  * `se_robot_swing_m`, `se_robot_attackhard_L01`, `se_robot_landing01` -> `se_eflame_c06/c07`
  * `vc_robot_attack01..04` (the voice takes `seq_robot_rnd_attack` chooses from) -> `vc_eflame_c06/c07`
  * the exact `seq_robot_rnd_attack` record of `robot.sqb` -> `eflame.sqb`

Only those tones are appended: sample bytes and tone records are copied unchanged, recipient
bank identity (BINF/PROP/GRP/DTON/PACK) is kept, and every donor tone is asserted to be a
single-sample tone so no group child index can dangle. The voice names are not assumed: they
are the `vc_robot_*` names whose CRC32 appear in the donor sequence record.

Chaining: each bank is read from the build output if an earlier merge already wrote it
(Hero, donor_sound, Snake all append to the same Pyra banks), else from the export. Run this
after them. Offline only (tier B); no claim that any sound plays in game.

    toolchains/py312/python.exe tools/merge_robot_dtilt_sound.py --check
    toolchains/py312/python.exe tools/merge_robot_dtilt_sound.py --output <dir under builds/ or scratch/>
"""
import argparse
import hashlib
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_hero_neutral_b_sound as codec

ROOT = codec.ROOT
REF = ROOT / 'refs/robot_attack_lw3/arc'
SQB = REF / 'sound/sequence/fighter/robot.sqb'
SQB_SHA256 = '9b26243c2b0a2d85f9b45cc2c22f195d61d35c1ee34d3fe343e9298f81ff8cd6'
SEQUENCE = 'seq_robot_rnd_attack'
SE_DONOR = REF / 'sound/bank/fighter/se_robot_c00'
VC_DONOR = REF / 'sound/bank/fighter_voice/vc_robot_c00'
SE_REQUIRED = {'se_robot_swing_m', 'se_robot_attackhard_l01', 'se_robot_landing01'}
PINS = {
    SE_DONOR: {'.nus3audio': 'bd5b1152750ed6079d1c5efbf20af231f60bc2a526d4e96909144cf3564dc2cd',
               '.nus3bank': 'c6a5a940f1a39af78378dc4053bcefe3d18d6ef560062955ea7f18dece920121',
               '.tonelabel': '9588580d0153099d60460924beea5dc840898635a586780063462f04c1958fc6'},
    VC_DONOR: {'.nus3audio': '6dc5de779cf1bc1db0702a24124fc643759b384ae1fd7fe5c71479478174626e',
               '.nus3bank': '0e159e9542ddc25ed3d0509dd5bd030d40e4dfdebf24bd42a0698773c9641a75',
               '.tonelabel': '42f135a0fb3ee59143893334dcec035a84088dc567b922822fdc89255943363f'},
}


def hash40(name):
    return len(name) << 32 | zlib.crc32(name.encode())


def check_pins():
    for stem, pins in PINS.items():
        for ext, digest in pins.items():
            assert codec.sha(stem.with_suffix(ext).read_bytes()) == digest, f'{stem}{ext} is not the pinned revision'
    assert codec.sha(SQB.read_bytes()) == SQB_SHA256, 'robot.sqb is not the pinned revision'


def sequence_record():
    records = [r for r in codec.sqb_read(SQB.read_bytes()) if int.from_bytes(r[:8], 'little') == hash40(SEQUENCE)]
    assert len(records) == 1, f'{SEQUENCE}: expected exactly one donor record, found {len(records)}'
    return records[0]


def voice_names(record, donor_names):
    """The donor `vc_robot_*` tones whose CRC32(lowercase) occurs in the record (measured, not assumed)."""
    found = [n for n in donor_names
             if n.startswith('vc_robot_') and zlib.crc32(n.lower().encode()).to_bytes(4, 'little') in record]
    assert found == [f'vc_robot_attack0{i}' for i in range(1, 5)], found
    return found


def append_tones(donor_stem, recipient, dest, wanted):
    """Append the `wanted` (lowercase) tones of `donor_stem` to `recipient`, writing `dest`."""
    donor = codec.audio_read(donor_stem.with_suffix('.nus3audio').read_bytes())
    chunks_d = dict(codec.bank_read(donor_stem.with_suffix('.nus3bank').read_bytes()))
    tones_d = codec.tones_read(chunks_d[b'TONE'])
    labels_d = codec.labels_read(donor_stem.with_suffix('.tonelabel').read_bytes(), [n for n, _ in donor])
    selected = [i for i, (n, _) in enumerate(donor) if n.lower() in wanted]
    assert len(selected) == len(wanted), f'{donor_stem.name}: {len(selected)} of {len(wanted)} tones found'
    names = [n for n, _ in donor]
    for i in selected:
        assert codec.group_links(tones_d[i], names) == [], f'{names[i]} is a group tone'

    original = codec.audio_read(recipient.with_suffix('.nus3audio').read_bytes())
    chunks_r = codec.bank_read(recipient.with_suffix('.nus3bank').read_bytes())
    for tag in (b'GRP ', b'DTON', b'PACK'):
        assert dict(chunks_r)[tag] == chunks_d[tag], f'{recipient.name}: {tag!r} differs from the donor bank'
    tones_r = codec.tones_read(dict(chunks_r)[b'TONE'])
    entries = original + [donor[i] for i in selected]
    assert len({n.lower() for n, _ in entries}) == len(entries), f'{recipient.name}: tone name collision'

    mapping = {i: len(original) + j for j, i in enumerate(selected)}
    labels = codec.labels_read(recipient.with_suffix('.tonelabel').read_bytes(), [n for n, _ in original])
    labels += [(crc, mapping[value >> 8] << 8 | (value & 255)) for crc, value in labels_d if value >> 8 in mapping]
    labels.sort()
    label_bytes = codec.pack(1) + codec.pack(len(labels)) + b''.join(struct.pack('<II', *p) for p in labels)
    codec.labels_read(label_bytes, [n for n, _ in entries])
    merged_tones = tones_r + [tones_d[i] for i in selected]
    files = {'.nus3audio': codec.audio_write(entries), '.tonelabel': label_bytes,
             '.nus3bank': codec.bank_write([(tag, codec.tones_write(merged_tones) if tag == b'TONE' else data)
                                            for tag, data in chunks_r])}
    for ext, content in files.items():
        path = dest.with_suffix(ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    # Verify against the written bytes.
    assert codec.audio_read(files['.nus3audio']) == entries
    assert codec.tones_read(dict(codec.bank_read(files['.nus3bank']))[b'TONE']) == merged_tones
    resolved = {zlib.crc32(n.lower().encode()) for n in wanted}
    assert resolved <= {crc for crc, _ in codec.labels_read(files['.tonelabel'], [n for n, _ in entries])}
    return {'recipient': recipient.name, 'retained_tones': len(original),
            'appended_names': sorted(donor[i][0] for i in selected),
            'output_hashes': {ext: codec.sha(c) for ext, c in files.items()}}


def build(output, check_only=False):
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / name) for name in ('scratch', 'builds')), 'output must be in builds/ or scratch/'
    check_pins()
    record_bytes = sequence_record()
    donor_voice = [n for n, _ in codec.audio_read(VC_DONOR.with_suffix('.nus3audio').read_bytes())]
    vc_wanted = set(voice_names(record_bytes, donor_voice))
    banks = []
    for slot in ('c06', 'c07'):
        for folder, prefix, donor, wanted in (('fighter', 'se_eflame', SE_DONOR, SE_REQUIRED),
                                              ('fighter_voice', 'vc_eflame', VC_DONOR, vc_wanted)):
            dest = output / f'sound/bank/{folder}/{prefix}_{slot}'
            base = dest if dest.with_suffix('.nus3audio').is_file() else codec.ARC / f'sound/bank/{folder}/{prefix}_{slot}'
            rep = append_tones(donor, base, dest, wanted)
            rep.update(folder=folder, slot=slot, recipient_was_chained=base == dest)
            banks.append(rep)

    sqb_dest = output / 'sound/sequence/fighter/eflame.sqb'
    sqb_base = sqb_dest if sqb_dest.is_file() else codec.ARC / 'sound/sequence/fighter/eflame.sqb'
    recipient_bytes = sqb_base.read_bytes()
    recipient = codec.sqb_read(recipient_bytes)
    assert not any(r[:8] == record_bytes[:8] for r in recipient), f'{SEQUENCE} already present in eflame.sqb'
    merged = codec.sqb_write(recipient + [record_bytes])
    assert codec.sqb_read(merged) == recipient + [record_bytes]
    sqb_dest.parent.mkdir(parents=True, exist_ok=True)
    sqb_dest.write_bytes(merged)

    report = {'tool_version': '1.0.0', 'date': '2026-09-30', 'evidence_tier': 'B', 'hardware_validated': False,
              'banks': banks, 'sequence': SEQUENCE, 'sequence_key': hex(hash40(SEQUENCE)),
              'sequence_voice_tones': sorted(vc_wanted), 'sqb_sha256': codec.sha(merged),
              'recipient_sqb_sha256': codec.sha(recipient_bytes), 'donor_sqb_sha256': SQB_SHA256,
              'note': 'No offline check establishes that a sound plays in game.'}
    (output / 'robot_dtilt_sound.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {len(banks)} banks + eflame.sqb; se {sorted(SE_REQUIRED)}; voice {sorted(vc_wanted)}')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        build(args.output)
    elif args.check:
        parent = ROOT / 'scratch' / '2026-09-30_claude_robot_dtilt'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            build(tmp, True)
    else:
        parser.error('choose --check or --output')


if __name__ == '__main__':
    main()
