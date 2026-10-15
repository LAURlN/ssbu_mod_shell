"""Sweep the robot down-tilt's arm reach and report it against the donor hitbox.

Read-only with respect to every built package and to the shipped recipe: the tool writes a
probe clip into its own output directory, restores the recipe file byte-for-byte afterwards,
and never touches `builds/`, the mod tree or the SD card. It runs no test and boots nothing.

Use it when choosing or re-checking `arm_reach` in
`src/pgwr/assets/robot_dtilt/recipe.json`, or when the donor capsule in
`src/pgwr/plugin/src/acmd/robot_attack_lw3.rs` changes and the reach needs revisiting.

    python -B tools/sweep_robot_dtilt_reach.py
    python -B tools/sweep_robot_dtilt_reach.py --package builds/pgwr/0.20.16+robot-dtilt.5 \\
        --reach 1.0 1.2 1.4

For each candidate it authors the clip through the real `retarget()` path, so every number it
prints is the number the staged generator would produce, not an estimate.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import build_robot_dtilt as builder  # noqa: E402

MOD = 'ultimate/mods/pyra_gamewatch_reskin'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=ROOT / 'builds/pgwr/0.20.16+robot-dtilt.4',
                        help='any complete built package; its recipient skeleton and idle are the inputs')
    parser.add_argument('--slot', default='c06')
    parser.add_argument('--out', type=Path, default=ROOT / 'state/scratch/robot_dtilt_reach')
    parser.add_argument('--reach', type=float, nargs='+',
                        default=[0.9, 1.0, 1.1, 1.15, 1.17, 1.2, 1.3, 1.45],
                        help='candidate arm_reach values, in body heights from the fighter origin')
    args = parser.parse_args()

    mod = args.package / MOD
    if not (mod / f'fighter/eflame/model/body/{args.slot}/model.nusktb').is_file():
        parser.error(f'{args.package} is not a complete built package')
    recipe_path = builder.RECIPE
    original = recipe_path.read_text(encoding='utf-8')
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        for reach in args.reach:
            recipe = json.loads(original)
            for key in recipe['keys']:
                if key['weight'] > 0 and key['arm_reach'] > 0:
                    key['arm_reach'] = reach
            recipe_path.write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8')
            report = builder.retarget(mod / f'fighter/eflame/model/body/{args.slot}',
                                      args.out / 'probe.nuanmb', args.slot,
                                      mod / f'fighter/eflame/motion/body/{args.slot}/a00wait1.nuanmb')
            frame3 = report['frame3']
            row = {'reach': reach,
                   'hand': frame3['hand'],
                   'hand_extension_body_heights': frame3['hand_extension_body_heights'],
                   'hand_forward_of_origin_body_heights': frame3['hand_forward_of_origin_body_heights'],
                   'hand_inside_hitbox': frame3['hand_inside_hitbox'],
                   'hand_to_capsule_surface': frame3['hand_to_capsule_surface'],
                   'arm_span': frame3['arm_span'],
                   'slide': frame3['slide']}
            rows.append(row)
            print(f"reach {reach:5.2f}  hand z L {frame3['hand']['L'][2]:6.2f} R {frame3['hand']['R'][2]:6.2f}"
                  f"  y L {frame3['hand']['L'][1]:5.2f} R {frame3['hand']['R'][1]:5.2f}"
                  f"  extH L {frame3['hand_extension_body_heights']['L']:5.3f}"
                  f" R {frame3['hand_extension_body_heights']['R']:5.3f}"
                  f"  gap L {frame3['hand_to_capsule_surface']['L']:6.2f}"
                  f" R {frame3['hand_to_capsule_surface']['R']:6.2f}"
                  f"  inside {frame3['hand_inside_hitbox']}")
    finally:
        recipe_path.write_text(original, encoding='utf-8')
    out = args.out / 'reach_sweep.json'
    out.write_text(json.dumps({'package': args.package.relative_to(ROOT).as_posix(), 'slot': args.slot,
                               'recipe': str(recipe_path.relative_to(ROOT)),
                               'capsule': builder.active_hitbox(), 'rows': rows}, indent=2) + '\n',
                   encoding='utf-8')
    print('wrote', out.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()