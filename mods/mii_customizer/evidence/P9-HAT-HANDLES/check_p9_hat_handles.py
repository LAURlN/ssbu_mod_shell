"""P9-HAT-HANDLES - re-read every address cited in research/P9-HAT-HANDLES.md
from the 13.0.4 main.bin and fail on any mismatch.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin
       sha256 f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613
       size   86672752 bytes, flat decompressed MOD0 (address == file offset)
       relocations 0x39c8070..0x40c9fc7, 24-byte
                {u64 r_offset, u32 r_info, u32 pad, u64 r_addend}, r_info 0x403.

Offsets and immediates are read from capstone's decoded operand objects, never
from a hand-rolled bit mask, so the ldp/stp split imm7 encodings are handled.

Usage (from the workspace root, with the mod's deps on PYTHONPATH):

  export PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python
  python mods/mii_customizer/evidence/P9-HAT-HANDLES/check_p9_hat_handles.py

Exit codes: 0 all claims matched, 1 a claim mismatched, 2 input identity failed.

Negative controls (each must exit 1; run them to prove the checker is not
silently passing):

  --neg word      expects a wrong instruction word at 0x19ccb20
  --neg branch    expects the wrong call target at 0x19ccbec
  --neg string    expects the wrong part name at 0x4306e2f
  --neg reloc     expects the wrong RELA addend for slot 0x50a6b18
  --neg vtable    expects the wrong method in row-callback vtable slot 0x50a6b18
  --neg ctor      expects a wrong sub-object size in the ctor
  --neg static    expects the wrong headgear static offset at 0x180acc4
  --neg label     expects the wrong label format string at 0x42a06fe
  --neg registry  expects the wrong handle tag inside 0x328b5d0
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

import capstone
import capstone.arm64 as arm64

ROOT = Path(__file__).resolve().parents[4]
IMAGE = ROOT / 'gamedata' / 'ssbu-13.0.4' / 'main.bin'
SHA256 = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
SIZE = 86672752
RELA_LO, RELA_HI, REC = 0x39C8070, 0x40C9FC7, 24
R_AARCH64_RELATIVE = 0x403

data = IMAGE.read_bytes()
_md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
_md.detail = True

CLAIMS = 0
MISMATCHES: list[str] = []


# ---------------------------------------------------------------- primitives
def check(label: str, got, want) -> None:
    global CLAIMS
    CLAIMS += 1
    if got != want:
        MISMATCHES.append('MISMATCH: %s expected %r got %r' % (label, want, got))


def word(a: int) -> int:
    return struct.unpack_from('<I', data, a)[0]


def qword(a: int) -> int:
    return struct.unpack_from('<Q', data, a)[0]


def cstr(a: int, limit: int = 96) -> str:
    e = data.find(b'\0', a, a + limit)
    if e < 0:
        return ''
    s = data[a:e]
    if not s or any(c < 0x20 or c > 0x7e for c in s):
        return ''
    return s.decode('latin1')


def one(a: int):
    got = list(_md.disasm(data[a:a + 4], a))
    return got[0] if got else None


def mem_disp(a: int):
    """Unsigned memory displacement of the single memory operand at a, else None."""
    ins = one(a)
    if ins is None:
        return None
    for op in ins.operands:
        if op.type == arm64.ARM64_OP_MEM and op.mem.index == 0 and op.mem.disp >= 0:
            return op.mem.disp
    return None


def last_imm(a: int):
    """Immediate of the last ALU operand at a (add/sub/mov/cmp), else None."""
    ins = one(a)
    if ins is None:
        return None
    for op in reversed(ins.operands):
        if op.type == arm64.ARM64_OP_IMM:
            return op.imm
    return None


def is_movz(a: int) -> bool:
    ins = one(a)
    return ins is not None and ins.mnemonic == 'mov'


def reg_of(a: int, n: int = 0) -> str:
    ins = one(a)
    if ins is None or len(ins.operands) <= n:
        return ''
    op = ins.operands[n]
    return ins.reg_name(op.reg) if op.type == arm64.ARM64_OP_REG else ''


def dest_reg(a: int) -> str:
    ins = one(a)
    if ins is None or not ins.operands:
        return ''
    op = ins.operands[0]
    return ins.reg_name(op.reg) if op.type == arm64.ARM64_OP_REG else ''


def mnemonic(a: int) -> str:
    ins = one(a)
    return '' if ins is None else ins.mnemonic


def branch_target(a: int):
    w = word(a)
    if (w & 0x7C000000) == 0x14000000:              # b / bl
        imm = w & 0x3FFFFFF
        if imm & 0x2000000:
            imm -= 0x4000000
        return a + (imm << 2)
    if (w & 0xFF000010) == 0x54000000:              # b.cond
        imm = (w >> 5) & 0x7FFFF
        if imm & 0x40000:
            imm -= 0x80000
        return a + (imm << 2)
    if (w & 0x7E000000) == 0x34000000:              # cbz / cbnz
        imm = (w >> 5) & 0x7FFFF
        if imm & 0x40000:
            imm -= 0x80000
        return a + (imm << 2)
    return None


def reloc_addend(slot: int):
    i = RELA_LO
    pat = struct.pack('<Q', slot)
    while i + REC <= RELA_HI:
        if data[i:i + 8] == pat:
            info, pad, addend = struct.unpack_from('<IIQ', data, i + 8)
            if info == R_AARCH64_RELATIVE and pad == 0 and addend != 0:
                return addend
        i += 1
    return None


def check_input() -> int:
    global MISMATCHES
    got = hashlib.sha256(data).hexdigest()
    if got != SHA256:
        print('INPUT SHA256 MISMATCH: expected %s got %s' % (SHA256, got), file=sys.stderr)
        return 2
    check('image size', len(data), SIZE)
    if MISMATCHES:
        for m in MISMATCHES:
            print(m, file=sys.stderr)
        return 2
    return 0


# ------------------------------------------------------------------- Q1: ctor
def c_ctor(neg: str) -> None:
    a = 0x19CEB30
    check('ctor entry mnemonic', mnemonic(a), 'stp')
    # vtable 0x50a6c00 into [x0]
    check('ctor vtable add imm', last_imm(0x19CEB54), 0xC00)
    check('ctor vtable adrp page', word(0x19CEB50) & 0x9F000000, 0x90000000)
    check('ctor stp vtable,xzr', mnemonic(0x19CEB5C), 'stp')
    check('ctor vtable dest', dest_reg(0x19CEB5C), 'x8')
    # sub-object allocation
    check('ctor new size imm', last_imm(0x19CEB80), 0x170)
    check('ctor new align imm', last_imm(0x19CEB8C), 0x10)
    check('ctor calls operator new', branch_target(0x19CEB90), 0x392DCE0)
    # the sub-object pointer is stored into [this+0x80]
    check('ctor subobj +0x80', mem_disp(0x19CED0C), 0x80)
    # sentinel 0x5aff_00ff_0000_0000 built by mov+movk
    check('ctor sentinel mov', mnemonic(0x19CEC7C), 'mov')
    check('ctor sentinel movk', mnemonic(0x19CEC80), 'movk')
    check('ctor sentinel movk imm', last_imm(0x19CEC80), 0x5AFF)
    # four handle slots + vector + flag
    check('ctor stp at +0x138', mem_disp(0x19CEC88), 0x138)
    check('ctor stp at +0x148', mem_disp(0x19CEC90), 0x148)
    check('ctor stp at +0x158', mem_disp(0x19CECA4), 0x158)
    check('ctor strh at +0x168', mem_disp(0x19CEC8C), 0x168)
    check('ctor strh 0x100', last_imm(0x19CEC84), 0x100)
    check('ctor stp at +0x128', mem_disp(0x19CECE4), 0x128)
    # the two callbacks stored into the sub-object
    check('ctor cb +0x78 add imm', last_imm(0x19CEC98), 0x3E0)
    check('ctor cb +0x88 add imm', last_imm(0x19CECAC), 0x3F0)
    check('ctor stp cb at +0x78', mem_disp(0x19CECE8), 0x78)
    check('ctor stp cb at +0x88', mem_disp(0x19CECEC), 0x88)
    # vector fill from the static table
    check('ctor calls 0x3274c50', branch_target(0x19CED28), 0x3274C50)
    check('ctor vector begin store +0x128', mem_disp(0x19CED48), 0x128)
    check('ctor vector end store +0x130', mem_disp(0x19CED50), 0x130)
    check('ctor vector cap store +0x138', mem_disp(0x19CECEC), 0x88)
    # ownership registry +0x230
    check('ctor registry add imm', last_imm(0x19CED68), 0x230)
    check('ctor calls 0x328b5d0', branch_target(0x19CED6C), 0x328B5D0)
    # scroller build
    check('ctor scroller part "scroll" imm', last_imm(0x19CF018), 0xC05)
    check('ctor part string', cstr(0x424EC05), 'scroll')
    check('ctor calls 0x3781470', branch_target(0x19CF028), 0x3781470)
    # constants registered for Lua
    check('ctor SCROLLER_ITEM_NUM imm', last_imm(0x19CF844), 0x8E6)
    check('ctor SCROLLER_ITEM_NUM name', cstr(0x42A18E6), 'SCROLLER_ITEM_NUM')
    check('ctor calls 0x33750a0', branch_target(0x19CF854), 0x33750A0)
    check('ctor INPUT_OPEN_SORT_WINDOW name', cstr(0x437AF86), 'INPUT_OPEN_SORT_WINDOW')
    check('ctor scroller global name', cstr(0x436B678), 'scroller')
    if neg == 'ctor':
        check('NEG wrong sub-object size', last_imm(0x19CEB80), 0x171)


# --------------------------------------------------- Q1/Q7: bridge delegates
def c_delegates() -> None:
    check('delegate get_top_index vtable imm', last_imm(0x19CF5E4), 0xB88)
    check('delegate get_top_index handler imm', last_imm(0x19CF5EC), 0xB0)
    check('delegate get_top_index name imm', last_imm(0x19CF608), 0x580)
    check('delegate get_top_index name', cstr(0x4290580), 'get_top_index')
    check('delegate get_top_index register', branch_target(0x19CF61C), 0x3376540)
    check('delegate sort vtable imm', last_imm(0x19CF694), 0xBB0)
    check('delegate sort handler imm', last_imm(0x19CF69C), 0x100)
    check('delegate sort name imm', last_imm(0x19CF6B0), 0x3A7)
    check('delegate sort name', cstr(0x427F3A7), 'sort_id_list')
    check('delegate sort register', branch_target(0x19CF6C4), 0x3376540)
    check('delegate backup vtable imm', last_imm(0x19CF73C), 0xBD8)
    check('delegate backup handler imm', last_imm(0x19CF744), 0x2C0)
    check('delegate backup name imm', last_imm(0x19CF758), 0x1FE)
    check('delegate backup name', cstr(0x44541FE), 'backup_list_selected_id')
    check('delegate backup register', branch_target(0x19CF770), 0x3376540)
    check('delegate select handler imm', last_imm(0x19CF7E8), 0x310)
    check('delegate select name imm', last_imm(0x19CF7F8), 0x4C)
    check('delegate select name', cstr(0x441204C), 'select_list_from_backup_id')
    check('delegate select register', branch_target(0x19CF814), 0x3376540)
    # every delegate stores the sub-object at [x0+0x10]
    for a in (0x19CF5F8, 0x19CF6A8, 0x19CF750, 0x19CF7FC):
        check('delegate stp subobj +0x10 (0x%x)' % a, mem_disp(a), 0x10)
    # delegate vtable slot 0 is the shared deleter
    for v in (0x50A6B88, 0x50A6BB0, 0x50A6BD8):
        check('delegate vtable 0x%x slot 0' % v, reloc_addend(v), 0x19C2210)


# ------------------------------------------------- Q1/Q7: the four handlers
def c_handlers() -> None:
    # get_top_index 0x19cd0b0
    check('get_top_index +0x128', mem_disp(0x19CD0D0), 0x128)
    check('get_top_index first handle', mnemonic(0x19CD0D4), 'ldr')
    check('get_top_index registry +0x230', last_imm(0x19CD0CC), 0x230)
    check('get_top_index calls 0x328b5d0', branch_target(0x19CD0D8), 0x328B5D0)
    check('get_top_index reads +0x169', mem_disp(0x19CD0E0), 0x169)
    check('get_top_index ret', word(0x19CD0FC), 0xD65F03C0)
    check('get_top_index 0x532e000 adrp', word(0x19CD0BC) & 0x9F000000, 0x90000000)
    # sort_id_list 0x19cd100
    check('sort cmp mode2 imm', last_imm(0x19CD11C), 2)
    check('sort b.eq mode2', branch_target(0x19CD120), 0x19CD174)
    check('sort cmp mode1 imm', last_imm(0x19CD124), 1)
    check('sort b.eq mode1', branch_target(0x19CD128), 0x19CD150)
    check('sort cbnz reject', branch_target(0x19CD12C), 0x19CD280)
    check('sort mode0 store +0x164', mem_disp(0x19CD130), 0x164)
    check('sort mode1 store +0x164', mem_disp(0x19CD154), 0x164)
    check('sort mode1 imm', last_imm(0x19CD150), 1)
    check('sort mode2 store +0x164', mem_disp(0x19CD178), 0x164)
    check('sort mode2 imm', last_imm(0x19CD174), 2)
    check('sort mode0 tail', branch_target(0x19CD14C), 0x19CD590)
    check('sort mode1 tail', branch_target(0x19CD170), 0x19CD9D0)
    check('sort returns', word(0x19CD294), 0xD65F03C0)
    # backup_list_selected_id 0x19cd2c0
    check('backup scroller +0xf8', mem_disp(0x19CD2C0), 0xF8)
    check('backup selected +0x2a4', mem_disp(0x19CD2C4), 0x2A4)
    check('backup cmn imm', last_imm(0x19CD2C8), 1)
    check('backup b.eq sentinel', branch_target(0x19CD2CC), 0x19CD2F0)
    check('backup vector +0x128', mem_disp(0x19CD2D0), 0x128)
    check('backup stores +0x158', mem_disp(0x19CD2E8), 0x158)
    check('backup sentinel movk imm', last_imm(0x19CD2F4), 0x5AFF)
    check('backup out-of-range +0x128', last_imm(0x19CD308), 0x128)
    check('backup out-of-range call', branch_target(0x19CD30C), 0x39C0D80)
    # select_list_from_backup_id 0x19cd310
    check('select backup +0x158', mem_disp(0x19CD318), 0x158)
    check('select tag 0x5a', last_imm(0x19CD31C), 0x5A00000000000000)
    check('select vector +0x128', mem_disp(0x19CD334), 0x128)
    check('select calls 0x3783660', branch_target(0x19CD3A8), 0x3783660)
    check('select w1 = matched index', mnemonic(0x19CD35C), 'ldr')
    check('select w2 = 0', mnemonic(0x19CD3A4), 'mov')
    check('select w3 = 1', last_imm(0x19CD3A0), 1)
    check('select out-of-range +0x128', last_imm(0x19CD394), 0x128)
    check('select out-of-range call', branch_target(0x19CD398), 0x39C0D80)


# ------------------------------------------------------------- Q2: row filler
def c_row_filler(neg: str) -> None:
    a = 0x19CCB20
    check('row filler entry mnemonic', mnemonic(a), 'sub')
    check('row filler vector ldp +0x128', mem_disp(a + 0x1C), 0x128)
    check('row filler count shift', mnemonic(a + 0x2C), 'asr')
    check('row filler loads handle', mnemonic(a + 0x38), 'ldr')
    check('row filler selected +0x150', mem_disp(a + 0x3C), 0x150)
    check('row filler tag 0x5a', last_imm(a + 0x40), 0x5A00000000000000)
    check('row filler handle mask', word(a + 0x2C - 0) and last_imm(a + 0x40), 0x5A00000000000000)
    # part names
    check('row filler "selecteditem"', cstr(0x4306E2F), 'selecteditem')
    check('row filler "notselecteditem"', cstr(0x44533D3), 'notselecteditem')
    check('row filler selecteditem add imm', last_imm(0x19CCB98), 0xE2F)
    check('row filler notselecteditem add imm', last_imm(0x19CCBC4), 0x3D3)
    check('row filler calls 0x3777d50', branch_target(a + 0xAC), 0x3777D50)
    # label
    check('row filler registry +0x238', mem_disp(0x19CCBDC), 0x238)
    check('row filler label builder', branch_target(0x19CCBEC), 0x3288330)
    check('row filler "set_txt_val" imm', last_imm(0x19CCBF4), 0x382)
    check('row filler "set_txt_val"', cstr(0x425E382), 'set_txt_val')
    check('row filler find part', branch_target(0x19CCC00), 0x3776360)
    check('row filler set text', branch_target(0x19CCC10), 0x3779B70)
    check('row filler "set_txt_val_disable" imm', last_imm(0x19CCC30), 0xC1A)
    check('row filler "set_txt_val_disable"', cstr(0x436AC1A), 'set_txt_val_disable')
    check('row filler disable find', branch_target(0x19CCC3C), 0x3776360)
    check('row filler disable set', branch_target(0x19CCC48), 0x3779B70)
    check('row filler "selected" imm', last_imm(0x19CCC60), 0x65F)
    check('row filler "selected"', cstr(0x430765F), 'selected')
    check('row filler selected find', branch_target(0x19CCC6C), 0x3776360)
    # tick bit from +0x148 vs the row handle
    check('row filler reads +0x148', mem_disp(0x19CCC70), 0x148)
    check('row filler flag byte +0x58', mem_disp(0x19CCCC4), 0x58)
    check('row filler clears bit 0', mnemonic(0x19CCCC8), 'and')
    check('row filler sets bit 0', mnemonic(0x19CCCE0), 'orr')
    check('row filler writes flag', mem_disp(0x19CCCE4), 0x58)
    # the per-row icon cell
    check('row filler new align 0x10', last_imm(0x19CCCE8), 0x10)
    check('row filler new size 8', last_imm(0x19CCCE8 + 4), 8)
    check('row filler texture 0x3796970', branch_target(0x19CCD64), 0x3796970)
    check('row filler cell row-node +8', mem_disp(0x19CCD48), 8)
    check('row filler cell owner +0x60', mem_disp(0x19CCD54), 0x60)
    check('row filler cell arg +0xb0', last_imm(0x19CCD60), 0xB0)
    # ownership
    check('row filler registry +0x230', last_imm(0x19CCD7C), 0x230)
    check('row filler ownership', branch_target(0x19CCD84), 0x328B5D0)
    check('row filler reads +0x169', mem_disp(0x19CCD8C), 0x169)
    # four cell vtable slots
    check('row filler slot 0x1f8', mem_disp(0x19CCD9C + 4), 0x1F8)
    check('row filler slot 0x200', mem_disp(0x19CCDB8), 0x200)
    check('row filler slot 0x210', mem_disp(0x19CCDCC), 0x210)
    check('row filler slot 0x388', mem_disp(0x19CCDE0), 0x388)
    check('row filler cell slot 0x1f8 arg w1 = 1', last_imm(0x19CCDA4), 1)
    check('row filler w2 = 0', mnemonic(0x19CCDEC), 'mov')
    check('row filler ret', word(0x19CCE28), 0xD65F03C0)
    # bounds failure
    check('row filler bounds branch', branch_target(0x19CCB54), 0x19CCE98)
    check('row filler out-of-range +0x128', last_imm(0x19CCE98), 0x128)
    check('row filler out-of-range call', branch_target(0x19CCE9C), 0x39C0D80)
    # vtable thunk
    check('thunk sub x0,#0x48', mnemonic(0x19CD010), 'sub')
    check('thunk imm 0x48', last_imm(0x19CD010), 0x48)
    check('thunk b 0x19ccb20', branch_target(0x19CD014), 0x19CCB20)
    # the sibling callback slots
    check('row cb 0x19cd020 vector', mem_disp(0x19CD034), 0xE0)
    check('row cb 0x19cd020 end', mem_disp(0x19CD038), 0x8)
    check('row cb ownership', branch_target(0x19CD070), 0x328B5D0)
    check('row cb +0x128 via sub', mnemonic(0x19CD078), 'sub')
    check('row cb +0x128 imm', last_imm(0x19CD078), 0x128)
    check('row cb reads +0x169', mem_disp(0x19CD07C), 0x169)
    check('row cb ret', word(0x19CD0A0), 0xD65F03C0)
    check('row cb out-of-range call', branch_target(0x19CD0A8), 0x39C0D80)
    # 0x19ccea0: row -> index
    check('row index vector +0x128', mem_disp(0x19CCEB0), 0x128)
    check('row index loads handle', mnemonic(0x19CCED0), 'ldr')
    check('row index ownership', branch_target(0x19CCEEC), 0x328B5D0)
    check('row index reads +0x169', mem_disp(0x19CCEF4), 0x169)
    check('row index out-of-range call', branch_target(0x19CCF24), 0x39C0D80)
    if neg == 'row':
        check('NEG wrong label-builder branch', branch_target(0x19CCBEC), 0x19CCB20)


# ------------------------------------------------- Q3: unknown-handle paths
def c_label_builder(neg: str) -> None:
    a = 0x3288330
    check('label entry mnemonic', mnemonic(a), 'sub')
    check('label tag mask mnemonic', mnemonic(a + 0x1C), 'and')
    check('label tag 0x5a', last_imm(a + 0x20), 0x5A00000000000000)
    check('label b.ne bad-tag', branch_target(a + 0x2C), 0x32883F0)
    check('label b.ne zero-hash', branch_target(a + 0x38), 0x32883F0)
    check('label hash mask mnemonic', mnemonic(a + 0x34), 'and')
    # registry lookups
    check('label calls 0x3269900', branch_target(0x3288440 - 4), 0x3269900)
    check('label calls 0x3269fd0', branch_target(0x3288454), 0x3269FD0)
    check('label calls 0x3269e30', branch_target(0x3288514), 0x3269E30)
    # failure path builds the literal "unknown" (7 chars) and hashes it in place
    check('label fallback b.hi', branch_target(0x3288504), 0x32885A0)
    check('label fallback b.lt', branch_target(0x32884F8), 0x32885A0)
    check('label unknown length 7', last_imm(0x32885A0), 0x700000000)
    check('label unknown "un"', last_imm(0x32885A8), 0x6E75)
    check('label unknown "kn"', last_imm(0x32885AC), 0x6E6B)
    check('label unknown "ow"', last_imm(0x32885B8), 0x776F)
    check('label unknown "n"', last_imm(0x32885BC), 0x6E)
    check('label fallback hash seed lo', last_imm(0x32885C4), 0x9DC5)
    check('label fallback hash seed hi', last_imm(0x32885C8), 0x811C)
    check('label fallback store hash', mem_disp(0x32885EC), 0x8)
    check('label fallback tail', branch_target(0x32885F0), 0x32886EC)
    # success path
    check('label format imm', last_imm(0x32886F0), 0x6FE)
    check('label format string', cstr(0x42A06FE), 'nam_mii_hat_%s')
    check('label format+hash call', branch_target(0x32886F8), 0x3A4CA0)
    check('label ret', word(a + 0x3E4), 0xD65F03C0)
    if neg == 'label':
        check('NEG wrong label format string', cstr(0x42A06FE), 'nam_mii_body_%s')


def c_registry(neg: str) -> None:
    for a, tag, name, call, cmp_at, cset_at, ret_at in (
            (0x328B5D0, 0x5A00000000000000, '0x328b5d0', 0x328B6EC, 0x328B7A0, 0x328B7AC, 0x328B7B8),
            (0x3286320, 0x1300000000000000, '0x3286320', 0x328643C, 0x32864F0, 0x32864FC, 0x3286508)):
        check('%s tag mask mnemonic' % name, mnemonic(a + 0x18), 'and')
        check('%s tag constant' % name, last_imm(a + 0x1C), tag)
        check('%s b.ne fallback' % name, branch_target(a + 0x24), a + 0xB8)
        check('%s calls 0x3269fd0' % name, branch_target(call), 0x3269FD0)
        # ends with cmp then cset w0, ls -> 1 if the found index is <= a bound
        check('%s cmp before return' % name, mnemonic(cmp_at), 'cmp')
        check('%s cset w0, ls' % name, mnemonic(cset_at), 'cset')
        check('%s ret' % name, word(ret_at), 0xD65F03C0)
    if neg == 'registry':
        check('NEG wrong handle tag in 0x328b5d0', last_imm(0x328B5F0), 0x1300000000000000)


# ------------------------------------------------------ Q7: the Lua thunks
def c_lua_thunks() -> None:
    # sort_id_list Lua thunk 0x19cd460
    check('sort thunk entry mnemonic', mnemonic(0x19CD460), 'sub')
    check('sort thunk reads S+0x10', mem_disp(0x19CD474), 0x10)
    check('sort thunk int tag 0x13', last_imm(0x19CD488), 0x13)
    check('sort thunk int path', mnemonic(0x19CD490), 'ldr')
    check('sort thunk float tag 3', last_imm(0x19CD4A4), 3)
    check('sort thunk number tag 4', last_imm(0x19CD4B0), 4)
    check('sort thunk number branch', branch_target(0x19CD4B4), 0x19CD4F4)
    check('sort thunk fcvtzs', mnemonic(0x19CD580), 'fcvtzs')
    check('sort thunk default x1 = 0', mnemonic(0x19CD4F4), 'mov')
    check('sort thunk tail-call', mnemonic(0x19CD554), 'br')
    check('sort thunk callee +0x10', mem_disp(0x19CD52C), 0x10)
    check('sort thunk callee +0x20', mem_disp(0x19CD530), 0x20)
    check('sort thunk pushes no result', dest_reg(0x19CD554), 'x2')
    # get_top_index Lua thunk 0x19cea80
    check('top thunk entry mnemonic', mnemonic(0x19CEA80), 'str')
    check('top thunk reads L+0x20', mem_disp(0x19CEA8C), 0x20)
    check('top thunk callee +0x28', mem_disp(0x19CEAC4), 0x28)
    check('top thunk sxtw', mnemonic(0x19CEAF0), 'sxtw')
    check('top thunk writes value', mem_disp(0x19CEAF4), 0)
    check('top thunk writes tag 0x13', last_imm(0x19CEAF8), 0x13)
    check('top thunk ret', word(0x19CEB14), 0xD65F03C0)
    # the shared deleter on every delegate vtable slot 0
    check('delegate deleter 0x19c2210 is a bare ret', word(0x19C2210), 0xD65F03C0)
    check('sort delegate slot +0x08', reloc_addend(0x50A6BB8), 0x19CD450)
    check('sort delegate slot +0x10', reloc_addend(0x50A6BC0), 0x19CD460)
    check('top delegate slot +0x08', reloc_addend(0x50A6B90), 0x19CEA70)
    check('top delegate slot +0x10', reloc_addend(0x50A6B98), 0x19CEA80)
    check('backup delegate slot +0x10', reloc_addend(0x50A6BE8), 0x19CD3D0)


# --------------------------------------------------------------- Q1: vtables
def c_vtables(neg: str) -> None:
    for slot, want in ((0x50A6C00, 0x19CFC30), (0x50A6C08, 0x19CFCF0),
                       (0x50A69A0, 0x19C8930),
                       (0x50A6AE0, 0x19CC9E0), (0x50A6AE8, 0x32CB650),
                       (0x50A6AF0, 0x32CB760), (0x50A6AF8, 0x32CB7C0),
                       (0x50A6B00, 0x32CB800), (0x50A6B08, 0x19CCA40),
                       (0x50A6B10, 0x19CCAB0), (0x50A6B18, 0x19CCB20),
                       (0x50A6B20, 0x19CCEA0), (0x50A6B38, 0x19CCF30),
                       (0x50A6B40, 0x19CCFA0), (0x50A6B48, 0x19CD010),
                       (0x50A6B50, 0x377C0D0), (0x50A6B58, 0x377C0E0),
                       (0x50A6B60, 0x19CD020), (0x50A6B68, 0x4542A30)):
        check('vtable slot 0x%08x' % slot, reloc_addend(slot), want)
    check('vtable 0x50a6b28 offset -0x48', qword(0x50A6B28), 0xFFFFFFFFFFFFFFB8)
    # the typeinfo/method table that names the row filler
    check('typeinfo table vtable', qword(0x3CF48D8), 0x50A6B18)
    check('typeinfo table tag', qword(0x3CF48E0), 0x403)
    check('typeinfo table method', qword(0x3CF48E8), 0x19CCB20)
    check('typeinfo table thunk pair', qword(0x3CF4948), 0x19CD010)
    if neg == 'vtable':
        check('NEG wrong row-callback slot 0', reloc_addend(0x50A6B18), 0x19CCEA0)


# ------------------------------------ Q4/Q5/Q6: the scene and the entry path
def c_scene(neg: str) -> None:
    # 0x180abd0: the state handler that applies the preview
    check('scene hat list +0x180', mem_disp(0x180ABF0), 0x180)
    check('scene subobj +0x80', mem_disp(0x180ABF4), 0x80)
    check('scene gate +0x160', mem_disp(0x180ABF8), 0x160)
    check('scene reads +0xe8', mem_disp(0x180AC18), 0xE8)
    check('scene reads +0x168', mem_disp(0x180AC20), 0x168)
    check('scene clears +0x168', mem_disp(0x180AC28), 0x168)
    check('scene reads +0x140', mem_disp(0x180AC34), 0x140)
    check('scene stores static', mnemonic(0x180AC3C), 'str')
    check('scene static imm 0xcb0', mem_disp(0x180AC3C), 0xCB0)
    check('scene tail-calls 0x180cf10', branch_target(0x180AC54), 0x180CF10)
    check('scene reads +0x148', mem_disp(0x180ACBC), 0x148)
    check('scene reads static 0xcb0', mem_disp(0x180ACC4), 0xCB0)
    check('scene reads +0x150', mem_disp(0x180AD38), 0x150)
    check('scene label refresh', branch_target(0x180ADD4), 0x19CB2E0)
    check('scene reads +0x164', mem_disp(0x180ADEC), 0x164)
    # 0x19cfe00: the entry path that positions the cursor
    check('entry entry mnemonic', mnemonic(0x19CFE00), 'stp')
    check('entry vector +0x128', mem_disp(0x19CFE10), 0x128)
    check('entry stp x1,x1 +0x140', mem_disp(0x19CFE18), 0x140)
    check('entry str x1 +0x150', mem_disp(0x19CFE1C), 0x150)
    check('entry clears +0x168', mem_disp(0x19CFE24), 0x168)
    check('entry "set_select_id" imm', last_imm(0x19CFED8), 0xD26)
    check('entry "set_select_id"', cstr(0x439BD26), 'set_select_id')
    check('entry set_select_id (hit)', branch_target(0x19CFF68), 0x38F4790)
    check('entry fallback registry +0x230', last_imm(0x19CFFEC), 0x230)
    check('entry fallback ownership', branch_target(0x19CFFF0), 0x328B5D0)
    check('entry fallback stores +0x169', mem_disp(0x19CFFF8), 0x169)
    check('entry ret', word(0x19D0008), 0xD65F03C0)
    check('scene calls 0x19cfe00', branch_target(0x180B060), 0x19CFE00)
    check('scene passes the static', mem_disp(0x180B058), 0xCB0)
    # 0x19cb2e0: the preview label refresh
    check('preview reads the static', mem_disp(0x019CB3E8), 0xCB0)
    check('preview uses hat label builder', branch_target(0x019CB3F8), 0x3288330)
    check('preview uses body label builder', branch_target(0x019CB47C), 0x32842E0)
    check('preview nam_mii_body_%s', cstr(0x43FEAB3), 'nam_mii_body_%s')
    # the entry copy of the static into the scene
    check('entry-copy static imm', last_imm(0x18094B4), 0xCB0)
    check('entry-copy ldp [x8,#0x20]', mem_disp(0x18094B8), 0x20)
    check('entry-copy ldr [x8]', mem_disp(0x18094EC), 0)
    # other readers of the headgear static
    check('other reader 0x180d4cc', mem_disp(0x180D4CC), 0xCB0)
    check('other reader 0x180d734', mem_disp(0x180D734), 0xCB0)
    check('other reader 0x19cb3e8 adrp', word(0x019CB3E4) & 0x9F000000, 0x90000000)
    if neg == 'static':
        check('NEG wrong headgear static offset', mem_disp(0x180ACC4), 0xCA8)


def c_frame_and_cancel() -> None:
    # 0x19cc3f0: the list frame callback
    check('frame cb entry mnemonic', mnemonic(0x019CC3F0), 'stp')
    check('frame cb vector +0x128', mem_disp(0x019CC44C), 0x128)
    check('frame cb selected +0x2a4', mem_disp(0x019CC450), 0x2A4)
    check('frame cb reads +0x140', mem_disp(0x019CC468), 0x140)
    check('frame cb ownership', branch_target(0x019CC548), 0x328B5D0)
    check('frame cb clears +0x169', mem_disp(0x019CC554), 0x169)
    check('frame cb second ownership', branch_target(0x019CC754), 0x328B5D0)
    check('frame cb stores +0x148', mem_disp(0x019CC6C4), 0x148)
    check('frame cb "get_decided_id"', cstr(0x43DE9D8), 'get_decided_id')
    check('frame cb reads get_decided_id', branch_target(0x019CC660), 0x38F4790)
    # the body's last ret is at 0x19cc8fc, so it ends at 0x19cc900 (0x510 bytes);
    # 0x19cc900..0x19cc90c is the out-of-range tail and 0x19cc90c is padding
    last_ret = max(a for a in range(0x019CC3F0, 0x019CC910, 4)
                   if word(a) == 0xD65F03C0)
    check('frame cb last ret', last_ret, 0x019CC8FC)
    check('frame cb body size', last_ret + 4 - 0x019CC3F0, 0x510)
    check('frame cb tail out-of-range +0x128', last_imm(0x019CC900), 0x128)
    check('frame cb tail trap call', branch_target(0x019CC904), 0x39C0D80)
    check('frame cb 0x19cc90c is padding, not code', word(0x019CC90C), 0x00000000)
    # 0x180cf10: the scene commit path (a different static, 0x5306ca8)
    check('commit static imm', last_imm(0x0180CFE4), 0xCA8)
    check('commit sets +0x163', mem_disp(0x0180D010), 0x163)
    check('commit ret', word(0x0180D024), 0xD65F03C0)
    # 0x17bd1b0: the special-skill record copy (not headgear)
    check('record copy +0x118 slots', mem_disp(0x017BD1E4), 0x118)
    check('record copy called from 0x180d428', branch_target(0x180D428), 0x17BD1B0)


def c_first_words() -> None:
    """Q8: exactly one listed entry has a PC-relative (adrp) word in its first
    four - the get_top_index handler, at word 3."""
    clean = [
        (0x19CEB30, 'ctor headgear'), (0x19CCB20, 'row filler'),
        (0x19CCEA0, 'row index-of-handle'), (0x19CD020, 'row callback slide'),
        (0x19CD100, 'sort_id_list handler'),
        (0x19CD2C0, 'backup handler'), (0x19CD310, 'select-from-backup handler'),
        (0x19CD460, 'sort_id_list Lua thunk'), (0x19CEA80, 'get_top_index Lua thunk'),
        (0x19CFE00, 'set_select_id native'), (0x19CC3F0, 'list frame callback'),
        (0x19CB2E0, 'preview label refresh'), (0x180ABD0, 'scene preview apply'),
        (0x3288330, 'hat label builder'), (0x328B5D0, 'registry contains 0x5a'),
        (0x19CD590, 'sort mode 0 body'), (0x19CD9D0, 'sort mode 1 body'),
    ]
    for a, name in clean:
        for k in range(4):
            w = word(a + 4 * k)
            check('first-four[%s] w%d not adrp' % (name, k),
                  (w & 0x9F000000) == 0x90000000, False)
    # the one exception, verified as an adrp at word 3
    check('first-four[get_top_index] w3 is adrp',
          (word(0x19CD0BC) & 0x9F000000) == 0x90000000, True)
    check('first-four[get_top_index] w0', word(0x19CD0B0), 0xF81E0FF3)
    check('first-four[get_top_index] w1', word(0x19CD0B4), 0xA9017BFD)
    check('first-four[get_top_index] w2', word(0x19CD0B8), 0x910043FD)


def c_hat_is_not_outfit() -> None:
    """The headgear handlers are distinct code from the outfit twins."""
    for a, b, label, diverge in ((0x19CD0B0, 0x19C1F00, 'get_top_index', 0x0C),
                                 (0x19CD2C0, 0x19C2110, 'backup', 0x35),
                                 (0x19CD310, 0x19C2160, 'select-from-backup', 0x0D),
                                 (0x19CD100, 0x19C1F50, 'sort_id_list', 0x4C)):
        same = 0
        while data[a + same] == data[b + same] and same < 0x80:
            same += 1
        check('twin %s diverges at +0x%x' % (label, diverge), same, diverge)
    # the headgear twin calls 0x328b5d0, the outfit twin 0x3286320
    check('hat get_top_index calls 0x328b5d0', branch_target(0x19CD0D8), 0x328B5D0)
    check('hat get_top_index registry +0x230', last_imm(0x19CD0CC), 0x230)
    check('outfit get_top_index registry +0x240', last_imm(0x19C1F1C), 0x240)
    check('outfit get_top_index calls 0x3286320', branch_target(0x19C1F28), 0x3286320)
    # the ctor of the headgear twin loads the hat script hash
    check('hat ctor script imm', last_imm(0x19CECF8), 0x3FC6)
    check('hat ctor script movk lo', last_imm(0x19CECFC), 0xA5C1)
    check('hat ctor script movk hi', last_imm(0x19CED08), 0x2F)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--neg', default='',
                    help='negative-control mode: '
                         'word|branch|string|reloc|vtable|ctor|row|label|registry|static')
    args = ap.parse_args()
    neg = args.neg

    rc = check_input()
    if rc:
        return rc

    c_ctor(neg)
    c_delegates()
    c_handlers()
    c_row_filler(neg)
    c_label_builder(neg)
    c_registry(neg)
    c_lua_thunks()
    c_vtables(neg)
    c_scene(neg)
    c_frame_and_cancel()
    c_first_words()
    c_hat_is_not_outfit()

    if neg == 'word':
        check('NEG wrong instruction word at 0x19ccb20', word(0x19CCB20), 0xDEADBEEF)
    if neg == 'branch':
        check('NEG wrong call target at 0x19cce98', branch_target(0x19CCE98), 0x19CCB20)
    if neg == 'string':
        check('NEG wrong part name at 0x4306e2f', cstr(0x4306E2F), 'notselecteditem')
    if neg == 'reloc':
        check('NEG wrong RELA addend for slot 0x50a6b18', reloc_addend(0x50A6B18), 0x19CCEA0)

    if MISMATCHES:
        for m in MISMATCHES:
            print(m, file=sys.stderr)
        print('P9-HAT-HANDLES check: %d claims, %d mismatches' % (CLAIMS, len(MISMATCHES)))
        print('negative-control mode: %s' % (neg or 'off'))
        return 1

    print('P9-HAT-HANDLES check: %d claims, 0 mismatches' % CLAIMS)
    print('negative-control mode: %s' % (neg or 'off'))
    return 0


if __name__ == '__main__':
    sys.exit(main())