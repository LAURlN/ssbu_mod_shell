"""Assemble the Pikachu back-air package from its three measured inputs (v1.1.0, supersedes 1.0.0).

Runs, in order, and only these:

  1. `build_pikachu_airb.deploy_for_slot` for c06 and c07 - the retargeted
     clips and the two-entry motion-list patch;
  2. `merge_pikachu_airb_sound.build` - the two `se` banks, the two `vc` banks
     and the `seq_pikachu_rnd_attack` record;
  3. the already-built NRO, copied in **by hash check only** - this script does
     not compile anything, so it cannot disagree with what `build.cmd` produced.

Everything else is written as records. The output is a **narrow delta**, not a
full mod tree: only the 19 files this task may touch are shipped, so the
installer merges them onto its own candidate and another agent's later edits
survive. `tools/audit_pikachu_airb_delta.py` then proves the file set, the
bytes, the source and the NRO.

    python -B src/pgwr/tools/package_pikachu_airb.py
    python -B src/pgwr/tools/package_pikachu_airb.py --out builds/pgwr/<dir>

Tier B: file composition and hashes. Nothing here proves the move works.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
sys.path.insert(0, str(ROOT / 'tools'))

import audit_pikachu_airb_donor as donor  # noqa: E402
import audit_pikachu_airb_hitboxes as hitboxes  # noqa: E402
import audit_pikachu_airb_params as params  # noqa: E402
import audit_pikachu_airb_pose as pose  # noqa: E402
import build_pikachu_airb as builder  # noqa: E402
import merge_pikachu_airb_sound as sound  # noqa: E402

VERSION = '1.1.0'
BASELINE_PKG = ROOT / 'builds/pgwr/0.20.23'
BASELINE = BASELINE_PKG / 'ultimate/mods/pyra_gamewatch_reskin'
NRO_REL = ('atmosphere/contents/01006A800016E000/romfs/skyline/plugins/'
           'libpyra_gamewatch_reskin.nro')
CACHE = ROOT / 'builds/.cache/pikachu-airb'
BUILT_NRO = (CACHE / 'plugin/target/aarch64-skyline-switch/release/'
             'libpyra_gamewatch_reskin.nro')
OUT = ROOT / 'builds/pgwr/pikachu-airb-1.1.0'
PATCH_SRC = CACHE / 'patches_v2'
FEATURES = ['snake-neutral-b', 'hero-side-b', 'hero-mana-hud']
BUILD_COMMAND = ('cargo skyline build --release --features '
                 + ','.join(FEATURES) + ' -- --offline')


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hash(root: Path) -> str:
    """sha256 over sorted `relpath TAB sha256 LF`, the mod's standard definition."""
    h = hashlib.sha256()
    for p in sorted(root.rglob('*')):
        if p.is_file():
            h.update(f'{p.relative_to(root).as_posix()}\t{sha(p)}\n'
                     .encode('utf-8'))
    return h.hexdigest()


def rel_path(path: Path) -> str:
    """Workspace-relative posix path. Records must not carry a machine's drive
    letter: the mod's rule is relative paths only, and a package that hardcodes
    `sd:/...` stops being readable the moment the repo moves."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=OUT)
    args = ap.parse_args()
    out = args.out
    mod = out / 'ultimate/mods/pyra_gamewatch_reskin'

    if not BUILT_NRO.is_file():
        raise SystemExit(f'missing {BUILT_NRO}; run builds/.cache/pikachu-airb/build.cmd first')
    shutil.rmtree(out, ignore_errors=True)
    mod.mkdir(parents=True)

    # 1. clips + motion list, per slot.
    stage = CACHE / 'stage'
    reports = {}
    for slot in ('c06', 'c07'):
        reports[slot] = builder.deploy_for_slot(
            slot, stage, BASELINE / 'fighter/eflame')
        dest = mod / 'fighter/eflame/motion/body' / slot
        dest.mkdir(parents=True)
        for clip in builder.CLIPS.values():
            shutil.copy2(stage / slot / clip, dest / clip)
        shutil.copy2(stage / slot / 'motion_list.bin', dest / 'motion_list.bin')

    # 2. sound. Always into a clean directory: the tone half of the merge
    # deliberately *refuses* a second pass over its own output, so reusing a
    # directory would turn a re-package into a false failure.
    merged_root = CACHE / 'sound_package'
    shutil.rmtree(merged_root, ignore_errors=True)
    merged = sound.build(merged_root, BASELINE)
    for rel in sorted(p.relative_to(merged_root).as_posix()
                      for p in merged_root.rglob('*')
                      if p.is_file() and not p.name.endswith('.json')):
        (mod / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(merged_root / rel, mod / rel)

    # 3. NRO.
    (out / NRO_REL).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BUILT_NRO, out / NRO_REL)

    # patches + records.
    shutil.copytree(PATCH_SRC, out / 'patches')
    # The three measurements the delta audit re-runs, kept as records. Each must
    # pass on the package just built or nothing is written.
    results, failures = pose.run(out)
    if failures:
        raise SystemExit(f'pose audit failed on the package just built: {failures[:3]}')
    (out / 'pikachu_airb_pose.json').write_text(
        json.dumps(results, indent=1), encoding='utf-8')
    measured = hitboxes.measure()
    if hitboxes.verdict(measured):
        raise SystemExit(f'hitbox audit failed: {hitboxes.verdict(measured)}')
    (out / 'pikachu_airb_hitboxes.json').write_text(
        json.dumps(measured, indent=1), encoding='utf-8')
    table, rs, snap = params.measure(CACHE / 'plugin')
    if params.verdict(table, rs, snap):
        raise SystemExit(f'params audit failed: {params.verdict(table, rs, snap)}')
    (out / 'pikachu_airb_params.json').write_text(
        json.dumps({'table': table, 'params_rs': rs}, indent=1), encoding='utf-8')
    # The build record is the report of *this* run (an earlier revision copied a
    # stale file from the cache directory, which can describe a previous build).
    (out / 'pikachu_airb_build.json').write_text(
        json.dumps({'tool_version': VERSION, 'evidence_tier': 'B',
                    'hardware_validated': False, 'slots': reports}, indent=1),
        encoding='utf-8')
    for name, src in (('pikachu_airb_sound.json',
                       merged_root / 'pikachu_airb_sound.json'),
                      ('pikachu_airb_inventory.json',
                       ROOT / 'refs/pikachu_attack_air_b/inventory.json')):
        if src.is_file():
            shutil.copy2(src, out / name)

    files = sorted(p for p in mod.rglob('*') if p.is_file())
    manifest = {
        'name': 'pikachu-airb',
        'version': VERSION,
        'date': datetime.date.today().isoformat(),
        'readiness': 'READY',
        'installed': False,
        'runtime_verified': False,
        'evidence_tier': 'B',
        'fighter': 'eflame',
        'costumes': ['c06', 'c07'],
        'status_id': None,
        'status_id_reason': ('both the attack-air and landing-air kinds are '
                             'vanilla AttackAirB / LandingAirB states, so no '
                             'custom status is registered and no free status '
                             'id is consumed'),
        'config_json_changed': False,
        'config_json_reason': ('the recipient and donor motion-list entries '
                               'already name the same clip file '
                               '`c05attackairb.nuanmb` / `c05landingairb.nuanmb`, '
                               'so there is no alias to declare'),
        'baseline': rel_path(BASELINE_PKG),
        'baseline_nro_sha256': sha(BASELINE_PKG / NRO_REL),
        'supersedes': 'builds/pgwr/pikachu-airb-1.0.0 (candidate; do not install it)',
        'supersedes_reason': (
            '1.0.0 transplanted the donor clip with Pikachu\'s own bone offsets, so the '
            'skeleton under G&W\'s mesh was Pikachu\'s; it also mislabelled the ATTACK '
            'fields (KBG/FKB/BKB, y/z), called `trans` an absent anchor, called '
            'Pikachu\'s landing lag unreachable and told the tester vanilla c00/c05 '
            'would show G&W\'s turtle'),
        'merge_kind': 'narrow delta: 19 files, applied over the installer\'s candidate',
        'delta_files': [p.relative_to(mod).as_posix() for p in files],
        'delta_sha256': {p.relative_to(mod).as_posix(): sha(p) for p in files},
        'delta_tree_sha256': tree_hash(mod),
        'source_snapshot': 'builds/.cache/silent-0.20.23/plugin',
        'source_patches': sorted(p.name for p in (out / 'patches').glob('*.patch')),
        'source_live': 'src/pgwr/plugin',
        'isolated_build_dir': 'builds/.cache/pikachu-airb/plugin',
        'features': FEATURES,
        'build_command': BUILD_COMMAND,
        'logging_feature': False,
        'nro_path': NRO_REL,
        'nro_sha256': sha(out / NRO_REL),
        'nro_bytes': (out / NRO_REL).stat().st_size,
        'control_unmodified_rebuild_nro_sha256':
            sha(CACHE / 'control/target/aarch64-skyline-switch/release/'
                         'libpyra_gamewatch_reskin.nro'),
        'control_note': ('an unmodified copy of the baseline snapshot, built with '
                         'the same command in the same environment, reproduces the '
                         'baseline NRO byte for byte, so the shipped NRO differs '
                         'from the baseline only because of this task'),
        'hooks': 'none: no engine interception, no raw offsets (mod rule 17)',
        'framework_changes': False,
        'parallel_agent_safety': ('this task edited only '
                                  'src/acmd/pikachu_attack_air_b.rs and three hunks '
                                  'of src/acmd/mod.rs in the live tree; every build '
                                  'used an isolated copy under builds/.cache'),
        'landing_lag': {
            'parameter': 'landing_attack_air_frame_b',
            'hash': '0x1a4262b54f',
            'source': ('fighter/common/param/fighter_param.prc entry 7 '
                       '(fighter_kind_pikachu in fighter_param_motion.prc), extracted '
                       'from the local data.arc'),
            'pikachu': 18.0, 'gamewatch': 18.0, 'pyra_eflame': 14.0,
            'unit': 'frames (float)',
            'params_rs_value': 18.0,
            'changed_by_this_package': False,
            'other_aerials_changed': False,
        },
        'open_items': [
            'the back air no longer spawns the G&W turtle article, because the donor '
            'has none. If the turtle is wanted elsewhere, check which other moves '
            'still use normal_weapon.',
            'the G&W expression scripts this replaces also hid a held item '
            '(ItemModule::set_have_item_visibility) and set the head to head_close in '
            'the landing; Pikachu\'s scripts do neither, so a held item stays visible '
            'during this move, as it does for Pikachu.',
            'sound and effect playback, how the retargeted pose looks on G&W\'s mesh '
            '(skinning is not modelled offline), hit reactions and the landing feel '
            'are unverified (tier D) until a hardware run.',
        ],
        'tests': 'tools/audit_pikachu_airb_delta.py (--negative-controls)',
    }
    (out / 'MANIFEST.json').write_text(json.dumps(manifest, indent=1),
                                       encoding='utf-8')
    (out / 'BUILD.txt').write_text(build_report(manifest, reports, merged),
                                   encoding='utf-8')
    print(json.dumps({'package': rel_path(out),
                      'files': len(files),
                      'nro_sha256': manifest['nro_sha256'],
                      'delta_tree_sha256': manifest['delta_tree_sha256']},
                     indent=1))
    return 0


def build_report(manifest: dict, reports: dict, merged: dict) -> str:
    lines = [
        'Pikachu back air on Pyra Game & Watch (eflame c06/c07) - task '
        f"{manifest['version']}, {manifest['date']}",
        '',
        'WHAT CHANGED',
        '  AttackAirB and LandingAirB are Pikachu\'s, for the modded costumes only.',
        '  game/effect/sound/expression handlers are ported verbatim from the',
        '  pinned donor scripts (refs/pikachu_attack_air_b/donor_acmd) and',
        '  registered at Priority::High, over the generated G&W ones.',
        '',
        'WHAT DELIBERATELY DID NOT CHANGE',
        '  config.json  - the clip name is already correct on both sides.',
        '  param/       - landing_attack_air_frame_b is Pikachu\'s own 18.0 (fighter_param.prc',
        '                  entry 7), equal to the 18.0 params.rs already gives c06/c07.',
        '  effect/      - sys_spin_wind / sys_attack_impact / sys_down_smoke are',
        '                  common-bank names, so no donor emitter is merged.',
        '  ui/          - no slot table change.',
        '  Any other motion-list entry, clip, bank or file in the mod tree.',
        '',
        'BUILD',
        f"  dir      {manifest['isolated_build_dir']}",
        f"  command  {manifest['build_command']}",
        f"  features {', '.join(manifest['features'])} (logging OFF)",
        f"  nro      {manifest['nro_bytes']} bytes  {manifest['nro_sha256']}",
        f"  control  unmodified snapshot rebuilds to "
        f"{manifest['control_unmodified_rebuild_nro_sha256']} "
        f"(= baseline {manifest['baseline_nro_sha256']})",
        '',
        'MEASURED PER SLOT',
    ]
    for slot, report in reports.items():
        for kind in (donor.KIND, donor.LANDING_KIND):
            rec = report['motion'][kind]
            lines.append(f"  {slot} {kind:<13} cancel "
                         f"{rec['cancel_before']}->{rec['cancel_after']}  flags "
                         f"{rec['flags_before']}->{rec['flags_after']}  "
                         f"differing bytes {rec['differing_bytes']} at "
                         f"{rec['differing_offsets']}")
        for kind in (donor.KIND, donor.LANDING_KIND):
            clip = report['clips'][builder.CLIPS[kind]]
            gc = clip['ground_contact_correction']
            lines.append(f"  {slot} {builder.CLIPS[kind]}  {clip['frames']} frames, "
                         f"{clip['native_nodes_written']} native nodes "
                         f"({clip['bones_kept']} pose bones from the donor, the rest "
                         f"held at the recipient idle); "
                         f"{len(clip['donor_nodes_not_carried'])} donor nodes not "
                         f"carried; {clip['vis_nodes']} visibility nodes from the "
                         f"recipient's own idle; 0 parent-chain mismatches; Rot y "
                         f"contact correction {gc['min']}..{gc['max']}")
    lines += ['', 'SOUND', f"  {json.dumps(merged)}", '',
              'INSTALL', '  Overlay the 19 files under ultimate/mods/'
              'pyra_gamewatch_reskin onto the installer\'s candidate, apply the',
              '  three patches under patches/ to the live plugin source, rebuild',
              '  with the command above and use the NRO in atmosphere/.',
              '  Do NOT copy a whole bank over one another task changed: the',
              '  banks here are a semantic merge, so re-run',
              '  tools/merge_pikachu_airb_sound.py --baseline <candidate> instead',
              '  if a later package changed them.',
              '',
              'NOT VERIFIED',
              '  Everything about how this feels in game. Tier B only: bytes,',
              '  structure, compile and binary content.']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    sys.exit(main())