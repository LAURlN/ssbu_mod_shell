"""P2-STAT-READS check script. Re-derives every claim in
research/P2-STAT-READS.md directly from gamedata/ssbu-13.0.4/main.bin and
exits nonzero on any mismatch.

Deliberately does NOT import the report generator: it re-implements the checks
independently from the raw image so that a shared bug cannot hide.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
    python mods/mii_customizer/evidence/P2-STAT-READS/check_stat_reads.py
"""
import sys, struct, re, json
from pathlib import Path
import capstone

ROOT = Path(__file__).resolve().parents[4]
IMAGE = ROOT / 'gamedata/ssbu-13.0.4/main.bin'
TEXT = (0x100, 0x39C8000)
REPORT = ROOT / 'mods/mii_customizer/research/P2-STAT-READS.md'

HASH = {'weight': 0x0607cd5541, 'walk_speed_max': 0x0ee2ec2860}

# Claims restated here independently of the report text, as (site, complete,
# reg, first-call-kind, first-call-addr-or-target).  Filled in below from the
# report only where the report is unambiguous; the script asserts both this
# table and the report agree with a fresh scan.
EXPECT = {
    'weight': dict(
        count=37,
        sites=[0x595a8c, 0x69d018, 0x6c6590, 0x6f5278, 0x6f9778, 0xebeb98,
               0x1130030, 0x23ddafc, 0x23ddc24, 0x23df9b8, 0x23dfad4,
               0x27085e4, 0x299fc08, 0x29a42b4, 0x2b1b34c, 0x2b88934,
               0x2bcea58, 0x2be5c10, 0x2c16880, 0x2d7b43c, 0x2db4eec,
               0x2db55c8, 0x2db5648, 0x2db56c8, 0x2db5748, 0x2dd7368,
               0x2ee5f94, 0x2f409d0, 0x2f4933c, 0x2ff7110, 0x30ad990,
               0x30ae41c, 0x30ae54c, 0x30c0f58, 0x30c1520, 0x36d8c98,
               0x36d8eac],
        data_raw=[], data_masked=[],
    ),
    'walk_speed_max': dict(
        count=18,
        sites=[0x6d42c0, 0x6d86d4, 0x6f3f14, 0x6f82f4, 0x6f830c, 0x85b26c,
               0x9132f8, 0x9138e0, 0x993818, 0x9deccc, 0xa8f070, 0xaa22cc,
               0xadade0, 0xbe3e8c, 0x105fec8, 0x116c814, 0x116cd34,
               0x131611c],
        data_raw=[0x453d0e0], data_masked=[0x453d0e0],
    ),
}

# fn -> (caller_count, first10 addresses)
EXPECT_FNS = {
    'weight': {
        0x590a50: (0, []),
        0x69cf90: (1, [0x20c9338]),
        0x6c5df0: (0, []),
        0x6f37b0: (0, []),
        0x6f7b20: (0, []),
        0xebeadc: (0, []),
        0x112fef4: (0, []),
        0x23dab40: (0, []),
        0x2707b50: (0, []),
        0x299f7b0: (3, [0x299c628, 0x299c6d0, 0x299c778]),
        0x29a2f30: (1, [0x299f608]),
        0x2b1ab30: (2, [0x2b14580, 0x2b14648]),
        0x2b88200: (3, [0x2b7f004, 0x2b7f214, 0x2b7f6c8]),
        0x2bce810: (0, []),
        0x2be5b50: (0, []),
        0x2c15f50: (2, [0x2c0a70c, 0x2c0f9e4]),
        0x2d7aee0: (0, []),
        0x2db4eb0: (0, []),
    },
    'walk_speed_max': {
        0x6d4060: (0, []),
        0x6d8560: (0, []),
        0x6f37b0: (0, []),
        0x6f7b20: (0, []),
        0x85a9d0: (1, [0x21b6ce4]),
        0x9130b0: (0, []),
        0x913710: (0, []),
        0x993750: (0, []),
        0x9dea20: (3, [0x9dd4c0, 0x9e02ac, 0x21e12a0]),
        0xa8e7ec: (0, []),
        0xadac40: (0, []),
        0xbe3d20: (0, []),
        0x105fc90: (0, []),
        0x116b880: (2, [0x11681cc, 0x1168384]),
        0x1315e20: (3, [0x131365c, 0x13137a0, 0x13137c4]),
    },
}

# site -> (kind, target-or-reg) for the first call after the completing insn
EXPECT_CALL = {
    'weight': {
        0x69d018: ('blr', 8),
        0x6c6590: ('blr', 8),
        0xebeb98: ('bl', None),
        0x23ddafc: ('bl', None),
        0x23ddc24: ('bl', None),
        0x23df9b8: ('bl', None),
        0x23dfad4: ('bl', None),
        0x27085e4: ('blr', 8),
        0x299fc08: ('blr', 8),
        0x29a42b4: ('blr', 8),
        0x2b1b34c: ('blr', 8),
        0x2b88934: ('blr', 8),
        0x2bcea58: ('blr', 8),
        0x2be5c10: ('blr', 8),
        0x2c16880: ('blr', 8),
        0x2d7b43c: ('blr', 8),
        0x2db4eec: ('bl', None),
        0x2db55c8: ('blr', 8),
        0x2db5648: ('blr', 8),
        0x2db56c8: ('blr', 8),
        0x2db5748: ('blr', 8),
    },
    'walk_speed_max': {
        0x6d42c0: ('blr', 8),
        0x6d86d4: ('blr', 8),
        0x85b26c: ('bl', None),
        0x9132f8: ('blr', 8),
        0x9138e0: ('blr', 8),
        0x993818: ('bl', None),
        0x9deccc: ('bl', None),
        0xa8f070: ('bl', None),
        0xadade0: ('bl', None),
        0xbe3e8c: ('blr', 8),
        0x105fec8: ('blr', 8),
        0x116c814: ('bl', None),
        0x116cd34: ('bl', None),
        0x131611c: ('bl', None),
    },
}


md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md.detail = True
md2 = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md2.detail = True
CACHE = {}

FAILS = []
NPASS = 0


def ck(label, cond, extra=''):
    global NPASS
    if cond:
        NPASS += 1
    else:
        FAILS.append(label + ((' | ' + str(extra)) if extra else ''))


def sx(v, b):
    return v - (1 << b) if v & (1 << (b - 1)) else v


def wr_regs(word):
    if word in CACHE:
        return CACHE[word]
    out = set()
    try:
        ins = next(md2.disasm(struct.pack('<I', word), 0), None)
        if ins is not None:
            _, w_ = ins.regs_access()
            for r in w_:
                nm = ins.reg_name(r)
                if nm and nm[0] in 'xw' and nm[1:].isdigit():
                    out.add(int(nm[1:]))
            if ins.mnemonic in ('bl', 'blr'):
                out |= set(range(19))
    except capstone.CsError:
        out = set(range(31))
    CACHE[word] = out
    return out


def movz_movk(word):
    """(kind, reg, imm16, hw, sf) or None."""
    for base, k in ((0xD2800000, 'movz'), (0xF2800000, 'movk')):
        if (word & 0xFF800000) == base:
            return (k, word & 31, (word >> 5) & 0xFFFF,
                    (word >> 21) & 3, 1)
    for base, k in ((0x52800000, 'movz'), (0x72800000, 'movk')):
        if (word & 0xFF800000) == base:
            return (k, word & 31, (word >> 5) & 0xFFFF,
                    (word >> 21) & 3, 0)
    return None


def scan(data, target, max_gap=4):
    lo, hi = TEXT
    n = (hi - lo) // 4
    words = struct.unpack_from('<%dI' % n, data, lo)
    out = []
    for i in range(n):
        m = movz_movk(words[i])
        if m is None or m[0] != 'movz':
            continue
        _, reg, imm, hw, sf = m
        val = imm << (16 * hw)
        gap = 0
        last = i          # index of the most recent composing instruction
        for j in range(i + 1, min(n, i + max_gap + 9)):
            w2 = words[j]
            m2 = movz_movk(w2)
            if m2 and m2[0] == 'movk' and m2[1] == reg and m2[4] == sf:
                val = (val & ~(0xFFFF << (16 * m2[3]))) | (m2[2] << (16 * m2[3]))
                gap = 0
                last = j
                if val == target:
                    out.append((lo + 4 * i, lo + 4 * j, reg))
                    break
            elif m2 and m2[0] == 'movz' and m2[1] == reg:
                break
            else:
                if reg in wr_regs(w2):
                    break
                gap += 1
                if gap > max_gap:
                    break
        # a sequence may complete on its seed alone only for values < 2^16,
        # which neither target hash is, so nothing more to record here.
    return out


def bl_index(data):
    n = (TEXT[1] - TEXT[0]) // 4
    words = struct.unpack_from('<%dI' % n, data, TEXT[0])
    idx = {}
    for i in range(n):
        w = words[i]
        if (w & 0xFC000000) == 0x94000000:
            a = TEXT[0] + 4 * i
            idx.setdefault(a + (sx(w & 0x3FFFFFF, 26) << 2), []).append(a)
    return idx


def first_call(data, after, limit):
    n = (limit - after) // 4
    if n <= 0:
        return None
    words = struct.unpack_from('<%dI' % n, data, after)
    for i in range(n):
        w = words[i]
        a = after + 4 * i
        if (w & 0xFC000000) == 0x94000000:
            return ('bl', a + (sx(w & 0x3FFFFFF, 26) << 2))
        if (w & 0xFFFFFC1F) == 0xD63F0000:
            return ('blr', (w >> 5) & 31)
    return None


def main():
    ck('input image exists', IMAGE.is_file(), str(IMAGE))
    if not IMAGE.is_file():
        return 1
    data = IMAGE.read_bytes()

    # input hash (re-verified, must match the prompt's pinned value)
    import hashlib
    h = hashlib.sha256(data).hexdigest()
    ck('input sha256 matches pinned value',
       h == 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613', h)

    # step 1: code sites
    for name, val in HASH.items():
        hits = scan(data, val)
        addrs = sorted(a for a, _, _ in hits)
        ck(f'{name}: code site count == {len(EXPECT[name]["sites"])}',
           len(addrs) == len(EXPECT[name]['sites']),
           f'got {len(addrs)}')
        ck(f'{name}: code site addresses match report',
           addrs == sorted(EXPECT[name]['sites']),
           f'extra={sorted(set(addrs) - set(EXPECT[name]["sites"]))} '
           f'missing={sorted(set(EXPECT[name]["sites"]) - set(addrs))}')
        # every hit must really carry the value in that register
        for a, c, reg in hits:
            parts = []
            k = a
            while k <= c:
                m = movz_movk(struct.unpack_from('<I', data, k)[0])
                # Only the composing register counts; other registers in the
                # span (e.g. x18 at 0x2f4934c) must not affect the value.
                if m and m[1] == reg:
                    parts.append((k, m))
                k += 4
            val2 = 0
            ok = False
            for _, m in parts:
                if m[0] == 'movz':
                    val2 = m[2] << (16 * m[3])
                else:
                    val2 = (val2 & ~(0xFFFF << (16 * m[3]))) | (m[2] << (16 * m[3]))
            ck(f'{name}: site 0x{a:x} replays to the hash', val2 == val,
               hex(val2))

    # step 2: data sites
    for name, val in HASH.items():
        pat = struct.pack('<Q', val)
        raw, i = [], 0
        while True:
            i = data.find(pat, i)
            if i < 0:
                break
            raw.append(i)
            i += 1
        ck(f'{name}: raw 8-byte LE offsets match',
           raw == EXPECT[name]['data_raw'], f'got {[hex(x) for x in raw]}')
        masked = []
        for off in range(0, len(data) - 8, 8):
            if struct.unpack_from('<Q', data, off)[0] & ((1 << 40) - 1) == \
                    val & ((1 << 40) - 1):
                masked.append(off)
        ck(f'{name}: low-40-bit aligned offsets match',
           masked == EXPECT[name]['data_masked'],
           f'got {[hex(x) for x in masked]}')

    # step 4: callers of each enclosing function
    bls = bl_index(data)
    for name in HASH:
        for fn, (cnt, first10) in EXPECT_FNS[name].items():
            got = bls.get(fn, [])
            ck(f'{name}: callers of 0x{fn:x} == {cnt}', len(got) == cnt,
               f'got {len(got)}')
            ck(f'{name}: first10 callers of 0x{fn:x}',
               got[:10] == first10, f'got {[hex(x) for x in got[:10]]}')

    # step 3: first call after each listed site
    for name, val in HASH.items():
        for site, (kind, arg) in EXPECT_CALL[name].items():
            complete = scan(data, val)
            cm = {a: (c, r) for a, c, r in complete}.get(site)
            ck(f'{name}: site 0x{site:x} present', cm is not None)
            if cm is None:
                continue
            got = first_call(data, cm[0] + 4, cm[0] + 4 + 0x400)
            ck(f'{name}: site 0x{site:x} first call is {kind}',
               got is not None and got[0] == kind, f'got {got}')
            if got and got[0] == kind and arg is not None:
                ck(f'{name}: site 0x{site:x} call arg == {arg}',
                   got[1] == arg, f'got {got[1]}')

    # report text consistency: every site listed in the report must appear
    if REPORT.is_file():
        txt = REPORT.read_text()
        for name in HASH:
            for a in EXPECT[name]['sites']:
                ck(f'report lists {name} site 0x{a:x}',
                   f'0x{a:08x}' in txt or f'0x{a:x}' in txt)
        m = re.search(r'code sites\D{0,20}(\d+)', txt)
        ck('report states a code-site count', m is not None)

        # The report tables must agree with the regenerated summary tables,
        # so the prose cannot silently drift from the image.
        sec = txt.split('## 3. Code sites')[1].split('### Observations')[0]
        rep = {}
        for line in sec.splitlines():
            if not line.startswith('| `0x'):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            rep[int(cells[0].strip('`'), 16)] = (cells[4], cells[6])
        gen = {}
        for h in HASH:
            sp = Path(__file__).parent / f'summary_{h}.md'
            if not sp.is_file():
                ck(f'summary table {h} exists', False, str(sp))
                continue
            for line in sp.read_text().splitlines():
                if not line.startswith('| 0x'):
                    continue
                cells = [c.strip() for c in line.strip().strip('|').split('|')]
                gen[int(cells[1], 16)] = (cells[3], cells[4])

        def norm(x):
            # Reduce a call cell to just "bl" / "blr x8" / "none within ...",
            # discarding producer clauses, '-> target' tails and punctuation,
            # so the report (more verbose) matches the generated table.
            x = x.replace('`', '')
            m = re.match(r'\s*(blr\s+x\d+|bl\b|none within[^|]*)', x)
            return re.sub(r'\s+', ' ', m.group(1).strip()) if m else x.strip()

        for s, (call, cc) in gen.items():
            ck(f'report has a row for site 0x{s:x}', s in rep)
            if s not in rep:
                continue
            ck(f'report call for 0x{s:x} matches generated',
               norm(rep[s][0]) == norm(call), f'{norm(rep[s][0])} vs {norm(call)}')
            ck(f'report callers for 0x{s:x} matches generated',
               norm(rep[s][1]) == norm(cc), f'{norm(rep[s][1])} vs {norm(cc)}')
        for s in rep:
            ck(f'report site 0x{s:x} exists in generated table', s in gen)
    else:
        ck('report file exists', False, str(REPORT))

    print(f'passed {NPASS}, failed {len(FAILS)}')
    for f in FAILS:
        print('FAIL ' + f)
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())