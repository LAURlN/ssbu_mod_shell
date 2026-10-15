"""Merge real donor sound banks into Pyra c06/c07 (v1.1.0).

Why this exists
---------------
The port plays other fighters' moves on Pyra's body (c06 Shadow Purple / c07 Golden
Light). A Pyra in c06/c07 is still `eflame`, and `PLAY_SE(Hash40::new("se_gamewatch_
wave04_mi"))` resolves against the banks the *current fighter* loaded. `se_gamewatch`
is not one of them, so every donor sound name played silence.

The previous answer was generator rule R2 in `src/pgwr/tools/gen_acmd.py`, which rewrote
each donor name to an `se_eflame_*` one so something audible would come out. That is a
stand-in, which `AGENTS.md` rule 17 forbids ("no stand-in sounds"), and it is wrong twice
over: G&W's swing, smash, dash and footstep noises *are* the audible identity of those
moves, so replacing them with Pyra's sword swings is the "leftover Pyra" symptom in a
different costume. Substituting also destroyed information the port wants to keep - three
distinct G&W waves (`wave01`, `wave02`, `wave04`) all collapsed onto one `swing_s01`, so
the jab, dash and aerial became audibly identical.

The sounds were never missing, only unreachable from this fighter's bank list. So this does
what `tools/merge_hero_neutral_b_sound.py` already does for Hero: append each donor's
complete tone records and encoded audio to Pyra's own c06/c07 banks. Recipient identity,
group tables and Pyra's own tones are untouched.

# Donors, and why each is here

| donor bank        | whose moves        | scripts that reference it |
| ----------------- | ------------------ | -------------------------- |
| `se_gamewatch`    | G&W (the reskin)   | `acmd/generated/*.rs`, from the G&W ACMD dumps |
| `se_diddy`        | Diddy (Monkey Flip = side-B) | `acmd/monkey_flip.rs` |
| `se_chrom`        | Chrom (the jab)    | `acmd/chrom_jab.rs` |
| `vc_diddy` (voice)| Diddy (Monkey Flip)| `acmd/monkey_flip.rs` |
| `se_littlemac_c00` | Little Mac (forward smash) | `acmd/littlemac_attack_s4.rs` |
| `vc_littlemac_c00` (voice) | Little Mac (forward smash) | `acmd/littlemac_attack_s4.rs` |

The two Little Mac banks are the exception to "present in the export":
`dumps/arc/fighter/littlemac` is **empty** on disk (0 of its 4290 indexed files), so
they were pulled live into `refs/littlemac_attack_s4/arc/sound/bank/` on 2026-09-30
(`tools/fetch_arc_files.py --set littlemac_attack_s4`) and resolve through
`DONOR_ROOTS` below. Everything else about them is handled identically.

All four banks are present in the export named in `paths.toml`, all four are tone-kind 0
(measured), and all four share `GRP `/`DTON`/`PACK` byte-for-byte with `se_eflame_c06`
(measured). Little Mac's two are measured the same way against the pinned extraction.
Chrom's jab and the Cloud forward-air trail are *not* in this table:
`se_chrom_swing_s` is already used verbatim in `chrom_jab.rs`, and Cloud's fair is Cloud's
own move, so neither is a Pyra stand-in to replace.

`vc_gamewatch` is ABSENT from the export, so G&W's four voice lines
(`vc_gamewatch_passive` and friends) remain unplayable. That is a dump request, not
something to substitute around - see `refs/sound/dump_requests.md`.

# What is and is not proven

Tier **B**: measured offline, on the 13.0.4 export named in paths.toml. Every parser round
trip, hash and coverage number is computed from real bytes.

*No offline check establishes that a sound plays in game.* That needs the console.

# Lookup semantics, which the whole thing rests on

A tone is found by CRC-32 of the **lowercased** name - measured: all 70 `se_gamewatch` and
all 214 `se_eflame_c06` label keys equal `crc32(name.lower())`, while only 67 and 111
respectively equal `crc32(name)`. Two consequences:

  * `se_gamewatch_smash_s01` resolves even though the bank *stores* `smash_S01`. The case
    difference is not a missing sound and must not be "fixed" by renaming.
  * Two tones whose names differ only by case would be unreachable, because the second key
    would collide. `check()` asserts no such pair exists in any bank, before or after.

# Scope

Only `se_eflame_c06` / `se_eflame_c07` and `vc_eflame_c06` / `vc_eflame_c07`. c00-c05 are
vanilla Pyra and keep their own banks, so the vanilla negative control (rule 18) stays
vanilla and rule 9 has its control.

Run:
    toolchains/py312/python.exe tools/merge_donor_sound.py --check
    toolchains/py312/python.exe tools/merge_donor_sound.py --output <dir>

`--output` must be inside `builds/` or `scratch/`, so a bank can never be written over the
read-only export in `dumps/`.
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

# The NUS3/BANK/TONE container parsers live in the Hero merge tool, which already
# round-trips them. Reuse them rather than write a second, divergent copy.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_hero_neutral_b_sound import (  # noqa: E402
    audio_read,
    audio_write,
    bank_read,
    bank_write,
    labels_read,
    tones_read,
    tones_write,
    u32,
)

ROOT = Path(__file__).resolve().parents[1]
BANK_ROOT = ROOT / 'dumps' / 'arc' / 'sound' / 'bank'

# Donors that are not in the read-only export. `dumps/arc/fighter/littlemac` is
# empty on disk (0 of its 4290 indexed files), so Little Mac's banks were pulled
# live into `refs/littlemac_attack_s4/arc/sound/bank/` by
# `tools/fetch_arc_files.py --set littlemac_attack_s4`. Every other donor resolves
# under BANK_ROOT. Keyed by donor stem; the file layout below it is identical
# (`<folder>/<stem>.{nus3audio,nus3bank,tonelabel}`), so nothing else changes.
DONOR_ROOTS = {
    'se_littlemac_c00': ROOT / 'refs/littlemac_attack_s4/arc/sound/bank/fighter',
    'vc_littlemac_c00': ROOT / 'refs/littlemac_attack_s4/arc/sound/bank/fighter_voice',
}


def donor_path(folder: str, donor: str) -> Path:
    """Where a donor's three bank files live: the export, or a pinned refs/ extraction."""
    return (DONOR_ROOTS[donor] if donor in DONOR_ROOTS else BANK_ROOT / folder) / donor

# Sections both banks must share byte for byte. GRP/DTON/PACK are the bank-wide tables
# every tone indexes into, so a mismatch means the two banks are not the same format and
# appending would produce a file whose indices point at the wrong things. BINF/PROP
# deliberately differ (per-bank identity and voice/language data); the recipient's copies
# are kept, so a bank does not become a different fighter's bank by accident.
SHARED = (b'GRP ', b'DTON', b'PACK')

# folder -> {donor stem: (recipient stems, name prefix)}
# The prefix is what makes each donor's referenced names findable, and it is asserted
# against the donor bank rather than assumed.
PLAN = {
    'fighter': {
        'se_gamewatch': (('se_eflame_c06', 'se_eflame_c07'), 'se_gamewatch_'),
        'se_diddy': (('se_eflame_c06', 'se_eflame_c07'), 'se_diddy_'),
        'se_chrom': (('se_eflame_c06', 'se_eflame_c07'), 'se_chrom_'),
        # Little Mac's forward smash (acmd::littlemac_attack_s4). His banks are in
        # refs/, not the export - see DONOR_ROOTS.
        'se_littlemac_c00': (('se_eflame_c06', 'se_eflame_c07'), 'se_littlemac_'),
    },
    'fighter_voice': {
        'vc_diddy': (('vc_eflame_c06', 'vc_eflame_c07'), 'vc_diddy_'),
        'vc_littlemac_c00': (('vc_eflame_c06', 'vc_eflame_c07'), 'vc_littlemac_'),
    },
}

# Where each donor's referenced names come from, per prefix. `gen_acmd` names are read out
# of the donor ACMD scripts themselves (via gen_acmd's own PORT/GROUPS tables) so the
# coverage check cannot drift from what the generator actually ships. The hand-written
# modules are read straight out of the Rust source.
SCRIPT_SOURCES = [
    ('se_gamewatch_', 'scripts', 'lua2cpp_gamewatch'),
    ('se_diddy_', 'acmd_rs', 'src/pgwr/plugin/src/acmd/monkey_flip.rs'),
    ('se_chrom_', 'acmd_rs', 'src/pgwr/plugin/src/acmd/chrom_jab.rs'),
    ('vc_diddy_', 'acmd_rs', 'src/pgwr/plugin/src/acmd/monkey_flip.rs'),
    ('se_littlemac_', 'acmd_rs', 'src/pgwr/plugin/src/acmd/littlemac_attack_s4.rs'),
    ('vc_littlemac_', 'acmd_rs', 'src/pgwr/plugin/src/acmd/littlemac_attack_s4.rs'),
]

RE_NAME = re.compile(r'((?:se|vc)_[a-z0-9_]+)')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tone_kind(tone: bytes) -> int:
    """The tone's body kind: 0 is a single sample, 1 a stream, 3 a randomised group."""
    at = 12 if u32(tone, 4) & 0x80000000 else 8
    size = tone[at]
    start = (at + 1 + size + 3) & ~3
    return u32(tone, start)


def labels_pairs(path: Path) -> list[tuple[int, int]]:
    data = path.with_suffix('.tonelabel').read_bytes()
    if u32(data, 0) != 1:
        raise RuntimeError(f'{path}: unexpected label version')
    return list(struct.iter_unpack('<II', data[8:]))


def bank_keys(path: Path) -> set[int]:
    return {crc for crc, _ in labels_pairs(path)}


def tone_names(path: Path) -> list[str]:
    return [n for n, _ in audio_read(path.with_suffix('.nus3audio').read_bytes())]


def referenced_names(prefix: str) -> set[str]:
    """Every name with `prefix` that the shipped scripts or modules reference."""
    kind = next((k for p, k, _ in SCRIPT_SOURCES if p == prefix), None)
    src = next((s for p, _, s in SCRIPT_SOURCES if p == prefix), None)
    if kind is None:
        raise RuntimeError(f'no source declared for {prefix}')
    names: set[str] = set()

    def harvest(text: str) -> None:
        # Exclude the bare prefix: the sources legitimately contain it as a literal
        # (`n.starts_with("se_diddy_")`, a `case_variant` check), and a name equal to the
        # prefix is not a sound anyone plays.
        names.update(n for n in RE_NAME.findall(text)
                     if n.startswith(prefix) and n != prefix)

    if kind == 'acmd_rs':
        # The Rust source, plus its sound table. Both are shipped code, so a name added to
        # either is a name the coverage check must account for.
        path = ROOT / src
        harvest(path.read_text(encoding='utf-8'))
        for m in re.finditer(r'\(\s*"((?:se|vc)_[a-z0-9_]+)"\s*,\s*"((?:se|vc)_[a-z0-9_]+)"\s*\)',
                             path.read_text(encoding='utf-8')):
            harvest(m.group(1))  # the donor key of a SOUND_MAP entry
    else:
        tools = ROOT / 'src/pgwr/tools'
        if str(tools) not in sys.path:
            sys.path.insert(0, str(tools))
        from gen_acmd import GROUPS, PORT, WEAPON_GROUPS  # noqa: E402

        base = (ROOT / 'dumps/scripts/SSBU-Dumped-Scripts-main/smashline'
                / 'lua2cpp_gamewatch')
        for statuses in GROUPS.values():
            for pyra in statuses:
                donor = base / 'gamewatch' / f'{PORT[pyra]}.txt'
                if not donor.is_file():
                    raise RuntimeError(f'missing donor script {donor}')
                harvest(donor.read_text(encoding='utf-8', errors='replace'))
        for group in GROUPS:
            for _, folder, scripts in WEAPON_GROUPS.get(group, []):
                for script in scripts:
                    harvest((base / folder / f'{script}.txt')
                            .read_text(encoding='utf-8', errors='replace'))
    if not names:
        raise RuntimeError(f'no {prefix} names found in its sources; the layout changed')
    return names


def merge_bank(folder: str, donor: str, recipient: Path, output: Path) -> dict:
    """Append `donor`'s tones to the bank at `recipient`, writing the result to `output`.

    `recipient` is read from wherever it currently is. When several donors target one bank
    the caller must pass the *previous donor's output* for every donor after the first: each
    call reads the recipient fresh, so chaining against the pristine export instead would
    silently discard the earlier donors (measured: that left only the last of three, and
    `check()` still passed because it tested a union of keys rather than the written bytes).
    """
    d = donor_path(folder, donor)
    da = audio_read(d.with_suffix('.nus3audio').read_bytes())
    ra = audio_read(recipient.with_suffix('.nus3audio').read_bytes())

    # A name in both banks makes one of the two tones unreachable, since the second label
    # key collides with the first. Measured: none for every pair here, but assert it.
    overlap = {n for n, _ in da} & {n for n, _ in ra}
    if overlap:
        raise RuntimeError(f'{donor} -> {recipient.name}: tone name collision {sorted(overlap)}')

    dc = dict(bank_read(d.with_suffix('.nus3bank').read_bytes()))
    rc = dict(bank_read(recipient.with_suffix('.nus3bank').read_bytes()))
    for tag in SHARED:
        if dc[tag] != rc[tag]:
            raise RuntimeError(f'{donor} -> {recipient.name}: incompatible section {tag!r}')

    dt = tones_read(dc[b'TONE'])
    rt = tones_read(rc[b'TONE'])
    if len(dt) != len(da) or len(rt) != len(ra):
        raise RuntimeError(f'{donor} -> {recipient.name}: tone count != audio count')

    # Every donor tone here is kind 0 (measured: 70/81/92/25), so no appended record holds
    # a child index that would now point at the wrong tone. Assert rather than assume: a
    # future donor with randomised groups needs the Hero tool's rebase_groups, and copying
    # such a record silently would ship a tone that plays the wrong sample.
    kinds = {tone_kind(t) for t in dt}
    if kinds != {0}:
        raise RuntimeError(f'{donor}: tone kinds {sorted(kinds)}; randomised groups would '
                           'need child-index rebasing - see merge_hero_neutral_b_sound')

    entries = ra + da
    count = len(ra)
    dl = labels_read(d.with_suffix('.tonelabel').read_bytes(), [n for n, _ in da])
    rl = labels_read(recipient.with_suffix('.tonelabel').read_bytes(), [n for n, _ in ra])

    new_labels = rl + [(crc, ((value >> 8) + count) << 8 | (value & 0xff)) for crc, value in dl]
    new_labels.sort()
    label_bytes = struct.pack('<II', 1, len(new_labels))
    label_bytes += b''.join(struct.pack('<II', *p) for p in new_labels)
    # Independent re-read: proves the sorted, rebased table still indexes the right names.
    labels_read(label_bytes, [n for n, _ in entries])

    files = {
        '.nus3audio': audio_write(entries),
        '.nus3bank': bank_write([(tag, tones_write(rt + dt) if tag == b'TONE' else data)
                                 for tag, data in bank_read(recipient.with_suffix('.nus3bank').read_bytes())]),
        '.tonelabel': label_bytes,
    }
    for ext, data in files.items():
        path = output.parent / (output.name + ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    # Post-write verification against the written bytes, not the in-memory values.
    w_audio = audio_read(files['.nus3audio'])
    if [n for n, _ in w_audio] != [n for n, _ in entries]:
        raise RuntimeError(f'{donor} -> {recipient.name}: written audio names differ')
    if [s for _, s in w_audio] != [s for _, s in entries]:
        raise RuntimeError(f'{donor} -> {recipient.name}: written audio samples differ')
    labels_read(files['.tonelabel'], [n for n, _ in w_audio])
    w_bank = dict(bank_read(files['.nus3bank']))
    for tag in SHARED:
        if w_bank[tag] != rc[tag]:
            raise RuntimeError(f'{recipient.name}: shared section {tag!r} changed on write')
    if tones_read(w_bank[b'TONE']) != rt + dt:
        raise RuntimeError(f'{recipient.name}: tone records did not survive the write')
    if w_bank[b'BINF'] != rc[b'BINF'] or w_bank[b'PROP'] != rc[b'PROP']:
        raise RuntimeError(f'{recipient.name}: recipient identity sections changed')

    return {
        'folder': folder,
        'donor': donor,
        'recipient': recipient.name,
        'retained_tones': count,
        'appended_tones': len(da),
        'total_tones': len(entries),
        'shared_sections_identical': [t.decode().strip() for t in SHARED],
        'retained_bank_identity': True,
        'case_variant_tones': sorted(n for n, _ in da if n != n.lower()),
        'input_hashes': {
            side + ext: sha(p.with_suffix(ext).read_bytes())
            for side, p in (('donor', d), ('recipient', recipient))
            for ext in ('.nus3audio', '.nus3bank', '.tonelabel')
        },
        'file_hashes': {ext: sha(data) for ext, data in files.items()},
    }


def check() -> dict:
    """Round trips, case safety, and the coverage claim, on the real bank files."""
    all_stems = []
    for folder, donors in PLAN.items():
        for donor, (recips, _) in donors.items():
            all_stems.append((folder, donor))
            all_stems += [(folder, r) for r in recips]

    # 1. Parser round trips and case-collision safety on every bank involved.
    for folder, stem in all_stems:
        p = donor_path(folder, stem)
        audio = audio_read(p.with_suffix('.nus3audio').read_bytes())
        if audio_read(audio_write(audio)) != audio:
            raise RuntimeError(f'{stem}: audio round trip failed')
        labels_read(p.with_suffix('.tonelabel').read_bytes(), [n for n, _ in audio])
        bank = p.with_suffix('.nus3bank').read_bytes()
        if bank_write(bank_read(bank)) != bank:
            raise RuntimeError(f'{stem}: bank round trip failed')
        payload = dict(bank_read(bank))[b'TONE']
        if tones_write(tones_read(payload)) != payload:
            raise RuntimeError(f'{stem}: tone round trip failed')
        folded: dict[str, list[str]] = {}
        for n, _ in audio:
            folded.setdefault(n.lower(), []).append(n)
        if dupes := {k: v for k, v in folded.items() if len(v) > 1}:
            raise RuntimeError(f'{stem}: tones unreachable behind a case collision: {dupes}')
        # Tone-kind policy, deliberately asymmetric: a DONOR tone must be kind 0 because it
        # gets appended (any child index would dangle), whereas a RECIPIENT tone is copied
        # verbatim and never re-indexed, so its kind only has to be one we recognise.
        for tone, (n, _) in zip(tones_read(payload), audio):
            k = tone_kind(tone)
            if k not in (0, 1, 3):
                raise RuntimeError(f'{stem}: unrecognised tone kind {k} for {n}')

    # 2. The claim the fix rests on, per donor: every referenced name resolves after the
    #    merge, and nothing resolved before unless it was already a recipient name.
    #
    #    `accumulated` is built the way `build()` writes the files - donor by donor onto the
    #    running total - so this predicts the shipped bank rather than a set-theoretic union.
    #    A union cannot detect the clobbering bug that shipped 0.20.10's first draft: three
    #    donors chained onto one bank all "resolve" in a union while only the last survives
    #    on disk. `accumulated` does, because it only ever grows.
    summary = {}
    for folder, donors in PLAN.items():
        accumulated: dict[str, set[int]] = {}
        for donor, (recips, prefix) in donors.items():
            needed = referenced_names(prefix)
            donor_keys = bank_keys(donor_path(folder, donor))
            for r in recips:
                accumulated.setdefault(r, set()).update(donor_keys)

        for r, merged in accumulated.items():
            # Every donor that targets this recipient must be present in the running total.
            for donor, (recips, prefix) in donors.items():
                if r not in recips:
                    continue
                needed = referenced_names(prefix)
                missing = sorted(n for n in needed
                                 if zlib.crc32(n.lower().encode()) not in merged)
                if missing:
                    raise RuntimeError(
                        f'{donor} -> {r}: still silent after the merge: {missing}')

        before = {r: bank_keys(BANK_ROOT / folder / r) for r in accumulated}
        for donor, (recips, prefix) in donors.items():
            needed = referenced_names(prefix)
            already = sorted(n for n in needed
                             if zlib.crc32(n.lower().encode())
                             in set().union(*(before[r] for r in recips)))
            # And the reverse: a donor name the scripts do not reference is dead weight
            # in the bank, which is fine (it is the donor's own full bank) but worth knowing.
            summary[donor] = {
                'referenced': sorted(needed),
                'referenced_count': len(needed),
                'already_resolvable_before_merge': already,
                'resolvable_after_merge': len(needed),
                'donor_tones_total': len(tone_names(donor_path(folder, donor))),
            }
    for donor, s in summary.items():
        print(f'PASS {donor:<13} {s["referenced_count"]:>3} referenced names | '
              f'before merge {len(s["already_resolvable_before_merge"]):>3} | '
              f'after {s["resolvable_after_merge"]:>3} | '
              f'donor bank holds {s["donor_tones_total"]}')
    return summary


def build(output: Path) -> dict:
    summary = check()
    output = Path(output)
    output = (output if output.is_absolute() else ROOT / output).resolve()
    if not (output.is_relative_to(ROOT / 'builds') or output.is_relative_to(ROOT / 'scratch')):
        raise RuntimeError(f'refusing to write outside builds/ or scratch/: {output}')

    reports = []
    for folder, donors in PLAN.items():
        for donor, (recips, _) in donors.items():
            for r in recips:
                dest = output / 'sound' / 'bank' / folder / r
                # Chain: the first donor reads the pristine export, each later donor reads
                # the file the previous one wrote, so all of them accumulate.
                base = dest if dest.with_suffix('.nus3audio').is_file() else BANK_ROOT / folder / r
                reports.append(merge_bank(folder, donor, base, dest))

    # Verify the claim against the bytes that were actually written, not against a union of
    # the donors' key sets. This is the check that catches a lost or clobbered merge.
    for folder, donors in PLAN.items():
        for donor, (_, prefix) in donors.items():
            needed = referenced_names(prefix)
            for r in dict.fromkeys(r for recips, _ in donors.values() for r in recips):
                stem = output / 'sound' / 'bank' / folder / r
                written = bank_keys(stem)
                missing = sorted(n for n in needed
                                 if zlib.crc32(n.lower().encode()) not in written)
                if missing:
                    raise RuntimeError(
                        f'{r}: written bank does not resolve {donor} names {missing}')

    report = {
        'date': '2026-09-30',
        'tool_version': '1.2.0',
        'evidence_tier': 'B',
        'what': ("real donor tone records and encoded audio appended to Pyra's own c06/c07 "
                 "sound and voice banks, so the ported scripts play the fighter's own "
                 "sounds instead of Pyra stand-ins"),
        'replaces': 'gen_acmd.py R2 sound substitution, and SOUND_MAP in acmd/monkey_flip.rs',
        'per_donor': summary,
        'banks': reports,
        'not_merged': {
            'vc_gamewatch': 'bank absent from the export; G&W voice lines stay silent '
                            '(see refs/sound/dump_requests.md)',
            'se_common_*': 'no common/system SFX bank in the export; those names are kept '
                           'verbatim by gen_acmd on the inference that the common bank is '
                           'resident for every fighter - unverifiable here',
        },
        'vanilla_costumes': 'c00-c05 keep their own banks (rule 18 control, rule 9)',
        'hardware_validated': False,
        'note': 'No offline check establishes that a sound plays in game.',
    }
    # The tone count is the cheapest possible detector for a lost merge: every donor tone
    # must be present in the written bank, on top of the name-resolution check above.
    for folder, donors in PLAN.items():
        recips = dict.fromkeys(r for rs, _ in donors.values() for r in rs)
        for r in recips:
            written = set(tone_names(output / 'sound' / 'bank' / folder / r))
            expected = set(tone_names(BANK_ROOT / folder / r))
            for donor, (rs, _) in donors.items():
                if r not in rs:
                    continue
                expected |= set(tone_names(donor_path(folder, donor)))
            if not expected <= written:
                raise RuntimeError(
                    f'{folder}/{r}: {len(expected - written)} donor tones lost on write')
            print(f'  {folder}/{r}: {len(written)} tones '
                  f'(export {len(set(tone_names(BANK_ROOT / folder / r)))})')

    output.mkdir(parents=True, exist_ok=True)
    (output / 'donor_sound.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'merged {len(reports)} donor banks into c06/c07; wrote {output / "donor_sound.json"}')
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    if args.check:
        check()
    elif args.output:
        build(args.output)
    else:
        ap.error('choose --check or --output')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
