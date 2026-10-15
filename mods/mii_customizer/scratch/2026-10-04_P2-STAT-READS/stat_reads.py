"""P2-STAT-READS scanner. Locates uses of two Hash40 parameter constants in
gamedata/ssbu-13.0.4/main.bin (flat decompressed NSO, VA == file offset).

  weight         0x0607cd5541
  walk_speed_max 0x0ee2ec2860

Subcommands:
  validate  self-test of the movz/movk sequence scanner on synthetic buffers
  data      step 2: raw 8-byte little-endian / low-40-bits data hits
  code      step 1+3+4: code sites, windows, enclosing fns, callers
"""
import struct, sys, json
from pathlib import Path
import capstone

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
TEXT = (0x100, 0x39C8000)
HASH = {
    'weight': 0x0607cd5541,
    'walk_speed_max': 0x0ee2ec2860,
}

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md.detail = True
# regs_access() raises CsError unless detail is enabled; without this the
# register-overwrite check silently saw no writers at all.
md_vs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md_vs.detail = True
_VS_CACHE = {}


def load():
    return IMAGE.read_bytes()


def sx(v, b):
    return v - (1 << b) if v & (1 << (b - 1)) else v


# ---------------------------------------------------------------- movz / movk
# AArch64 wide-immediate forms:
#   MOVZ 64: 0xd2800000 | hw<<21 | imm16<<5 | Rd
#   MOVK 64: 0xf2800000 | hw<<21 | imm16<<5 | Rd
#   MOVZ 32: 0x52800000 ... ; MOVK 32: 0x72800000 ...
def decode_movz(word):
    """Return (reg, imm16, hw, sf) if word is MOVZ, else None."""
    if (word & 0xFF800000) == 0xD2800000:
        sf = 1
    elif (word & 0xFF800000) == 0x52800000:
        sf = 0
    else:
        return None
    return (word & 31, (word >> 5) & 0xFFFF, (word >> 21) & 3, sf)


def decode_movk(word):
    """Return (reg, imm16, hw, sf) if word is MOVK, else None."""
    if (word & 0xFF800000) == 0xF2800000:
        sf = 1
    elif (word & 0xFF800000) == 0x72800000:
        sf = 0
    else:
        return None
    return (word & 31, (word >> 5) & 0xFFFF, (word >> 21) & 3, sf)


def dest_regs(word):
    """Registers written by an arbitrary instruction, as a set of x-register
    numbers.  Uses capstone regs_access; falls back conservatively."""
    hit = _VS_CACHE.get(word)
    if hit is not None:
        return hit
    out = set()
    try:
        ins = next(md_vs.disasm(struct.pack('<I', word), 0), None)
        if ins is not None:
            _, writes = ins.regs_access()
            for r in writes:
                name = ins.reg_name(r)
                if name and name[0] in 'xw' and name[1:].isdigit():
                    out.add(int(name[1:]))
            # A call clobbers the caller-saved registers; capstone reports only
            # the link register, so add the ABI-clobbered set by hand.
            if ins.mnemonic in ('bl', 'blr'):
                out |= set(range(0, 19))
    except capstone.CsError:
        out = set(range(0, 31))
    _VS_CACHE[word] = out
    return out


def scan_sequences(data, targets, lo, hi, max_gap=4):
    """Scan [lo,hi) for movz(+movk) sequences composing any value in targets.

    A sequence starts at a MOVZ of the low bits (or any MOVZ) on register R and
    is completed by subsequent MOVK/MOVZ instructions on the same R, allowed to
    be separated by at most max_gap other instructions that do not write R.
    Returns list of dicts: {addr, reg, value, insns:[{addr,word,kind}]}.
    """
    targets = set(targets)
    n = (hi - lo) // 4
    words = struct.unpack_from('<%dI' % n, data, lo)
    hits = []

    for i in range(n):
        mz = decode_movz(words[i])
        if mz is None:
            continue
        reg, imm16, hw, sf = mz
        if sf == 1:
            value = imm16 << (16 * hw)
        else:
            value = imm16 << (16 * hw)  # 32-bit movz zeroes upper 32
        start_addr = lo + 4 * i
        seq = [{'addr': start_addr, 'word': words[i], 'kind': 'movz'}]
        gap = 0
        for j in range(i + 1, min(n, i + 1 + max_gap + 8)):
            w2 = words[j]
            wr = dest_regs(w2)
            mk = decode_movk(w2)
            mz2 = decode_movz(w2)
            if mk is not None and mk[0] == reg and mk[3] == sf:
                _, imm2, hw2, _ = mk
                value = (value & ~(0xFFFF << (16 * hw2))) | (imm2 << (16 * hw2))
                seq.append({'addr': lo + 4 * j, 'word': w2, 'kind': 'movk'})
                gap = 0
            elif mz2 is not None and mz2[0] == reg and mz2[3] == sf:
                # a second MOVZ restarts; treat as overwrite of the register
                break
            else:
                if reg in wr:
                    break  # register overwritten, sequence invalid
                gap += 1
                if gap > max_gap:
                    break
            if value in targets:
                hits.append({
                    'addr': start_addr,
                    'reg': reg,
                    'value': value,
                    'insns': list(seq),
                    'complete_addr': seq[-1]['addr'],
                })
                break
    return hits


def scan_sequences_strict(data, targets, lo, hi, max_gap=4):
    """Simpler variant: compose full value from a MOVZ seed and up to 3 MOVKs,
    requiring each MOVK to appear within max_gap instructions of the previous
    composing instruction and no intervening write to the register.  Used as the
    cross-check implementation for `validate`."""
    targets = set(targets)
    n = (hi - lo) // 4
    words = struct.unpack_from('<%dI' % n, data, lo)
    hits = []
    for i in range(n):
        mz = decode_movz(words[i])
        if mz is None:
            continue
        reg, imm16, hw, sf = mz
        value = imm16 << (16 * hw)
        seq = [{'addr': lo + 4 * i, 'word': words[i], 'kind': 'movz'}]
        last = i
        for j in range(i + 1, min(n, i + 1 + max_gap * 3 + 4)):
            w2 = words[j]
            # max_gap intervening instructions means the next composing
            # instruction may sit at distance max_gap + 1.
            if j - last > max_gap + 1:
                break
            wr = dest_regs(w2)
            mk = decode_movk(w2)
            if mk is not None and mk[0] == reg and mk[3] == sf:
                _, imm2, hw2, _ = mk
                value = (value & ~(0xFFFF << (16 * hw2))) | (imm2 << (16 * hw2))
                seq.append({'addr': lo + 4 * j, 'word': w2, 'kind': 'movk'})
                last = j
                if value in targets:
                    hits.append({'addr': lo + 4 * i, 'reg': reg,
                                 'value': value, 'insns': list(seq),
                                 'complete_addr': seq[-1]['addr']})
                    break
            elif reg in wr:
                # any other write to the register kills the chain (a second
                # MOVZ on the same register included)
                break
    return hits


# ------------------------------------------------------------------ step 2
def data_hits(data, value):
    """Raw 8-byte LE match anywhere, and low-40-bits match at 8-byte
    alignment.  Returns (raw_offsets, masked_offsets)."""
    pat = struct.pack('<Q', value)
    raw, masked = [], []
    i = 0
    while True:
        i = data.find(pat, i)
        if i < 0:
            break
        raw.append(i)
        i += 1
    # masked: any 8-byte aligned slot whose low 40 bits equal value
    for off in range(0, len(data) - 8, 8):
        q = struct.unpack_from('<Q', data, off)[0]
        if (q & ((1 << 40) - 1)) == (value & ((1 << 40) - 1)):
            masked.append(off)
    return raw, masked


# ------------------------------------------------------------------ helpers
def disasm(data, addr, count):
    out = []
    for k in range(count):
        a = addr + 4 * k
        if a + 4 > len(data):
            break
        w = struct.unpack_from('<I', data, a)[0]
        ins = next(md.disasm(data[a:a + 4], a), None)
        txt = f'{ins.mnemonic:8s} {ins.op_str}' if ins else '.word'
        out.append({'addr': a, 'word': w, 'text': txt.strip()})
    return out


def main():
    c = sys.argv[1]
    data = load()
    if c == 'validate':
        run_validate()
    elif c == 'data':
        for name, v in HASH.items():
            raw, masked = data_hits(data, v)
            print(f'== {name} 0x{v:010x}')
            print(f'raw 8-byte LE count: {len(raw)}')
            for o in raw[:64]:
                print(f'  0x{o:08x} (align8={"yes" if o % 8 == 0 else "no"})')
            print(f'low-40-bits at 8-byte alignment count: {len(masked)}')
            for o in masked[:64]:
                print(f'  0x{o:08x}')
    elif c == 'code':
        report_code(data)
    else:
        print('unknown subcommand', c)


# ------------------------------------------------------------------ validate
def encode_movz(reg, imm16, hw, sf=1):
    base = 0xD2800000 if sf else 0x52800000
    return base | (hw << 21) | ((imm16 & 0xFFFF) << 5) | reg


def encode_movk(reg, imm16, hw, sf=1):
    base = 0xF2800000 if sf else 0x72800000
    return base | (hw << 21) | ((imm16 & 0xFFFF) << 5) | reg


def nop():
    return 0xD503201F  # nop


def run_validate():
    """Plant hashes in a synthetic buffer; both scanners must find them, and
    neither may report a sequence whose register is overwritten in between."""
    ok = True
    def check(label, cond):
        nonlocal ok
        print(('PASS ' if cond else 'FAIL ') + label)
        if not cond:
            ok = False

    # dest_regs must actually report writers, otherwise the overwrite
    # negative tests below would pass vacuously.
    check('dest_regs reports writer of movz x5', 5 in dest_regs(encode_movz(5, 0x1234, 0)))
    check('dest_regs reports clobber on bl', 3 in dest_regs(0x94000003))
    check('dest_regs reports writer of add x5,x6,x7',
          5 in dest_regs(0x8B0600A5))

    for name, v in HASH.items():
        h = [(v >> (16 * k)) & 0xFFFF for k in range(4)]  # h[0..3]
        # canonical 3-instruction build: movz h0, movk h1, movk h2
        buf = [encode_movz(5, h[0], 0), encode_movk(5, h[1], 1),
               encode_movk(5, h[2], 2), nop()]
        data = struct.pack('<%dI' % len(buf), *buf)
        r1 = scan_sequences(data, [v], 0, len(data), max_gap=4)
        r2 = scan_sequences_strict(data, [v], 0, len(data), max_gap=4)
        check(f'{name}: 3-insn adjacent plant found by scanner', len(r1) == 1)
        check(f'{name}: 3-insn adjacent plant found by strict', len(r2) == 1)
        if r1:
            check(f'{name}: plant register x5', r1[0]['reg'] == 5)
            check(f'{name}: plant value', r1[0]['value'] == v)

        # split build with gap: movz, 3 nops, movk, 3 nops, movk  (gap<=4)
        buf = [encode_movz(6, h[0], 0), nop(), nop(), nop(),
               encode_movk(6, h[1], 1), nop(), nop(), nop(),
               encode_movk(6, h[2], 2), nop()]
        data = struct.pack('<%dI' % len(buf), *buf)
        r1 = scan_sequences(data, [v], 0, len(data), max_gap=4)
        r2 = scan_sequences_strict(data, [v], 0, len(data), max_gap=4)
        check(f'{name}: gapped (gap=3) plant found by scanner', len(r1) == 1)
        check(f'{name}: gapped (gap=3) plant found by strict', len(r2) == 1)

        # gap of exactly 4 intervening non-register instructions, with the
        # intervening instructions writing OTHER registers (the shape seen at
        # 0x595a8c in the real image).  Must be found by both scanners.
        buf = [encode_movz(11, h[0], 0), nop(), nop(), nop(), nop(),
               encode_movk(11, h[1], 1), nop(), nop(), nop(), nop(),
               encode_movk(11, h[2], 2), nop()]
        data = struct.pack('<%dI' % len(buf), *buf)
        r1 = scan_sequences(data, [v], 0, len(data), max_gap=4)
        r2 = scan_sequences_strict(data, [v], 0, len(data), max_gap=4)
        check(f'{name}: gap=exactly-4 plant found by scanner', len(r1) == 1)
        check(f'{name}: gap=exactly-4 plant found by strict', len(r2) == 1)

        # same, but the intervening movks write other registers, as at 0x595a8c
        buf = [encode_movz(12, h[0], 0), encode_movk(15, 0x14, 2),
               encode_movk(16, 0x14, 2), encode_movk(17, 0x0b, 2),
               encode_movk(18, 0x0a, 2), encode_movk(12, h[1], 1),
               encode_movk(12, h[2], 2), nop()]
        data = struct.pack('<%dI' % len(buf), *buf)
        r1 = scan_sequences(data, [v], 0, len(data), max_gap=4)
        r2 = scan_sequences_strict(data, [v], 0, len(data), max_gap=4)
        check(f'{name}: interleaved-other-register plant (scanner)', len(r1) == 1)
        check(f'{name}: interleaved-other-register plant (strict)', len(r2) == 1)

        # negative: intervening overwrite of the same register
        #   movz x7,h0 ; movz x7,#1 (overwrite) ; movk x7,h1 ; movk x7,h2
        buf = [encode_movz(7, h[0], 0), encode_movz(7, 0x1234, 0),
               encode_movk(7, h[1], 1), encode_movk(7, h[2], 2), nop()]
        data = struct.pack('<%dI' % len(buf), *buf)
        r1 = scan_sequences(data, [v], 0, len(data), max_gap=4)
        r2 = scan_sequences_strict(data, [v], 0, len(data), max_gap=4)
        check(f'{name}: overwrite-between NOT reported (scanner)', len(r1) == 0)
        check(f'{name}: overwrite-between NOT reported (strict)', len(r2) == 0)

        # negative: gap too large (>4)
        buf = [encode_movz(8, h[0], 0)] + [nop()] * 6 + \
              [encode_movk(8, h[1], 1)] + [nop()] * 6 + \
              [encode_movk(8, h[2], 2), nop()]
        data = struct.pack('<%dI' % len(buf), *buf)
        r1 = scan_sequences(data, [v], 0, len(data), max_gap=4)
        r2 = scan_sequences_strict(data, [v], 0, len(data), max_gap=4)
        check(f'{name}: gap>4 NOT reported (scanner)', len(r1) == 0)
        check(f'{name}: gap>4 NOT reported (strict)', len(r2) == 0)

        # negative: a plain data-literal u64 of the hash (movz+movk on a
        # different register) must not be confused -- actually that IS a build;
        # instead confirm a lone movz of only h0 does not match.
        buf = [encode_movz(9, h[0], 0), nop()]
        data = struct.pack('<%dI' % len(buf), *buf)
        r1 = scan_sequences(data, [v], 0, len(data), max_gap=4)
        check(f'{name}: lone movz low-half NOT reported', len(r1) == 0)

    print('VALIDATE', 'OK' if ok else 'FAILED')
    return 0 if ok else 1


# ------------------------------------------------------------------ step 1/3/4
def fstart(data, addr):
    a = addr & ~3
    for _ in range(6000):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0xFF8003FF) == 0xD10003FF or (w & 0xFFC003E0) == 0xA98003E0:
            pw = struct.unpack_from('<I', data, a - 4)[0]
            if (pw in (0xD65F03C0, 0) or (pw & 0xFC000000) == 0x14000000
                    or (pw & 0xFFFFFC1F) == 0xD61F0000 or pw == 0xD4200020
                    or (pw & 0xFC000000) == 0x94000000):
                return a
        a -= 4
        if a < TEXT[0]:
            break
    return None


def call_targets(data, lo, hi):
    out = []
    n = (hi - lo) // 4
    words = struct.unpack_from('<%dI' % n, data, lo)
    for i in range(n):
        w = words[i]
        if (w & 0x7C000000) == 0x14000000:
            a = lo + 4 * i
            t = a + (sx(w & 0x3FFFFFF, 26) << 2)
            out.append((a, 'bl', t))
    return out


def blr_targets(data, lo, hi):
    out = []
    n = (hi - lo) // 4
    words = struct.unpack_from('<%dI' % n, data, lo)
    for i in range(n):
        w = words[i]
        if (w & 0xFFFFFC1F) == 0xD63F0000:
            reg = (w >> 5) & 31
            out.append((lo + 4 * i, 'blr', reg))
    return out


def callers(data, target):
    out = []
    for a, _, t in call_targets(data, TEXT[0], TEXT[1]):
        if t == target:
            out.append(a)
    return out


def nearby_const(data, lo, hi):
    """Any 40-bit-ish constant built in the window (value >= 2^32)."""
    found = []
    n = (hi - lo) // 4
    words = struct.unpack_from('<%dI' % n, data, lo)
    for i in range(n):
        mz = decode_movz(words[i])
        if mz is None:
            continue
        reg, imm16, hw, sf = mz
        value = imm16 << (16 * hw)
        seq = [lo + 4 * i]
        gap = 0
        for j in range(i + 1, min(n, i + 12)):
            w2 = words[j]
            wr = dest_regs(w2)
            mk = decode_movk(w2)
            if mk is not None and mk[0] == reg and mk[3] == sf:
                _, imm2, hw2, _ = mk
                value = (value & ~(0xFFFF << (16 * hw2))) | (imm2 << (16 * hw2))
                seq.append(lo + 4 * j)
                gap = 0
            else:
                if reg in wr:
                    break
                gap += 1
                if gap > 4:
                    break
            if value >= (1 << 32) and (value & ((1 << 40) - 1)) != 0:
                found.append((seq[0], reg, value))
                break
    return found


def vtable_load_for_reg(data, addr, reg, lookback=20):
    """Find the instruction that produced `reg` before a blr at `addr`."""
    best = None
    for k in range(1, lookback + 1):
        a = addr - 4 * k
        if a < TEXT[0]:
            break
        w = struct.unpack_from('<I', data, a)[0]
        wr = dest_regs(w)
        if reg in wr:
            ins = next(md.disasm(data[a:a + 4], a), None)
            txt = ins.mnemonic + ' ' + ins.op_str if ins else '.word'
            return {'addr': a, 'text': txt.strip()}
    return best


def report_code(data):
    for name, v in HASH.items():
        hits = scan_sequences(data, [v], TEXT[0], TEXT[1], max_gap=4)
        print(f'== code sites for {name} 0x{v:010x}: {len(hits)}')
        for h in hits:
            fs = fstart(data, h['addr'])
            win_lo = h['addr'] - 12 * 4
            win_hi = h['addr'] + 20 * 4
            # first bl or blr after the completing instruction
            first_call = None
            for a, kind, tgt in call_targets(data, h['complete_addr'] + 4, win_hi + 64):
                first_call = {'addr': a, 'kind': kind, 'target': hex(tgt)}
                break
            if first_call is None:
                for a, kind, reg in blr_targets(data, h['complete_addr'] + 4, win_hi + 64):
                    load = vtable_load_for_reg(data, a, reg)
                    first_call = {'addr': a, 'kind': 'blr', 'reg': reg,
                                  'load': load}
                    break
            near = nearby_const(data, win_lo, win_hi)
            near_other = [(hex(a), reg, hex(val)) for a, reg, val in near
                          if val != v]
            print(f'  site 0x{h["addr"]:08x} reg x{h["reg"]} '
                  f'complete 0x{h["complete_addr"]:08x} fstart {hex(fs) if fs else None}')
            print(f'    first call after: {first_call}')
            print(f'    other 40-bit consts in window: {near_other}')


if __name__ == '__main__':
    sys.exit(main() or 0)