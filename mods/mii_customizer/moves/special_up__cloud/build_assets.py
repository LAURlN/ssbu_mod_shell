#!/usr/bin/env python3
"""Build the game assets of MV-special_up__cloud (Cloud's up special, Climhazzard, on Mii Gunner).

    python -I mods/mii_customizer/moves/special_up__cloud/build_assets.py      (from the workspace root)

Six body clips retargeted to the Gunner skeleton and the motion-list reference (vanilla Gunner list + six
entries). The Buster Sword article, the effect-bank and sound-bank additions and the two trail textures are
shared with MV-aerial_forward__cloud and are built by that unit's build_assets.py (this script runs it when
its outputs are missing). Outputs under gamedata/mii_customizer/moves/special_up__cloud/:
    package/fighter/miigunner/motion/body/c00/c01mccloudspecial*.nuanmb
    reference/motion_list_vanilla_plus_owned.bin
    tables/build_report.json, manifest.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SHARED_CODE = Path(__file__).resolve().parents[1] / 'aerial_forward__cloud'
sys.path.insert(0, str(SHARED_CODE))
import mccloud_build as b  # noqa: E402
from mccloud_common import G, SHARED, WORKSPACE, rel  # noqa: E402

UNIT = 'special_up__cloud'
OUT = G / 'moves' / UNIT
PACKAGE = OUT / 'package'
REFERENCE = OUT / 'reference/motion_list_vanilla_plus_owned.bin'


def clip_table(k: float) -> dict:
    """owned kind -> (donor kind, donor clip, owned clip, script suffix, Trans scale, limbs must move)."""
    return {
        'mc_cloud_special_hi': ('special_hi', 'd02specialhi1.nuanmb', 'c01mccloudspecialhi1.nuanmb',
                                'mccloudspecialhi', k, True),
        'mc_cloud_special_air_hi': ('special_air_hi', 'd02specialairhi1.nuanmb', 'c01mccloudspecialairhi1.nuanmb',
                                    'mccloudspecialairhi', k, True),
        'mc_cloud_special_hi2': ('special_hi2', 'd02specialhi2.nuanmb', 'c01mccloudspecialhi2.nuanmb',
                                 'mccloudspecialhi2', k, False),
        'mc_cloud_special_hi2_fall': ('special_hi2_fall', 'd02specialhifall.nuanmb', 'c01mccloudspecialhifall.nuanmb',
                                      'mccloudspecialhi2fall', k, False),
        'mc_cloud_special_hi2_end': ('special_hi2_end', 'd02specialhifallend.nuanmb',
                                     'c01mccloudspecialhifallend.nuanmb', 'mccloudspecialhi2end', k, True),
        'mc_cloud_special_hi2_landing': ('special_hi2_landing', 'd02specialhilanding.nuanmb',
                                         'c01mccloudspecialhilanding.nuanmb', 'mccloudspecialhi2landing', k, True),
    }


def main() -> int:
    sword = SHARED / 'package/fighter/miigunner/model/mccloudsword/c00/model.numshb'
    if not (SHARED / 'manifest.json').is_file() or not sword.is_file():
        r = subprocess.run([sys.executable, '-I', str(SHARED_CODE / 'build_assets.py')], cwd=WORKSPACE)
        if r.returncode != 0:
            raise RuntimeError('the shared Cloud assets (forward-air unit) did not build')
    b.extract_inputs()
    params = b.cloud_params()
    # Root motion (Trans) is scaled by Cloud's model scale over the Gunner's so the travel stays Cloud's.
    k = params['cloud']['scale'] / params['miigunner']['scale']
    clips = clip_table(k)
    if PACKAGE.exists():
        shutil.rmtree(PACKAGE)
    report = {'unit': UNIT, 'trans_scale': k, 'body': b.build_body_clips(PACKAGE, clips, REFERENCE),
              'params': params}
    (OUT / 'tables').mkdir(parents=True, exist_ok=True)
    (OUT / 'tables/build_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    pkg = b.manifest_files(PACKAGE)
    ref = b.manifest_files(OUT / 'reference')
    manifest = {
        'unit': UNIT, 'package_name': 'mii_customizer_move_special_up__cloud',
        'files': {f'package/{k_}': v for k_, v in pkg.items()},
        'reference': {f'reference/{k_}': v for k_, v in ref.items()},
        'config_needed_by_coordinator': {'new-dir-files': {'fighter/miigunner/c00': sorted(pkg)}},
        'needs_shared_cloud_assets_from': 'gamedata/mii_customizer/moves/aerial_forward__cloud '
                                          '(sword article, trails, effect and sound additions)',
        'shared_file_additions': {'fighter/miigunner/motion/body/c00/motion_list.bin': {
            'added_kinds': sorted(clips), 'reference': 'reference/motion_list_vanilla_plus_owned.bin'}},
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    for kind, rep in report['body']['clips'].items():
        print(f"clip {kind}: {rep['frames']} frames, Trans max |xyz| {rep['trans_max_abs_translation']}, "
              f"cancel field {rep['motion_entry']['cancel_field']}, flags {rep['motion_entry']['flags']}")
    print(f"reference list: {report['body']['reference_list']['entries']} entries "
          f"(vanilla {report['body']['reference_list']['vanilla_entries']} + {len(clips)})")
    print(f"manifest: {rel(OUT / 'manifest.json')} ({len(pkg)} package files)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
