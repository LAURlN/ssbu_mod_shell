"""P8-HAT-NATIVE claim checker.

Re-reads every address cited in research/P8-HAT-NATIVE.md straight out of the
flat image gamedata/ssbu-13.0.4/main.bin (address == file offset) and fails if
anything differs from what the report claims.

    PYTHONPATH=../ssbu_mod_new/builds/.cache/dk_cargo/python \
        python evidence/P8-HAT-NATIVE/check_p8_hat_native.py

Negative control (must exit non-zero): add --neg NAME, where NAME is one of the
injected faults listed in NEGATIVE_CONTROLS below.

Exit codes: 0 = all claims match, 1 = at least one mismatch, 2 = bad usage /
input identity failure.
"""
import hashlib
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
IMAGE = ROOT / 'gamedata/ssbu-13.0.4/main.bin'
SHA256 = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
SIZE = 86672752

RELOC_FIRST = 0x39C8070
RELOC_LAST = 0x40C9FC8   # exclusive; 24-byte records
REC = 24
R_AARCH64_RELATIVE = 0x403

fails = []
checks = 0


def word(a):
    return struct.unpack_from('<I', DATA, a)[0]


def qword(a):
    return struct.unpack_from('<Q', DATA, a)[0]


def sx(v, b):
    """Sign-extend the low b bits of v."""
    return v - (1 << b) if v & (1 << (b - 1)) else v


def br_target(w, a):
    """Target of a b / bl / b.cond (26-bit imm) at address a; None if none."""
    if (w & 0xFC000000) in (0x14000000, 0x94000000):     # b / bl
        return a + (sx(w & 0x3FFFFFF, 26) << 2)
    if (w & 0xFF000010) == 0x54000000:                   # b.cond: imm19 at 23:5
        return a + (sx((w >> 5) & 0x7FFFF, 19) << 2)
    return None


def cstr(a, limit=128):
    e = DATA.find(b'\0', a, a + limit)
    return '' if e < 0 else DATA[a:e].decode('ascii', 'replace')


def ok(cond, label, detail=''):
    global checks
    checks += 1
    if not cond:
        fails.append('%s %s' % (label, detail))
    return cond


def expect_word(addr, expect, label):
    got = word(addr)
    ok(got == expect, label,
       'at 0x%08x expected 0x%08x got 0x%08x' % (addr, expect, got))


def expect_branch(addr, target, label):
    got = br_target(word(addr), addr)
    ok(got == target, label,
       'branch at 0x%08x expected target 0x%x got %s' % (addr, target, hex(got) if got else 'none'))


def expect_adrp_add(addr, target, label):
    """addr points at the `add` that completes an adrp; checks the pair resolves
    to `target` (a string address when it is inside .rodata)."""
    w = word(addr)
    ok((w & 0xFF800000) == 0x91000000, label + ' (add form)',
       'at 0x%08x got 0x%08x' % (addr, w))
    rd = w & 31
    rn = (w >> 5) & 31
    imm = (w >> 10) & 0xFFF
    ad = word(addr - 4)
    ok((ad & 0x9F000000) == 0x90000000, label + ' (adrp form)',
       'at 0x%08x got 0x%08x' % (addr - 4, ad))
    page = (addr & ~0xFFF) + (sx((((ad >> 5) & 0x7FFFF) << 2) | ((ad >> 29) & 3), 21) << 12)
    ok(rn == rd, label + ' (same base register)',
       'adrp rd=%d add rn=%d' % (rd, rn))
    ok(page + imm == target, label + ' (resolves)',
       'adrp+add resolved 0x%x expected 0x%x' % (page + imm, target))


def expect_str(addr, text, label):
    got = cstr(addr)
    ok(got == text, label,
       'string at 0x%08x expected %r got %r' % (addr, text, got))


def expect_reloc_slot(slot, addend, label):
    """A RELATIVE relocation record targets `slot` with `addend`."""
    found = []
    for a in range(RELOC_FIRST, RELOC_LAST, REC):
        if qword(a) == slot and word(a + 8) == R_AARCH64_RELATIVE \
                and word(a + 0xC) == 0 and qword(a + 0x10) == addend:
            found.append(a)
    ok(bool(found), label,
       'no RELATIVE record for slot 0x%x addend 0x%x' % (slot, addend))


def expect_no_reloc_addend(addend, label):
    for a in range(RELOC_FIRST, RELOC_LAST, REC):
        if word(a + 8) == R_AARCH64_RELATIVE and word(a + 0xC) == 0 \
                and qword(a + 0x10) == addend:
            ok(False, label, 'unexpected RELATIVE addend 0x%x at slot 0x%x'
               % (addend, qword(a)))
            return
    ok(True, label)


# ---------------------------------------------------------------- identity ---
if not IMAGE.is_file():
    sys.stderr.write('missing input %s\n' % IMAGE)
    sys.exit(2)
DATA = IMAGE.read_bytes()
digest = hashlib.sha256(DATA).hexdigest()
if digest != SHA256 or len(DATA) != SIZE:
    sys.stderr.write('input identity mismatch: sha256 %s size %d\n' % (digest, len(DATA)))
    sys.exit(2)

NEG = None
for i, a in enumerate(sys.argv):
    if a == '--neg' and i + 1 < len(sys.argv):
        NEG = sys.argv[i + 1]

# ------------------------------------------------------------ Q0 strings -----
expect_str(0x427F3A7, 'sort_id_list', 'anchor sort_id_list')
expect_str(0x4290580, 'get_top_index', 'anchor get_top_index')
expect_str(0x4290570, 'sub_list_window', 'anchor sub_list_window')
expect_str(0x4348C43, 'sub_list_window_facade', 'anchor sub_list_window_facade')
expect_str(0x436B678, 'scroller', 'anchor scroller')
expect_str(0x426E989, 'mii_select_scroller', 'anchor mii_select_scroller')
expect_str(0x42A18E6, 'SCROLLER_ITEM_NUM', 'anchor SCROLLER_ITEM_NUM')
expect_str(0x4358A4E, 'MetatableLayoutListScroller', 'scroller metatable name')
expect_str(0x42A06FE, 'nam_mii_hat_%s', 'hat row label format')
expect_str(0x43FEAB3, 'nam_mii_body_%s', 'body row label format')
expect_str(0x4306E2F, 'selecteditem', 'row part selecteditem')
expect_str(0x44533D3, 'notselecteditem', 'row part notselecteditem')
expect_str(0x425E382, 'set_txt_val', 'row part set_txt_val')
expect_str(0x436AC1A, 'set_txt_val_disable', 'row part set_txt_val_disable')
expect_str(0x430765F, 'selected', 'row part selected')
expect_str(0x424EC05, 'scroll', 'scroller part name')
expect_str(0x4452000, 'select_item', 'scroller method select_item')
expect_str(0x4441001, 'get_selected_item', 'scroller method get_selected_item')
expect_str(0x440FDBB, 'get_decided_item', 'scroller method get_decided_item')
expect_str(0x426D4FE, 'redraw_all_items', 'scroller method redraw_all_items')
expect_str(0x439A900, 'ensure_visible', 'scroller method ensure_visible')

# ------------------------------------------------------------ Q1 ctor 1 -------
expect_word(0x19C7854, 0x91268108, 'ctor1 vtable add')
expect_adrp_add(0x19C7854, 0x50A69A0, 'ctor1 vtable 0x50a69a0')
expect_word(0x19C785C, 0xA9007C08, 'ctor1 stores vtable+null at [x0]')
expect_word(0x19C7864, 0xA906201F, 'ctor1 init [x0+0x60..0x70]')
expect_word(0x19C7880, 0x52802E01, 'ctor1 sub-object size immediate (mov w1,#0x170)')
expect_branch(0x19C7890, 0x392DCE0, 'ctor1 op-new for the 0x170-byte sub-object')
expect_adrp_add(0x19C8304, 0x4290580, 'ctor1 get_top_index name')
expect_branch(0x19C8318, 0x3376540, 'ctor1 get_top_index delegate registration call')
expect_branch(0x19C83C0, 0x3376540, 'ctor1 sort_id_list delegate registration call')
expect_adrp_add(0x19C83AC, 0x427F3A7, 'ctor1 sort_id_list name')
expect_adrp_add(0x19C8240, 0x436B678, 'ctor1 "scroller" name')
expect_branch(0x19C8248, 0x3373F00, 'ctor1 scroller setter call')
expect_branch(0x19C846C, 0x3376540, 'ctor1 backup_list_selected_id registration call')
expect_branch(0x19C8510, 0x3376540, 'ctor1 select_list_from_backup_id registration call')
expect_word(0x19C8540, 0x91239821, 'ctor1 SCROLLER_ITEM_NUM add')
expect_adrp_add(0x19C8540, 0x42A18E6, 'ctor1 SCROLLER_ITEM_NUM name')
expect_word(0x19C8538, 0xB940D7E3, 'ctor1 SCROLLER_ITEM_NUM w3 = [sp+0xd4]')
expect_branch(0x19C8550, 0x33750A0, 'ctor1 constant registration call')

# ------------------------------------------------------------ Q1 ctor 2 -------
expect_adrp_add(0x19CEB54, 0x50A6C00, 'ctor2 vtable 0x50a6c00')
expect_word(0x19CEB5C, 0xA9007C08, 'ctor2 stores vtable+null at [x0]')
expect_adrp_add(0x19CF608, 0x4290580, 'ctor2 get_top_index name')
expect_adrp_add(0x19CF6B0, 0x427F3A7, 'ctor2 sort_id_list name')
expect_branch(0x19CF61C, 0x3376540, 'ctor2 get_top_index delegate registration call')
expect_branch(0x19CF6C4, 0x3376540, 'ctor2 sort_id_list delegate registration call')
expect_branch(0x19CF770, 0x3376540, 'ctor2 backup_list_selected_id registration call')
expect_branch(0x19CF814, 0x3376540, 'ctor2 select_list_from_backup_id registration call')
expect_adrp_add(0x19CF544, 0x436B678, 'ctor2 "scroller" name')
expect_branch(0x19CF54C, 0x3373F00, 'ctor2 scroller setter call')
expect_adrp_add(0x19CF844, 0x42A18E6, 'ctor2 SCROLLER_ITEM_NUM name')
expect_branch(0x19CF854, 0x33750A0, 'ctor2 constant registration call')

# ------------------------------------------------------------ Q1 call sites ---
expect_branch(0x1809558, 0x19CEB30, 'editor scene calls ctor2')
expect_branch(0x1809670, 0x19C7830, 'editor scene calls ctor1')
expect_branch(0x1982C68, 0x19CEB30, '0x1982xxx calls ctor2')
expect_branch(0x1982DD4, 0x19C7830, '0x1982xxx calls ctor1')

# ------------------------------------------------------------ Q2 handlers -----
expect_word(0x19C1F00, 0xF81E0FF3, 'get_top_index handler first insn (sp-relative)')
expect_word(0x19C1F0C, 0xB001CB68, 'get_top_index handler 4th insn is adrp (PC-rel)')
expect_word(0x19C1F1C, 0x91090100, 'get_top_index handler add x0, x8, #0x240')
expect_word(0x19C1F20, 0xF9409668, 'get_top_index handler ldr x8,[x19,#0x128]')
expect_word(0x19C1F24, 0xF9400101, 'get_top_index handler ldr x1,[x8]')
expect_branch(0x19C1F28, 0x3286320, 'get_top_index handler calls 0x3286320')
expect_word(0x19C1F30, 0x3945A668, 'get_top_index handler ldrb [x19,#0x169]')

expect_word(0x19C1F50, 0xD101C3FF, 'sort_id_list handler first insn (sub sp,#0x70)')
expect_word(0x19C1F54, 0xA9035FF8, 'sort_id_list handler 2nd insn (no PC-rel)')
expect_word(0x19C1F58, 0xA90457F6, 'sort_id_list handler 3rd insn (no PC-rel)')
expect_word(0x19C1F5C, 0xA9054FF4, 'sort_id_list handler 4th insn (no PC-rel)')
expect_word(0x19C1F6C, 0x7100083F, 'sort handler cmp w1,#2')
expect_branch(0x19C1F70, 0x19C1FC4, 'sort handler mode 2 target')
expect_word(0x19C1F74, 0x7100043F, 'sort handler cmp w1,#1')
expect_word(0x19C1F7C, 0x35000AA1, 'sort handler mode test cbnz w1 (reject >2)')
expect_word(0x19C1F80, 0xB901667F, 'sort handler mode0 -> [x19+0x164] = 0')
expect_word(0x19C1FA4, 0xB9016668, 'sort handler mode1 -> [x19+0x164] = 1')
expect_word(0x19C1F9C, 0x14000115, 'sort handler mode0 tail-b')
expect_branch(0x19C1F9C, 0x19C23F0, 'sort handler mode0 tail target')
expect_branch(0x19C1F78, 0x19C1FA0, 'sort handler mode1 target')

expect_word(0x19C2110, 0xF9407C08, 'backup handler ldr x8,[x0,#0xf8]')
expect_word(0x19C2114, 0xB982A508, 'backup handler ldrsw [x8,#0x2a4]  (scroller selected index)')
expect_word(0x19C2120, 0xA952A809, 'backup handler ldp [x0+0x128] (vector begin/end)')
expect_word(0x19C2160, 0xA9BF7BFD, 'select handler first insn (no PC-rel)')
expect_word(0x19C2168, 0xF940AC09, 'select handler ldr x9,[x0,#0x158] (backed-up handle)')
expect_word(0x19C216C, 0xD2E26008, 'select handler sentinel tag 0x1300000000000000')

expect_word(0x19C7780, 0xF81E0FF3, 'get_top_index thunk first insn')
expect_word(0x19C778C, 0xF9401028, 'thunk ldr x8,[x1,#0x20]')
expect_word(0x19C7794, 0xF9400829, 'thunk ldr x9,[x1,#0x10]  (S-0x10)')

# ------------------------------------------------------------ Q5 count --------
expect_word(0x19C7CF0, 0xF94002E8, 'count: ldr x8,[x23] (vector end)')
expect_word(0x19C7CF4, 0xF9400349, 'count: ldr x9,[x26] (vector begin)')
expect_word(0x19C7CF8, 0xCB090108, 'count: sub x8,x8,x9')
expect_word(0x19C7D00, 0xD343FD08, 'count: lsr x8,x8,#3')
expect_word(0x19C7D04, 0xB900D7E8, 'count: str w8,[sp,#0xd4]')
expect_word(0x19C7D10, 0x91301442, 'scroller ctor call: part name "scroll"')
expect_adrp_add(0x19C7D10, 0x424EC05, 'scroller ctor part name "scroll"')
expect_word(0x19C7A4C, 0xF9009688, 'ctor1 stores vector begin at obj+0x128')
expect_word(0x19C7A54, 0xA9135A88, 'ctor1 stores vector end/cap at obj+0x130')
expect_branch(0x19C7A2C, 0x3276440, 'ctor1 vector filler 0x3276440')
expect_branch(0x19CED28, 0x3274C50, 'ctor2 vector filler 0x3274c50')
expect_branch(0x19C7A70, 0x3286320, 'ctor1 filter call 0x3286320 (table at +0x240)')
expect_word(0x19C7A6C, 0x91090100, 'ctor1 filter table x0 = global+0x240')
expect_branch(0x19CED6C, 0x328B5D0, 'ctor2 filter call 0x328b5d0 (table at +0x230)')
expect_word(0x19CED68, 0x9108C100, 'ctor2 filter table x0 = global+0x230')

# ------------------------------------------------------------ Q6 rows ---------
expect_word(0x19CCB20, 0xD10303FF, 'row fill first insn (sub sp,#0xc0)')
expect_word(0x19CCB3C, 0xA952A809, 'row fill ldp [x0+0x128] (item vector)')
expect_word(0x19CCB4C, 0x9343FD4A, 'row fill count = (end-begin)>>3')
expect_word(0x19CCB58, 0xF8687934, 'row fill ldr x20,[x9,x8,lsl #3]  (item handle)')
expect_word(0x19CCB5C, 0xF940AA68, 'row fill ldr x8,[x19,#0x150] (selected handle)')
expect_adrp_add(0x19CCB98, 0x4306E2F, 'row fill "selecteditem"')
expect_adrp_add(0x19CCBC4, 0x44533D3, 'row fill "notselecteditem"')
expect_word(0x19CCBCC, 0x9476AC61, 'row fill call 0x3777d50 (row mark, s0=1.0)')
expect_word(0x19CCBC8, 0x1E2E1000, 'row fill fmov s0,#1.0')
expect_branch(0x19CCBEC, 0x3288330, 'row fill calls 0x3288330 (nam_mii_hat_%s builder)')
expect_word(0x19CCBE0, 0x910063E0, 'row fill x0 = sp+0x18 (label out)')
expect_word(0x19CCBE4, 0xAA1403E2, 'row fill x2 = item handle')
expect_adrp_add(0x19CCBF4, 0x425E382, 'row fill "set_txt_val"')
expect_branch(0x19CCC00, 0x3776360, 'row fill part lookup 0x3776360')
expect_branch(0x19CCC10, 0x3779B70, 'row fill set text 0x3779b70')
expect_adrp_add(0x19CCC30, 0x436AC1A, 'row fill "set_txt_val_disable"')
expect_adrp_add(0x19CCC60, 0x430765F, 'row fill "selected"')
expect_word(0x19CCCC4, 0x39416109, 'row fill ldrb w9,[x8,#0x58] (mark flags)')
expect_word(0x19CCCC8, 0x121F1929, 'row fill clears mark bit 0 (and #0xfe)')
expect_word(0x19CCCE0, 0x32000129, 'row fill sets mark bit 0 (orr #1)')
expect_word(0x19CCCE4, 0x39016109, 'row fill strb mark flags')
expect_branch(0x19CCD84, 0x328B5D0, 'row fill ownership test 0x328b5d0')
expect_word(0x19CCD7C, 0x9108C100, 'row fill ownership table = global+0x230')
expect_word(0x19CCD8C, 0x3945A668, 'row fill ldrb [x19,#0x169] (mode flag)')
expect_word(0x19CCCE8, 0x321C03E0, 'row fill small alloc w0=0x10')

# hat label builder 0x3288330
expect_word(0x32886EC, 0x900080C0, 'hat label builder adrp (for "nam_mii_hat_%s")')
expect_adrp_add(0x32886F0, 0x42A06FE, 'hat label builder "nam_mii_hat_%s"')
expect_branch(0x32886F8, 0x3A4CA0, 'hat label builder formats via 0x3a4ca0')
expect_word(0x3A4D54, 0xB9000660, '0x3a4ca0 stores length at [x19+4]')
expect_word(0x3A4D7C, 0xB9000275, '0x3a4ca0 stores FNV-style hash at [x19]')

# row-fill virtual thunk
expect_word(0x19CD010, 0xD1012000, 'row-fill thunk: sub x0,x0,#0x48')
expect_branch(0x19CD014, 0x19CCB20, 'row-fill thunk: tail-b 0x19ccb20')

# scroller per-row registration in 0x3781470
expect_word(0x37821A8, 0x97FFCFBA, 'scroller row: bl 0x3776090')
expect_branch(0x37821A8, 0x3776090, 'scroller row: name lookup 0x3776090')
expect_branch(0x3782214, 0x3776360, 'scroller row: part lookup 0x3776360')
expect_word(0x3782264, 0xF9412D08, 'scroller row: vtable slot 0x258 on row object')
expect_word(0x3782278, 0xF900AB68, 'scroller row: [row+0x150] = item data')
expect_word(0x3782284, 0xB901A368, 'scroller row: [row+0x1a0] = row index')
expect_word(0x378228C, 0xF940DD08, 'scroller row: vtable slot 0x1b8 (row refresh)')
expect_word(0x378229C, 0xF900175B, 'scroller row: push row into list at [x21+0x170]')

# ------------------------------------------------------------ Q7 decision -----
expect_reloc_slot(0x5183B40, 0x440FDBB, 'scroller method table: get_decided_item name')
expect_reloc_slot(0x5183B48, 0x3363070, 'scroller method table: get_decided_item handler')
expect_reloc_slot(0x5183B30, 0x4441001, 'scroller method table: get_selected_item name')
expect_reloc_slot(0x5183B38, 0x3362FF0, 'scroller method table: get_selected_item handler')
expect_reloc_slot(0x5183B10, 0x4452000, 'scroller method table: select_item name')
expect_reloc_slot(0x5183B18, 0x3362BA0, 'scroller method table: select_item handler')
expect_reloc_slot(0x5183B50, 0x426D4FE, 'scroller method table: redraw_all_items name')
expect_reloc_slot(0x5183B20, 0x439A900, 'scroller method table: ensure_visible name')
expect_word(0x3363070, 0xF9400808, 'get_decided_item handler first insn')
expect_word(0x33630B4, 0xB982B52A, 'get_decided_item reads vtable slot +0x2b4 (ldrsw)')
expect_word(0x33630C4, 0x52800269, 'get_decided_item pushes Lua integer tag 0x13')
expect_word(0x33630CC, 0xB81F8109, 'get_decided_item writes stack slot')
expect_word(0x3362FF0, 0xF9400808, 'get_selected_item handler first insn')
expect_word(0x3363034, 0xB982A52A, 'get_selected_item reads vtable slot +0x2a4 (ldrsw)')
expect_word(0x377D2BC, 0xB902A408, 'scroller frame: [self+0x2a4] = [self+0x2a0]')
expect_word(0x377D2D0, 0xF9000117, 'scroller frame: [self+0x2b4] = -1 each frame')
expect_word(0x377D2D4, 0x390AF01F, 'scroller frame: [self+0x2bc] = 0')
expect_word(0x377D658, 0xB902B668, 'scroller frame: latches [self+0x2b0] into [self+0x2b4]')
expect_word(0x377D660, 0xB902B277, 'scroller frame: clears [self+0x2b0]')
expect_word(0x377D2C0, 0x910AD008, 'scroller frame: address of [self+0x2b4]')

# ------------------------------------------------------------ Q8 prologues ----
def prologue_has_pc_rel(addr, n=4):
    """True when any of the first n instructions is PC-relative (adrp / adr).

    Only the two PC-relative-immediate encodings are treated as PC-relative.
    Pre-indexed sp stores (stp x28,x27,[sp,#-0x60]!) are PC-*dependent* for a
    code cave but carry no encoded displacement, so they are counted as free.
    """
    a = addr & ~3
    for _ in range(n):
        w = word(a)
        if (w & 0x9F000000) == 0x90000000:          # adrp
            return True
        if (w & 0x1F000001) == 0x10000001:          # adr
            return True
        a += 4
    return False


expect_word(0x19C1F50, 0xD101C3FF, 'hook sort handler entry word 0')
expect_word(0x19C2110, 0xF9407C08, 'hook backup handler entry word 0')
expect_word(0x19C2160, 0xA9BF7BFD, 'hook select handler entry word 0')
expect_word(0x19CCB20, 0xD10303FF, 'hook row-fill entry word 0')
expect_word(0x19C7830, 0xA9BA6FFC, 'hook ctor1 entry word 0 (sp pre-index)')
ok(not prologue_has_pc_rel(0x19C1F50), 'sort handler first 4 insns PC-relative-free')
ok(not prologue_has_pc_rel(0x19C2110), 'backup handler first 4 insns PC-relative-free')
ok(not prologue_has_pc_rel(0x19C2160), 'select handler first 4 insns PC-relative-free')
ok(not prologue_has_pc_rel(0x19CCB20), 'row-fill first 4 insns PC-relative-free')
ok(prologue_has_pc_rel(0x19C1F00), 'get_top_index handler first 4 insns contain an adrp')
ok(not prologue_has_pc_rel(0x19C7830), 'ctor1 first 4 insns carry no PC-relative immediate')

# ------------------------------------------------------------ negative -------
NEGATIVE_CONTROLS = {
    'word': lambda: expect_word(0x19C7D04, 0xDEADBEEF, 'NEG wrong count-store word'),
    'string': lambda: expect_str(0x42A06FE, 'nam_mii_body_%s', 'NEG wrong label format'),
    'reloc': lambda: expect_reloc_slot(0x5183B40, 0x4441001, 'NEG wrong method-table addend'),
    'branch': lambda: expect_branch(0x19CCBEC, 0x19CCB20, 'NEG wrong label-builder call'),
    'size': lambda: ok(len(DATA) != SIZE, 'NEG wrong input size'),
}
if NEG:
    if NEG not in NEGATIVE_CONTROLS:
        sys.stderr.write('unknown --neg %s (known: %s)\n' % (NEG, ', '.join(NEGATIVE_CONTROLS)))
        sys.exit(2)
    NEGATIVE_CONTROLS[NEG]()

print('P8-HAT-NATIVE check: %d claims, %d mismatches' % (checks, len(fails)))
for f in fails:
    print('  MISMATCH: %s' % f)
print('negative-control mode: %s' % (NEG if NEG else 'off'))
sys.exit(1 if fails else 0)
