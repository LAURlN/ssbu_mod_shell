"""Compare the member manifests of the original and patched diagnostic archives.

Written for evidence only: lists every member of both archives and reports which
ones differ, plus the header fields and per-member offsets that must be equal.
"""

import hashlib
import json
import os
import struct
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
SARC = os.path.join(ROOT, "mods/mii_customizer/tools/sarc-layout/sarc_layout.py")
OUT = os.path.join(ROOT, "mods/mii_customizer/evidence/P2-LAYOUT-PATCH/manifest_compare.json")

FILES = {
    "original": "gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc",
    "control": "gamedata/mii_customizer/P2-LAYOUT-PATCH/control/layout_original.arc",
    "patched": "gamedata/mii_customizer/P2-LAYOUT-PATCH/patched/layout_row00_scale075.arc",
}


def load(name, rel):
    # Flat dump name: `rel` is a workspace path with slashes, so it must not be
    # used as a filename or it recreates a whole tree inside scratch.
    tmp = os.path.join(ROOT, "mods/mii_customizer/scratch/2026-10-04_P2-LAYOUT-PATCH",
                       name + "_manifest.json")
    subprocess.run([sys.executable, SARC, "list", rel, "--json", tmp, "--quiet"], check=True, cwd=ROOT)
    with open(tmp, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    manifests = {name: load(name, rel) for name, rel in FILES.items()}
    base = manifests["original"]
    out = {"files": FILES, "manifests": {}}
    for name, m in manifests.items():
        out["manifests"][name] = {
            "sha256": m["sha256"],
            "size": m["size"],
            "header": m["header"],
            "members": [
                {
                    "index": x["index"],
                    "name": x["name"],
                    "data_start": x["data_start"],
                    "data_end": x["data_end"],
                    "size": x["size"],
                    "sha256": x["sha256"],
                    "name_off_field": x["name_off_field"],
                }
                for x in m["members"]
            ],
        }

    cmp = {}
    for name in ("control", "patched"):
        other = manifests[name]
        by_name = {x["name"]: x for x in other["members"]}
        changed = [
            x["name"] for x in base["members"]
            if by_name[x["name"]]["sha256"] != x["sha256"]
        ]
        moved = [
            x["name"] for x in base["members"]
            if (by_name[x["name"]]["data_start"], by_name[x["name"]]["data_end"],
                by_name[x["name"]]["name_off_field"])
            != (x["data_start"], x["data_end"], x["name_off_field"])
        ]
        cmp[name] = {
            "member_count": [len(base["members"]), len(other["members"])],
            "membership_identical": {x["name"] for x in base["members"]} == {x["name"] for x in other["members"]},
            "changed_members": changed,
            "moved_or_renamed_members": moved,
            "header_identical": base["header"] == other["header"],
            "gaps_identical": base["gaps"] == other["gaps"],
            "byte_identical_to_original": base["sha256"] == other["sha256"],
        }
    out["comparison"] = cmp

    # the exact bytes that differ inside the changed member
    a = open(os.path.join(ROOT, FILES["original"]), "rb").read()
    b = open(os.path.join(ROOT, FILES["patched"]), "rb").read()
    diffs = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    out["archive_byte_diffs"] = [
        {
            "archive_offset": i,
            "archive_offset_hex": hex(i),
            "original_byte": "0x%02x" % a[i],
            "patched_byte": "0x%02x" % b[i],
            "inside_member": "blyt/make_mii_special.bflyt",
            "member_relative_offset": i - 0x2000 - 0x11D60,
            "field": "scale_x" if i - 0x2000 - 0x11D60 in (0x10E0, 0x10E1, 0x10E2, 0x10E3) else "scale_y",
        }
        for i in diffs
    ]
    out["archive_size_unchanged"] = len(a) == len(b)
    out["sha256"] = {
        name: hashlib.sha256(open(os.path.join(ROOT, rel), "rb").read()).hexdigest()
        for name, rel in FILES.items()
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({"comparison": cmp, "archive_byte_diffs": out["archive_byte_diffs"],
                      "archive_size_unchanged": out["archive_size_unchanged"]}, indent=1))


if __name__ == "__main__":
    main()