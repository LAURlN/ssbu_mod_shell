"""Merge genuine Little Mac fist resources into owned Pyra slot banks (v2.1.0).

Uses the repaired Hero converter and dependency-preserving merge. Missing inputs
or unsupported external models/variants stop packaging. No donor-folder copy or
vanilla-bank override is generated. Runtime appearance requires console review.

The recipient is the vanilla `effect/fighter/eflame/ef_eflame.eff`, read either
from the workspace or from the read-only ARC export named by paths.toml
`[dumps] arc`; it is only ever read, never written. The two requested emitters
carry a G3PR model whose id 1347192488 is also used by a *different* Pyra mesh,
so the merge relocates that model id and its name (see
merge_hero_neutral_b_effects.MODEL_REFERENCE_FIELDS).

Usage: python tools/build_littlemac_fsmash_effect.py --mod builds/.../mod
       [--recipient <ef_eflame.eff>] [--generated-dir builds/.../generated_effects]
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import merge_hero_neutral_b_effects as merge_effects

ROOT = Path(__file__).resolve().parents[1]
DONOR = ROOT / 'refs/littlemac_attack_s4/arc/effect/fighter/littlemac/ef_littlemac.eff'
DONOR_SHA256 = 'c2f33cdb2157be04d80940182aced6ae762c004f9b08ea4ec3929749ea2b2228'
REQUIRED_EMITTERS = ('LITTLEMAC_ATTACK_LINE', 'LITTLEMAC_ATTACK_ARC')
REQUIRED_KINDS = ('littlemac_attack_line', 'littlemac_attack_arc')
# Converter work directories. They are content-addressed inside this root, so
# two concurrent builds cannot see each other's output, and they stay out of the
# package tree (rule 5).
SCRATCH = ROOT / 'builds/.cache/effect_merge_scratch'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(cond, msg):
    if not cond:
        raise RuntimeError(msg)

def eff_names(path):
    # Preserve the public reader used by existing audit tools.
    import re
    raw = Path(path).read_bytes()
    end = raw.find(b'VFXB')
    require(end > 0, f'{path}: no VFXB marker')
    return [x[:-1].decode('ascii') for x in re.findall(rb'[A-Za-z0-9_.-]{4,}\x00', raw[:end])]

def check_inputs():
    """Smoke test: every input the merge needs, and nothing that would be
    silently wrong. Cheap enough to run before every packaging session."""
    import merge_hero_neutral_b_effects as merge
    arc = Path(merge.ARC)
    vanilla = arc / 'effect/fighter/eflame/ef_eflame.eff'
    require(vanilla.is_file(),
            f'vanilla recipient not found at {vanilla}; point paths.toml [dumps] arc at an export that has it')
    require(DONOR.is_file() and sha(DONOR) == DONOR_SHA256, 'Pinned Little Mac donor missing or changed')
    require(merge.CONVERTER.is_file(),
            f'converter not built: run python tools/build_hero_effect_converter.py --from-source')
    require(all(n in eff_names(DONOR) for n in REQUIRED_EMITTERS), 'Pinned donor lacks requested resources')
    # The declaration in build.py must be a new file, not a base-game duplicate.
    for slot in ('c06', 'c07'):
        rel = f'effect/fighter/eflame/ef_eflame_{slot}.eff'
        require(not (arc / rel).exists(), f'{rel} exists in the base game; it is not a new file')
    # The retired payload is a real ARC path, which is why shipping it was wrong
    # twice over: unreachable for eflame, and a duplicate of a base-game file.
    # Reported, not required: this export carries an empty littlemac folder.
    donor_in_export = (arc / 'effect/fighter/littlemac/ef_littlemac.eff').is_file()
    print(f'PASS: donor {DONOR_SHA256[:12]}, vanilla recipient {sha(vanilla)[:12]}, converter present, '
          f'both slot banks are new files')
    return {'donor_sha256': DONOR_SHA256, 'vanilla_recipient_sha256': sha(vanilla),
            'converter_sha256': sha(merge.CONVERTER), 'emitters': list(REQUIRED_EMITTERS),
            'retired_donor_bank_present_in_export': donor_in_export}


def build(mod_dir, *, recipient=None, generated_dir=None):
    mod_dir = Path(mod_dir).resolve()
    require(mod_dir.is_relative_to(ROOT / 'builds'), 'Output must be an isolated builds/ tree')
    source = Path(recipient).resolve() if recipient else merge_effects.ARC / 'effect/fighter/eflame/ef_eflame.eff'
    lab = ROOT.parents[1]
    # The vanilla bank is an input only. It may come from the workspace or from
    # the read-only export named by paths.toml; nothing is ever written to it.
    arc_export = Path(merge_effects.ARC).resolve()
    inside_lab = source.resolve().is_relative_to(lab)
    inside_arc = source.resolve().is_relative_to(arc_export)
    require(inside_lab or inside_arc,
            'Recipient must be inside the workspace or inside the read-only ARC export named by paths.toml [dumps] arc')
    require(source.is_file(), 'Missing original effect/fighter/eflame/ef_eflame.eff; export it and configure dumps.arc or pass --recipient')
    require(DONOR.is_file() and sha(DONOR) == DONOR_SHA256, 'Pinned Little Mac donor missing or changed')
    require(merge_effects.CONVERTER.is_file(), 'Missing repaired EffectConverter; see tools/build_hero_effect_converter.py and paths.toml')
    require(all(n in eff_names(DONOR) for n in REQUIRED_EMITTERS), 'Pinned donor lacks requested resources')
    generated = Path(generated_dir).resolve() if generated_dir else mod_dir.parent / 'generated_effects'
    require(generated.is_relative_to(ROOT / 'builds'), 'Generated effects must stay in builds/')
    records = {}
    # Finish both merges before changing either staged recipient bank.
    for slot in ('c06', 'c07'):
        baseline = mod_dir / f'effect/fighter/eflame/ef_eflame_{slot}.eff'
        # Chain onto existing owned banks rather than discarding earlier effects.
        target = baseline if baseline.is_file() else source
        output = generated / f'ef_eflame_{slot}.eff'
        require(output != target, 'Generated output must differ from recipient input')
        merge_effects.merge(target, output, donor_file=DONOR,
                           effect_names=REQUIRED_EMITTERS, donor_sha256=DONOR_SHA256,
                           scratch=SCRATCH)
        records[slot] = json.loads(output.with_suffix('.merge.json').read_text())
        records[slot]['output'] = baseline.relative_to(mod_dir).as_posix()
        records[slot]['chained_onto_owned_bank'] = baseline.is_file()
    for slot in records:
        dest = mod_dir / records[slot]['output']
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(generated / dest.name, dest)
    # Retire only the obsolete deployment payload; keep the pinned refs donor.
    obsolete = mod_dir / 'effect/fighter/littlemac/ef_littlemac.eff'
    retired = None
    if obsolete.is_file():
        retired = sha(obsolete)
        obsolete.unlink()
    require(not (mod_dir / 'effect/fighter/littlemac/ef_littlemac.eff').exists(),
            'the misplaced donor-folder bank is still shipped')
    return {'tool_version': '2.1.0', 'donor_sha256': DONOR_SHA256,
            'vanilla_recipient': source.relative_to(arc_export).as_posix() if inside_arc
                                 else source.relative_to(lab).as_posix(),
            'vanilla_recipient_sha256': sha(source),
            'required_emitters': list(REQUIRED_EMITTERS), 'slots': records,
            'retired_donor_folder_bank_sha256': retired,
            'donor_folder_bank_shipped': False,
            'hardware_validated': False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--recipient', type=Path)
    parser.add_argument('--generated-dir', type=Path)
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check_inputs(), indent=2))
    elif args.mod:
        print(json.dumps(build(args.mod, recipient=args.recipient,
                               generated_dir=args.generated_dir), indent=2))
    else:
        parser.error('choose --check or --mod')
