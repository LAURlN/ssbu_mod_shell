"""Merge Ness's back-throw sounds into Mythra c06/c07 (v1.0.0).

Plays the donor's own sounds for `mythra::ness_throw_b` instead of stand-ins
(AGENTS.md rule 17):

  * `se_ness_throw_pk01`, `se_ness_throw_pk02`, `se_ness_pk_s`
    -> `se_elight_c06` / `se_elight_c07`   (the PK grab, the swing, the release)
  * `vc_ness_attack01..04`
    -> `vc_elight_c06` / `vc_elight_c07`   (**measured** out of the donor
    sequence record by CRC32, the same way `merge_snake_uptilt_sound.py` does it
    for Snake, so the voice set follows the record rather than a hand list)
  * the exact `seq_ness_rnd_attack` record of `ness.sqb`
    -> `sound/sequence/fighter/elight.sqb`

The voice tones are not optional decoration. `sound_throwb` calls
`PLAY_SEQUENCE(seq_ness_rnd_attack)`; that record names four `vc_ness_*` tones
by CRC32, so a Mythra bank without them resolves the sequence to silence. The
set is therefore derived from the record at run time and asserted to be exactly
the four names.

`se_common_throw_01` and `se_common_throw_02` are **not** merged: they are
common-bank sounds every throw uses, and the donor names them for that reason.
That split is asserted, not assumed.

Only the five tones are appended: sample bytes and tone records are copied
unchanged, recipient bank identity (BINF/PROP/GRP/DTON/PACK) is kept, and every
appended tone is asserted to be a single-sample tone so no group child index can
dangle. The sequence append is **idempotent**: if `seq_ness_rnd_attack` is
already in `elight.sqb` the record is compared byte for byte against the donor
and left alone rather than duplicated.

Preservation is a *checked* property, not a claim: `build()` compares the tone
names, the sample bytes and the tone labels of every bank before and after, and
raises if any pre-existing tone is lost, reordered or rebased. A negative
control proves that check is live rather than decorative.

Chaining: each bank is read from `--baseline` (the installed package this delta
was recorded against), so re-running after another agent's merge is a matter of
pointing `--baseline` at that merge's output.

Offline only (tier B). No offline check establishes that a sound plays in game.

    python -B tools/merge_ness_throw_sound.py --check
    python -B tools/merge_ness_throw_sound.py --output <dir under builds/ or scratch/>
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
# Baseline this delta is recorded against: the collective 0.20.19 package that is
# currently on the card. Its elight banks already carry the earlier Hero merges,
# so it is the correct chaining point.
BASELINE = ROOT / 'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
GAMEDATA = ROOT.parents[1] / 'gamedata/ssbu-13.0.4/files'

SE_DONOR = GAMEDATA / 'sound/bank/fighter/se_ness_c00'
VC_DONOR = GAMEDATA / 'sound/bank/fighter_voice/vc_ness_c00'
SQB_DONOR = GAMEDATA / 'sound/sequence/fighter/ness.sqb'

# Pinned 2026-10-02 from tools/arc-extract against the local 13.0.4 data.arc
# (archive sha256 ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995,
# 17,600,869,448 B). Re-checked on every run.
PINS = {
    SE_DONOR: {'.nus3audio': '13a14aac91faa9526bb52894ce3b7fe0882f543235e914ad65c8b81f37f918db',
               '.nus3bank': '3f8d4ef96d38e5977cb047e76283c800d92361f3527e70da9b798ba615cac6ee',
               '.tonelabel': '68828c6d9724f79d8969fa018ad500ff74c6fe997d41b62bd7de8df170a62f85'},
    VC_DONOR: {'.nus3audio': '7b84a3f3f861f33dd23851d661aeb14c50042dc69a1e74419f981a0f3037f356',
               '.nus3bank': '69cc8944a3133a350323ac397fe9e131cbb6ee953948ac775c063b32489f8f54',
               '.tonelabel': '7dee6aae2f3f44b78c92c5147b50fa285c5684b12f873a42092ff27fb4695531'},
}
SQB_SHA256 = '8fc0ee194941d8029eb20eeb658c00f5ab7be48c82751374b07100976557e30a'
SEQUENCE = 'seq_ness_rnd_attack'
SE_REQUIRED = {'se_ness_throw_pk01', 'se_ness_throw_pk02', 'se_ness_pk_s'}
# The two common sounds the donor names. Asserted absent from the donor bank so
# this set cannot silently grow into a re-implementation of the common bank.
COMMON_SOUNDS = {'se_common_throw_01', 'se_common_throw_02'}
# Recorded from the donor banks on 2026-10-02, so a changed donor stops the run.
DONOR_SE_TONES = 63
DONOR_VC_TONES = 33


def hash40(name):
    return len(name) << 32 | zlib.crc32(name.encode())


def _donor(stem, arc_root=None):
    """The pinned donor stem, from whichever tree actually holds it.

    `stem` is an extensionless bank stem, so it is never a file itself: the test
    is that all three payload files are present next to it.
    """
    candidates = [Path(arc_root) / stem.name if arc_root else None,
                  GAMEDATA / stem.relative_to(GAMEDATA)]
    for path in candidates:
        if path and all(path.with_suffix(ext).is_file() for ext in PINS[stem]):
            return path
    wanted = sorted(p.name + e for p in candidates if p for e in PINS[stem])
    raise RuntimeError(
        f'donor {stem.name} not found. Re-pull with (workspace root):\n'
        '  tools/arc-extract/target/release/arc-extract.exe --arc '
        'gamedata/ssbu-13.0.4/data.arc --out gamedata/ssbu-13.0.4/files \\\n'
        '    ' + ' '.join(wanted))


def _sqb_path(arc_root=None):
    """The pinned donor sequence table, which is a real file, not a bank stem."""
    for path in ([Path(arc_root) / SQB_DONOR.name] if arc_root else []) + [SQB_DONOR]:
        if path.is_file() and codec.sha(path.read_bytes()) == SQB_SHA256:
            return path
    raise RuntimeError(
        f'donor {SQB_DONOR.name} not found at sha256 {SQB_SHA256}. Re-pull with '
        '(workspace root):\n'
        '  tools/arc-extract/target/release/arc-extract.exe --arc '
        'gamedata/ssbu-13.0.4/data.arc --out gamedata/ssbu-13.0.4/files \\\n'
        f'    {SQB_DONOR.name}')


def check_pins(arc_root=None):
    for stem, pins in PINS.items():
        source = _donor(stem, arc_root)
        for ext, digest in pins.items():
            data = source.with_suffix(ext).read_bytes()
            assert codec.sha(data) == digest, f'{source.name}{ext} is not the pinned revision'
    _sqb_path(arc_root)
    return {stem.name: _donor(stem, arc_root) for stem in PINS}


def sequence_record(arc_root=None):
    records = [r for r in codec.sqb_read(_sqb_path(arc_root).read_bytes())
               if int.from_bytes(r[:8], 'little') == hash40(SEQUENCE)]
    assert len(records) == 1, f'{SEQUENCE}: expected exactly one donor record, found {len(records)}'
    return records[0]


def voice_names(record, donor_names):
    """The donor `vc_ness_*` tones whose CRC32(lowercase) occurs in the record.

    Measured, not listed: the same method `merge_snake_uptilt_sound.py` uses, so
    the voice set follows the record instead of a hand-typed expectation.
    """
    return sorted(n for n in donor_names
                  if n.startswith('vc_ness_')
                  and zlib.crc32(n.lower().encode()).to_bytes(4, 'little') in record)


def labels_read_partial(data, names):
    """`codec.labels_read` but tolerating a donor whose label table is incomplete.

    `labels_read` asserts full coverage, which is right for a recipient bank and
    wrong for a donor: `vc_ness_c00.tonelabel` does not name every tone it ships.
    Every entry that *is* present is still checked against its name and length.
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
    labels = codec.labels_read(stem.with_suffix('.tonelabel').read_bytes(),
                               [n for n, _ in entries])
    return entries, chunks, labels


def _read_donor_bank(stem):
    entries = codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())
    chunks = codec.bank_read(stem.with_suffix('.nus3bank').read_bytes())
    labels = labels_read_partial(stem.with_suffix('.tonelabel').read_bytes(),
                                 [n for n, _ in entries])
    return entries, chunks, labels


def append_tones(donor_stem, recipient, dest, wanted):
    """Append the `wanted` (lowercase) tones of `donor_stem` to `recipient`."""
    donor, chunks_d, labels_d = _read_donor_bank(donor_stem)
    names = [n for n, _ in donor]
    # The common grab/release sounds must NOT live in the donor's own bank. If
    # they ever do, the "nothing to merge for them" claim in this file's
    # docstring is wrong and the run must stop rather than quietly skip them.
    assert not (COMMON_SOUNDS & {n.lower() for n in names}), \
        f'{donor_stem.name}: a "common" sound is donor-owned after all; re-audit'
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
    assert len({n.lower() for n, _ in entries}) == len(entries), \
        f'{recipient.name}: tone name collision'
    assert all(a.lower() not in wanted for a, _ in original), \
        f'{recipient.name}: one of the requested tones is already present'

    mapping = {i: len(original) + j for j, i in enumerate(selected)}
    labels = list(labels_r) + [(crc, mapping[value >> 8] << 8 | (value & 255))
                               for crc, value in labels_d if value >> 8 in mapping]
    labels.sort()
    label_bytes = codec.pack(1) + codec.pack(len(labels)) + b''.join(
        struct.pack('<II', *pair) for pair in labels)
    codec.labels_read(label_bytes, [n for n, _ in entries])
    merged_tones = tones_r + [tones_d[i] for i in selected]
    files = {'.nus3audio': codec.audio_write(entries), '.tonelabel': label_bytes,
             '.nus3bank': codec.bank_write([(tag, codec.tones_write(merged_tones)
                                            if tag == b'TONE' else data)
                                           for tag, data in chunks_r])}
    for ext, content in files.items():
        path = dest.with_suffix(ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    assert codec.audio_read(files['.nus3audio']) == entries
    assert codec.tones_read(dict(codec.bank_read(files['.nus3bank']))[b'TONE']) == merged_tones
    verify_preserved(dest, original, tones_r, labels_r, recipient_chunks, wanted)
    return {'recipient': recipient.name, 'retained_tones': len(original),
            'retained_tones_byte_equal': True, 'retained_labels_byte_equal': True,
            'appended_names': sorted(names[i] for i in selected),
            'recipient_sha256': {e: codec.sha(Path(recipient).with_suffix(e).read_bytes())
                                 for e in ('.nus3audio', '.nus3bank', '.tonelabel')},
            'output_sha256': {ext: codec.sha(c) for ext, c in files.items()}}


def verify_preserved(dest, original, tones_r, labels_r, recipient_chunks, wanted):
    """Assert the written bank still holds every pre-existing tone, unchanged.

    Split out of `append_tones` so `--check` can point it at a deliberately
    damaged bank and prove the assertion is live rather than decorative.
    """
    read_back, chunks_back, labels_back = _read_bank(dest)
    chunks_back = dict(chunks_back)
    assert read_back[:len(original)] == original, f'{dest.name}: a pre-existing sample changed'
    assert [n for n, _ in read_back][:len(original)] == [n for n, _ in original], \
        f'{dest.name}: a pre-existing tone was renamed or reordered'
    assert chunks_back[b'BINF'] == recipient_chunks[b'BINF']
    assert chunks_back[b'PROP'] == recipient_chunks[b'PROP']
    assert codec.tones_read(chunks_back[b'TONE'])[:len(tones_r)] == tones_r, \
        f'{dest.name}: a pre-existing tone record changed'
    kept = {(crc, value) for crc, value in labels_back if value >> 8 < len(original)}
    assert kept == {(crc, value) for crc, value in labels_r}, \
        f'{dest.name}: a pre-existing tone label was lost or rebased'
    resolved = {zlib.crc32(n.lower().encode()) for n in wanted}
    assert resolved <= {crc for crc, _ in labels_back}, f'{dest.name}: appended tones do not resolve'


def build(output, baseline=None, arc_root=None):
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / name) for name in ('scratch', 'builds')), \
        'output must be in builds/ or scratch/'
    baseline = Path(baseline) if baseline else BASELINE
    donors = check_pins(arc_root)
    record = sequence_record(arc_root)

    se_donor, vc_donor = donors[SE_DONOR.name], donors[VC_DONOR.name]
    se_names = [n for n, _ in codec.audio_read(se_donor.with_suffix('.nus3audio').read_bytes())]
    vc_names = [n for n, _ in codec.audio_read(vc_donor.with_suffix('.nus3audio').read_bytes())]
    assert len(se_names) == DONOR_SE_TONES, len(se_names)
    assert len(vc_names) == DONOR_VC_TONES, len(vc_names)
    vc_wanted = voice_names(record, vc_names)
    assert vc_wanted == ['vc_ness_attack01', 'vc_ness_attack02',
                         'vc_ness_attack03', 'vc_ness_attack04'], vc_wanted

    banks = []
    for slot in ('c06', 'c07'):
        for folder, prefix, donor, wanted in (
                ('fighter', 'se_elight', se_donor, set(SE_REQUIRED)),
                ('fighter_voice', 'vc_elight', vc_donor, set(vc_wanted))):
            dest = output / f'sound/bank/{folder}/{prefix}_{slot}'
            base = dest if dest.with_suffix('.nus3audio').is_file() \
                else baseline / f'sound/bank/{folder}/{prefix}_{slot}'
            rep = append_tones(donor, base, dest, wanted)
            rep.update(folder=folder, slot=slot, recipient_chained=base == dest)
            banks.append(rep)

    sqb_dest = output / 'sound/sequence/fighter/elight.sqb'
    sqb_base = sqb_dest if sqb_dest.is_file() else baseline / 'sound/sequence/fighter/elight.sqb'
    recipient_bytes = sqb_base.read_bytes()
    recipient = codec.sqb_read(recipient_bytes)
    already = [r for r in recipient if int.from_bytes(r[:8], 'little') == hash40(SEQUENCE)]
    if already:
        assert already == [record], 'elight.sqb already carries a different seq_ness_rnd_attack record'
        merged_bytes, added = recipient_bytes, False
    else:
        merged = codec.sqb_write(recipient + [record])
        assert codec.sqb_read(merged) == recipient + [record]
        merged_bytes, added = merged, True
    sqb_dest.parent.mkdir(parents=True, exist_ok=True)
    sqb_dest.write_bytes(merged_bytes)
    assert codec.sqb_read(merged_bytes)[:len(recipient)] == recipient, \
        'elight.sqb lost a pre-existing record'

    report = {'tool_version': '1.0.0', 'date': '2026-10-02', 'evidence_tier': 'B',
              'hardware_validated': False,
              'move': "vanilla Ness back throw (throw_b) on Mythra (elight) c06/c07",
              'baseline': str(baseline), 'banks': banks, 'sequence': SEQUENCE,
              'sequence_key': hex(hash40(SEQUENCE)), 'sequence_voice_tones': vc_wanted,
              'sequence_appended': added,
              'sqb_records_before': len(recipient), 'sqb_records_after': len(codec.sqb_read(merged_bytes)),
              'sqb_sha256': codec.sha(merged_bytes),
              'recipient_sqb_sha256': codec.sha(recipient_bytes),
              'donor_sqb_sha256': SQB_SHA256,
              'common_sounds_not_merged': sorted(COMMON_SOUNDS),
              'note': 'No offline check establishes that a sound plays in game.'}
    (output / 'ness_throw_sound.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {len(banks)} banks + elight.sqb; se {sorted(SE_REQUIRED)}; '
          f'voice {vc_wanted}; sequence appended={added}')
    return report


def negative_control(output):
    """`verify_preserved` must reject a bank that lost a tone."""
    import shutil
    good = output / 'sound/bank/fighter/se_elight_c06'
    bad = output / 'sound/bank/fighter/probe_se_elight_c06'
    for ext in ('.nus3audio', '.nus3bank', '.tonelabel'):
        shutil.copy2(good.with_suffix(ext), bad.with_suffix(ext))
    entries_before, _, _ = _read_bank(bad)
    original = entries_before[:-1]
    chunks = codec.bank_read(bad.with_suffix('.nus3bank').read_bytes())
    tones = codec.tones_read(dict(chunks)[b'TONE'])
    bad.with_suffix('.nus3bank').write_bytes(codec.bank_write(
        [(tag, codec.tones_write(tones[:-1]) if tag == b'TONE' else data)
         for tag, data in chunks]))
    labels = [p for p in codec.labels_read(bad.with_suffix('.tonelabel').read_bytes(),
                                           [n for n, _ in entries_before])
              if p[1] >> 8 < len(original)]
    bad.with_suffix('.tonelabel').write_bytes(
        codec.pack(1) + codec.pack(len(labels))
        + b''.join(struct.pack('<II', *p) for p in labels))
    try:
        verify_preserved(bad, original, tones[:-1], labels, dict(chunks), SE_REQUIRED)
    except AssertionError:
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--baseline', type=Path,
                        help='package this delta chains onto (default: installed 0.20.19)')
    parser.add_argument('--arc-root', type=Path)
    args = parser.parse_args()
    if args.output:
        build(args.output, args.baseline, args.arc_root)
        return
    if not args.check:
        parser.error('choose --check or --output')
    parent = ROOT / 'scratch/2026-10-02_buffy/ness_throw_b'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as tmp:
        report = build(Path(tmp), args.baseline, args.arc_root)
        kept = {b['retained_tones'] for b in report['banks']}
        # Measured 2026-10-02 against the installed 0.20.19 package: the
        # recipient banks hold 389 `se_elight_*` and 233 `vc_elight_*` tones
        # before this merge. Recorded so a changed baseline stops the run rather
        # than silently re-basing the preservation claim.
        assert kept == {389, 233}, f'unexpected retained-tone counts: {kept}'
        assert negative_control(Path(tmp)), 'preservation check did not fire on a truncated bank'
    print('merge_ness_throw_sound OK')


if __name__ == '__main__':
    main()