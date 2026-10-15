#!/usr/bin/env python3
"""Build every game asset of MV-aerial_forward__cloud (Cloud's forward air on Mii Gunner) and the Cloud
assets it shares with MV-special_up__cloud. Run from the workspace root:

    python -I mods/mii_customizer/moves/aerial_forward__cloud/build_assets.py

Inputs: the user's data.arc (extracted on first run into gamedata/mii_customizer/moves/aerial_forward__cloud/
donor/ and recipient/). Outputs, all under gamedata/mii_customizer/moves/aerial_forward__cloud/:

  package/   files only this mod uses; ship as they are
    fighter/miigunner/motion/body/c00/c01mccloudattackairf.nuanmb     Cloud's forward air, retargeted
    fighter/miigunner/motion/body/c00/c01mccloudlandingairf.nuanmb    Cloud's forward-air landing, retargeted
    fighter/miigunner/model/mccloudsword/c00/*                        Buster Sword article model   (shared)
    fighter/miigunner/motion/mccloudsword/c00/*                       its two one-frame clips      (shared)
    effect/fighter/miigunner/trail/tex_mc_cloud_sword{1_red,2}.nutexb Climhazzard ribbon textures  (shared)
  reference/ additions applied to the VANILLA shared Gunner files (the coordinator re-applies the scripts to
             whatever base the merged package uses; none of these is "the" file)
    motion_list_vanilla_plus_owned.bin                 vanilla list + the two body entries
    effect/fighter/miigunner/ef_miigunner.eff          vanilla bank + 8 Cloud sets      (mccloud_effects.py)
    sound/bank/fighter/se_miigunner.*                  vanilla bank + 6 Cloud tones     (mccloud_sounds.py)
  tables/build_report.json, manifest.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mccloud_build as b  # noqa: E402
import mccloud_effects  # noqa: E402
import mccloud_sounds  # noqa: E402
from mccloud_common import SHARED, RECIPIENT, rel  # noqa: E402

UNIT = 'aerial_forward__cloud'
OUT = SHARED
PACKAGE = OUT / 'package'
REFERENCE = OUT / 'reference'

# owned kind -> (donor kind, donor clip, owned clip, script suffix, Trans scale, limbs must move)
CLIPS = {
    'mc_cloud_attack_air_f': ('attack_air_f', 'c05attackairf.nuanmb', 'c01mccloudattackairf.nuanmb',
                              'mccloudattackairf', 1.0, True),
    'mc_cloud_landing_air_f': ('landing_air_f', 'c05landingairf.nuanmb', 'c01mccloudlandingairf.nuanmb',
                               'mccloudlandingairf', 1.0, True),
}


def main() -> int:
    b.extract_inputs()
    report = {'unit': UNIT}
    report['body'] = b.build_body_clips(PACKAGE, CLIPS, REFERENCE / 'motion_list_vanilla_plus_owned.bin')
    report['sword_article'] = b.build_sword(PACKAGE)
    report['trails'] = b.build_trails(PACKAGE)
    report['effects'] = mccloud_effects.merge(RECIPIENT / 'effect/fighter/miigunner/ef_miigunner.eff',
                                              REFERENCE / 'effect/fighter/miigunner/ef_miigunner.eff')
    report['sounds'] = mccloud_sounds.merge(RECIPIENT / 'sound/bank/fighter', REFERENCE / 'sound/bank/fighter')
    report['params'] = b.cloud_params()
    (OUT / 'tables').mkdir(exist_ok=True)
    (OUT / 'tables/build_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    pkg = b.manifest_files(PACKAGE)
    manifest = {
        'unit': UNIT, 'package_name': 'mii_customizer_move_aerial_forward__cloud',
        'files': {f'package/{k}': v for k, v in pkg.items()},
        'reference': {f'reference/{k}': v for k, v in b.manifest_files(REFERENCE).items()
                      if not k.endswith('.merge.json')},
        'config_needed_by_coordinator': {'new-dir-files': {'fighter/miigunner/c00': sorted(pkg)}},
        'shared_file_additions': {
            'fighter/miigunner/motion/body/c00/motion_list.bin': {
                'added_kinds': sorted(CLIPS), 'reference': 'reference/motion_list_vanilla_plus_owned.bin',
                'apply': 'tools/move-package motdiff against the vanilla list, merged with the other units'},
            'effect/fighter/miigunner/ef_miigunner.eff': {
                'added_handles': sorted(report['effects']['added_handles']),
                'apply': 'python -I mods/mii_customizer/moves/aerial_forward__cloud/mccloud_effects.py '
                         '--base <bank> --output <bank>'},
            'sound/bank/fighter/se_miigunner.{nus3audio,nus3bank,tonelabel}': {
                'added_tones': [t['name'] for t in report['sounds']['appended']],
                'apply': 'python -I mods/mii_customizer/moves/aerial_forward__cloud/mccloud_sounds.py '
                         '--base <dir> --output <dir>'},
        },
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    for kind, rep in report['body']['clips'].items():
        print(f"clip {kind}: {rep['frames']} frames, {len(rep['pose_nodes'])} pose nodes, "
              f"{len(rep['dropped_donor_nodes'])} donor-only nodes dropped, "
              f"cancel field {rep['motion_entry']['cancel_field']}")
    print(f"reference list: {report['body']['reference_list']['entries']} entries "
          f"(vanilla {report['body']['reference_list']['vanilla_entries']} + {len(CLIPS)})")
    print(f"sword article: {len(report['sword_article']['meshes'])} meshes; trails: {sorted(report['trails'])}")
    print(f"effects: +{len(report['effects']['added_handles'])} handles; "
          f"sounds: +{len(report['sounds']['appended'])} tones")
    print(f"manifest: {rel(OUT / 'manifest.json')} ({len(pkg)} package files)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
