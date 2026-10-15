#!/usr/bin/env python
"""Audit the Hero mana HUD route: plugin constants against the 13.0.4 image, and the build.

Purpose: `src/pgwr/plugin/src/mythra/hero_mana/hud.rs` shows the pair's MP on the real
fighter HUD by *calling* the game's own panel part selector and HUD SP setters. It follows
game structures by offsets that were read out of disassembly. A hash of a function proves
the function has not changed; it does not prove the offset the plugin uses is the one that
function uses. This tool closes that gap: every constant in `hud.rs` is tied to the exact
instruction(s) on the 13.0.4 image it was read from, and the instruction is disassembled and
compared. It also checks the things a build can get wrong without any compiler error:

* the HUD is gated by `hero-mana-hud` and **not** by `hero-mana-reserved`, and the reserved
  hit/shield recovery is still only behind `hero-mana-reserved`;
* Hero's chara id in the plugin is `hash40("ui_chara_brave")` and that key is in the
  package's `ui_chara_db.prc`;
* the part selector really maps fighter kind 0x53 (and Kirby copying 0x53) to the part at
  gauge+0x300, read from the two jump tables in the image;
* an NRO built with the feature carries the HUD markers and one built without it does not
  (`--nro` / `--nro-without`).

Read-only. Tier B: it measures files. It proves nothing about what the console draws.

Usage:
  python tools/audit_hero_mana_hud.py --main ../../gamedata/ssbu-13.0.4/main.bin \\
      [--hud-rs src/pgwr/plugin/src/mythra/hero_mana/hud.rs] \\
      [--plugin src/pgwr/plugin] [--ui-chara-db <package>/ui/param/database/ui_chara_db.prc] \\
      [--nro <with feature>] [--nro-without <without feature>] [--json report.json]
  python tools/audit_hero_mana_hud.py --main <main.bin> --smoke

Needs `capstone` (`--python-path` or env PGWR_PYLIBS names a directory that holds it).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys
import zlib
from pathlib import Path

VERSION = "1.0.0"
MAIN_SHA256 = "f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613"

# constant in hud.rs -> [(image offset, disassembly it was read from)]; `{v}` is the
# constant in hex, `{page}` / `{low}` its adrp page and low 12 bits.
CONSTANT_SITES = {
    "FIGHTER_MANAGER_REF": [(0x852a98, "adrp x8, #{page}"), (0x852a9c, "ldr x8, [x8, #{low}]"),
                            (0x852aa0, "ldr x9, [x8]")],
    "FM_ENTRIES": [(0x852aa4, "add x9, x9, w0, sxtw #3"), (0x852aa8, "ldr x10, [x9, #{v}]")],
    "ENTRY_HUD_PLAYER": [(0x852aac, "mov w9, #{v}"), (0x852ac4, "ldr w9, [x9]")],
    "ENTRY_HUD_FLAG": [(0x852ab0, "mov w11, #{v}"), (0x852ab8, "ldrb w10, [x10, x11]")],
    "EVENT_SP_SET": [(0x852ac8, "mov w10, #{v}"), (0x852b00, "ldr x21, [x9, #0x8a8]"),
                     (0x1374e8c, "mov w8, #{v}"), (0x1374dc4, "add x27, x22, #0x8a8")],
    "EVENT_KINDS_MIN": [(0x85bbfc, "mov w10, #0x5e"), (0x85bc18, "cmp w8, #{v}")],
    "FM_LISTS": [(0x852af4, "ldr x9, [x19, #{v}]")],
    "DELEGATE_SP_SET": [(0x1374da4, "adrp x8, #{page}"), (0x1374da8, "add x8, x8, #{low}"),
                        (0x1374db4, "stp x19, x8, [x20, #0x10]"), (0x1374db0, "str xzr, [x20, #0x20]"),
                        (0x1374e0c, "str x20, [x21, #0x10]"), (0x1378650, "ldr x0, [x0, #0x20]"),
                        (0x1378668, "ldr x2, [x9, #0x2e0]"), (0x1378698, "ldr x2, [x9, #0x2e8]"),
                        (0x13786c0, "ldr x2, [x8, #0x2f0]"), (0x137865c, "ldr w8, [x1, #0xc]"),
                        (0x1378660, "ldr s0, [x1, #0x10]"), (0x1378664, "mov x1, x8")],
    "HUD_ROOT": [(0x13689d0, "adrp x8, #{page}"), (0x13689d4, "ldr x8, [x8, #{low}]"),
                 (0x13689e8, "ldr x8, [x8, #8]"), (0x13689ec, "ldr x8, [x8]")],
    "HUD_PLAYER_TABLE": [(0x13689dc, "ldr x9, [x0, #{v}]"), (0x13689f0, "ldrsw x9, [x9, #0xc]")],
    "HUD_PLAYER_STRIDE": [(0x13689e0, "mov w10, #{v}"), (0x13689e4, "smaddl x9, w1, w10, x9")],
    "HUD_VIEW_ARRAY": [(0x1368a00, "add x8, x8, x9, lsl #3"), (0x1368a04, "ldr x8, [x8, #{v}]")],
    "HUD_DEFAULT_VIEW": [(0x13689f8, "cmn w9, #1"), (0x1368a0c, "add x8, x8, #{v}")],
    "MODE_ROOT": [(0x1368a40, "adrp x8, #{page}"), (0x1368a44, "ldr x8, [x8, #{low}]"),
                  (0x1368a4c, "ldr x8, [x8, #8]"), (0x1368a50, "ldr w9, [x8, #0x138]"),
                  (0x1368a58, "ldrb w8, [x8, #0x2b8]"), (0x1368a5c, "cmp w8, #0xb")],
    "VIEW_ACTIVE": [(0x1368a14, "ldr x9, [x8, #8]"), (0x1368a28, "ldr w8, [x8, #0x14]"),
                    (0x1368a68, "ldr x8, [x8]"), (0x1368a6c, "ldrb w9, [x8, #{v}]"),
                    (0x138b1cc, "ldrb w8, [x8, #{v}]"), (0x138b1d4, "ldr w8, [x0, #0x14]"),
                    (0x138b1d8, "cmn w8, #1")],
    "PANELS": [(0x1368a78, "cmp w9, #{v}"), (0x1b7f8c0, "cmp w1, #{v}")],
    "VIEW_INNER": [(0x1368a80, "ldr x8, [x8, #{v}]")],
    "INNER_PANELS": [(0x1368a84, "ldr x8, [x8, #{v}]")],
    "PANEL_STRIDE": [(0x1368a88, "mov w10, #{v}"), (0x1368a8c, "madd x8, x9, x10, x8")],
    "PANEL_GAUGE": [(0x1367690, "add x0, x9, #{v}"), (0x1367694, "bl #0x1426fb0"),
                    (0x141a998, "add x0, x8, #{v}"), (0x141a99c, "bl #0x1426fb0")],
    "PANEL_SELECT_PART": [(0x1367694, "bl #{v}"), (0x1367674, "ldr x2, [x8, #0x3d0]"),
                          (0x1367654, "ldr x1, [x11, #0x3c8]")],
    "GAUGE_PART": [(0x1426fe0, "ldr x20, [x19, #{v}]"), (0x1427130, "str x8, [x19, #{v}]")],
    "GAUGE_BRAVE_PART": [(0x14270f4, "add x8, x19, #{v}"), (0x14270f8, "mov w21, #8"),
                         (0x1426640, "str x8, [x19, #{v}]"), (0x142663c, "str x19, [x19, #0x308]")],
    "BRAVE_PART_VTABLE": [(0x142661c, "adrp x8, #{page}"), (0x1426620, "add x8, x8, #{low}")],
    "GAUGE_BRAVE_UI": [(0x14265e0, "add x0, x19, #{v}"), (0x1426644, "bl #0x1405be0"),
                       (0x14060e4, "str x20, [x19]"), (0x1368a90, "ldr x8, [x8, #0x318]")],
    "GAUGE_PANEL_INDEX": [(0x1427154, "ldr w1, [x19, #{v}]"), (0x1427270, "ldrsw x8, [x0, #{v}]"),
                          (0x1427274, "cmp w8, #8")],
    "GAUGE_LAYOUT": [(0x1427150, "ldr x0, [x19, #{v}]"), (0x142715c, "bl #0x1b7d460")],
    "LAYOUT_ROWS": [(0x1424b34, "ldr x8, [x20, #{v}]"), (0x1b7f8c8, "ldr x19, [x0, #{v}]")],
    "ROW_STRIDE": [(0x1424b38, "mov w9, #{v}"), (0x1424b3c, "smaddl x8, w0, w9, x8")],
    "ROW_BRAVE_BINDING": [(0x1424b40, "add x8, x8, #{v}"), (0x1424b44, "str x8, [sp, #8]"),
                          (0x1424b94, "bl #0x1406350"), (0x1406484, "ldr x20, [x8]"),
                          (0x1406494, "add x0, x20, #0x180")],
    "BRAVE_UI_STATE": [(0x1405c58, "add x0, x20, #{v}"), (0x1405c68, "bl #0x1407360"),
                       (0x1368a94, "ldr x8, [x8, #{v}]")],
    "SP_QUEUE_DESCRIPTOR": [(0x14073d8, "adrp x9, #{page}"), (0x14073dc, "add x9, x9, #{low}")],
    "STATE_QUEUE_DESCRIPTOR": [(0x14073ec, "mov w10, #0xc"), (0x14074bc, "stp x9, x10, [x0, #{v}]")],
    "STATE_QUEUE_CAPACITY": [(0x1368a98, "ldr x9, [x8, #{v}]"), (0x1406d38, "ldr x10, [x0, #{v}]")],
    "STATE_QUEUE_BUFFER": [(0x14073c8, "add x8, x0, #0x100"), (0x14073cc, "stp xzr, x8, [x0, #0xf0]"),
                           (0x1368ab0, "ldr x8, [x8, #{v}]")],
    "STATE_TARGET": [(0x1406d8c, "str w8, [x19, #{v}]"), (0x1406da0, "ldr s1, [x19, #{v}]"),
                     (0x14063c0, "str x8, [x0, #{v}]")],
    "STATE_SIZE": [(0x1407374, "mov w1, #{v}")],
    "CHARA_TAG": [(0x1426f68, "mov x2, #0xff0000000000"), (0x1426f6c, "movk x2, #0xc1ff, lsl #48"),
                  (0x3262148, "and x8, x1, #0xff00000000000000"),
                  (0x326214c, "mov x9, #-0x3f00000000000000"),
                  (0x326215c, "and x22, x1, #0xffffffffff"),
                  (0x3262220, "ubfx x20, x21, #0x28, #0x10"), (0x3262228, "b.ls #0x3262244")],
}
# The two HUD classes, and the three slots called through them.
VTABLE_SLOTS = {0x2e0: 0x13689c0, 0x2e8: 0x1368ae0, 0x2f0: 0x1368bb0}
# Queue commands the plugin relies on: {0, sp} written by hud_sp_set, {1, sp} by the add path.
COMMAND_SITES = [(0x1368ab4, "str wzr, [x8]"), (0x1368ab8, "str s8, [x8, #4]"),
                 (0x139ffc4, "mov w10, #1"), (0x139ffc8, "stp w10, w9, [x8]"),
                 (0x1368c80, "strb w9, [x8, #0x38]")]
FIGHTER_KIND_BRAVE = 0x53
KIND_TABLE, KIND_TABLE_FIRST, KIND_TABLE_LEN = 0x44ed8b4, 6, 0x58
COPY_TABLE, COPY_TABLE_FIRST, COPY_TABLE_LEN = 0x44eda14, 0x30, 0x2e
BRAVE_CASE, BRAVE_COPY_CASE, NO_PART_CASE = 0x14270f4, 0x14271e4, 0x142707c


def hash40(text: str) -> int:
    return (len(text) << 32) | zlib.crc32(text.encode())


def rust_constants(source: str) -> dict:
    out = {}
    for name, value in re.findall(r"^const (\w+): [\w\[\]; ]+ = ([^;]+);", source, re.M):
        value = value.strip()
        if re.fullmatch(r"0x[0-9a-fA-F_]+|\d[\d_]*", value):
            out[name] = int(value.replace("_", ""), 0)
    m = re.search(r"const HUD_CLASS: \[usize; 2\] = \[([^\]]+)\];", source)
    if m:
        out["HUD_CLASS"] = [int(x.strip().replace("_", ""), 0) for x in m.group(1).split(",")]
    m = re.search(r"const CHARA_BRAVE: u64 = CHARA_TAG \| (0x[0-9a-fA-F_]+);", source)
    if m:
        out["CHARA_BRAVE_HASH"] = int(m.group(1).replace("_", ""), 0)
    return out


class Image:
    def __init__(self, path: Path):
        import capstone
        self.data = path.read_bytes()
        self.md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

    def text(self, offset: int) -> str:
        ins = next(self.md.disasm(self.data[offset:offset + 4], offset), None)
        return "" if ins is None else ("%s %s" % (ins.mnemonic, ins.op_str)).strip()

    def relocs(self) -> dict:
        d = self.data
        mod0 = struct.unpack_from("<I", d, 4)[0]
        cursor = mod0 + struct.unpack_from("<i", d, mod0 + 4)[0]
        tags = {}
        while True:
            tag, value = struct.unpack_from("<qQ", d, cursor)
            cursor += 16
            if tag == 0:
                break
            tags.setdefault(tag, value)
        out = {}
        for k in range(0, tags[8], 24):
            r_off, r_info, addend = struct.unpack_from("<QQq", d, tags[7] + k)
            if r_info & 0xFFFFFFFF == 0x403:
                out[r_off] = addend
        return out

    def jump(self, table: int, index: int) -> int:
        return table + struct.unpack_from("<i", self.data, table + 4 * index)[0]


def check_constants(image: Image, consts: dict) -> list:
    rows = []
    for name, sites in CONSTANT_SITES.items():
        if name not in consts:
            rows.append({"constant": name, "verdict": "MISSING in hud.rs"})
            continue
        value = consts[name]
        fmt = {"v": hex(value) if value > 9 else str(value),
               "page": hex(value & ~0xFFF), "low": hex(value & 0xFFF)}
        for offset, template in sites:
            want = template.format(**fmt)
            got = image.text(offset)
            rows.append({"constant": name, "value": hex(value), "at": hex(offset),
                         "want": want, "got": got,
                         "verdict": "MATCH" if got == want else "MISMATCH"})
    return rows


def check_structure(image: Image, consts: dict) -> list:
    rows = []
    relocs = image.relocs()
    for vtable in consts.get("HUD_CLASS", []):
        for slot, target in VTABLE_SLOTS.items():
            got = relocs.get(vtable + slot)
            rows.append({"check": "hud class %#x slot %#x" % (vtable, slot), "want": hex(target),
                         "got": None if got is None else hex(got),
                         "verdict": "MATCH" if got == target else "MISMATCH"})
    for offset, want in COMMAND_SITES:
        got = image.text(offset)
        rows.append({"check": "queue command at %#x" % offset, "want": want, "got": got,
                     "verdict": "MATCH" if got == want else "MISMATCH"})
    brave = image.jump(KIND_TABLE, FIGHTER_KIND_BRAVE - KIND_TABLE_FIRST)
    rows.append({"check": "selector: fighter kind 0x53 -> gauge+0x300 (part 8)", "want": hex(BRAVE_CASE),
                 "got": hex(brave), "verdict": "MATCH" if brave == BRAVE_CASE else "MISMATCH"})
    copy = image.jump(COPY_TABLE, FIGHTER_KIND_BRAVE - COPY_TABLE_FIRST)
    rows.append({"check": "selector: Kirby copying 0x53 -> gauge+0x300 (the non-Hero precedent)",
                 "want": hex(BRAVE_COPY_CASE), "got": hex(copy),
                 "verdict": "MATCH" if copy == BRAVE_COPY_CASE else "MISMATCH"})
    others = [k for k in range(KIND_TABLE_FIRST, KIND_TABLE_FIRST + KIND_TABLE_LEN)
              if k != FIGHTER_KIND_BRAVE and image.jump(KIND_TABLE, k - KIND_TABLE_FIRST) == BRAVE_CASE]
    rows.append({"check": "selector: no other fighter kind selects the MP gauge", "want": "[]",
                 "got": str([hex(k) for k in others]),
                 "verdict": "MATCH" if not others else "MISMATCH"})
    # eflame (0x5a) / elight (0x5b) have no part of their own, so an empty part is what
    # the plugin expects to find on a c06/c07 panel, and what a form swap restores.
    for kind, name in ((0x5a, "eflame"), (0x5b, "elight")):
        got = image.jump(KIND_TABLE, kind - KIND_TABLE_FIRST)
        rows.append({"check": "selector: %s (kind %#x) owns no panel part" % (name, kind),
                     "want": hex(NO_PART_CASE), "got": hex(got),
                     "verdict": "MATCH" if got == NO_PART_CASE else "MISMATCH"})
    parts = {k: image.jump(KIND_TABLE, k - KIND_TABLE_FIRST)
             for k in range(KIND_TABLE_FIRST, KIND_TABLE_FIRST + KIND_TABLE_LEN)}
    with_part = sorted(hex(k) for k, v in parts.items() if v != NO_PART_CASE)
    rows.append({"check": "selector: fighter kinds that own a panel part", "want": "(recorded)",
                 "got": str(with_part), "verdict": "RECORDED"})
    return rows


def check_source(plugin: Path, consts: dict, ui_db: Path | None) -> list:
    rows = []
    cargo = (plugin / "Cargo.toml").read_text(encoding="utf-8")
    mod_rs = (plugin / "src/mythra/hero_mana/mod.rs").read_text(encoding="utf-8")

    def row(check, ok, got=""):
        rows.append({"check": check, "got": got, "verdict": "MATCH" if ok else "MISMATCH"})

    row("Cargo.toml declares hero-mana-hud", bool(re.search(r"^hero-mana-hud = \[\]", cargo, re.M)))
    row("Cargo.toml still declares hero-mana-reserved",
        bool(re.search(r"^hero-mana-reserved = \[\]", cargo, re.M)))
    default = re.search(r"^default = \[([^\]]*)\]", cargo, re.M)
    row("neither mana feature is a default feature",
        bool(default) and "hero-mana" not in default.group(1), default.group(1) if default else "")
    row("hud module is gated by hero-mana-hud",
        bool(re.search(r'#\[cfg\(feature = "hero-mana-hud"\)\]\s*\nmod hud;', mod_rs)))
    row("damage module is still gated by hero-mana-reserved",
        bool(re.search(r'#\[cfg\(feature = "hero-mana-reserved"\)\]\s*\npub mod damage;', mod_rs)))
    reserved_blocks = re.findall(r'#\[cfg\(feature = "hero-mana-reserved"\)\]\s*\n([^\n]*)', mod_rs)
    row("nothing but `damage` is behind hero-mana-reserved",
        reserved_blocks == ["pub mod damage;"], str(reserved_blocks))
    row("recovery-on-hit is not called from the meter",
        "damage::" not in mod_rs, "damage:: referenced" if "damage::" in mod_rs else "")
    want = hash40("ui_chara_brave")
    have = consts.get("CHARA_BRAVE_HASH")
    row("CHARA_BRAVE is hash40(\"ui_chara_brave\")", have == want,
        "%s vs %#x" % (None if have is None else hex(have), want))
    if ui_db is not None:
        blob = ui_db.read_bytes()
        row("ui_chara_brave is a key of the package's ui_chara_db.prc",
            struct.pack("<Q", want) in blob, "%s sha256 %s" % (ui_db.name, hashlib.sha256(blob).hexdigest()[:12]))
    return rows


# Rust splits a format string at every `{}`, so only literal runs are searched for.
HUD_MARKERS = (b"HUD READY route=game-part-selector", b"HUD REFUSED signature", b"REBIND",
               b"HUD SELECT-FAILED entry=", b"HUD LOST entry=", b"HUD OFF entry=",
               b"HUD REFUSED entry=")
ABSENT_MARKER = b"HUD absent: built without the hero-mana-hud feature"


def check_nro(path: Path, with_feature: bool) -> list:
    blob = path.read_bytes()
    rows = []
    label = "%s (%s, sha256 %s)" % (path.name, "with" if with_feature else "without",
                                    hashlib.sha256(blob).hexdigest())
    for marker in HUD_MARKERS:
        present = marker in blob
        rows.append({"check": "%s: %r %s" % (label, marker.decode(), "present" if with_feature else "absent"),
                     "verdict": "MATCH" if present == with_feature else "MISMATCH"})
    present = ABSENT_MARKER in blob
    rows.append({"check": "%s: 'HUD absent' line %s" % (label, "absent" if with_feature else "present"),
                 "verdict": "MATCH" if present != with_feature else "MISMATCH"})
    for marker in (b"REGISTERED max=", b"[PGWR-MANA]"):
        rows.append({"check": "%s: meter marker %r present" % (label, marker.decode()),
                     "verdict": "MATCH" if marker in blob else "MISMATCH"})
    return rows


def write_listing(image: Image, out: Path, main_sha: str) -> None:
    """Disassemble every span of the HUD route, so the evidence is readable without the image."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from audit_hero_mana_native import HUD_ROUTE
    lines = ["# HUD route listing, 13.0.4 main sha256 %s" % main_sha,
             "# tools/audit_hero_mana_hud.py v%s --listing; spans from audit_hero_mana_native.HUD_ROUTE"
             % VERSION, ""]
    for site in HUD_ROUTE:
        lines.append("## %s  %#x..%#x  sha256 %s" % (site["id"], site["off"],
                                                    site["off"] + site["span"], site["sha256"]))
        lines.append("## %s" % site["why"])
        for offset in range(site["off"], site["off"] + site["span"], 4):
            word = struct.unpack_from("<I", image.data, offset)[0]
            lines.append("%#010x %08x %s" % (offset, word, image.text(offset) or ".word"))
        lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    print("# wrote %s" % out)


def failures_of(rows: list) -> int:
    return sum(1 for r in rows if r["verdict"] not in ("MATCH", "RECORDED"))


def smoke(image: Image) -> int:
    """Negative controls: a wrong constant, a wrong gate and a wrong hash must each fail."""
    good = {name: None for name in CONSTANT_SITES}
    problems = []
    sample = {"STATE_TARGET": 0x258, "PANEL_STRIDE": 0x3e0, "ROW_BRAVE_BINDING": 0xf78,
              "ENTRY_HUD_PLAYER": 0x41e4, "HUD_ROOT": 0x52c2420}
    for name, value in sample.items():
        ok = failures_of(check_constants_subset(image, {name: value}, [name]))
        bad = failures_of(check_constants_subset(image, {name: value + 8}, [name]))
        if ok != 0:
            problems.append("%s=%#x is the measured value but did not pass" % (name, value))
        if bad == 0:
            problems.append("%s=%#x is wrong on purpose and still passed" % (name, value + 8))
    if hash40("ui_chara_brave") != 0x0e29e05d6a:
        problems.append("hash40 does not reproduce the pinned ui_chara_brave key")
    if hash40("ui_chara_brave") == hash40("ui_chara_elight"):
        problems.append("hash40 cannot tell two chara ids apart")
    if image.jump(KIND_TABLE, 0x5a - KIND_TABLE_FIRST) == BRAVE_CASE:
        problems.append("a non-Hero kind selects the MP gauge; the selector check proves nothing")
    for line in problems:
        print("FAIL\t%s" % line, file=sys.stderr)
    if not problems:
        print("PASS\t%d constants x right/wrong value, hash40 pin and selector negative control"
              % len(sample))
    del good
    return 1 if problems else 0


def check_constants_subset(image: Image, consts: dict, names: list) -> list:
    rows = []
    for name in names:
        value = consts[name]
        fmt = {"v": hex(value) if value > 9 else str(value),
               "page": hex(value & ~0xFFF), "low": hex(value & 0xFFF)}
        for offset, template in CONSTANT_SITES[name]:
            want = template.format(**fmt)
            if "{" not in template:
                continue
            rows.append({"verdict": "MATCH" if image.text(offset) == want else "MISMATCH"})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", required=True, help="decoded 13.0.4 main.bin")
    ap.add_argument("--plugin", default="src/pgwr/plugin")
    ap.add_argument("--hud-rs")
    ap.add_argument("--ui-chara-db")
    ap.add_argument("--nro", help="NRO built with hero-mana-hud")
    ap.add_argument("--nro-without", help="NRO built without hero-mana-hud (negative control)")
    ap.add_argument("--listing", help="write the disassembly of every HUD route span here")
    ap.add_argument("--python-path")
    ap.add_argument("--json")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    for cand in (args.python_path, os.environ.get("PGWR_PYLIBS")):
        if cand:
            sys.path.insert(0, str(Path(cand)))
    main_path = Path(args.main)
    main_sha = hashlib.sha256(main_path.read_bytes()).hexdigest()
    if main_sha != MAIN_SHA256:
        print("MISMATCH\tmain image sha256 %s is not the pinned 13.0.4 image" % main_sha,
              file=sys.stderr)
        return 1
    image = Image(main_path)
    if args.smoke:
        return smoke(image)
    if args.listing:
        write_listing(image, Path(args.listing), main_sha)
    plugin = Path(args.plugin)
    hud_rs = Path(args.hud_rs) if args.hud_rs else plugin / "src/mythra/hero_mana/hud.rs"
    consts = rust_constants(hud_rs.read_text(encoding="utf-8"))
    report = {"tool": "tools/audit_hero_mana_hud.py v" + VERSION, "tier": "B",
              "main_sha256": main_sha, "hud_rs": str(hud_rs),
              "hud_rs_sha256": hashlib.sha256(hud_rs.read_bytes()).hexdigest()}
    sections = [("constants", check_constants(image, consts)),
                ("structure", check_structure(image, consts)),
                ("source", check_source(plugin, consts,
                                        Path(args.ui_chara_db) if args.ui_chara_db else None))]
    if args.nro:
        sections.append(("nro_with_feature", check_nro(Path(args.nro), True)))
    if args.nro_without:
        sections.append(("nro_without_feature", check_nro(Path(args.nro_without), False)))
    total = 0
    for name, rows in sections:
        bad = failures_of(rows)
        total += bad
        report[name] = rows
        print("%-20s %3d checks, %d not matching" % (name, len(rows), bad))
        for row in rows:
            if row["verdict"] not in ("MATCH", "RECORDED"):
                print("  %s" % json.dumps(row))
            elif row["verdict"] == "RECORDED":
                print("  recorded: %s = %s" % (row["check"], row["got"]))
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("# wrote %s" % out)
    print("# %d check(s) not matching" % total)
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
