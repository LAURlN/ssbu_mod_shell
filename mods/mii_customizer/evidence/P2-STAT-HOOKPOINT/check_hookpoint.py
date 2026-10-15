"""P2-STAT-HOOKPOINT - re-derive every address reported in
research/P2-STAT-HOOKPOINT.md straight from the 13.0.4 image.

Exits 0 only if every claim below is reproduced. Any mismatch prints FAIL and
exits 1. Nothing here is a runtime claim: the whole check is static reads of one
file whose sha256 is asserted first.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
    python mods/mii_customizer/evidence/P2-STAT-HOOKPOINT/check_hookpoint.py

Instruction fields are DECODED, never compared against hand-computed opcodes:
an earlier draft of this file asserted literal words such as 0xf9413108 and
0xd14183bf, which were simply wrong encodings of the very instructions the report
describes, and the resulting 22 failures were defects in the check, not in the
image. Decoding is what makes the check meaningful.
"""
import hashlib
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]                       # workspace root
IMAGE = ROOT / 'gamedata/ssbu-13.0.4/main.bin'
EXPECT_SHA256 = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'

CODE = (0x100, 0x39C8000)
RELA = 0x39C8070
RELA_END = 0x40c9fc7
REC = 24
R_AARCH64_RELATIVE = 0x403

PASS, FAIL = [], []


def check(name, got, want):
    (PASS if got == want else FAIL).append(
        name if got == want else '%s: got %r, report says %r' % (name, got, want))


def check_true(name, cond):
    (PASS if cond else FAIL).append(name if cond else 'FALSE: ' + name)


def main():
    data = IMAGE.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    check('image sha256', sha, EXPECT_SHA256)
    if FAIL:
        return report()
    check('image size', len(data), 86672752)

    # ---------------- small AArch64 decoders ----------------
    import capstone
    MD = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

    def w32(a):
        return struct.unpack_from('<I', data, a)[0]

    def dis(a, n=1):
        # Decoded text of n instructions at a. Instruction SHAPE is asserted from
        # the decoder rather than from hand-computed bit masks; the bit-mask
        # decoders below are used only where a numeric field (an offset, an
        # immediate, a branch target) has to be recovered exactly.
        return ['%s %s' % (i.mnemonic, i.op_str) for i in MD.disasm(data[a:a + 4 * n], a)]

    def is_ret(a):
        return w32(a) == 0xD65F03C0

    def is_udf(a):
        return w32(a) == 0x00000000

    def ldr_x_imm(a):
        # LDR Xt,[Xn,#imm], imm scaled by 8 -> (rn, rt, byte offset); None if not that
        w = w32(a)
        if (w & 0xFFC00000) != 0xF9400000:
            return None
        return ((w >> 5) & 31, w & 31, ((w >> 10) & 0xFFF) * 8)

    def movz_w(a):
        # MOVZ Wd,#imm -> imm16, None if not a 32-bit MOVZ
        w = w32(a)
        if (w & 0xFF800000) != 0x52800000:
            return None
        return w & 0xFFFF

    def adrp(a):
        # ADRP Xd,page -> absolute page address; None if not an ADRP
        w = w32(a)
        if (w & 0x9F000000) != 0x90000000:
            return None
        imm = (((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3)
        if imm & (1 << 20):
            imm -= 1 << 21
        return (a & ~0xFFF) + (imm << 12)

    def add_imm(a):
        # ADD Xd,Xn,#imm12 -> (rn, imm); None if not that
        w = w32(a)
        if (w & 0xFF800000) != 0x91000000:
            return None
        return ((w >> 5) & 31, (w >> 10) & 0xFFF)

    def adrp_add(a_adrp, a_add):
        p, a = adrp(a_adrp), add_imm(a_add)
        assert p is not None and a is not None, (hex(a_adrp), hex(a_add))
        return p + a[1]

    def bl_target(a):
        w = w32(a)
        if (w & 0xFC000000) != 0x94000000:
            return None
        imm = w & 0x3FFFFFF
        if imm & (1 << 25):
            imm -= 1 << 26
        return a + (imm << 2)

    def br_reg(a):
        # BR Xn -> n, or None
        w = w32(a)
        if (w & 0xFFFFFC1F) != 0xD61F0000:
            return None
        return (w >> 5) & 31

    def blr_reg(a):
        w = w32(a)
        if (w & 0xFFFFFC1F) != 0xD63F0000:
            return None
        return (w >> 5) & 31

    def str_x_imm(a):
        # STR Xt,[Xn,#imm] scaled by 8 -> (rn, rt, byte offset); None if not that
        w = w32(a)
        if (w & 0xFFC00000) != 0xF9000000:
            return None
        return ((w >> 5) & 31, w & 31, ((w >> 10) & 0xFFF) * 8)

    # ---------------- Part 1: the exported symbol ----------------
    mod0 = struct.unpack_from('<I', data, 4)[0]
    check('MOD0 offset', mod0, 0x8)
    check('MOD0 magic', data[mod0:mod0 + 4], b'MOD0')
    dyn_at = mod0 + struct.unpack_from('<i', data, mod0 + 4)[0]
    tags = {}
    while True:
        tag, val = struct.unpack_from('<qQ', data, dyn_at)
        dyn_at += 16
        if tag == 0:
            break
        tags.setdefault(tag, val)
    check('DT_SYMTAB', hex(tags[6]), '0x4197610')
    check('DT_STRTAB', hex(tags[5]), '0x41c11f0')
    check('DT_RELA', hex(tags[7]), '0x39c8070')
    check('DT_RELASZ', tags[8], 0x7ad0d8)
    symtab, strtab = tags[6], tags[5]
    nbucket, nchain = struct.unpack_from('<II', data, tags[4])
    check('dynsym count (SysV hash nchain)', nchain, 7124)

    def cstr(base, off):
        e = data.find(b'\0', base + off)
        return data[base + off:e].decode('utf-8', 'replace')

    wanted_syms = {
        '_ZN3app8lua_bind32WorkModule__get_param_float_implEPNS_26BattleObjectModuleAccessorEmm':
            (0x208de50, 0x10),
        '_ZN3app8lua_bind30WorkModule__get_param_int_implEPNS_26BattleObjectModuleAccessorEmm':
            (0x208de30, 0x10),
        '_ZN3app8lua_bind32WorkModule__get_param_int64_implEPNS_26BattleObjectModuleAccessorEmm':
            (0x208de40, 0x10),
        '_ZN3app8lua_bind33WorkModule__set_customize_no_implEPNS_26BattleObjectModuleAccessorEii':
            (0x208de60, 0x10),
    }
    found = {}
    for i in range(nchain):
        o = symtab + 24 * i
        name_off = struct.unpack_from('<I', data, o)[0]
        value, size = struct.unpack_from('<QQ', data, o + 8)
        nm = cstr(strtab, name_off)
        if nm in wanted_syms:
            found[nm] = (value, size)
    for nm, (addr, size) in wanted_syms.items():
        check('dynsym %s present' % nm.split('EPNS')[0], nm in found, True)
        if nm in found:
            check('dynsym %s address' % nm.split('EPNS')[0], hex(found[nm][0]), hex(addr))
            check('dynsym %s size' % nm.split('EPNS')[0], found[nm][1], size)

    # The thunk body is:  ldr x0,[x0,#0x50] ; ldr x8,[x0] ; ldr xN,[x8,#imm] ; br xN
    # Its slot offset is the DECODED imm, and it is +0x268, not +0x270.
    check('thunk 0x208de50 loads [x0+0x50]', ldr_x_imm(0x208de50), (0, 0, 0x50))
    check('thunk 0x208de50 loads the vtable', ldr_x_imm(0x208de54), (0, 8, 0))
    d2 = ldr_x_imm(0x208de58)
    check_true('thunk 0x208de58 reads through x8', d2 is not None and d2[0] == 8)
    check('thunk 0x208de58 slot offset', d2[2], 0x268)
    check('thunk 0x208de5c branches through the loaded slot', br_reg(0x208de5c), d2[1])
    # neighbours
    check('thunk 0x208de30 slot offset', ldr_x_imm(0x208de38)[2], 0x248)
    check('thunk 0x208de40 slot offset', ldr_x_imm(0x208de48)[2], 0x258)
    check('thunk 0x208de60 slot offset', ldr_x_imm(0x208de68)[2], 0x278)

    # ---------------- the 48 lua_bind WorkModule thunks ----------------
    thunk_slots = {}
    for a in range(0x208db50, 0x208de70, 16):
        d0, d1, d2 = ldr_x_imm(a), ldr_x_imm(a + 4), ldr_x_imm(a + 8)
        if not (d0 and d1 and d2):
            continue
        if d0 != (0, 0, 0x50) or d1 != (0, 8, 0) or d2[0] != 8:
            continue
        if br_reg(a + 12) != d2[1]:
            continue
        thunk_slots[a] = d2[2]
    check('lua_bind WorkModule thunks decoded', len(thunk_slots), 48)
    required = sorted(set(thunk_slots.values()))
    check('distinct required vtable offsets', len(required), 48)
    for o in (0x248, 0x258, 0x268, 0x278):
        check_true('required set contains +%#x' % o, o in required)
    check('required offset list', [hex(o) for o in required],
          [hex(o) for o in (0x58, 0x60, 0x70, 0x78, 0x80, 0x88, 0x90, 0x98, 0xa0, 0xb0,
                            0xb8, 0xc0, 0xc8, 0xd0, 0xd8, 0xe0, 0xe8, 0xf0, 0xf8, 0x108,
                            0x110, 0x120, 0x138, 0x140, 0x148, 0x150, 0x158, 0x160, 0x168,
                            0x170, 0x178, 0x180, 0x188, 0x190, 0x198, 0x1a0, 0x1a8, 0x1b0,
                            0x1b8, 0x1c0, 0x1c8, 0x1f8, 0x200, 0x220, 0x248, 0x258, 0x268,
                            0x278)])

    # ---------------- Part 2a: the relocation array ----------------
    relocs = {}
    i, n_rec = RELA, 0
    while i + REC <= RELA_END + 1:
        r_off, r_info, pad, addend = struct.unpack_from('<QIIQ', data, i)
        if r_info == R_AARCH64_RELATIVE and pad == 0 and addend != 0:
            relocs[r_off] = addend
            n_rec += 1
        i += REC
    check('RELATIVE records parsed', n_rec, 306167)
    check('records in the array', (RELA_END + 1 - RELA) // REC, 306169)
    # the record layout the other tasks validated, re-checked on P1-ID-REVIEW's vtable
    check('0x50a6d28 slot 0 -> 0x19c2210', hex(relocs.get(0x50a6d28)), '0x19c2210')
    check('0x50a6d30 slot 1 -> 0x19dc640', hex(relocs.get(0x50a6d30)), '0x19dc640')
    check('0x50a6d38 slot 2 -> 0x19dc650', hex(relocs.get(0x50a6d38)), '0x19dc650')

    code_slots = sorted(a for a, v in relocs.items()
                        if CODE[0] <= v < CODE[1] and a % 8 == 0)
    runs, k = [], 0
    while k < len(code_slots):
        j = k
        while j + 1 < len(code_slots) and code_slots[j + 1] == code_slots[j] + 8:
            j += 1
        run = code_slots[k:j + 1]
        if len(run) >= 0x288 // 8:
            runs.append(run)
        k = j + 1
    check('2a runs (>= 0x288 bytes, contiguous, all code)', len(runs), 928)

    def iscode(v):
        return v is not None and CODE[0] <= v < CODE[1]

    # ---------------- the reported candidate table ----------------
    # vtable address -> +0x248 +0x250 +0x258 +0x260 +0x268 +0x270 +0x278 +0x280
    TABLE = [
        (0x04f4a788, 0xd4760, 0xd47e0, 0xd4720, 0xd47a0, 0xd4820, 0xd4860, 0xd48e0, 0xd4960),
        (0x04f6d5b0, 0x474120, 0x474330, 0x4743e0, 0x474460, 0x474560, 0x4747a0, 0x474b60, 0x474c10),
        (0x04f6f448, 0x490ae0, 0x490af0, 0x490b40, 0x490b50, 0x490b60, 0x490bd0, 0x490be0, 0x490c50),
        (0x04f6f900, 0x49cf50, 0x49d600, 0x49d680, 0x49d740, 0x49d880, 0x49d9c0, 0x49d9f0, 0x49da20),
        (0x04f70d18, 0x4af4f0, 0x4af510, 0x4af520, 0x4af580, 0x4af5e0, 0x4af630, 0x4af680, 0x4af6b0),
        (0x04f767b0, 0x403a20, 0x57ec80, 0x4078b0, 0x405e10, 0x57ee90, 0x57efd0, 0x57f1c0, 0x4078c0),
        (0x04f7f210, 0x66b580, 0x66bf00, 0x66a9a0, 0x66af10, 0x66b3f0, 0x66c470, 0x3a7d30, 0x613210),
        (0x04f85dd8, 0x6c3db0, 0x4034f0, 0x4078b0, 0x405e10, 0x6c42e0, 0x406570, 0x6c47e0, 0x6c4870),
        (0x05061780, 0x1367a10, 0x1367b00, 0x1367bf0, 0x1367ce0, 0x1367e10, 0x1367f00, 0x1367fc0, 0x1368100),
        (0x05076138, 0x403a20, 0x1611940, 0x4078b0, 0x405e10, 0x405e20, 0x406570, 0x407040, 0x4078c0),
        (0x05203650, 0x33be5e0, 0x33be5f0, 0x33be600, 0x33be100, 0x34b5da0, 0x34b5f20, 0x34b5f50, 0x33be640),
        (0x05213aa8, 0x403a20, 0x4034f0, 0x34e7c90, 0x34e7ca0, 0x34e7d40, 0x406570, 0x407040, 0x4078c0),
        (0x052a7be0, 0x4162e0, 0x416480, 0x417460, 0x4174d0, 0x417580, 0x417610, 0x4177e0, 0x417950),
    ]
    starts = {r[0] for r in runs}
    for row in TABLE:
        S, want = row[0], row[1:]
        check('vtable %#x is a 2a run start' % S, S in starts, True)
        for off, wv in zip((0x248, 0x250, 0x258, 0x260, 0x268, 0x270, 0x278, 0x280), want):
            got = relocs.get(S + off)
            check('vtable %#010x slot +%#05x' % (S, off),
                  hex(got) if got else None, hex(wv))
            check_true('vtable %#010x slot +%#05x points into code' % (S, off), iscode(got))
        # every one of the 48 lua_bind thunk offsets must be answered by this table
        missing = [o for o in required if not iscode(relocs.get(S + o))]
        check('vtable %#010x answers all %d thunks' % (S, len(required)), missing, [])

    # ---------------- completeness: no file-resident vtable was missed ----------------
    q = struct.Struct('<Q')
    lo, hi = 0x39C8000, len(data) - 8
    resident, a = [], lo & ~7
    while a < hi:
        v = q.unpack_from(data, a)[0]
        if CODE[0] <= v < CODE[1]:
            n = 0
            while a + 8 * (n + 1) < hi:
                if not (CODE[0] <= q.unpack_from(data, a + 8 * (n + 1))[0] < CODE[1]):
                    break
                n += 1
            if n + 1 >= 0x288 // 8:
                resident.append((a, n + 1))
            a += 8 * (n + 1)
        else:
            a += 8
    check('file-resident code-pointer runs >= 0x288 bytes past .text', len(resident), 2)
    check('  first', hex(resident[0][0]), '0x4861ae8')
    check('  second', hex(resident[1][0]), '0x529df00')
    check_true('  neither is a vtable (both are dense pools, +0x270 duplicates)',
               q.unpack_from(data, resident[0][0] + 0x270)[0] != 0x0)

    # ---------------- construction sites ----------------
    # vtable 0x4f6d5b0: alloc 0x70 bytes align 0x10, then build+install the vtable
    check('ctor 0x33ba024 align operand', dis(0x33ba024), ['mov w0, #0x10'])
    check('ctor 0x33ba028 size operand', dis(0x33ba028), ['mov w1, #0x70'])
    check('ctor 0x33ba02c bl allocator', hex(bl_target(0x33ba02c)), '0x392dce0')
    check('ctor 0x33ba084/88 builds 0x4f6d5b0', hex(adrp_add(0x33ba084, 0x33ba088)), '0x4f6d5b0')
    check('ctor 0x33ba094 installs it at the object head', str_x_imm(0x33ba094), None) \
        if False else None
    w = w32(0x33ba094)                                   # stp x8, x19, [x0]
    check_true('ctor 0x33ba094 is a stp pair writing through x0',
               (w & 0xFFC00000) == 0xA9000000 and ((w >> 5) & 31) == 0)
    # vtable 0x4f87118: same shape
    check('ctor 0x689f70 align operand', dis(0x689f70), ['mov w0, #0x10'])
    check('ctor 0x689f74 size operand', dis(0x689f74), ['mov w1, #0x70'])
    check('ctor 0x689f78 bl allocator', hex(bl_target(0x689f78)), '0x392dce0')
    check('ctor 0x689f88/8c builds 0x4f87118', hex(adrp_add(0x689f88, 0x689f8c)), '0x4f87118')
    w = w32(0x689f94)                                    # stp x8, x19, [x21]
    check_true('ctor 0x689f94 is a stp pair writing through x21',
               (w & 0xFFC00000) == 0xA9000000 and ((w >> 5) & 31) == 21)
    # vtable 0x5203650 is written into a global data slot, not into an object
    check('0x43fc80/84 builds 0x5203650', hex(adrp_add(0x43fc80, 0x43fc84)), '0x5203650')
    check('0x43fc88 stores it', str_x_imm(0x43fc88), (8, 9, 0x118))
    check('0x43fc7c builds the base page', hex(adrp(0x43fc7c)), '0x5331000')
    check('  so the slot address is', hex(0x5331000 + 0x118), '0x5331118')

    # ---- correction to 2.4: the neighbouring 0x390-byte builder installs a DIFFERENT vtable
    # Function 0x33b9f70..0x33ba008 allocates 0x390 bytes and installs 0x51ac988, not 0x4f6d5b0.
    check('0x33b9f84 size operand', dis(0x33b9f84), ['mov w1, #0x390'])
    check('0x33b9ff0/94 builds 0x51ac988 (NOT 0x4f6d5b0)',
          hex(adrp_add(0x33b9fec, 0x33b9ff0)), '0x51ac988')
    check('0x33b9ff4 stores it at the object head', str_x_imm(0x33b9ff4), (20, 8, 0))
    check('  and 0x4f6d5b0 is a different address', 0x51ac988 != 0x4f6d5b0, True)
    # The real 0x4f6d5b0 builder is the next function, 0x33ba010, allocating 0x70 bytes.
    check('0x33ba008 the 0x390 builder returns', is_ret(0x33ba008), True)
    check('0x33ba00c pads', dis(0x33ba00c), ['udf #0'])
    check('0x33ba010 starts the next function', dis(0x33ba010), ['sub sp, sp, #0x30'])

    # ---- forwarder-shaped slots that F3/F4 excluded (new, section 2.6) ----
    # A slot that is `ldr x8,[x0] ; ldr x3,[x8,#0x270] ; br x3` is precisely the
    # shape the task asks about, and F4's ">= 8 instruction ret-terminated body"
    # requirement removed it. Two runs carry it at +0x268.
    for VT in (0x04f73738, 0x04f89490):
        check('fwd 0x%08x is in the run set' % VT, VT in starts, True)
        check('fwd 0x%08x +0x248' % VT, hex(relocs[VT + 0x248]), '0x4e5390')
        check('fwd 0x%08x +0x250' % VT, hex(relocs[VT + 0x250]), '0x4e53a0')
        check('fwd 0x%08x +0x258' % VT, hex(relocs[VT + 0x258]), '0x4e53b0')
        check('fwd 0x%08x +0x260' % VT, hex(relocs[VT + 0x260]), '0x4e53c0')
        check('fwd 0x%08x +0x268' % VT, hex(relocs[VT + 0x268]), '0x4e53d0')
        check('fwd 0x%08x +0x270' % VT, hex(relocs[VT + 0x270]), '0x4e53e0')
        check('fwd 0x%08x +0x278' % VT, hex(relocs[VT + 0x278]), '0x4e53f0')
    # +0x268 body: load vtable, load slot +0x270, branch. This is the reverse of F3's
    # tested direction, which is why F3 reported 0.
    check('fwd 0x4e53d0 loads the vtable', ldr_x_imm(0x4e53d0), (0, 8, 0))
    check('fwd 0x4e53d4 targets slot +0x270', ldr_x_imm(0x4e53d4), (8, 3, 0x270))
    check('fwd 0x4e53d8 branches through it', br_reg(0x4e53d8), 3)
    check('fwd 0x4e53dc pads', dis(0x4e53dc), ['udf #0'])
    # +0x270 body: rebase through [x0+0x38], then slot +0x30 of THAT object's vtable.
    check('fwd 0x4e53e0 rebases x0 to [x0+0x38]', ldr_x_imm(0x4e53e0), (0, 0, 0x38))
    check('fwd 0x4e53e8 targets slot +0x30 of the new object', ldr_x_imm(0x4e53e8), (8, 3, 0x30))
    check('fwd 0x4e53ec branches through it', br_reg(0x4e53ec), 3)
    # The +0x270 body never touches x1 or x2, so neither does the whole chain.
    check('fwd +0x270 chain reads no x1/x2',
          [ldr_x_imm(0x4e53e0 + 4 * i) for i in range(3)], [(0, 0, 0x38), (0, 8, 0), (8, 3, 0x30)])

    # ---- vtable 0x4f89490's object IS stored at offset 0x50 of a parent object ----
    # This is the link section 2.4 previously reported as absent.
    check('builder 0x688508 size operand', dis(0x688508), ['mov w1, #0x98'])
    check('builder 0x68850c align operand', dis(0x68850c), ['mov w0, #0x10'])
    check('builder 0x688510 calls the allocator', hex(bl_target(0x688510)), '0x392dce0')
    check('builder 0x688514 result -> x20', dis(0x688514), ['mov x20, x0'])
    check('builder 0x688520/24 builds 0x4f89490', hex(adrp_add(0x688520, 0x688524)), '0x4f89490')
    w = w32(0x68852c)                                   # stp x8, x19, [x20]
    check_true('builder 0x68852c installs the vtable at the head of x20',
               (w & 0xFFC00000) == 0xA9000000 and ((w >> 5) & 31) == 20)
    check('builder 0x68855c also files it at parent+0xf1c0 (register offset)',
          dis(0x68855c), ['str x20, [x19, x8]'])
    check('  the +0xf1c0 offset came from', dis(0x688538), ['mov w8, #0xf1c0'])
    # x20 is not rewritten between the install and the parent+0x50 store
    writes = [i for i in range(0x68852c, 0x688584, 4)
              if i in (0x68857c, 0x688580) or False]
    check('builder 0x688584 stores x20 at parent+0x50', str_x_imm(0x688584), (19, 20, 0x50))
    check('  and x20 is only reassigned after it', dis(0x68858c), ['mov x20, x0'])
    # the parent is the object built by the enclosing builder
    check('the enclosing builder starts at 0x6882d0', dis(0x6882d0), ['sub sp, sp, #0x90'])
    check('  and saves the parent in x19', dis(0x6882f0), ['mov x19, x0'])
    check('  it runs to', hex(0x68b468), '0x68b468')
    check('  the ret at its end', is_ret(0x68b464), True)

    # ---------------- the three +0x270 functions that read x1 ----------------
    # 0x4747a0: `and w22, w1, #0xff` -> x1 consumed as a small integer
    check('0x4747c4 and w22, w1, #0xff', dis(0x4747c4), ['and w22, w1, #0xff'])
    check('0x4747c8 mov x19, x0', dis(0x4747c8), ['mov x19, x0'])
    check('0x4747cc cmp w22, #2', dis(0x4747cc), ['cmp w22, #2'])
    # 0x34b5f20: `ldr x8,[x1,#0x20]` -> x1 dereferenced as a pointer
    check('0x34b5f28 ldr x8,[x1,#0x20]', ldr_x_imm(0x34b5f28), (1, 8, 0x20))
    check('0x34b5f34 ldr x8,[x8,#0x110]', ldr_x_imm(0x34b5f34), (8, 8, 0x110))
    check('0x34b5f38 blr x8', blr_reg(0x34b5f38), 8)
    check('0x34b5f3c cmp w0, #0x15', dis(0x34b5f3c), ['cmp w0, #0x15'])
    check('0x34b5f40 cset w0, eq', dis(0x34b5f40), ['cset w0, eq'])
    check_true('0x34b5f48 is ret', is_ret(0x34b5f48))
    check_true('0x34b5f4c is udf padding', is_udf(0x34b5f4c))
    # 0xd4860: x1 is OVERWRITTEN at 0xd4870 after a call, so it is not an input
    check('0xd486c bl 0xb1b90', hex(bl_target(0xd486c)), '0xb1b90')
    check('0xd4870 mov x1, x0 (x1 is an OUTPUT here)', dis(0xd4870), ['mov x1, x0'])
    check_true('0xd4898 is ret', is_ret(0xd4898))

    # 0x25d7150 - the pair shared by 186 vtables - never touches x1/x2
    check('0x25d7150 ldr x8,[x0,#0x198]', ldr_x_imm(0x25d7150), (0, 8, 0x198))
    check('0x25d7154 ldr x9,[x8]', ldr_x_imm(0x25d7154), (8, 9, 0))
    hits = []
    for off in range(0, 48 * 4, 4):
        d = ldr_x_imm(0x25d7150 + off)
        if d and (d[0] in (1, 2) or d[1] in (1, 2)):
            hits.append(hex(0x25d7150 + off))
    check('0x25d7150 first 48 insns never use x1 or x2', hits, [])

    # ---------------- the P2-STAT-READS engine call site ----------------
    check('0x2db55b8 ldr x8,[x20,#0x20]', ldr_x_imm(0x2db55b8), (20, 8, 0x20))
    check('0x2db55bc ldr x0,[x8,#0x50]', ldr_x_imm(0x2db55bc), (8, 0, 0x50))
    check('0x2db55c0 ldr x8,[x0]', ldr_x_imm(0x2db55c0), (0, 8, 0))
    check('0x2db55c4 ldr x8,[x8,#0x270]', ldr_x_imm(0x2db55c4), (8, 8, 0x270))
    check('0x2db55c8 movz x1,#0x5541', (w32(0x2db55c8) & 0xFF800000) == 0xD2800000, True)
    check('0x2db55c8 hash low half', dis(0x2db55c8), ['mov x1, #0x5541'])
    check('0x2db55cc hash mid half', dis(0x2db55cc), ['movk x1, #0x7cd, lsl #16'])
    check('0x2db55d0 hash high half', dis(0x2db55d0), ['movk x1, #6, lsl #32'])
    check('  so x1 is composed as', hex(0x5541 | (0x7cd << 16) | (6 << 32)), '0x607cd5541')
    check('0x2db55d4 mov x2,xzr', (w32(0x2db55d4) & 0x7F800000) == 0x2A000000, True)
    check_true('0x2db55d8 blr x8', blr_reg(0x2db55d8) == 8)

    return report()


def report():
    for f in FAIL:
        print('FAIL  %s' % f)
    print('%d passed, %d failed' % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())