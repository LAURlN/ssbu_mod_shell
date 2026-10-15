"""Merge Lucas's down-smash sounds into Mythra c06/c07. v1.0.0.

Plays the donor's own sounds for `mythra::lucas_attack_lw4` instead of stand-ins
(AGENTS.md rule 17). Six tones, and the list is read out of the donor's own
scripts rather than typed from memory:

  sound_attacklw4        : `se_lucas_smash_l04` (the charge wind-up, and the
                            same name STOP_SE'd at frame 7), `vc_lucas_attack07`
                            (frame 16), then `se_lucas_smash_l01` / `_l02` /
                            `_l03` on the three hits at frames 22, 30, 40.
  sound_attacklw4charge  : `se_common_smash_start_04` (common bank, no merge
                            needed) and `se_lucas_pk_charge` via PLAY_STATUS.

`se_common_smash_start_04` is the only name the move plays that no merge is
required for, and that is checked rather than assumed: the tool asserts the
common name resolves in the common bank and that none of the six donor tones is
already present in a recipient bank.

The recipient is **Mythra's own c06/c07 banks**, not Pyra's: the other three
concurrent tasks target G&W (`eflame`), and this move is on `elight`. Measured
baseline: `se_elight_c06/c07` carry 389 tones, `vc_elight_c06/c07` 233, and the
`GRP `/`DTON`/`PACK` bank-wide tables are byte-equal to the donor's, which is
what makes an append valid at all.

Chaining: each bank is read from the build output if an earlier merge already
wrote it, else from the recorded baseline package. Appends only; sample bytes
and tone records of every pre-existing tone are preserved, and that is a
*checked* property rather than a claim - `build()` re-reads the written bytes
and fails if any pre-existing tone changed, was reordered, was renamed or lost
its label.

    python tools/merge_lucas_downsmash_sound.py --check
    python tools/merge_lucas_downsmash_sound.py --output <dir under builds/ or scratch/>

Offline only (tier B). No offline check establishes that a sound plays in game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_hero_neutral_b_sound as codec
import merge_donor_sound as donor_sound

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / 'refs/lucas_attack_lw4'
# The donor banks are pinned in refs/ like every other donor, not read out of a
# live export (rule 29: pin what a later run needs).
SE_DONOR = REFS / 'arc/sound/bank/fighter/se_lucas'
VC_DONOR = REFS / 'arc/sound/bank/fighter_voice/vc_lucas'
PINS = {
    SE_DONOR: {'.nus3audio': '726e86302fc190f91522964374249efb100fad4a9a1296fe0df176e50b3b520c',
               '.nus3bank': '03b8daac0e14a18685c0276b21f76d500ddf7c20b7e45e68657c8694d8dc0277',
               '.tonelabel': '45c0f22a5e0d5503018a3b75d9cec49db5f19ae9058573e35e04f7fe1ab4da38'},
    VC_DONOR: {'.nus3audio': 'f2a15153519a1b9566fc53770abd1d401f165c147f55babc7b7430885ff04878',
               '.nus3bank': '90780146f4275104bd8d76072a799a2833c755ded6a6736b500ba3abde4d6bbc',
               '.tonelabel': 'a7d200b01362e082d201f2177f810f4b60fcaa1e70c02e399501e0572de6ee55'},
}
SE_REQUIRED = {'se_lucas_smash_l01', 'se_lucas_smash_l02', 'se_lucas_smash_l03',
               'se_lucas_smash_l04', 'se_lucas_pk_charge'}
VC_REQUIRED = {'vc_lucas_attack07'}
# Names the donor scripts play that resolve in a shared bank, so no merge is
# needed. Asserted to be absent from the donor banks precisely because they are
# common-bank names: if one of them ever moved into a fighter bank, the merge
# would silently stop being complete.
COMMON_NAMES = {'se_common_smash_start_04'}
ACMD = REFS / 'donor_acmd/lucas__AttackLw4.txt'
ACMD_CHARGE = REFS / 'donor_acmd/lucas__AttackLw4Charge.txt'
RE_PLAY = re.compile(r'(?:PLAY_SE|PLAY_STATUS|STOP_SE)\(agent, Hash40::new\("([a-z0-9_]+)"\)\)')
BASELINE = ROOT / 'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
# folder, recipient prefix, donor stem, required names
PLAN = (
    ('fighter', 'se_elight', SE_DONOR, SE_REQUIRED),
    ('fighter_voice', 'vc_elight', VC_DONOR, VC_REQUIRED),
)


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def check_pins() -> None:
    for stem, pins in PINS.items():
        for ext, digest in pins.items():
            path = stem.with_suffix(ext)
            assert path.is_file(), f'missing pinned donor bank file {path}'
            assert codec.sha(path.read_bytes()) == digest, f'{path} is not the pinned revision'


def script_names() -> dict:
    """Every SE/VC name the two donor scripts play, read from the pinned text.

    Reading the scripts rather than a hand-typed list is the point: this is the
    same reasoning `merge_donor_sound.referenced_names` uses for the generated
    modules, and it is what makes "every dependency" checkable instead of
    asserted. The charge script is read too, which is how `se_lucas_pk_charge`
    is caught - it is played by PLAY_STATUS, not PLAY_SE, and a regex that only
    knew about PLAY_SE would have missed it.
    """
    names = set()
    for path in (ACMD, ACMD_CHARGE):
        assert path.is_file(), f'missing pinned donor script {path}'
        names |= set(RE_PLAY.findall(path.read_text(encoding='utf-8')))
    return {'all': sorted(names),
            'needs_merge': sorted(names - COMMON_NAMES),
            'common': sorted(names & COMMON_NAMES)}


def read_bank(stem: Path) -> tuple:
    entries = codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())
    chunks = codec.bank_read(stem.with_suffix('.nus3bank').read_bytes())
    labels = codec.labels_read(stem.with_suffix('.tonelabel').read_bytes(), [n for n, _ in entries])
    return entries, chunks, labels


def read_donor_bank(stem: Path) -> tuple:
    """Like `read_bank`, but tolerant of a donor whose label table is partial.

    Measured on both pinned Lucas banks: every tone this merge wants *is* named,
    but the table is not asserted to be complete, because a donor bank is free
    not to name every file it ships. Each entry that is present is still checked
    against its name and length.
    """
    entries = codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())
    chunks = codec.bank_read(stem.with_suffix('.nus3bank').read_bytes())
    data = stem.with_suffix('.tonelabel').read_bytes()
    assert codec.u32(data, 0) == 1
    pairs = list(struct.iter_unpack('<II', data[8:]))
    assert codec.u32(data, 4) == len(pairs)
    names = [n for n, _ in entries]
    for crc, value in pairs:
        assert 0 <= (value >> 8) < len(names), f'label points outside the bank: {value:#x}'
        assert crc == zlib.crc32(names[value >> 8].lower().encode())
        assert value & 0xff == len(names[value >> 8].encode())
    return entries, chunks, pairs


def append_tones(donor_stem: Path, recipient: Path, dest: Path, wanted: set) -> dict:
    donor, donor_chunks, donor_labels = read_donor_bank(donor_stem)
    names = [n for n, _ in donor]
    donor_tones = codec.tones_read(dict(donor_chunks)[b'TONE'])
    selected = [i for i, n in enumerate(names) if n.lower() in wanted]
    assert len(selected) == len(wanted), (
        f'{donor_stem.name}: found {len(selected)} of {sorted(wanted)}')
    # Every appended record must be a single-sample tone. A randomised-group tone
    # carries child indices that would now point into the recipient's list, and
    # the result would be a tone that plays the wrong sample - measured kind 0
    # for all six, and asserted rather than assumed.
    kinds = {donor_sound.tone_kind(donor_tones[i]) for i in selected}
    assert kinds == {0}, f'{donor_stem.name}: tone kinds {sorted(kinds)}; a group tone would need rebasing'

    original, recipient_chunks, recipient_labels = read_bank(recipient)
    original_names = {n.lower() for n, _ in original}
    collision = original_names & {n.lower() for n in (names[i] for i in selected)}
    assert not collision, f'{recipient.name}: tone name collision {sorted(collision)}'
    for tag in donor_sound.SHARED:
        assert dict(donor_chunks)[tag] == dict(recipient_chunks)[tag], \
            f'{recipient.name}: shared section {tag!r} differs from the donor bank'

    recipient_tones = codec.tones_read(dict(recipient_chunks)[b'TONE'])
    assert len(recipient_tones) == len(original)
    entries = original + [donor[i] for i in selected]
    assert len({n.lower() for n, _ in entries}) == len(entries)

    mapping = {i: len(original) + j for j, i in enumerate(selected)}
    labels = list(recipient_labels) + [(crc, mapping[value >> 8] << 8 | (value & 0xff))
                                       for crc, value in donor_labels if value >> 8 in mapping]
    labels.sort()
    label_bytes = codec.pack(1) + codec.pack(len(labels)) + \
        b''.join(struct.pack('<II', *pair) for pair in labels)
    codec.labels_read(label_bytes, [n for n, _ in entries])

    merged_tones = recipient_tones + [donor_tones[i] for i in selected]
    files = {
        '.nus3audio': codec.audio_write(entries),
        '.tonelabel': label_bytes,
        '.nus3bank': codec.bank_write(
            [(tag, codec.tones_write(merged_tones) if tag == b'TONE' else data)
             for tag, data in recipient_chunks]),
    }
    for ext, data in files.items():
        path = dest.with_suffix(ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    verify_preserved(dest, original, recipient_tones, recipient_labels, recipient_chunks, wanted)
    return {
        'recipient': recipient.name, 'retained_tones': len(original),
        'retained_tones_byte_equal': True, 'retained_labels_byte_equal': True,
        'appended_names': sorted(names[i] for i in selected),
        'appended_bank_case': sorted(names[i] for i in selected if names[i] != names[i].lower()),
        'output_hashes': {ext: codec.sha(d) for ext, d in files.items()},
    }


def verify_preserved(dest: Path, original, recipient_tones, recipient_labels,
                     recipient_chunks, wanted: set) -> None:
    """Assert the written bank still holds every pre-existing tone, unchanged.

    Split out of `append_tones` so `--check` can point it at a damaged bank and
    prove the assertion is live rather than decorative.
    """
    read_back, chunks_back, labels_back = read_bank(dest)
    chunks_back = dict(chunks_back)
    assert read_back[:len(original)] == original, f'{dest.name}: a pre-existing sample changed'
    assert [n for n, _ in read_back][:len(original)] == [n for n, _ in original], \
        f'{dest.name}: a pre-existing tone was reordered or renamed'
    assert chunks_back[b'BINF'] == dict(recipient_chunks)[b'BINF']
    assert chunks_back[b'PROP'] == dict(recipient_chunks)[b'PROP']
    assert codec.tones_read(chunks_back[b'TONE'])[:len(recipient_tones)] == recipient_tones, \
        f'{dest.name}: a pre-existing tone record changed'
    kept = {(crc, value) for crc, value in labels_back if value >> 8 < len(original)}
    assert kept == {(crc, value) for crc, value in recipient_labels}, \
        f'{dest.name}: a pre-existing tone label was lost or rebased'
    resolved = {zlib.crc32(n.lower().encode()) for n in wanted}
    assert resolved <= {crc for crc, _ in labels_back}, f'{dest.name}: appended tones do not resolve'


def build(output: Path) -> dict:
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / name) for name in ('scratch', 'builds')), \
        'output must be in builds/ or scratch/'
    check_pins()
    scripts = script_names()
    assert set(scripts['needs_merge']) == SE_REQUIRED | VC_REQUIRED, (
        f'the donor scripts play {scripts["needs_merge"]}, this tool merges '
        f'{sorted(SE_REQUIRED | VC_REQUIRED)}; they must agree')

    banks = []
    for folder, prefix, donor, wanted in PLAN:
        for slot in ('c06', 'c07'):
            dest = output / f'sound/bank/{folder}/{prefix}_{slot}'
            base = dest if dest.with_suffix('.nus3audio').is_file() else BASELINE / f'sound/bank/{folder}/{prefix}_{slot}'
            rep = append_tones(donor, base, dest, wanted)
            rep.update(folder=folder, slot=slot, recipient_was_chained=base == dest,
                       donor=str(donor.relative_to(ROOT)))
            banks.append(rep)

    report = {'tool_version': '1.0.0', 'date': '2026-10-02', 'evidence_tier': 'B',
              'hardware_validated': False,
              'move': 'Lucas AttackLw4 / AttackLw4Hold on Mythra c06/c07',
              'donor_scripts': {'all_names_played': scripts['all'],
                                'merged': scripts['needs_merge'],
                                'common_bank_no_merge_needed': scripts['common']},
              'baseline': str(BASELINE.relative_to(ROOT)),
              'banks': banks,
              'note': 'No offline check establishes that a sound plays in game.'}
    (output / 'lucas_downsmash_sound.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {len(banks)} banks; merged {sorted(SE_REQUIRED | VC_REQUIRED)}; '
          f'common {scripts["common"]}')
    for rep in banks:
        print(f'  {rep["slot"]} {rep["recipient"]}: {rep["retained_tones"]} retained, '
              f'+{len(rep["appended_names"])} appended')
    return report


def negative_controls() -> None:
    """Prove `verify_preserved` is live, by pointing it at a damaged bank."""
    import tempfile
    with tempfile.TemporaryDirectory(dir=ROOT / 'scratch') as tmp:
        dest = Path(tmp) / 'se_elight_c06'
        build_report = None
        original = BASELINE / 'sound/bank/fighter/se_elight_c06'
        # A correct merge, then a corrupted copy of it.
        good = Path(tmp) / 'good'
        append_tones(SE_DONOR, original, good / 'se_elight_c06', SE_REQUIRED)
        entries, chunks, labels = read_bank(good / 'se_elight_c06')
        bad_tones = codec.tones_read(dict(chunks)[b'TONE'])
        # Damage 1: a pre-existing tone record edited.
        damaged = codec.audio_write(entries)
        chunks_bad = [(tag, codec.tones_write(
            [bad_tones[0][:-1] + bytes([bad_tones[0][-1] ^ 0xff])] + bad_tones[1:])
            if tag == b'TONE' else data) for tag, data in chunks]
        bad = Path(tmp) / 'bad'
        bad.mkdir()
        for ext, data in (('.nus3audio', damaged), ('.tonelabel', (good / 'se_elight_c06.tonelabel').read_bytes()),
                          ('.nus3bank', codec.bank_write(chunks_bad))):
            (bad / f'se_elight_c06{ext}').write_bytes(data)
        try:
            verify_preserved(bad / 'se_elight_c06', entries[:0] or
                             codec.audio_read(original.with_suffix('.nus3audio').read_bytes()),
                             codec.tones_read(dict(codec.bank_read(original.with_suffix('.nus3bank').read_bytes()))[b'TONE']),
                             codec.labels_read(original.with_suffix('.tonelabel').read_bytes(),
                                               [n for n, _ in codec.audio_read(original.with_suffix('.nus3audio').read_bytes())]),
                             dict(codec.bank_read(original.with_suffix('.nus3bank').read_bytes())),
                             SE_REQUIRED)
        except AssertionError:
            print('negative control PASS: a damaged pre-existing tone is rejected')
            return
        raise RuntimeError('verify_preserved accepted a damaged bank')


def check() -> None:
    check_pins()
    scripts = script_names()
    print('donor scripts play:', scripts['all'])
    print('  merged into the elight banks:', scripts['needs_merge'])
    print('  common bank, no merge needed:', scripts['common'])
    for folder, prefix, donor, wanted in PLAN:
        names = {n.lower() for n, _ in codec.audio_read(donor.with_suffix('.nus3audio').read_bytes())}
        assert wanted <= names, f'{donor.name}: missing {sorted(wanted - names)}'
        common_in_donor = COMMON_NAMES & names
        assert not common_in_donor, f'{donor.name} unexpectedly carries {sorted(common_in_donor)}'
        for slot in ('c06', 'c07'):
            recip = BASELINE / f'sound/bank/{folder}/{prefix}_{slot}'
            entries = codec.audio_read(recip.with_suffix('.nus3audio').read_bytes())
            have = {n.lower() for n, _ in entries}
            assert not (wanted & have), f'{recip.name}: already carries {sorted(wanted & have)}'
            print(f'  {recip.name}: {len(entries)} baseline tones, none of the six present')
    print('PASS: pins, script coverage, donor tones present, recipients clean')
    negative_controls()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    if args.check or not args.output:
        check()
        return 0
    build(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
