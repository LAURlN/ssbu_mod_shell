#!/usr/bin/env python3
"""audit_hero_mana_recovery.py 1.0.0 - Hero's hit/shield MP recovery route on the 13.0.4 `main`.

What it measures (tier B, read out of the pinned image; nothing here is a runtime claim):

* **Event ownership.** `Fighter` vtable `main+0x4f7f210`: slot `+0x3f8` (`0x6204c0`) and `+0x400`
  (`0x621020`) forward to the per-character class object at `fighter+0xf700`, slots `+0x130` and
  `+0x138`. The engine raises them on the **owner fighter of the attacking object** (the single
  call sites `0x40285c` in the damage path and `0x4c721c` in the ShieldModule family resolve the
  attacker's `TeamModule::team_owner_id` first), with `w2` = the struck object's id, `w3` = the
  attacking object's id (fighter, weapon or item) and a pointer to the hit's `AttackData`.
* **Hero's handlers.** His class (`main+0x4f931d8`) fills `+0x130` with `0x854610` and `+0x138`
  with `0x854b10`. Both read `AttackData.power` (`+0x20`) and enter one core, `0x854630`, with
  flag 0 (damage) or 1 (shield). The core selects `param+0xbc` or `param+0xc0` on that flag; the
  passive recovery at `0x853500` reads `+0xb4` / `+0xb8`, so the four fields are, in the donor
  parameter order, `sp_recover_frame`, `recover_sp`, `sp_recover_damage_mul`,
  `sp_recover_shield_mul`.
* **Exclusions and the amount**, as instruction-level assertions (`CORE_FACTS`).
* **The recipients.** Pyra's (`0x4faf9c8`) and Mythra's (`0x4fb1fa0`) classes keep the base
  defaults `0x68d800` / `0x68d810`, both a bare `ret`, in those two slots. G&W's class is the
  control (also defaults); Hero's class is the positive control.

It also generates and checks the plugin's signature table (`recovery_signatures.rs`), and can
show that a built NRO does or does not carry that table (`--nro` / `--nro-without`).

    python tools/audit_hero_mana_recovery.py --main ../../gamedata/ssbu-13.0.4/main.bin \
        --python-path builds/.cache/mana_hud/python --check \
        [--emit-rust F | --check-rust F] [--listing F] [--json F] [--nro N] [--nro-without N]

`--check` adds the negative controls. Needs `capstone` (`--python-path` or env PGWR_PYLIBS).
Smoke test: `--check` on the pinned image exits 0; any moved byte exits 1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

VERSION = "1.0.0"
MAIN_SHA256 = "f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613"

FIGHTER_VTABLE = 0x4F7F210
BRAVE_CLASS = 0x4F931D8
EFLAME_CLASS = 0x4FAF9C8
ELIGHT_CLASS = 0x4FB1FA0
GAMEWATCH_CLASS = 0x4FB8F00
SLOT_DAMAGE, SLOT_SHIELD = 0x130, 0x138
DEFAULT_DAMAGE, DEFAULT_SHIELD = 0x68D800, 0x68D810
RET = bytes.fromhex("c0035fd6")

# (offset, length, id, why) - every function the plugin's owned handlers rely on.
SPANS = [
    (0x854610, 0x14, "brave_damage_thunk", "class +0x130: power = [x5+0x20], flag 0"),
    (0x854B10, 0x18, "brave_shield_thunk", "class +0x138: power = [x4+0x20], flag 1"),
    (0x854630, 0x458, "brave_recover_core", "exclusions, ratios, multiplier select, add_sp"),
    (0x620ECC, 0x24, "fighter_notify_attack_dispatch", "Fighter +0x3f8 tail: class +0x130(cls, fighter, w2, w3, x4, x5, w6)"),
    (0x621020, 0x30, "fighter_notify_shield", "Fighter +0x400: class +0x138(cls, fighter, w2, w3, x4)"),
    (0x614180, 0xE8, "fighter_attack_ratio", "Fighter +0x318: the attacker-side ratio the core multiplies by"),
    (0x68D800, 0x4, "class_default_damage", "base class +0x130: ret"),
    (0x68D810, 0x4, "class_default_shield", "base class +0x138: ret"),
    (0x21410D0, 0xC, "fm_one_on_one_ratio", "FighterManager::one_on_one_ratio = [[x0]+0xf0]"),
]
# (slot address, target, id) - relocated pointers the plugin compares before it writes.
SLOTS = [
    (EFLAME_CLASS + SLOT_DAMAGE, DEFAULT_DAMAGE, "eflame_class_damage"),
    (EFLAME_CLASS + SLOT_SHIELD, DEFAULT_SHIELD, "eflame_class_shield"),
    (ELIGHT_CLASS + SLOT_DAMAGE, DEFAULT_DAMAGE, "elight_class_damage"),
    (ELIGHT_CLASS + SLOT_SHIELD, DEFAULT_SHIELD, "elight_class_shield"),
    (FIGHTER_VTABLE + 0x318, 0x614180, "fighter_attack_ratio"),
    (FIGHTER_VTABLE + 0x3F8, 0x6204C0, "fighter_notify_attack"),
    (FIGHTER_VTABLE + 0x400, 0x621020, "fighter_notify_shield"),
]
# Instruction-level facts: (address, expected capstone text, what it establishes).
CORE_FACTS = [
    (0x854610, "ldr s0, [x5, #0x20]", "damage event: amount is AttackData.power at +0x20 of x5"),
    (0x854614, "mov x0, x1", "handler x1 is the fighter object"),
    (0x854618, "mov w1, w3", "handler w3 is the attacking object's id"),
    (0x85461C, "mov w3, wzr", "damage event enters the core with flag 0"),
    (0x854620, "b #0x854630", "damage thunk -> core"),
    (0x854B10, "ldr s0, [x4, #0x20]", "shield event: amount is AttackData.power at +0x20 of x4"),
    (0x854B1C, "orr w3, wzr, #1", "shield event enters the core with flag 1"),
    (0x854B24, "b #0x854630", "shield thunk -> core"),
    (0x85464C, "ldr x24, [x0, #0x20]", "accessor at fighter+0x20"),
    (0x854650, "ldr x21, [x24, #0x50]", "WorkModule of the fighter"),
    (0x854658, "mov w0, w2", "w2 (struck object id) is looked up first"),
    (0x8546BC, "ldrb w9, [x8, #0xc4]", "team rule byte 1 on FighterManager"),
    (0x8546C4, "ldrb w8, [x8, #0xc5]", "team rule byte 2 on FighterManager"),
    (0x854728, "ldr x10, [x10, #0xf8]", "entry -> info"),
    (0x854730, "ldr w10, [x10, #0x2c]", "info team id"),
    (0x85473C, "b.eq #0x854a6c", "same team: no award"),
    (0x854788, "cmp w8, #4", "attacking object category ITEM"),
    (0x854790, "cmp w8, #2", "attacking object category ENEMY"),
    (0x854794, "b.eq #0x854a6c", "an enemy's hit: no award"),
    (0x854798, "cmp w8, #1", "attacking object category WEAPON"),
    (0x8547A4, "cmp w8, #6", "weapon branch: only when the fighter kind is Kirby"),
    (0x8547B0, "cmp w8, #0x3d", "and only WEAPON_KIND_KIRBY_FINALCUTTERSHOT"),
    (0x8547BC, "ldr x0, [x8, #0xf8]", "ReflectModule of the weapon"),
    (0x8547C4, "ldr x8, [x8, #0xc0]", "ReflectModule::count"),
    (0x8547CC, "cbnz w0, #0x854a6c", "a reflected weapon: no award"),
    (0x8547E4, "mov w1, #9", "ITEM_INSTANCE_WORK_INT_TRAIT_FLAG low half"),
    (0x8547F0, "mov w8, #0x8c00", "item attacker trait mask"),
    (0x854850, "cmp w8, #0x54", "ITEM_KIND_KILLEREYESHOT excluded"),
    (0x854858, "cmp w8, #0x71", "ITEM_KIND_CHICKENPARTY excluded"),
    (0x854878, "b.gt #0x854a6c", "a reflected item: no award"),
    (0x854884, "cmp w9, #4", "struck object category bound"),
    (0x85488C, "cmp w9, #3", "struck gimmick: no award"),
    (0x8548CC, "mov w8, #0x8400", "struck item: ASSIST without WEAPON"),
    (0x8548D4, "mov w9, #0x9000", "struck item: BOSS without WEAPON"),
    (0x8548F0, "cmp w10, #0x1aa", "ITEM_KIND_SANDBAGHR counts"),
    (0x8548F8, "cmp w10, #8", "ITEM_KIND_SANDBAG counts"),
    (0x85490C, "cmp w8, #0xe6", "struck weapon: only WEAPON_KIND_ROSETTA_TICO"),
    (0x854964, "mov w1, #0xe5", "FIGHTER_BRAVE_INSTANCE_WORK_ID_FLAG_DISABLE_SP_AUTO_RECOVER low half"),
    (0x854968, "movk w1, #0x2000, lsl #16", "... = 0x200000e5"),
    (0x854974, "tbnz w0, #0, #0x854a6c", "flag set: no award"),
    (0x85497C, "ldr x0, [x23, #0xb0]", "HitModule of the struck object"),
    (0x854984, "ldr x8, [x8, #0x150]", "HitModule::get_total_status"),
    (0x854990, "cbnz w0, #0x854a6c", "struck object not HIT_STATUS_NORMAL: no award"),
    (0x8549B0, "ldr s9, [x8, #0xf0]", "FighterManager one_on_one_ratio"),
    (0x8549D4, "fmul s0, s9, s8", "power * one_on_one_ratio (fighter victims only)"),
    (0x8549DC, "ldrb w9, [x8, #0xce]", "ratio rule byte on FighterManager"),
    (0x8549FC, "ldr s2, [x9, #0x378]", "victim info value"),
    (0x854A00, "ldr s3, [x8, #0xb7c]", "common threshold"),
    (0x854A0C, "ldr s1, [x8, #0xb78]", "common victim scale"),
    (0x854A1C, "ldr s2, [x8, #0xb88]", "common victim floor"),
    (0x854A2C, "ldr x8, [x8, #0x318]", "attacker ratio: Fighter +0x318"),
    (0x854A3C, "fmul s8, s8, s0", "... multiplied in"),
    (0x854A4C, "tst w20, #1", "flag selects the multiplier"),
    (0x854A50, "mov w9, #0xbc", "flag 0: param +0xbc"),
    (0x854A54, "orr w10, wzr, #0xc0", "flag 1: param +0xc0"),
    (0x854A58, "csel x9, x10, x9, ne", "select"),
    (0x854A60, "fmul s0, s8, s0", "amount = scaled power * multiplier"),
    (0x854A68, "bl #0x853890", "add_sp"),
    # passive recovery: the two fields in front of the multipliers
    (0x853618, "ldr w8, [x23, #0xb4]", "passive recovery reads sp_recover_frame at +0xb4"),
    (0x85363C, "ldr s0, [x23, #0xb8]", "passive recovery reads recover_sp at +0xb8"),
    (0x853628, "sub w1, w19, #3", "passive recovery tests the same DISABLE_SP_AUTO_RECOVER flag"),
    # dispatch
    (0x620ECC, "mov w8, #0xf700", "class object at fighter+0xf700"),
    (0x620EDC, "ldr x8, [x8, #0x130]", "Fighter +0x3f8 calls class +0x130"),
    (0x620EE4, "mov x1, x24", "x1 = fighter"),
    (0x620EE8, "mov w2, w22", "w2 = struck id (the method's w1)"),
    (0x620EEC, "mov w3, w21", "w3 = attacking id (the method's w2)"),
    (0x620EF4, "mov x5, x19", "x5 = AttackData (the method's x4)"),
    (0x621030, "ldr x5, [x9, #0x138]", "Fighter +0x400 calls class +0x138"),
    (0x621034, "mov x4, x3", "x4 = AttackData (the method's x3)"),
    (0x621038, "mov w3, w2", "w3 = attacking id"),
    (0x62103C, "mov w2, w1", "w2 = struck id"),
    # engine call sites
    (0x40282C, "ldr w2, [x25, #0x24]", "damage path: w2 = attacking object id from the hit log"),
    (0x402850, "ldr x8, [x8, #0x3f8]", "damage path raises Fighter +0x3f8 on the attacker's owner"),
    (0x402854, "mov x4, x20", "... with the hit's AttackData"),
    (0x4027F8, "ldr x8, [x8, #0xa8]", "damage path: TeamModule::team_owner_id of the attacking object"),
    (0x4C7210, "ldr x8, [x8, #0x400]", "shield path raises Fighter +0x400 on the attacker's owner"),
    (0x4C71A8, "ldr x8, [x8, #0x1e8]", "shield path: AttackModule::attack_data"),
    (0x4C71C0, "ldr x8, [x8, #0xa8]", "shield path: TeamModule::team_owner_id"),
]
# lua_bind thunks whose exported name identifies a module virtual: (module offset, vtable offset, name part)
THUNKS = [
    (0xB0, 0x150, "HitModule__get_total_status_impl"),
    (0xF8, 0xC0, "ReflectModule__count_impl"),
    (0xA0, 0x1E8, "AttackModule__attack_data_impl"),
    (0xD8, 0xA8, "TeamModule__team_owner_id_impl"),
    (0x50, 0x108, "WorkModule__is_flag_impl"),
    (0x50, 0x98, "WorkModule__get_int_impl"),
]


def fnv1a64(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for b in data:
        h = ((h ^ b) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


class Image:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        self.sha256 = hashlib.sha256(self.data).hexdigest()
        import capstone
        self.md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        self._relocs = None
        self._syms = None

    def _dynamic(self) -> dict[int, int]:
        d = self.data
        mod0 = struct.unpack_from("<I", d, 4)[0]
        i = mod0 + struct.unpack_from("<i", d, mod0 + 4)[0]
        tags: dict[int, int] = {}
        while True:
            t, v = struct.unpack_from("<qQ", d, i)
            i += 16
            if t == 0:
                return tags
            tags.setdefault(t, v)

    @property
    def relocs(self) -> dict[int, int]:
        if self._relocs is None:
            tags = self._dynamic()
            off, size = tags[7], tags[8]
            out = {}
            for k in range(0, size, 24):
                r_off, r_info, addend = struct.unpack_from("<QQq", self.data, off + k)
                if r_info & 0xFFFFFFFF == 0x403:
                    out[r_off] = addend
            self._relocs = out
        return self._relocs

    @property
    def symbols(self) -> dict[int, str]:
        if self._syms is None:
            tags = self._dynamic()
            symtab, strtab = tags[6], tags[5]
            out, k = {}, 1
            while symtab + k * 24 < strtab:
                name, _info, _other, shndx, value, _size = struct.unpack_from("<IBBHQQ", self.data, symtab + k * 24)
                if shndx and value:
                    e = self.data.index(b"\0", strtab + name)
                    out[value] = self.data[strtab + name:e].decode("latin1")
                k += 1
            self._syms = out
        return self._syms

    def ptr(self, slot: int) -> int | None:
        return self.relocs.get(slot)

    def ins(self, off: int) -> str:
        got = list(self.md.disasm(self.data[off:off + 4], off))
        return f"{got[0].mnemonic} {got[0].op_str}".strip() if got else ".word"

    def listing(self, off: int, size: int) -> list[str]:
        return [f"{a:#010x} {self.data[a:a + 4][::-1].hex()} {self.ins(a)}" for a in range(off, off + size, 4)]

    def vtable_start(self, slot: int) -> int:
        b = slot
        while (b - 8) in self.relocs:
            b -= 8
        return b

    def thunk(self, module: int, vt: int) -> list[str]:
        want0 = 0xF9400000 | ((module // 8) << 10)
        out = []
        for addr, name in self.symbols.items():
            if "lua_bind" not in name:
                continue
            w = struct.unpack_from("<3I", self.data, addr)
            if w[0] == want0 and w[1] == 0xF9400008 and (w[2] & 0xFFC00000) == 0xF9400000 \
                    and ((w[2] >> 10) & 0xFFF) == vt // 8 and ((w[2] >> 5) & 31) == 8:
                out.append(name)
        return out


def rust_table(img: Image) -> str:
    lines = [
        "// Generated by tools/audit_hero_mana_recovery.py --emit-rust. Do not edit.",
        "// Every span is a function the owned hit/shield recovery handlers rely on,",
        f"// hashed on the 13.0.4 main image sha256 {MAIN_SHA256}.",
        "// (offset, length, fnv1a64, id)",
        "pub(super) const SPANS: &[(usize, usize, u64, &str)] = &[",
    ]
    for off, size, ident, _why in SPANS:
        lines.append(f"    ({off:#x}, {size:#x}, {fnv1a64(img.data[off:off + size]):#018x}, \"{ident}\"),")
    lines += ["];", "// (slot, target, id): the relocated pointer at `slot` must be `base + target`.",
              "pub(super) const SLOTS: &[(usize, usize, &str)] = &["]
    for slot, target, ident in SLOTS:
        lines.append(f"    ({slot:#x}, {target:#x}, \"{ident}\"),")
    lines += ["];", ""]
    return "\n".join(lines)


def audit(img: Image, negative: bool) -> tuple[list[dict], int]:
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    check("main sha256", img.sha256 == MAIN_SHA256, img.sha256)
    for addr, want, why in CORE_FACTS:
        got = img.ins(addr)
        check(f"ins {addr:#x}", got == want, f"{got!r} want {want!r}: {why}")
    for slot, target, ident in SLOTS:
        check(f"slot {ident}", img.ptr(slot) == target, f"[{slot:#x}] = {img.ptr(slot) and hex(img.ptr(slot))} want {target:#x}")
    check("default +0x130 is ret", img.data[DEFAULT_DAMAGE:DEFAULT_DAMAGE + 4] == RET)
    check("default +0x138 is ret", img.data[DEFAULT_SHIELD:DEFAULT_SHIELD + 4] == RET)
    # class tables really start where the plugin says (no relocated slot directly in front)
    for name, base in (("brave", BRAVE_CLASS), ("eflame", EFLAME_CLASS), ("elight", ELIGHT_CLASS),
                       ("gamewatch", GAMEWATCH_CLASS), ("fighter", FIGHTER_VTABLE)):
        check(f"{name} vtable start", img.vtable_start(base + 0x100) == base, hex(img.vtable_start(base + 0x100)))
    # positive control: Hero's class owns both slots; control class G&W keeps the defaults
    check("brave class +0x130 is his handler", img.ptr(BRAVE_CLASS + SLOT_DAMAGE) == 0x854610)
    check("brave class +0x138 is his handler", img.ptr(BRAVE_CLASS + SLOT_SHIELD) == 0x854B10)
    check("gamewatch class keeps defaults", img.ptr(GAMEWATCH_CLASS + SLOT_DAMAGE) == DEFAULT_DAMAGE
          and img.ptr(GAMEWATCH_CLASS + SLOT_SHIELD) == DEFAULT_SHIELD)
    # exactly one branch into the core from each thunk, and nothing else reaches it
    callers = []
    for off in range(0x100, 0x39C8000, 4):
        w = struct.unpack_from("<I", img.data, off)[0]
        if w >> 26 in (0x05, 0x25):
            imm = w & 0x3FFFFFF
            if imm & 0x2000000:
                imm -= 0x4000000
            if off + imm * 4 == 0x854630:
                callers.append(off)
    check("core is entered only from the two thunks", callers == [0x854620, 0x854B24], str([hex(c) for c in callers]))
    for module, vt, part in THUNKS:
        names = img.thunk(module, vt)
        check(f"thunk [{module:#x}]->vt[{vt:#x}] is {part}", len(names) == 1 and part in names[0], str(names))
    one = img.symbols.get(0x21410D0, "")
    check("0x21410d0 is FighterManager::one_on_one_ratio", "FighterManager__one_on_one_ratio_impl" in one, one)
    check("one_on_one_ratio reads +0xf0", img.ins(0x21410D4) == "ldr s0, [x8, #0xf0]", img.ins(0x21410D4))
    # the shield call site sits in a function owned by the ShieldModule vtable family
    fam = sorted(o for o, a in img.relocs.items() if a == 0x4C7080)
    check("shield call site function 0x4c7080 is a single-class virtual", len(fam) == 1, str([hex(x) for x in fam]))

    controls = 0
    if negative:
        def expect_fail(name: str, failed: bool, detail: str = "") -> None:
            nonlocal controls
            controls += 1
            checks.append({"check": f"negative control: {name}", "ok": bool(failed), "detail": detail})

        off, size, ident, _ = SPANS[2]
        good = fnv1a64(img.data[off:off + size])
        flipped = bytearray(img.data[off:off + size])
        flipped[0x41C] ^= 0x01  # inside the multiplier select
        expect_fail("one flipped bit in the core changes its signature", fnv1a64(bytes(flipped)) != good)
        expect_fail("a neighbouring slot is not Hero's handler", img.ptr(BRAVE_CLASS + 0x128) != 0x854610,
                    hex(img.ptr(BRAVE_CLASS + 0x128) or 0))
        expect_fail("Hero's class would be refused as a recipient (slot is not the default)",
                    img.ptr(BRAVE_CLASS + SLOT_DAMAGE) != DEFAULT_DAMAGE)
        table = rust_table(img)
        expect_fail("a table with one changed hash differs from the generated one",
                    table.replace(f"{good:#018x}", f"{good ^ 1:#018x}") != table)
        expect_fail("the shield thunk does not read x5", img.ins(0x854B10) != "ldr s0, [x5, #0x20]", img.ins(0x854B10))
    return checks, controls


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--main", required=True, help="decoded 13.0.4 main.bin")
    ap.add_argument("--python-path")
    ap.add_argument("--check", action="store_true", help="also run the negative controls")
    ap.add_argument("--emit-rust", help="write the plugin's signature table here")
    ap.add_argument("--check-rust", help="fail unless this file equals the generated table")
    ap.add_argument("--listing", help="write the disassembly of every span here")
    ap.add_argument("--json")
    ap.add_argument("--nro", help="NRO that must carry every span hash")
    ap.add_argument("--nro-without", help="NRO that must carry none of them (negative control)")
    args = ap.parse_args()
    for p in (args.python_path, os.environ.get("PGWR_PYLIBS")):
        if p:
            sys.path.insert(0, str(Path(p).resolve()))
    img = Image(Path(args.main))
    checks, controls = audit(img, args.check)
    table = rust_table(img)
    if args.emit_rust:
        Path(args.emit_rust).write_text(table, encoding="utf-8", newline="\n")
    if args.check_rust:
        got = Path(args.check_rust).read_text(encoding="utf-8").replace("\r\n", "\n")
        checks.append({"check": "signature table equals the generated one", "ok": got == table, "detail": args.check_rust})
    hashes = [struct.pack("<Q", fnv1a64(img.data[o:o + s])) for o, s, _i, _w in SPANS if s > 4]
    if args.nro:
        blob = Path(args.nro).read_bytes()
        n = sum(h in blob for h in hashes)
        checks.append({"check": "NRO carries every span hash", "ok": n == len(hashes), "detail": f"{n}/{len(hashes)} in {args.nro}"})
    if args.nro_without:
        blob = Path(args.nro_without).read_bytes()
        n = sum(h in blob for h in hashes)
        checks.append({"check": "negative control: NRO without the route carries no span hash", "ok": n == 0,
                       "detail": f"{n}/{len(hashes)} in {args.nro_without}"})
        controls += 1
    if args.listing:
        out = [f"# Hero hit/shield recovery route, 13.0.4 main sha256 {img.sha256}",
               f"# tools/audit_hero_mana_recovery.py v{VERSION} --listing", ""]
        for off, size, ident, why in SPANS:
            out += [f"## {ident}  {off:#x}..{off + size:#x}  fnv1a64 {fnv1a64(img.data[off:off + size]):#018x}", f"## {why}"]
            out += img.listing(off, size) + [""]
        for label, off, size in (("engine damage-path call site", 0x4027E0, 0x88),
                                 ("engine shield-path call site", 0x4C7188, 0x94),
                                 ("passive recovery field reads", 0x853600, 0x48)):
            out += [f"## {label}  {off:#x}..{off + size:#x}"] + img.listing(off, size) + [""]
        Path(args.listing).write_text("\n".join(out), encoding="utf-8", newline="\n")
    failed = [c for c in checks if not c["ok"]]
    report = {"tool": f"tools/audit_hero_mana_recovery.py v{VERSION}", "tier": "B",
              "main": {"sha256": img.sha256, "bytes": len(img.data)},
              "checks": len(checks), "failed": len(failed), "negative_controls": controls,
              "spans": [{"id": i, "offset": hex(o), "length": hex(s), "fnv1a64": f"{fnv1a64(img.data[o:o + s]):#018x}",
                         "sha256": hashlib.sha256(img.data[o:o + s]).hexdigest(), "why": w} for o, s, i, w in SPANS],
              "slots": [{"id": i, "slot": hex(s), "target": hex(t)} for s, t, i in SLOTS],
              "results": checks}
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    for c in failed:
        print("FAIL", c["check"], c["detail"])
    print(f"audit_hero_mana_recovery {VERSION}: {len(checks) - len(failed)}/{len(checks)} checks, "
          f"{controls} negative controls, {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
