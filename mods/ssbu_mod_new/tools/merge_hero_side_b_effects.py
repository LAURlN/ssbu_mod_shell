"""Merge the original Hero side-B emitter sets into Mythra's c06/c07 bank (v1.0.0).

Reuses merge_hero_neutral_b_effects.merge unchanged (same pinned converter,
donor ef_brave.eff, id remapping, collision rejection and re-export equality
check); only the resource list differs. Run it on a bank that already holds the
neutral-B sets: brave_chant/brave_chant_finish come from there and are not
merged twice. The sword-flare variant is the costume-4 set (tier D choice, see
src/pgwr/plugin/src/mythra/hero_side_b/script_acmd.rs).
Also lists the three Hero trail textures the side-B scripts name.
Smoke test: --check verifies every listed set and texture exists in the donor dump.
No claim about in-game loading follows from a successful offline merge.
"""
import argparse
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_hero_neutral_b_effects as base  # noqa: E402

EFFECTS = {
    'BRAVE_LIGHTNING1_DISCHARGE', 'BRAVE_LIGHTNING1_HOLD', 'BRAVE_LIGHTNING1_SPARK',
    'BRAVE_LIGHTNING2_HOLD', 'BRAVE_LIGHTNING2_HOLD_FLASH', 'BRAVE_LIGHTNING2_SPARK',
    'BRAVE_LIGHTNING2_SWORDSPARK', 'BRAVE_LIGHTNING3_HIT', 'BRAVE_LIGHTNING3_HIT2',
    'BRAVE_LIGHTNING3_HOLD_FLASH', 'BRAVE_LIGHTNING3_LIGHTNING', 'BRAVE_LIGHTNING3_LIGHTNING2',
    'BRAVE_LIGHTNING3_ROLLLIGHTNING', 'BRAVE_LIGHTNING3_SWORD', 'BRAVE_LIGHTNING3_SWORDSPARK',
    'BRAVE_LIGHTNING_SWORDFLARE4',
}
TRAILS = ('tex_brave_sword1', 'tex_brave_sword2', 'tex_brave_lightningsword1')
DONOR = base.ARC / 'effect/fighter/brave'


def trail_files():
    return [DONOR / 'trail' / f'{name}.nutexb' for name in TRAILS]


def check():
    assert base.CONVERTER.exists()
    names = {n.decode() for n in re.findall(rb'BRAVE_[A-Z0-9_]+', (DONOR / 'ef_brave.eff').read_bytes())}
    assert EFFECTS <= names, sorted(EFFECTS - names)
    assert all(path.is_file() for path in trail_files())
    assert not (EFFECTS & {n.upper() for n in ('brave_chant', 'brave_chant_finish')})


def merge(recipient, output):
    check()
    original = base.required
    base.required = lambda: set(EFFECTS)
    try:
        base.merge(Path(recipient), Path(output))
    finally:
        base.required = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--recipient', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.check:
        check()
        print(f'PASS: {len(EFFECTS)} side-B emitter sets and {len(TRAILS)} trail textures present in the donor dump')
    elif args.recipient and args.output:
        merge(args.recipient, args.output)
    else:
        parser.error('choose --check or --recipient and --output')


if __name__ == '__main__':
    main()
