"""Negative control for P14 host tests (host_test.rs next to this file).

Each mutation is applied to a COPY of the pure plugin sources under
builds/.cache/host-test/mut14/ (plugin/src is not touched); the test must then fail or stop
compiling. A mutation whose text is not found counts as missed.

  python scratch/2026-10-07_P14-SORT-OPTIONS/mutation_control.py [filter]

Exit 0 only when every mutation is caught.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
WORK = MOD / "builds/.cache/host-test/mut14"
SOURCES = ("list.rs", "loadout.rs", "logic.rs", "menu.rs", "names.rs", "preset.rs", "ui.rs")
RUSTC = ["rustc", "+stable-x86_64-pc-windows-gnu", "--edition", "2021", "--test", "-C", "opt-level=1"]

M = [
    # ---- names.rs: sort by name
    (
        "sort case sensitive",
        "names.rs",
        "cmp_ascii_ci(key_a, key_b)",
        "key_a.cmp(key_b)",
    ),
    (
        "sort order inverted",
        "names.rs",
        "ord == core::cmp::Ordering::Greater",
        "ord == core::cmp::Ordering::Less",
    ),
    (
        "sort fallback to preset name disabled",
        "names.rs",
        "buf.get(..len).unwrap_or(&[])",
        "b\"\"",
    ),
    (
        "sort comparison ignores character name",
        "names.rs",
        "cmp_ascii_ci(key_a, key_b).then_with(|| a.cmp(&b))",
        "a.cmp(&b)",
    ),
    # ---- menu.rs: Kind::Option and OptionItem
    (
        "max options 32 -> 16",
        "menu.rs",
        "pub const MAX_OPTIONS: usize = 32;",
        "pub const MAX_OPTIONS: usize = 16;",
    ),
    (
        "empty option entry not rejected",
        "menu.rs",
        "let remove = menu.entries[i].kind == Kind::Option && menu.entries[i].options_len == 0;",
        "let remove = false;",
    ),
    (
        "duplicate option id accepted",
        "menu.rs",
        "if self.find_option(opt_id).is_some() {",
        "if false {",
    ),
    (
        "option page rows off by one",
        "menu.rs",
        "Kind::Option => e.options_len() as u32,",
        "Kind::Option => e.options_len() as u32 + 1,",
    ),
    (
        "option page rows unavailable",
        "menu.rs",
        "Kind::Option => row < e.options_len() as u32,",
        "Kind::Option => false,",
    ),
    (
        "option page step decide emits wrong effect",
        "menu.rs",
        "Kind::Option => Step { next: back, effect: Effect::OptionChosen { entry, option: row as usize } },",
        "Kind::Option => Step { next: back, effect: Effect::Nothing },",
    ),
    # ---- loadout.rs: Loadout v3 and Options
    (
        "loadout v3 version line changed",
        "loadout.rs",
        "pub const VERSION_LINE_3: &str = \"mc_loadouts 3\";",
        "pub const VERSION_LINE_3: &str = \"mc_loadouts 4\";",
    ),
    (
        "loadout max options 16 -> 8",
        "loadout.rs",
        "pub const MAX_LOADOUT_OPTIONS: usize = 16;",
        "pub const MAX_LOADOUT_OPTIONS: usize = 8;",
    ),
    (
        "loadout default option 0 does not remove line",
        "loadout.rs",
        "if option == 0 {",
        "if false {",
    ),
    (
        "loadout serialise always emits v2",
        "loadout.rs",
        "if has_any_options {",
        "if false {",
    ),
    (
        "loadout serialise always emits v3",
        "loadout.rs",
        "if has_any_options {",
        "if true {",
    ),
    (
        "loadout four-field accepted in v2",
        "loadout.rs",
        "if report.version < 3 || key_field != OPTION_KEY {",
        "if key_field != OPTION_KEY {",
    ),
]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    env = dict(os.environ)
    env["MC_MOD_DIR"] = MOD.as_posix()
    env["PATH"] = str(Path.home() / ".cargo/bin") + os.pathsep + env.get("PATH", "")
    caught = missed = 0
    for name, file, old, new in M:
        if only not in name:
            continue
        if WORK.exists():
            shutil.rmtree(WORK)
        (WORK / "plugin/src").mkdir(parents=True)
        (WORK / "scratch/x").mkdir(parents=True)
        for src in SOURCES:
            shutil.copy(MOD / "plugin/src" / src, WORK / "plugin/src" / src)
        shutil.copy(HERE / "host_test.rs", WORK / "scratch/x/host_test.rs")
        target = WORK / "plugin/src" / file
        text = target.read_bytes().decode("utf-8")
        if old not in text:
            print("NOT APPLIED  %s" % name)
            missed += 1
            continue
        target.write_bytes(text.replace(old, new).encode("utf-8"))
        exe = WORK / "t.exe"
        build = subprocess.run(RUSTC + [str(WORK / "scratch/x/host_test.rs"), "-o", str(exe)],
                               capture_output=True, text=True, env=env)
        if build.returncode != 0:
            print("CAUGHT (does not compile)  %s" % name)
            caught += 1
            continue
        try:
            run = subprocess.run([str(exe)], capture_output=True, text=True, env=env, timeout=120)
            failed = run.returncode != 0
            count = sum(1 for line in run.stdout.splitlines() if line.endswith("FAILED") and line.startswith("test "))
        except subprocess.TimeoutExpired:
            failed, count = True, -1
        if failed:
            print("CAUGHT (%s)  %s" % ("timeout" if count < 0 else "%d tests fail" % count, name))
            caught += 1
        else:
            print("MISSED  %s" % name)
            missed += 1
        sys.stdout.flush()
    if WORK.exists():
        shutil.rmtree(WORK)
    print("\nTotal: %d caught, %d missed" % (caught, missed))
    sys.exit(0 if missed == 0 else 1)


if __name__ == "__main__":
    main()
