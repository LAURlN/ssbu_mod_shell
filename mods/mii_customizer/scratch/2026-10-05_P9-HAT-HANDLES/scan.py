"""P9-HAT-HANDLES: walk a TEXT address range, split it into functions by prologue
heuristics, and report per-function which of a set of immediate offsets are
touched by ldr/str/ldp/stp (unsigned-offset forms only).

  PYTHONPATH=... python scan.py 0x19c1e00 0x19d0000 0x128 0x130 0x138 0x150 0x158 0x164 0x169

Prologue detection: an instruction that writes sp as `stp x29,x30,[sp,#-N]!`,
`str x19,[sp,#-N]!`, `sub sp,sp,#N` followed by a stack push, etc.
"""
import struct
import sys
from pathlib import Path

import capstone
import capstone.arm64 as arm64

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
TEXT = (0x100, 0x39C8000)
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md.detail = True


def dis(a, n=1):
    return list(md.disasm(data[a:a + 4 * n], a))[:n]


def is_prologue(ins):
    if ins.mnemonic == 'sub' and ins.op_str.startswith('sp, sp,'):
        return True
    if ins.mnemonic in ('stp', 'str') and '[sp, #-' in ins.op_str and ins.op_str.endswith('!'):
        return True
    if ins.mnemonic == 'stp' and ins.op_str.endswith('[sp]') and 'x29, x30' in ins.op_str:
        return True
    if ins.mnemonic == 'str' and ins.op_str.endswith('[sp]') and ins.op_str.startswith(('x19', 'x20', 'x21', 'x22', 'x23', 'x24', 'x25', 'x26', 'x27', 'x28')):
        return True
    return False


def mem_offsets(ins):
    """Return list of unsigned mem displacements touched by a load/store."""
    out = []
    for op in ins.operands:
        if op.type != arm64.ARM64_OP_MEM:
            continue
        m = op.mem
        if m.index == 0 and m.disp >= 0:
            out.append(m.disp)
    return out


def main():
    lo = int(sys.argv[1], 16)
    hi = int(sys.argv[2], 16)
    want = {int(x, 16) for x in sys.argv[3:]}
    funcs = []
    cur = None
    for a in range(lo, hi, 4):
        insl = dis(a, 1)
        ins = insl[0] if insl else None
        if ins is None:
            continue
        if cur is None:
            cur = [a, None, {}]  # start, end, offset->count
        for o in mem_offsets(ins):
            if o in want:
                cur[2][o] = cur[2].get(o, 0) + 1
        if is_prologue(ins):
            if cur[2]:
                funcs.append(cur)
            cur = [a, None, {}]
        else:
            cur[1] = a
    if cur[2]:
        funcs.append(cur)

    for start, end, hits in funcs:
        offs = ' '.join('0x%x:%d' % (o, c) for o, c in sorted(hits.items()))
        print('fn 0x%08x .. 0x%08x  %s' % (start, (end or start) + 4, offs))


if __name__ == '__main__':
    main()