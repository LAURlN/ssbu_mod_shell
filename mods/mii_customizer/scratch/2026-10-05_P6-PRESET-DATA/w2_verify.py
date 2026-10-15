"""Second-worker independent verification of the P6-PRESET-DATA outputs.
Reads only; prints counts and hashes. Run from the workspace root."""
import sys, csv, json, struct, hashlib, re, io, contextlib, importlib
sys.path.insert(0, 'mods/ssbu_mod_new/src/pgwr/tools'); sys.path.insert(0, 'mods/mii_customizer/scratch/2026-10-05_P6-PRESET-DATA')
import prc
G = 'gamedata/mii_customizer/P6-PRESET-DATA/'
PRC = 'gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc'
fails = 0
def check(name, ok, note=''):
    global fails; fails += not ok
    print(('ok   ' if ok else 'FAIL ') + name + ('  -- ' + str(note) if note != '' else ''))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
for p in (PRC, G + 'presets.txt', G + 'fighters.json', G + 'fighter_param_full.json', G + 'files/ui/message/msg_name.msbt'):
    print(sha(p), len(open(p, 'rb').read()), p)
check('prc hash pinned', sha(PRC) == '87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2')
labels = {}
for row in csv.reader(open('mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv', newline='', encoding='utf-8')):
    if len(row) >= 2 and row[1]: labels.setdefault(int(row[0], 16), row[1])
rows = [prc.as_dict(r) for r in prc.as_dict(prc.read(PRC))[prc.hash40('fighter_param_table')][1]]
fields = [l.strip() for l in open('mods/mii_customizer/tools/stat-presets/stat_fields.txt') if l.strip() and not l.startswith('#')]
check('field list is the ten of the prompt, in order', fields == 'weight walk_speed_max run_speed_max dash_speed air_speed_x_stable air_speed_y_stable air_accel_y air_accel_x_mul jump_y jump_speed_x'.split())
bits = lambda f: struct.unpack('<I', struct.pack('<f', f))[0]
def plugin_parse(s):  # model of plugin/src/loadout.rs parse_decimal: (u64 mantissa as f64 / f64 scale) as f32
    m = re.fullmatch(r'(-?)(\d+)(?:\.(\d+))?', s)
    if not m or len(m.group(2)) + len(m.group(3) or '') > 18: return None
    v = int(m.group(2) + (m.group(3) or '')) / (10.0 ** len(m.group(3) or ''))
    v = struct.unpack('<f', struct.pack('<f', v))[0]
    return -v if m.group(1) else v
raw = open(G + 'presets.txt', 'rb').read()
check('ASCII only, no CR, ends with LF', all(b < 128 for b in raw) and b'\r' not in raw and raw.endswith(b'\n'))
lines = raw.decode('ascii').split('\n')
check('line 1', lines[0] == 'mc_presets 1')
presets = []; n_exact = n_plugin = n_vals = 0; maxlen = 0; bad = []
for ln in lines[1:]:
    ln = ln.split('#', 1)[0].strip()
    if not ln: continue
    t = ln.split()
    if t[0] == 'fighter':
        assert len(t) == 3 and re.fullmatch(r'[a-z0-9_]+', t[1]) and re.fullmatch(r'0x[0-9a-f]{10}', t[2]), ln
        presets.append((t[1], int(t[2], 16), []))
    else:
        assert len(t) == 2 and re.fullmatch(r'0x[0-9a-f]{10}', t[0]), ln
        presets[-1][2].append((int(t[0], 16), t[1])); maxlen = max(maxlen, len(t[1]))
check('94 presets', len(presets) == 94, len(presets))
kk = prc.hash40('fighter_kind')
for i, (name, kind, vals) in enumerate(presets):
    r = rows[i]
    if not (r[kk] == ('hash', kind) and labels.get(kind) == 'fighter_kind_' + name and prc.hash40('fighter_kind_' + name) == kind): bad.append(('kind', name))
    if [h for h, _ in vals] != [prc.hash40(f) for f in fields]: bad.append(('order', name))
    for (h, s), f in zip(vals, fields):
        tag, v = r[h]; n_vals += 1
        if tag != 'float': bad.append(('type', name, f))
        n_exact += bits(float(s)) == bits(v) if bits(struct.unpack('<f', struct.pack('<f', float(s)))[0]) == bits(v) else 0
        pv = plugin_parse(s)
        if pv is not None and bits(pv) == bits(v): n_plugin += 1
        else: bad.append(('plugin_parse', name, f, s))
check('preset i is table row i, kind label hash-verified, field order', not [b for b in bad if b[0] in ('kind', 'order', 'type')])
check('values bit-exact with a correctly rounded parse', n_exact == n_vals, '%d/%d' % (n_exact, n_vals))
check("values bit-exact with the plugin's own decimal parser model", n_plugin == n_vals, '%d/%d, longest value token %d chars; first misses %s' % (n_plugin, n_vals, maxlen, [b for b in bad if b[0] == 'plugin_parse'][:5]))
check('kind hashes unique, names unique', len({p[1] for p in presets}) == 94 and len({p[0] for p in presets}) == 94)
# full json
full = json.load(open(G + 'fighter_param_full.json'))
frows = full['rows'] if isinstance(full, dict) else full
print('full json top keys:', list(full)[:12] if isinstance(full, dict) else 'list', '| row keys:', list(frows[0])[:8])
fj = json.load(open(G + 'fighters.json'))['fighters']
check('fighters.json order/name/kind/row', [(f['name'], int(f['kind_hash'], 16), f['row_index']) for f in fj] == [(p[0], p[1], i) for i, p in enumerate(presets)])
# label families
sys.argv = ['x', G + 'files/ui/message/msg_name.msbt']
with contextlib.redirect_stdout(io.StringIO()): m = importlib.import_module('w2_msbt').m
for fam in ('nam_chr0_00_', 'nam_chr1_00_', 'nam_chr2_00_', 'nam_chr3_00_'):
    have = [p[0] for p in presets if fam + p[0] in m]
    print(fam, 'resolves', len(have), 'of 94; texts containing a line break:', sum('\n' in m[fam + n] for n in have), '; missing:', [p[0] for p in presets if fam + p[0] not in m])
check('fighters.json labels all exist in msg_name', all(f['display_name_label'] is None or f['display_name_label'] in m for f in fj))
print('type counts:', {t: sum(1 for r in rows for tg, _ in r.values() if tg == t) for t in ('float', 'i32', 'bool', 'hash')}, 'fields/row', {len(r) for r in rows}, 'unlabelled', sum(1 for h in rows[0] if labels.get(h) is None or prc.hash40(labels[h]) != h))
print('FAILS', fails)
