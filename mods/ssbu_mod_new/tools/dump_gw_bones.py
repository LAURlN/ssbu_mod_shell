"""Dump Mr. Game & Watch's exported skeleton bone names.

The Monkey Flip catch box is attached to the bone hash "top".  A CATCH box on a
bone that does not exist on the recipient model can never intersect a hurtbox,
so the bone list has to be verified before any conclusion about box size.
"""
import glob
import os
from pathlib import Path

import ssbh_data_py as s

ROOT = Path(__file__).resolve().parents[1] / "dumps" / "arc" / "fighter" / "gamewatch"

CANDIDATES = [
    Path("model") / "body" / "c07" / "model.nusktb",
    Path("model") / "body" / "c00" / "model.nusktb",
]

PROBE = ["top", "hip", "waist", "bust", "head", "rot", "trans", "handr", "handl"]


def dump(path):
    skel = s.skel_data.read_skel(path)
    bones = list(skel.bones)
    names = [b.name for b in bones]
    print("=" * 70)
    print(path)
    print("bone count:", len(names))
    for probe in PROBE:
        hits = [n for n in names if n.lower() == probe]
        print("  exact {!r}: {}".format(probe, hits if hits else "MISSING"))
    lower = {n.lower() for n in names}
    for probe in PROBE:
        if probe not in lower:
            near = [n for n in names if probe in n.lower()]
            if near:
                print("  partial {!r}: {}".format(probe, near))
    print("all names:")
    print(sorted(names))


def main():
    found = 0
    for rel in CANDIDATES:
        path = ROOT / rel
        if os.path.exists(path):
            found += 1
            dump(str(path))
    if not found:
        print("no exported skeleton found under", ROOT)
        for path in sorted(glob.glob(os.path.join(str(ROOT), "**", "*.nusktb"), recursive=True)):
            print("  candidate:", path)


if __name__ == "__main__":
    main()
