"""P11-MENU: write builds/0.5.0-menu/MANIFEST.json from the files on disk.

  python mods/mii_customizer/scratch/2026-10-06_P11-MENU/write_manifest.py     (any directory)

Hashes the staged NRO, the plugin sources it was built from, the build script and the example
menu. It runs nothing: build first (build-plugin.sh), then this, then the check script
(evidence/P11-MENU/check_p11_menu.py), which compares the manifest with the files again.
"""
import hashlib
import json
from pathlib import Path

MOD = Path(__file__).resolve().parents[2]
WORKSPACE = MOD.parents[1]
PKG = MOD / "builds/0.5.0-menu"


def item(path):
    data = path.read_bytes()
    return {"path": path.relative_to(WORKSPACE).as_posix(), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


sources = sorted((MOD / "plugin/src").glob("*.rs")) + [MOD / "plugin/Cargo.toml", MOD / "plugin/Cargo.lock",
                                                       MOD / "build-plugin.sh"]
manifest = {
    "package": "0.5.0-menu",
    "name": "mii_customizer",
    "version": "0.5.0",
    "variant": "menu",
    "date": "2026-10-06",
    "written_by": "P11-MENU worker (scratch/2026-10-06_P11-MENU/write_manifest.py)",
    "status": "built and checked offline; not installed; the menu pages, greyed rows and literal row text "
              "have never run in the game (tier D)",
    "purpose": "0.4.0 plus: mod mode opens a main page with one row per entry of menu.txt; each entry opens a "
               "character page; rows of a slot page without an allow line are greyed and cannot be decided; "
               "the stats page sets or clears the Mii's preset as 0.4.0 did",
    "nro": item(PKG / "libmii_customizer.nro"),
    "card_path": "atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro (replaces 0.4.0-ui)",
    "source": [item(p) for p in sources],
    "files": [item(PKG / "example/menu.txt")],
    "files_read_once_at_load": [
        "sd:/ultimate/mii_customizer/presets.txt",
        "sd:/ultimate/mii_customizer/loadouts.txt (loadouts.new when loadouts.txt does not exist)",
        "sd:/ultimate/mii_customizer/list.txt",
        "sd:/ultimate/mii_customizer/menu.txt (new; absent or unusable = the 0.4.0 character list)",
    ],
    "switch_files": {
        "sd:/ultimate/mii_customizer/ui_off": "no UI hook is installed; the stat engine still loads",
        "sd:/ultimate/mii_customizer/text_off": "new: rows keep their message labels, no literal text is set",
    },
    "files_written": ["sd:/ultimate/mii_customizer_log.txt (append)",
                      "sd:/ultimate/mii_customizer/loadouts.txt via loadouts.new (when a stats row is decided)"],
    "hook_sites": {
        "0x4e53e0": "stat engine (unchanged since 0.3.0)",
        "0x180a030": "edit-menu dispatcher: arming",
        "0x180abd0": "headgear state: open / keep / close a page, page change",
        "0x328b5d0": "unlisted test: greyed rows",
        "0x3288330": "message key of a handle: row labels",
        "0x19cd100": "sort_id_list: ignored while a list is open",
        "0x19ccb20": "row filler: literal text (new in 0.5.0)",
    },
    "dependencies": {
        "skyline 0.6.0": "ultimate-research/skyline-rs 6b52d321275639f26c2371d8142550ba0013a5e4",
        "skyline_smash 0.1.0": "ultimate-research/skyline-smash 315e4e8bebb460ebb9f02f30f07b0f13883ba3d6",
    },
    "rollback_nro": item(MOD / "builds/0.4.0-ui/libmii_customizer.nro"),
    "checks": [
        "bash mods/mii_customizer/build-plugin.sh",
        "bash mods/mii_customizer/scratch/2026-10-06_P11-MENU/run_host_test.sh",
        "python mods/mii_customizer/scratch/2026-10-06_P11-MENU/mutation_control.py",
        "PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python "
        "mods/mii_customizer/evidence/P11-MENU/check_p11_menu.py --selftest",
    ],
    "report": "mods/mii_customizer/research/P11-MENU.md",
}
out = PKG / "MANIFEST.json"
out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
print("wrote %s" % out.relative_to(WORKSPACE).as_posix())
print("nro %s %d bytes" % (manifest["nro"]["sha256"], manifest["nro"]["bytes"]))
