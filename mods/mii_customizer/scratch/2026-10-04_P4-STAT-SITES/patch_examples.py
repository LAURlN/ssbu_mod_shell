"""One-off patcher: inserts the example-window block into scan_all.py."""
from pathlib import Path

P = Path(__file__).resolve().parent / 'scan_all.py'
ANCHOR = "    with open(EV / 'sites.json', 'w') as f:\n"

BLOCK = r'''    # Example windows: one per distinct (class, displacement) pair, written to
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

'''

s = P.read_text()
if 'example_windows' not in s:
    assert ANCHOR in s, 'anchor not found'
    s = s.replace(ANCHOR, BLOCK + ANCHOR, 1)
    P.write_text(s)
    print('patched')
else:
    print('already patched')