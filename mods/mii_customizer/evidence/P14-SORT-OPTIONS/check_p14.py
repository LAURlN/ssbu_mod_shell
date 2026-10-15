"""P14-SORT-OPTIONS check: everything plugin 0.7.0's editor UI takes from the 13.0.4 image,
re-read from workspace gamedata/ssbu-13.0.4/main.bin (flat image, address == file offset),
and the built NRO.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python \
      mods/mii_customizer/evidence/P14-SORT-OPTIONS/check_p14.py [--neg MODE | --selftest]

The input paths come from this file's location; the PYTHONPATH above is relative to the
workspace root, so start it there (or give an absolute one). capstone is needed.
Exit 0 = every check passed, 1 = at least one mismatch, 2 = an input is missing or the image
is not the audited one.

Sections
  A  image identity
  B  every `Site { offset, words }` record of plugin/src/ui.rs (6 hook sites, 48 probes)
     and the stat hook site of logic.rs: words equal the image
  C  what those instructions are (disassembly text, written out here independently),
     including sort handler 0x19cd100 and Minus Lua constant registration 0x1808fe0..0x1809018
  D  call targets: every game function the plugin calls or hooks is a function entry and is
     called from the cited site (including FN_REG_CONST from scene builder)
  E  offsets and statics: every numeric constant of ui.rs tied to an instruction that uses it
  F  facts derived from whole ranges (restart byte, decided-row writers, callers, vtables,
     Lua method tables, hook-site relocatability)
  G  message labels
  H  the NRO (records, strings, stub, exports, foreign hook acceptance, nn::hid symbols, manifest)

Negative controls (`--neg MODE`, each must exit 1): word, disasm, call, entry, offset,
static, scan, reloc, label, nro, manifest. `--selftest` runs the clean check and all of
them and exits 0 only when the clean run passes and every control fails.
"""
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
MOD = HERE.parents[2]
WORKSPACE = HERE.parents[4]
IMAGE = WORKSPACE / "gamedata/ssbu-13.0.4/main.bin"
IMAGE_SHA = "f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613"
IMAGE_SIZE = 86672752
MSBT = WORKSPACE / "gamedata/ssbu-13.0.4/files/ui/message/msg_name.msbt"
UI_RS = MOD / "plugin/src/ui.rs"
LOGIC_RS = MOD / "plugin/src/logic.rs"
MENU_RS = MOD / "plugin/src/menu.rs"
EDITOR_RS = MOD / "plugin/src/editor.rs"
LIB_RS = MOD / "plugin/src/lib.rs"
PKG = MOD / "builds/0.7.0-menu"
NRO = PKG / "libmii_customizer.nro"
MANIFEST = PKG / "MANIFEST.json"
TEXT = (0x100, 0x39C8000)
RELA0, RELA1 = 0x39C8070, 0x40C9FC8

NEG_MODES = ("word", "disasm", "call", "entry", "offset", "static", "scan", "reloc", "label", "nro", "manifest")
neg = None
if len(sys.argv) == 3 and sys.argv[1] == "--neg":
    neg = sys.argv[2]
    if neg not in NEG_MODES:
        print("unknown negative control %r; one of %s" % (neg, ", ".join(NEG_MODES)))
        sys.exit(2)

if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
    results = []
    clean = subprocess.run([sys.executable, str(HERE)], capture_output=True, text=True)
    last = clean.stdout.strip().splitlines()[-1] if clean.stdout.strip() else ""
    print("clean run: exit %d   %s" % (clean.returncode, last))
    ok = clean.returncode == 0
    for mode in NEG_MODES:
        run = subprocess.run([sys.executable, str(HERE), "--neg", mode], capture_output=True, text=True)
        first = next((l for l in run.stdout.splitlines() if l.startswith("FAIL")), "(no FAIL line)")
        print("--neg %-8s exit %d   first: %s" % (mode, run.returncode, first[:150]))
        ok = ok and run.returncode == 1
    print("selftest: %s" % ("ok (clean run passes, every control fails)" if ok else "NOT ok"))
    sys.exit(0 if ok else 1)

try:
    import capstone
except ImportError:
    print("capstone is not importable; set PYTHONPATH as in the docstring")
    sys.exit(2)

for needed in (IMAGE, MSBT, UI_RS, LOGIC_RS, MENU_RS, EDITOR_RS, LIB_RS, NRO):
    if not needed.is_file():
        print("missing input: %s" % needed)
        sys.exit(2)

image = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

checks = 0
fails = 0


def check(ok, text):
    global checks, fails
    checks += 1
    if not ok:
        fails += 1
    print(("PASS " if ok else "FAIL ") + text)
    return ok


def word(a):
    return struct.unpack_from("<I", image, a)[0]


def dis(a):
    ins = next(md.disasm(image[a:a + 4], a), None)
    if ins is None:
        return ".word 0x%08x" % word(a)
    return ("%s %s" % (ins.mnemonic, ins.op_str)).strip()


def sx(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def bl_target(a):
    w = word(a)
    if (w & 0x7C000000) != 0x14000000:
        return None
    return a + (sx(w & 0x3FFFFFF, 26) << 2)


def num(text):
    return int(text.replace("_", ""), 16)


# ---------------------------------------------------------------- A: image identity
print("== A image")
sha = hashlib.sha256(image).hexdigest()
if not check(sha == IMAGE_SHA and len(image) == IMAGE_SIZE, "image sha256 %s, %d bytes" % (sha, len(image))):
    print("not the audited image; stopping")
    sys.exit(2)

# ---------------------------------------------------------------- B: site records
print("== B site and probe words")
ui_src = UI_RS.read_text(encoding="utf-8")
logic_src = LOGIC_RS.read_text(encoding="utf-8")
named = {}
for m in re.finditer(r"const (\w+): \[u32; 4\] = \[([^\]]+)\];", ui_src):
    named[m.group(1)] = [num(w.strip()[2:]) for w in m.group(2).split(",") if w.strip()]


def records(src):
    out = []
    for m in re.finditer(r"Site\s*\{\s*offset: 0x([0-9a-f_]+),\s*words: (\[[^\]]+\]|\w+),?\s*\}", src):
        w = m.group(2)
        words = named[w] if w in named else [num(x.strip()[2:]) for x in w.strip("[]").split(",") if x.strip()]
        out.append((num(m.group(1)), words))
    return out


ui_records = records(ui_src)
param_records = records(logic_src)
sites_decl = int(re.search(r"pub const UI_SITES: usize = (\d+);", ui_src).group(1))
probes_decl = int(re.search(r"pub const PROBES: usize = (\d+);", ui_src).group(1))
check(sites_decl == 6 and probes_decl == 48, "ui.rs declares %d hook sites and %d probes" % (sites_decl, probes_decl))
check(len(ui_records) == sites_decl + probes_decl,
      "%d Site records parsed from ui.rs (expected %d)" % (len(ui_records), sites_decl + probes_decl))
check(len(param_records) == 1 and param_records[0][0] == 0x4E53E0, "logic.rs: one record, the stat hook 0x4e53e0")
check(len({off for off, _ in ui_records}) == len(ui_records), "no offset appears twice")
for off, words in param_records + ui_records:
    found = [word(off + 4 * k) for k in range(4)]
    expect = list(words)
    if neg == "word" and off == 0x180CEBC:
        expect[0] ^= 0x400  # another byte offset than #0x154
    check(found == expect, "words at 0x%x: %s" % (off, " ".join("%08x" % x for x in found)))

SITE_OFFSETS = [off for off, _ in ui_records[:sites_decl]]
check(SITE_OFFSETS == [0x180A030, 0x180ABD0, 0x328B5D0, 0x3288330, 0x19CD100, 0x19CCB20],
      "hook sites in order: " + " ".join("0x%x" % o for o in SITE_OFFSETS))

# ---------------------------------------------------------------- C: what the instructions are
print("== C disassembly of the instructions the design rests on")
DISASM = [
    # state reader 0x180ce40 (M3)
    (0x180CE4C, "ldrsw x8, [x0, #0x144]", "reader: stack index"),
    (0x180CE50, "cmp w8, #0x13", "reader: 19 slots"),
    (0x180CE5C, "ldr w8, [x8, #0xf8]", "reader: state on top of the stack"),
    (0x180CE60, "ldr w9, [x0, #0x148]", "reader: current state"),
    (0x180CE68, "cmp w9, w8", "reader: same state?"),
    (0x180CE6C, "b.eq #0x180cebc", "reader: same state -> restart test"),
    (0x180CEB8, "str wzr, [x19, #0x14c]", "reader: a state change clears the frame counter"),
    (0x180CEBC, "ldrb w8, [x19, #0x154]", "reader: restart byte"),
    (0x180CEC0, "cbz w8, #0x180cef4", "reader: clear -> return"),
    (0x180CEC4, "ldp x8, x10, [x19, #0x18]", "reader: change-callback pair"),
    (0x180CED0, "cbz x11, #0x180ceec", "reader: no callback -> skip the call"),
    (0x180CEEC, "str wzr, [x19, #0x14c]", "reader: restart clears the frame counter"),
    (0x180CEF0, "strb wzr, [x19, #0x154]", "reader: and the restart byte"),
    # frame update 0x180ead0
    (0x180EAF4, "bl #0x180ce40", "frame update: reader first"),
    (0x180EB24, "blr x8", "frame update: then the current state's handler"),
    (0x180EB28, "ldr w8, [x19, #0x14c]", "frame update: frame counter"),
    (0x180EB30, "add w8, w8, #1", "frame update: +1 after the handler"),
    (0x180EB34, "str w8, [x19, #0x14c]", "frame update: stored"),
    # state 5
    (0x180ABE4, "ldr w8, [x0, #0x14c]", "state 5: frame counter"),
    (0x180ABEC, "cbz w8, #0x180ac58", "state 5: 0 -> first-tick path"),
    (0x180AC18, "ldr w9, [x8, #0xe8]", "state 5: list state"),
    (0x180AC1C, "cbz w9, #0x180acbc", "state 5: 0 -> end-of-screen path"),
    (0x180ADF4, "ldr w8, [x19, #0x144]", "state 5 pop: load"),
    (0x180ADF8, "subs w8, w8, #1", "state 5 pop: -1"),
    (0x180ADFC, "b.lt #0x180b0e8", "state 5 pop: never below 0"),
    (0x180AE00, "str w8, [x19, #0x144]", "state 5 pop: store"),
    (0x180B060, "bl #0x19cfe00", "state 5 first tick: seeds S from the static"),
    (0x180B0E4, "strb wzr, [x19, #0x70]", "state 5 first tick: list active in the pump"),
    # scene constructor
    (0x180DF10, "stp xzr, xzr, [x19, #0x18]", "ctor: change-callback pair = 0"),
    (0x180DF20, "strb wzr, [x19, #0x154]", "ctor: restart byte = 0"),
    # row filler
    (0x19CCB3C, "ldp x9, x10, [x0, #0x128]", "row filler: item vector of S"),
    (0x19CCB58, "ldr x20, [x9, x8, lsl #3]", "row filler: the row's handle"),
    (0x19CCB74, "mov x22, x2", "row filler: row node = x2"),
    (0x19CCB90, "ldr x0, [x22, #8]", "row filler: dereferences the row node"),
    (0x19CCBE0, "add x0, sp, #0x18", "row filler: label struct"),
    (0x19CCBEC, "bl #0x3288330", "row filler: message key of the handle"),
    (0x19CCBF8, "add x8, sp, #8", "row filler: pane result buffer in x8"),
    (0x19CCBFC, "mov x0, x22", "row filler: row node"),
    (0x19CCC00, "bl #0x3776360", "row filler: find pane set_txt_val"),
    (0x19CCC04, "add x21, x21, #8", "row filler: key text = struct + 8"),
    (0x19CCC10, "bl #0x3779b70", "row filler: set message"),
    (0x19CCC14, "ldr x0, [sp, #0x10]", "row filler: the holder"),
    (0x19CCC28, "bl #0x392e590", "row filler: frees the holder"),
    (0x19CCC3C, "bl #0x3776360", "row filler: find pane set_txt_val_disable"),
    (0x19CCD84, "bl #0x328b5d0", "row filler: unlisted?"),
    (0x19CCD88, "tbz w0, #0, #0x19ccd94", "row filler: 0 -> enabled"),
    (0x19CCD8C, "ldrb w8, [x19, #0x169]", "row filler: S+0x169"),
    (0x19CCD90, "cbz w8, #0x19cce2c", "row filler: unlisted and flag clear -> disabled"),
    (0x19CCDA0, "ldr x8, [x8, #0x1f8]", "row filler, enabled: button slot +0x1f8"),
    (0x19CCDA4, "mov w1, #1", "row filler, enabled: argument 1"),
    (0x19CCE38, "ldr x8, [x8, #0x1f8]", "row filler, disabled: button slot +0x1f8"),
    (0x19CCE40, "mov w1, wzr", "row filler, disabled: argument 0"),
    # row filler thunk (secondary vtable)
    (0x19CD010, "sub x0, x0, #0x48", "thunk: S+0x48 -> S"),
    (0x19CD014, "b #0x19ccb20", "thunk: to the row filler entry"),
    # cursor helpers
    (0x19CD070, "bl #0x328b5d0", "cursor step A: unlisted?"),
    (0x19CD084, "add w8, w21, w19", "cursor step A: skips one row"),
    (0x19CD08C, "csel w19, w8, w20, gt", "cursor step A: or stays"),
    (0x19CCEEC, "bl #0x328b5d0", "cursor step B: unlisted?"),
    (0x19CCF18, "csel w0, w8, w19, gt", "cursor step B: skips or stays"),
    # scroller decide
    (0x377E230, "ldr x8, [x9, x8, lsl #3]", "scroller decide: cursor row part"),
    (0x377E234, "ldr x21, [x8, #0x28]", "scroller decide: its button"),
    (0x377E27C, "ldr x8, [x8, #0x200]", "scroller decide: button slot +0x200"),
    (0x377E288, "tbz w0, #0, #0x377e33c", "scroller decide: 0 -> nothing decided"),
    (0x377E290, "ldr x8, [x8, #0x210]", "scroller decide: button slot +0x210"),
    (0x377E29C, "tbz w0, #0, #0x377e33c", "scroller decide: 0 -> nothing decided"),
    (0x377E2A0, "ldr w8, [x19, #0x2a0]", "scroller decide: cursor row"),
    (0x377E2A4, "str w8, [x19, #0x2b0]", "scroller decide: pending decided row"),
    (0x377E33C, "ldr x0, [x19, #0x140]", "scroller, nothing decided: optional object"),
    (0x377D648, "ldr w8, [x19, #0x2b0]", "scroller: pending decided row"),
    (0x377D658, "str w8, [x19, #0x2b4]", "scroller: becomes the decided row"),
    (0x33630B4, "ldrsw x10, [x9, #0x2b4]", "Lua get_decided_item returns scroller+0x2b4"),
    # button class
    (0x378A6CC, "strb w1, [x0, #0x1c2]", "button +0x1f8: stores the enable bit"),
    (0x378A6F0, "ldrb w0, [x0, #0x1c2]", "button +0x200: returns it"),
    (0x378A6F4, "ret", "button +0x200: nothing else"),
    # pane lookup 0x3776360
    (0x3776378, "mov x20, x8", "find pane: result pointer comes in x8"),
    (0x37763D4, "mov x19, x0", "find pane: row node comes in x0"),
    (0x3776458, "str x8, [x20]", "find pane: result[0] = vtable"),
    (0x377645C, "bl #0x392dce0", "find pane: allocates the holder"),
    (0x37764B0, "str x22, [x20, #8]", "find pane: result[1] = holder"),
    (0x37764B4, "stp xzr, xzr, [x22, #0x10]", "find pane: holder zeroed"),
    (0x37764BC, "ldr x8, [x19, #8]", "find pane: dereferences the row node like the row filler"),
    (0x37764C4, "cbz x8, #0x3776504", "find pane: null-checked"),
    (0x37764F0, "bl #0x3772a30", "find pane: text-pane cast"),
    (0x37764F4, "str x0, [x22, #0x10]", "find pane: holder+0x10 = text pane"),
    # set message / set text
    (0x3779BA8, "ldr x9, [x0, #8]", "set message: holder"),
    (0x3779BAC, "ldr x9, [x9, #0x10]", "set message: text pane = holder+0x10"),
    (0x3779BB0, "cbz x9, #0x3779cb4", "set message: null-checked"),
    (0x335A1B0, "bl #0x3779b70", "Lua set_text_message -> set message"),
    (0x335A54C, "ldr x8, [x21, #8]", "Lua set_text_string: holder"),
    (0x335A550, "ldr x0, [x8, #0x10]", "Lua set_text_string: text pane = holder+0x10"),
    (0x335A554, "cbz x0, #0x335a55c", "Lua set_text_string: null-checked"),
    (0x335A558, "bl #0x37a22f0", "Lua set_text_string -> set UTF-8 text"),
    (0x37A2304, "mov x20, x1", "set UTF-8 text: string in x1"),
    (0x37A2308, "mov x19, x0", "set UTF-8 text: pane in x0"),
    (0x37A231C, "cbz x20, #0x37a23b8", "set UTF-8 text: null string handled"),
    (0x37A23A0, "cmp x2, #0x7fe", "set UTF-8 text: at most 0x7fe units"),
    (0x37A23DC, "bl #0x37a1cc0", "set UTF-8 text -> set UTF-16 text"),
    # 0.4.0 facts still relied on
    (0x180A098, "ldr w8, [x8, #0x128]", "dispatcher: exit value"),
    (0x180A064, "ldrb w9, [x8, #0x130]", "dispatcher: has-value flag"),
    (0x180A0C0, "add w10, w8, #4", "dispatcher: pushed state = value + 4"),
    (0x180AC28, "strb wzr, [x8, #0x168]", "state 5: preview flag consumed"),
    (0x180AC3C, "str x8, [x9, #0xcb0]", "state 5: writer 1 of the headgear static"),
    (0x180AD20, "str x10, [x11, #0xcb0]", "state 5: writer 2 of the headgear static"),
    (0x19CFE18, "stp x1, x1, [x0, #0x140]", "set_select: preview and decided slots"),
    (0x19CFE1C, "str x1, [x0, #0x150]", "set_select: selected slot"),
    (0x19CFFF0, "bl #0x328b5d0", "set_select tail: unlisted flag from the handle"),
    (0x19CFFF8, "strb w8, [x19, #0x169]", "set_select tail: stored in S+0x169"),
    (0x19CC530, "cbz w8, #0x19cc88c", "frame callback block A: S+0x169 clear -> no model change"),
    (0x19CC740, "cbz w8, #0x19cc80c", "frame callback block B: same"),
    # Sort handler 0x19cd100 (S1 facts)
    (0x19CD11C, "cmp w1, #2", "sort: mode 2 test"),
    (0x19CD120, "b.eq #0x19cd174", "sort: mode 2 (name) path"),
    (0x19CD124, "cmp w1, #1", "sort: mode 1 test"),
    (0x19CD128, "b.eq #0x19cd150", "sort: mode 1 path"),
    (0x19CD12C, "cbnz w1, #0x19cd280", "sort: any mode but 0..2 goes to the epilogue"),
    (0x19CD130, "str wzr, [x19, #0x164]", "sort mode 0: stores 0 in +0x164"),
    (0x19CD150, "mov w8, #1", "sort mode 1: loads 1"),
    (0x19CD154, "str w8, [x19, #0x164]", "sort mode 1: stores 1 in +0x164"),
    (0x19CD174, "mov w8, #2", "sort mode 2: loads 2"),
    (0x19CD178, "str w8, [x19, #0x164]", "sort mode 2: stores 2 in +0x164"),
    (0x19CD280, "ldp x29, x30, [sp, #0x60]", "sort: 0x19cd280 is the epilogue"),
    (0x19CD294, "ret", "sort: epilogue ends"),
    (0x3783114, "str w1, [x19, #0x34]", "set item count: count"),
    (0x3783118, "str w1, [x19, #0x288]", "set item count: count (scroller+0x288)"),
    # Scene builder registration of Lua constants (0.6.0 Minus global channel)
    (0x1808FF8, "ldr x8, [x22, #0x40]", "scene builder: script holder = inner+0x40 (S_SCRIPT)"),
    (0x1808FFC, "ldr x0, [x8]", "scene builder: lua state pointer from holder"),
    (0x1809000, "cbz x0, #0x1809150", "scene builder: null lua state skip"),
    (0x1809014, "mov w3, #7", "scene builder: integer constant value 7 (INPUT_FAVORITE)"),
    (0x1809018, "bl #0x33750a0", "scene builder: register constant call (FN_REG_CONST)"),
]
for a, expect, what in DISASM:
    if neg == "disasm" and a == 0x377E288:
        expect = "tbnz w0, #0, #0x377e33c"
    got = dis(a)
    check(got == expect, "0x%x %-34s %s" % (a, got, what) if got == expect
          else "0x%x expected %r got %r (%s)" % (a, expect, got, what))

# ---------------------------------------------------------------- D: call targets
print("== D functions the plugin calls or hooks")
consts = {m.group(1): num(m.group(2)) for m in re.finditer(r"pub const (\w+): usize = 0x([0-9a-f_]+);", ui_src)}


def is_entry(a):
    """A function entry: a prologue word, after a word that ends the previous function."""
    w, prev = word(a), word(a - 4)
    prologue = (w & 0xFF8003FF) == 0xD10003FF or (w & 0xFFC003E0) == 0xA98003E0 or (w & 0xFFE00FE0) == 0xF8000FE0
    prev_ends = prev in (0xD65F03C0, 0) or (prev & 0xFC000000) == 0x14000000 or (prev & 0xFFFFFC1F) == 0xD61F0000 \
        or (prev & 0xFC000000) == 0x94000000 or prev == 0xD4200020
    return prologue and prev_ends


FUNCTIONS = [
    # (constant in ui.rs or None, address, a site that calls it, what)
    ("FN_SET_ITEM_COUNT", 0x37830E0, None, "scroller set item count"),
    ("FN_SET_SELECT", 0x19CFE00, 0x180B060, "set_select (state 5 first tick)"),
    ("FN_REG_CONST", 0x33750A0, 0x1809018, "Lua constant registrar (scene builder and Minus)"),
    ("FN_ALLOC", 0x392DCE0, 0x377645C, "allocator"),
    ("FN_FREE", 0x392E590, 0x19CCC28, "free"),
    ("FN_FIND_PANE", 0x3776360, 0x19CCC00, "find pane of a row node"),
    ("FN_SET_TEXT_UTF8", 0x37A22F0, 0x335A558, "set UTF-8 text of a text pane"),
    (None, 0x180A030, None, "hooked: dispatcher"),
    (None, 0x180ABD0, None, "hooked: headgear state"),
    (None, 0x328B5D0, 0x19CCD84, "hooked: unlisted test"),
    (None, 0x3288330, 0x19CCBEC, "hooked: message key"),
    (None, 0x19CD100, None, "hooked: sort"),
    (None, 0x19CCB20, 0x19CD014, "hooked: row filler"),
    (None, 0x180CE40, 0x180EAF4, "state reader (not called by the plugin)"),
]
for name, addr, site, what in FUNCTIONS:
    if name is not None:
        check(consts.get(name) == addr, "%s = 0x%x in ui.rs (%s)" % (name, consts.get(name, 0), what))
    entry_addr = addr + 4 if (neg == "entry" and addr == 0x3776360) else addr
    check(is_entry(entry_addr), "0x%x is a function entry: %s (%s)" % (entry_addr, dis(entry_addr), what))
    if site is not None:
        expect = addr + 0x10 if (neg == "call" and addr == 0x37A22F0) else addr
        check(bl_target(site) == expect, "0x%x branches to 0x%x (%s)" % (site, bl_target(site) or 0, what))

# ---------------------------------------------------------------- E: offsets and statics
print("== E numeric constants of ui.rs, each tied to an instruction")


def operand_has(a, text):
    return text in dis(a)


OFFSETS = [
    ("SCENE_CHANGE_CB", 0x18, 0x180CEC4, "[x19, #0x18]"),
    ("SCENE_STACK", 0xF8, 0x180CE5C, "#0xf8]"),
    ("SCENE_DEPTH", 0x144, 0x180ADF4, "[x19, #0x144]"),
    ("SCENE_STATE", 0x148, 0x180CE60, "[x0, #0x148]"),
    ("SCENE_RESTART", 0x154, 0x180CEBC, "[x19, #0x154]"),
    ("SCENE_FRAME", 0x14C, 0x180ABE4, "[x0, #0x14c]"),
    ("SCENE_EDIT", 0x178, 0x180A048, "[x0, #0x178]"),
    ("SCENE_HAT", 0x180, 0x180ABF0, "[x19, #0x180]"),
    ("WRAP_INNER", 0x80, 0x180ABF4, "[x8, #0x80]"),
    ("EDIT_EXIT_VALUE", 0x128, 0x180A098, "[x8, #0x128]"),
    ("EDIT_HAS_VALUE", 0x130, 0x180A064, "[x8, #0x130]"),
    ("S_SCRIPT", 0x40, 0x19CF830, "#0x40]"),
    ("S_STATE", 0xE8, 0x180AC18, "[x8, #0xe8]"),
    ("S_SCROLLER", 0xF8, 0x19CC434, "#0xf8]"),
    ("S_VEC_BEGIN", 0x128, 0x19CCB3C, "[x0, #0x128]"),
    ("S_PREVIEW", 0x140, 0x180AC34, "[x8, #0x140]"),
    ("S_DECIDED", 0x148, 0x180ACBC, "[x8, #0x148]"),
    ("S_SELECTED", 0x150, 0x180AD38, "[x8, #0x150]"),
    ("S_PREVIEW_DIRTY", 0x168, 0x180AC20, "[x8, #0x168]"),
    ("S_UNLISTED_FLAG", 0x169, 0x19CCD8C, "[x19, #0x169]"),
    ("SCROLLER_COUNT", 0x288, 0x3783118, "[x19, #0x288]"),
    ("SCROLLER_CURSOR", 0x2A0, 0x377D2B8, "[x0, #0x2a0]"),
    ("SCROLLER_SELECTED", 0x2A4, 0x377D2BC, "[x0, #0x2a4]"),
    ("HOLDER_TEXT", 0x10, 0x37764F4, "[x22, #0x10]"),
]
for name, value, a, operand in OFFSETS:
    want = value + 8 if (neg == "offset" and name == "SCENE_RESTART") else value
    check(consts.get(name) == want and operand_has(a, operand),
          "%s = 0x%x, used at 0x%x: %s" % (name, consts.get(name, -1), a, dis(a)))
check(consts.get("S_VEC_END") == 0x130 and consts.get("S_VEC_CAP") == 0x138,
      "S_VEC_END / S_VEC_CAP follow S_VEC_BEGIN (std::vector: begin, end, capacity)")


def adrp_page(a):
    w = word(a)
    if (w & 0x9F000000) != 0x90000000:
        return None
    return (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)


hat = (adrp_page(0x180AC38) or 0) + 0xCB0
want_hat = consts.get("HAT_STATIC", 0) + (8 if neg == "static" else 0)
check(hat == want_hat, "HAT_STATIC 0x%x = adrp at 0x180ac38 + #0xcb0 = 0x%x" % (consts.get("HAT_STATIC", 0), hat))
check(consts.get("HAT_STATIC", 0) - consts.get("WORK_RECORD", 0) == 0x138, "HAT_STATIC = WORK_RECORD + 0x138")
check(consts.get("RECORD_SNAPSHOT", 0) >= 0x140, "the snapshot covers the headgear handle")


def cstr(addr):
    end = image.index(b"\0", addr)
    return image[addr:end].decode("ascii", "replace")


check(cstr(consts["STR_ITEM_NUM"]) == "SCROLLER_ITEM_NUM", "string SCROLLER_ITEM_NUM at 0x%x" % consts["STR_ITEM_NUM"])
check(cstr(consts["STR_INT"]) == "i", "string 'i' at 0x%x" % consts["STR_INT"])
check(cstr(0x425E382) == "set_txt_val" and cstr(0x436AC1A) == "set_txt_val_disable",
      "the row filler's two pane names: %r, %r" % (cstr(0x425E382), cstr(0x436AC1A)))
editor_src = EDITOR_RS.read_text(encoding="utf-8")
check('b"set_txt_val\\0"' in editor_src and 'b"set_txt_val_disable\\0"' in editor_src,
      "editor.rs uses the same two pane names, NUL-terminated")
check(b'b"MC_MINUS\x00"' in EDITOR_RS.read_bytes(), "editor.rs defines MINUS_GLOBAL")
check("pub const BUTTON_MINUS: u64 = 1 << 11;" in ui_src, "ui.rs defines BUTTON_MINUS = 1 << 11")
check("pub const BUTTON_ZL: u64 = 1 << 8;" in ui_src and "pub const BUTTON_ZR: u64 = 1 << 9;" in ui_src,
      "ui.rs defines BUTTON_ZL and BUTTON_ZR")

# ---------------------------------------------------------------- F: derived facts
print("== F facts derived from whole ranges")
slots = {}
for at in range(RELA0, RELA1, 24):
    r_off, r_info, _pad, addend = struct.unpack_from("<QIIQ", image, at)
    if r_info == 0x403:
        slots[r_off] = addend

SCENE_LO, SCENE_HI = 0x1808980, 0x180F400
refs = [(a, dis(a)) for a in range(SCENE_LO, SCENE_HI, 4) if "#0x154]" in dis(a)]
loads = [a for a, t in refs if t.startswith("ldrb")]
zero_stores = [a for a, t in refs if t.startswith("strb wzr")]
want_refs = 5 if neg == "scan" else 4
check(len(refs) == want_refs and loads == [0x180CEBC] and zero_stores == [0x180CEF0, 0x180DF20, 0x180E168],
      "scene code 0x%x..0x%x: the restart byte +0x154 has %d references: one load (reader) and three "
      "stores of zero; nothing in the scene code ever sets it: %s"
      % (SCENE_LO, SCENE_HI, len(refs), " ".join("0x%x" % a for a, _ in refs)))

pair = [(a, dis(a)) for a in range(SCENE_LO, SCENE_HI, 4)
        if re.match(r"st[rp] .*\[x19, #0x(18|20)\]$", dis(a))]
check([a for a, _ in pair] == [0x180DF10],
      "scene code: the only store to [x19, #0x18/#0x20] is the constructor's zeroing: %s"
      % "; ".join("0x%x %s" % p for p in pair))

DISP_LO, DISP_HI = 0x180A030, 0x180A5B0
hat_refs = [a for a in range(DISP_LO, DISP_HI, 4) if "#0x180]" in dis(a)]
check(hat_refs == [], "the dispatcher (state 3) 0x%x..0x%x never touches the headgear list object (scene+0x180)"
      % (DISP_LO, DISP_HI))

SCR_LO, SCR_HI = 0x377C000, 0x3784000
w2b4 = [a for a in range(SCR_LO, SCR_HI, 4) if re.match(r"str w\d+, \[x\d+, #0x2b4\]", dis(a))]
check(w2b4 == [0x377D658, 0x3783938], "scroller code: writers of the decided row +0x2b4: %s"
      % " ".join("0x%x" % a for a in w2b4))
w2b0 = [a for a in range(SCR_LO, SCR_HI, 4) if re.match(r"str [wx]\d+, \[x\d+, #0x2b0\]", dis(a))]
check(w2b0 == [0x377CD8C, 0x377D660, 0x377E2A4, 0x377FB94, 0x377FC6C, 0x3780014, 0x3783940],
      "scroller code: writers of the pending decided row +0x2b0: %s (0x377e2a4 = button decide, "
      "0x3780014 = the pointer/touch path, the rest reset it)" % " ".join("0x%x" % a for a in w2b0))

callers = []
for a in range(TEXT[0], TEXT[1], 4):
    w = word(a)
    if (w & 0xFC000000) == 0x94000000 and a + (sx(w & 0x3FFFFFF, 26) << 2) == 0x328B5D0:
        callers.append(a)
LIST_CALLERS = [0x19CC548, 0x19CC754, 0x19CCD84, 0x19CCEEC, 0x19CD070, 0x19CFFF0]
check(all(c in callers for c in LIST_CALLERS),
      "0x328b5d0 has %d bl callers; the six of the headgear list class are among them: %s"
      % (len(callers), " ".join("0x%x" % c for c in LIST_CALLERS)))
in_filler = [c for c in callers if 0x19CCB20 <= c < 0x19CCEA0]
check(in_filler == [0x19CCD84], "the row filler 0x19ccb20..0x19ccea0 asks 0x328b5d0 exactly once (0x19ccd84)")

# the row filler is primary slot +0x38 of the sub-object vtable, the thunk secondary slot +0x10
vt_sub = consts["VT_SUB_OBJECT"]
want_slot = 0x19CCB24 if neg == "reloc" else 0x19CCB20
check(slots.get(vt_sub + 0x38) == want_slot, "sub-object vtable 0x%x slot +0x38 -> 0x%x (row filler)"
      % (vt_sub, slots.get(vt_sub + 0x38, 0)))
check(slots.get(vt_sub + 0x58 + 0x10) == 0x19CD010, "secondary vtable 0x%x slot +0x10 -> 0x%x (thunk to the row filler)"
      % (vt_sub + 0x58, slots.get(vt_sub + 0x58 + 0x10, 0)))
check(slots.get(vt_sub + 0x58 + 0x28) == 0x19CD020 and slots.get(vt_sub + 0x40) == 0x19CCEA0,
      "cursor helpers: secondary slot +0x28 -> 0x19cd020, primary slot +0x40 -> 0x19ccea0")
check(slots.get(vt_sub) == 0x19CC9E0 and slots.get(consts["VT_LIST_OBJECT"] + 0x18) == 0x19CFDB0,
      "sub-object slot 0 = 0x19cc9e0, list object slot +0x18 = 0x19cfdb0 (P10-HAT-OPEN)")
check(consts["VT_SCROLLER"] in slots, "scroller vtable 0x%x is a relocated table" % consts["VT_SCROLLER"])

# the button class family: every relocated table that holds the enable-bit setter or getter
setter_tables = sorted(a - 0x1F8 for a, v in slots.items() if v == 0x378A6C0)
getter_tables = sorted(a - 0x200 for a, v in slots.items() if v == 0x378A6F0)
check(len(setter_tables) == 9 and setter_tables == getter_tables,
      "the enable-bit setter 0x378a6c0 sits in slot +0x1f8 of %d vtables and the getter 0x378a6f0 in slot "
      "+0x200 of the same ones (no table has one without the other): %s"
      % (len(setter_tables), " ".join("0x%x" % t for t in setter_tables)))
check(all(0x523C000 <= t < 0x5240000 for t in setter_tables) and 0x523C000 <= consts["VT_SCROLLER"] < 0x5240000,
      "all of them, and the scroller's vtable, lie in 0x523c000..0x5240000 (the UI part classes)")
slot210 = sorted({slots.get(t + 0x210, 0) for t in setter_tables})
check(slot210 == [0x378A710, 0x378DE10] and dis(0x378A710) == "ldrb w0, [x0, #0x1c3]" and dis(0x378DE10) == "mov w0, wzr",
      "slot +0x210 of that family is a second flag byte (%s) or constant 0 (%s): it can only refuse more"
      % (dis(0x378A710), dis(0x378DE10)))

# Lua method tables {name, function}
LUA = [(0x51833B0, "set_text_message", 0x335A100), (0x51833E0, "set_text_string", 0x335A490),
       (0x5183B40, "get_decided_item", 0x3363070)]
for at, name, fn in LUA:
    check(at in slots and cstr(slots[at]) == name and slots.get(at + 8) == fn,
          "Lua method table 0x%x: %s -> 0x%x" % (at, name, slots.get(at + 8, 0)))

# A64HookFunction overwrites the first instructions of a site; none of them is PC-relative
PCREL = ("adr", "adrp", "b", "bl", "cbz", "cbnz", "tbz", "tbnz")
for off in SITE_OFFSETS:
    heads = [dis(off + 4 * k) for k in range(5)]
    bad = [t for t in heads if t.split()[0] in PCREL or t.startswith("b.") or ("ldr" in t and "#0x" in t and "[" not in t)]
    check(not bad, "hook site 0x%x: first five instructions are position-independent: %s" % (off, " ; ".join(heads)))

# ---------------------------------------------------------------- G: message labels
print("== G message labels")
msbt = MSBT.read_bytes()
menu_src = MENU_RS.read_text(encoding="utf-8")
default_label = re.search(r'pub const DEFAULT_LABEL: &str = "([a-z0-9_]+)";', menu_src).group(1)
none_label = re.search(r'pub const NONE_LABEL: &str = "([a-z0-9_]+)";', ui_src).group(1)
unknown_label = re.search(r'pub const UNKNOWN_LABEL: &str = "([a-z0-9_]+)";', ui_src).group(1)
check(default_label == "nam_chr1_00_miigunner", "row 0 of an entry page: %s (contract M2)" % default_label)


def label_exists(label):
    return bytes([len(label)]) + label.encode() in msbt


for label in (default_label, none_label, unknown_label):
    probe = label + "_zz" if neg == "label" and label == default_label else label
    check(label_exists(probe), "label %s exists in ui/message/msg_name.msbt" % probe)

# ---------------------------------------------------------------- H: the NRO
print("== H the built NRO")
nro = NRO.read_bytes()
nro_sha = hashlib.sha256(nro).hexdigest()
print("     %s: %d bytes, sha256 %s" % (NRO.relative_to(MOD).as_posix(), len(nro), nro_sha))
check(nro[0x10:0x14] == b"NRO0", "NRO0 magic")
for k, (off, words) in enumerate(param_records + ui_records):
    rec = struct.pack("<Q4I", off, *words)
    if neg == "nro" and off == 0x19CCB20:
        rec = struct.pack("<Q4I", off + 4, *words)
    check(rec in nro, "record for 0x%x is in the NRO" % off)
site_table = b"".join(struct.pack("<Q4I", off, *words) for off, words in param_records + ui_records[:sites_decl])
probe_table = b"".join(struct.pack("<Q4I", off, *words) for off, words in ui_records[sites_decl:])
check(site_table in nro, "MC_SITES: the stat site and the six UI sites, contiguous and in order")
check(probe_table in nro, "MC_PROBES: the 48 probes, contiguous and in order")
STRINGS = [b"sd:/ultimate/mii_customizer/menu.txt", b"sd:/ultimate/mii_customizer/list.txt",
           b"sd:/ultimate/mii_customizer/ui_off", b"sd:/ultimate/mii_customizer/text_off",
           b"sd:/ultimate/mii_customizer/minus_off", b"sd:/ultimate/mii_customizer/loadouts.txt",
           b"sd:/ultimate/mii_customizer/names.txt", b"mc_menu 1", b"mc_list 1", b"mc_names 1",
           b"mc_loadouts 3", b"set_txt_val\0", b"set_txt_val_disable\0", default_label.encode(),
           none_label.encode(), unknown_label.encode(), b"0.7.0", b"MC_MINUS\0",
           b"mc_save_loadouts", b"MC_SITES", b"MC_PROBES"]
for text in STRINGS:
    check(text in nro, "NRO contains %r" % text.decode("ascii", "replace"))

# foreign hook acceptance (0.5.1 rule in lib.rs)
lib_src = LIB_RS.read_text(encoding="utf-8")
check("0x5800_0051" in lib_src and "0xd61f_0220" in lib_src,
      "lib.rs accepts foreign hook stub ldr x17,#8 ; br x17 (0x58000051, 0xd61f0220) at FN_SET_TEXT_UTF8")

# nn::hid symbols used in NRO
HID_SYMS = [
    b"_ZN2nn3hid15GetNpadStyleSetERKj",
    b"_ZN2nn3hid12GetNpadStateEPNS0_16NpadFullKeyStateERKj",
    b"_ZN2nn3hid12GetNpadStateEPNS0_17NpadHandheldStateERKj",
    b"_ZN2nn3hid12GetNpadStateEPNS0_16NpadJoyDualStateERKj",
    b"_ZN2nn3hid12GetNpadStateEPNS0_16NpadJoyLeftStateERKj",
    b"_ZN2nn3hid12GetNpadStateEPNS0_17NpadJoyRightStateERKj",
    b"_ZN2nn3hid12GetNpadStateEPNS0_11NpadGcStateERKj",
]
for sym in HID_SYMS:
    check(sym in nro, "NRO references nn::hid symbol %s" % sym.decode("ascii"))

# mc_call_sret: stp x29,x30,[sp,#-16]! ; mov x29,sp ; mov x9,x0 ; mov x8,x1 ; mov x0,x2 ; mov x1,x3 ;
#               blr x9 ; ldp x29,x30,[sp],#16 ; ret
STUB = struct.pack("<9I", 0xA9BF7BFD, 0x910003FD, 0xAA0003E9, 0xAA0103E8, 0xAA0203E0, 0xAA0303E1,
                   0xD63F0120, 0xA8C17BFD, 0xD65F03C0)
check(nro.count(STUB) == 1, "the x8-result call stub is in the NRO once, as written")
stub_text = [("%s %s" % (i.mnemonic, i.op_str)).strip() for i in md.disasm(STUB, 0)]
check(stub_text == ["stp x29, x30, [sp, #-0x10]!", "mov x29, sp", "mov x9, x0", "mov x8, x1", "mov x0, x2",
                    "mov x1, x3", "blr x9", "ldp x29, x30, [sp], #0x10", "ret"],
      "stub disassembly: " + " ; ".join(stub_text))

nro_text_end = struct.unpack_from("<I", nro, 0x24)[0]


def nro_word(a):
    return struct.unpack_from("<I", nro, a)[0]


def nro_dis(a, n):
    out = []
    for k in range(n):
        ins = next(md.disasm(nro[a + 4 * k:a + 4 * k + 4], a + 4 * k), None)
        out.append(("%s %s" % (ins.mnemonic, ins.op_str)).strip() if ins else ".word")
    return out


PARAM_STUB = [0xA9BF7BFD, 0x910003FD, 0xD10043FF, 0xF90003FE, None, 0x910043FF, 0xA8C17BFD, 0xD65F03C0]
stubs = [a for a in range(0, nro_text_end, 4)
         if all(s is None or nro_word(a + 4 * k) == s for k, s in enumerate(PARAM_STUB)) and nro_word(a + 16) >> 26 == 0x25]
check(len(stubs) == 1, "exactly one stat-hook entry stub (unchanged since 0.1.0): %s" % " ".join("0x%x" % a for a in stubs))
if stubs:
    impl = stubs[0] + 16 + (sx(nro_word(stubs[0] + 16) & 0x3FFFFFF, 26) << 2)
    body = nro_dis(impl, 64)
    k_br = next((k for k, t in enumerate(body) if t.startswith("br ")), None)
    miss = body[:k_br + 1] if k_br is not None else []
    check(0 < len(miss) <= 32, "stat hook, unknown hash: %d instructions of straight-line code ending in `br`" % len(miss))
    forbidden = [t for t in miss if t.split()[0] in ("bl", "blr", "ret", "stp", "str", "strb", "stur", "svc",
                                                     "ldxr", "stxr", "ldaxr", "stlxr")
                 or (t.split()[0] == "sub" and "sp" in t) or re.search(r"\[sp[^\]]*\]!|\], #", t)]
    check(not forbidden, "stat hook, unknown hash: no call, no return, no stack write, no sp change, no "
          "exclusive instruction: %s" % (forbidden or "none"))
if MANIFEST.is_file():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    want_sha = manifest["nro"]["sha256"]
    if neg == "manifest":
        want_sha = "0" * 64
    check(want_sha == nro_sha and manifest["nro"]["bytes"] == len(nro), "NRO equals MANIFEST.json (sha256, size)")
    for item in manifest.get("source", []) + manifest.get("files", []):
        path = WORKSPACE / item["path"]
        ok = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        check(ok, "manifest hash of %s" % item["path"])
else:
    check(neg != "manifest", "MANIFEST.json not written yet (checked once it exists)")

print("P14-SORT-OPTIONS check: %d checks, %d failed%s" % (checks, fails, "   [negative control: %s]" % neg if neg else ""))
sys.exit(1 if fails else 0)
