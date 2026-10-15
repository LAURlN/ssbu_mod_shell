#!/usr/bin/env python3
"""check_p11_row_text.py - acceptance check for task P11-ROW-TEXT.

Re-reads the pinned image and the extracted message files and verifies every
instruction word, branch target, relocation, string and label fact cited in
research/P11-ROW-TEXT.md.  Stdlib only (the msbt reader is the mod's own
tools/stat-presets/msbt.py).

  python mods/mii_customizer/evidence/P11-ROW-TEXT/check_p11_row_text.py          # all pass -> exit 0
  python mods/mii_customizer/evidence/P11-ROW-TEXT/check_p11_row_text.py --neg    # 5 deliberate
                                                                                 # corruptions -> exit 1

Any mismatch prints a `MISMATCH:` line and the script exits 1.
"""
from __future__ import annotations

import hashlib
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
IMAGE_PATH = os.path.join(ROOT, "gamedata", "ssbu-13.0.4", "main.bin")
IMAGE_SHA256 = "f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613"
MSG_DIR = os.path.join(ROOT, "gamedata", "mii_customizer", "P11-ROW-TEXT", "ui", "message")
sys.path.insert(0, os.path.join(ROOT, "mods", "mii_customizer", "tools", "stat-presets"))
import msbt  # noqa: E402

failures: list[str] = []
checks = 0

# ---------------------------------------------------------------- helpers ---


def check(cond: bool, desc: str) -> None:
    global checks
    checks += 1
    if not cond:
        failures.append(f"MISMATCH: {desc}")


def u32(data: bytes, addr: int) -> int:
    return struct.unpack_from("<I", data, addr)[0]


def u16(data: bytes, addr: int) -> int:
    return struct.unpack_from("<H", data, addr)[0]


def rela(data: bytes, rec: int):
    off, info, add = struct.unpack_from("<QQq", data, rec)
    return off, info, add & 0xFFFFFFFFFFFFFFFF


def branch_target(w: int, addr: int):
    """Decode b/bl/b.cond/cbz/cbnz/tbz/tbnz targets; None if not a branch."""
    if (w & 0x7C000000) == 0x14000000:                      # b / bl (imm26)
        imm = w & 0x3FFFFFF
        if imm & 0x2000000:
            imm -= 0x4000000
        return addr + (imm << 2)
    if (w & 0xFF000010) == 0x54000000:                      # b.cond (imm19)
        imm = (w >> 5) & 0x7FFFF
        if imm & 0x40000:
            imm -= 0x80000
        return addr + (imm << 2)
    if (w & 0x7E000000) in (0x34000000, 0x36000000):        # cbz/cbnz/tbz/tbnz (imm19/14)
        if (w & 0x7E000000) == 0x34000000:
            imm = (w >> 5) & 0x7FFFF
            if imm & 0x40000:
                imm -= 0x80000
        else:
            imm = (w >> 5) & 0x3FFF
            if imm & 0x2000:
                imm -= 0x4000
        return addr + (imm << 2)
    return None


def adrp_page(w: int, addr: int):
    if (w & 0x9F000000) != 0x90000000:
        return None
    imm = (((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3)
    if imm & 0x100000:
        imm -= 0x200000
    return (addr & ~0xFFF) + (imm << 12)


# ------------------------------------------------- expected instruction words ---
# addr -> word, taken from the disassembler on the pinned image (tier B).
WORD_EXPECT_TEXT = """
0x019ccbec 0x9462edd1
0x019ccc00 0x9476a5d8
0x019ccc10 0x9476b3d8
0x019ccc3c 0x9476a5c9
0x019ccc48 0x9476b3ca
0x03779b70 0xf81c0ffc
0x03779b74 0xa90157f6
0x03779b78 0xa9024ff4
0x03779b7c 0xa9037bfd
0x03779ba8 0xf9400409
0x03779bac 0xf9400929
0x03779bb0 0xb4000829
0x03779c60 0xb0010e08
0x03779c64 0xf9463108
0x03779c70 0x9400a88c
0x03779c9c 0x9400cfc9
0x03779cb0 0x9400a004
0x03776360 0xd10603ff
0x03776364 0xa9145ffc
0x03776368 0xa91557f6
0x0377636c 0xa9164ff4
0x03776458 0xf9000288
0x037764b0 0xf9000696
0x037764e4 0x97fff10f
0x037764f4 0xf9000ac0
0x037a3ea0 0xa9bd57f6
0x037a3ea4 0xa9014ff4
0x037a3ea8 0xa9027bfd
0x037a3eac 0x910083fd
0x037a3ee4 0x97217157
0x037a3f4c 0x3941a10b
0x037a3f78 0x9101c108
0x037a3f94 0x9721712b
0x00000440 0xa9ba6ffc
0x0000045c 0xb9802008
0x00000464 0x54000520
0x037adbe4 0xb4002081
0x037adbe8 0x79400028
0x037adbf0 0x34002028
0x037adff4 0x2a1f03f6
0x037adff8 0x7836da7f
0x037ae000 0x2a1603e0
0x037a1cc0 0xa9bd57fc
0x037a1cc4 0xa9014ff4
0x037a1cc8 0xa9027bfd
0x037a1ccc 0x910083fd
0x037a1ce4 0x36000be3
0x01977480 0x9126ba94
0x0197760c 0x910042f7
0x01977610 0xf10342ff
0x01977624 0xf001fe08
0x01977628 0xf9463108
0x019ccd84 0x9462fa13
0x019ccd88 0x36000060
0x019ccd8c 0x3945a668
0x019ccd90 0x340004e8
0x019ccda4 0x320003e1
0x019ccdb0 0xd63f0100
0x019cce40 0x2a1f03e1
0x019cce44 0xd63f0100
0x019ccce8 0x321c03e0
0x019cccec 0x321d03e1
0x019cccf0 0x947d83fc
0x019ccd64 0x94772703
0x019ccd70 0xf90002e0
0x0335a490 0xf81d0ff5
0x0335a494 0xa9014ff4
0x0335a498 0xa9027bfd
0x0335a49c 0x910083fd
0x0335a54c 0xf94006a8
0x0335a550 0xf9400900
0x0335a554 0xb4000040
0x0335a558 0x94111f66
0x037a22f0 0xf81d0ffc
0x037a22f4 0xa9014ff4
0x037a22f8 0xa9027bfd
0x037a22fc 0x910083fd
0x037a23a0 0xf11ff85f
0x037a23d0 0x910003e1
0x037a23d4 0x320003e3
0x037a23d8 0xaa1303e0
0x037a23dc 0x97fffe39
0x03370e28 0xf000f081
0x03370e2c 0x91098021
0x03370e30 0x52805202
0x03370e40 0x900082e1
0x03370e44 0x912b0821
0x03370e4c 0x94161799
0x0377c76c 0xf9400908
0x0377c770 0xd63f0100
0x019cc52c 0x3945a668
0x019cc530 0x34001ae8
0x019cc548 0x9462fc22
0x019cc554 0x3905a67f
0x019cc5d8 0xf9400908
0x019cc5dc 0xd63f0100
0x019cc75c 0x3905a67f
0x019cc7e4 0xd63f0100
0x0377db50 0xb9029e74
0x0377db54 0x97fffadf
0x03363140 0x94106564
0x019cd010 0xd1012000
0x019cd014 0x17fffec3
0x0378a6cc 0x39070801
0x0378a6f0 0x39470800
0x0378a710 0x39470c00
0x0377e27c 0xf9410108
0x0377e288 0x360005a0
0x0377e290 0xf9410908
0x0377e29c 0x36000500
0x0377e2a4 0xb902b268
0x0377e33c 0xf940a260
0x0377e340 0xb5ff96c0
0x019cceec 0x9462f9b9
0x019ccf10 0x0b150288
0x019ccf14 0x7100029f
0x019ccf18 0x1a93c100
0x019cd070 0x9462f958
0x019cd084 0x0b1302a8
0x019cd088 0x710002bf
0x019cd08c 0x1a94c113
0x019cd0d8 0x9462f93e
0x019cd0dc 0x36000060
0x019cd0e4 0x34000068
0x019cd0f0 0x320003e0
"""
WORD_EXPECT = {}
_lines = [ln.split() for ln in WORD_EXPECT_TEXT.strip().splitlines()]
for _a, _w in _lines:
    WORD_EXPECT[int(_a, 16)] = int(_w, 16)

# ------------------------------------------------------------- branch targets ---
# addr -> expected target (decoded from the word; wrong table entries fail here)
BRANCH_EXPECT = {
    0x19CCBEC: 0x3288330,   # row filler -> label builder
    0x19CCC00: 0x3776360,   # find set_txt_val
    0x19CCC10: 0x3779B70,   # set text from key
    0x19CCC3C: 0x3776360,   # find set_txt_val_disable
    0x19CCC48: 0x3779B70,
    0x3779C70: 0x37A3EA0,   # message lookup
    0x3779C9C: 0x37ADBC0,   # expand
    0x3779CB0: 0x37A1CC0,   # apply
    0x3779BB0: 0x3779CB4,   # cbz: no inner pane -> early ret
    0x37A3EE4: 0x440,       # per-table label lookup (tree)
    0x37A3F94: 0x440,       # per-table label lookup (vector)
    0x37764E4: 0x3772920,   # typed getter A
    0x000464: 0x508,        # 0x440 miss -> return 0
    0x37ADBE4: 0x37ADFF4,   # expander: null source -> return 0
    0x37ADBF0: 0x37ADFF4,   # expander: first unit 0 -> return 0
    0x37A1CE4: 0x37A1E60,   # apply: w3 bit0 clear -> skip recompute
    0x19CCD84: 0x328B5D0,   # registry test (filler)
    0x19CCD88: 0x19CCD94,   # in table -> normal branch
    0x19CCD90: 0x19CCE2C,   # not in table + flag 0 -> greyed branch
    0x19CC530: 0x19CC88C,   # frame model block gate: flag 0 -> skip
    0x19CC548: 0x328B5D0,   # ownership test (frame)
    0x19CCCF0: 0x392DCE0,   # cell alloc
    0x19CCD64: 0x3796970,   # icon fetch
    0x335A554: 0x335A55C,   # cbz: no pane -> skip
    0x335A558: 0x37A22F0,   # Lua set_text_string -> UTF-8 setter
    0x37A23DC: 0x37A1CC0,   # UTF-8 setter -> final apply (w3=1)
    0x3370E4C: 0x38F6CB0,   # metatable registration
    0x377DB54: 0x377C6D0,   # scroll -> redraw entry
    0x3363140: 0x377C6D0,   # Lua redraw_all_items -> redraw entry
    0x19CD014: 0x19CCB20,   # thunk -> row filler
    0x377E288: 0x377E33C,   # decide: +0x200 fails -> refusal
    0x377E29C: 0x377E33C,   # decide: +0x210 fails -> refusal
    0x377E340: 0x377D618,   # refusal: optional [scroller+0x140] call
    0x19CCEEC: 0x328B5D0,   # helpers: registry test
    0x19CD070: 0x328B5D0,
    0x19CD0D8: 0x328B5D0,
    0x19CD0DC: 0x19CD0E8,   # predicate: in table -> 0
    0x19CD0E4: 0x19CD0F0,   # predicate: flag 0 -> 1
}

# first-four words of the entries named in Q2/Q1 that must not be PC-relative
PCREL_GUARD = [
    0x335A490, 0x335A494, 0x335A498, 0x335A49C,
    0x37A22F0, 0x37A22F4, 0x37A22F8, 0x37A22FC,
    0x37A1CC0, 0x37A1CC4, 0x37A1CC8, 0x37A1CCC,
    0x3779B70, 0x3779B74, 0x3779B78, 0x3779B7C,
    0x3776360, 0x3776364, 0x3776368, 0x377636C,
]

# --------------------------------------------------------------- relocations ---
# record -> (slot offset, info, addend)
RELA_EXPECT = {
    # MetatableLayoutPane name/handler slots
    0x3EA7050: (0x51833B0, 0x403, 0x42D3B08),   # "set_text_message"
    0x3EA7068: (0x51833B8, 0x403, 0x335A100),
    0x3EA7080: (0x51833C0, 0x403, 0x42E4844),   # "set_text_message_args"
    0x3EA7098: (0x51833C8, 0x403, 0x335A1E0),
    0x3EA70B0: (0x51833D0, 0x403, 0x42E485A),   # "set_text_args"
    0x3EA70E0: (0x51833E0, 0x403, 0x439A8B9),   # "set_text_string"
    0x3EA70F8: (0x51833E8, 0x403, 0x335A490),   # its handler
    0x3EA7110: (0x51833F0, 0x403, 0x4316617),   # "set_text_string_16"
    0x3EA7128: (0x51833F8, 0x403, 0x335A570),
    0x3EA7140: (0x5183400, 0x403, 0x4369AD8),   # "clear_text_string"
    0x3EA7158: (0x5183408, 0x403, 0x335A620),
    # row-callback vtables
    0x3CF48A8: (0x50A6B08, 0x403, 0x19CCA40),
    0x3CF48D8: (0x50A6B18, 0x403, 0x19CCB20),   # primary +0x38 = row filler
    0x3CF4938: (0x50A6B48, 0x403, 0x19CD010),   # secondary +0x10 = thunk
    # button-class vtables: +0x1f8 / +0x200
    0x4092750: (0x523D000, 0x403, 0x378A6C0),
    0x4092768: (0x523D008, 0x403, 0x378A6F0),
}

# ------------------------------------------------------------------- strings ---
STRING_EXPECT = {
    0x425E382: b"set_txt_val",
    0x436AC1A: b"set_txt_val_disable",
    0x439A9AE: b"ui/message/msg_%s.msbt",
    0x42E49A3: b"/message/msg_%s+%%s.msbt",
    0x439A8B9: b"set_text_string",
    0x43CCAC2: b"MetatableLayoutPane",
    0x42D3B08: b"set_text_message",
    0x42E4844: b"set_text_message_args",
    0x4316617: b"set_text_string_16",
    0x4369AD8: b"clear_text_string",
    0x42E485A: b"set_text_args",
    # relocated names of the 13-entry msbt name table
    0x43BBD5B: b"system",
    0x43AB0B9: b"common",
    0x43CCB7D: b"popup",
    0x4316BA6: b"name",
    0x441FBBC: b"melee",
    0x439A9C5: b"menu",
    0x42F54E3: b"spirits",
    0x44308A1: b"campaign",
    0x43AB0C0: b"bgm",
    0x4327749: b"staff",
    0x4347A98: b"tips",
    0x42E49BC: b"script",
    0x43AB0C4: b"title",
}

# name table at 0x5184f40: 13 x {3-char tag, +8 relocated name pointer}
NAME_TABLE = [
    (b"sys", 0x43BBD5B, b"system"),
    (b"cmn", 0x43AB0B9, b"common"),
    (b"pop", 0x43CCB7D, b"popup"),
    (b"nam", 0x4316BA6, b"name"),
    (b"mel", 0x441FBBC, b"melee"),
    (b"mnu", 0x439A9C5, b"menu"),
    (b"spi", 0x42F54E3, b"spirits"),
    (b"cam", 0x44308A1, b"campaign"),
    (b"bgm", 0x43AB0C0, b"bgm"),
    (b"stf", 0x4327749, b"staff"),
    (b"tip", 0x4347A98, b"tips"),
    (b"scr", 0x42E49BC, b"script"),
    (b"tit", 0x43AB0C4, b"title"),
]

# -------------------------------------------------------------------- msbt ----
MSG_SHA256 = {
    "msg_bgm.msbt": "87dfdaa67c472309c2a007247730bca396fb78f616e260bdc4fd66982d4fc996",
    "msg_campaign.msbt": "a8dbca58bedcf3700dbd5fb4185f2218e9d2553f409952bec8e103b5b7e09a07",
    "msg_common.msbt": "f1a0e6e328cf49366959d00f10e9ed62faf6ea129f067414117e632eab6643fa",
    "msg_melee.msbt": "cee272e95d08ad8a5e867e0ad3e1752c7554bc1dffbb5947c6c086ac60bca239",
    "msg_menu.msbt": "4b4f3d23640032858334ab0b51939f3675271cad326131bcb5c70c1a4f25b26b",
    "msg_name.msbt": "9efc357db8ea46e671222dbbd90bbdc0ea5455383090fae3fe2ba6017e9da3ad",
    "msg_popup.msbt": "e9f3913bb5fcc32df233c702668d5bfd5a2f380af5a7df2101a4ec9885a1ca1d",
    "msg_script.msbt": "a55f9865079bb5b69c6277d4c9f2714d88b019d4a71dbea0a91e8848de56b5ea",
    "msg_spirits.msbt": "de971c361d73d2a2373dcd0d334964f3711ea00b06ee8ded338f872c1ba9aafc",
    "msg_staff.msbt": "6da03d41c27b2690f096e7dfa64344f8c9ace8b8a4c9acf671b2469b7f924c1b",
    "msg_system.msbt": "81aac6eb1cea10496637b73ed1e0b3dacdfaf153dcbc38daa9577303977ec608",
    "msg_tips.msbt": "9c214b102863336338aab6ff3c06dc2a763e8b9c92b8beaea353fde904b71abf",
    "msg_title.msbt": "f058bc8c7b05896fde35a50bfa871e8bf4cb5cff7f1a22275797161218c82c44",
}
MSG_PREFIX = {
    "msg_bgm.msbt": "bgm", "msg_campaign.msbt": "cam", "msg_common.msbt": "cmn",
    "msg_melee.msbt": "mel", "msg_menu.msbt": "mnu", "msg_name.msbt": "nam",
    "msg_popup.msbt": "pop", "msg_script.msbt": "scr", "msg_spirits.msbt": "spi",
    "msg_staff.msbt": "stf", "msg_system.msbt": "sys", "msg_tips.msbt": "tip",
    "msg_title.msbt": "tit",
}
MSG_LABEL_COUNTS = {
    "msg_bgm.msbt": 2696, "msg_campaign.msbt": 678, "msg_common.msbt": 222,
    "msg_melee.msbt": 1337, "msg_menu.msbt": 3342, "msg_name.msbt": 3839,
    "msg_popup.msbt": 545, "msg_script.msbt": 2384, "msg_spirits.msbt": 1441,
    "msg_staff.msbt": 1916, "msg_system.msbt": 11, "msg_tips.msbt": 4406,
    "msg_title.msbt": 586,
}
# raw TXT2 text (trailing NUL included) of every exact-match label the report cites
EXACT_TEXTS = {
    ("msg_menu.msbt", "mnu_record_count_title"): "Stats\x00",
    ("msg_menu.msbt", "mnu_coll_record_top_count"): "Stats\x00",
    ("msg_common.msbt", "cmn_hold"): "Grab\x00",
    ("msg_menu.msbt", "mnu_opt_btn_key_hold"): "Grab\x00",
    ("msg_menu.msbt", "mnu_spirits_select_refine_sort_03"): "Grab\x00",
    ("msg_popup.msbt", "pop_opt_btn_key_noassign_grab"): "Grab \x00",
    ("msg_tips.msbt", "tip_title_0995"): "Grab\x00",
    ("msg_melee.msbt", "mel_training_cp_attack"): "Neutral Special\x00",
    ("msg_menu.msbt", "mnu_mmiif_setup_sp_move_normal"): "Neutral Special\x00",
    ("msg_menu.msbt", "mnu_mmiif_setup_sp_move_width"): "Side Special\x00",
    ("msg_menu.msbt", "mnu_mmiif_setup_sp_move_up"): "Up Special\x00",
    ("msg_menu.msbt", "mnu_mmiif_setup_sp_move_btm"): "Down Special\x00",
    ("msg_menu.msbt", "mnu_opt_btn_ctrl_init"): "Default\x00",
    ("msg_melee.msbt", "mel_chara_select_without"): "None\x00",
    ("msg_melee.msbt", "mel_rule_item_freq_00"): "None\x00",
    ("msg_menu.msbt", "mnu_controller_assign_none"): "None\x00",
    ("msg_menu.msbt", "mnu_opt_btn_key_smash"): "Smash Attack\x00",
    ("msg_melee.msbt", "mel_training_cp_smash_side"): "Side Smash\x00",
    ("msg_name.msbt", "nam_spirits_skill_dash_attack_offense_up"):
        "Dash Attack \ue092\x00",
}
WANTED = [
    "Stats", "Jab", "Dash Attack",
    "Forward Tilt", "Up Tilt", "Down Tilt",
    "Forward Smash", "Up Smash", "Down Smash",
    "Neutral Air", "Forward Air", "Back Air", "Up Air", "Down Air",
    "Grab", "Pummel",
    "Forward Throw", "Back Throw", "Up Throw", "Down Throw",
    "Neutral Special", "Side Special", "Up Special", "Down Special",
    "Default", "None",
]
# wanted texts the report says have NO exact label anywhere
WANTED_NO_EXACT = [
    "Jab", "Dash Attack",
    "Forward Tilt", "Up Tilt", "Down Tilt",
    "Forward Smash", "Up Smash", "Down Smash",
    "Neutral Air", "Forward Air", "Back Air", "Up Air", "Down Air",
    "Pummel",
    "Forward Throw", "Back Throw", "Up Throw", "Down Throw",
]
# wanted texts the report says have >= 1 exact label
WANTED_HAS_EXACT = [
    "Stats", "Grab", "Neutral Special", "Side Special", "Up Special",
    "Down Special", "Default", "None",
]
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def clean(text: str) -> str:
    return CONTROL.sub("", text).strip()


def fold(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# --------------------------------------------------------------------- main ---


def main() -> int:
    neg = "--neg" in sys.argv[1:]

    data = open(IMAGE_PATH, "rb").read()

    # 0. image identity
    got = hashlib.sha256(data).hexdigest()
    check(got == IMAGE_SHA256, f"image sha256 expected {IMAGE_SHA256} got {got}")

    # 1. instruction words
    for addr, want in sorted(WORD_EXPECT.items()):
        got = u32(data, addr)
        check(got == want,
              f"word at 0x{addr:08x} expected 0x{want:08x} got 0x{got:08x}")

    # 2. branch targets (decoded independently of the word table)
    for addr, want in sorted(BRANCH_EXPECT.items()):
        got = branch_target(u32(data, addr), addr)
        check(got == want,
              f"branch at 0x{addr:08x} expected target 0x{want:x} got "
              + (f"0x{got:x}" if got is not None else "not a branch"))

    # 3. no PC-relative instructions among the cited entry prologues
    for addr in PCREL_GUARD:
        w = u32(data, addr)
        is_adrp = adrp_page(w, addr) is not None
        is_b = (w & 0x7C000000) == 0x14000000
        check(not (is_adrp or is_b),
              f"entry word 0x{addr:08x} must not be PC-relative "
              f"(adrp={is_adrp}, b/bl={is_b})")

    # 4. adrp page cited for the manager global
    w = u32(data, 0x3779C60)
    check(adrp_page(w, 0x3779C60) == 0x593A000,
          f"adrp at 0x3779c60 expected page 0x593a000 got "
          f"{hex(adrp_page(w, 0x3779C60) or 0)}")
    w = u32(data, 0x1977624)
    check(adrp_page(w, 0x1977624) == 0x593A000,
          f"adrp at 0x1977624 expected page 0x593a000 got "
          f"{hex(adrp_page(w, 0x1977624) or 0)}")

    # 5. relocations
    for rec, (slot, info, addend) in sorted(RELA_EXPECT.items()):
        got = rela(data, rec)
        check(got == (slot, info, addend),
              f"RELA record 0x{rec:x} expected (0x{slot:x}, 0x{info:x}, "
              f"0x{addend:x}) got (0x{got[0]:x}, 0x{got[1]:x}, 0x{got[2]:x})")
    # derived: first button vtable base = slot - 0x1f8
    check(rela(data, 0x4092750)[0] - 0x1F8 == 0x523CE08,
          "button vtable base (slot 0x523d000 - 0x1f8) must be 0x523ce08")

    # 6. strings
    for addr, want in sorted(STRING_EXPECT.items()):
        got = data[addr:addr + len(want) + 1]
        check(got == want + b"\0",
              f"string at 0x{addr:x} expected {want!r} got {got[:-1]!r}")

    # 7. 13-entry name table: tags in place, relocated name pointers, names
    for i, (tag, name_ptr, name) in enumerate(NAME_TABLE):
        base = 0x5184F40 + i * 0x10
        got_tag = data[base:base + 3]
        check(got_tag == tag, f"name table 0x{base:x} tag expected {tag!r} "
                              f"got {got_tag!r}")
    # name slots come from the rela map (records are not at a fixed step)
    rela_map = {}
    for rec in range(0x3C00000, 0x3F00000, 8):
        off, info, add = struct.unpack_from("<QQq", data, rec)
        if info == 0x403:
            rela_map[off] = add & 0xFFFFFFFFFFFFFFFF
    for i, (tag, name_ptr, name) in enumerate(NAME_TABLE):
        slot = 0x5184F40 + i * 0x10 + 8
        got_ptr = rela_map.get(slot, 0)
        check(got_ptr == name_ptr,
              f"name table slot 0x{slot:x} addend expected 0x{name_ptr:x} "
              f"got 0x{got_ptr:x}")

    # 8. the lookup sentinel's first UTF-16 unit is 0 (empty text on a miss)
    want_sentinel = 0xFFFF if neg else 0
    got_sentinel = u16(data, 0x4752EA0)
    check(got_sentinel == want_sentinel,
          f"sentinel 0x4752ea0 first UTF-16 unit expected 0x{want_sentinel:04x} "
          f"got 0x{got_sentinel:04x}")

    # 9. message files
    got_files = sorted(os.listdir(MSG_DIR))
    check(got_files == sorted(MSG_SHA256),
          f"expected exactly the 13 msbt files, got {got_files}")
    texts = {}
    for name, want_hash in MSG_SHA256.items():
        raw = open(os.path.join(MSG_DIR, name), "rb").read()
        got = hashlib.sha256(raw).hexdigest()
        check(got == want_hash, f"{name} sha256 expected {want_hash} got {got}")
    for name in MSG_SHA256:
        labels, head, bad = msbt.read_labels_counted(os.path.join(MSG_DIR, name))
        texts[name] = labels
        check(len(labels) == MSG_LABEL_COUNTS[name],
              f"{name} label count expected {MSG_LABEL_COUNTS[name]} "
              f"got {len(labels)}")
        prefix = MSG_PREFIX[name]
        offenders = [lb for lb in labels if not lb.startswith(prefix)]
        check(not offenders,
              f"{name}: {len(offenders)} labels lack the {prefix!r} prefix "
              f"(first {offenders[:3]})")

    # exact-match labels cited in the report (raw text incl. trailing NUL)
    for (name, label), want in EXACT_TEXTS.items():
        if neg and label == "mnu_record_count_title":
            want = "Jab\x00"
        got = texts.get(name, {}).get(label)
        check(got == want, f"{name}::{label} expected {want!r} got {got!r}")

    # wanted texts with / without an exact label
    def has_exact(want: str):
        for name, labels in texts.items():
            for label, txt in labels.items():
                if clean(txt).lower() == want.lower():
                    return True
        return False

    for want in WANTED_NO_EXACT:
        check(not has_exact(want),
              f"wanted text {want!r} must have no exact label (report Q4)")
    for want in WANTED_HAS_EXACT:
        check(has_exact(want),
              f"wanted text {want!r} must have >=1 exact label (report Q4)")
    # Forward Smash: not even a close hit anywhere
    fs = any("forwardsmash" in fold(clean(t))
             for labels in texts.values() for t in labels.values())
    check(not fs, "'Forward Smash' must not appear in any label text (Q4)")

    # 10. negative controls: --neg corrupts expectations; each must MISMATCH
    if neg:
        got = u32(data, 0x378A6CC)
        want = 0xDEADBEEF
        check(got == want,
              f"NEG word at 0x378a6cc expected 0x{want:08x} got 0x{got:08x}")
        got = branch_target(u32(data, 0x19CCBEC), 0x19CCBEC)
        want = 0x19CCB20
        check(got == want,
              f"NEG branch at 0x19ccbec expected target 0x{want:x} "
              f"got 0x{got:x}" if got else "NEG branch not a branch")
        got = rela(data, 0x3EA70F8)
        want = (0x51833E8, 0x403, 0x335A100)
        check(got == want,
              f"NEG RELA 0x3ea70f8 addend expected 0x335a100 got "
              f"0x{got[2]:x}")

    # ---------------------------------------------------------------- report ---
    print(f"check_p11_row_text: {checks} checks run")
    for line in failures:
        print(line)
    if failures:
        print(f"FAIL: {len(failures)} mismatches"
              + (" (negative controls detected, as expected)" if neg else ""))
        return 1
    if neg:
        print("FAIL: negative controls did NOT fire - check is broken")
        return 1
    print("PASS: all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
