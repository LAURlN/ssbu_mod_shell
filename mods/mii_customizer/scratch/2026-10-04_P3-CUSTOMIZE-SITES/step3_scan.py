"""P3-CUSTOMIZE-SITES step 3: indirect vtable-dispatch sites through slot +0x278.

Shape searched (exactly as the task specifies):
  A  `ldr xN, [xM, #0x278]`
  B  `blr xN` or `br xN` on the SAME register N, within 8 instructions AFTER A
  C  the NEAREST preceding definition of xM (within 6 instructions before A) is
     `ldr xM, [xK]` - displacement 0, the vtable word itself
Filter applied to the sites found above:
  D  the NEAREST preceding definition of xK (within 12 instructions before A) is
     `ldr xK, [xJ, #0x50]`

"Nearest preceding definition" means the search walks backwards and stops at the
first instruction that writes the register; if that instruction is not of the required
form the site is rejected. That is what makes the "register overwritten in between"
synthetic case fail.

Outputs (all under mods/mii_customizer/evidence/P3-CUSTOMIZE-SITES/):
  05_step3_synthetic.txt   synthetic validation of the matcher
  06_step3_sites.json      every unfiltered and kept site, machine readable
Writes nothing to the current directory.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python step3_scan.py
"""
import json
from array import array
from pathlib import Path

import capstone

import lib
from lib import TEXT, dis, ldr_imm, branch_reg, written

EV = Path(__file__).resolve().parents[2] / 'evidence/P3-CUSTOMIZE-SITES'
SLOT = 0x278
WRAPPER = 0x208DE60

# LDR (immediate, unsigned offset), 64-bit: 0b111_11_01_01_0xx, i.e. (w & 0xFFC00000)
# == 0xF9400000. imm12 for displacement 0x278 is 0x278/8 = 0x4F.
LDR64_BASE = 0xF9400000
LDR64_MASK = 0xFFC00000
IMM12_OF_SLOT = SLOT >> 3


def match(items, i):
    """items: list of (addr, CsInsn). i: index of a candidate `ldr`.

    Returns (ok: bool, rec: dict). rec is filled in whenever the candidate was a
    64-bit ldr with displacement 0x278, so failures are still reported.
    """
    addr, ins = items[i]
    r = ldr_imm(ins)
    if r is None:
        return False, {}
    width, n, m, disp = r
    rec = {'ldr': addr, 'reg_call': n, 'reg_vt': m, 'disp': disp}
    if width != 64 or disp != SLOT:
        rec['reject'] = 'candidate is not ldr xN,[xM,#0x278]'
        return False, rec

    # C: nearest preceding definition of xM within 6 instructions.
    vt = None
    for j in range(i - 1, max(-1, i - 7), -1):
        if m in written(items[j][1]):
            vt = j
            break
    if vt is None:
        rec['reject'] = 'no definition of xM within 6 instructions before'
        return False, rec
    v = ldr_imm(items[vt][1])
    rec['vtable_load'] = items[vt][0]
    rec['vtable_load_back'] = i - vt
    if v is None or v[1] != m or v[3] != 0:
        rec['reject'] = 'nearest def of xM is not `ldr xM,[xK]` (%s)' % (
            '%s %s' % (items[vt][1].mnemonic, items[vt][1].op_str))
        return False, rec
    rec['reg_ptr'] = v[2]

    # D: nearest preceding definition of xK within 12 instructions.
    k = v[2]
    rec['has_0x50'] = False
    for j in range(i - 1, max(-1, i - 13), -1):
        if k in written(items[j][1]):
            p = ldr_imm(items[j][1])
            rec['base_of_0x50'] = items[j][0]
            rec['base_of_0x50_back'] = i - j
            if p is not None and p[1] == k and p[3] == 0x50:
                rec['has_0x50'] = True
                rec['reg_0x50_src'] = p[2]
            rec['nearest_def_of_k'] = '%s %s' % (items[j][1].mnemonic, items[j][1].op_str)
            break
    else:
        rec['base_of_0x50'] = 0
        rec['nearest_def_of_k'] = None

    # B: blr/br on the same register within 8 instructions after.
    call = None
    for j in range(i + 1, min(len(items), i + 9)):
        b = branch_reg(items[j][1])
        if b is None:
            continue
        if b[1] == n:
            call = j
            rec['call_kind'] = b[0]
            break
        if call is None:
            break          # a different register was branched to first
    if call is None:
        rec['reject'] = 'no blr/br on x%d within 8 instructions after' % n
        return False, rec
    rec['call'] = items[call][0]
    rec['call_after'] = call - i
    return True, rec


def window(addr, before, after):
    lo = max(TEXT[0], addr - 4 * before)
    return [(a, ins) for a, ins in zip(
        range(lo, lo + 4 * (before + after + 1), 4), dis(lo, before + after + 1))]


def scan():
    n = TEXT[1] - TEXT[0]
    words = array('I')
    words.frombytes(lib.data[TEXT[0]:TEXT[1]])
    cands = []
    for i, w in enumerate(words):
        if (w & LDR64_MASK) == LDR64_BASE and ((w >> 10) & 0xFFF) == IMM12_OF_SLOT:
            cands.append(TEXT[0] + 4 * i)
    cache = {}

    def win(a, before, after):
        key = (a, before, after)
        if key not in cache:
            cache[key] = window(a, before, after)
        return cache[key]

    unfiltered, kept = [], []
    for a in cands:
        items = win(a, 12, 8)
        idx = next((k for k, (aa, _) in enumerate(items) if aa == a), None)
        if idx is None:
            continue
        ok, rec = match(items, idx)
        if ok:
            unfiltered.append(rec)
            if rec.get('has_0x50'):
                kept.append(rec)
    return cands, unfiltered, kept


# ---------------------------------------------------------------- synthetic tests
def asm(words, base=0x1000):
    b = b''.join(struct_pack(w) for w in words)
    return [(base + 4 * k, ins) for k, ins in enumerate(disasm_bytes(b, base))]


def struct_pack(w):
    return w.to_bytes(4, 'little')


def disasm_bytes(b, base):
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    md.detail = True
    return list(md.disasm(b, base))


LDR_X_RT_RN_D0 = lambda rt, rn: 0xF9400000 | (rn << 5) | rt          # ldr xRt,[xRn]
LDR_X_RT_RN_D = lambda rt, rn, imm12: 0xF9400000 | (imm12 << 10) | (rn << 5) | rt
BLR = lambda rn: 0xD63F0000 | (rn << 5)
BR = lambda rn: 0xD61F0000 | (rn << 5)
MOVZ = lambda rd, imm16: 0xD2800000 | ((imm16 & 0xFFFF) << 5) | rd    # mov xRd,#imm16
NOP = 0xD503201F


def synthetic():
    out = []
    # (1) must match: ldr x0,[x3,#0x50]; ldr x8,[x0]; ldr x3,[x8,#0x278]; blr x3
    seq = [NOP, NOP, LDR_X_RT_RN_D(0, 3, 0x50 >> 3), LDR_X_RT_RN_D0(8, 0),
           LDR_X_RT_RN_D(3, 8, SLOT >> 3), BLR(3)]
    items = asm(seq)
    i = next(k for k, (a, _) in enumerate(items) if a == 0x1000 + 16)
    ok, rec = match(items, i)
    out.append(('must match (ldr xK,[xJ,#0x50] present)', ok, rec))

    # (2) must NOT match: x8 (the vtable pointer register) is overwritten between the
    #     vtable load and the slot load
    seq = [NOP, NOP, LDR_X_RT_RN_D(0, 3, 0x50 >> 3), LDR_X_RT_RN_D0(8, 0),
           MOVZ(8, 1), LDR_X_RT_RN_D(3, 8, SLOT >> 3), BLR(3)]
    items = asm(seq)
    i = next(k for k, (a, _) in enumerate(items) if a == 0x1000 + 20)
    ok, rec = match(items, i)
    out.append(('must NOT match (x8 overwritten in between)', not ok, rec))

    # (3) must NOT match: different displacement (#0x270 instead of #0x278)
    seq = [NOP, NOP, LDR_X_RT_RN_D(0, 3, 0x50 >> 3), LDR_X_RT_RN_D0(8, 0),
           LDR_X_RT_RN_D(3, 8, 0x270 >> 3), BLR(3)]
    items = asm(seq)
    i = next(k for k, (a, _) in enumerate(items) if a == 0x1000 + 16)
    ok, rec = match(items, i)
    out.append(('must NOT match (displacement 0x270)', not ok, rec))

    # (4) shape matches but the #0x50 filter does not apply
    seq = [NOP, NOP, LDR_X_RT_RN_D0(0, 3), LDR_X_RT_RN_D0(8, 0),
           LDR_X_RT_RN_D(3, 8, SLOT >> 3), BLR(3)]
    items = asm(seq)
    i = next(k for k, (a, _) in enumerate(items) if a == 0x1000 + 16)
    ok, rec = match(items, i)
    out.append(('shape matches, filter D must be False', ok and not rec.get('has_0x50'), rec))
    return out, items


if __name__ == '__main__':
    print('capstone %s' % lib.CAPSTONE_VERSION)
    print('image %s  %d bytes  TEXT 0x%x..0x%x'
          % (lib.IMAGE.as_posix(), len(lib.data), TEXT[0], TEXT[1]))

    syn, _ = synthetic()
    lines = ['synthetic validation of the matcher (built from hand-computed encodings,'
             ' then decoded by capstone)',
             'base address 0x1000; each sequence printed in decoded form']
    allok = True
    for label, ok, rec in syn:
        allok = allok and ok
        lines.append('')
        lines.append('CASE %-46s -> %s' % (label, 'PASS' if ok else 'FAIL'))
        lines.append('  match() returned ok=%s %s' % (rec.get('call') is not None, rec))
    # show one decoded sequence for the record
    seq = [NOP, NOP, LDR_X_RT_RN_D(0, 3, 0x50 >> 3), LDR_X_RT_RN_D0(8, 0),
           LDR_X_RT_RN_D(3, 8, SLOT >> 3), BLR(3)]
    lines.append('')
    lines.append('decoded form of case 1 (words %s):' % [hex(w) for w in seq])
    for a, ins in asm(seq):
        lines.append('  0x%08x: %s %s' % (a, ins.mnemonic, ins.op_str))
    lines.append('')
    lines.append('synthetic validation overall: %s' % ('PASS' if allok else 'FAIL'))
    if not allok:
        (EV / '05_step3_synthetic.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print('\n'.join(lines))
        raise SystemExit('synthetic validation failed; scan not run')

    # known wrapper must be found by the unfiltered shape
    wr_items = window(0x208DE68, 12, 8)
    i = next(k for k, (a, _) in enumerate(wr_items) if a == 0x208DE68)
    wok, wrec = match(wr_items, i)
    lines.append('')
    lines.append('known wrapper check: ldr x3,[x8,#0x278] at 0x208de68')
    lines.append('  window decoded:')
    for a, ins in wr_items:
        mark = ' <<<' if a == 0x208DE68 else ''
        lines.append('    0x%08x: %s %s%s' % (a, ins.mnemonic, ins.op_str, mark))
    lines.append('  match() ok=%s rec=%s' % (wok, wrec))
    lines.append('  wrapper found by unfiltered shape: %s' % wok)
    allok = allok and wok
    (EV / '05_step3_synthetic.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    if not wok:
        raise SystemExit('wrapper not found by the unfiltered shape; scan not run')

    cands, unf, kept = scan()
    print('')
    print('LDR (64-bit, unsigned offset) words with displacement 0x278 in TEXT: %d'
          % len(cands))
    print('unfiltered shape matches: %d' % len(unf))
    print('kept after filter D (xK loaded with displacement 0x50): %d' % len(kept))
    (EV / '06_step3_sites.json').write_text(
        json.dumps({'slot': SLOT, 'wrapper': WRAPPER,
                    'candidates': len(cands), 'unfiltered': unf, 'kept': kept},
                   indent=1), encoding='utf-8')
    print('wrote %s' % (EV / '06_step3_sites.json').as_posix())