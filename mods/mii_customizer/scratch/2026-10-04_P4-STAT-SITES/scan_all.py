"""P4-STAT-SITES survey.

Extends the copied P2-STAT-READS scanner (stat_reads.py, report.py, d.py were
copied verbatim into this folder; the originals are untouched) to all stat
candidates recorded in evidence/P1-DATASET/gunner_catalog.json.

Locating task only.  For every catalogue hash it reports:
  * code-site count from the same movz/movk scanner and gap rule as P2,
  * data-site count (8-byte little-endian, and low-40-bits at 8-byte
    alignment),
  * for each code site: the first bl/blr after the completing movk inside the
    same 0x400-byte span P2 used, classified as indirect (target register
    produced by ldr xN,[xM,#D] -> report D), direct bl (report target), or
    none; for indirect sites also whether the base register xM came from
    `ldr xM,[x0]` with x0 loaded by displacement #0x50, and the immediate
    moved into x2 before the call if any.

Subcommands:
  validate  re-run the copied scanner self-test
  scan      write evidence/P4-STAT-SITES/sites.json and the tables
"""
import sys, json, struct, time
from pathlib import Path
import capstone

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
sys.path.insert(0, str(HERE))

from stat_reads import (load, TEXT, scan_sequences, scan_sequences_strict,
                        decode_movz, decode_movk, dest_regs, sx, disasm,
                        fstart, IMAGE, md)

CATALOGUE = MOD / 'evidence/P1-DATASET/gunner_catalog.json'
EV = MOD / 'evidence/P4-STAT-SITES'
EV.mkdir(parents=True, exist_ok=True)

MASK40 = (1 << 40) - 1
SPAN = 0x400          # same span P2-STAT-READS used
BACK_REG = 20         # same producer lookback P2 used
BACK_50 = 12          # instructions to look back for the [x0] / #0x50 chain

# --------------------------------------------------------------------- inputs
def catalogue_stats():
    """Stat candidates exactly as recorded: name, Hash40, type.  No additions."""
    cat = json.loads(CATALOGUE.read_text())
    out = []
    for s in cat['stat_candidates']:
        out.append({
            'stat_id': s['stat_id'],
            'name': s['parameter_name'],
            'hash_text': s['hash'],
            'hash': int(s['hash'], 16),
            'type': s['decoded_type'],
            'type_matches': s['type_matches'],
            'value_f32_bits': s.get('value_f32_bits'),
            'row_index': s['provenance']['row_index'],
        })
    return out


def data_hits(data, value):
    """Copied verbatim from stat_reads.py: raw 8-byte LE anywhere, and
    low-40-bits match at 8-byte alignment."""
    pat = struct.pack('<Q', value)
    raw, masked = [], []
    i = 0
    while True:
        i = data.find(pat, i)
        if i < 0:
            break
        raw.append(i)
        i += 1
    for off in range(0, len(data) - 8, 8):
        q = struct.unpack_from('<Q', data, off)[0]
        if (q & MASK40) == (value & MASK40):
            masked.append(off)
    return raw, masked


def data_hits_fast(data, value):
    """Same result as data_hits(), computed by searching the 5-byte low part
    and the zero 6th byte.  Used for speed; the check script verifies the two
    agree on every candidate hash."""
    assert value < (1 << 40)
    pat5 = struct.pack('<I', value & 0xFFFFFFFF) + bytes([(value >> 32) & 0xFF])
    masked = []
    i = 0
    while True:
        i = data.find(pat5, i)
        if i < 0:
            break
        if i % 8 == 0 and data[i + 5] == 0:
            masked.append(i)
        i += 1
    raw = []
    pat8 = struct.pack('<Q', value)
    i = 0
    while True:
        i = data.find(pat8, i)
        if i < 0:
            break
        raw.append(i)
        i += 1
    return sorted(raw), sorted(masked)

# ------------------------------------------------------------- instruction decode
def insn_text(data, a):
    ins = next(md.disasm(data[a:a + 4], a), None)
    return (ins.mnemonic + ' ' + ins.op_str).strip() if ins else '.word'


def is_ldr_imm64(word):
    """LDR Xt,[Xn,#imm] (unsigned scaled).  Returns (rt, rn, byte_off) or None."""
    if (word & 0xFFC00000) == 0xF9400000:
        return (word & 31, (word >> 5) & 31, ((word >> 10) & 0xFFF) * 8)
    if (word & 0xFFC00000) == 0xF8400000:      # LDUR Xt,[Xn,#imm]
        imm = (word >> 12) & 0x1FF
        if imm & 0x100:
            imm -= 0x200
        return (word & 31, (word >> 5) & 31, imm)
    return None


def is_mov_imm_to(word, reg):
    """MOVZ/MOV Xt or Wt, #imm16{,lsl #16}.  Returns the value or None."""
    mz = decode_movz(word)
    if mz is None:
        return None
    r, imm16, hw, sf = mz
    if r != reg:
        return None
    return imm16 << (16 * hw)


def writer_before(data, addr, reg, back):
    """Address of the closest instruction at or before addr that writes `reg`,
    scanning back at most `back` instructions.  None if not found."""
    for k in range(1, back + 1):
        a = addr - 4 * k
        if a < TEXT[0]:
            break
        if reg in dest_regs(struct.unpack_from('<I', data, a)[0]):
            return a
    return None


# --------------------------------------------------------------- classification
def first_call(data, start, limit):
    """First bl or blr at or after `start`, within `limit` bytes.
    Same span definition as P2-STAT-READS: start = completing movk + 4,
    limit = complete + 4 + 0x400."""
    n = (limit - start) // 4
    if n <= 0:
        return None
    words = struct.unpack_from('<%dI' % n, data, start)
    for i in range(n):
        w = words[i]
        a = start + 4 * i
        if (w & 0xFC000000) == 0x94000000:
            t = a + (sx(w & 0x3FFFFFF, 26) << 2)
            return {'kind': 'bl', 'addr': a, 'target': t}
        if (w & 0xFFFFFC1F) == 0xD63F0000:
            return {'kind': 'blr', 'addr': a, 'reg': (w >> 5) & 31}
    return None


def classify_site(data, hit):
    """Classify one code site by what follows it."""
    call = first_call(data, hit['complete_addr'] + 4,
                      hit['complete_addr'] + 4 + SPAN)
    out = {'site': hit['addr'], 'reg': 'x%d' % hit['reg'],
           'complete': hit['complete_addr']}
    if call is None:
        out['class'] = 'none'
        out['call'] = None
        return out

    out['call'] = {'kind': call['kind'], 'addr': call['addr']}
    if call['kind'] == 'bl':
        out['call']['target'] = call['target']
        out['class'] = 'direct_bl'
        out['displacement'] = None
        return out

    reg = call['reg']
    out['call']['reg'] = reg
    pa = writer_before(data, call['addr'], reg, BACK_REG)
    if pa is None:
        out['class'] = 'indirect_no_producer'
        out['producer'] = None
        out['displacement'] = None
        out['from_x0_chain'] = None
        out['x2_immediate'] = None
        return out
    pw = struct.unpack_from('<I', data, pa)[0]
    out['producer'] = {'addr': pa, 'text': insn_text(data, pa)}
    dec = is_ldr_imm64(pw)
    if dec is None:
        out['class'] = 'indirect_other_producer'
        out['displacement'] = None
    else:
        rt, rn, off = dec
        out['class'] = 'indirect'
        out['displacement'] = off
        out['producer']['base_reg'] = rn
        out['from_x0_chain'] = x0_chain(data, pa, rn)
    out['x2_immediate'] = x2_immediate_before(data, call['addr'])
    return out


def x0_chain(data, prod_addr, base_reg):
    """yes/no: was `base_reg` produced by `ldr xM,[x0]` and was x0 loaded with
    displacement #0x50 within the 12 instructions before?"""
    res = {'ldr_from_x0': False, 'x0_via_0x50': False,
           'ldr_from_x0_addr': None, 'ldr_x0_0x50_addr': None}
    ba = writer_before(data, prod_addr, base_reg, BACK_50)
    if ba is not None:
        w = struct.unpack_from('<I', data, ba)[0]
        dec = is_ldr_imm64(w)
        # ldr xM,[x0] exactly: base x0, zero displacement
        if dec is not None and dec[1] == 0 and dec[2] == 0:
            res['ldr_from_x0'] = True
            res['ldr_from_x0_addr'] = ba
            xa = writer_before(data, ba, 0, BACK_50)
            if xa is not None:
                w2 = struct.unpack_from('<I', data, xa)[0]
                d2 = is_ldr_imm64(w2)
                if d2 is not None and d2[0] == 0 and d2[2] == 0x50:
                    res['x0_via_0x50'] = True
                    res['ldr_x0_0x50_addr'] = xa
    return res


def x2_immediate_before(data, call_addr, back=8):
    """The closest instruction before the call that writes x2, with the value
    it moved in when that value is an immediate.  `mov x2, xzr` is encoded as
    `orr x2, xzr, xzr` and is reported as value 0; a register move is reported
    with value null.  None if x2 is not written in the lookback."""
    for k in range(1, back + 1):
        a = call_addr - 4 * k
        if a < TEXT[0]:
            break
        w = struct.unpack_from('<I', data, a)[0]
        if 2 not in dest_regs(w):
            continue
        v = is_mov_imm_to(w, 2)
        if v is None and (w & 0xFF200000) == 0xAA000000 and w & 31 == 2                 and ((w >> 5) & 31) == 31 and ((w >> 16) & 31) == 31:
            v = 0          # mov x2, xzr
        return {'addr': a, 'text': insn_text(data, a), 'value': v,
                'immediate': v is not None}
    return None


# ------------------------------------------------------------------------ main
def run_validate():
    """The copied scanner's own self-test, unchanged."""
    import stat_reads
    return stat_reads.run_validate()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'scan'
    if cmd == 'validate':
        return run_validate()
    stats = catalogue_stats()
    t0 = time.time()
    data = load()
    t_load = time.time() - t0

    targets = [s['hash'] for s in stats]
    t0 = time.time()
    hits = scan_sequences(data, targets, TEXT[0], TEXT[1], max_gap=4)
    t_scan = time.time() - t0
    t0 = time.time()
    strict = scan_sequences_strict(data, targets, TEXT[0], TEXT[1], max_gap=4)
    t_strict = time.time() - t0

    by_hash = {}
    for h in hits:
        by_hash.setdefault(h['value'], []).append(h)
    strict_by_hash = {}
    for h in strict:
        strict_by_hash.setdefault(h['value'], []).append(h)

    report = {
        'image': 'gamedata/ssbu-13.0.4/main.bin',
        'code_range': [hex(TEXT[0]), hex(TEXT[1])],
        'catalogue': 'evidence/P1-DATASET/gunner_catalog.json',
        'candidates': len(stats),
        'timing_seconds': {'load': round(t_load, 1),
                           'scan_primary': round(t_scan, 1),
                           'scan_strict': round(t_strict, 1)},
        'stats': {},
    }

    for s in stats:
        v = s['hash']
        hs = by_hash.get(v, [])
        ss = strict_by_hash.get(v, [])
        raw, masked = data_hits_fast(data, v)
        sites = []
        for h in hs:
            c = classify_site(data, h)
            c['seq'] = [hex(i['addr']) for i in h['insns']]
            c['fstart'] = fstart(data, h['addr'])
            sites.append(c)
        disp = {}
        for c in sites:
            k = c.get('displacement')
            k = 'none' if k is None else hex(k)
            disp[k] = disp.get(k, 0) + 1
        classes = {}
        for c in sites:
            classes[c['class']] = classes.get(c['class'], 0) + 1
        report['stats'][s['name']] = {
            'stat_id': s['stat_id'],
            'hash': s['hash_text'],
            'hash_value': v,
            'type': s['type'],
            'type_matches': s['type_matches'],
            'value_f32_bits': s['value_f32_bits'],
            'code_sites': len(hs),
            'code_sites_strict': len(ss),
            'scanners_agree': sorted(h['addr'] for h in hs) ==
                              sorted(h['addr'] for h in ss),
            'data_sites_raw': len(raw),
            'data_sites_masked': len(masked),
            'data_offsets_raw': [hex(o) for o in raw[:64]],
            'data_offsets_masked': [hex(o) for o in masked[:64]],
            'classes': classes,
            'displacements': disp,
            'via_0x270': disp.get('0x270', 0),
            'via_0x250': disp.get('0x250', 0),
            'via_0x260': disp.get('0x260', 0),
            'other_displacement': sum(n for k, n in disp.items()
                                      if k not in ('0x270', '0x250', '0x260',
                                                   'none')),
            'direct_bl': classes.get('direct_bl', 0),
            'none': classes.get('none', 0),
            'from_x0_chain_yes': sum(
                1 for c in sites
                if c.get('from_x0_chain') and c['from_x0_chain']['x0_via_0x50']),
            'sites': sites,
        }

    # Example windows: one per distinct (class, displacement) pair, written to
    # evidence/P4-STAT-SITES/win_*.txt so the report can quote five of them.
    BEFORE, AFTER = 12, 20
    examples = []
    seen = set()
    for st in stats:
        for c in report['stats'][st['name']]['sites']:
            key = (c['class'], c.get('displacement'))
            if key in seen:
                continue
            seen.add(key)
            lo = c['site'] - 4 * BEFORE
            hi = c['site'] + 4 * AFTER
            win = disasm(data, lo, (hi - lo) // 4)
            d = c.get('displacement')
            path = EV / ('win_%s_%08x.txt' % (st['name'], c['site']))
            with open(path, 'w') as f:
                f.write('# %s %s site 0x%08x reg %s completes 0x%08x\n'
                        % (st['name'], st['hash_text'], c['site'], c['reg'],
                           c['complete']))
                f.write('# class %s  displacement %s\n'
                        % (c['class'], hex(d) if d is not None else 'none'))
                f.write('# first call after 0x%08x: %s\n'
                        % (c['complete'] + 4, json.dumps(c['call'])))
                f.write('# producer: %s\n' % json.dumps(c.get('producer')))
                f.write('# x0 chain: %s\n' % json.dumps(c.get('from_x0_chain')))
                f.write('# x2 before call: %s\n'
                        % json.dumps(c.get('x2_immediate')))
                f.write('# %d instructions before, %d after\n'
                        % (BEFORE, AFTER))
                for i in win:
                    mark = ''
                    if i['addr'] == c['site']:
                        mark = '   <== movz seed'
                    elif i['addr'] == c['complete']:
                        mark = '   <== completes hash'
                    f.write('0x%08x: %s%s\n' % (i['addr'], i['text'], mark))
            examples.append({'stat': st['name'], 'site': c['site'],
                             'file': path.name, 'class': c['class'],
                             'displacement': d})
    report['example_windows'] = examples
    with open(EV / 'examples.json', 'w') as f:
        json.dump(examples, f, indent=1, default=str)

    with open(EV / 'sites.json', 'w') as f:
        json.dump(report, f, indent=1, default=str)

    print('image load %.1fs  primary %.1fs  strict %.1fs' %
          (t_load, t_scan, t_strict))
    print('candidates: %d' % len(stats))
    for s in stats:
        r = report['stats'][s['name']]
        print('%-18s %-12s %-6s code=%-4d strict=%-4d data_raw=%-3d '
              'data_masked=%-3d  %s' %
              (s['name'], s['hash_text'], s['type'], r['code_sites'],
               r['code_sites_strict'], r['data_sites_raw'],
               r['data_sites_masked'],
               ' '.join('%s=%d' % (k, v) for k, v in
                        sorted(r['displacements'].items()))))
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
