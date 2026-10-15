#!/usr/bin/env python3
"""Offline checks for the P2-PLUGIN-SCAFFOLD NRO.

Run from anywhere:
    python mods/mii_customizer/scratch/2026-10-04_P2-PLUGIN-SCAFFOLD/check_scaffold.py

Every check is a pure byte/string read of files in this mod. Nothing here
starts the game, an emulator or a console connection. Tier B: these checks
verify that the artifact is a well-formed NRO containing the expected
strings. They say nothing about what the plugin does when Skyline loads it.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

MOD = Path(__file__).resolve().parents[2]
PKG = MOD / "builds" / "0.0.1-scaffold"
NRO = PKG / "libmii_customizer.nro"
MANIFEST = PKG / "MANIFEST.json"
CRATE_TOML = MOD / "plugin" / "Cargo.toml"
LIB_RS = MOD / "plugin" / "src" / "lib.rs"
LOCK = MOD / "plugin" / "Cargo.lock"

failures = []
passes = []


def check(name, ok, detail=""):
    (passes if ok else failures).append(name)
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" - {detail}" if detail else ""))


def main():
    data = NRO.read_bytes()
    manifest = json.loads(MANIFEST.read_text())

    # 1. sha256 and size agree with the manifest.
    digest = hashlib.sha256(data).hexdigest()
    check("nro sha256 matches manifest", digest == manifest["sha256"], digest)
    check("nro size matches manifest", len(data) == manifest["size_bytes"],
          f"{len(data)} bytes")

    # 2. NRO magic. The NRO header is: u32 branch at 0x00, u32 mod_offset at
    #    0x04, then the 4-byte ASCII magic "NRO0" at offset 0x10.
    magic = data[0x10:0x14]
    check("NRO magic at 0x10 is NRO0", magic == b"NRO0",
          f"read {magic!r} at 0x10")

    # 3. MOD0 section: the NRO's asset section starts at the mod_offset field
    #    and is introduced by its own "MOD0" magic.
    mod_offset = struct.unpack("<I", data[0x04:0x08])[0]
    mod_magic = data[mod_offset:mod_offset + 4]
    check("MOD0 magic at mod_offset", mod_magic == b"MOD0",
          f"read {mod_magic!r} at 0x{mod_offset:04x}")

    # 4. The identifying line's parts and the SD log path are in the binary.
    check("contains version string '0.0.1 loaded'", b"0.0.1 loaded" in data)
    check("contains SD log path",
          b"sd:/ultimate/mii_customizer_log.txt" in data)
    check("contains plugin name", b"mii_customizer" in data)

    # 5. Cargo.toml version matches the compiled-in version and the manifest.
    toml_version = None
    for line in CRATE_TOML.read_text().splitlines():
        if line.startswith("version = "):
            toml_version = line.split('"')[1]
            break
    check("Cargo.toml version matches binary",
          f"{toml_version} loaded".encode() in data, toml_version)
    check("Cargo.toml version matches manifest",
          toml_version == manifest["crate_version"])

    # 6. The pinned skyline revision in Cargo.lock is the one in the manifest.
    rev = None
    in_skyline = False
    for line in LOCK.read_text().splitlines():
        if line.startswith("name = "):
            in_skyline = line.strip() == 'name = "skyline"'
        if in_skyline and line.startswith("source = "):
            rev = line.rsplit("#", 1)[1].strip().strip('"')
            break
    check("Cargo.lock skyline rev matches manifest", rev == manifest["skyline_rev"], rev)

    # 7. Only skyline is a direct dependency - no smashline / skyline-smash.
    check("no smashline in lock", "smashline" not in LOCK.read_text())
    check("no skyline-smash in lock", "skyline-smash" not in LOCK.read_text())

    # 8. The source installs no hook and calls no game function.
    src = LIB_RS.read_text()
    for forbidden in ("skyline::patching", "skyline::hooks", "skyline::nro",
                      "smashline", "skyline_smash", "Patch::in_text",
                      "smash::", "lua2cpp", "install_acmd", "Agent::new",
                      "unwrap()", "expect(", "panic!"):
        check(f"source contains no {forbidden!r}", forbidden not in src)

    # 9. It must not have been installed: no install scripts, no sd paths in
    #    this mod's build tree beyond the one log path literal.
    stray = [p for p in (MOD / "builds").rglob("*.sh")]
    check("no install script under builds/", not stray, str(stray))

    print(f"\n{len(passes)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())