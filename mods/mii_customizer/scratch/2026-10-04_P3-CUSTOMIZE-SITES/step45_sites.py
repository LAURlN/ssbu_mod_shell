"""P3-CUSTOMIZE-SITES steps 4-6: per-site windows, argument provenance, enclosing
function candidates and their direct callers.

Reads 06_step3_sites.json (produced by step3_scan.py) and the image, and writes:
  07_site_windows.txt      raw 24-before/8-after window for every kept site
  08_step45_sites.json     machine readable provenance / loop / function data

Nothing is written to the current directory.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python step45_sites.py
"""
import json
from array import array
from pathlib import Path

import capstone.arm64 as arm64

import lib
from lib import TEXT, dis, ldr_imm, branch_reg, written, text, last_prologue_at_or_before

HERE = Path(__file__).resolve().parent
EV = HERE.parents[1] / 'evidence/P3-CUSTOMIZE-SITES'

BEFORE, AFTER = 24, 8
LOOP_UP, LOOP_DOWN = 400, 200     # instructions above/below the call searched for loops
MAX_DEPTH = 6                     # register-following depth for provenance


def win(call, before=BEFORE, after=AFTER):
    lo = max(TEXT[0], call - 4 * before)
    n = before + after + 1
    return [(a, i) for a, i in zip(range(lo, lo + 4 * n, 4), dis(lo, n))]


def regof(ins, i):
    o = ins.operands
    if i < len(o) and o[i].type == arm64.ARM64_OP_REG:
        n = ins.reg_name(o[i].reg)
        if n and n[0] in 'xw' and n[1:].isdigit():
            return int(n[1:])
    return None


def uncond_target(ins):
    """Target of an unconditional b/bl, else None. Returns (target, kind)."""
    if ins.mnemonic not in ('b', 'bl'):
        return None
    o = ins.operands
    if o and o[0].type == arm64.ARM64_OP_IMM:
        return o[0].imm
    return None


def boundary_between(items, i, callidx):
    """First unconditional control transfer strictly between items[i] and the call.

    Returns None, or (addr, mnemonic, target_or_None, 'passes'|'blocks').
    'passes' means the transfer's static target lies inside the span, so the path
    from items[i] to the call is still statically contiguous; 'blocks' means the
    path cannot be shown from the image alone (ret, or an indirect br).
    """
    for j in range(i + 1, callidx):
        a, ins = items[j]
        t = uncond_target(ins)
        if t is not None:
            if items[i][0] < t <= items[callidx][0]:
                return (a, ins.mnemonic, t, 'passes')
            return (a, ins.mnemonic, t, 'blocks')
        if ins.mnemonic == 'ret':
            return (a, 'ret', None, 'blocks')
        if ins.mnemonic == 'br':
            return (a, 'br', None, 'blocks')
    return None


def resolve(items, callidx, reg, depth=0, seen=None):
    """Follow the nearest in-window definition of `reg` backwards from items[callidx]."""
    seen = seen or set()
    if depth > MAX_DEPTH:
        return ['provenance leaves the window (follow depth limit %d)' % MAX_DEPTH]
    if reg in seen:
        return ['provenance leaves the window (re-enters a register already followed)']
    seen = seen | {reg}
    idx = None
    for j in range(callidx - 1, -1, -1):
        if reg in written(items[j][1]):
            idx = j
            break
    if idx is None:
        return ['x%d/w%d is NOT written by any instruction in the %d-instruction '
                'window 0x%08x..0x%08x; the value at the call is whatever entered the '
                'enclosing entry point with (argument register)'
                % (reg, reg, BEFORE, items[0][0], items[-1][0])]
    a, ins = items[idx]
    steps = ['0x%08x: %s %s   <- nearest definition of x%d/w%d'
             % (a, ins.mnemonic, ins.op_str, reg, reg)]
    b = boundary_between(items, idx, callidx)
    if b is not None and b[3] == 'blocks':
        steps.append('  BLOCK BOUNDARY: %s at 0x%08x (%s%s) lies between this '
                     'definition and the call, so control does not reach the call '
                     'from here by any path visible in this window'
                     % (b[1], b[0], b[1] if b[2] is None else 'to 0x%x' % b[2], ''))
        steps.append('  provenance leaves the window')
        return steps
    if b is not None:
        steps.append('  path continues through %s at 0x%08x -> 0x%08x (target lies '
                     'between the definition and the call)'
                     % (b[1], b[0], b[2]))

    l = ldr_imm(ins)
    if l is not None:
        width, rt, rn, disp = l
        steps.append('  LOAD: base register x%d, displacement 0x%x%s'
                     % (rn, disp, '' if width == 64 else ' (32-bit ldr)'))
        bidx = None
        for j in range(idx - 1, -1, -1):
            if rn in written(items[j][1]):
                bidx = j
                break
        if bidx is None:
            steps.append('  base x%d is not defined earlier in the window '
                         '(window starts at 0x%08x)' % (rn, items[0][0]))
            steps.append('  provenance leaves the window')
        else:
            steps += ['  ' + s for s in resolve(items, bidx + 1, rn, depth + 1, seen)]
        return steps

    if ins.mnemonic in ('movz', 'movn', 'adr', 'adrp'):
        steps.append('  IMMEDIATE %s' % ins.op_str)
        return steps
    srcs = [ins.reg_name(o.reg) for o in ins.operands
            if o.type == arm64.ARM64_OP_REG]
    if any(s in ('wzr', 'xzr') for s in srcs[1:]):
        steps.append('  IMMEDIATE 0 (source is the zero register)')
        return steps
    src = regof(ins, 1)
    if src is not None and ins.mnemonic not in ('cmp', 'add', 'sub'):
        steps.append('  register move from %s'
                     % ('x%d' % src if ins.op_str.split(',')[0].strip()[0] == 'x'
                        else 'w%d' % src))
        steps += ['  ' + t for t in resolve(items, idx, src, depth + 1, seen)]
        return steps
    steps.append('  arithmetic / other instruction: provenance not followed past '
                 'this one (locating task; instruction printed above)')
    return steps


def cmp_imms(items):
    """[(addr, text, reg, imm)] for every `cmp <reg>, #imm` in the sequence."""
    out = []
    for a, ins in items:
        if ins.mnemonic != 'cmp':
            continue
        o = ins.operands
        if len(o) == 2 and o[1].type == arm64.ARM64_OP_IMM:
            out.append((a, '%s %s' % (ins.mnemonic, ins.op_str), regof(ins, 0), o[1].imm))
    return out


def loops_containing(call):
    """Every backward `b`/`bl` whose loop body [target, branch] contains `call`."""
    lo = max(TEXT[0], call - 4 * LOOP_UP)
    hi = min(len(lib.data) - 4, call + 4 * LOOP_DOWN)
    region = [(a, i) for a, i in zip(range(lo, hi + 4, 4), dis(lo, (hi - lo) // 4 + 1))]
    out = []
    for a, ins in region:
        t = uncond_target(ins)
        if t is None or t >= a:
            continue
        if not (t <= call <= a):
            continue
        body = [(aa, ii) for aa, ii in dis(t, (a - t) // 4 + 1)]
        body = [(t + 4 * k, ii) for k, ii in enumerate(body)]
        out.append({'branch': '0x%08x: %s %s' % (a, ins.mnemonic, ins.op_str),
                    'loop_start': '0x%08x' % t,
                    'body_instrs': (a - t) // 4 + 1,
                    'cmp_immediates': [{'addr': hex(ca), 'text': ct, 'reg': cr, 'imm': ci}
                                       for ca, ct, cr, ci in cmp_imms(body)]})
    return out


def bl_callers(starts):
    """One pass over TEXT collecting direct bl/b callers of each address in `starts`."""
    want = set(starts)
    out = {s: [] for s in starts}
    if not want:
        return out
    words = array('I')
    words.frombytes(lib.data[TEXT[0]:TEXT[1]])
    sx = lib.sx
    for i, w in enumerate(words):
        if (w & 0xFC000000) != 0x94000000:
            continue
        a = TEXT[0] + 4 * i
        t = a + (sx(w & 0x3FFFFFF, 26) << 2)
        if t in want:
            out[t].append((a, 'bl' if w >> 31 else 'b'))
    return out


if __name__ == '__main__':
    sites = json.loads((EV / '06_step3_sites.json').read_text(encoding='utf-8'))
    kept = sites['kept']
    print('capstone %s; kept sites: %d' % (lib.CAPSTONE_VERSION, len(kept)))

    lines, result = [], []
    for s in kept:
        call = s['call']
        items = win(call)
        ci = next(i for i, (a, _) in enumerate(items) if a == call)
        lines.append('=' * 78)
        lines.append('SITE  ldr x%d,[x%d,#0x278] at 0x%08x   call %s x%d at 0x%08x'
                     % (s['reg_call'], s['reg_vt'], s['ldr'], s['call_kind'],
                        s['reg_call'], call))
        lines.append('  vtable load: %s' % text(s['vtable_load']))
        lines.append('  displacement-0x50 load of x%d: %s'
                     % (s['reg_ptr'], text(s['base_of_0x50'])))
        lines.append('  window 0x%08x..0x%08x (%d before, %d after the call)'
                     % (items[0][0], items[-1][0], BEFORE, AFTER))
        for a, ins in items:
            mark = '   <<< call' if a == call else (
                '   <<< ldr #0x278' if a == s['ldr'] else '')
            lines.append('    0x%08x: %s %s%s' % (a, ins.mnemonic, ins.op_str, mark))
        rec = {'ldr': s['ldr'], 'call': call, 'call_kind': s['call_kind'],
               'reg_call': s['reg_call'], 'reg_vt': s['reg_vt'],
               'reg_ptr': s['reg_ptr'], 'vtable_load': s['vtable_load'],
               'base_of_0x50': s['base_of_0x50'],
               'window': {'start': items[0][0], 'end': items[-1][0],
                          'before': BEFORE, 'after': AFTER}}
        for name, r in (('w1', 1), ('w2', 2)):
            lines.append('')
            lines.append('  %s provenance (backward, inside the window):' % name)
            st = resolve(items, ci, r)
            lines += ['    ' + x for x in st]
            rec[name] = st
        loops = loops_containing(call)
        lines.append('')
        lines.append('  loops whose body contains the call (backward b/bl in the '
                     'range call-%d .. call+%d instructions):'
                     % (LOOP_UP, LOOP_DOWN))
        if not loops:
            lines.append('    NONE')
        for L in loops:
            lines.append('    %s, body starts %s, %d instructions'
                         % (L['branch'], L['loop_start'], L['body_instrs']))
            if not L['cmp_immediates']:
                lines.append('      no `cmp <reg>, #imm` anywhere in that loop body')
            for c in L['cmp_immediates']:
                note = ''
                if c['imm'] in (2, 3, 4):
                    note = ('   <-- count bound: 0..%d' % (c['imm'] - 1)) \
                        if c['imm'] in (3, 4) else '   <-- bound #2'
                lines.append('      %s: %s%s' % (c['addr'], c['text'], note))
        rec['loops'] = loops
        fs = last_prologue_at_or_before(call)
        rec['prologue_candidate'] = fs
        rec['prologue_text'] = text(fs) if fs else None
        # does the candidate's own function end before the site?  count `ret`
        rets = []
        if fs:
            for a2 in range(fs, call, 4):
                t2 = text(a2)
                if t2 and t2.startswith('ret'):
                    rets.append(a2)
        rec['rets_between_candidate_and_site'] = rets
        lines.append('')
        lines.append('  nearest prologue candidate at or above the call: %s (%s)'
                     % (hex(fs) if fs else 'none', text(fs) if fs else '-'))
        lines.append('  `ret` instructions between that candidate and the call: %s'
                     % ([hex(x) for x in rets] if rets else 'none'))
        result.append(rec)

    starts = sorted({r['prologue_candidate'] for r in result if r['prologue_candidate']})
    callers = bl_callers(starts)
    lines.append('')
    lines.append('direct bl/b callers of each prologue candidate (single pass over '
                 'TEXT 0x%x..0x%x)' % (TEXT[0], TEXT[1]))
    for r in result:
        fs = r['prologue_candidate']
        cl = callers.get(fs, []) if fs else []
        r['caller_count'] = len(cl)
        r['callers'] = [a for a, _ in cl[:10]]
        lines.append('  0x%08x: %d direct bl/b callers; first 10: %s'
                     % (fs, len(cl), [hex(a) for a, _ in cl[:10]]))

    (EV / '07_site_windows.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (EV / '08_step45_sites.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
    print('\n'.join(lines))
    print('\nwrote %s and %s' % ((EV / '07_site_windows.txt').as_posix(),
                                 (EV / '08_step45_sites.json').as_posix()))