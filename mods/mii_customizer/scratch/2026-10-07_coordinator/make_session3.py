"""Coordinator: session files for 0.5.0-menu (menu.txt, list.txt without the Mii Gunner row,
SESSION.json). Run from the workspace root. The worker's MANIFEST.json is not touched (its
check script verifies it). list.txt holds game label names, so it stays under gamedata/."""
import hashlib
import json
import os

MOD = "mods/mii_customizer"
PKG = MOD + "/builds/0.5.0-menu"
GD = "gamedata/mii_customizer/COORD-session3"
SRC_LIST = "gamedata/mii_customizer/P10-PRESET-WIDE/list.txt"

# (id, kind, text, fallback label or None). Ids are the P1-DATASET slot ids; labels are the
# exact-text matches of research/P11-ROW-TEXT.md Q4 (shown only when literal text is off).
ENTRIES = [
    ("stats", "stats", "Stats", "mnu_record_count_title"),
    ("normal_jab", "slot", "Jab", None),
    ("normal_dash", "slot", "Dash Attack", None),
    ("tilt_side", "slot", "Forward Tilt", None),
    ("tilt_up", "slot", "Up Tilt", None),
    ("tilt_down", "slot", "Down Tilt", None),
    ("smash_forward", "slot", "Forward Smash", None),
    ("smash_up", "slot", "Up Smash", None),
    ("smash_down", "slot", "Down Smash", None),
    ("aerial_neutral", "slot", "Neutral Air", None),
    ("aerial_forward", "slot", "Forward Air", None),
    ("aerial_back", "slot", "Back Air", None),
    ("aerial_up", "slot", "Up Air", None),
    ("aerial_down", "slot", "Down Air", None),
    ("grab", "slot", "Grab", "cmn_hold"),
    ("pummel", "slot", "Pummel", None),
    ("throw_forward", "slot", "Forward Throw", None),
    ("throw_back", "slot", "Back Throw", None),
    ("throw_up", "slot", "Up Throw", None),
    ("throw_down", "slot", "Down Throw", None),
    ("special_neutral", "slot", "Neutral Special", "mnu_mmiif_setup_sp_move_normal"),
    ("special_side", "slot", "Side Special", "mnu_mmiif_setup_sp_move_width"),
    ("special_up", "slot", "Up Special", "mnu_mmiif_setup_sp_move_up"),
    ("special_down", "slot", "Down Special", "mnu_mmiif_setup_sp_move_btm"),
]


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def entry(path):
    return {"path": path, "bytes": os.path.getsize(path), "sha256": sha(path)}


os.makedirs(PKG + "/session", exist_ok=True)
os.makedirs(GD, exist_ok=True)

menu = PKG + "/session/menu.txt"
with open(menu, "w", newline="\n") as f:
    f.write("mc_menu 1\n")
    f.write("# Mii Customizer menu, session 0.5.0-menu: Stats + the 23 move slots of the Gunner\n")
    f.write("# catalogue. No move is implemented, so no slot has an allow line.\n")
    for eid, kind, text, label in ENTRIES:
        f.write("entry %s %s %s\n" % (eid, kind, text))
        if label:
            f.write("label %s %s\n" % (eid, label))

lst = GD + "/list.txt"
kept = 0
dropped = []
with open(SRC_LIST, "r", newline="") as src, open(lst, "w", newline="\n") as out:
    for line in src.read().split("\n"):
        if line.split(" ")[0] == "miigunner":
            dropped.append(line)
            continue
        if line and not line.startswith("#") and line != "mc_list 1":
            kept += 1
        out.write(line + "\n")
# the source ends with a newline, so the loop wrote one line too many
data = open(lst, "rb").read()
while data.endswith(b"\n\n"):
    data = data[:-1]
open(lst, "wb").write(data)
assert dropped == ["miigunner nam_chr1_00_miigunner"], dropped
assert kept == 86, kept

session = {
    "session": "0.5.0-menu (session 3)",
    "written_by": "coordinator, 2026-10-07",
    "nro": entry(PKG + "/libmii_customizer.nro"),
    "card_files": {
        "ultimate/mii_customizer/menu.txt": entry(menu),
        "ultimate/mii_customizer/list.txt": entry(lst),
        "ultimate/mods/mii_customizer_ui/ui/script_patch/chara_make/make_mii_edit_actor.lc": entry(
            MOD + "/builds/0.4.0-edit-entry/variant_entry/mii_customizer_ui/ui/script_patch/chara_make/make_mii_edit_actor.lc"),
        "ultimate/mods/mii_customizer_ui/info.toml": entry(
            MOD + "/builds/0.4.0-edit-entry/variant_entry/mii_customizer_ui/info.toml"),
    },
    "unchanged_on_card": {
        "ultimate/mii_customizer/presets.txt": entry("gamedata/mii_customizer/P10-PRESET-WIDE/presets_wide.txt"),
        "ultimate/mii_customizer/loadouts.txt": "as the plugin saved it in session 2 (0000f589 dedede, 0000f58b fox)",
    },
    "rollback_nro": entry(MOD + "/builds/0.4.0-ui/libmii_customizer.nro"),
    "menu_entries": len(ENTRIES),
    "list_rows": kept,
}
with open(PKG + "/SESSION.json", "w", newline="\n") as f:
    json.dump(session, f, indent=2)
    f.write("\n")
print("menu", os.path.getsize(menu), sha(menu))
print("list", os.path.getsize(lst), sha(lst), "rows", kept)
for k, v in session["card_files"].items():
    print(k, v["bytes"], v["sha256"])
print("nro", session["nro"]["sha256"])
