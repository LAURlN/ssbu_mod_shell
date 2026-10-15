"""Merge Pikachu's back-air and landing sounds into Pyra c06/c07 (v1.0.0).

Plays the donor's own sounds for `acmd::pikachu_attack_air_b` instead of
stand-ins (AGENTS.md rule 17):

  * `se_pikachu_swing_s` (the finisher swing), `se_pikachu_landing02` (the
    landing)  ->  `se_eflame_c06` / `se_eflame_c07`
  * `vc_pikachu_attack01..04`
    ->  `vc_eflame_c06` / `vc_eflame_c07`  (**measured** out of the donor
    sequence record by CRC32, the same way `merge_ness_throw_sound.py` does it
    for Ness, so the voice set follows the record rather than a hand list)
  * the exact `seq_pikachu_rnd_attack` record of `pikachu.sqb`
    ->  `sound/sequence/fighter/eflame.sqb`

The voice tones are not optional decoration. `sound_attackairb` calls
`PLAY_SEQUENCE(seq_pikachu_rnd_attack)`; that record names four `vc_pikachu_*`
tones by CRC32, so a Pyra bank without them resolves the sequence to silence.
The set is therefore derived from the record at run time and asserted to be
exactly the four names.

`se_common_swing_02` is **not** merged: it is a common-bank sound every swing
uses, and the donor names it for that reason. That split is asserted, not
assumed.

Effects need nothing here. `effect_attackairb` and `effect_landingairb` name
`sys_spin_wind`, `sys_attack_impact` and `sys_down_smoke`, all of which are
always-resident common-bank names, so no donor emitter is merged and no
recipient effect bank is touched. `tools/audit_pikachu_airb_donor.py` stops the
run if that ever stops being true.

Only the six tones are appended: sample bytes and tone records are copied
unchanged, recipient bank identity (BINF/PROP/GRP/DTON/PACK) is kept, and every
appended tone is asserted to be a single-sample tone so no group child index can
dangle. The sequence append is **idempotent**: if `seq_pikachu_rnd_attack` is
already in `eflame.sqb` the record is compared byte for byte against the donor
and left alone rather than duplicated.

Preservation is a *checked* property, not a claim: `build()` compares the tone
names, the sample bytes and the tone labels of every bank before and after, and
raises if any pre-existing tone is lost, reordered or rebased. A negative
control proves that check is live rather than decorative.

Chaining: each bank is read from `--baseline` (the installed package this delta
is recorded against), so re-running after another agent's merge is a matter of
pointing `--baseline` at that merge's output. This is a **semantic merge**: apply
it to the installer's candidate bank, never copy a bank over one another task
changed.

Offline only (tier B). No offline check establishes that a sound plays in game.

    python -B tools/merge_pikachu_airb_sound.py --check
    python -B tools/merge_pikachu_airb_sound.py --output <dir under builds/ or scratch/>
"""
from __future__ import annotations

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
REF = ROOT / 'refs/pikachu_attack_air_b'
ARC = REF / 'arc'
# Baseline this delta is recorded against: the installed 0.20.23 package. Its
# eflame banks already carry the earlier merges, so it is the right chaining
# point.
BASELINE = ROOT / 'builds/pgwr/0.20.23/ultimate/mods/pyra_gamewatch_reskin'
SE_DONOR = ARC / 'sound/bank/fighter/se_pikachu_c00'
VC_DONOR = ARC / 'sound/bank/fighter_voice/vc_pikachu_c00'
SQB_DONOR = ARC / 'sound/sequence/fighter/pikachu.sqb'

# Pinned 2026-10-03 out of the local 13.0.4 data.arc
# (archive sha256 ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995,
# 17,600,869,448 B) with the workspace tool tools/arc-extract. Re-checked on
# every run.
PINS = {
    SE_DONOR: {'.nus3audio': 'b8dafdbd61e20a8cd08ad316abce8a7c9b751133c7cc31426b922bfec95e71c6',
               '.nus3bank': '03c56027c8c99399ce3052272aa347e054bccb80223868548c2f6dd48b2148f6',
               '.tonelabel': '8f67ad6e56b359f15310b9b094dcb7e6fea61072cc5229b032f856c4fe2c9521'},
    VC_DONOR: {'.nus3audio': 'ced0269a277b65b81b71ea567f310315b7d62d972fac03d6761148e62ba1935e',
               '.nus3bank': 'ed5c1ebaa7ce0f0dbee496b2a2c2183cffe9841194a635650b853d33b15d633e',
               '.tonelabel': '141ee9a001af633d632a5ebbf43e81c725beca265a8beed1fe34793497cc8e7a'},
}
SQB_SHA256 = 'dbb822c05944e76e153c9a7fb8433c727924e8e4ccdfe02853c7cea2d1149845'
SEQUENCE = 'seq_pikachu_rnd_attack'
SE_REQUIRED = {'se_pikachu_swing_s', 'se_pikachu_landing02'}
# The common sounds the donor names. Asserted absent from the donor bank so this
# set cannot silently grow into a re-implementation of the common bank.
COMMON_SOUNDS = {'se_common_swing_02'}
# Recorded from the donor banks on 2026-10-03, so a changed donor stops the run.
DONOR_SE_TONES = 61
DONOR_VC_TONES = 36
EXPECTED_VOICE = ['vc_pikachu_attack01', 'vc_pikachu_attack02',
                  'vc_pikachu_attack03', 'vc_pikachu_attack04']


def _rel(path: Path) -> str:
    """Workspace-relative posix path, so a shipped report carries no drive letter."""
    try:
        return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def hash40(name):
    return len(name) << 32 | zlib.crc32(name.encode())


def _donor(stem, arc_root=None):
    candidates = [Path(arc_root) / stem.name if arc_root else None, stem]
    for path in candidates:
        if path and all(path.with_suffix(ext).is_file() for ext in PINS[stem]):
            return path
    wanted = sorted(str(p) for p in candidates if p for e in PINS[stem])
    raise RuntimeError(
        f'donor {stem.name} not found next to any of {wanted}. Re-pull with '
        '(workspace root):\n'
        '  tools/arc-extract/target/release/arc-extract.exe --arc '
        'gamedata/ssbu-13.0.4/data.arc --out gamedata/ssbu-13.0.4/files \\\n'
        '    ' + ' '.join(wanted))


def _sqb_path(arc_root=None):
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
    """The donor `vc_pikachu_*` tones whose CRC32 occurs in the record.

    Measured, not listed, and by scanning every 4-byte boundary rather than a
    hand-modelled child layout - the surrounding record layout is not documented,
    and the same measured approach `merge_ness_throw_sound.py` takes for its four
    tones.
    """
    found = []
    for name in donor_names:
        crc = zlib.crc32(name.lower().encode()) & 0xffffffff
        needle = crc.to_bytes(4, 'little')
        start = 0
        while True:
            at = record.find(needle, start)
            if at < 0:
                break
            if struct.unpack_from('<I', record, at + 4)[0] == len(name.encode()):
                if name not in found:
                    found.append(name)
                break
            start = at + 4
    return found


def labels_read_partial(data, names):
    """`codec.labels_read` but tolerating a donor whose label table is incomplete.

    `labels_read` asserts full coverage, which is right for a recipient bank and
    wrong for a donor: a donor `.tonelabel` does not name every tone it ships.
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
    # The common swing sound must NOT live in the donor's own bank. If it ever
    # does, the "nothing to merge for it" claim in this file's docstring is wrong
    # and the run must stop rather than quietly skip it.
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


def assert_idempotent(merged, arc_root=None):
    """A second pass over this tool's own output must add nothing.

    Two different properties, checked separately because they behave differently:

    * the **tone** half must *refuse* - the tones are already present, so
      `append_tones` raises a name collision instead of silently doubling the
      bank. A merge tool that quietly appends twice is how a bank grows tones
      nobody can account for.
    * the **sequence** half must be a genuine no-op: the record is compared byte
      for byte against the donor and left alone rather than duplicated.
    """
    sqb = merged / 'sound/sequence/fighter/eflame.sqb'
    before = sqb.read_bytes()
    refused = False
    with tempfile.TemporaryDirectory(dir=ROOT / 'scratch/2026-10-03_buffy') as tmp:
        try:
            build(Path(tmp), merged, arc_root)
        except AssertionError as exc:
            # Only the tone-collision refusal counts; any other assertion is a
            # real failure and must not be swallowed here.
            if 'tone name collision' in str(exc):
                refused = True
            else:
                raise
    assert refused, 'a second tone merge appended duplicate tones instead of refusing'
    after = sqb.read_bytes()
    assert after == before, 'a second pass changed eflame.sqb'
    records = codec.sqb_read(after)
    keys = [int.from_bytes(r[:8], 'little') for r in records]
    assert keys.count(hash40(SEQUENCE)) == 1, \
        f'{SEQUENCE} appears {keys.count(hash40(SEQUENCE))} times in eflame.sqb'
    return {'sqb_records': len(records), 'tone_merge_refused_on_second_pass': True}


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
    assert vc_wanted == EXPECTED_VOICE, vc_wanted

    banks = []
    for slot in ('c06', 'c07'):
        for folder, prefix, donor, wanted in (
                ('fighter', 'se_eflame', se_donor, set(SE_REQUIRED)),
                ('fighter_voice', 'vc_eflame', vc_donor, set(vc_wanted))):
            dest = output / f'sound/bank/{folder}/{prefix}_{slot}'
            base = dest if dest.with_suffix('.nus3audio').is_file() \
                else baseline / f'sound/bank/{folder}/{prefix}_{slot}'
            rep = append_tones(donor, base, dest, wanted)
            rep.update(folder=folder, slot=slot, recipient_chained=base == dest)
            banks.append(rep)

    sqb_dest = output / 'sound/sequence/fighter/eflame.sqb'
    sqb_base = sqb_dest if sqb_dest.is_file() else baseline / 'sound/sequence/fighter/eflame.sqb'
    recipient_bytes = sqb_base.read_bytes()
    recipient = codec.sqb_read(recipient_bytes)
    already = [r for r in recipient if int.from_bytes(r[:8], 'little') == hash40(SEQUENCE)]
    if already:
        assert already == [record], 'eflame.sqb already carries a different seq_pikachu_rnd_attack record'
        merged_bytes, added = recipient_bytes, False
    else:
        merged = codec.sqb_write(recipient + [record])
        assert codec.sqb_read(merged) == recipient + [record]
        merged_bytes, added = merged, True
    sqb_dest.parent.mkdir(parents=True, exist_ok=True)
    sqb_dest.write_bytes(merged_bytes)
    assert codec.sqb_read(merged_bytes)[:len(recipient)] == recipient, \
        'eflame.sqb lost a pre-existing record'

    report = {'tool_version': '1.0.0', 'date': '2026-10-03', 'evidence_tier': 'B',
              'hardware_validated': False,
              'move': "vanilla Pikachu back air (AttackAirB) + landing on eflame c06/c07",
              # Recorded workspace-relative: a shipped report must not carry this
              # machine's drive letter (mod rule: relative paths only).
              'baseline': _rel(baseline), 'banks': banks, 'sequence': SEQUENCE,
              'sequence_key': hex(hash40(SEQUENCE)), 'sequence_voice_tones': vc_wanted,
              'sequence_appended': added,
              'sqb_records_before': len(recipient),
              'sqb_records_after': len(codec.sqb_read(merged_bytes)),
              'sqb_sha256': codec.sha(merged_bytes),
              'recipient_sqb_sha256': codec.sha(recipient_bytes),
              'donor_sqb_sha256': SQB_SHA256,
              'common_sounds_not_merged': sorted(COMMON_SOUNDS),
              'effects_merged': [],
              'effects_note': 'every effect the donor names is a common-bank sys_* name, '
                              'so no donor emitter and no recipient effect bank is touched',
              'note': 'No offline check establishes that a sound plays in game.'}
    (output / 'pikachu_airb_sound.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {len(banks)} banks + eflame.sqb; se {sorted(SE_REQUIRED)}; '
          f'voice {vc_wanted}; sequence appended={added}')
    return report


def negative_controls(output):
    """`verify_preserved` must reject a bank that lost a tone."""
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
                        help='package this delta chains onto (default: installed 0.20.23)')
    parser.add_argument('--arc-root', type=Path)
    args = parser.parse_args()
    if args.output:
        build(args.output, args.baseline, args.arc_root)
        return
    if not args.check:
        parser.error('choose --check or --output')
    parent = ROOT / 'scratch/2026-10-03_buffy/pikachu_airb'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as tmp:
        report = build(Path(tmp), args.baseline, args.arc_root)
        kept = {(b['folder'], b['retained_tones']) for b in report['banks']}
        # Measured 2026-10-03 against the installed 0.20.23 package. Recorded so a
        # changed baseline stops the run rather than silently re-basing the
        # preservation claim. (0.20.22's Zapple/HUD release and the earlier
        # Snake/Lucas/Ness merges are already in these banks, which is why the
        # counts exceed the 544/240 recorded against 0.20.19.)
        assert kept == {('fighter', 561), ('fighter_voice', 250)}, \
            f'unexpected retained-tone counts: {kept}'
        assert negative_control_ran(Path(tmp)), \
            'preservation check did not fire on a truncated bank'
        # Idempotence: a second pass over this tool's own output must add nothing.
        idem = assert_idempotent(Path(tmp), args.arc_root)
        assert idem['sqb_records'] == report['sqb_records_after'], \
            'the sequence record count changed on the second pass'
        # Merging twice onto the *original* baseline must be byte-identical to
        # merging once, which is the property the installer actually relies on.
        with tempfile.TemporaryDirectory(dir=parent) as twin:
            repeat = build(Path(twin), args.baseline, args.arc_root)
            for a, b in zip(report['banks'], repeat['banks']):
                assert a['output_sha256'] == b['output_sha256'], \
                    f'{a["recipient"]}: a repeat merge from the same baseline differs'
            assert repeat['sqb_sha256'] == report['sqb_sha256'], \
                'a repeat merge from the same baseline differs in eflame.sqb'
    print('merge_pikachu_airb_sound OK')


def negative_control_ran(output):
    return negative_controls(output)


if __name__ == '__main__':
    main()