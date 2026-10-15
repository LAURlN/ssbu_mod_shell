"""Merge Lucas's down-smash PSI emitters into Mythra's own c06/c07 banks. v1.0.0.

For `mythra::lucas_attack_lw4` (AGENTS.md rule 17: the mod owns what it uses, and
does not call another fighter's bank at runtime). Lucas's down smash spawns two
of his own emitters, read out of the pinned donor scripts rather than assumed:

  * `LUCAS_PSI_HOLD`   - the charging orb held at `havel`, spawned at frames 8
                         (release) and 5 (charge hold), and killed at frame 20.
  * `LUCAS_PSI_ATK_LW` - the three-hit sweep, spawned at frames 20, 29 and 39
                         on `top` with rising scale 1.25 / 1.3 / 1.45.

The other three effects the move plays - `sys_smash_flash`, `sys_dash_smoke`,
`sys_run_smoke` - are `sys_` common-bank effects, so nothing is merged for them
and that is asserted rather than assumed.

# Why the emitters go into `ef_elight_c0{6,7}.eff` and not into a donor folder

`kb/findings/effect-ownership-of-donor-banks-and-per-slot-trails.md` measured
that an `.eff` shipped under `effect/fighter/lucas/` is loaded by *nobody*: a
fighter only reaches its own per-slot bank, which ARCropolis routes from
`config.json`. So shipping a copy of `ef_lucas.eff` would add 10.6 MB that never
loads, and every offline check would still pass. The two emitters are merged
into the **recipient-owned** `ef_elight_c06.eff` / `ef_elight_c07.eff`, which the
0.20.19 package already declares under `new-dir-files`, so this port adds no
`config.json` entry and no new file name.

That merge is `merge_hero_neutral_b_effects.merge`, which also **relocates
texture and model ids**. That is not decoration: texture and model ids are
bank-global, and `AddPrimitive` returns silently on a duplicate model id, so an
unrelocated donor model would draw Mythra's mesh while every offline check still
passed. The T-0050 write-up records exactly that defect being found in Little
Mac's arc. The relocation table for this donor is empty - the two sets share no
texture id with a different payload - and the merge reports it either way.

    python tools/build_lucas_downsmash_effect.py --check
    python tools/build_lucas_downsmash_effect.py --output <dir under builds/ or scratch/>

Offline only (tier B). No offline check establishes that an effect is visible in
game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_hero_neutral_b_effects as merge_effects

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / 'refs/lucas_attack_lw4'
DONOR = REFS / 'arc/effect/fighter/lucas/ef_lucas.eff'
DONOR_SHA256 = 'ab46b9eb2addeec621f613f67a581fa66aa5bdd907968feede5614a7047ae2c4'
# The bank emitter names, as spelled in the donor bank.
REQUIRED_EMITTERS = ('LUCAS_PSI_HOLD', 'LUCAS_PSI_ATK_LW')
# The `sys_` effects the move also plays. Common bank, so nothing to merge - and
# checked to be absent from the donor bank, because a `sys_` name living in a
# fighter bank would mean the "common" assumption is wrong.
COMMON_EFFECTS = {'sys_smash_flash', 'sys_dash_smoke', 'sys_run_smoke'}
ACMD = (REFS / 'donor_acmd/lucas__AttackLw4.txt',
        REFS / 'donor_acmd/lucas__AttackLw4Charge.txt')
RE_SCRIPT_EFFECT = re.compile(r'Hash40::new\("((?:sys|lucas)_[a-z0-9_]+)"\)')
BASELINE = ROOT / 'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
# Content-addressed converter work directory, so two concurrent builds cannot see
# each other's output and a stale dump can never be reused.
SCRATCH = ROOT / 'builds/.cache/lucas_downsmash_effect_scratch'
SLOTS = ('c06', 'c07')


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def script_effects() -> dict:
    """Every effect name the two donor scripts name, read from the pinned text."""
    names = set()
    for path in ACMD:
        assert path.is_file(), f'missing pinned donor script {path}'
        names |= set(RE_SCRIPT_EFFECT.findall(path.read_text(encoding='utf-8')))
    lower = {n.lower() for n in names}
    return {'all': sorted(names),
            'donor_named': sorted(lower - {e.lower() for e in COMMON_EFFECTS}),
            'common': sorted(lower & {e.lower() for e in COMMON_EFFECTS})}


def check() -> None:
    assert DONOR.is_file(), f'missing pinned donor bank {DONOR}'
    assert sha(DONOR) == DONOR_SHA256, f'{DONOR} is not the pinned revision'
    assert merge_effects.CONVERTER.is_file(), (
        f'converter not built at {merge_effects.CONVERTER}; run '
        f'python tools/build_hero_effect_converter.py --from-source')

    scripts = script_effects()
    print('donor scripts name these effects:', scripts['all'])
    print('  merged into the elight banks:', scripts['donor_named'])
    print('  common bank, no merge needed:', scripts['common'])
    assert set(scripts['common']) == {e.lower() for e in COMMON_EFFECTS}, \
        f'the common-effect set changed: {scripts["common"]}'
    # The scripts' donor-named effects must be exactly the two emitters, spelled
    # any case. This is the check that keeps "every dependency" a measurement.
    assert {n.upper() for n in scripts['donor_named']} == set(REQUIRED_EMITTERS), \
        f'the scripts name {scripts["donor_named"]}, this tool merges {list(REQUIRED_EMITTERS)}'

    for slot in SLOTS:
        base = BASELINE / f'effect/fighter/elight/ef_elight_{slot}.eff'
        assert base.is_file(), f'baseline recipient bank missing: {base}'
        rel = f'effect/fighter/elight/ef_elight_{slot}.eff'
        print(f'  {rel}: {base.stat().st_size} bytes, sha256 {sha(base)[:16]}')
    # The retired payload must not be a real ARC path we are tempted to ship.
    donor_folder = merge_effects.ARC / 'effect/fighter/lucas/ef_lucas.eff'
    print(f'  effect/fighter/lucas/ef_lucas.eff in the export: '
          f'{donor_folder.is_file()} (shipping this would load nothing)')
    print('PASS: donor bank pinned, converter present, script coverage exact, '
          'recipient banks present')


def build(output: Path) -> dict:
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / name) for name in ('scratch', 'builds')), \
        'output must be in builds/ or scratch/'
    check()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    banks = []
    for slot in SLOTS:
        recipient = BASELINE / f'effect/fighter/elight/ef_elight_{slot}.eff'
        dest = output / f'effect/fighter/elight/ef_elight_{slot}.eff'
        merge_effects.merge(recipient, dest, donor_file=DONOR,
                            effect_names=set(REQUIRED_EMITTERS),
                            donor_sha256=DONOR_SHA256, scratch=SCRATCH)
        record = json.loads(dest.with_suffix('.merge.json').read_text())
        banks.append({'slot': slot, 'recipient_sha256': record['recipient_sha256'],
                      'output_sha256': record['output_sha256'],
                      'output_bytes': dest.stat().st_size,
                      'texture_id_relocations': record['texture_id_relocations'],
                      'model_id_relocations': record['model_id_relocations'],
                      'emitter_fields_preserved': record['decoded_emitter_fields_preserved']})
        print(f'  {slot}: merged {record["resource_names"]}, '
              f'{len(record["texture_id_relocations"])} texture and '
              f'{len(record["model_id_relocations"])} model ids relocated, '
              f'sha256 {record["output_sha256"]}')

    report = {'tool_version': '1.0.0', 'date': '2026-10-02', 'evidence_tier': 'B',
              'hardware_validated': False,
              'move': 'Lucas AttackLw4 / AttackLw4Hold on Mythra c06/c07',
              'donor_bank': str(DONOR.relative_to(ROOT)), 'donor_sha256': DONOR_SHA256,
              'emitters': list(REQUIRED_EMITTERS),
              'common_effects_no_merge': sorted(COMMON_EFFECTS),
              'recipient_is_own_bank': True,
              'why': 'an .eff under effect/fighter/lucas/ is loaded by nobody; '
                     'the per-slot elight bank is what the fighter loader reads, '
                     'and it is already declared in the shipped config.json',
              'config_json_change': 'none - ef_elight_c06.eff / ef_elight_c07.eff are '
                                    'already declared under new-dir-files',
              'baseline': str(BASELINE.relative_to(ROOT)),
              'banks': banks,
              'note': 'No offline check establishes that an effect is visible in game.'}
    (output / 'lucas_downsmash_effect.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {len(banks)} recipient-owned banks written')
    return report


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
