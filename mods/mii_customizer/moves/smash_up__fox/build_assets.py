#!/usr/bin/env python3
"""Build game assets for MV-smash_up__fox (Fox's up smash and its charge on Mii Gunner).

Run from the workspace root (python -I, stdlib + ssbh_data_py + numpy):

    python -I mods/mii_customizer/moves/smash_up__fox/build_assets.py

Inputs: Fox's and the Gunner's files from the user's data.arc, extracted with tools/arc-extract into
gamedata/mii_customizer/moves/smash_up__fox/{donor,recipient}/ when missing (exact ARC paths).

Outputs, all under gamedata/mii_customizer/moves/smash_up__fox/:
  package/fighter/miigunner/motion/body/c00/c01mcfoxattackhi4.nuanmb
  package/fighter/miigunner/motion/body/c00/c01mcfoxattackhi4charge.nuanmb
        Fox's c04attackhi4 / c04attackhi4charge retargeted onto the Gunner skeleton (retarget.py, the recipe of
        MV-aerial_forward__cloud: name intersection, world-space limbs, Rot ground correction).
  reference/motion_list_vanilla_plus_owned.bin
        vanilla Gunner motion list + ONLY this unit's two entries (mc_fox_attack_hi4, mc_fox_attack_hi4_hold).
        Donor flags, blend, size and cancel fields are copied from Fox's attack_hi4 / attack_hi4_hold entries.
  tables/build_report.json   the retarget reports (dropped donor nodes, limb gate, ground correction, ...)
  manifest.json              hashes of everything above and of the inputs

The coordinator merges the reference entries into the shared motion list; nothing here writes config.json or
any shared file.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

UNIT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT_DIR))
import retarget as rt  # noqa: E402
from retarget_common import (WORKSPACE, G, ARC, hash40, sha256, rel, parse_mlist, owned_entry,  # noqa: E402
                             build_reference_list, entry_cancel)

UNIT = 'smash_up__fox'
OUT = G / 'moves' / UNIT
DONOR_ROOT = OUT / 'donor'
RECIPIENT_ROOT = OUT / 'recipient'
PACKAGE = OUT / 'package'
BODY = PACKAGE / 'fighter/miigunner/motion/body/c00'
REFERENCE = OUT / 'reference/motion_list_vanilla_plus_owned.bin'
VANILLA_LIST = G / 'P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin'
DONOR_LIST = DONOR_ROOT / 'fighter/fox/motion/body/c00/motion_list.bin'
DONOR_IDLE = DONOR_ROOT / 'fighter/fox/motion/body/c00/a00wait1.nuanmb'
DONOR_SKEL = DONOR_ROOT / 'fighter/fox/model/body/c00/model.nusktb'
RECIPIENT_IDLE = RECIPIENT_ROOT / 'fighter/miigunner/motion/body/c00/a00wait1.nuanmb'
GUNNER_SKEL = G / 'P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb'
ARC_EXTRACT = WORKSPACE / 'tools/arc-extract/target/release/arc-extract.exe'

# owned kind -> (donor kind, donor clip, owned clip, script suffix, Trans scale, limbs must move)
CLIPS = {
    'mc_fox_attack_hi4': ('attack_hi4', 'c04attackhi4.nuanmb', 'c01mcfoxattackhi4.nuanmb',
                          'mcfoxattackhi4', 1.0, True),
    'mc_fox_attack_hi4_hold': ('attack_hi4_hold', 'c04attackhi4charge.nuanmb', 'c01mcfoxattackhi4charge.nuanmb',
                               'mcfoxattackhi4charge', 1.0, True),
}

DONOR_INPUTS = ['fighter/fox/motion/body/c00/motion_list.bin', 'fighter/fox/motion/body/c00/a00wait1.nuanmb',
                'fighter/fox/motion/body/c00/c04attackhi4.nuanmb', 'fighter/fox/motion/body/c00/c04attackhi4charge.nuanmb',
                'fighter/fox/model/body/c00/model.nusktb']
RECIPIENT_INPUTS = ['fighter/miigunner/motion/body/c00/a00wait1.nuanmb']


def ensure_inputs() -> None:
    """Extract the inputs that are missing on disk (exact ARC paths, read-only archive)."""
    for root, paths in ((DONOR_ROOT, DONOR_INPUTS), (RECIPIENT_ROOT, RECIPIENT_INPUTS)):
        missing = [p for p in paths if not (root / p).is_file()]
        if not missing:
            continue
        if not ARC_EXTRACT.is_file() or not ARC.is_file():
            raise RuntimeError(f'cannot extract {missing}: need {rel(ARC_EXTRACT)} and {rel(ARC)}')
        r = subprocess.run([str(ARC_EXTRACT), '--arc', str(ARC), '--out', str(root)] + missing,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f'arc-extract failed: {r.stdout[-400:]} {r.stderr[-400:]}')


def main() -> int:
    ensure_inputs()
    for p in (DONOR_LIST, DONOR_IDLE, DONOR_SKEL, RECIPIENT_IDLE, VANILLA_LIST, GUNNER_SKEL):
        if not p.is_file():
            raise RuntimeError(f'missing input {rel(p)}')

    if PACKAGE.exists():  # this unit's own package folder only
        shutil.rmtree(PACKAGE)
    BODY.mkdir(parents=True)

    _, _, donor_entries = parse_mlist(DONOR_LIST.read_bytes())
    by_kind = {e['kind']: e for e in donor_entries}
    report = {}
    raws = []
    for owned_kind, (donor_kind, donor_clip, owned_clip, suffix, trans_scale, need_limbs) in CLIPS.items():
        e = by_kind[hash40(donor_kind)]
        if e['anims'] != (hash40(donor_clip),):
            raise RuntimeError(f'donor {donor_kind} does not name {donor_clip}')
        donor_clip_path = DONOR_ROOT / 'fighter/fox/motion/body/c00' / donor_clip
        rep = rt.retarget(DONOR_IDLE, DONOR_SKEL, RECIPIENT_IDLE, donor_clip_path, BODY / owned_clip,
                          trans_scale=trans_scale, require_limb_motion=need_limbs, recipient_skel=GUNNER_SKEL)
        raw = owned_entry(e, owned_kind, owned_clip, suffix)
        raws.append(raw)
        rep['motion_entry'] = {
            'owned_kind': owned_kind, 'owned_kind_hash': f'0x{hash40(owned_kind):010x}',
            'donor_kind': donor_kind, 'donor_clip': donor_clip, 'donor_clip_sha256': sha256(donor_clip_path),
            'owned_clip': owned_clip, 'owned_clip_hash': f'0x{hash40(owned_clip):010x}',
            'scripts': {c: f'{c}_{suffix}' for c in ('game', 'expression', 'sound', 'effect')},
            'flags': f'0x{e["flags"]:04x}', 'blend': e['blend'], 'cancel_field': entry_cancel(e), 'size': e['size'],
            'entry_sha256': __import__('hashlib').sha256(raw).hexdigest(),
        }
        report[owned_kind] = rep
        print(f"clip {owned_kind}: {rep['frames']} frames, {len(rep['pose_nodes'])} pose nodes, "
              f"{len(rep['dropped_donor_nodes'])} donor-only nodes dropped, cancel field {rep['motion_entry']['cancel_field']}")

    REFERENCE.parent.mkdir(parents=True, exist_ok=True)
    ref = build_reference_list(VANILLA_LIST.read_bytes(), raws)
    REFERENCE.write_bytes(ref)
    _, _, ref_entries = parse_mlist(ref)
    print(f"reference list: {rel(REFERENCE)} {len(ref_entries)} entries (vanilla {len(ref_entries) - len(raws)} + {len(raws)})")

    tables = OUT / 'tables'
    tables.mkdir(exist_ok=True)
    (tables / 'build_report.json').write_text(json.dumps({'unit': UNIT, 'body': report,
                                                         'reference_list_entries': len(ref_entries)},
                                                        indent=2, default=str) + '\n', encoding='utf-8')

    def files_under(root: Path) -> dict:
        return {p.relative_to(root).as_posix(): {'size': p.stat().st_size, 'sha256': sha256(p)}
                for p in sorted(root.rglob('*')) if p.is_file()}

    manifest = {
        'unit': UNIT, 'entry': 'smash_up', 'donor': 'fox',
        'owned_motions': {k: {'kind_hash': f'0x{hash40(k):010x}', **v['motion_entry']['scripts'],
                              'clip': v['motion_entry']['owned_clip'], 'clip_hash': v['motion_entry']['owned_clip_hash'],
                              'flags': v['motion_entry']['flags'], 'cancel_field': v['motion_entry']['cancel_field']}
                          for k, v in report.items()},
        'files': {f'package/{k}': v for k, v in files_under(PACKAGE).items()},
        'reference': {f'reference/{k}': v for k, v in files_under(OUT / 'reference').items()},
        'inputs': {f'donor/{p}': {'sha256': sha256(DONOR_ROOT / p)} for p in DONOR_INPUTS}
                  | {f'recipient/{p}': {'sha256': sha256(RECIPIENT_ROOT / p)} for p in RECIPIENT_INPUTS}
                  | {'gunner_motion_list_vanilla': {'path': rel(VANILLA_LIST), 'sha256': sha256(VANILLA_LIST)},
                     'gunner_skeleton': {'path': rel(GUNNER_SKEL), 'sha256': sha256(GUNNER_SKEL)}},
        'config_needed_by_coordinator': {'new-dir-files': {'fighter/miigunner/c00': sorted(files_under(PACKAGE))}},
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"package files: {len(manifest['files'])}; manifest: {rel(OUT / 'manifest.json')}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
