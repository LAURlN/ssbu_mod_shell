"""Merge Ness's back-throw PSI emitter into the recipient-owned Mythra banks.

Version 1.0.0. Thin, task-owned driver over `merge_hero_neutral_b_effects.merge`,
which is the merge engine and its evidence discipline (id relocation, re-export
field comparison, negative controls). This file supplies Ness's inputs and the
one resource his back throw names; it does not reimplement any of the merge.

Why the merge at all
--------------------
`effect_throwb` spawns `ness_psi_rush` ten times. That name lives in
`effect/fighter/ness/ef_ness.eff`, and the loader only ever searches the
*requesting* fighter's own folder (handbook/10, measured on
main+0x355f66c). Filing Ness's bank under `effect/fighter/ness/` would ship
12 MB that an `elight` fighter never loads, and the throw would animate and hit
with no PSI drawn - the silent no-op shape. So `NESS_PSI_RUSH` is merged into
`ef_elight_c06.eff` / `ef_elight_c07.eff`, which is what Mythra c06/c07 load.

`sys_run_smoke` and `sys_smash_flash_s` are **not** merged: they are common-bank
effects every fighter requests, and the donor names them for that reason.

Usage
-----
    python -B tools/merge_ness_throw_effects.py --check
    python -B tools/merge_ness_throw_effects.py \
        --recipient <ef_elight_c06.eff> --output <merged.eff> [--scratch DIR]

Both slots are identical inputs here, so one invocation per slot is correct.
Evidence tier: **B** for bytes, **D** for whether the emitter draws in game.
No emulator, no console, no install is performed by this tool.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import merge_hero_neutral_b_effects as engine  # noqa: E402

# The complete donor-resource set of Ness's back throw. `NESS_PSI_RUSH` is the
# only donor-owned one; the other two names in the script are common effects and
# are asserted absent from the donor bank so this set cannot silently grow.
DONOR_RESOURCES = ('NESS_PSI_RUSH',)
COMMON_RESOURCES = ('sys_run_smoke', 'sys_smash_flash_s')

# effect/fighter/ness/ef_ness.eff, extracted 2026-10-02 from the local 13.0.4
# data.arc (sha256 of the archive itself: ef615e671e1d4907f0a707f2eb13e3cb
# c8539c4e67ac51c89ef547c22b82995, 17,600,869,448 B).
DONOR_ARC_PATH = 'effect/fighter/ness/ef_ness.eff'
DONOR_SHA256 = '5aab79ed940d085398b45f6b1b39cd593237572998d64b4ef14f4ff817929595'
DONOR_BYTES = 12497408

# Recorded 2026-10-02 from the donor's own NamcoFile.json (34 emitters). Kept so
# the tool refuses a donor bank whose emitter set changed underneath it.
DONOR_EMITTER_COUNT = 34

# The donor emitter's own decoded record, pinned. If the archive ever yields a
# different record for NESS_PSI_RUSH, stop rather than ship a silently different
# effect. Fields are the ones the merge engine round-trips.
DONOR_ENTRY_FIELDS = {
    'Name': 'NESS_PSI_RUSH',
    'ExternalModelFlag': 0,
    'Variants': [],
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def candidate_donors(arc_root=None):
    """Where the pinned donor bank may live, most authoritative first."""
    out = []
    if arc_root:
        out.append(Path(arc_root) / DONOR_ARC_PATH)
    out.append(ROOT.parents[1] / 'gamedata/ssbu-13.0.4/files' / DONOR_ARC_PATH)
    try:
        cfg = tomllib.loads((ROOT / 'paths.toml').read_text(encoding='utf-8'))
        arc = cfg['dumps'].get('arc')
        if arc:
            out.append(Path(arc) / DONOR_ARC_PATH)
    except Exception:  # noqa: BLE001 - paths.toml is optional input here
        pass
    return out


def find_donor(arc_root=None):
    for path in candidate_donors(arc_root):
        if path.is_file() and sha(path) == DONOR_SHA256:
            return path
    raise RuntimeError(
        f'no copy of {DONOR_ARC_PATH} at pinned sha256 {DONOR_SHA256}.\n'
        '  re-pull with (workspace root):\n'
        '    tools/arc-extract/target/release/arc-extract.exe \\\n'
        '      --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/ssbu-13.0.4/files \\\n'
        f'      {DONOR_ARC_PATH}')


def check(arc_root=None):
    """Verify the toolchain, the donor pin and the resource split. Writes nothing."""
    assert engine.CONVERTER.is_file(), f'missing configured converter {engine.CONVERTER}'
    donor = find_donor(arc_root)
    assert donor.stat().st_size == DONOR_BYTES, donor.stat().st_size
    names = donor_emitters(donor, scratch_check_only=True)
    assert len(names) == DONOR_EMITTER_COUNT, (len(names), DONOR_EMITTER_COUNT)
    for wanted in DONOR_RESOURCES:
        assert wanted in names, f'{wanted} is not in the donor bank'
    # The two common effects must NOT be donor-owned: if they ever appear in
    # ef_ness.eff the split recorded in the module docstring is wrong.
    for common in COMMON_RESOURCES:
        assert common not in names, (common, 'is donor-owned after all; re-audit')
    record = donor_entry(donor)
    for key, value in DONOR_ENTRY_FIELDS.items():
        assert record.get(key) == value, (key, record.get(key), value)
    print(f'PASS: converter present; donor {donor.name} sha256 {sha(donor)[:16]}... '
          f'with {len(names)} emitters; {list(DONOR_RESOURCES)} donor-owned and '
          f'{list(COMMON_RESOURCES)} common')


def _dump(path, scratch):
    return engine.dump(path, Path(scratch))


def donor_emitters(donor, scratch_check_only=False):
    """The donor bank emitter names, decoded once through the pinned converter."""
    import tempfile
    with tempfile.TemporaryDirectory(dir=str(_scratch_root())) as tmp:
        folder = _dump(donor, tmp)
        entries = json.loads((folder / 'NamcoFile.json').read_text())
        return [e['Name'] for e in entries]


def donor_entry(donor):
    import tempfile
    with tempfile.TemporaryDirectory(dir=str(_scratch_root())) as tmp:
        folder = _dump(donor, tmp)
        entries = json.loads((folder / 'NamcoFile.json').read_text())
        return next(e for e in entries if e['Name'] == 'NESS_PSI_RUSH')


def _scratch_root():
    path = ROOT / 'scratch/2026-10-02_buffy/ness_throw_b/eff_merge_scratch'
    path.mkdir(parents=True, exist_ok=True)
    return path


def merge(recipient, output, arc_root=None, scratch=None):
    donor = find_donor(arc_root)
    engine.merge(recipient, output,
                 donor_file=donor,
                 effect_names=set(DONOR_RESOURCES),
                 donor_sha256=DONOR_SHA256,
                 scratch=str(scratch) if scratch else str(_scratch_root()))
    # Re-label the record so this delta is not mistaken for a Hero merge, and
    # record the inputs it was built from. The engine's own checks already ran.
    record_path = Path(output).with_suffix('.merge.json')
    record = json.loads(record_path.read_text())
    record.update({
        'tool': 'tools/merge_ness_throw_effects.py 1.0.0',
        'move': "vanilla Ness back throw (throw_b) on Mythra (elight) c06/c07",
        'donor_arc_path': DONOR_ARC_PATH,
        'donor_arc_sha256': DONOR_SHA256,
        'donor_emitter_count': DONOR_EMITTER_COUNT,
        'common_resources_not_merged': list(COMMON_RESOURCES),
        'recipient_slot': Path(recipient).parent.name,
        'hardware_validated': False,
    })
    record_path.write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--recipient', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--arc-root', type=Path)
    parser.add_argument('--scratch', type=Path)
    args = parser.parse_args()
    if args.check:
        check(args.arc_root)
    elif args.recipient and args.output:
        record = merge(args.recipient, args.output, args.arc_root, args.scratch)
        print(f'merged into {args.output} sha256 {record["output_sha256"]}; '
              f'texture relocations {len(record["texture_id_relocations"])}, '
              f'model relocations {len(record["model_id_relocations"])}')
    else:
        parser.error('choose --check, or --recipient and --output')


if __name__ == '__main__':
    main()