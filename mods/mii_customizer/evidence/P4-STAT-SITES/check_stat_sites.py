"""P4-STAT-SITES check script.

Re-derives every count and every per-site classification claimed in
research/P4-STAT-SITES.md directly from gamedata/ssbu-13.0.4/main.bin and
exits nonzero on any mismatch.

Deliberately does NOT import scan_all.py.  The movz/movk rule from
research/P2-STAT-READS.md section 1 is re-implemented here twice, in two
different shapes (a per-seed scanner and a forward per-register dataflow
scanner), the data search is written separately, and the first-call search and
the displacement decode are re-derived, so a shared bug cannot hide.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
    python mods/mii_customizer/evidence/P4-STAT-SITES/check_stat_sites.py

Runtime: about 2 minutes (whole-code-range scans in pure Python).
"""
import sys, re, json, struct, hashlib, time
from pathlib import Path
import capstone

ROOT = Path(__file__).resolve().parents[4]
IMAGE = ROOT / 'gamedata/ssbu-13.0.4/main.bin'
MOD = ROOT / 'mods/mii_customizer'
REPORT = MOD / 'research/P4-STAT-SITES.md'
SITES = MOD / 'evidence/P4-STAT-SITES/sites.json'
CATALOGUE = MOD / 'evidence/P1-DATASET/gunner_catalog.json'

TEXT = (0x100, 0x39C8000)
SPAN = 0x400            # P2-STAT-READS "first call after" span
BACK_REG = 20           # P2-STAT-READS producer lookback
BACK_50 = 12            # lookback for the [x0] / #0x50 chain
MAX_GAP = 4             # P2-STAT-READS gap rule
MASK40 = (1 << 40) - 1
EXPECTED_SHA256 = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'

# Control counts published by research/P2-STAT-READS.md.  If the survey does not
# reproduce them the method has drifted and the comparison is not valid.
CONTROL = {'weight': 37, 'walk_speed_max': 18}

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md.detail = True
_VCACHE = {}


# ----------------------------------------------------------------- primitives
def sx(v, b):
    return v - (1 << b) if v & (1 << (b - 1)) else v


def dec_movz(w):
    if (w & 0xFF800000) == 0xD2800000:
        sf = 1
    elif (w & 0xFF800000) == 0x52800000:
        sf = 0
    else:
        return None
    return (w & 31, (w >> 5) & 0xFFFF, (w >> 21) & 3, sf)


def dec_movk(w):
    if (w & 0xFF800000) == 0xF2800000:
        sf = 1
    elif (w & 0xFF800000) == 0x72800000:
        sf = 0
    else:
        return None
    return (w & 31, (w >> 5) & 0xFFFF, (w >> 21) & 3, sf)


def dest(w):
    """Registers written by one instruction word.  Cached; bl/blr get the ABI
    caller-saved set added because capstone reports only the link register."""
    hit = _VCACHE.get(w)
    if hit is not None:
        return hit
    out = set()
    try:
        ins = next(md.disasm(struct.pack('<I', w), 0), None)
        if ins is not None:
            _, wr = ins.regs_access()
            for r in wr:
                nm = ins.reg_name(r)
                if nm and nm[0] in 'xw' and nm[1:].isdigit():
                    out.add(int(nm[1:]))
            if ins.mnemonic in ('bl', 'blr'):
                out |= set(range(0, 19))
    except capstone.CsError:
        out = set(range(0, 31))
    _VCACHE[w] = out
    return out


def scan_seeds(data, targets):
    """Per-seed composition scan: start at every MOVZ and extend the value with
    MOVKs on the same register, allowing at most MAX_GAP intervening
    instructions that do not write the register."""
    targets = set(targets)
    n = (TEXT[1] - TEXT[0]) // 4
    words = struct.unpack_from('<%dI' % n, data, TEXT[0])
    hits = []
    for i in range(n):
        mz = dec_movz(words[i])
        if mz is None:
            continue
        reg, imm, hw, sf = mz
        val = imm << (16 * hw)
        gap = 0
        comp = None
        for j in range(i + 1, min(n, i + 13)):
            w = words[j]
            mk = dec_movk(w)
            mz2 = dec_movz(w)
            if mk is not None and mk[0] == reg and mk[3] == sf:
                val = (val & ~(0xFFFF << (16 * mk[2]))) | (mk[1] << (16 * mk[2]))
                gap = 0
                comp = TEXT[0] + 4 * j
            elif mz2 is not None and mz2[0] == reg and mz2[3] == sf:
                break
            else:
                if reg in dest(w):
                    break
                gap += 1
                if gap > MAX_GAP:
                    break
                continue
            if val in targets:
                hits.append({'site': TEXT[0] + 4 * i, 'value': val,
                             'complete': comp, 'reg': reg})
                break
    return hits


def scan_dataflow(data, value):
    """Forward per-register dataflow form of the same rule, written
    independently of scan_seeds: one live partial value per register, extended
    by a MOVK within MAX_GAP instructions, killed by any other write to that
    register or once the gap is exceeded.  Returns the seed addresses."""
    n = (TEXT[1] - TEXT[0]) // 4
    words = struct.unpack_from('<%dI' % n, data, TEXT[0])
    # live[reg] = [value, sf, index_of_last_composing_insn, seed_index]
    live = {}
    found = []
    for i in range(n):
        w = words[i]
        d = dest(w)
        for r in [k for k in live if k in d and not dec_movz(w)
                  and not dec_movk(w)]:
            del live[r]
        for r in [k for k in live if i - live[k][2] > MAX_GAP + 1]:
            del live[r]
        mz = dec_movz(w)
        mk = dec_movk(w)
        if mz is not None:
            live[mz[0]] = [mz[1] << (16 * mz[2]), mz[3], i, i]
            continue
        if mk is not None:
            r, imm, hw, sf = mk
            e = live.get(r)
            if e is not None and e[1] == sf:
                val = (e[0] & ~(0xFFFF << (16 * hw))) | (imm << (16 * hw))
                live[r] = [val, sf, i, e[3]]
                if val == value:
                    # report the movz seed address, as scan_seeds does
                    found.append(TEXT[0] + 4 * e[3])
            else:
                live.pop(r, None)
    return found


def data_sites(data, value):
    """Raw 8-byte little-endian match at any offset, plus the low-40-bits match
    at 8-byte alignment.  The aligned search locates candidates by the five
    low bytes and the zero sixth byte, then reads the qword back and tests the
    mask, so the reported offsets are verified against the image."""
    raw, masked = [], []
    pat8 = struct.pack('<Q', value)
    i = 0
    while True:
        i = data.find(pat8, i)
        if i < 0:
            break
        raw.append(i)
        i += 1
    pat5 = struct.pack('<I', value & 0xFFFFFFFF) + \
        bytes([(value >> 32) & 0xFF])
    i = 0
    while True:
        i = data.find(pat5, i)
        if i < 0:
            break
        if i % 8 == 0 and (struct.unpack_from('<Q', data, i)[0] & MASK40) \
                == (value & MASK40):
            masked.append(i)
        i += 1
    return sorted(raw), sorted(masked)


def writer_before(data, addr, reg, back):
    for k in range(1, back + 1):
        a = addr - 4 * k
        if a < TEXT[0]:
            break
        if reg in dest(struct.unpack_from('<I', data, a)[0]):
            return a
    return None


def ldr_imm(word):
    """(rt, rn, byte displacement) for LDR/LDUR Xt,[Xn,#imm], else None."""
    if (word & 0xFFC00000) == 0xF9400000:
        return (word & 31, (word >> 5) & 31, ((word >> 10) & 0xFFF) * 8)
    if (word & 0xFFC00000) == 0xF8400000:
        imm = (word >> 12) & 0x1FF
        if imm & 0x100:
            imm -= 0x200
        return (word & 31, (word >> 5) & 31, imm)
    return None


def x2_before(data, call_addr, back=8):
    """Value moved into x2 by the closest x2-writing instruction before the
    call, when that instruction moves an immediate; None otherwise."""
    for k in range(1, back + 1):
        a = call_addr - 4 * k
        if a < TEXT[0]:
            break
        w = struct.unpack_from('<I', data, a)[0]
        if 2 not in dest(w):
            continue
        mz = dec_movz(w)
        if mz is not None and mz[0] == 2:
            return mz[1] << (16 * mz[2])
        if (w & 0xFF200000) == 0xAA000000 and w & 31 == 2 and \
                ((w >> 5) & 31) == 31 and ((w >> 16) & 31) == 31:
            return 0            # mov x2, xzr
        return None
    return None


def classify(data, site, complete):
    """Re-derives class, displacement, the [x0]/#0x50 chain and the x2 value
    for one code site, using P2's span and lookback definitions."""
    start = complete + 4
    words = struct.unpack_from('<%dI' % (SPAN // 4), data, start)
    call = None
    for i in range(len(words)):
        w = words[i]
        a = start + 4 * i
        if (w & 0xFC000000) == 0x94000000:
            call = ('bl', a, None)
            break
        if (w & 0xFFFFFC1F) == 0xD63F0000:
            call = ('blr', a, (w >> 5) & 31)
            break
    if call is None:
        return {'class': 'none', 'disp': None, 'chain': False, 'x2': None}
    if call[0] == 'bl':
        return {'class': 'direct_bl', 'disp': None, 'chain': False,
                'x2': None}
    reg = call[2]
    pa = writer_before(data, call[1], reg, BACK_REG)
    if pa is None:
        return {'class': 'indirect_no_producer', 'disp': None,
                'chain': False, 'x2': None}
    dec = ldr_imm(struct.unpack_from('<I', data, pa)[0])
    if dec is None:
        return {'class': 'indirect_other_producer', 'disp': None,
                'chain': False, 'x2': x2_before(data, call[1])}
    rn = dec[1]
    chain = False
    ba = writer_before(data, pa, rn, BACK_50)
    if ba is not None:
        d2 = ldr_imm(struct.unpack_from('<I', data, ba)[0])
        if d2 is not None and d2[1] == 0 and d2[2] == 0:
            xa = writer_before(data, ba, 0, BACK_50)
            if xa is not None:
                d3 = ldr_imm(struct.unpack_from('<I', data, xa)[0])
                chain = d3 is not None and d3[0] == 0 and d3[2] == 0x50
    return {'class': 'indirect', 'disp': dec[2], 'chain': chain,
            'x2': x2_before(data, call[1])}


# --------------------------------------------------------------------- checks
class Checker:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def __call__(self, label, cond, detail=''):
        if cond:
            self.passed += 1
        else:
            self.failed += 1
            print('FAIL %s  %s' % (label, detail))
        return cond


def split_sentences(text):
    """Split into sentences and lines without regex escape sequences."""
    parts = []
    for line in text.splitlines():
        buf = ''
        for ch in line:
            buf += ch
            if ch in '.!?':
                parts.append(buf)
                buf = ''
        if buf.strip():
            parts.append(buf)
    return parts


def overall_table_rows(text):
    rows, collecting = [], False
    for line in text.splitlines():
        if line.startswith('| stat | type in the catalogue |'):
            collecting = True
            continue
        if not collecting:
            continue
        if line.startswith('|---'):
            continue
        if not line.startswith('|'):
            break
        rows.append([c.strip() for c in line.strip('|').split('|')])
    return rows


# Terms that would amount to interpretation, a ranking or a recommendation.
# The report must not contain any of them.  Sentences that explicitly disclaim
# those things are allowed to name them ("no recommendation is offered"), so the
# check looks for a use that is not inside a disclaimer sentence.
BANNED = ['knockback', 'floatiness', 'terminal velocity', 'terminal-style',
          'best stat', 'easiest to', 'highest priority', 'we recommend',
          'it is recommended', 'should be made editable',
          'should be made adjustable', 'candidate to make editable']
DISCLAIMER = ['no recommendation', 'not a recommendation',
              'no ranking', 'not a ranking', 'no such ranking',
              'nothing here indicates', 'does not recommend',
              'no priority', 'nothing is named', 'no function purpose',
              'makes no claim', 'no claim is made']


def main():
    ck = Checker()
    t0 = time.time()

    h = hashlib.sha256()
    with open(IMAGE, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    ck('input sha256 matches the prompt value',
       h.hexdigest() == EXPECTED_SHA256, h.hexdigest())

    stats = json.loads(CATALOGUE.read_text())['stat_candidates']
    ck('catalogue holds exactly 12 stat candidates', len(stats) == 12,
       str(len(stats)))
    targets = {}
    for s in stats:
        ck('catalogue hash for %s is a 10-digit hex Hash40' %
           s['parameter_name'],
           re.fullmatch(r'0x[0-9a-f]{10}', s['hash']) is not None, s['hash'])
        targets[s['parameter_name']] = int(s['hash'], 16)
    ck('the 12 catalogue hashes are distinct',
       len(set(targets.values())) == 12)

    data = IMAGE.read_bytes()

    hits = scan_seeds(data, targets.values())
    by = {}
    for x in hits:
        by.setdefault(x['value'], []).append(x)
    print('per-seed scan %.1fs, %d sites' % (time.time() - t0, len(hits)))

    for name, want in CONTROL.items():
        got = len(by.get(targets[name], []))
        ck('control %s: code sites == %d as in P2-STAT-READS' % (name, want),
           got == want, 'got %d' % got)

    for name in CONTROL:
        pr = sorted(x['site'] for x in by.get(targets[name], []))
        fl = sorted(scan_dataflow(data, targets[name]))
        ck('independent dataflow scanner agrees for %s' % name, fl == pr,
           'dataflow %d vs per-seed %d; diff %s' %
           (len(fl), len(pr), sorted(set(fl) ^ set(pr))))
        print('  dataflow cross-check %s: %d sites' % (name, len(fl)))

    expect = json.loads(SITES.read_text())
    ck('sites.json records 12 candidates', expect['candidates'] == 12)
    ck('sites.json used the same code range',
       expect['code_range'] == [hex(TEXT[0]), hex(TEXT[1])])

    derived = {}
    for s in stats:
        name = s['parameter_name']
        v = targets[name]
        hs = sorted(by.get(v, []), key=lambda x: x['site'])
        raw, masked = data_sites(data, v)
        rows = [classify(data, x['site'], x['complete']) for x in hs]
        disp, cls = {}, {}
        chain_yes = 0
        for r in rows:
            k = 'none' if r['disp'] is None else hex(r['disp'])
            disp[k] = disp.get(k, 0) + 1
            cls[r['class']] = cls.get(r['class'], 0) + 1
            chain_yes += 1 if r['chain'] else 0
        other = sum(n for k, n in disp.items()
                    if k not in ('0x270', '0x250', '0x260', 'none'))
        derived[name] = {'hash': s['hash'], 'type': s['decoded_type'],
                         'code': len(hs), 'disp': disp, 'cls': cls,
                         'other': other, 'chain_yes': chain_yes,
                         'data_raw': len(raw), 'data_masked': len(masked)}
        e = expect['stats'][name]

        ck('%s: sites.json hash equals the catalogue hash' % name,
           e['hash'] == s['hash'], e['hash'])
        ck('%s: sites.json type equals the catalogue type' % name,
           e['type'] == s['decoded_type'], e['type'])
        ck('%s: code site count' % name, e['code_sites'] == len(hs),
           'json %d derived %d' % (e['code_sites'], len(hs)))
        ck('%s: per-site addresses and completion addresses' % name,
           [(x['site'], x['complete']) for x in e['sites']] ==
           [(x['site'], x['complete']) for x in hs])
        ck('%s: every site carries an address inside the code range' % name,
           all(isinstance(x['site'], int) and TEXT[0] <= x['site'] < TEXT[1]
               for x in e['sites']))
        ck('%s: class counts' % name, e['classes'] == cls,
           'json %s derived %s' % (e['classes'], cls))
        ck('%s: displacement counts' % name, e['displacements'] == disp,
           'json %s derived %s' % (e['displacements'], disp))
        ck('%s: sites via +0x270' % name,
           e['via_0x270'] == disp.get('0x270', 0))
        ck('%s: sites via +0x250' % name,
           e['via_0x250'] == disp.get('0x250', 0))
        ck('%s: sites via +0x260' % name,
           e['via_0x260'] == disp.get('0x260', 0))
        ck('%s: sites via another displacement' % name,
           e['other_displacement'] == other)
        ck('%s: direct bl sites' % name,
           e['direct_bl'] == cls.get('direct_bl', 0))
        ck('%s: sites with no call in the span' % name,
           e['none'] == cls.get('none', 0))
        ck('%s: [x0]/#0x50 chain count' % name,
           e['from_x0_chain_yes'] == chain_yes,
           'json %d derived %d' % (e['from_x0_chain_yes'], chain_yes))
        ck('%s: data sites, raw 8-byte little-endian' % name,
           e['data_sites_raw'] == len(raw),
           'json %d derived %d' % (e['data_sites_raw'], len(raw)))
        ck('%s: data sites, low 40 bits at 8-byte alignment' % name,
           e['data_sites_masked'] == len(masked),
           'json %d derived %d' % (e['data_sites_masked'], len(masked)))
        ck('%s: data offsets' % name,
           [int(x, 16) for x in e['data_offsets_raw']] == raw[:64] and
           [int(x, 16) for x in e['data_offsets_masked']] == masked[:64])
        ck('%s: class counts sum to the site count' % name,
           sum(cls.values()) == len(hs))

        for j, x in enumerate(e['sites']):
            r = rows[j]
            tag = '%s site 0x%08x' % (name, x['site'])
            ck('%s class' % tag, x['class'] == r['class'],
               'json %s derived %s' % (x['class'], r['class']))
            ck('%s displacement' % tag, x.get('displacement') == r['disp'],
               'json %s derived %s' % (x.get('displacement'), r['disp']))
            ck('%s [x0]/#0x50 chain' % tag,
               bool((x.get('from_x0_chain') or {})
                    .get('x0_via_0x50')) == r['chain'])
            ck('%s x2 value before the call' % tag,
               (x.get('x2_immediate') or {}).get('value') == r['x2'],
               'json %s derived %s' % ((x.get('x2_immediate') or {}).get('value'),
                                       r['x2']))
            if x['class'] == 'indirect':
                reg = x['call']['reg']
                pa = writer_before(data, x['call']['addr'], reg, BACK_REG)
                dec = ldr_imm(struct.unpack_from('<I', data, pa)[0])
                ck('%s producer really is ldr x%d,[..,#%s]' %
                   (tag, reg, hex(r['disp'])),
                   dec is not None and dec[0] == reg and dec[2] == r['disp'])
            if x['class'] == 'direct_bl':
                a = x['call']['addr']
                w = struct.unpack_from('<I', data, a)[0]
                ck('%s is a direct bl to the reported target' % tag,
                   (w & 0xFC000000) == 0x94000000 and
                   a + (sx(w & 0x3FFFFFF, 26) << 2) == x['call']['target'])

    text = REPORT.read_text()
    rows = overall_table_rows(text)
    ck('the overall table is present in the report', bool(rows))
    ck('the overall table has one row per candidate', len(rows) == 12,
       str(len(rows)))
    for row in rows:
        name = row[0].strip('`')
        d = derived.get(name)
        if not ck('overall row %s names a catalogue stat' % name, d is not None):
            continue
        ck('overall row %s type' % name, row[1].strip('`') == d['type'],
           row[1])
        nums = [int(x) for x in row[2:8]]
        ck('overall row %s counts' % name,
           nums == [d['code'], d['disp'].get('0x270', 0),
                    d['disp'].get('0x250', 0), d['other'],
                    d['cls'].get('direct_bl', 0), d['cls'].get('none', 0)],
           str(nums))

    # per-stat tables: section 5 (chain/x2) and section 6 (class and
    # displacement counts) must match the derivation too, not only the
    # overall table.
    for s in stats:
        name = s['parameter_name']
        rows5 = [ln for ln in text.splitlines()
                 if ln.startswith('| `%s` |' % re.escape(name))]
        sec = text.split('## 5. ', 1)[1].split('## 6. ', 1)
        chain_rows = [ln for ln in sec[0].splitlines()
                      if ln.startswith('| `%s` |' % re.escape(name))]
        # only this candidate's own subsection of section 6
        m6 = re.search(r'^### %s$' % re.escape(name), text, re.M)
        ck('section 6 has a subsection for %s' % name, m6 is not None)
        cls_rows, disp_rows = [], []
        grab = 0
        if m6:
            for ln in text[m6.end():].splitlines():
                if ln.startswith('### '):
                    break
                if ln.startswith('| class | count |'):
                    grab = 1
                    continue
                if ln.startswith('| feeding `ldr` displacement | sites |'):
                    grab = 2
                    continue
                if ln.startswith('|---'):
                    continue
                if ln.startswith('|') and grab:
                    (cls_rows if grab == 1 else disp_rows).append(ln)
        d = derived[name]
        ck('section 5 has one row for %s' % name, len(chain_rows) == 1,
           str(len(chain_rows)))
        if len(chain_rows) == 1:
            nums = [int(x) for x in chain_rows[0].strip('|').split('|')[1:7]]
            ind = [x for x in expect['stats'][name]['sites']
                   if x['class'].startswith('indirect')]
            lx0 = sum(1 for x in ind
                      if (x.get('from_x0_chain') or {}).get('ldr_from_x0'))
            z = sum(1 for x in ind
                    if (x.get('x2_immediate') or {}).get('value') == 0)
            g = sum(1 for x in ind if x.get('x2_immediate')
                    and not x['x2_immediate']['immediate'])
            nn = sum(1 for x in ind if x.get('x2_immediate') is None)
            ck('section 5 row for %s' % name,
               nums == [len(ind), lx0, d['chain_yes'], z, g, nn], str(nums))
        if cls_rows:
            counts = {}
            for ln in cls_rows:
                c = [x.strip() for x in ln.strip('|').split('|')]
                key = c[0].strip('`*')
                if key == 'total':
                    continue
                counts[key] = int(c[1].strip('*'))
            ck('section 6 class table for %s' % name, counts == d['cls'],
               'report %s derived %s' % (counts, d['cls']))
            ck('section 6 class total for %s' % name,
               sum(counts.values()) == d['code'])
        if disp_rows:
            reported = {}
            for ln in disp_rows:
                c = [x.strip() for x in ln.strip('|').split('|')]
                k = c[0].strip('`*')
                # a cell may carry example addresses in parentheses; the count
                # is the leading integer
                cnt = int(re.match(r'\d+', c[1]).group(0))
                if k.startswith('no indirect class') or                         k.startswith('producer not'):
                    reported['none'] = reported.get('none', 0) + cnt
                    continue
                reported[k] = reported.get(k, 0) + cnt
            ck('section 6 displacement table for %s' % name,
               reported == d['disp'],
               'report %s derived %s' % (reported, d['disp']))

    for s in stats:
        name = s['parameter_name']
        ck('the report has a section for %s' % name,
           re.search(r'^#+\s*`?%s`?\s*$' % re.escape(name), text,
                     re.M) is not None)
    sentences = split_sentences(text)
    for b in BANNED:
        used = [s2.strip()[:70] for s2 in sentences
                if b in s2.lower() and
                not any(d in s2.lower() for d in DISCLAIMER)]
        ck('the report never uses %r outside a disclaimer' % b, not used,
           str(used))
    low = text.lower()
    ck('the report states that no ranking is offered',
       'no ranking' in low and 'no such ranking' in low)
    ck('the report states that the task is locating only',
       'locating' in low)

    print('\n%d passed, %d failed, %.1fs' % (ck.passed, ck.failed,
                                            time.time() - t0))
    return 1 if ck.failed else 0


if __name__ == '__main__':
    sys.exit(main())