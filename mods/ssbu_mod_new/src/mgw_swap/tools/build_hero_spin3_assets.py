"""Retarget Mii Swordfighter's actual Hero's Spin (Hi3) to Mythra c07.

The old build_hero_spin_assets.py targets Hi1 (Stone Scabbard). This script
shares its format helpers but intentionally starts from the original elight
motion list, so the Hi1 loop/cancel patches cannot leak into the Hi3 payload.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / "vendor"))
import ssbh_data_py as s
import build_hero_spin_assets as base

ROOT = TOOLS.parents[2]
DONOR = ROOT / "dumps/arc/fighter/miiswordsman/motion/body/c00"
OUT = ROOT / "mod_output/ultimate/mods/mythra_gamewatch_swap/fighter/elight/motion/body/c07"
MANIFEST = ROOT / "references/miiswordsman_special_hi3/animation_manifest.json"

# Recipient slots are established names; their script categories are replaced
# separately by the Rust plugin. The unused special_air_hi_start slot is not
# part of Hi3 and must not carry the old Hi1 payload in a release package.
MOTIONS = (
    ("special_hi3_start", "d02specialhi3start.nuanmb", "special_hi_start", "d02specialhistart.nuanmb"),
    ("special_hi3_hold", "d02specialhi3hold.nuanmb", "special_air_hi1", "d02specialairhi1.nuanmb"),
    ("special_hi3", "d02specialhi3.nuanmb", "special_air_hi_jump", "d02specialairhijump.nuanmb"),
    ("special_air_hi3", "d02specialairhi3.nuanmb", "special_air_hi_end", "d02specialairhiend.nuanmb"),
)
DONOR_SHA256 = {
    "d02specialhi3start.nuanmb": "4351ef1fd837712a244a0ddf53945abbe7321b0ee7842e113ef45c64fad7d24c",
    "d02specialhi3hold.nuanmb": "e6049cc8622af5ade38e7a8f0b5d9f05c79b4c8a5502b37d87267cf63ce4b3be",
    "d02specialhi3.nuanmb": "b6b3c3b7edcae3b3bd8b098cecf216b093d19ca27549b2cb76cbc33711dcee4f",
    "d02specialairhi3.nuanmb": "9cc205a67e19e2c9eec38283586fa02a03955d81a55cbba1cc82fa082cf20b88",
}


def fail(message):
    raise SystemExit(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retarget(donor_slot, donor_file, recipient_slot, recipient_file, bones, donor_list, recipient_list):
    source = DONOR / donor_file
    if not source.is_file() or sha(source) != DONOR_SHA256[donor_file]:
        fail(f"Missing or changed donor clip: {source}")
    de = donor_list[base.hash40(donor_slot)]
    re = recipient_list[base.hash40(recipient_slot)]
    if de["animations"] != (base.hash40(donor_file),):
        fail(f"Donor motion-list entry does not reference {donor_file}")
    if re["animations"] != (base.hash40(recipient_file),):
        fail(f"Recipient motion-list entry does not reference {recipient_file}")

    anim = s.anim_data.read_anim(str(source))
    groups = base.groups_by_type(anim)
    if set(groups) != {"Transform", "Visibility"}:
        fail(f"Unexpected donor groups in {donor_file}: {sorted(groups)}")
    original = list(groups["Transform"].nodes)
    kept = [n for n in original if n.name in bones]
    dropped = sorted(n.name for n in original if n.name not in bones)
    if len(original) != 75 or len(kept) != 64 or dropped != sorted(base.EXPECTED_DROPPED_TRACKS):
        fail(f"Unexpected skeleton intersection in {donor_file}: {len(original)} -> {len(kept)}, dropped {dropped}")
    intended = base.collapse_series(base.node_series(kept))
    frame_count = int(round(anim.final_frame_index)) + 1
    vis, mat, _ = base.read_recipient_groups()
    groups["Transform"].nodes = kept
    anim.groups = [groups["Transform"], base.build_group(vis, frame_count), base.build_group(mat, frame_count)]
    target = OUT / recipient_file
    anim.save(str(target))

    check = s.anim_data.read_anim(str(target))
    found = base.groups_by_type(check)
    if set(found) != {"Transform", "Visibility", "Material"}:
        fail(f"Wrong output groups in {target}")
    if int(round(check.final_frame_index)) + 1 != frame_count:
        fail(f"Wrong frame count in {target}")
    if {n.name for n in found["Transform"].nodes} != {n.name for n in kept}:
        fail(f"Wrong transform bones in {target}")
    reread = base.collapse_series(base.node_series(found["Transform"].nodes))
    for name in sorted(intended):
        difference = base.first_difference(name, intended[name], reread[name])
        if difference:
            fail(f"Round-trip transform mismatch in {target}: {difference}")
    if len(found["Visibility"].nodes) != 19 or len(found["Material"].nodes) != 4:
        fail(f"Wrong recipient visual groups in {target}")
    print(f"{donor_slot} -> {recipient_slot}: {frame_count} frames, {len(kept)} bones, {target.stat().st_size} bytes")
    return {
        "donor_slot": donor_slot,
        "donor_animation": donor_file,
        "donor_sha256": sha(source),
        "recipient_slot": recipient_slot,
        "recipient_animation": recipient_file,
        "frames": frame_count,
        "kept_bones": len(kept),
        "dropped_bones": dropped,
        "output_bytes": target.stat().st_size,
        "output_sha256": sha(target),
    }


def patch_list(donor_list, recipient_list, magic, motion_path):
    # Assert the donor metadata. Loop=0x02, move=0x04, cancel is entry[-2].
    required = {
        "special_hi3_start": (0x80, 0),
        "special_hi3_hold": (0x82, 0),
        "special_hi3": (0x80, 75),
        "special_air_hi3": (0x80, 0),
    }
    for donor_slot, (flags, cancel) in required.items():
        entry = donor_list[base.hash40(donor_slot)]
        if entry["flags"] != flags or entry["cancel"] != cancel:
            fail(f"Donor motion metadata changed for {donor_slot}")

    changes = {
        "special_air_hi1": (0x82, 0),
        "special_air_hi_jump": (0x80, 75),
        "special_air_hi_end": (0x80, 0),
    }
    patched = {key: dict(value) for key, value in recipient_list.items()}
    for slot, (flags, cancel) in changes.items():
        key = base.hash40(slot)
        entry = patched[key]
        raw = bytearray(entry["raw"])
        struct.pack_into("<H", raw, 16, flags)
        if entry["cancel"] is None:
            fail(f"No cancel field in {slot}")
        raw[-2] = cancel
        entry["raw"] = bytes(raw)
    result = base.encode_mlist(magic, motion_path, patched)
    target = OUT / "motion_list.bin"
    target.write_bytes(result)
    _, _, check = base.parse_mlist(target)
    if len(check) != len(recipient_list):
        fail("Motion-list entry count changed")
    changed_keys = {base.hash40(slot) for slot in changes}
    for key, entry in recipient_list.items():
        if key not in changed_keys and check[key]["raw"] != entry["raw"]:
            fail(f"Unrelated motion entry changed: {key:#x}")
    for slot, (flags, cancel) in changes.items():
        entry = check[base.hash40(slot)]
        if entry["flags"] != flags or entry["cancel"] != cancel:
            fail(f"Motion-list patch failed for {slot}")
    print(f"motion_list.bin: {len(result)} bytes, {len(changed_keys)} patched entries, {len(check)-len(changed_keys)} unchanged")
    return {"output_bytes": len(result), "output_sha256": sha(target), "patched_slots": changes}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if sha(base.RECIPIENT_SKEL) != base.RECIPIENT_SKEL_SHA256:
        fail("Recipient skeleton changed")
    original_list = base.RECIPIENT_MLIST_FALLBACKS[0]
    if sha(original_list) != base.RECIPIENT_MLIST_SHA256:
        fail("Original recipient motion list changed")
    bones = {b.name for b in s.skel_data.read_skel(str(base.RECIPIENT_SKEL)).bones}
    if len(bones) != base.EXPECTED_RECIPIENT_BONES:
        fail("Recipient bone count changed")
    magic, motion_path, recipient_list = base.parse_mlist(original_list)
    _, _, donor_list = base.parse_mlist(base.DONOR_MLIST)
    records = [retarget(*item, bones, donor_list, recipient_list) for item in MOTIONS]
    motion_list = patch_list(donor_list, recipient_list, magic, motion_path)
    # Hi1 had a fifth carrier that Hi3 never plays. Remove only the exact
    # previous payload, which is retained in backups/before-hi3 for rollback.
    stale = OUT / "d02specialairhistart.nuanmb"
    backup = ROOT / "mod_files/mythra_gamewatch_swap/backups/before-hi3/d02specialairhistart.nuanmb"
    if stale.exists():
        if not backup.is_file() or sha(stale) != sha(backup):
            fail(f"Unexpected old Hi1 carrier content; inspect before removal: {stale}")
        stale.unlink()
        print(f"Removed unused Hi1 carrier: {stale.name}")
    manifest = {
        "donor": "Mii Swordfighter Hero's Spin (Hi3)",
        "donor_motion_list_sha256": sha(base.DONOR_MLIST),
        "recipient_skeleton_sha256": sha(base.RECIPIENT_SKEL),
        "recipient_motion_list_sha256": sha(original_list),
        "motions": records,
        "motion_list": motion_list,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {MANIFEST}")


if __name__ == "__main__":
    main()
