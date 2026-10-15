"""List every (status kind, condition, function) a lua2cpp fighter NRO registers via sv_set_status_func.

Usage: python status_table.py <flat.bin> <labels.json>     (inputs from nro_flatten.py)
Output lines: `<STATUS_KIND const> <LUA_SCRIPT_STATUS_FUNC_* const> <function address in the NRO>`.

Method: find the PLT stub of `L2CAgentBase::sv_set_status_func`, walk the function that calls it,
and pair each call with the two `ldr w1, [table, #off | x8]` constant loads before it and the
`adrp/add x3` function pointer. Constant names come from lua2cpp_common's const table (nro_util.const_name).
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import nro_util as u

SV = '_ZN7lua2cpp12L2CAgentBase18sv_set_status_funcERKN3lib8L2CValueES4_Pv'


def table(img, meta):
    plt = u.plt_map(img, meta['labels'], meta['text_end'])
    sv = [a for a, n in plt.items() if n == SV]
    assert len(sv) == 1, 'sv_set_status_func PLT stub not found'
    sv = sv[0]
    # all calls sit in one registering function; walk from just before the first to just after the last
    callers = u.bl_callers(img, meta['text_end'], sv)
    assert callers, 'no caller of sv_set_status_func'
    rows, w1, regs = [], [], {}
    for ins in u.disasm(img, callers[0] - 0x80, callers[-1] - callers[0] + 0x100):
        m, ops = ins.mnemonic, ins.op_str
        if ins.address < callers[0] - 0x80: continue
        if m == 'mov' and ops.startswith('w8, #'):
            regs['w8'] = int(ops.split('#')[1], 0)
        elif m == 'ldr' and ops.startswith('w1,'):
            mm = re.search(r'#(0x[0-9a-f]+|\d+)\]', ops)
            w1.append(regs.get('w8', -1) if ops.endswith('x8]') else (int(mm.group(1), 0) if mm else 0))
        elif m in ('adrp', 'adr'):
            r, v = ops.split(', #'); regs[r] = int(v, 0)
        elif m == 'add' and ops.count('#') == 1:
            p = [x.strip() for x in ops.split(',')]
            if p[1] in regs: regs[p[0]] = regs[p[1]] + int(p[2].lstrip('#'), 0)
        elif m == 'bl' and int(ops.lstrip('#'), 0) == sv:
            st, co = w1[-2:]
            rows.append((u.const_name(st) or hex(st), u.const_name(co) or hex(co), regs.get('x3', -1)))
    return rows


if __name__ == '__main__':
    img = open(sys.argv[1], 'rb').read(); meta = json.load(open(sys.argv[2]))
    for st, co, fn in table(img, meta):
        print(st, co, hex(fn))
