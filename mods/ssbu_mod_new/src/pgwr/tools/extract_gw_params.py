#!/usr/bin/env python3
"""Extract Mr. Game & Watch physics and gameplay parameters and diff against Pyra (eflame).

Reads:
  - export/fighter/common/param/fighter_param.prc (common attributes: weight, speed, jumps, gravity, etc.)
  - export/fighter/gamewatch/param/vl.prc (fighter-specific parameters: param_private)
  - dumps/scripts/ParamLabels.csv (param hash labels)

Generates or checks:
  - plugin/src/params.rs (Skyline WorkModule parameter override bridge)
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Add directory containing prc.py to sys.path
TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
ROOT_DIR = PROJECT_DIR.parent.parent
sys.path.insert(0, str(TOOLS_DIR))

import prc  # noqa: E402

# Deliberate departures from G&W's fighter_param.prc values, keyed by hash.
# Each one belongs to a ported move that is not G&W's own; the move file is named
# so the override is removed together with the port.
#   0x1a450f7156 landing_attack_air_frame_f: Cloud's fair port (plugin/src/acmd/attack_air_f.rs,
#   tools/build_cloud_fair.py) uses Cloud's 11 landing frames instead of G&W's 17.
#   0x1a4262b54f landing_attack_air_frame_b: Pikachu's back air port (plugin/src/acmd/pikachu_attack_air_b.rs,
#   tools/audit_pikachu_airb_params.py). Pikachu's own value is entry 7 of fighter_param.prc: 18.0, the same as
#   G&W's, so the number does not move; the override exists so a regeneration keeps saying whose it is.
COMMON_FLOAT_OVERRIDES: dict[int, tuple[float, str]] = {
    0x1a450f7156: (11.0, "Cloud"),
    0x1a4262b54f: (18.0, "Pikachu"),
}


def load_labels(labels_file: Path) -> dict[int, str]:
    labels: dict[int, str] = {}
    if not labels_file.is_file():
        return labels
    with open(labels_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try:
                    labels[int(parts[0], 16)] = parts[1]
                except ValueError:
                    pass
    return labels


def extract_params(
    fighter_param_path: Path,
    gw_vl_path: Path,
    labels: dict[int, str],
):
    tree = prc.read(fighter_param_path)
    fighters = tree[1][0][1][1]
    gw_common = prc.as_dict(fighters[26])
    ef_common = prc.as_dict(fighters[77])

    # Diffs in fighter_param.prc
    diffs_float: list[tuple[int, str, float, float]] = []
    diffs_int: list[tuple[int, str, str, int, int]] = []
    diffs_other: list[tuple[int, str, str, any, any]] = []

    for k in gw_common:
        v_gw = gw_common[k]
        v_ef = ef_common.get(k)
        if v_gw != v_ef:
            tag, val_gw = v_gw
            _, val_ef = v_ef
            name = labels.get(k, f"0x{k:010x}")
            if tag == "float":
                diffs_float.append((k, name, float(val_gw), float(val_ef)))
            elif tag in ("i32", "u32", "i16", "u16", "i8", "u8", "bool"):
                diffs_int.append((k, name, tag, int(val_gw), int(val_ef)))
            else:
                diffs_other.append((k, name, tag, val_gw, val_ef))

    # Sort diffs by name for consistency
    diffs_float.sort(key=lambda x: x[1])
    diffs_int.sort(key=lambda x: x[1])

    # param_private in vl.prc
    gw_vl = prc.as_dict(prc.read(gw_vl_path))
    private = prc.as_dict(gw_vl[prc.hash40("param_private")])

    priv_float: list[tuple[int, str, float]] = []
    priv_int: list[tuple[int, str, str, int]] = []

    for k, (tag, val) in private.items():
        name = labels.get(k, f"0x{k:010x}")
        if tag == "float":
            priv_float.append((k, name, float(val)))
        else:
            priv_int.append((k, name, tag, int(val)))

    priv_float.sort(key=lambda x: x[1])
    priv_int.sort(key=lambda x: x[1])

    # param_special_hi[0] in vl.prc: G&W's up special (Fire). Read by the ported
    # statuses in plugin/src/status/special_hi.rs through WorkModule::get_param_float,
    # exactly as G&W's lua2cpp does (refs/gamewatch_special_hi/README.md). Pyra's own
    # param_special_hi has no key with these names, so nothing of hers is shadowed.
    special_hi_node = gw_vl[prc.hash40("param_special_hi")]
    special_hi = prc.as_dict(special_hi_node[1][0])
    sh_float: list[tuple[int, str, float]] = []
    for k, (tag, val) in special_hi.items():
        if tag != "float":
            raise SystemExit(f"param_special_hi: unexpected {tag} {k:#x}")
        sh_float.append((k, labels.get(k, f"0x{k:010x}"), float(val)))
    sh_float.sort(key=lambda x: x[1])

    return {
        "diffs_float": diffs_float,
        "diffs_int": diffs_int,
        "diffs_other": diffs_other,
        "priv_float": priv_float,
        "priv_int": priv_int,
        "sh_float": sh_float,
    }


def generate_rust_source(params_data: dict) -> str:
    diffs_float = params_data["diffs_float"]
    diffs_int = params_data["diffs_int"]
    priv_float = params_data["priv_float"]
    priv_int = params_data["priv_int"]
    sh_float = params_data["sh_float"]

    lines = [
        "//! Mr. Game & Watch physics and fighter parameter overrides for Pyra (`eflame`) on c06/c07.",
        "//!",
        "//! Generated by tools/extract_gw_params.py from:",
        "//!   - export/fighter/common/param/fighter_param.prc (entries 26 vs 77)",
        "//!   - export/fighter/gamewatch/param/vl.prc (param_private, param_special_hi[0])",
        "//!",
        "//! Intercepts WorkModule::get_param_float and WorkModule::get_param_int when",
        "//! the fighter is eflame on TARGET_COSTUMES (6 or 7). Vanilla Pyra, vanilla Mythra,",
        "//! and real Mr. Game & Watch are completely untouched.",
        "",
        "use smash::{",
        "    app::{self, lua_bind::*, BattleObjectModuleAccessor},",
        "    lib::lua_const::*,",
        "    hash40,",
        "};",
        "",
        "const HASH_COMMON: u64 = 0x06e5ec7051; // hash40(\"common\")",
        "const HASH_PARAM_PRIVATE: u64 = 0x0f2bf05a96; // hash40(\"param_private\")",
        "const HASH_PARAM_SPECIAL_HI: u64 = 0x1086bc4a93; // hash40(\"param_special_hi\")",
        "",
        "#[inline]",
        "pub unsafe fn is_target_fighter(boma: *mut BattleObjectModuleAccessor) -> bool {",
        "    if boma.is_null() {",
        "        return false;",
        "    }",
        "    if app::utility::get_category(&mut *boma) != *BATTLE_OBJECT_CATEGORY_FIGHTER {",
        "        return false;",
        "    }",
        "    if app::utility::get_kind(&mut *boma) != *FIGHTER_KIND_EFLAME {",
        "        return false;",
        "    }",
        "    let color = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR);",
        "    color >= 0 && crate::TARGET_COSTUMES.contains(&(color as usize))",
        "}",
        "",
        "/// Lookup G&W common float parameter difference.",
        "#[inline]",
        "pub fn get_common_param_float(hash: u64) -> Option<f32> {",
        "    match hash {",
    ]

    for k, name, val_gw, _ in diffs_float:
        if k in COMMON_FLOAT_OVERRIDES:
            val, why = COMMON_FLOAT_OVERRIDES[k]
            lines.append(f"        0x{k:010x} => Some({repr(val)}f32), // {name} ({why})")
            continue
        # Use repr or precise float representation
        lines.append(f"        0x{k:010x} => Some({repr(val_gw)}f32), // {name}")

    lines.extend([
        "        _ => None,",
        "    }",
        "}",
        "",
        "/// Lookup G&W common int/bool parameter difference.",
        "#[inline]",
        "pub fn get_common_param_int(hash: u64) -> Option<i32> {",
        "    match hash {",
    ])

    for k, name, tag, val_gw, _ in diffs_int:
        lines.append(f"        0x{k:010x} => Some({val_gw}), // {name} ({tag})")

    lines.extend([
        "        _ => None,",
        "    }",
        "}",
        "",
        "/// Lookup G&W param_private float parameter from vl.prc.",
        "#[inline]",
        "pub fn get_private_param_float(hash: u64) -> Option<f32> {",
        "    match hash {",
    ])

    for k, name, val_gw in priv_float:
        lines.append(f"        0x{k:010x} => Some({repr(val_gw)}f32), // {name}")

    lines.extend([
        "        _ => None,",
        "    }",
        "}",
        "",
        "/// Lookup G&W param_private int parameter from vl.prc.",
        "#[inline]",
        "pub fn get_private_param_int(hash: u64) -> Option<i32> {",
        "    match hash {",
    ])

    for k, name, tag, val_gw in priv_int:
        lines.append(f"        0x{k:010x} => Some({val_gw}), // {name} ({tag})")

    lines.extend([
        "        _ => None,",
        "    }",
        "}",
        "",
        "/// Lookup G&W param_special_hi[0] float parameter from vl.prc (up special, Fire).",
        "#[inline]",
        "pub fn get_special_hi_param_float(hash: u64) -> Option<f32> {",
        "    match hash {",
    ])
    for k, name, val_gw in sh_float:
        lines.append(f"        0x{k:010x} => Some({repr(val_gw)}f32), // {name}")
    lines.extend([
        "        _ => None,",
        "    }",
        "}",
        "",
        "/// Map queried (parent, child) to G&W float parameter if overridden.",
        "#[inline]",
        "pub fn get_fighter_param_float(parent: u64, child: u64) -> Option<f32> {",
        "    if parent == HASH_PARAM_PRIVATE {",
        "        return get_private_param_float(child);",
        "    }",
        "    if parent == HASH_PARAM_SPECIAL_HI {",
        "        return get_special_hi_param_float(child);",
        "    }",
        "    if parent == 0 || parent == HASH_COMMON {",
        "        if let Some(val) = get_common_param_float(child) {",
        "            return Some(val);",
        "        }",
        "    }",
        "    if child == 0 || child == HASH_COMMON {",
        "        if let Some(val) = get_common_param_float(parent) {",
        "            return Some(val);",
        "        }",
        "    }",
        "    None",
        "}",
        "",
        "/// Map queried (parent, child) to G&W int parameter if overridden.",
        "#[inline]",
        "pub fn get_fighter_param_int(parent: u64, child: u64) -> Option<i32> {",
        "    if parent == HASH_PARAM_PRIVATE {",
        "        return get_private_param_int(child);",
        "    }",
        "    if parent == 0 || parent == HASH_COMMON {",
        "        if let Some(val) = get_common_param_int(child) {",
        "            return Some(val);",
        "        }",
        "    }",
        "    if child == 0 || child == HASH_COMMON {",
        "        if let Some(val) = get_common_param_int(parent) {",
        "            return Some(val);",
        "        }",
        "    }",
        "    None",
        "}",
        "",
        "#[skyline::hook(replace = WorkModule::get_param_int)]",
        "unsafe fn param_int(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> i32 {",
        "    if let Some(val) = crate::mythra::hero_neutral_b::handle_param_int(boma, parent, child) { return val; }",
        "    if let Some(val) = crate::breath::handle_param_int(boma, parent, child) {",
        "        return val;",
        "    }",
        "    if is_target_fighter(boma) {",
        "        if let Some(val) = get_fighter_param_int(parent, child) {",
        "            return val;",
        "        }",
        "    }",
        "    original!()(boma, parent, child)",
        "}",
        "",
        "#[skyline::hook(replace = WorkModule::get_param_float)]",
        "unsafe fn param_float(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> f32 {",
        "    if let Some(val) = crate::mythra::hero_neutral_b::handle_param_float(boma, parent, child) { return val; }",
        "    if let Some(val) = crate::breath::handle_param_float(boma, parent, child) {",
        "        return val;",
        "    }",
        "    if is_target_fighter(boma) {",
        "        if let Some(val) = get_fighter_param_float(parent, child) {",
        "            return val;",
        "        }",
        "    }",
        "    original!()(boma, parent, child)",
        "}",
        "",
        "pub fn install() {",
        "    unsafe {",
        "        skyline::install_hooks!(param_int, param_float);",
        "    }",
        "    println!(\"{} Fighter physics & parameters bridge installed (G&W attributes -> eflame c06/c07)\", crate::LOG);",
        "}",
        "",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extract G&W parameters and diff with Pyra")
    parser.add_argument("--summary", action="store_true", help="Print summary of diffs")
    parser.add_argument("--write", action="store_true", help="Write plugin/src/params.rs")
    parser.add_argument("--check", action="store_true", help="Verify params.rs matches extracted data")
    args = parser.parse_args()

    fighter_param = ROOT_DIR / "dumps/arc/fighter/common/param/fighter_param.prc"
    gw_vl = ROOT_DIR / "dumps/arc/fighter/gamewatch/param/vl.prc"
    labels_path = ROOT_DIR / "dumps/scripts/ParamLabels.csv"
    rust_out = PROJECT_DIR / "plugin/src/params.rs"

    if not fighter_param.is_file():
        sys.exit(f"Error: missing {fighter_param}")
    if not gw_vl.is_file():
        sys.exit(f"Error: missing {gw_vl}")

    labels = load_labels(labels_path)
    data = extract_params(fighter_param, gw_vl, labels)

    diffs_float = data["diffs_float"]
    diffs_int = data["diffs_int"]
    priv_float = data["priv_float"]
    priv_int = data["priv_int"]

    print(f"Extracted {len(diffs_float)} common float diffs, {len(diffs_int)} common int/bool diffs.")
    print(f"Extracted {len(priv_float)} private float params, {len(priv_int)} private int params.")

    # Show key physics highlights
    key_params = [
        "weight", "scale", "run_speed_max", "walk_speed_max", "dash_speed",
        "air_speed_x_stable", "air_accel_x_add", "air_accel_x_mul", "air_brake_x",
        "air_accel_y", "air_speed_y_stable", "air_brake_y", "dive_speed_y",
        "jump_y", "mini_jump_y", "jump_initial_y", "jump_aerial_y",
        "ground_brake", "shield_radius", "height"
    ]
    print("\n--- Key Physics Attributes Diff (gamewatch vs eflame) ---")
    float_dict = {name: (gw, ef) for _, name, gw, ef in diffs_float}
    for kp in key_params:
        if kp in float_dict:
            gw_v, ef_v = float_dict[kp]
            print(f"  {kp:22}: G&W={gw_v:<10.4f} | Pyra={ef_v:<10.4f}")

    if args.check:
        if not rust_out.is_file():
            sys.exit(f"Check failed: {rust_out} does not exist")
        # Exact comparison: params.rs must be byte-for-byte this generator's output.
        if rust_out.read_text(encoding="utf-8") != generate_rust_source(data):
            sys.exit(f"Check failed: {rust_out} differs from generator output (run --write)")
        print(f"\nVerification PASSED: params.rs is the generator output "
              f"({len(diffs_float)} common floats, {len(diffs_int)} common ints, "
              f"{len(priv_float)} private floats, {len(priv_int)} private ints, "
              f"{len(data['sh_float'])} param_special_hi floats)")

    if args.write:
        code = generate_rust_source(data)
        rust_out.write_text(code, encoding="utf-8")
        print(f"\nWrote Rust parameter bridge to {rust_out}")


if __name__ == "__main__":
    main()
