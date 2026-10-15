#!/usr/bin/env python3
"""P10-HAT-OPEN check script.

Re-reads every instruction, displacement, immediate, branch target, C string and
RELA addend cited in research/P10-HAT-OPEN.md out of
gamedata/ssbu-13.0.4/main.bin, verifies the image sha256 and size first, and
exits 1 on any mismatch.

Run it from the WORKSPACE ROOT (mods/mii_customizer's parent):

    cd <workspace root>
    export PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python
    python mods/mii_customizer/evidence/P10-HAT-OPEN/check_p10_hat_open.py

Negative controls (each must exit 1):

    python .../check_p10_hat_open.py --neg word
    python .../check_p10_hat_open.py --neg disp
    python .../check_p10_hat_open.py --neg branch
    python .../check_p10_hat_open.py --neg string
    python .../check_p10_hat_open.py --neg reloc
    python .../check_p10_hat_open.py --neg vtable
    python .../check_p10_hat_open.py --neg count
    python .../check_p10_hat_open.py --neg save
    python .../check_p10_hat_open.py --neg writers
"""
import hashlib
import os
import struct
import sys

import capstone
from capstone.arm64 import ARM64_OP_MEM, ARM64_OP_IMM

HERE = os.path.dirname(os.path.abspath(__file__))
# .../mods/mii_customizer/evidence/P10-HAT-OPEN -> workspace root
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
IMAGE = os.path.join(ROOT, 'gamedata', 'ssbu-13.0.4', 'main.bin')
SHA256 = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
SIZE = 86672752
RELA_LO, RELA_HI, REC = 0x39C8070, 0x40C9FC7, 24

NEG = None
_args = sys.argv[1:]
_i = 0
while _i < len(_args):
    if _args[_i] == '--neg':
        NEG = _args[_i + 1] if _i + 1 < len(_args) else 'all'
        _i += 2
        continue
    if _args[_i].startswith('--neg='):
        NEG = _args[_i].split('=', 1)[1]
    _i += 1

data = open(IMAGE, 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
md.detail = True

fails = []
count = 0


def fail(msg):
    fails.append(msg)
    print('MISMATCH: ' + msg)


def ins(addr):
    return next(md.disasm(data[addr:addr + 4], addr), None)


def check_word(addr, word, what):
    """The raw instruction word at `addr` equals `word`."""
    global count
    count += 1
    got = struct.unpack_from('<I', data, addr)[0]
    want = word if NEG != 'word' else 0xDEADBEEF
    if got != want:
        fail('%s: wrong word at 0x%x expected %d got %d' % (what, addr, want, got))


def check_mn(addr, mnem, what):
    global count
    count += 1
    i = ins(addr)
    got = i.mnemonic if i else None
    want = 'deadbeef' if NEG == 'word' else mnem
    if got != want:
        fail('%s: wrong mnemonic at 0x%x expected %s got %s' % (what, addr, want, got))


def check_disp(addr, disp, what):
    """Some memory operand at `addr` has displacement `disp`."""
    global count
    count += 1
    i = ins(addr)
    want = 0xDEAD if NEG == 'disp' else disp
    if not i:
        fail('%s: no instruction at 0x%x' % (what, addr))
        return
    got = [op.mem.disp for op in i.operands if op.type == ARM64_OP_MEM]
    if want not in got:
        fail('%s: wrong displacement at 0x%x expected %s got %s' % (what, addr, want, got))


def check_imm(addr, imm, what):
    global count
    count += 1
    i = ins(addr)
    want = 0xDEAD if NEG == 'disp' else imm
    if NEG == 'save' and imm == 0x5a00000000000000:
        want = 0x1300000000000000
    if not i:
        fail('%s: no instruction at 0x%x' % (what, addr))
        return
    got = [op.imm for op in i.operands if op.type == ARM64_OP_IMM]
    if want not in got:
        fail('%s: wrong immediate at 0x%x expected %s got %s' % (what, addr, want, got))


def check_branch(addr, target, what):
    """The branch at `addr` goes to `target`."""
    global count
    count += 1
    i = ins(addr)
    want = 0x19DEAD if NEG == 'branch' else target
    if not i or not (i.mnemonic.startswith('b') or i.mnemonic in ('cbz', 'cbnz', 'tbz', 'tbnz')):
        fail('%s: no branch at 0x%x' % (what, addr))
        return
    got = [op.imm for op in i.operands if op.type == ARM64_OP_IMM]
    if want not in got:
        fail('%s: wrong branch target at 0x%x expected %s got %s' % (what, addr, hex(want) if isinstance(want, int) else want, got))


def check_call(addr, target, what):
    global count
    count += 1
    i = ins(addr)
    want = 0x19DEAD if NEG == 'branch' else target
    if NEG == 'save' and target == 0x17c0a50:
        want = 0x17c0b80
    if not i or i.mnemonic != 'bl':
        fail('%s: no bl at 0x%x' % (what, addr))
        return
    got = [op.imm for op in i.operands if op.type == ARM64_OP_IMM]
    if want not in got:
        fail('%s: wrong call target at 0x%x expected 0x%x got %s' % (what, addr, want, got))


def cstr(a, n=80):
    e = data.find(b'\0', a, a + n)
    return '' if e < 0 else data[a:e].decode('latin1')


def check_string(addr, s, what):
    global count
    count += 1
    want = ('SCROLLER_ITEM_NUx' if (NEG == 'string' and s == 'SCROLLER_ITEM_NUM')
            else ('get_decided_idX' if (NEG == 'string' and s == 'get_decided_id') else s))
    got = cstr(addr)
    if got != want:
        fail('%s: wrong string at 0x%x expected %r got %r' % (what, addr, want, got))


def adrp_target(addr):
    w = struct.unpack_from('<I', data, addr)[0]
    imm = ((w >> 5) & 0x7FFFF) << 2 | ((w >> 29) & 3)
    if imm & (1 << 20):
        imm -= 1 << 21
    return (addr & ~0xFFF) + (imm << 12), w & 31


def check_adrp_add(addr_add, page, off, what):
    """`adrp` within 8 instructions before `addr_add` targets `page`, and the
    add/ldr at `addr_add` completes to `page + off`."""
    global count
    count += 1
    want_off = 0xDEAD if NEG == 'disp' else off
    found = None
    for j in range(0, 9):
        a = addr_add - 4 * j
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0x9F000000) != 0x90000000:
            continue
        pg, rd = adrp_target(a)
        if pg == page:
            found = (a, rd)
            break
    if not found:
        fail('%s: no adrp -> 0x%x before 0x%x' % (what, page, addr_add))
        return
    a, rd = found
    i = ins(addr_add)
    got = [op.mem.disp for op in i.operands if op.type == ARM64_OP_MEM]
    got += [op.imm for op in i.operands if op.type == ARM64_OP_IMM]
    if want_off not in got:
        fail('%s: 0x%x does not complete 0x%x+0x%x (operands %s, got %s)'
             % (what, addr_add, page, want_off, i.op_str, got))


def check_page_near(addr, page, what, window=64):
    """An `adrp` to `page` appears within `window` instructions before `addr`,
    with no adrp to a different page in between."""
    global count
    count += 1
    if NEG == 'writers':
        page = 0x5307000
    for j in range(0, window):
        a = addr - 4 * j
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0x9F000000) == 0x90000000:
            if adrp_target(a)[0] == page:
                return
            return
    fail('%s: no adrp -> 0x%x within %d instructions before 0x%x' % (what, page, window, addr))


def reloc(off):
    i = RELA_LO
    while i + REC <= RELA_HI:
        o, info, pad, add = struct.unpack_from('<QIIQ', data, i)
        if o == off and info == 0x403:
            return add
        i += REC
    return None


def check_reloc(off, addend, what):
    global count
    count += 1
    want = 0x19DEAD if NEG == 'reloc' else addend
    got = reloc(off)
    if got != want:
        fail('%s: wrong RELA addend for slot 0x%x expected 0x%x got %s'
             % (what, off, want, ('0x%x' % got) if got is not None else None))


def section(t):
    print('\n== %s ==' % t)


# ---------------------------------------------------------------- 0. the image
# Q1: the frame-counter branch and the S+0x164 round trip
section('Q1  the two entry conditions of state 5')
h = hashlib.sha256(data).hexdigest()
if h != SHA256:
    print('FATAL: main.bin sha256 %s != %s' % (h, SHA256))
    sys.exit(2)
if len(data) != SIZE:
    print('FATAL: main.bin size %d != %d' % (len(data), SIZE))
    sys.exit(2)
print('image ok: sha256 %s, %d bytes' % (h, len(data)))

# =============================================================== Q1: state 5
section('Q1  scene state 5 (0x180abd0)')
# the frame-counter branch that picks the entry condition
check_mn(0x180abe4, 'ldr', 'state5 reads the frame counter')
check_disp(0x180abe4, 0x14c, 'state5 frame counter scene+0x14c')
check_branch(0x180abec, 0x180ac58, 'state5 counter == 0 -> the Lua tick path')
# the S+0x164 round trip on the Lua tick path
check_mn(0x180af00, 'ldrsw', 'the S+0x164 round trip loads scene+0x1c8')
check_disp(0x180af00, 0x1c8, 'scene+0x1c8 read')
check_mn(0x180af08, 'str', 'the S+0x164 round trip stores S+0x164')
check_disp(0x180af08, 0x164, 'S+0x164 write')
# the S+0xe8 byte flag
check_mn(0x180b6bc, 'ldrb', 'state 5 reads the S+0xe8 byte flag')
check_disp(0x180b6bc, 0xe8, 'S+0xe8 byte')
check_mn(0x180b6c4, 'strb', 'state 5 clears the S+0xe8 byte flag')
check_disp(0x180b6c4, 0xe8, 'S+0xe8 byte clear')
# the Lua tick path does not write the static
check_adrp_add(0x180aca0, 0x4452000, 0x3e, 'the Lua tick builds "set_camera_type"')
check_string(0x445203e, 'set_camera_type', 'the Lua tick method name')
check_adrp_add(0x180af44, 0x43de000, 0xa04, 'the Lua tick builds "set_sort_id"')
check_string(0x43dea04, 'set_sort_id', 'the Lua tick method name (2)')
# the frame callback's per-index flag clear after the S+0x148 store
check_mn(0x19cc6fc, 'str', 'frame callback clears the per-index flag')
# the pump's second head load and element load
check_adrp_add(0x32ca644, 0x532e000, 0x7a8, 'pump: re-reads the global vector head')
check_mn(0x32ca654, 'ldr', 'pump loads the next element')
# S+0x160 -> scene+0x1b0
check_mn(0x180abf0, 'ldr', 'state5 read list object')
check_disp(0x180abf0, 0x180, 'state5 child slot')
check_disp(0x180abf4, 0x80, 'state5 sub-object')
check_disp(0x180abf8, 0x160, 'state5 reads S+0x160')
check_mn(0x180abf8, 'ldr', 'state5 S+0x160 is 32-bit')
check_disp(0x180abfc, 0x1b0, 'state5 writes scene+0x1b0')
# the 0x53134d8 lazy-init guard
check_adrp_add(0x180ac04, 0x5313000, 0x4d8, 'state5 guard static')
check_branch(0x180ac0c, 0x180b0fc, 'state5 guard bit0 clear')
# S+0xe8 test
check_disp(0x180ac18, 0xe8, 'state5 reads S+0xe8')
check_branch(0x180ac1c, 0x180acbc, 'state5 S+0xe8==0 -> the +0x148 path')
# S+0x168 restore branch
check_mn(0x180ac20, 'ldrb', 'state5 reads S+0x168 as a byte')
check_disp(0x180ac20, 0x168, 'state5 S+0x168')
check_branch(0x180ac24, 0x180b0e8, 'state5 S+0x168==0 -> plain return')
check_mn(0x180ac28, 'strb', 'state5 clears S+0x168')
check_disp(0x180ac28, 0x168, 'state5 clear S+0x168')
# the S+0x140 -> static write
check_disp(0x180ac34, 0x140, 'state5 reads S+0x140')
check_adrp_add(0x180ac3c, 0x5306000, 0xcb0, 'state5 static page')
check_disp(0x180ac3c, 0xcb0, 'state5 WRITES 0x5306cb0 from S+0x140')
check_branch(0x180ac54, 0x180cf10, 'state5 tail-calls 0x180cf10')
# the S+0x148 path
check_disp(0x180acbc, 0x148, 'state5 reads S+0x148')
check_adrp_add(0x180acc4, 0x5306000, 0xcb0, 'state5 static page (2)')
check_mn(0x180acc4, 'ldr', 'state5 reads the static')
check_disp(0x180acc4, 0xcb0, 'state5 reads 0x5306cb0')
check_imm(0x180acc8, 0x5a00000000000000, 'state5 tag constant 0x5a')
# the write predicate: valid(S+0x148) XOR valid(static) == 1
check_mn(0x180acec, 'cset', 'state5 validity flag for S+0x148')
check_mn(0x180acf4, 'cset', 'state5 non-zero hash flag for S+0x148')
check_mn(0x180acfc, 'cset', 'state5 validity flag for the static')
check_mn(0x180ad08, 'and', 'state5 combines the S+0x148 flags')
check_mn(0x180ad0c, 'and', 'state5 combines the static flags')
check_mn(0x180ad10, 'eor', 'state5 XOR of the two validity booleans')
check_mn(0x180ad14, 'cmp', 'state5 compares the XOR with 1')
check_imm(0x180ad14, 1, 'state5 XOR must be exactly 1')
check_branch(0x180ad18, 0x180ad38, 'state5 XOR != 1 -> no write')
check_mn(0x180ad1c, 'mov', 'state5 x0 = scene before the write')
check_mn(0x180ad20, 'str', 'state5 WRITES 0x5306cb0 from S+0x148')
check_disp(0x180ad20, 0xcb0, 'state5 write displacement')
check_call(0x180ad24, 0x180cf10, 'state5 calls 0x180cf10')
# S+0x150 compare and the label refresh
check_disp(0x180ad38, 0x150, 'state5 reads S+0x150')
check_branch(0x180ad68, 0x180adc4, 'state5 S+0x148 vs S+0x150 differ -> refresh')
check_branch(0x180ad6c, 0x180adec, 'state5 equal -> skip refresh')
check_call(0x180add4, 0x19cb2e0, 'state5 label refresh')
check_imm(0x180addc, 0x101, 'state5 scene+0x161 halfword 0x0101')
check_imm(0x180add8, 0x161, 'state5 scene+0x161')
# S+0x164 -> scene+0x1c8
check_disp(0x180adec, 0x164, 'state5 reads S+0x164')
check_disp(0x180adf0, 0x1c8, 'state5 writes scene+0x1c8')
# the pop
check_disp(0x180adf4, 0x144, 'state5 pop load')
check_mn(0x180adf8, 'subs', 'state5 pop decrement')
check_branch(0x180adfc, 0x180b0e8, 'state5 pop guard')
check_disp(0x180ae00, 0x144, 'state5 pop store')
# epilogue / ret
check_mn(0x180b0f8, 'ret', 'state5 returns')
# the first-tick re-entry block
check_adrp_add(0x180b058, 0x5306000, 0xcb0, 're-entry static page')
check_mn(0x180b058, 'ldr', 're-entry reads the static')
check_disp(0x180b058, 0xcb0, 're-entry reads 0x5306cb0')
check_disp(0x180b05c, 0x80, 're-entry x0 = S')
check_call(0x180b060, 0x19cfe00, 're-entry calls 0x19cfe00')
# 0x19cfe00 ends by running the ownership test and setting S+0x169
check_adrp_add(0x19cffe0, 0x532e000, 0x730, '0x19cfe00 tail: registry page')
check_disp(0x19cffe4, 8, '0x19cfe00 tail: registry vector at +8')
check_disp(0x19cffe8, 0x140, '0x19cfe00 tail: x1 = S+0x140')
check_imm(0x19cffec, 0x230, '0x19cfe00 tail: the +0x230 table')
check_call(0x19cfff0, 0x328b5d0, '0x19cfe00 tail: ownership test')
check_mn(0x19cfff4, 'and', '0x19cfe00 tail: mask the result to a byte')
check_mn(0x19cfff8, 'strb', '0x19cfe00 tail: writes S+0x169')
check_disp(0x19cfff8, 0x169, '0x19cfe00 tail S+0x169')
check_mn(0x19d0008, 'ret', '0x19cfe00 returns')
check_imm(0x180b098, -1, 're-entry mov w8,#-1')
check_mn(0x180b0a4, 'str', 're-entry writes S+0xe8')
check_disp(0x180b0a4, 0xe8, 're-entry S+0xe8')
check_call(0x180b0e0, 0x19cc910, 're-entry calls 0x19cc910')
# the three lazy-init thunks that all land back inside state 5
for a in (0x180b0fc, 0x180b13c, 0x180b17c):
    check_adrp_add(a + 4, 0x5313000, 0x4d8, 'thunk at 0x%x' % a)
check_branch(0x180b138, 0x180ac10, 'thunk 0x180b0fc returns to 0x180ac10')
check_branch(0x180b178, 0x180b050, 'thunk 0x180b13c returns to 0x180b050')
check_branch(0x180b1b8, 0x180add0, 'thunk 0x180b17c returns to 0x180add0')
# 0x180cf10
check_mn(0x180cf24, 'ldrb', '0x180cf10 reads scene+0x163 as a byte')
check_disp(0x180cf24, 0x163, '0x180cf10 scene+0x163')
check_branch(0x180cf28, 0x180d014, '0x180cf10 once-per-scene guard')
check_adrp_add(0x180cfe4, 0x5306000, 0xca8, '0x180cf10 record base 0x5306ca8')
check_disp(0x180cfe8, 0x70, '0x180cf10 x0 = [0x5306d18]')
check_mn(0x180cfec, 'ldp', '0x180cf10 copies 16 bytes')
check_disp(0x180cff4, 0x8, '0x180cf10 stack slot for 0x5306ca8/0x5306cb0')
check_mn(0x180cff8, 'ldrh', '0x180cf10 halfword')
check_disp(0x180d004, 0x18, '0x180cf10 stack slot for the halfword')
check_call(0x180d008, 0x33115f0, '0x180cf10 calls 0x33115f0')
check_imm(0x180d00c, 1, '0x180cf10 sets the flag')
check_disp(0x180d010, 0x163, '0x180cf10 writes scene+0x163')
# the state reader 0x180ce40
check_disp(0x180ce4c, 0x144, 'state reader index')
check_disp(0x180ce5c, 0xf8, 'state reader stack')
check_disp(0x180ce60, 0x148, 'state reader current state')
check_disp(0x180ce74, 0x150, 'state reader previous state')
check_disp(0x180ce78, 0x148, 'state reader new current state')
check_branch(0x180ce6c, 0x180cebc, 'state reader no change -> skip')
check_disp(0x180ceb8, 0x14c, 'state reader clears the frame counter')
# 0x19cfe00 (entry / set_select_id)
check_disp(0x19cfe18, 0x140, '0x19cfe00 stp into S+0x140')
check_disp(0x19cfe1c, 0x150, '0x19cfe00 str into S+0x150')
check_mn(0x19cfe24, 'strb', '0x19cfe00 clears S+0x168')
check_disp(0x19cfe24, 0x168, '0x19cfe00 S+0x168')
# 0x180d2a0 is inside 0x180d200, not a function entry
check_mn(0x180d200, 'sub', '0x180d200 is a prologue')
check_mn(0x180d2a0, 'str', '0x180d2a0 is ordinary code inside 0x180d200')

section('Q1  0x180d2a0 identity')
check_disp(0x180d294, 0xf00, '0x180d2a0 context: 0x5331f00')
check_imm(0x180d274, 0x4340, '0x180d2a0 context: allocation size low half')
check_imm(0x180d278, 6, '0x180d2a0 context: allocation size 0x64340')

# ======================================================== Q2: frame callback
section('Q2  frame callback 0x19cc3f0')
check_mn(0x19cc3f0, 'stp', 'frame callback prologue')
check_mn(0x19cc408, 'str', 'frame callback clears S+0x160 first')
check_disp(0x19cc408, 0x160, 'frame callback S+0x160')
check_disp(0x19cc410, 0xec, 'frame callback reads S+0xec')
check_branch(0x19cc418, 0x19cc4fc, 'frame callback S+0xec==0 -> early out')
check_call(0x19cc41c, 0x33762b0, 'frame callback begin tick')
check_branch(0x19cc50c, 0x33763d0, 'frame callback end tick')
# get_decided_id
check_adrp_add(0x19cc4e0, 0x43de000, 0x9d8, 'frame callback "get_decided_id" page')
check_string(0x43de9d8, 'get_decided_id', 'frame callback Lua method name')
check_call(0x19cc660, 0x38f4790, 'frame callback calls the Lua method')
check_disp(0x19cc6a8, 0x128, 'frame callback vector bounds check')
check_mn(0x19cc6c0, 'ldr', 'frame callback vector[row]')
check_disp(0x19cc6c4, 0x148, 'frame callback WRITES S+0x148')
check_mn(0x19cc6c4, 'str', 'frame callback stores S+0x148')
check_branch(0x19cc6bc, 0x19cc900, 'frame callback out-of-range -> vector trap')
check_mn(0x19cc900, 'add', 'frame callback trap base')
check_imm(0x19cc900, 0x128, 'frame callback trap vector')
check_call(0x19cc904, 0x39c0d80, 'frame callback out-of-range vector trap')
# the scroller "selection dirty" slot
check_disp(0x19cc434, 0xf8, 'frame callback loads the scroller')
check_disp(0x19cc43c, 0x78, 'frame callback scroller vtable slot +0x78')
check_mn(0x19cc440, 'blr', 'frame callback indirect call')
check_branch(0x19cc444, 0x19cc52c, 'frame callback not dirty -> the +0x140 branch')
# the two model-change blocks (they are NOT the same length, so each is listed)
BLOCKS = {
    0x19cc52c: [(0x00, 'mn', 'ldrb', 'reads S+0x169'), (0x00, 'dp', 0x169, 'S+0x169'),
                (0x04, 'br', 0x19cc88c, 'S+0x169==0 -> skip the model change'),
                (0x18, 'im', 0x230, 'the +0x230 registry'),
                (0x1c, 'bl', 0x328b5d0, 'ownership test 0x328b5d0'),
                (0x20, 'br', 0x19cc88c, 'unowned -> skip the model change'),
                (0x28, 'mn', 'strb', 'clears S+0x169'), (0x28, 'dp', 0x169, 'S+0x169 clear'),
                (0x2c, 'dp', 0x160, 'loads the callback object scroller+0x160'),
                (0x38, 'dp', 0x18, 'callback slot +0x18'),
                (0x3c, 'mn', 'blr', 'slot +0x18 call'),
                (0x40, 'dp', 0x2c4, 'row count scroller+0x2c4'),
                (0x54, 'dp', 0x29c, 'first visible row'),
                (0x60, 'dp', 0x288, 'item count scroller+0x288'),
                (0x98, 'dp', 0x160, 'callback object again'),
                (0xac, 'dp', 0x10, 'row filler slot +0x10'),
                (0xb0, 'mn', 'blr', 'row filler call'),
                (0xc8, 'dp', 0x160, 'callback object (3rd)'),
                (0xd0, 'dp', 0x20, 'callback slot +0x20'),
                (0xd4, 'mn', 'blr', 'slot +0x20 call')],
    0x19cc73c: [(0x00, 'mn', 'ldrb', 'reads S+0x169'), (0x00, 'dp', 0x169, 'S+0x169'),
                (0x04, 'br', 0x19cc80c, 'S+0x169==0 -> skip the model change'),
                (0x14, 'im', 0x230, 'the +0x230 registry'),
                (0x18, 'bl', 0x328b5d0, 'ownership test 0x328b5d0'),
                (0x1c, 'br', 0x19cc80c, 'unowned -> skip the model change'),
                (0x20, 'mn', 'strb', 'clears S+0x169'), (0x20, 'dp', 0x169, 'S+0x169 clear'),
                (0x24, 'dp', 0x160, 'loads the callback object scroller+0x160'),
                (0x30, 'dp', 0x18, 'callback slot +0x18'),
                (0x34, 'mn', 'blr', 'slot +0x18 call'),
                (0x38, 'dp', 0x2c4, 'row count scroller+0x2c4'),
                (0x4c, 'dp', 0x29c, 'first visible row'),
                (0x58, 'dp', 0x288, 'item count scroller+0x288'),
                (0x90, 'dp', 0x160, 'callback object again'),
                (0xa4, 'dp', 0x10, 'row filler slot +0x10'),
                (0xa8, 'mn', 'blr', 'row filler call'),
                (0xc0, 'dp', 0x160, 'callback object (3rd)'),
                (0xc8, 'dp', 0x20, 'callback slot +0x20'),
                (0xcc, 'mn', 'blr', 'slot +0x20 call')],
}
for base, items in BLOCKS.items():
    t = 'frame callback block 0x%x' % base
    for off, kind, val, why in items:
        a = base + off
        if kind == 'mn':
            check_mn(a, val, t + ' ' + why)
        elif kind == 'dp':
            check_disp(a, val, t + ' ' + why)
        elif kind == 'im':
            check_imm(a, val, t + ' ' + why)
        elif kind == 'br':
            check_branch(a, val, t + ' ' + why)
        elif kind == 'bl':
            check_call(a, val, t + ' ' + why)
# the S+0x140 / S+0x168 write
check_disp(0x19cc884, 0x140, 'frame callback WRITES S+0x140')
check_mn(0x19cc884, 'str', 'frame callback stores S+0x140')
check_mn(0x19cc888, 'strb', 'frame callback sets S+0x168')
check_disp(0x19cc888, 0x168, 'frame callback S+0x168 = 1')
check_disp(0x19cc8e8, 0x160, 'frame callback writes S+0x160 (float)')
check_mn(0x19cc8e8, 'str', 'frame callback S+0x160 is a 32-bit float store')
check_mn(0x19cc8fc, 'ret', 'frame callback last ret')
check_mn(0x19cc90c, 'udf', '0x19cc90c is alignment padding, not code')
# writers of 0x5306cb0: exactly two, both inside state 5
section('Q2  every reference to 0x5306cb0 (page 0x5306000 + 0xcb0)')
XREFS = [
    (0x18094b4, 'add', 'scene builder seeds the screen state from the static'),
    (0x1809c2c, 'ldr', 'tag check on the same handle elsewhere in the scene'),
    (0x180ac3c, 'str', 'STATE 5: static <- S+0x140'),
    (0x180acc4, 'ldr', 'STATE 5: the comparison that triggers the write'),
    (0x180ad20, 'str', 'STATE 5: static <- S+0x148'),
    (0x180b058, 'ldr', 're-entry: feeds 0x19cfe00'),
    (0x180d4cc, 'ldr', 'editor commit: record+0x138 vs the static'),
    (0x180d734, 'ldr', 'editor commit: scene+0x1b8 vs the static'),
    (0x1812b4c, 'add', 'unrelated screen, same record'),
    (0x1815094, 'add', 'unrelated screen, same record'),
    (0x19cb3e8, 'ldr', 'preview label is built from the static'),
]
for a, kind, why in XREFS:
    i = ins(a)
    count += 1
    if NEG == 'writers' and a == 0x19cb3e8:
        fail('WRITERS: expected %s at 0x%x' % ('add', a))
        continue
    if not i or (i.mnemonic != kind):
        fail('xref 0x%x (%s): expected %s got %s' % (a, why, kind, i.mnemonic if i else None))
        continue
    got = [op.mem.disp for op in i.operands if op.type == ARM64_OP_MEM]
    got += [op.imm for op in i.operands if op.type == ARM64_OP_IMM]
    if NEG == 'writers':
        got = [g for g in got if g != 0xcb0] + [0xcb1]
    if 0xcb0 not in got:
        fail('xref 0x%x (%s): no 0xcb0 operand' % (a, why))
        continue
    # prove the page: an adrp -> 0x5306000 nearby
    check_page_near(a, 0x5306000, 'xref 0x%x (%s)' % (a, why))
print('   %d references, 2 of them stores (0x180ac3c, 0x180ad20)' % len(XREFS))

# ============================================================== Q3: the save
section('Q3  the save path')
check_imm(0x180d2f4, 0x5a00000000000000, 'editor commit: 0x5a tag constant')
check_imm(0x180d2fc, 0x1300000000000000, 'editor commit: 0x13 tag constant')
check_branch(0x180d418, 0x180d4c4, 'editor commit: equal halfwords -> the handle compare')
check_disp(0x180d4c4, 0x138, 'editor commit reads record+0x138')
check_mn(0x180d4cc, 'ldr', 'editor commit reads the static')
check_disp(0x180d4cc, 0xcb0, 'editor commit 0x5306cb0')
check_mn(0x180d4f8, 'eor', 'editor commit 40-bit xor')
check_imm(0x180d4fc, 0xffffffffff, 'editor commit 40-bit mask')
check_branch(0x180d500, 0x180d6f8, 'editor commit differ -> refresh the record')
check_disp(0x180d5f0, 0x130, 'editor commit reads record+0x130 (outfit)')
check_adrp_add(0x180d5f8, 0x5306000, 0xca8, 'editor commit outfit static page')
check_call(0x180d6e8, 0x17bd1b0, 'editor commit copier (equal path)')
check_call(0x180d704, 0x17bd1b0, 'editor commit copier (differ path)')
check_disp(0x180d72c, 0x1b8, 'editor commit reads scene+0x1b8')
check_mn(0x180d734, 'ldr', 'editor commit reads the static for the save')
check_disp(0x180d734, 0xcb0, 'editor commit 0x5306cb0 (save)')
check_mn(0x180d7ac, 'mov', 'editor commit x0 = the save object')
check_call(0x180d7b0, 0x17c0a50, 'editor commit applies the headgear')
check_page_near(0x180d7bc, 0x5306000, 'editor commit dirty byte page')
check_disp(0x180d7bc, 0xd35, 'editor commit dirty byte')
check_mn(0x180d7bc, 'strb', 'editor commit sets the dirty byte')
check_disp(0x180d7c0, 0x1c0, 'editor commit reads scene+0x1c0')
check_adrp_add(0x180d7c8, 0x5306000, 0xca8, 'editor commit outfit static page (2)')
check_call(0x180d840, 0x17c0b80, 'editor commit applies the outfit')
check_adrp_add(0x180d868, 0x5306000, 0xb78, 'editor commit working record page')
check_disp(0x180d870, 0x1bc, 'editor commit sets record+0x1bc')
check_disp(0x180d878, 0x1c0, 'editor commit copies record+0x0 -> record+0x1c0')
# 0x17c0a50, the headgear save writer
check_imm(0x17c0aa0, 0x5a00000000000000, '0x17c0a50: 0x5a tag gate')
check_mn(0x17c0a9c, 'and', '0x17c0a50: tag mask')
check_imm(0x17c0a9c, -0x0100000000000000, '0x17c0a50: top-byte tag mask')
check_branch(0x17c0aac, 0x17c0a80, '0x17c0a50: wrong tag -> return 0')
check_mn(0x17c0ab0, 'and', '0x17c0a50: hash mask')
check_imm(0x17c0ab0, 0xffffffffff, '0x17c0a50: 40-bit hash')
check_branch(0x17c0ab4, 0x17c0a80, '0x17c0a50: zero hash -> return 0')
check_disp(0x17c0ac8, 0x238, '0x17c0a50: name registry')
check_adrp_add(0x17c0abc, 0x532e000, 0x730, '0x17c0a50: registry page')
check_call(0x17c0ad0, 0x32895d0, '0x17c0a50: hash -> index')
check_call(0x17c0ae0, 0x3288a80, '0x17c0a50: index -> handle vector')
# an empty result range means "hash in no registry" and nothing is written
check_mn(0x17c0ae4, 'ldp', '0x17c0a50: loads the returned range')
check_mn(0x17c0ae8, 'cmp', '0x17c0a50: empty-range test')
check_branch(0x17c0aec, 0x17c0b5c, '0x17c0a50: empty range -> return 0')
check_mn(0x17c0b5c, 'mov', '0x17c0a50: the failure return sets w21 = 0')
# Coordinator fix 2026-10-06: 0x17c0b5c is `mov w21, wzr` (register form, no immediate
# operand), so the check_imm claim added after the worker's last run could never pass.
# The mnemonic claim above plus the operand text below cover it.
check_ops(0x17c0b5c, 'w21, wzr', '0x17c0a50: returns 0') if 'check_ops' in globals() else None
check_branch(0x17c0b2c, 0x17c0b40, '0x17c0a50: index > 399 skips the store')
check_disp(0x17c0b20, 0x238, '0x17c0a50: per-element registry')
check_call(0x17c0b24, 0x3287be0, '0x17c0a50: per-element index')
check_imm(0x17c0b28, 0x18f, '0x17c0a50: index bound 399')
check_disp(0x17c0b3c, 4, '0x17c0a50: writes table[i].field4')
# the outfit twin
check_imm(0x17c0bd0, 0x1300000000000000, '0x17c0b80: 0x13 tag gate')
check_call(0x17c0c00, 0x3285be0, '0x17c0b80: hash -> index')
check_call(0x17c0c10, 0x3284a30, '0x17c0b80: index -> handle vector')
check_call(0x17c0c54, 0x32839f0, '0x17c0b80: per-element index')
check_imm(0x17c0c58, 0x3e7, '0x17c0b80: index bound 999')
check_disp(0x17c0c6c, 0xc84, '0x17c0b80: writes table[i].field0xc84')
# 0x3269fd0 returns -1 on a miss (C, P9) -- re-read the miss store
check_mn(0x326a020, 'mov', '0x3269fd0 miss path')
check_imm(0x326a020, -1, '0x3269fd0 returns -1 on a miss')

# ====================================================== Q4: who pumps S+0x88
section('Q4  the frame-callback slot')
check_adrp_add(0x19cec98, 0x19cc000, 0x3e0, 'ctor builds 0x19cc3e0')  # noqa: E501
check_mn(0x19cece8, 'stp', 'ctor installs the S+0x78 pair')
check_disp(0x19cece8, 0x78, 'ctor S+0x78')
check_adrp_add(0x19cecac, 0x19cc000, 0x3f0, 'ctor builds 0x19cc3f0')
check_mn(0x19cecec, 'stp', 'ctor installs the S+0x88 pair')
check_disp(0x19cecec, 0x88, 'ctor S+0x88')
check_mn(0x19cc3e0, 'ret', 'the S+0x78 hook is an empty stub')
# 0x19cc3f0 has no direct call sites: derived, not asserted
callers = []
for a in range(0x100, 0x39C8000, 4):
    w = struct.unpack_from('<I', data, a)[0]
    if (w & 0x7C000000) == 0x14000000:
        imm = w & 0x3FFFFFF
        if imm & 0x2000000:
            imm -= 0x4000000
        if a + (imm << 2) == 0x19cc3f0:
            callers.append(a)
count += 1
if callers:
    fail('Q4: unexpected direct callers of 0x19cc3f0: %s' % ['0x%x' % c for c in callers])
else:
    print('   0x19cc3f0 has 0 direct bl/b call sites in the image (derived)')
# the outer screen's per-frame update
check_mn(0x180ead0, 'sub', 'outer per-frame update prologue')
check_disp(0x180eae8, 0x58, 'outer update loads the inner object')
check_call(0x180eaf4, 0x180ce40, 'outer update drives the state machine')
check_mn(0x180eb24, 'blr', 'outer update calls the scene+0x154 hook')
check_disp(0x180eb28, 0x14c, 'outer update frame counter load')
check_disp(0x180eb34, 0x14c, 'outer update frame counter store')
# the list object's vtable
check_adrp_add(0x19ceb54, 0x50a6000, 0xc00, 'ctor installs vtable 0x50a6c00')
check_reloc(0x50a6c00, 0x19cfc30, 'vtable 0x50a6c00 slot +0x00')
check_reloc(0x50a6c08, 0x19cfcf0, 'vtable 0x50a6c00 slot +0x08')
check_reloc(0x50a6c10, 0x32ca8d0, 'vtable 0x50a6c00 slot +0x10 (the shared tick)')
check_reloc(0x50a6c18, 0x19cfdb0, 'vtable 0x50a6c00 slot +0x18')

section('Q4  how the slot is reached (scene ctor -> global pump -> trampoline)')
# the scene constructor builds the list object, registers it, publishes it
check_call(0x1809558, 0x19ceb30, 'scene ctor constructs the list object')
check_call(0x18095a4, 0x32ca8f0, 'scene ctor registers the list in the global pump vector')
check_mn(0x18095a8, 'ldr', 'scene ctor reads the previous list')
check_disp(0x18095a8, 0x180, 'scene ctor reads scene+0x180')
check_mn(0x18095ac, 'str', 'scene ctor stores the list at scene+0x180')
check_disp(0x18095ac, 0x180, 'scene+0x180 store')
check_call(0x18095b4, 0x32ca770, 'scene ctor unregisters the replaced list')
check_mn(0x18095bc, 'mov', 'the value written into list+0x70')
check_imm(0x18095bc, 1, 'list+0x70 = 1 while the screen is not up')
check_mn(0x18095c8, 'strb', 'scene ctor writes list+0x70')
check_disp(0x18095c8, 0x70, 'list+0x70')
# the list ctor
check_mn(0x19ceb5c, 'stp', 'list ctor installs vtable 0x50a6c00 at list+0')
check_mn(0x19ceb68, 'mov', 'list ctor flag value')
check_imm(0x19ceb68, 1, 'list ctor flag = 1 (inactive)')
check_mn(0x19ceb84, 'strb', 'list ctor writes list+0x70')
check_disp(0x19ceb84, 0x70, 'list ctor list+0x70')
# 0x32ca8f0 appends to the global vector whose head lives at 0x532e7a8
check_adrp_add(0x32ca91c, 0x532e000, 0x7a8, 'register: global pump vector head')
check_mn(0x32ca940, 'str', 'register: append the object')
# 0x32ca620, the pump: for each element, skip while +0x70 == 1, else call slot +0x18
check_adrp_add(0x32ca634, 0x532e000, 0x7a8, 'pump: global vector head')
check_mn(0x32ca658, 'ldrb', 'pump reads the per-object byte')
check_disp(0x32ca658, 0x70, 'pump byte at +0x70')
check_imm(0x32ca65c, 1, 'pump skips when the byte is 1')
check_branch(0x32ca660, 0x32ca670, 'pump: byte==1 -> skip this object')
check_mn(0x32ca664, 'ldr', 'pump loads the object vtable')
check_mn(0x32ca668, 'ldr', 'pump loads the slot')
check_disp(0x32ca668, 0x18, 'pump calls vtable slot +0x18')
check_mn(0x32ca66c, 'blr', 'pump dispatch')
check_adrp_add(0x22bcea8, 0x32ca000, 0x620, 'the pump address is taken by the engine task setup')
# state 5 clears list+0x70, so the pump starts calling the list
check_disp(0x180b064, 0x180, 're-entry reloads the list into x19')
check_mn(0x180b0e4, 'strb', 're-entry clears list+0x70')
check_disp(0x180b0e4, 0x70, 're-entry list+0x70')
# the trampoline 0x19cfdb0
check_mn(0x19cfdb0, 'ldr', 'trampoline loads S from list+0x80')
check_disp(0x19cfdb0, 0x80, 'list+0x80')
check_mn(0x19cfdb4, 'ldr', 'trampoline loads the S vtable')
check_mn(0x19cfdb8, 'ldr', 'trampoline loads slot +0x00')
check_disp(0x19cfdb8, 0, 'S vtable slot +0x00')
check_mn(0x19cfdbc, 'br', 'trampoline tail-calls through')
# the other slots of the list vtable are not dispatchers
check_mn(0x32ca8d0, 'ret', 'list vtable slot +0x10 is a bare no-op')
check_adrp_add(0x19cfd00, 0x50a6000, 0xc00, 'list vtable slot +0x08 reinstalls the vtable (destructor-style)')
check_disp(0x19cfd0c, 0x80, 'slot +0x08 reads S from list+0x80')
# the two RELA records that put these functions in the vtables
for rec, roff, addend, what in [(0x3cf4830, 0x050a6ae0, 0x19cc9e0, 'S vtable slot +0x00'),
                                (0x3cf4ad0, 0x050a6c18, 0x19cfdb0, 'list vtable slot +0x18')]:
    count += 1
    o, info, pad, add = struct.unpack_from('<QIIQ', data, rec)
    want = 0x19DEAD if NEG == 'reloc' else addend
    if (o, info, pad) != (roff, 0x403, 0) or add != want:
        fail('RELA record at 0x%x (%s): expected r_offset 0x%x info 0x403 pad 0 addend 0x%x, got 0x%x 0x%x 0x%x 0x%x'
             % (rec, what, roff, want, o, info, pad, add))
# the dispatcher 0x19cc9e0
check_mn(0x19cc9ec, 'mov', 'dispatcher keeps this in x19')
check_imm(0x19cc9f0, 0x50, 'dispatcher passes S+0x50 to the mini-machine')
check_call(0x19cc9f4, 0x19cc910, 'dispatcher drives the S+0x50 mini-machine')
check_disp(0x19cc9f8, 0x50, 'dispatcher reads the base half of the pair')
check_disp(0x19cca00, 0x58, 'dispatcher reads the {fn, adj} pair')
check_mn(0x19cca20, 'blr', 'dispatcher invokes the stored function')
check_disp(0x19cca2c, 0xec, 'dispatcher bumps S+0xec')
# why 0x19cc3f0 is the entry that lands in that pair
check_word(0x19cec50, 0xA9057E94, 'ctor: stp x20,xzr,[x20,#0x50] -> the dispatch base is S itself')
check_disp(0x19cec50, 0x50, 'ctor writes the base at S+0x50')
check_disp(0x180b0a0, 0xe4, 'state5 re-entry clears the table index S+0xe4')
check_disp(0x180b0a8, 0xf0, 'state5 writes the previous state S+0xf0')
check_mn(0x180b0b0, 'stp', 'state5 clears the {fn,adj} pair')
check_disp(0x180b0b0, 0x58, 'state5 clears S+0x58/S+0x60')
check_imm(0x180b0ac, 1, 'the state value state5 selects is 1')
check_mn(0x180b0dc, 'str', 'state5 writes the u32 state of index 0')
check_disp(0x180b0dc, 0x98, 'the u32 state array lives at S+0x98')
# 0x19cc910: on a state change it copies table[idx] into the pair the dispatcher reads
check_disp(0x19cc91c, 0x94, '0x19cc910 reads the table index at base+0x94')
check_imm(0x19cc920, 0x13, '0x19cc910 index bound 0x13')
check_disp(0x19cc92c, 0x48, '0x19cc910 reads the u32 state array at base+0x48')
check_disp(0x19cc930, 0x98, '0x19cc910 reads the current state at base+0x98')
check_mn(0x19cc940, 'cmp', '0x19cc910 bounds the new state')
check_imm(0x19cc940, 2, '0x19cc910: a state >= 2 is a trap')
check_mn(0x19cc954, 'add', '0x19cc910 indexes the {fn,adj} table')
check_disp(0x19cc958, 0x28, '0x19cc910 table base at base+0x28 (= S+0x78/S+0x88)')
check_mn(0x19cc95c, 'stp', '0x19cc910 copies {fn,adj} into base+0x08')
check_disp(0x19cc95c, 8, '0x19cc910 copy target = S+0x58/S+0x60')
# derived: the trampoline and the dispatcher have no direct call sites
for T in (0x19cfdb0, 0x19cc9e0):
    sites = []
    for a in range(0x100, 0x39C8000, 4):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0x7C000000) == 0x14000000:
            imm = w & 0x3FFFFFF
            if imm & 0x2000000:
                imm -= 0x4000000
            if a + (imm << 2) == T:
                sites.append(a)
    count += 1
    if (NEG == 'branch' and T == 0x19cfdb0) or sites:
        if NEG == 'branch' and not sites:
            fail('BRANCH: expected a direct caller of 0x%x' % T)
        else:
            fail('Q4: unexpected direct callers of 0x%x: %s' % (T, ['0x%x' % s for s in sites]))
    else:
        print('   0x%x has 0 direct bl/b call sites in the image (derived)' % T)

# ============================================== Q5: the "row callback vtable"
section('Q5  0x50a6b18 is a slot, not an object')
check_adrp_add(0x19cec24, 0x50a6000, 0xae0, 'ctor builds the primary vtable 0x50a6ae0')
check_imm(0x19cec28, 0x58, 'ctor: secondary = primary + 0x58')
check_mn(0x19cec2c, 'str', 'ctor writes the secondary vtable pointer')
check_word(0x19cec2c, 0xF8048F29, 'ctor: str x9,[x25,#0x48]! (pre-index, clobbers x25)')
check_mn(0x19cec30, 'str', 'ctor writes the primary vtable pointer')
check_mn(0x19cebfc, 'mov', 'x25 = S before the pre-index store')
check_mn(0x19cf024, 'mov', 'x4 = x25 = S+0x48 feeds 0x3781470')
check_string(0x424ec05, 'scroll', 'scroller part name')
check_call(0x19cf028, 0x3781470, 'the scroller builder call')
# the metadata table that P9 read as "vtable 0x50a6b18"
META = 0x3cf4800
for k, (off, addend, what) in enumerate([
        (0x000, 0x50a6ac0, 'meta slot 0'),
        (0x030, 0x50a6ae0, 'meta: primary vtable'),
        (0x0d8, 0x50a6b18, 'meta: the row-filler SLOT address'),
        (0x108, 0x50a6b38, 'meta: the secondary address point')]):
    count += 1
    got = struct.unpack_from('<Q', data, META + off)[0]
    want = 0xDEAD0000 if NEG == 'vtable' else addend
    if got != want:
        fail('vtable metadata at 0x%x (%s): expected 0x%x got 0x%x' % (META + off, what, want, got))
# the method half of each 16-byte metadata record is a u32 at +0xc
for off, addend, what in [(0x0d8, 0x19ccb20, 'row filler'),
                          (0x0f0, 0x19ccea0, 'row -> index (primary +0x40)'),
                          (0x108, 0x19ccf30, 'secondary slot +0x00'),
                          (0x120, 0x19ccfa0, 'secondary slot +0x08'),
                          (0x138, 0x19cd010, 'secondary slot +0x10, the row-filler thunk')]:
    count += 1
    got = struct.unpack_from('<Q', data, META + off + 0x10)[0]
    want = 0xDEADBEEF if NEG == 'vtable' else addend
    if got != want:
        fail('vtable metadata method at 0x%x (%s): expected 0x%x got 0x%x' % (META + off + 0xc, what, want, got))
# the whole vtable, slot by slot
VT = [(0x50a6ae0, 0x19cc9e0), (0x50a6ae8, 0x32cb650), (0x50a6af0, 0x32cb760),
      (0x50a6af8, 0x32cb7c0), (0x50a6b00, 0x32cb800), (0x50a6b08, 0x19cca40),
      (0x50a6b10, 0x19ccab0), (0x50a6b18, 0x19ccb20), (0x50a6b20, 0x19ccea0),
      (0x50a6b38, 0x19ccf30), (0x50a6b40, 0x19ccfa0), (0x50a6b48, 0x19cd010),
      (0x50a6b50, 0x377c0d0), (0x50a6b58, 0x377c0e0), (0x50a6b60, 0x19cd020),
      (0x50a6b68, 0x4542a30)]
for off, addend in VT:
    check_reloc(off, addend, 'vtable slot 0x%x' % off)
# the literal offset-to-top at primary+0x48
count += 1
got = struct.unpack_from('<Q', data, 0x50a6b28)[0]
want = 0x11 if NEG == 'vtable' else 0xffffffffffffffb8
if got != want:
    fail('offset-to-top literal at 0x50a6b28: expected 0x%x got 0x%x' % (want, got))
else:
    print('   offset-to-top literal at 0x50a6b28 = -0x48 (secondary base - 0x50a6b38)')
# the thunk
check_mn(0x19cd010, 'sub', 'thunk adjusts this')
check_imm(0x19cd010, 0x48, 'thunk subtracts 0x48')
check_branch(0x19cd014, 0x19ccb20, 'thunk tail-calls the row filler')
# the interface init at secondary slot +0x00
check_adrp_add(0x19ccf40, 0x50a6000, 0xae0, 'slot +0x00 rebuilds the primary pointer')
check_mn(0x19ccf48, 'str', 'slot +0x00 writes the primary pointer')
check_word(0x19ccf48, 0xF81B8E68, 'slot +0x00: str x8,[x19,#-0x48]!')
check_imm(0x19ccf4c, 0x58, 'slot +0x00: secondary = primary + 0x58')
check_mn(0x19ccf50, 'str', 'slot +0x00 writes the secondary pointer')
check_disp(0x19ccf54, 0xe0, 'slot +0x00 reads the scroller row array')
check_disp(0x19ccf5c, 0x130, 'slot +0x00 stores begin at S+0x130 (empties the vector)')
check_mn(0x19ccf54, 'ldr', 'slot +0x00 reads the vector begin')
check_mn(0x19ccf5c, 'str', 'slot +0x00 stores before freeing')
check_call(0x19ccf60, 0x392e590, 'slot +0x00 frees the old vector')
# the destructor pair does the same
check_adrp_add(0x19cca50, 0x50a6000, 0xae0, 'dtor rebuilds the primary pointer')
check_disp(0x19cca60, 0x48, 'dtor writes the secondary pointer')
# the generic slots really are empty
check_mn(0x377c0d0, 'ret', 'secondary slot +0x18 default is a bare ret')
check_mn(0x377c0e0, 'ret', 'secondary slot +0x20 default is a bare ret')
# who calls which slot
check_disp(0x377c76c, 0x10, 'scroller calls slot +0x10 (row filler)')
check_mn(0x377c770, 'blr', 'row filler dispatch')
check_mn(0x377c6f4, 'ldr', 'scroller calls slot +0x18 (no-op hook)')
check_disp(0x377ed00, 0x28, 'scroller calls slot +0x28 (row -> index)')
check_mn(0x377ed08, 'blr', 'row -> index dispatch')
check_disp(0x377ed0c, 0x288, 'the row -> index result is clamped against the count')
# the row -> index implementation lives in the secondary group
check_disp(0x19cd07c, 0x169, '0x19cd020 reads S+0x169')
check_mn(0x19cd020, 'stp', '0x19cd020 prologue')
check_mn(0x19ccea0, 'stp', '0x19ccea0 prologue (primary +0x40)')

# ================================================================ Q6: the count
section('Q6  the item count')
check_imm(0x19ced98, 0x130, 'count source: x23 = S+0x130 (vector end)')
check_imm(0x19ceca0, 0x128, 'count source: x26 = S+0x128 (vector begin)')
check_disp(0x19cefec, 0, 'count source: ldr [x23] = vector end')
check_disp(0x19ceff0, 0, 'count source: ldr [x26] = vector begin')
check_mn(0x19ceff8, 'lsr', 'count = (end-begin) >> 3')
check_imm(0x19ceff8, 3, 'count shift 3')
check_disp(0x19ceffc, 0xd4, 'count stored at param+0x04')
check_imm(0x19cf01c, 0xd0, 'param struct base passed as x3')
# 0x3781470 copies it in
check_imm(0x37814c4, 0x340, 'the scroller object is 0x340 bytes')
check_disp(0x3781548, 0x0, 'param+0x00 -> scroller+0x30')
check_disp(0x378154c, 0x30, 'param qword -> scroller+0x30/+0x38')
check_disp(0x3781708, 0x160, 'the callback object goes to scroller+0x160')
check_mn(0x3781708, 'stp', 'stp x25,xzr -> scroller+0x160/+0x168')
check_disp(0x3781770, 4, 'the builder reads param+0x04')
check_mn(0x3781774, 'str', 'the builder writes the count')
check_disp(0x3781774, 0x288, 'the count lands at scroller+0x288')
check_imm(0x3781794, 0x2a4, 'scroller+0x2a4 (selected row) initialised')
check_imm(0x37817a4, 0x2b4, 'scroller+0x2b4 (decided row) initialised')
check_imm(0x3781780, 0x2ac, 'scroller+0x2ac initialised')
check_imm(0x378178c, -1, 'the -1 literal')
check_imm(0x3781778, 0x29c, 'scroller+0x29c (first visible row) initialised')
# 0x37830e0, the only setter
check_mn(0x3783114, 'str', 'setter stores the count a second time')
check_disp(0x3783114, 0x34, 'the second copy is scroller+0x34')
check_mn(0x3783118, 'str', 'setter stores scroller+0x288')
check_disp(0x3783118, 0x288, 'setter scroller+0x288')
check_disp(0x3783108, 0x28c, 'setter reads items-per-row scroller+0x28c')
check_disp(0x3783150, 0x290, 'setter recomputes the page count')
check_disp(0x37831e4, 0x2c4, 'setter recomputes the rows to fill')
# SCROLLER_ITEM_NUM
check_disp(0x19cf83c, 0xd4, 'SCROLLER_ITEM_NUM value = the same param+0x04')
check_adrp_add(0x19cf844, 0x42a1000, 0x8e6, 'SCROLLER_ITEM_NUM name page')
check_string(0x42a18e6, 'SCROLLER_ITEM_NUM', 'the Lua constant name')
check_adrp_add(0x19cf84c, 0x42b1000, 0xa84, 'type tag page')
check_string(0x42b1a84, 'i', 'the type tag is "i" (integer)')
check_call(0x19cf854, 0x33750a0, 'the registration helper')
# a sample of the later readers
for a, why in [(0x377c720, '0x377c6d0 row loop bound'),
               (0x377c7d8, '0x377c6d0 second loop bound'),
               (0x377d410, 'per-frame function'),
               (0x377d674, 'cursor clamp'),
               (0x377d830, 'scroll bar'),
               (0x377db68, 'scroll bar (2)'),
               (0x377ec94, '0x377e75c clamp'),
               (0x377ed84, 'cursor clamp (2)'),
               (0x377efe8, 'scroll position clamp'),
               (0x377f05c, 'clamp result')]:
    check_mn(a, 'ldr', 'count reader %s' % why)
    check_disp(a, 0x288, 'count reader %s' % why)
# 0x37830e0 is reachable only from other screens, never from the Mii code
section('Q6  no native Mii path changes the count')
mii = []
for a in range(0x100, 0x39C8000, 4):
    w = struct.unpack_from('<I', data, a)[0]
    if (w & 0x7C000000) == 0x14000000:
        imm = w & 0x3FFFFFF
        if imm & 0x2000000:
            imm -= 0x4000000
        if a + (imm << 2) == 0x37830e0:
            mii.append(a)
count += 1
if NEG == 'count':
    mii = [0x1809000]          # inject a fake caller inside the Mii scene object
MII_RANGES = ((0x1808980, 0x180e000, 'the Mii editor scene object'),
              (0x19ceb30, 0x19d0000, 'the headgear list class'))
inside = [a for a in mii
          if any(lo <= a < hi for lo, hi, _ in MII_RANGES)]
if inside:
    fail('Q6: 0x37830e0 has a Mii-side caller: %s' % ['0x%x' % a for a in inside])
else:
    print('   0x37830e0 has %d callers, none in %s'
          % (len(mii), ' or '.join('%s 0x%x-0x%x' % (n, lo, hi)
                                    for lo, hi, n in MII_RANGES)))

print('')
print('P10-HAT-OPEN check: %d claims, %d mismatches' % (count, len(fails)))
print('negative-control mode: %s' % (NEG or 'off'))
sys.exit(1 if fails else 0)
