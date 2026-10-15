"""P2-STAT-READS report generator. Reads gamedata/ssbu-13.0.4/main.bin only.
Writes evidence/P2-STAT-READS/ raw windows and a machine-readable site list.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
    python report.py
"""
import sys, json, struct
from pathlib import Path
import capstone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stat_reads import (load, HASH, TEXT, scan_sequences, fstart, disasm,
                        decode_movz, decode_movk, dest_regs, sx,
                        scan_sequences_strict, IMAGE)

EV = HERE.parents[1] / 'evidence/P2-STAT-READS'
EV.mkdir(parents=True, exist_ok=True)

BEFORE, AFTER = 12, 20


def bl_index(data):
    """One pass: {target: [bl sites]} over the whole code range."""
    n = (TEXT[1] - TEXT[0]) // 4
    words = struct.unpack_from('<%dI' % n, data, TEXT[0])
    out = {}
    for i in range(n):
        w = words[i]
        if (w & 0xFC000000) == 0x94000000:
            a = TEXT[0] + 4 * i
            t = a + (sx(w & 0x3FFFFFF, 26) << 2)
            out.setdefault(t, []).append(a)
    return out


def next_bl_or_blr(data, start, limit):
    """First bl or blr at or after `start`, searching up to `limit` bytes.
    Returns dict with kind, addr and target (bl) or reg+producer (blr)."""
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
            reg = (w >> 5) & 31
            prod = None
            for k in range(1, 21):
                pa = a - 4 * k
                if pa < TEXT[0]:
                    break
                pw = struct.unpack_from('<I', data, pa)[0]
                if reg in dest_regs(pw):
                    ins = next(capstone.Cs(capstone.CS_ARCH_ARM64,
                                           capstone.CS_MODE_ARM)
                               .disasm(data[pa:pa + 4], pa), None)
                    prod = {'addr': pa,
                            'text': (ins.mnemonic + ' ' + ins.op_str).strip()
                            if ins else '.word'}
                    break
            return {'kind': 'blr', 'addr': a, 'reg': reg, 'producer': prod}
    return None


def second_const(data, lo, hi, exclude):
    """Other >=2^32 constants composed in the window, excluding `exclude`."""
    n = (hi - lo) // 4
    if n <= 0:
        return []
    words = struct.unpack_from('<%dI' % n, data, lo)
    found = []
    for i in range(n):
        mz = decode_movz(words[i])
        if mz is None:
            continue
        reg, imm16, hw, sf = mz
        value = imm16 << (16 * hw)
        start = lo + 4 * i
        gap = 0
        for j in range(i + 1, min(n, i + 13)):
            w2 = words[j]
            mk = decode_movk(w2)
            if mk is not None and mk[0] == reg and mk[3] == sf:
                _, imm2, hw2, _ = mk
                value = (value & ~(0xFFFF << (16 * hw2))) | (imm2 << (16 * hw2))
                gap = 0
            else:
                if reg in dest_regs(w2):
                    break
                gap += 1
                if gap > 4:
                    break
            if value >= (1 << 32) and value != exclude:
                found.append({'addr': start, 'reg': reg, 'value': value})
                break
    return found


def main():
    data = load()
    bls = bl_index(data)
    report = {}

    for name, val in HASH.items():
        hits = scan_sequences(data, [val], TEXT[0], TEXT[1], max_gap=4)
        strict = scan_sequences_strict(data, [val], TEXT[0], TEXT[1], max_gap=4)
        s_set = {(h['addr'], h['value']) for h in strict}
        m_set = {(h['addr'], h['value']) for h in hits}

        # cross-check the two independent scanners agree
        cross = {'primary': len(hits), 'strict': len(strict),
                 'agree': s_set == m_set,
                 'only_primary': sorted(hex(a) for a, _ in m_set - s_set),
                 'only_strict': sorted(hex(a) for a, _ in s_set - m_set)}

        shown = hits[:25]
        omitted = len(hits) - len(shown)

        sites = []
        for h in shown:
            addr = h['addr']
            fs = fstart(data, addr)
            lo = addr - 4 * BEFORE
            hi = addr + 4 * AFTER
            # "first call after" bound: the completing instruction's successor
            # through a fixed 0x400-byte span.  The check script uses the
            # identical definition so the two agree by construction.
            call = next_bl_or_blr(data, h['complete_addr'] + 4,
                                  h['complete_addr'] + 4 + 0x400)
            other = second_const(data, lo, hi, val)
            win = disasm(data, lo, (hi - lo) // 4)
            sites.append({
                'site': addr,
                'reg': f'x{h["reg"]}',
                'complete': h['complete_addr'],
                'seq': [hex(i['addr']) for i in h['insns']],
                'fstart': fs,
                'window': [(f'0x{i["addr"]:08x}', i['text']) for i in win],
                'first_call': call,
                'other_consts': other,
            })

            with open(EV / f'win_{name}_{addr:08x}.txt', 'w') as f:
                f.write(f'# {name} 0x{val:010x} site 0x{addr:08x} '
                        f'reg x{h["reg"]} complete 0x{h["complete_addr"]:08x}\n')
                f.write(f'# fstart candidate {hex(fs) if fs else "none"}\n')
                f.write(f'# {BEFORE} instructions before, {AFTER} after\n')
                for a, t in zip(range(lo, hi, 4),
                                [i['text'] for i in win]):
                    mark = ''
                    if a == addr:
                        mark = '   <== movz seed'
                    elif a == h['complete_addr']:
                        mark = '   <== completes hash'
                    f.write(f'0x{a:08x}: {t}{mark}\n')
                f.write(f'# first call after 0x{h["complete_addr"]+4:08x}: '
                        f'{json.dumps(call)}\n')
                f.write(f'# other >=2^32 constants in window: '
                        f'{json.dumps(other)}\n')

        # distinct enclosing functions and their direct bl callers
        fns = {}
        for s in sites:
            if s['fstart'] is None:
                continue
            fns.setdefault(s['fstart'], []).append(s['site'])
        fn_rows = []
        for fn, site_list in sorted(fns.items()):
            cl = bls.get(fn, [])
            fn_rows.append({
                'fstart': fn,
                'sites': site_list,
                'callers_count': len(cl),
                'callers_first10': [hex(a) for a in cl[:10]],
            })

        report[name] = {
            'hash': val,
            'count': len(hits),
            'count_strict': len(strict),
            'cross': cross,
            'omitted': omitted,
            'sites': sites,
            'functions': fn_rows,
        }

        # summary table rows
        with open(EV / f'summary_{name}.md', 'w') as f:
            f.write('| hash | site | enclosing fn (fstart) | call / vtable | '
                    'callers of fn |\n')
            f.write('|---|---|---|---|---|\n')
            for s in sites:
                fn = s['fstart']
                c = s['first_call']
                if c is None:
                    ct = 'none within completing+0x400'
                elif c['kind'] == 'bl':
                    ct = f"`bl` -> 0x{c['target']:x}"
                else:
                    pt = c.get('producer')
                    ct = (f"`blr x{c['reg']}` (producer {pt['text']} @ "
                          f"0x{pt['addr']:x})" if pt else
                          f"`blr x{c['reg']}` (producer not found)")
                cc = next((r['callers_count'] for r in fn_rows
                           if r['fstart'] == fn), '-')
                f.write(f'| 0x{val:010x} | 0x{s["site"]:08x} | '
                        f'{hex(fn) if fn else "none"} | {ct} | {cc} |\n')

    with open(EV / 'sites.json', 'w') as f:
        json.dump(report, f, indent=1, default=str)
    print(json.dumps({k: {'count': v['count'], 'count_strict': v['count_strict'],
                          'omitted': v['omitted'], 'cross': v['cross'],
                          'fns': len(v['functions'])}
                      for k, v in report.items()}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())