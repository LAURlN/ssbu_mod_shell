"""Merge Snake's up-tilt sounds into Pyra c06/c07 (v1.0.0).

Plays the donor's own sounds for `acmd::snake_attack_hi3` instead of stand-ins
(AGENTS.md rule 17):

  * `se_snake_attackhard_h01`   -> `se_eflame_c06` / `c07` (his own hard-attack tone)
  * `vc_snake_attack01..04`     -> `vc_eflame_c06` / `c07` (the voice takes
    `seq_snake_rnd_attack` chooses from; the four names are *measured* out of the
    donor sequence record by CRC32, not assumed)
  * the exact `seq_snake_rnd_attack` record of `snake.sqb` -> `eflame.sqb`

Only those tones are appended: sample bytes and tone records are copied
unchanged, recipient bank identity (BINF/PROP/GRP/DTON/PACK) is kept, and every
appended tone is asserted to be a single-sample tone so no group child index can
dangle. The voice names are measured, not listed by hand.

Chaining: each bank is read from the build output if an earlier merge already
wrote it (`merge_hero_neutral_b_sound`, `merge_donor_sound`,
`merge_snake_neutral_b_sound`, `merge_robot_dtilt_sound` all append to the same
Pyra banks), else from the export. Run this after them. The sequence append is
**idempotent**: if `seq_snake_rnd_attack` is already in `eflame.sqb` the record is
compared byte for byte against the donor and left alone rather than duplicated.

Preservation is a *checked* property, not a claim: `build()` compares the tone
names, the sample bytes and the tone labels of every bank before and after, and
raises if any pre-existing tone is lost, reordered or renamed. The report
records the counts.

Offline only (tier B). No offline check establishes that a sound plays in game.

    python tools/merge_snake_uptilt_sound.py --check
    python tools/merge_snake_uptilt_sound.py --output <dir under builds/ or scratch/>
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
SEQ_REF = ROOT / 'refs/snake_attack_hi3'
# The tone and the sequence table were already pinned for Snake neutral-B
# (refs/snake_grenade); the voice bank was pinned for this move. Rule 29: not
# re-copied.
SE_DONOR = ROOT / 'refs/snake_grenade/arc/sound/bank/fighter/se_snake_c00'
VC_DONOR = SEQ_REF / 'arc/sound/bank/fighter_voice/vc_snake_c00'
SQB = ROOT / 'refs/snake_grenade/sequence/arc/sound/sequence/fighter/snake.sqb'
PINS = {
    SE_DONOR: {'.nus3audio': '88057e12e9aa1dcadad8c604e1bf148a9b49e93b898a7ce8b7f67ec19479a495',
               '.nus3bank': '4e09776aad72a942e317be17b809e4dc8b8fa55c6f5538ba1510a1bfd4f28fa0',
               '.tonelabel': '8692a0a7eec86fb7159fbb96884f9424c44e57458388e37cb278f518d47a67c1'},
    VC_DONOR: {'.nus3audio': '12d080d0588400d8aa8ac228eb1cf2fbaf3c9f03608b1e42b5a7515e950e6c13',
               '.nus3bank': 'b8a677da89ebb3fafd3eb718a2f3db2a404cc9f40f58c3a4f88adb0117d3a0a8',
               '.tonelabel': 'd8280363e3c76aef19aa7436f3c0f094555a2aa0f7fb638b77414cf1e423f8a1'},
}
SQB_SHA256 = '90370dcfeaed1e27498c1eaf4dc6e2a64d03d79e6a2df8ac1daa7f45df44ce0b'
SEQUENCE = 'seq_snake_rnd_attack'
SE_REQUIRED = {'se_snake_attackhard_h01'}
BASELINE = ROOT / 'builds/pgwr/0.20.17/ultimate/mods/pyra_gamewatch_reskin'


def hash40(name):
    return len(name) << 32 | zlib.crc32(name.encode())


def check_pins():
    for stem, pins in PINS.items():
        for ext, digest in pins.items():
            assert codec.sha(stem.with_suffix(ext).read_bytes()) == digest, \
                f'{stem}{ext} is not the pinned revision'
    assert codec.sha(SQB.read_bytes()) == SQB_SHA256, 'snake.sqb is not the pinned revision'


def sequence_record():
    records = [r for r in codec.sqb_read(SQB.read_bytes())
               if int.from_bytes(r[:8], 'little') == hash40(SEQUENCE)]
    assert len(records) == 1, f'{SEQUENCE}: expected exactly one donor record, found {len(records)}'
    return records[0]


def voice_names(record, donor_names):
    """The donor `vc_snake_*` tones whose CRC32(lowercase) occurs in the record.

    Measured, not listed: the same method `merge_robot_dtilt_sound.py` uses, so
    the voice set follows the record rather than a hand-typed expectation.
    """
    return sorted(n for n in donor_names
                  if n.startswith('vc_snake_')
                  and zlib.crc32(n.lower().encode()).to_bytes(4, 'little') in record)


def labels_read_partial(data, names):
    """`codec.labels_read` but tolerating a donor whose label table is incomplete.

    Measured 2026-10-02 on the pinned `vc_snake_c00.tonelabel`: the table has
    **34 entries for 48 audio files**, so it does not name every tone it ships.
    `labels_read` asserts full coverage, which is right for a recipient bank and
    wrong for this donor. Every entry that *is* present is still checked against
    its name and length, so a malformed record still fails here.
    """
    assert codec.u32(data, 0) == 1
    entries = list(struct.iter_unpack('<II', data[8:]))
    assert codec.u32(data, 4) == len(entries)
    for crc, value in entries:
        assert 0 <= (value >> 8) < len(names), f'label points outside the bank: {value:#x}'
        assert crc == zlib.crc32(names[value >> 8].lower().encode())
        assert value & 0xff == len(names[value >> 8].encode())
    return entries


def _read_bank(stem):
    entries = codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())
    chunks = codec.bank_read(stem.with_suffix('.nus3bank').read_bytes())
    labels = codec.labels_read(stem.with_suffix('.tonelabel').read_bytes(), [n for n, _ in entries])
    return entries, chunks, labels


def _read_donor_bank(stem):
    entries = codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())
    chunks = codec.bank_read(stem.with_suffix('.nus3bank').read_bytes())
    labels = labels_read_partial(stem.with_suffix('.tonelabel').read_bytes(), [n for n, _ in entries])
    return entries, chunks, labels


def append_tones(donor_stem, recipient, dest, wanted):
    """Append the `wanted` (lowercase) tones of `donor_stem` to `recipient`, writing `dest`."""
    donor, chunks_d, labels_d = _read_donor_bank(donor_stem)
    names = [n for n, _ in donor]
    tones_d = codec.tones_read(dict(chunks_d)[b'TONE'])
    selected = [i for i, n in enumerate(names) if n.lower() in wanted]
    assert len(selected) == len(wanted), f'{donor_stem.name}: {len(selected)} of {len(wanted)} tones found'
    for i in selected:
        assert codec.group_links(tones_d[i], names) == [], f'{names[i]} is a group tone'

    original, chunks_r, labels_r = _read_bank(recipient)
    donor_chunks, recipient_chunks = dict(chunks_d), dict(chunks_r)
    for tag in (b'GRP ', b'DTON', b'PACK'):
        assert recipient_chunks[tag] == donor_chunks[tag], \
            f'{recipient.name}: {tag!r} differs from the donor bank'
    tones_r = codec.tones_read(recipient_chunks[b'TONE'])
    entries = original + [donor[i] for i in selected]
    assert len({n.lower() for n, _ in entries}) == len(entries), f'{recipient.name}: tone name collision'
    assert all(a.lower() not in wanted for a, _ in original), \
        f'{recipient.name}: one of the requested tones is already present'

    mapping = {i: len(original) + j for j, i in enumerate(selected)}
    labels = list(labels_r) + [(crc, mapping[value >> 8] << 8 | (value & 255))
                               for crc, value in labels_d if value >> 8 in mapping]
    labels.sort()
    label_bytes = codec.pack(1) + codec.pack(len(labels)) + b''.join(
        struct.pack('<II', *pair) for pair in labels)
    codec.labels_read(label_bytes, [n for n, _ in entries])  # round-trips, so it is well formed
    merged_tones = tones_r + [tones_d[i] for i in selected]
    files = {'.nus3audio': codec.audio_write(entries), '.tonelabel': label_bytes,
             '.nus3bank': codec.bank_write([(tag, codec.tones_write(merged_tones) if tag == b'TONE' else data)
                                            for tag, data in chunks_r])}
    for ext, content in files.items():
        path = dest.with_suffix(ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    # Verify against the written bytes, and prove nothing pre-existing was lost.
    assert codec.audio_read(files['.nus3audio']) == entries
    assert codec.tones_read(dict(codec.bank_read(files['.nus3bank']))[b'TONE']) == merged_tones
    verify_preserved(dest, original, tones_r, labels_r, recipient_chunks, wanted)
    return {'recipient': recipient.name, 'retained_tones': len(original),
            'retained_tones_byte_equal': True, 'retained_labels_byte_equal': True,
            'appended_names': sorted(names[i] for i in selected),
            'output_hashes': {ext: codec.sha(c) for ext, c in files.items()}}


def verify_preserved(dest, original, tones_r, labels_r, recipient_chunks, wanted):
    """Assert the written bank still holds every pre-existing tone, unchanged.

    Split out of `append_tones` so `--check` can point it at a deliberately
    damaged bank and prove the assertion is live rather than decorative.
    """
    read_back, chunks_back, labels_back = _read_bank(dest)
    chunks_back = dict(chunks_back)
    assert read_back[:len(original)] == original, f'{dest.name}: a pre-existing sample changed'
    assert [n for n, _ in read_back] == [n for n, _ in original] + \
        [n for n, _ in read_back[len(original):]]
    assert chunks_back[b'BINF'] == recipient_chunks[b'BINF']
    assert chunks_back[b'PROP'] == recipient_chunks[b'PROP']
    assert codec.tones_read(chunks_back[b'TONE'])[:len(tones_r)] == tones_r, \
        f'{dest.name}: a pre-existing tone record changed'
    kept = {(crc, value) for crc, value in labels_back if value >> 8 < len(original)}
    assert kept == {(crc, value) for crc, value in labels_r}, \
        f'{dest.name}: a pre-existing tone label was lost or rebased'
    resolved = {zlib.crc32(n.lower().encode()) for n in wanted}
    assert resolved <= {crc for crc, _ in labels_back}, f'{dest.name}: appended tones do not resolve'


def build(output, check_only=False):
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / name) for name in ('scratch', 'builds')), \
        'output must be in builds/ or scratch/'
    check_pins()
    record = sequence_record()
    donor_voice = [n for n, _ in codec.audio_read(VC_DONOR.with_suffix('.nus3audio').read_bytes())]
    vc_wanted = voice_names(record, donor_voice)
    assert vc_wanted == ['vc_snake_attack01', 'vc_snake_attack02',
                         'vc_snake_attack03', 'vc_snake_attack04'], vc_wanted

    banks = []
    for slot in ('c06', 'c07'):
        for folder, prefix, donor, wanted in (('fighter', 'se_eflame', SE_DONOR, SE_REQUIRED),
                                              ('fighter_voice', 'vc_eflame', VC_DONOR, set(vc_wanted))):
            dest = output / f'sound/bank/{folder}/{prefix}_{slot}'
            base = dest if dest.with_suffix('.nus3audio').is_file() else codec.ARC / f'sound/bank/{folder}/{prefix}_{slot}'
            rep = append_tones(donor, base, dest, wanted)
            rep.update(folder=folder, slot=slot, recipient_was_chained=base == dest)
            banks.append(rep)

    sqb_dest = output / 'sound/sequence/fighter/eflame.sqb'
    sqb_base = sqb_dest if sqb_dest.is_file() else codec.ARC / 'sound/sequence/fighter/eflame.sqb'
    recipient_bytes = sqb_base.read_bytes()
    recipient = codec.sqb_read(recipient_bytes)
    already = [r for r in recipient if int.from_bytes(r[:8], 'little') == hash40(SEQUENCE)]
    if already:
        # Chaining after a merge that already carried this record must not duplicate it.
        assert already == [record], 'eflame.sqb already carries a different seq_snake_rnd_attack record'
        merged_bytes, added = recipient_bytes, False
    else:
        merged = codec.sqb_write(recipient + [record])
        assert codec.sqb_read(merged) == recipient + [record]
        merged_bytes, added = merged, True
    sqb_dest.parent.mkdir(parents=True, exist_ok=True)
    sqb_dest.write_bytes(merged_bytes)
    merged_records = codec.sqb_read(merged_bytes)
    assert merged_records[:len(recipient)] == recipient, 'eflame.sqb lost a pre-existing record'

    report = {'tool_version': '1.0.0', 'date': '2026-10-02', 'evidence_tier': 'B',
              'hardware_validated': False, 'move': 'Snake AttackHi3 on Pyra c06/c07',
              'banks': banks, 'sequence': SEQUENCE, 'sequence_key': hex(hash40(SEQUENCE)),
              'sequence_voice_tones': vc_wanted, 'sequence_appended': added,
              'sqb_records_before': len(recipient), 'sqb_records_after': len(merged_records),
              'sqb_sha256': codec.sha(merged_bytes), 'recipient_sqb_sha256': codec.sha(recipient_bytes),
              'donor_sqb_sha256': SQB_SHA256,
              'note': 'No offline check establishes that a sound plays in game.'}
    (output / 'snake_uptilt_sound.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {len(banks)} banks + eflame.sqb; se {sorted(SE_REQUIRED)}; '
          f'voice {vc_wanted}; sequence appended={added}')
    return report


def stage_baseline(output):
    """Copy the real 0.20.17 Pyra banks/sqb in, so --check runs against shipped files.

    `dumps/arc` is empty in this workspace, so the tool's normal fallback base is
    unavailable. The 0.20.17 package already carries the output of the earlier
    Snake neutral-B merge, which is exactly the state this merge chains onto.
    """
    import shutil
    for rel in ('sound/bank/fighter/se_eflame_c06', 'sound/bank/fighter/se_eflame_c07',
                'sound/bank/fighter_voice/vc_eflame_c06', 'sound/bank/fighter_voice/vc_eflame_c07'):
        stem = BASELINE / rel
        for ext in ('.nus3audio', '.nus3bank', '.tonelabel'):
            target = (output / rel).with_suffix(ext)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stem.with_suffix(ext), target)
    target = output / 'sound/sequence/fighter/eflame.sqb'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BASELINE / 'sound/sequence/fighter/eflame.sqb', target)


def negative_control(output):
    """`verify_preserved` must reject a bank that lost a tone.

    Without this, "PASS" on the real run would only say the tool agreed with
    itself. Dropping the last tone record of a written bank - the one this tool
    appended - is the smallest change that has to trip the check, and it is
    checked here rather than assumed.
    """
    import shutil
    good = output / 'sound/bank/fighter/se_eflame_c06'
    bad = output / 'sound/bank/fighter/probe_se_eflame_c06'
    for ext in ('.nus3audio', '.nus3bank', '.tonelabel'):
        shutil.copy2(good.with_suffix(ext), bad.with_suffix(ext))
    entries_before, _, _ = _read_bank(bad)
    original = entries_before[:-1]
    chunks = codec.bank_read(bad.with_suffix('.nus3bank').read_bytes())
    tones = codec.tones_read(dict(chunks)[b'TONE'])
    bad.with_suffix('.nus3bank').write_bytes(codec.bank_write(
        [(tag, codec.tones_write(tones[:-1]) if tag == b'TONE' else data) for tag, data in chunks]))
    labels = [pair for pair in codec.labels_read(bad.with_suffix('.tonelabel').read_bytes(),
                                                  [n for n, _ in entries_before])
              if pair[1] >> 8 < len(original)]
    bad.with_suffix('.tonelabel').write_bytes(
        codec.pack(1) + codec.pack(len(labels)) + b''.join(struct.pack('<II', *p) for p in labels))
    try:
        verify_preserved(bad, original, tones[:-1], labels, dict(chunks), SE_REQUIRED)
    except AssertionError:
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        build(args.output)
        return
    if not args.check:
        parser.error('choose --check or --output')
    parent = ROOT / 'scratch' / '2026-10-02_fb-2-snake-up-tilt'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as tmp:
        out = Path(tmp)
        stage_baseline(out)
        report = build(out, True)
        kept = {b['retained_tones'] for b in report['banks']}
        assert kept == {543, 240}, f'unexpected retained-tone counts: {kept}'
        assert negative_control(out), 'preservation check did not fail on a truncated bank'
    print('merge_snake_uptilt_sound OK')


if __name__ == '__main__':
    main()