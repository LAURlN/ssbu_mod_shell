"""Compare the donor's bone naming convention with the recipient's.

The Monkey Flip catch box is created with Hash40::new("top").  Mr. Game & Watch's
exported skeletons contain no bone literally named "top", so the question is
whether Diddy really has a lowercase "top" bone (making the donor correct and the
recipient bone missing) and which hash strings the game's own Game & Watch scripts
use for bone attachments.
"""
import collections
import glob
import os
import re
from pathlib import Path

import ssbh_data_py as s

WS = str(Path(__file__).resolve().parents[1])
DUMP_ROOT = os.environ.get("MGW_EXPORT", os.path.join(WS, "dumps", "arc"))
HASH_RE = re.compile(r'hash40\(\s*"([^"]+)"\s*\)')
BONEISH = {
    "top", "bust", "hip", "waist", "head", "neck", "handl", "handr",
    "shoulderl", "shoulderr", "arml", "armr", "legl", "legr", "rot", "trans",
    "kneel", "kneer", "footl", "footr", "toel", "toer", "throw",
}


def skeletons(fighter):
    pattern = os.path.join(DUMP_ROOT, "fighter", fighter, "model", "body", "*", "model.nusktb")
    for path in sorted(glob.glob(pattern)):
        skel = s.skel_data.read_skel(path)
        names = sorted(b.name for b in skel.bones)
        print("SKEL", fighter, path.replace(WS, ""), "bones:", len(names))
        print("   all-lowercase bones:", [n for n in names if n.islower()])
        probes = [n for n in names if n.lower() in BONEISH]
        print("   bone-ish names present:", probes)
        print("   any 'top':", [n for n in names if "top" in n.lower()])
        print()


def script_hashes(fighter):
    roots = sorted(glob.glob(os.path.join(WS, "dumps", "scripts", "SSBU-Dumped-Scripts*")))
    if not roots:
        print("SCRIPTS", fighter, "no dumped-scripts checkout in the workspace")
        return
    counter = collections.Counter()
    files = 0
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            if fighter not in dirpath.lower():
                continue
            for name in filenames:
                if not name.endswith(".txt"):
                    continue
                files += 1
                try:
                    with open(os.path.join(dirpath, name), "r", encoding="utf-8", errors="replace") as fh:
                        counter.update(HASH_RE.findall(fh.read()))
                except OSError:
                    pass
    print("SCRIPTS", fighter, "files:", files)
    print("   bone-like hash40 strings used:",
          sorted(k for k in counter if k.lower() in BONEISH))
    print("   any 'top'-ish hash40 strings:",
          sorted(k for k in counter if "top" in k.lower()))
    print()


def main():
    for fighter in ("diddy", "gamewatch"):
        skeletons(fighter)
        script_hashes(fighter)


if __name__ == "__main__":
    main()
