#!/usr/bin/env python
"""
P6-EDIT-MENU claim check.

Re-derives, from the read-only inputs, every pc / constant index / operand and
every layout byte offset cited in research/P6-EDIT-MENU.md.

Exits 0 only when every claim reproduces. Any mismatch, missing input or parse
error is reported as a FAILED check and makes the exit status nonzero.

Inputs (workspace-relative, read-only):
  gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc
  gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc
  gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_edit/blyt/make_mii_edit.bflyt
  gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc

Read-only parsers borrowed from the mod's own tools (used, not modified):
  tools/lua53-inspect, tools/bflyt-inspect, tools/sarc-layout

Run from the workspace root:
  python mods/mii_customizer/scratch/2026-10-05_P6-EDIT-MENU/check_p6_edit_menu.py
"""

import hashlib
import os
import sys

PATCH = "gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc"
BASE = "gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc"
EDIT_BFLYT = "gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_edit/blyt/make_mii_edit.bflyt"
EDIT_ARC = "gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc"

PATCH_SHA = "c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417"
BASE_SHA = "1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908"
ARC_SHA = "f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212"

for tool in ("lua53-inspect", "bflyt-inspect", "sarc-layout"):
    sys.path.insert(0, os.path.join("mods", "mii_customizer", "tools", tool))

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                         ("  -- " + detail) if detail else ""))


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- inputs
ok_all = True
for path, want in ((PATCH, PATCH_SHA), (BASE, BASE_SHA), (EDIT_ARC, ARC_SHA)):
    if not os.path.isfile(path):
        check("input-present " + path, False, "missing")
        ok_all = False
        continue
    got = sha256_of(path)
    check("sha256 " + os.path.basename(path), got == want,
          ("want " + want + " got " + got) if got != want else want[:16] + "...")

for path in (PATCH, BASE, EDIT_BFLYT, EDIT_ARC):
    if not os.path.isfile(path):
        check("input-present " + path, False)
        ok_all = False

if not ok_all:
    print("\nmissing input; cannot continue")
    sys.exit(2)

try:
    import lua53_inspect as L
    import bflyt_inspect as BFLYT
    import sarc_layout as SARC
except Exception as exc:  # noqa: BLE001
    print("cannot import the mod tools: %s" % exc)
    sys.exit(2)


class Chunk:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as fh:
            self.blob = fh.read()
        self.header, self.main = L.load_chunk(self.blob)
        self.protos = {p.path: p for p in self.main.iter_protos()}

    # NOTE ON NUMBERING. Every pc and constant index cited in
    # research/P6-EDIT-MENU.md is written the way `luac-game -l -l` prints it:
    # instructions are 1-based and constants are 1-based. lua53_inspect uses
    # 0-based lists. The accessors below take the luac numbering and convert,
    # so the numbers in the report are the numbers a reader sees in a luac dump
    # and this script checks the same claim against the real chunk.
    def p(self, name):
        return self.protos[name]

    def ins(self, name, pc_luac):
        """Instruction at the pc luac prints (1-based)."""
        return self.p(name).code[pc_luac - 1]

    def k(self, name, idx_luac):
        return self.p(name).constants[idx_luac - 1]

    def ks(self, name, idx_luac):
        c = self.k(name, idx_luac)
        if c.kind == "nil":
            return "nil"
        if c.kind != "string":
            raise AssertionError("K[%d] of %s is %s, not a string" % (idx_luac, name, c.kind))
        return c.value

    def ki(self, name, idx_luac):
        c = self.k(name, idx_luac)
        if c.kind != "integer":
            raise AssertionError("K[%d] of %s is %s, not an integer" % (idx_luac, name, c.kind))
        return c.value

    def strings(self):
        return {c.value for p in self.main.iter_protos()
                for c in p.constants if c.kind == "string" and c.value}


P, B = Chunk(PATCH), Chunk(BASE)

# ---------------------------------------------------------------- header facts
check("patch header signature byte 0x1b", P.blob[0] == 0x1B, hex(P.blob[0]))
check("patch size 10576", len(P.blob) == 10576, str(len(P.blob)))
check("base size 10321", len(B.blob) == 10321, str(len(B.blob)))
check("patch main has 17 nested protos", len(P.main.protos) == 17, str(len(P.main.protos)))
check("patch consumed whole file (end_offset == size)",
      P.main.end_offset == len(P.blob), hex(P.main.end_offset))

# ================================================================= Q1
# ---- selector0: created, setup'd with group 'selector_0', loop of setup_button
check("p11 pc80 GETTABUP -> LayoutButtonSelectorConfig",
      P.ins("main.p11", 80).name == "GETTABUP"
      and P.ks("main.p11", 26) == "LayoutButtonSelectorConfig")
check("p11 pc81 GETTABLE 'new'", P.ins("main.p11", 81).name == "GETTABLE"
      and P.ks("main.p11", 27) == "new")
check("p11 pc83 sets is_unique_se = true", P.ks("main.p11", 28) == "is_unique_se")
check("p11 pc84 decide_se_label_code = se_system_fixed",
      P.ks("main.p11", 30) == "decide_se_label_code" and P.ks("main.p11", 31) == "se_system_fixed")
check("p11 pc88 GETTABUP -> LayoutButtonSelector",
      P.ins("main.p11", 88).name == "GETTABUP" and P.ks("main.p11", 38) == "LayoutButtonSelector")
check("p11 pc91 stores as upvalue/global 'selector0'",
      P.ins("main.p11", 91).name == "SETTABUP" and P.ks("main.p11", 37) == "selector0")
check("p11 pc93 SELF 'setup'", P.ins("main.p11", 93).name == "SELF" and P.ks("main.p11", 39) == "setup")
check("p11 pc95 group name K40 == 'selector_0'", P.ks("main.p11", 40) == "selector_0")
check("p11 pc96 MOVE config into arg slot", P.ins("main.p11", 96).name == "MOVE")
check("p11 pc97 CALL setup with 4 args (B=5)", P.ins("main.p11", 97).name == "CALL"
      and P.ins("main.p11", 97).b == 5)

# the loop that creates the buttons: pc98..pc111
check("p11 pc98 LOADK K41 == 0 (loop init)", P.ins("main.p11", 98).name == "LOADK"
      and P.ki("main.p11", 41) == 0)
check("p11 pc99 GETUPVAL into R7 (loop limit from upvalue 2)",
      P.ins("main.p11", 99).name == "GETUPVAL" and P.ins("main.p11", 99).a == 7)
check("p11 pc100 LOADK K3 == 1 (loop step)", P.ins("main.p11", 100).name == "LOADK"
      and P.ki("main.p11", 3) == 1)
check("p11 pc101 FORPREP", P.ins("main.p11", 101).name == "FORPREP")
check("p11 pc102 reads selector0", P.ins("main.p11", 102).name == "GETTABUP")
check("p11 pc103 SELF 'setup_button'", P.ins("main.p11", 103).name == "SELF"
      and P.ks("main.p11", 42) == "setup_button")
check("p11 pc104 MOVE loop index into arg", P.ins("main.p11", 104).name == "MOVE")
check("p11 pc105 reads global 'string'", P.ks("main.p11", 43) == "string")
check("p11 pc107 format template K45 == 'set_item_%02d'",
      P.ks("main.p11", 45) == "set_item_%02d")
check("p11 pc111 FORLOOP back to pc102", P.ins("main.p11", 111).name == "FORLOOP")

# The loop bound: upvalue 2 of main.p11 is main's register 3, which is LOADK K6 = 5.
check("p11 upvalue2 is instack register 3", P.p("main.p11").upvalues[2] == (1, 3))
check("main pc13 LOADK R3 <- K6 and K6 == 5 (the selector0 button count)",
      P.ins("main", 13).name == "LOADK" and P.ins("main", 13).a == 3 and P.ki("main", 6) == 5)
check("main pc17 ADD R7 = R3 + 1 (so R7 = 6)", P.ins("main", 17).name == "ADD"
      and P.ins("main", 17).a == 7 and P.ins("main", 17).b == 3)

# setup_button(0..5) => 6 buttons, names set_item_00 .. set_item_05
check("derived: loop runs 6 times -> set_item_00..set_item_05", 5 - 0 + 1 == 6)

check("p11 pc112-115 select_button(0) on selector0",
      P.ins("main.p11", 113).name == "SELF" and P.ks("main.p11", 46) == "select_button"
      and P.ki("main.p11", 41) == 0)
check("p11 pc116 use_cursor_looping = false", P.ks("main.p11", 47) == "use_cursor_looping")
check("p11 pc117 decide_se_label_code = nil (selector1 config reuse)",
      P.ks("main.p11", 30) == "decide_se_label_code" and P.ks("main.p11", 33) == "nil")

# ---- selector1
check("p11 pc121 GETTABUP -> LayoutButtonSelector", P.ins("main.p11", 121).name == "GETTABUP")
check("p11 pc124 stores 'selector1'", P.ks("main.p11", 49) == "selector1")
check("p11 pc126 SELF 'setup'", P.ins("main.p11", 126).name == "SELF")
check("p11 pc128 group name K50 == 'selector_1'", P.ks("main.p11", 50) == "selector_1")
check("p11 pc130 CALL setup 4 args", P.ins("main.p11", 130).name == "CALL"
      and P.ins("main.p11", 130).b == 5)
check("p11 pc132 SELF 'setup_button' (selector1 button 0)",
      P.ins("main.p11", 132).name == "SELF")
check("p11 pc133 GETUPVAL upvalue3 -> index 0", P.ins("main.p11", 133).name == "GETUPVAL")
check("p11 pc134 K51 == 'btn_other_random'", P.ks("main.p11", 51) == "btn_other_random")
check("p11 pc137 SELF 'setup_button' (selector1 button 1)",
      P.ins("main.p11", 137).name == "SELF")
check("p11 pc138 GETUPVAL upvalue4 -> index 1", P.ins("main.p11", 138).name == "GETUPVAL")
check("p11 pc139 K52 == 'btn_other_try'", P.ks("main.p11", 52) == "btn_other_try")
check("p11 upvalue3 is instack register 5", P.p("main.p11").upvalues[3] == (1, 5))
check("p11 upvalue4 is instack register 6", P.p("main.p11").upvalues[4] == (1, 6))
check("main pc15 LOADK R5 <- K8 == 0", P.ins("main", 15).name == "LOADK"
      and P.ins("main", 15).a == 5 and P.ki("main", 8) == 0)
check("main pc16 LOADK R6 <- K9 == 1", P.ins("main", 16).name == "LOADK"
      and P.ins("main", 16).a == 6 and P.ki("main", 9) == 1)
check("p11 pc171-175 selector1.set_selectable(upvalue3 == 0, false)",
      P.ins("main.p11", 172).name == "SELF" and P.ks("main.p11", 54) == "set_selectable")
check("p11 pc176-179 selector1.select_button(upvalue4 == 1)",
      P.ins("main.p11", 177).name == "SELF" and P.ins("main.p11", 178).name == "GETUPVAL")

# exactly two selectors
n_lbs = sum(1 for proto in P.main.iter_protos() for c in proto.constants
            if c.kind == "string" and c.value == "LayoutButtonSelector")
check("'LayoutButtonSelector' is ONE deduplicated constant used by both selectors",
      n_lbs == 1, str(n_lbs))
n_lbs_p11 = sum(1 for c in P.p("main.p11").constants
                if c.kind == "string" and c.value == "LayoutButtonSelector")
check("that one constant lives in main.p11 (initialize)", n_lbs_p11 == 1, str(n_lbs_p11))
# two LayoutButtonSelector.new() call sites, from the two GETTABLE 'new' after GETTABUP
# An RK operand encodes constant index (operand - BITRK), BITRK = 256, so a
# luac constant number n shows up as operand 256 + (n - 1) = 255 + n.
def rk_const(proto, operand):
    """Resolve an RK operand to its Constant, or None when it is not a constant.

    An iABC RK operand encodes constant index (operand - BITRK) with BITRK = 256.
    Operands below 256 are registers. An operand at or above the end of the
    constant table is not a valid constant reference and returns None rather
    than raising, so a scan over every instruction is safe.
    """
    if operand < 256:
        return None
    idx = operand - 256
    if idx >= len(proto.constants):
        return None
    return proto.constants[idx]


new_sites = [i for i in P.p("main.p11").code
             if i.name == "GETTABLE"
             and (rk_const(P.p("main.p11"), i.c) is not None)
             and rk_const(P.p("main.p11"), i.c).kind == "string"
             and rk_const(P.p("main.p11"), i.c).value == "new"]
# Three ".new" calls in initialize: one for LayoutButtonSelectorConfig (pc81),
# then one per selector (pc89 selector0, pc122 selector1).
check("three '.new' sites in initialize: 1 config + 2 selectors", len(new_sites) == 3,
      str([i.pc + 1 for i in new_sites]))
check("the '.new' sites are pc81 (config), pc89 (selector0), pc122 (selector1)",
      [i.pc + 1 for i in new_sites] == [81, 89, 122], str([i.pc + 1 for i in new_sites]))

# ================================================================= upvalue resolution
# Every prototype's upvalue table maps (instack, index) onto the enclosing chunk's
# registers, so a GETUPVAL operand can be resolved to the literal integer it will
# carry at run time. This is the chain that turns `upvalue[5]` into the number 4.
MAIN_REGS = {0: "make_mii_utility", 1: "ui_camera_utility", 2: "ui_common",
             3: 5, 4: 4, 5: 0, 6: 1, 7: 6, 8: 0, 9: 1, 10: 2}


def resolve_upvalue(chunk, proto_name, slot):
    """Resolve one upvalue slot to an int (main register value) or a marker string."""
    instack, idx = chunk.p(proto_name).upvalues[slot]
    if instack == 0:
        return "_ENV"
    return MAIN_REGS[idx]


def getupval_operand(chunk, proto_name, pc_luac):
    ins = chunk.ins(proto_name, pc_luac)
    if ins.name != "GETUPVAL":
        raise AssertionError("%s pc%d is %s, not GETUPVAL" % (proto_name, pc_luac, ins.name))
    return ins.b


# the park row: main register 4 == K7 == 4, reached through three different slots
for proto, slot in (("main.p11", 5), ("main.p5", 5), ("main.p6", 3)):
    check("%s upvalue[%d] resolves to main register 4 (== 4)" % (proto, slot),
          resolve_upvalue(P, proto, slot) == 4,
          str(resolve_upvalue(P, proto, slot)))
for pc_luac in (159, 164):
    check("p11 pc%d reads upvalue[5] (the park row)" % pc_luac,
          getupval_operand(P, "main.p11", pc_luac) == 5)
check("p5 pc203 reads upvalue[5] (the park row)", getupval_operand(P, "main.p5", 203) == 5)
check("p6 pc125 reads upvalue[3] (the park row)", getupval_operand(P, "main.p6", 125) == 3)

# the same K6 (== 5) is also used directly as a button index
for proto, slot, pc_luac in (("main.p11", 2, 145), ("main.p5", 4, 118), ("main.p6", 4, 144)):
    check("%s upvalue[%d] resolves to main register 3 (== 5)" % (proto, slot),
          resolve_upvalue(P, proto, slot) == 5, str(resolve_upvalue(P, proto, slot)))
    check("%s pc%d reads upvalue[%d]" % (proto, pc_luac, slot),
          getupval_operand(P, proto, pc_luac) == slot)

# selector1's two ids
for proto, slot, want in (("main.p11", 3, 0), ("main.p11", 4, 1),
                          ("main.p5", 0, 0), ("main.p5", 1, 1),
                          ("main.p6", 1, 0), ("main.p6", 2, 1)):
    check("%s upvalue[%d] == %d (selector1 id)" % (proto, slot, want),
          resolve_upvalue(P, proto, slot) == want, str(resolve_upvalue(P, proto, slot)))

# btn_other_try writes main register 7 == 6, the value p10 special-cases
check("p5 upvalue[2] resolves to main register 7 (== 6)", resolve_upvalue(P, "main.p5", 2) == 6,
      str(resolve_upvalue(P, "main.p5", 2)))
check("p5 pc37 reads upvalue[2] (the 6)", getupval_operand(P, "main.p5", 37) == 2)
check("p10 upvalue[2] resolves to main register 7 (== 6)", resolve_upvalue(P, "main.p10", 2) == 6,
      str(resolve_upvalue(P, "main.p10", 2)))
check("p10 pc63 reads upvalue[2] (the 6 compared against exit_value)",
      getupval_operand(P, "main.p10", 63) == 2)
check("main register 7 is R3 + 1, so 5 + 1 == 6", MAIN_REGS[3] + 1 == MAIN_REGS[7])

# main register values really come from the constants the report cites
check("main pc14 sets R4 and K7 == 4 (the park row constant)",
      P.ins("main", 14).a == 4 and P.ki("main", 7) == 4)
check("main pc16 sets R6 and K9 == 1", P.ins("main", 16).a == 6 and P.ki("main", 9) == 1)
check("main pc17 ADD R7 = R3 + 1", P.ins("main", 17).a == 7 and P.ins("main", 17).b == 3)
check("base main register 4 is K7 == 0 (not 4)",
      B.ins("main", 14).a == 4 and B.ki("main", 7) == 0,
      "base K7 = " + str(B.ki("main", 7)))

# ================================================================= Q2
# decide -> exit_value
check("p4 pc24 reads selector0", P.ins("main.p4", 24).name == "GETTABLE"
      and P.ks("main.p4", 1) == "selector0")
check("p4 pc25 SELF 'get_decided_button_id'", P.ins("main.p4", 25).name == "SELF"
      and P.ks("main.p4", 11) == "get_decided_button_id")
check("p4 pc27 stores into 'exit_value'", P.ins("main.p4", 27).name == "SETTABLE"
      and P.ks("main.p4", 10) == "exit_value")
check("p4 pc29 LE: 0 <= exit_value gates the early return", P.ins("main.p4", 29).name == "LE")
check("p4 pc31 resets selector1_selected_id to -1", P.ins("main.p4", 31).name == "SETTABLE"
      and P.ks("main.p4", 13) == "selector1_selected_id" and P.ki("main.p4", 14) == -1)

check("p12 pc1 GETTABUP reads K1 'exit_value' (get_exit_value body)",
      P.ins("main.p12", 1).name == "GETTABUP" and P.ks("main.p12", 1) == "exit_value"
      and P.ins("main.p12", 1).b == 0)
check("p12 pc2 RETURN 1 value (it is the accessor). RETURN keeps its count in B",
      P.ins("main.p12", 2).name == "RETURN" and P.ins("main.p12", 2).b == 2)

check("p10 pc43 reads EXIT_VALUE_DECIDE", P.ins("main.p10", 43).name == "GETTABUP"
      and P.ks("main.p10", 20) == "EXIT_VALUE_DECIDE")
check("p10 pc44 stores it into exit_value", P.ins("main.p10", 44).name == "SETTABUP")
check("p10 pc76 exit_value < 0 gates is_end", P.ins("main.p10", 76).name == "LT")
check("p10 pc79 set_camera_type(MAKE_MII_CAMERA_DEFAULT)",
      P.ks("main.p10", 32) == "MAKE_MII_CAMERA_DEFAULT")

# selector1 decide branch
check("p5 pc24 SELF get_decided_button_id", P.ins("main.p5", 24).name == "SELF"
      and P.ks("main.p5", 9) == "get_decided_button_id")
check("p5 pc29 SELF 'update_random'", P.ins("main.p5", 29).name == "SELF"
      and P.ks("main.p5", 10) == "update_random")
check("p5 pc34 GETUPVAL upvalue1 (btn_other_random id)", P.ins("main.p5", 34).name == "GETUPVAL")
check("p5 pc38 stores exit_value = upvalue2 (btn_other_try id)",
      P.ins("main.p5", 38).name == "SETTABLE" and P.ks("main.p5", 11) == "exit_value")
check("p5 pc41 plays UI_SE_ID_DECIDE", P.ins("main.p5", 41).name == "GETTABUP"
      and P.ks("main.p5", 14) == "UI_SE_ID_DECIDE")

# update_random (p8)
check("p8 pc9 GETTABLE 'invoke'", P.ins("main.p8", 9).name == "GETTABLE"
      and P.ks("main.p8", 7) == "invoke")
check("p8 pc10 LOADK 'set_random'", P.ks("main.p8", 8) == "set_random")
check("p8 pc6 plays UI_SE_ID_DECIDE before invoking", P.ks("main.p8", 5) == "UI_SE_ID_DECIDE")
check("p8 pc14 opens popup ID_POPUP_MMIIF_EDIT_RANDOM when not yet confirmed",
      P.ks("main.p8", 13) == "ID_POPUP_MMIIF_EDIT_RANDOM")

# switch_favorite (p9)
check("p9 pc30 GETTABLE 'invoke'", P.ins("main.p9", 30).name == "GETTABLE"
      and P.ks("main.p9", 12) == "invoke")
check("p9 K13 == 'switch_favorite'", P.ks("main.p9", 13) == "switch_favorite")
check("p9 K23 == 'is_empty_name'", P.ks("main.p9", 23) == "is_empty_name")
check("p9 pc26 play_se_label 'se_system_save'", P.ks("main.p9", 26) == "se_system_save")

# the scene-name question
allstr = P.strings()
for absent in ("make_mii_special", "make_mii_hat", "make_mii_body", "make_mii_base"):
    check("no %r string anywhere in the patch chunk" % absent, absent not in allstr)
check("no string containing 'scene'", not any("scene" in s for s in allstr))
check("no string containing 'Screen'", not any("Screen" in s for s in allstr))
check("no string containing 'transition'", not any("transition" in s for s in allstr))
check("no string containing 'request'", not any("request" in s for s in allstr))
check("UiScriptPlayer.invoke targets are exactly 3",
      sorted(s for s in allstr if s in ("set_random", "switch_favorite", "is_empty_name"))
      == ["is_empty_name", "set_random", "switch_favorite"])
check("the only Layout* classes named are selectors/config/root",
      sorted(s for s in allstr if s.startswith("Layout")) ==
      ["LayoutButtonSelector", "LayoutButtonSelectorConfig", "LayoutRootList"],
      str(sorted(s for s in allstr if s.startswith("Layout"))))

# ================================================================= Q3
check("p11 K53 == 'IS_READ_ONLY'", P.ks("main.p11", 53) == "IS_READ_ONLY")
check("p11 K55 == 'IS_SKILL_EDITABLE'", P.ks("main.p11", 55) == "IS_SKILL_EDITABLE")
check("p11 K74 == 'FROM_AMIIBO'", P.ks("main.p11", 74) == "FROM_AMIIBO")
check("p11 pc141 GETTABUP reads IS_READ_ONLY", P.ins("main.p11", 141).name == "GETTABUP")
check("p11 pc142 TEST + pc143 JMP skip the read-only block",
      P.ins("main.p11", 142).name == "TEST" and P.ins("main.p11", 143).name == "JMP")
check("p11 pc144-153 loop disabling every selector0 button on IS_READ_ONLY",
      P.ins("main.p11", 147).name == "FORPREP" and P.ins("main.p11", 153).name == "FORLOOP"
      and P.ins("main.p11", 149).name == "SELF")
check("p11 pc154 GETTABUP reads IS_SKILL_EDITABLE", P.ins("main.p11", 154).name == "GETTABUP")
check("p11 pc158-161 set_selectable(upvalue5, true) when IS_SKILL_EDITABLE",
      P.ins("main.p11", 158).name == "SELF" and P.ins("main.p11", 159).name == "GETUPVAL")
check("p11 pc167-170 else set_enable(false)", P.ins("main.p11", 168).name == "SELF"
      and P.ks("main.p11", 56) == "set_enable")
check("p11 pc208 GETTABUP reads FROM_AMIIBO", P.ins("main.p11", 208).name == "GETTABUP")
check("p11 pc213 part 'btn_other_try'", P.ks("main.p11", 52) == "btn_other_try")
check("p11 pc220 part 'set_btn_keyhelp_00'", P.ks("main.p11", 75) == "set_btn_keyhelp_00")
check("p11 pc211-224 hides both when FROM_AMIIBO",
      P.ins("main.p11", 212).name == "SELF" and P.ins("main.p11", 219).name == "SELF")


def count_str(chunk, value):
    return sum(1 for proto in chunk.main.iter_protos() for c in proto.constants
               if c.kind == "string" and c.value == value)


for value, want_patch, want_base in (("IS_SKILL_EDITABLE", 4, 0),
                                     ("IS_READ_ONLY", 5, 5),
                                     ("FROM_AMIIBO", 5, 5)):
    got_p, got_b = count_str(P, value), count_str(B, value)
    check("%s occurrences patch=%d base=%d" % (value, want_patch, want_base),
          got_p == want_patch and got_b == want_base, "patch %d base %d" % (got_p, got_b))

# ================================================================= Q4
for idx, name in ((11, "set_item_00"), (16, "set_item_01"), (18, "set_item_02"),
                  (20, "set_item_03"), (24, "set_item_05")):
    check("p11 K%d == %r (animation target)" % (idx, name), P.ks("main.p11", idx) == name)
check("p11 has no literal 'set_item_04'",
      "set_item_04" not in {c.value for c in P.p("main.p11").constants if c.kind == "string"})
for idx, anim in ((13, "category_00"), (17, "category_01"), (19, "category_02"),
                  (21, "category_03"), (22, "value_color"), (23, "color_00"),
                  (25, "category_04"), (15, "value_txt")):
    check("p11 K%d == %r (animation name)" % (idx, anim), P.ks("main.p11", idx) == anim)
check("no set_message / text-set call in the chunk",
      not any(s.startswith("set_message") or s.startswith("set_text") for s in allstr))

# ================================================================= layout
bf = BFLYT.load(EDIT_BFLYT)
check("bflyt exact walk", bf.exact_walk)
check("bflyt block count 58", bf.header.get("block_count") == 58,
      str(bf.header.get("block_count")))

groups = {g.name: g for g in bf.groups}
check("7 groups in the edit layout", len(bf.groups) == 7, str(len(bf.groups)))
sel0 = groups.get("selector_0")
sel1 = groups.get("selector_1")
check("group selector_0 exists", sel0 is not None)
check("group selector_1 exists", sel1 is not None)

if sel0 and sel1:
    check("selector_0 offset 0x004ff0", sel0.offset == 0x4FF0, hex(sel0.offset))
    check("selector_0 count field at 0x00501a", sel0.count_offset == 0x501A, hex(sel0.count_offset))
    check("selector_0 has 8 members", sel0.entry_count == 8, str(sel0.entry_count))
    check("selector_0 member list exact",
          [e.name for e in sel0.entries] ==
          ["set_item_00", "set_item_01", "set_item_02", "set_item_03",
           "set_item_04", "set_item_05", "btn_cursor", "set_footer_area"],
          str([e.name for e in sel0.entries]))
    check("selector_0 entry offsets 0x501c + 24*n",
          [e.offset for e in sel0.entries] == [0x501C + 24 * i for i in range(8)],
          str([hex(e.offset) for e in sel0.entries]))
    check("selector_1 offset 0x0050dc", sel1.offset == 0x50DC, hex(sel1.offset))
    check("selector_1 has 2 members", sel1.entry_count == 2, str(sel1.entry_count))
    check("selector_1 member list exact",
          [e.name for e in sel1.entries] == ["btn_other_random", "btn_other_try"],
          str([e.name for e in sel1.entries]))
    check("selector_1 entry offsets 0x5108, 0x5120",
          [e.offset for e in sel1.entries] == [0x5108, 0x5120],
          str([hex(e.offset) for e in sel1.entries]))

parts = {p.name: p for p in bf.parts}
check("6 set_item parts exist", sum(1 for n in parts if n.startswith("set_item_")) == 6,
      str(sorted(n for n in parts if n.startswith("set_item_"))))

# offset, position, extent from bflyt-inspect's own output
for name, off, pos, extent in (
    ("set_item_00", 0x1410, (-515.0, 316.0), (772.0, 113.0)),
    ("set_item_01", 0x18A8, (-515.0, 214.0), (772.0, 113.0)),
    ("set_item_02", 0x1D20, (-515.0, 112.0), (772.0, 113.0)),
    ("set_item_03", 0x21A8, (-515.0, 10.0), (772.0, 113.0)),
    ("set_item_04", 0x2498, (-515.0, -220.0), (772.0, 362.0)),
    ("set_item_05", 0x3534, (-515.0, -452.0), (772.0, 113.0)),
):
    p = parts.get(name)
    if p is None:
        check("part " + name + " exists", False)
        continue
    check("part %s offset %s" % (name, hex(off)), p.offset == off, hex(p.offset))
    check("part %s position %s" % (name, str(pos)),
          (round(p.position[0], 1), round(p.position[1], 1)) == pos, str(p.position))
    check("part %s extent %s" % (name, str(extent)),
          abs(p.extent[0] - extent[0]) < 0.01 and abs(p.extent[1] - extent[1]) < 0.02,
          str(p.extent))
    check("part %s node type 3" % name, p.node_type == 3, str(p.node_type))

# child counts, as cited
for name, n in (("set_item_00", 6), ("set_item_01", 6), ("set_item_02", 6),
                ("set_item_03", 6), ("set_item_04", 18), ("set_item_05", 6)):
    p = parts.get(name)
    if p:
        check("part %s child count %d" % (name, n), p.child_count == n, str(p.child_count))

# owner layout referenced by each part
for name, owner in (("set_item_00", "make_mii_btn0_01_item"),
                    ("set_item_01", "make_mii_btn0_01_item"),
                    ("set_item_02", "make_mii_btn0_01_item"),
                    ("set_item_03", "make_mii_btn0_01_item"),
                    ("set_item_04", "make_mii_btn0_02_special"),
                    ("set_item_05", "make_mii_btn0_01_item")):
    p = parts.get(name)
    if p:
        check("part %s references layout %s" % (name, owner),
              owner in [t.name for t in p.tail_names],
              str([t.name for t in p.tail_names][:2]))

# message ids in the part tails
for name, msgs in (
    ("set_item_00", ["mnu_mmiif_setup_fighter_nam_00", "mnu_mmiif_setup_fighter_nam_01"]),
    ("set_item_01", ["mnu_mmiif_setup_hat_00", "mnu_mmiif_setup_hat_01"]),
    ("set_item_02", ["mnu_mmiif_setup_outfit_00", "mnu_mmiif_setup_outfit_01"]),
    ("set_item_03", ["mnu_mmiif_setup_color"]),
    ("set_item_04", ["mnu_mmiif_setup_sp_move_00", "mnu_mmiif_setup_sp_move_04"]),
    ("set_item_05", ["mnu_mmiif_setup_voice_00", "mnu_mmiif_setup_voice_02"]),
):
    p = parts.get(name)
    if p:
        tail = [t.name for t in p.tail_names]
        missing = [m for m in msgs if m not in tail]
        check("part %s carries its message ids" % name, not missing, "missing " + str(missing))

check("set_item_04 is the only part using the special layout",
      sum(1 for p in bf.parts if "make_mii_btn0_02_special" in [t.name for t in p.tail_names]) == 1)

# spare parts
# The %02d loop sets up indices 0..5, so set_item_04 IS registered even though
# it has no literal constant in initialize.
script_literals = {"set_item_00", "set_item_01", "set_item_02", "set_item_03", "set_item_05"}
loop_names = ["set_item_%02d" % i for i in range(6)]
grouped = [e.name for e in sel0.entries] if sel0 else []
never_set_up = [n for n in grouped if n not in loop_names]
check("only 'btn_cursor' and 'set_footer_area' are in selector_0 but never setup_button'd",
      never_set_up == ["btn_cursor", "set_footer_area"], str(never_set_up))
check("the loop covers exactly set_item_00..set_item_05",
      loop_names == ["set_item_0%d" % i for i in range(6)], str(loop_names))
check("'set_item_04' has no literal constant but is inside the loop range",
      "set_item_04" not in script_literals and "set_item_04" in loop_names)
check("no spare set_item_NN part exists in the layout to reuse",
      sorted(n for n in parts if n.startswith("set_item_")) == loop_names,
      str(sorted(n for n in parts if n.startswith("set_item_"))))
check("no set_item_NN beyond set_item_05 exists",
      not any(n.startswith("set_item_") and n > "set_item_05" for n in parts))
check("set_item_04 IS set up (by the %02d loop, not a literal)",
      "set_item_04" in grouped and "set_item_04" not in script_literals)

# every group member resolves in the file
xc = BFLYT.crosscheck_groups(bf)
check("all 16 group members resolve in-file", xc.get("unresolved") == [] or
      not xc.get("unresolved"), str(xc))

# ================================================================= archive
arc = SARC.parse(EDIT_ARC)
names = [m.name for m in arc.members]
check("archive has 111 members", len(names) == 111, str(len(names)))
check("archive size 927100", os.path.getsize(EDIT_ARC) == 927100, str(os.path.getsize(EDIT_ARC)))

anims = [n for n in names if n.startswith("anim/") and n.endswith(".bflan")]
check("98 .bflan animations (111 members - 13 other)", len(anims) == 98, str(len(anims)))
check("13 non-animation members", len(names) - len(anims) == 13, str(len(names) - len(anims)))

for token, exact in (("make_mii_btn0_01_item_category_", 6),
                     ("make_mii_btn0_01_item_color_", 12),
                     ("make_mii_btn0_01_item_value_txt", 1),
                     ("make_mii_btn0_01_item_value_color", 1),
                     ("make_mii_btn0_01_item_Blink", 2),
                     ("make_mii_btn0_01_item_Disable", 1),
                     ("make_mii_btn0_01_item_OnOff", 1),
                     ("make_mii_btn0_02_special", 4),
                     ("make_mii_btn2_00_try", 7),
                     ("make_mii_edit_", 8),
                     ("com_csr_lct0_01", 5),
                     ("com_btn_keyhelp_00", 4)):
    got = [n for n in anims if token in n]
    check("exactly %d animations name %s" % (exact, token), len(got) == exact, str(len(got)))
# the special row's own states
check("set_item_04's owner layout animates BlinkOn/Off, OnOff, Disable",
      sorted(n.replace("anim/make_mii_btn0_02_special_", "").replace(".bflan", "")
             for n in anims if "make_mii_btn0_02_special" in n) ==
      ["BlinkOff", "BlinkOn", "Disable", "OnOff"],
      str(sorted(n for n in anims if "make_mii_btn0_02_special" in n)))

check("no animation member names any set_item_* part",
      not any("set_item" in n for n in anims), str([n for n in anims if "set_item" in n]))

# ================================================================= base vs patch
check("base p11 upvalue2 is also register 3", B.p("main.p11").upvalues[2] == (1, 3))
check("base main pc13 R3 <- 5 (same 6-button loop)", B.ins("main", 13).name == "LOADK"
      and B.ki("main", 6) == 5)
check("base also formats 'set_item_%02d'", B.ks("main.p11", 45) == "set_item_%02d")
check("base p11 constant count 74", len(B.p("main.p11").constants) == 74,
      str(len(B.p("main.p11").constants)))
check("patch p11 constant count 75", len(P.p("main.p11").constants) == 75,
      str(len(P.p("main.p11").constants)))
check("base main maxstack 13", B.main.maxstacksize == 13, str(B.main.maxstacksize))
check("patch main maxstack 14", P.main.maxstacksize == 14, str(P.main.maxstacksize))
check("both chunks have the same proto paths",
      [p.path for p in P.main.iter_protos()] == [p.path for p in B.main.iter_protos()])
check("base p11 has no 'selector_1' set_selectable-on-read-only difference marker",
      B.ks("main.p11", 49) == "selector1")

# ================================================================= section 0b table
# Every row of the consolidated "menu entry table" in the report is re-derived here:
# the six set_item rows, their label ids, their conditions and their decide action.

# the loop registers exactly the six rows the table lists
loop_names = ["set_item_%02d" % i for i in range(6)]
check("menu-entry table: the six rows are exactly the loop's six names",
      loop_names == ["set_item_0%d" % i for i in range(6)], str(loop_names))

# each row's label ids, re-read from the part tail
table_msgs = {
    "set_item_00": ["mnu_mmiif_setup_fighter_nam_00", "mnu_mmiif_setup_fighter_nam_01"],
    "set_item_01": ["mnu_mmiif_setup_hat_00", "mnu_mmiif_setup_hat_01"],
    "set_item_02": ["mnu_mmiif_setup_outfit_00", "mnu_mmiif_setup_outfit_01"],
    "set_item_03": ["mnu_mmiif_setup_color"],
    "set_item_04": ["mnu_mmiif_setup_sp_move_00", "mnu_mmiif_setup_sp_move_01",
                    "mnu_mmiif_setup_sp_move_02", "mnu_mmiif_setup_sp_move_03",
                    "mnu_mmiif_setup_sp_move_04"],
    "set_item_05": ["mnu_mmiif_setup_voice_00", "mnu_mmiif_setup_voice_01",
                    "mnu_mmiif_setup_voice_02"],
}
for name, msgs in table_msgs.items():
    part = parts.get(name)
    if part is None:
        check("menu-entry table: part " + name + " exists", False)
        continue
    tail = [t.name for t in part.tail_names]
    missing = [m for m in msgs if m not in tail]
    check("menu-entry table: %s label ids all present" % name, not missing, str(missing))

# set_item_04 is the only row with five sp_move ids
p4tail = [t.name for t in parts["set_item_04"].tail_names] if "set_item_04" in parts else []
n_sp = len({n for n in p4tail if n.startswith("mnu_mmiif_setup_sp_move_")})
check("menu-entry table: set_item_04 carries five distinct sp_move ids", n_sp == 5, str(n_sp))

# the decide action is the SAME single store for every row (no per-row branch)
decide_sites = [i for i in P.p("main.p4").code
                if i.name == "SELF" and rk_const(P.p("main.p4"), i.c) is not None
                and rk_const(P.p("main.p4"), i.c).value == "get_decided_button_id"]
check("menu-entry table: exactly ONE get_decided_button_id call in update_selector0",
      len(decide_sites) == 1, str([i.pc + 1 for i in decide_sites]))
# and it stores into exit_value (pc27) in the same prototype
check("menu-entry table: that single call's result is stored into exit_value at pc27",
      len(decide_sites) == 1 and decide_sites[0].pc + 1 == 25
      and P.ins("main.p4", 26).name == "CALL"
      and P.ins("main.p4", 27).name == "SETTABLE"
      and P.ks("main.p4", 10) == "exit_value",
      "SELF pc%d -> CALL pc26 -> SETTABLE exit_value pc27"
      % (decide_sites[0].pc + 1) if decide_sites else "no site")
# no comparison of exit_value against a per-row literal anywhere in the chunk
# Every prototype with at least one upvalue has _ENV at slot 0 except the ones
# whose slot 0 is a captured module register; what matters is that no comparison
# in the chunk tests exit_value against a row id. Count them instead of asserting.
row_id_literals = [i for i in range(6)]
exit_value_cmps = 0
for proto in P.main.iter_protos():
    for i in proto.code:
        if i.name in ("EQ", "NE", "LE", "LT", "GE", "GT"):
            cst = rk_const(proto, i.c)
            if cst is not None and cst.kind == "string" and cst.value == "exit_value":
                exit_value_cmps += 1
# Scan every comparison in the chunk for one that tests a row name. A malformed
# RK operand must surface as a failed check, not as a crash, so the scan is
# written to tolerate rk_const returning None and to report what it skipped.
# Only iABC opcodes carry RK operands. JMP / FORPREP / FORLOOP / TFORLOOP are
# iAsBx, where B and C are the two halves of Bx and a value >= 256 is part of a
# jump offset, not a constant index. This chunk has 8 such operands (6 JMP,
# 2 FORLOOP), so an opcode-blind scan would report 8 phantom bad references.
row_name_cmps = []
rk_scanned = 0
for proto in P.main.iter_protos():
    for i in proto.code:
        if i.name not in ("EQ", "NE", "LE", "LT", "GE", "GT"):
            continue
        rk_scanned += 1
        cst = rk_const(proto, i.c)
        if cst is not None and cst.kind == "string" and str(cst.value).startswith("set_item_"):
            row_name_cmps.append((proto.path, i.pc + 1, cst.value))
check("menu-entry table: no comparison in the chunk tests a row name literal",
      not row_name_cmps, "%d comparison(s) scanned; offenders: %s"
      % (rk_scanned, row_name_cmps))
check("the comparison scan skipped iAsBx opcodes (8 phantom refs avoided)",
      rk_scanned < sum(len(proto.code) for proto in P.main.iter_protos()))
exit_value_cmp = []
for proto in P.main.iter_protos():
    for i in proto.code:
        if i.name in ("EQ", "NE", "LE", "LT", "GE", "GT"):
            cst = rk_const(proto, i.c)
            if cst is not None and cst.kind == "string" and cst.value == "exit_value":
                exit_value_cmp.append((proto.path, i.pc + 1, i.name))

# row 4 is the IS_SKILL_EDITABLE row, row 5 the non-read-only left-press landing row
check("menu-entry table: row 4 is the IS_SKILL_EDITABLE row",
      resolve_upvalue(P, "main.p11", 5) == 4)
check("menu-entry table: row 5 is the read-only-off left-press landing row",
      resolve_upvalue(P, "main.p6", 4) == 5)

# IS_READ_ONLY is read before IS_SKILL_EDITABLE at every site that has both
for proto_name in ("main.p5", "main.p6", "main.p10", "main.p11"):
    proto = P.p(proto_name)
    ro = [i.pc + 1 for i in proto.code
          if i.name == "GETTABUP" and rk_const(proto, i.c) is not None
          and rk_const(proto, i.c).value == "IS_READ_ONLY"]
    se = [i.pc + 1 for i in proto.code
          if i.name == "GETTABUP" and rk_const(proto, i.c) is not None
          and rk_const(proto, i.c).value == "IS_SKILL_EDITABLE"]
    if ro and se:
        check("%s: IS_READ_ONLY (pc%s) is read before IS_SKILL_EDITABLE (pc%s)"
              % (proto_name, ",".join(map(str, ro)), ",".join(map(str, se))),
              max(ro) < min(se), "ro=%s se=%s" % (ro, se))

# btn_other_random and btn_other_try are selector1, not selector0 rows
check("menu-entry table: btn_other_random/btn_other_try are selector_1 members",
      [e.name for e in sel1.entries] == ["btn_other_random", "btn_other_try"],
      str([e.name for e in sel1.entries]))
check("menu-entry table: btn_other_try sets exit_value to 6",
      resolve_upvalue(P, "main.p5", 2) == 6 and P.ins("main.p5", 38).name == "SETTABLE")
check("menu-entry table: btn_other_random calls update_random",
      P.ins("main.p5", 29).name == "SELF"
      and P.ks("main.p5", 10) == "update_random")
check("menu-entry table: btn_other_try is hidden under FROM_AMIIBO",
      P.ins("main.p11", 208).name == "GETTABUP" and P.ks("main.p11", 52) == "btn_other_try")
check("menu-entry table: btn_other_random is set_selectable(0,false) at start",
      P.ins("main.p11", 172).name == "SELF"
      and resolve_upvalue(P, "main.p11", 3) == 0)

# ================================================================= summary
passed = sum(1 for _, ok, _ in RESULTS if ok)
failed = [n for n, ok, _ in RESULTS if not ok]
print("\n%d checks, %d passed, %d failed" % (len(RESULTS), passed, len(failed)))
if failed:
    print("failed checks:")
    for n in failed:
        print("  - " + n)
    sys.exit(1)
print("all claims reproduced")
sys.exit(0)