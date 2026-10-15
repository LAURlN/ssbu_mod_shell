"""P2-STAT-API offline source audit.

Every source claim this task makes about the pinned third-party bindings and the
old mod repo is re-checked here by locating the exact symbol / constant in the
pinned files and printing the surrounding evidence. Nothing is executed, nothing
is built, no offsets are invented and no game is run.

Tiers: C = pinned third-party source read, B = file-level measurement of the
local binaries. Nothing here is runtime behaviour.

Usage (from the workspace root):

    python -B mods/mii_customizer/evidence/P2-STAT-API/check_stat_api_sources.py

Exit 0 = every check passed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import struct
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[4]

# Pinned third-party sources, as named by the workspace's own Cargo.lock files.
CARGO = Path.home() / ".cargo/git/checkouts"
SKYLINE_RS = CARGO / "skyline-rs-b25835daefc3721d/6b52d32"
SKYLINE_SMASH = CARGO / "skyline-smash-f820da3599566683/315e4e8"
SMASHLINE = CARGO / "smashline-0ccc30393002c4aa/be3ef30"
OLD_MOD = WS / "mods/ssbu_mod_new"

# The two parameters this task assesses.
TARGETS = {"weight": 0x0607CD5541, "walk_speed_max": 0x0EE2EC2860}
ROW_KEY = 0x0C541EF0B3  # fighter_kind
GUNNER_KIND_HASH = 0x166E9FAE70  # hash40("fighter_kind_miigunner")
PRC_REL = "gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc"

failures: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" :: {detail}" if detail else ""))
    if not ok:
        failures.append(label)
    return ok


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def section_1_inputs() -> None:
    print("\n== 1. inputs")
    prc = WS / PRC_REL
    check(prc.is_file(), "fighter_param.prc present", str(PRC_REL))
    if prc.is_file():
        digest = sha256(prc)
        check(
            digest == "87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2",
            "fighter_param.prc sha256 matches the coordinator's independent hash",
            digest,
        )
    cat = WS / "mods/mii_customizer/evidence/P1-DATASET/gunner_catalog.json"
    if check(cat.is_file(), "P1-DATASET catalogue present", "evidence/P1-DATASET/gunner_catalog.json"):
        digest = sha256(cat)
        check(
            digest == "e210923b7a912b760b3f5f76322640562c799a1c2042a55eeaf756e889a81081",
            "catalogue sha256 matches the value P1-DATASET reported",
            digest,
        )


def section_2_prc_row() -> None:
    """B: re-decode both parameters out of the pinned .prc, independently."""
    print("\n== 2. B - re-decode weight and walk_speed_max from the pinned .prc")
    prc = load("pgwr_prc", OLD_MOD / "src/pgwr/tools/prc.py")
    tree = prc.read(WS / PRC_REL)
    tag, top = tree
    check(tag == "struct", "top-level node is a struct", tag)
    rows = next((node[1] for _, node in top if node[0] == "list"), None)
    check(rows is not None and len(rows) == 94, "94 fighter rows in the table",
          f"{len(rows) if rows else 0}")

    hits = [
        (i, row)
        for i, row in enumerate(rows)
        if row[0] == "struct"
        and any(k == ROW_KEY and n[0] == "hash" and n[1] == GUNNER_KIND_HASH for k, n in row[1])
    ]
    check(len(hits) == 1, "exactly one row carries fighter_kind_miigunner",
          f"{len(hits)} row(s)")
    if len(hits) != 1:
        return
    index, row = hits[0]
    check(index == 82, "that row is index 82, as the catalogue records", f"index {index}")

    for name, want in TARGETS.items():
        check(prc.hash40(name) == want, f"hash40({name!r}) recomputed",
              f"{prc.hash40(name):#011x}")
        found = [(k, n) for k, n in row[1] if k == want]
        if not check(len(found) == 1, f"{name} appears exactly once in the row",
                     f"{len(found)}"):
            continue
        node = found[0][1]
        bits = struct.unpack("<I", struct.pack("<f", node[1]))[0]
        check(node[0] == "float", f"{name} decodes as float", node[0])
        print(f"        {name} = {node[1]!r}  f32 bits {bits:#010x}")


def section_3_declaration_path() -> None:
    """C: the binding declaration for parameter retrieval."""
    print("\n== 3. C - declaration path: WorkModule param accessors")
    smash_rs = CARGO / "smash-rs-136d0db18d3df73e/ddacc5e"
    work = smash_rs / "src/app/modules/work.rs"
    if not check(work.is_file(), "smash-rs WorkModule source present",
                 "smash-rs ddacc5e src/app/modules/work.rs (cargo git checkout)"):
        return
    text = work.read_text(encoding="utf-8", errors="replace")
    for symbol, offset in (
        ("get_param_int_impl", "0x248"),
        ("pub get_param_int", "0x250"),
        ("get_param_float_impl", "0x268"),
        ("pub get_param_float", "0x270"),
        ("pub set_customize_no", "0x278"),
        ("pub recalculate_params", "0x280"),
    ):
        window = re.search(
            r"#\[offset = " + offset + r"\]\s*\n(?:\s*///[^\n]*\n)*\s*" + re.escape(symbol) + r":",
            text,
        )
        check(window is not None, f"smash-rs WorkModule vtable declares {symbol} at {offset}")
    check(
        "This function is not exported by the main executable, the name is assumed"
        in text,
        "smash-rs itself marks these names as assumed, not exported",
    )

    cpp = (CARGO / "skyline-smash-f820da3599566683/315e4e8/src/cpp.rs").read_text(
        encoding="utf-8", errors="replace"
    )
    link = "_ZN3app8lua_bind32WorkModule__get_param_float_implEPNS_26BattleObjectModuleAccessorEmm"
    check(link in cpp, "skyline-smash declares the lua2cpp marshalling for the same call",
          link)
    check(
        cpp.count("_ZN3app8lua_bind32WorkModule__get_param_float_implEPNS_26BattleObjectModuleAccessorEmm") == 1,
        "the declaration appears exactly once (no second, differently shaped overload)",
    )


def section_4_implementation_path_a() -> None:
    """C/B: the per-call-site override the old mod already ships."""
    print("\n== 4. C - implementation path A: per-boma get_param_* override")
    params = OLD_MOD / "src/pgwr/plugin/src/params.rs"
    if not check(params.is_file(), "old mod param bridge source present",
                 "src/pgwr/plugin/src/params.rs"):
        return
    text = params.read_text(encoding="utf-8", errors="replace")
    check('#[skyline::hook(replace = WorkModule::get_param_float)]' in text,
          "path A hooks WorkModule::get_param_float by replace")
    check("unsafe fn param_float(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> f32" in text,
          "the hook receives the BattleObjectModuleAccessor, i.e. the calling fighter object")
    check("get_common_param_float" in text and "0x0ee2ec2860 => Some(" in text,
          "walk_speed_max is one of the values path A substitutes")
    check("0x0607cd5541 => Some(" in text, "weight is one of the values path A substitutes")
    check("get_category(&mut *boma) != *BATTLE_OBJECT_CATEGORY_FIGHTER" in text,
          "path A gates on the object being a fighter before substituting")
    check("app::utility::get_kind(&mut *boma) != *FIGHTER_KIND_EFLAME" in text,
          "path A then gates on the fighter kind")
    check("FIGHTER_INSTANCE_WORK_ID_INT_COLOR" in text,
          "path A finally discriminates instances by a per-object work int (colour)")
    check("mod params;" in (OLD_MOD / "src/pgwr/plugin/src/lib.rs").read_text(encoding="utf-8", errors="replace"),
          "the bridge is compiled into the pgwr plugin, not a dead file")


def section_5_implementation_path_b() -> None:
    """C: the per-battle-object param object the clone engine writes into."""
    print("\n== 5. C - implementation path B: per-object param object at accessor+0x2758")
    core = OLD_MOD / "src/mgw_standalone/vendor/ssbu_clone_engine/clone_engine_core/src/fighter_common_copies.rs"
    impl = OLD_MOD / "src/mgw_standalone/vendor/ssbu_clone_engine/src/fighter_common_copies.rs"
    if not (check(core.is_file(), "clone engine core table present", core.name)
            and check(impl.is_file(), "clone engine implementation present", impl.name)):
        return
    ctext = core.read_text(encoding="utf-8", errors="replace")
    check("pub const ACCESSOR_PARAM_OBJECT: usize = 0x2758;" in ctext,
          "the per-object param object is read from accessor+0x2758")
    check("pub const PARAM_OBJECT_SIZE: usize = 0x1b60;" in ctext,
          "that object is 0x1b60 bytes")
    check("name: \"common\", file: \"common.prc\"" in ctext,
          "the object is built from per-fighter copies of six shared .prc files")
    itext = impl.read_text(encoding="utf-8", errors="replace")
    check("ACCESSOR_PARAM_OBJECT) as *const usize" in itext,
          "the implementation re-reads that same accessor field")
    check("pub(crate) unsafe fn on_accessor_init(accessor: u64, entry_id: i32" in itext,
          "the write is keyed on the accessor's own entry id, not on a global")

    # Does the curated per-object field table actually cover our two parameters?
    table = OLD_MOD / ("src/mgw_standalone/vendor/ssbu_clone_engine/clone_engine_core/"
                        "src/fighter_common_copies_table.rs")
    ttext = table.read_text(encoding="utf-8", errors="replace")
    listed = dict(re.findall(r'hash: (0x[0-9a-f]+), offset: 0x[0-9a-f]+, kind: FieldType::\w+, name: "([^"]+)"',
                              ttext))
    for name, want in TARGETS.items():
        absent = f"{want:#011x}" not in listed
        check(absent, f"the curated per-object table does NOT list {name}",
              "so path B has no recorded offset for it")

    # The per-kind row table DOES list both, in the global fighter_param row.
    rowt = OLD_MOD / ("src/mgw_standalone/vendor/ssbu_clone_engine/clone_engine_core/"
                      "src/fighter_param_row_table.rs")
    rtext = rowt.read_text(encoding="utf-8", errors="replace")
    for name, want in TARGETS.items():
        lines = [ln for ln in rtext.splitlines() if f'"{name}"' in ln]
        if not check(len(lines) == 1, f"{name} appears once in the pinned fighter_param row table",
                     f"{len(lines)}"):
            continue
        got = int(lines[0].split("hash: ")[1].split(",")[0], 16)
        off = int(lines[0].split("offset: ")[1].split(",")[0], 16)
        check(got == want, f"{name} Hash40 in the pinned row table agrees with hash40()",
              f"{got:#011x}, row offset {off:#x}")
    check("pub const ROW_SIZE: usize = 0x628;" in
          (OLD_MOD / "src/mgw_standalone/vendor/ssbu_clone_engine/clone_engine_core/"
                     "src/fighter_param_row.rs").read_text(encoding="utf-8", errors="replace"),
          "that row is 0x628 bytes, i.e. the global per-kind fighter_param row")


def section_6_per_kind_not_per_instance() -> None:
    """C: the framework registration is per fighter KIND, so it cannot separate two Gunners."""
    print("\n== 6. C - the framework param registration is per kind, not per instance")
    text = (CARGO / "smashline-0ccc30393002c4aa/be3ef30/src/params.rs").read_text(
        encoding="utf-8", errors="replace"
    )
    check("pub static WHITELISTED_PARAMS: RwLock<BTreeMap<i32, Vec<Hash40>>>" in text,
          "smashline's whitelisted params are keyed by an i32 fighter id")
    check("let check_key = |key: u64| allowed_names.contains(&key);" in text,
          "one value list per fighter id; there is no instance key anywhere in the map")
    check("set_get_param_object(get_param_reimpl)" in text,
          "the override is installed on the FighterParamHolder vtable at construction")
    check("if whitelisted_params.get(&fighter_id).is_none()" in text,
          "the decision is taken from fighter_id alone")


def section_7_13_0_4_fork() -> None:
    """C: the 13.0.4 fork of the same file keeps the shape and moves one offset."""
    print("\n== 7. C - the local 13.0.4 smashline fork, same shape, one changed offset")
    upstream = (CARGO / "smashline-0ccc30393002c4aa/be3ef30/src/params.rs").read_text(
        encoding="utf-8", errors="replace"
    ).replace("\r\n", "\n")
    fork_path = OLD_MOD / "src/mgw_standalone/smashline_1304/src/params.rs"
    fork = fork_path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    check("0x37209b4 + 0x5B0" in upstream,
          "upstream pins the param-object construction site at 0x37209b4 + 0x5B0")
    check("#[skyline::hook(offset = 0x37209b4 /* MGW: verified against 13.0.4 dump" in fork,
          "the local 13.0.4 fork re-verified that site as 0x37209b4")
    stripped_up = re.sub(r"\s+", " ", upstream.replace("0x37209b4 + 0x5B0", "SITE"))
    stripped_fk = re.sub(r"\s+", " ", fork.replace(
        "0x37209b4 /* MGW: verified against 13.0.4 dump; see offset-audit.json */", "SITE"))
    check(stripped_up == stripped_fk,
          "apart from that one offset the two param.rs files are identical",
          f"{sha256(fork_path)[:16]}")


def section_8_caching_and_reset() -> None:
    """C: what the sources say about caching and reset, and what they do not."""
    print("\n== 8. C - caching and reset: declared, and deliberately not inferred")
    work = (CARGO / "smash-rs-136d0db18d3df73e/ddacc5e/src/app/modules/work.rs").read_text(
        encoding="utf-8", errors="replace"
    )
    check("Recalculates runtime-cached params based off of a stat change." in work,
          "smash-rs documents a runtime-cached param layer with a recalculation entry point")
    check("This function sends an event with ID `0x31`" in work,
          "that entry point is described as sending event 0x31")
    check("is not exported by the main executable, the name is assumed" in work,
          "the entry point's own name is flagged as assumed, so it stays tier D")
    impl = (OLD_MOD / "src/mgw_standalone/vendor/ssbu_clone_engine/src/fighter_common_copies.rs"
            ).read_text(encoding="utf-8", errors="replace")
    check("registration.clear();" in impl,
          "the clone engine resets its per-entry registration on accessor init")
    rows_src = (OLD_MOD / "src/mgw_standalone/vendor/ssbu_clone_engine/src/fighter_param_rows.rs"
                ).read_text(encoding="utf-8", errors="replace")
    check("ENTRY_STRUCT_ENTRY_ID: usize = 0xa8;" in rows_src
          and "core::ptr::read_volatile((entry_struct as usize + ENTRY_STRUCT_ENTRY_ID)"
          in rows_src,
          "that entry id is read off the entry struct at +0xa8, so the reset is per entry, per object")
    print("        NOTE: nothing in any pinned source states what a stock loss, a respawn or an")
    print("        object destruction does to walk_speed_max or weight. That stays unresolved.")


def main() -> int:
    print("P2-STAT-API offline source audit")
    print("workspace: <this checkout> (paths in this output are repo-relative on purpose)")
    section_1_inputs()
    section_2_prc_row()
    section_3_declaration_path()
    section_4_implementation_path_a()
    section_5_implementation_path_b()
    section_6_per_kind_not_per_instance()
    section_7_13_0_4_fork()
    section_8_caching_and_reset()

    print(f"\n{len(failures)} failing check(s)")
    for f in failures:
        print(f"  - {f}")
    print("RESULT:", "PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())