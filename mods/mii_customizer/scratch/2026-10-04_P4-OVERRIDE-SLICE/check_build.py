"""P4-OVERRIDE-SLICE: offline checks of the staged 0.2.0-override NRO, then (re)write its MANIFEST.json.
usage: python check_build.py [--write-manifest]      exit 0 = all checks pass
Reads builds/0.2.0-override/, plugin/ and build-plugin.sh. Runs nothing."""
import hashlib, json, re, struct, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
WS = MOD.parents[1]
sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/builds/.cache/dk_cargo/python'))
import capstone
PKG = MOD / 'builds/0.2.0-override'
NRO = PKG / 'libmii_customizer.nro'
EXAMPLE = PKG / 'example/loadouts.txt'
d = NRO.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
ok = bad = 0


def check(name, cond, detail=''):
    global ok, bad
    ok += bool(cond)
    bad += not cond
    print(('PASS ' if cond else 'FAIL ') + name + (' | ' + str(detail) if detail != '' else ''))


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def u32(a): return struct.unpack_from('<I', d, a)[0]
def sx(v, b): return v - (1 << b) if v & (1 << (b - 1)) else v


def dis(a, n):
    out = []
    for k in range(n):
        i = next(md.disasm(d[a + 4 * k:a + 4 * k + 4], a + 4 * k), None)
        out.append(f'{i.mnemonic} {i.op_str}'.strip() if i else '.word')
    return out


def bl_target(a):
    w = u32(a)
    return a + (sx(w & 0x3ffffff, 26) << 2) if w >> 26 == 0x25 else None


SITES = [
    ('param', 0x4e53e0, [0xf9401c00, 0xf9400008, 0xf9401903, 0xd61f0060], 'L3/L4/L5/OV',
     'f32 getter thunk, slot +0x270 of vtables 0x4f89490/0x4f73738; the only hook that can change a value',
     'replace (A64HookFunction): original called first, its result returned unless every override condition holds'),
    ('custom', 0x4e53f0, [0xf9401c00, 0xf9400008, 0xf9401d03, 0xd61f0060], 'L6',
     'slot +0x278 thunk of the same two vtables (D: set_customize_no)',
     'replace (A64HookFunction), log-only: registers saved, logged, restored, tail-jump to the trampoline'),
]
GAME_IMPORTS = [
    '_ZN3app16sv_battle_object15module_accessorEj',
    '_ZN3app16sv_battle_object8categoryEj',
    '_ZN3app16sv_battle_object4kindEj',
    '_ZN3app16sv_battle_object8entry_idEj',
    '_ZN3app7utility8get_kindEPKNS_26BattleObjectModuleAccessorE',
    '_ZN3app8lua_bind24WorkModule__get_int_implEPNS_26BattleObjectModuleAccessorEi',
]
SKYLINE_REV = '6b52d321275639f26c2371d8142550ba0013a5e4'
SMASH_REV = '315e4e8bebb460ebb9f02f30f07b0f13883ba3d6'

print('== container')
check('NRO0 magic at 0x10', d[0x10:0x14] == b'NRO0')
mod0 = u32(4)
check('MOD0 magic at header offset', d[mod0:mod0 + 4] == b'MOD0', hex(mod0))
check('file size equals NRO size field', u32(0x18) == len(d), len(d))
text_end = u32(0x24)

print('== hook table in the binary')
rec = b''.join(struct.pack('<Q4I', off, *w) for _, off, w, _, _, _ in SITES)
at = d.find(rec)
check('MC_SITES: two contiguous {u64 offset, u32 words[4]} records, order param, custom', at >= 0 and d.count(rec) == 1, hex(at))
check('no record for the 0.1.0 store/load sites (0x179e440, 0x17c8210)',
      d.find(struct.pack('<Q', 0x179e440)) < 0 and d.find(struct.pack('<Q', 0x17c8210)) < 0)

print('== imports')
dyn = mod0 + struct.unpack_from('<i', d, mod0 + 4)[0]
tags = {}
while True:
    t, v = struct.unpack_from('<QQ', d, dyn)
    dyn += 16
    if t == 0:
        break
    tags[t] = v
symtab, strtab = tags[6], tags[5]
names = []
for i in range((strtab - symtab) // 24):
    name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', d, symtab + 24 * i)
    e = d.find(b'\0', strtab + name)
    names.append((d[strtab + name:e].decode('latin1'), shndx))
imports = [s for s, shndx in names if s and shndx == 0]
print('   ' + ' '.join(imports))
check('imports A64HookFunction and getRegionAddress', 'A64HookFunction' in imports and 'getRegionAddress' in imports)
check('does not import A64InlineHook, sky_memcpy or any thread-creation symbol',
      not any(x in imports for x in ('A64InlineHook', 'sky_memcpy', 'pthread_create')) and not any('CreateThread' in x for x in imports))
game = sorted(x for x in imports if x.startswith('_ZN3app') or x.startswith('_ZN3lib'))
check('game symbols imported: exactly the six identity functions', game == sorted(GAME_IMPORTS), game)
ALLOWED = re.compile(r'^(__nro_header_start|skyline_tcp_send_raw|A64HookFunction|getRegionAddress|free|malloc|memset|memcpy|memcmp|posix_memalign|pthread_\w+|_ZN2nn2fs\w+)$')
other = [x for x in imports if not ALLOWED.match(x) and x not in GAME_IMPORTS]
check('everything else imported is skyline, libc, pthread or nn::fs', not other, other)
fs = sorted(x for x in imports if x.startswith('_ZN2nn2fs'))
check('nn::fs imports contain no delete/rename/directory-create call',
      not any(re.search(r'Delete|Rename|CreateDirectory|CleanDirectory', x) for x in fs), [re.sub(r'^_ZN2nn2fs\d+', '', x)[:14] for x in fs])

# PLT stubs of the game imports: adrp x16 ; ldr x17,[x16,#imm] ; add x16 ; br x17
got = {}
jmprel, pltsz = tags.get(23), tags.get(2)
for o in range(jmprel, jmprel + pltsz, 24):
    off, info, add = struct.unpack_from('<QQq', d, o)
    got[off] = names[info >> 32][0]
plt = {}
for a in range(0, text_end, 4):
    w = [u32(a + 4 * k) for k in range(4)]
    if (w[0] & 0x9f00001f) == 0x90000010 and (w[1] & 0xffc003ff) == 0xf9400211 and w[3] == 0xd61f0220:
        page = (a & ~0xfff) + (sx((((w[0] >> 5) & 0x7ffff) << 2) | ((w[0] >> 29) & 3), 21) << 12)
        plt[a] = got.get(page + (((w[1] >> 10) & 0xfff) << 3), '?')
gplt = {a: n for a, n in plt.items() if n in GAME_IMPORTS}
check('one PLT stub per game import', sorted(gplt.values()) == sorted(GAME_IMPORTS), {hex(a): n[8:40] for a, n in gplt.items()})

print('== entry stubs')
PARAM_STUB = [0xa9bf7bfd, 0x910003fd, 0xd10043ff, 0xf90003fe, None, 0x910043ff, 0xa8c17bfd, 0xd65f03c0]
pstubs = [a for a in range(0, text_end, 4) if all(s is None or u32(a + 4 * k) == s for k, s in enumerate(PARAM_STUB)) and bl_target(a + 16)]
check('exactly one param stub: stp x29,x30 / mov x29,sp / sub sp,16 / str x30,[sp] / bl / add sp,16 / ldp / ret', len(pstubs) == 1, [hex(a) for a in pstubs])
CUSTOM_STUB = ['stp x29, x30, [sp, #-0xe0]!', 'mov x29, sp', 'stp x0, x1, [sp, #0x10]', 'stp x2, x3, [sp, #0x20]', 'stp x4, x5, [sp, #0x30]',
               'stp x6, x7, [sp, #0x40]', 'str x8, [sp, #0x50]', 'stp q0, q1, [sp, #0x60]', 'stp q2, q3, [sp, #0x80]', 'stp q4, q5, [sp, #0xa0]',
               'stp q6, q7, [sp, #0xc0]', 'mov x3, x30', None, 'mov x16, x0', 'ldp x0, x1, [sp, #0x10]', 'ldp x2, x3, [sp, #0x20]',
               'ldp x4, x5, [sp, #0x30]', 'ldp x6, x7, [sp, #0x40]', 'ldr x8, [sp, #0x50]', 'ldp q0, q1, [sp, #0x60]', 'ldp q2, q3, [sp, #0x80]',
               'ldp q4, q5, [sp, #0xa0]', 'ldp q6, q7, [sp, #0xc0]', 'ldp x29, x30, [sp], #0xe0', None, 'br x16',
               'ldr x0, [x0, #0x38]', 'ldr x8, [x0]', 'ldr x3, [x8, #0x38]', 'br x3']
cstub = pstubs[0] + 0x20 if pstubs else 0
cd = dis(cstub, len(CUSTOM_STUB))
check('custom stub follows: saves x0-x8/q0-q7, bl logger, restores all, `br x16` to the trampoline',
      all(s is None or s == x for s, x in zip(CUSTOM_STUB, cd)) and cd[12].startswith('bl #') and cd[24] == f'cbz x16, #{cstub + 26 * 4:#x}', cd[12:14] + cd[24:26])
check('custom stub fallback (no trampoline) is the four original words of 0x4e53f0',
      [u32(cstub + 4 * k) for k in range(26, 30)] == SITES[1][2])
check('custom stub: between restore and the jump nothing writes x0-x8, x30 or sp', cd[23:26] == ['ldp x29, x30, [sp], #0xe0', f'cbz x16, #{cstub + 26 * 4:#x}', 'br x16'])


def consts(a, n):
    regs, found = {}, set()
    for k in range(n):
        w = u32(a + 4 * k)
        if (w & 0xff800000) == 0xd2800000:
            regs[w & 31] = ((w >> 5) & 0xffff) << (((w >> 21) & 3) * 16)
        elif (w & 0xff800000) == 0xf2800000:
            r, sh = w & 31, ((w >> 21) & 3) * 16
            regs[r] = (regs.get(r, 0) & ~(0xffff << sh)) | (((w >> 5) & 0xffff) << sh)
        found.update(regs.values())
    return found


print('== param hook body')
pimpl = bl_target(pstubs[0] + 16) if pstubs else 0
pi = dis(pimpl, 51)
check('param impl builds both hashes 0x0607cd5541 and 0x0ee2ec2860 in its prologue', {0x0607cd5541, 0x0ee2ec2860} <= consts(pimpl, 16), hex(pimpl))
first_call = next((k for k, x in enumerate(pi) if x.split()[0] in ('bl', 'blr', 'br', 'ret')), None)
cmp_at = next((k for k, x in enumerate(pi) if x.split()[0] in ('cmp', 'ccmp')), None)
check('param impl: hash compare before any call', cmp_at is not None and first_call is not None and cmp_at < first_call, f'cmp +{cmp_at * 4:#x}, first call +{first_call * 4:#x}')
check('param impl: reads the 9th argument (return address) from the caller stack before any call', any(x.startswith('ldr') and '[sp, #0x30]' in x for x in pi[:first_call]))
check('param impl: a tail `br` (other hashes: original result untouched) and a `blr` (original called first on the two hashes)',
      any(x.startswith('br ') for x in pi) and any(x.startswith('blr ') for x in pi))
ev = next((pimpl + 4 * k + (sx(u32(pimpl + 4 * k) & 0x3ffffff, 26) << 2) for k, x in enumerate(pi) if x.startswith('b #') and k > first_call), None)
check('param impl ends with a tail jump to the decision function', ev is not None and 0 < ev < text_end, hex(ev or 0))

print('== identity function (resolve)')
callers = {}
for a in range(0, text_end, 4):
    t = bl_target(a)
    if t in gplt:
        callers.setdefault(gplt[t], []).append(a)
check('each game import is called from exactly one place', all(len(callers.get(n, [])) == 1 for n in GAME_IMPORTS), {n[8:36]: [hex(a) for a in v] for n, v in callers.items()})
order = [n for _, n in sorted((v[0], n) for n, v in callers.items())]
check('call order in the code: module_accessor, category, kind, entry_id, then get_kind and get_int (accessor-taking calls last)',
      order == [GAME_IMPORTS[0], GAME_IMPORTS[1], GAME_IMPORTS[2], GAME_IMPORTS[3], GAME_IMPORTS[4], GAME_IMPORTS[5]], [n[8:36] for n in order])
first = min(v[0] for v in callers.values()) if callers else 0
start = next((a for a in range(first, first - 0x40, -4) if 'sp, #-' in dis(a, 1)[0]), 0)
rs = dis(start, (max(v[0] for v in callers.values()) - start) // 4 + 12) if start else []
k_id = next((k for k, x in enumerate(rs) if re.fullmatch(r'ldr w\d+, \[x1, #8\]', x)), None)
k_cat = next((k for k, x in enumerate(rs) if re.fullmatch(r'lsr w\d+, w\d+, #0x1c', x)), None)
k_bl = next((k for k, x in enumerate(rs) if x.startswith('bl ')), None)
check('resolve: object id read from [accessor+8], category = id >> 28 tested (cbnz) before the first game call',
      None not in (k_id, k_cat, k_bl) and k_id < k_cat < k_bl and rs[k_cat + 1].startswith('cbnz'), rs[:8])
k_ma = (callers[GAME_IMPORTS[0]][0] - start) // 4
check('resolve: module_accessor(id) result compared with the parent and mismatch leaves before any further call',
      rs[k_ma + 1].startswith('cmp x') and rs[k_ma + 2].startswith('b.ne'), rs[k_ma:k_ma + 3])
k_c = (callers[GAME_IMPORTS[1]][0] - start) // 4
check('resolve: category(id) must be 0 (cbz) to reach the remaining calls', rs[k_c + 1].startswith('cbz w0'), rs[k_c:k_c + 2])
k_gi = (callers[GAME_IMPORTS[5]][0] - start) // 4
check('resolve: get_int is called with w1 = 0x10000000 (FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID)', rs[k_gi - 1] == 'mov w1, #0x10000000', rs[k_gi - 2:k_gi + 1])
check('resolve: entry id range test is unsigned `cmp w, #7` (negative ids rejected)', any(re.fullmatch(r'cmp w\d+, #7', x) for x in rs[k_gi:k_gi + 8]), rs[k_gi + 1:k_gi + 8])
rcall = [a for a in range(0, text_end, 4) if bl_target(a) == start]
check('resolve has exactly one caller', len(rcall) == 1, [hex(a) for a in rcall])
if rcall and ev:
    span = dis(ev, (rcall[0] - ev) // 4)
    check('decision function: reads tpidrro_el0 (per-thread guard) before calling resolve', any(x == 'mrs x8, tpidrro_el0' or x.startswith('mrs') and 'tpidrro_el0' in x for x in span))
    check('decision function: [x0+8] parent and [parent+0x50] back-pointer loads precede the resolve call',
          any(re.fullmatch(r'ldr x\d+, \[x0, #8\]', x) for x in span) and any(re.fullmatch(r'ldr x\d+, \[x\d+, #0x50\]', x) for x in span))
    wide = set()
    for a in range(0, text_end - 4, 4):
        w, w2 = u32(a), u32(a + 4)
        if (w & 0x7f800000) == 0x52800000 and (w2 & 0x7f800000) == 0x72800000 and (w & 31) == (w2 & 31) and ((w2 >> 21) & 3) == 1:
            wide.add(((w >> 5) & 0xffff) | (((w2 >> 5) & 0xffff) << 16))
    check('vtable constants 0x4f89490 and 0x4f73738 are built in the code (mov/movk pairs)', {0x4f89490, 0x4f73738} <= wide,
          sorted(hex(v) for v in wide if 0x4f00000 <= v < 0x5000000))

print('== strings')
for s in (b'sd:/ultimate/mii_customizer_log.txt', b'sd:/ultimate/mii_customizer/loadouts.txt', b'mc_loadouts 1', b'mc|', b'0.2.0', b'override',
          b'mii_customizer', b'words_differ', b'weight', b'walk_speed_max', b'loadout_reject', b'out_of_range', b'too_many_ids', b'bad_version_line'):
    check(f'string {s.decode()!r} present', d.find(s) >= 0)
check('the loadout path occurs once (one open site, read-only by source rule below)', d.count(b'sd:/ultimate/mii_customizer/loadouts.txt') == 1)

print('== source rules')
src = ''
files = sorted((MOD / 'plugin/src').glob('*.rs'))
for f in files:
    for line in f.read_text(encoding='utf-8').splitlines():
        src += line.split('//')[0] + '\n'
for pat, why in ((r'\.unwrap\(\)', 'unwrap'), (r'\.expect\(', 'expect'), (r'\bpanic!', 'panic!'), (r'unreachable!|todo!|unimplemented!|assert!|assert_eq!|debug_assert', 'panicking macro'),
                 (r'skyline::hook\b|#\[\s*hook|install_hook','skyline hook macro (its expansion unwraps)'), (r'\bMutex\b|\bRwLock\b|thread::|\bVec<|\bBox<|format!|String::|to_string\(|to_owned\(', 'lock/thread/heap type'),
                 (r'Patch::|patching', 'instruction patching'), (r'\w\[[^\]]*\](?!\s*[;=,)])', 'unchecked indexing expression'),
                 (r'\bstatic mut\b', 'static mut'), (r'\.parse::<|parse\(\)\s*\.', 'std number parsing (accepts inf/nan/exponents)'),
                 (r'fs::write|create_dir|remove_file|remove_dir|rename\(|\.truncate\(', 'file writing/removal other than the log append')):
    hits = re.findall(pat, src)
    check(f'no {why} in plugin/src code', not hits, hits[:3])
check('files in plugin/src', [p.name for p in files] == ['lib.rs', 'loadout.rs', 'logic.rs'])
lib = (MOD / 'plugin/src/lib.rs').read_text(encoding='utf-8')
check('LOADOUT_PATH is used by File::open only (never OpenOptions / create / write)',
      len(re.findall(r'LOADOUT_PATH', lib)) == 4 and 'std::fs::File::open(LOADOUT_PATH)' in lib and len(re.findall(r'OpenOptions', lib)) == 1 and '.open(LOG_PATH)' in lib)
check('smash:: items used in lib.rs are the documented ones only',
      sorted(set(x.rstrip(':') for x in re.findall(r'smash::[\w:]+', src))) == ['smash::app', 'smash::app::lua_bind::WorkModule', 'smash::lib::lua_const'] and
      sorted(set(re.findall(r'(?:sv_battle_object|utility|WorkModule)::(\w+)', src))) == ['category', 'entry_id', 'get_category', 'get_int', 'get_kind', 'kind', 'module_accessor'],
      (sorted(set(x.rstrip(':') for x in re.findall(r'smash::[\w:]+', src))), sorted(set(re.findall(r'(?:sv_battle_object|utility|WorkModule)::(\w+)', src)))))
check('pure modules use no skyline/smash/std item', not re.search(r'\b(skyline|smash|std)::',
      ''.join(l.split('//')[0] + '\n' for f in ('logic.rs', 'loadout.rs') for l in (MOD / 'plugin/src' / f).read_text(encoding='utf-8').splitlines())))

print('== crate')
toml = (MOD / 'plugin/Cargo.toml').read_text(encoding='utf-8')
lock = (MOD / 'plugin/Cargo.lock').read_text(encoding='utf-8')
check('crate version 0.2.0', 'version = "0.2.0"' in toml and 'name = "mii_customizer"\nversion = "0.2.0"' in lock)
pk = re.findall(r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"\n(?:source = "([^"]+)"\n)?', lock)
skl = [p for p in pk if p[0] == 'skyline']
check('Cargo.lock has a single `skyline` package, at 6b52d32 through the bare git URL',
      len(skl) == 1 and skl[0][2] == f'git+https://github.com/ultimate-research/skyline-rs#{SKYLINE_REV}', skl)
sm = [p for p in pk if p[0] == 'skyline_smash']
check('Cargo.lock has a single `skyline_smash` package, at 315e4e8', len(sm) == 1 and sm[0][2] == f'git+https://github.com/ultimate-research/skyline-smash#{SMASH_REV}', sm)
check('Cargo.toml names both git dependencies without rev (as the reference plugin documents)',
      re.search(r'^skyline = \{ git = "https://github.com/ultimate-research/skyline-rs" \}$', toml, re.M) and
      re.search(r'^skyline_smash = \{ git = "https://github.com/ultimate-research/skyline-smash", features = \["weak_l2cvalue"\] \}$', toml, re.M))
check('no smashline / smash_script / acmd dependency', not re.search(r'smashline|smash_script|acmd', lock))
ref = (WS / 'mods/ssbu_mod_new/src/pgwr/plugin/Cargo.lock').read_text(encoding='utf-8')
refpk = set(re.findall(r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"\n(?:source = "([^"]+)"\n)?', ref))
extra = [p for p in pk if p not in refpk and p[0] != 'mii_customizer']
check('every locked dependency (name, version, source) also appears in the reference plugin lock', not extra, extra)
git = {p[0]: p[2].split('#')[-1] for p in pk if p[2].startswith('git+')}
print('   git pins:', git)

print('== example loadout file')
ex = EXAMPLE.read_bytes()
lines = ex.decode('utf-8').split('\n')
vals = [l.split() for l in lines[1:] if l.strip() and not l.lstrip().startswith('#')]
check('example: first line `mc_loadouts 1`, LF endings, no BOM, under 16 KiB', lines[0] == 'mc_loadouts 1' and b'\r' not in ex and not ex.startswith(b'\xef\xbb\xbf') and len(ex) <= 16384)
check('example: exactly 0000f589 weight 130.0 and walk_speed_max 1.6; 0000f58b has no value line',
      vals == [['0000f589', 'weight', '130.0'], ['0000f589', 'walk_speed_max', '1.6']], vals)

print(f'\n{ok} passed, {bad} failed')
if '--write-manifest' in sys.argv and not bad:
    manifest = {
        'name': 'mii_customizer',
        'version': '0.2.0',
        'variant': 'override',
        'status': 'not installed, not tested on hardware',
        'purpose': 'first behaviour-changing build: weight / walk_speed_max of a Mii Gunner come from a mod-owned loadout file, keyed by the saved-fighter ID of the fighter\'s player; everything else returns the original value',
        'date': '2026-10-05',
        'nro': {'file': 'libmii_customizer.nro', 'sha256': sha(NRO), 'size': len(d),
                'card_path': 'atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro (replaces 0.1.0-diag)'},
        'example_loadout': {'file': 'example/loadouts.txt', 'sha256': sha(EXAMPLE), 'size': len(ex),
                            'card_path': 'ultimate/mii_customizer/loadouts.txt', 'format': 'mc_loadouts 1 (prompts/P4-OVERRIDE-SLICE.md)',
                            'content': {'0000f589': {'weight': 130.0, 'walk_speed_max': 1.6}, '0000f58b': 'absent on purpose (vanilla control)'}},
        'log_file': 'sd:/ultimate/mii_customizer_log.txt (append)',
        'loadout_file': 'sd:/ultimate/mii_customizer/loadouts.txt (read once at load, never written)',
        'target_image': {'title': 'SSBU 13.0.4 main', 'flat_image': 'gamedata/ssbu-13.0.4/main.bin (workspace-relative)',
                         'sha256': 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'},
        'hooks': [{'name': n, 'offset': f'0x{o:x}', 'kind': kind, 'installed_only_if_words_match': True,
                   'expected_words': [f'0x{w:08x}' for w in ws], 'log_events': ev, 'what': what} for n, o, ws, ev, what, kind in SITES],
        'hooks_removed_since_0.1.0': ['0x179e440 (L1)', '0x17c8210 (L2)'],
        'override': {
            'hashes': {'weight': '0x0607cd5541', 'walk_speed_max': '0x0ee2ec2860'},
            'accepted_ranges_proposal_not_declared_safe': {'weight': [60.0, 140.0], 'walk_speed_max': [0.5, 2.0]},
            'object_guard': '[x0] == base+0x4f89490, parent = [x0+8] != 0, [parent+0x50] == x0',
            'identity': 'skyline_smash 315e4e8: utility::get_category(accessor) (binding inline, field battle_object_id), sv_battle_object::{module_accessor,category,kind,entry_id}(id), utility::get_kind(accessor), WorkModule::get_int(accessor, FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID)',
            'constants': {'FIGHTER_KIND_MIIGUNNER': '0x4a', 'BATTLE_OBJECT_CATEGORY_FIGHTER': '0x0', 'FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID': '0x10000000'},
            'cache': 'none; identity and slot ID are re-read on every request',
        },
        'game_imports': GAME_IMPORTS,
        'static_reads': {'T': '0x5307760', 'saved_fighter_id_u32': 'T + 0xe58 + p*0x240', 'special_bytes_4 (L4 only)': 'T + 0xa2 + p*0x1c8', 'p': '0..7'},
        'crate': {'cargo_toml_sha256': sha(MOD / 'plugin/Cargo.toml'), 'cargo_lock_sha256': sha(MOD / 'plugin/Cargo.lock'),
                  'lib_rs_sha256': sha(MOD / 'plugin/src/lib.rs'), 'logic_rs_sha256': sha(MOD / 'plugin/src/logic.rs'),
                  'loadout_rs_sha256': sha(MOD / 'plugin/src/loadout.rs'), 'build_script_sha256': sha(MOD / 'build-plugin.sh')},
        'dependencies': {
            'skyline': f'0.6.0 git https://github.com/ultimate-research/skyline-rs rev {SKYLINE_REV}',
            'skyline_smash': f'0.1.0 git https://github.com/ultimate-research/skyline-smash rev {SMASH_REV} (feature weak_l2cvalue)',
            'nnsdk (via skyline_smash)': '0.6.2 git https://github.com/ultimate-research/nnsdk-rs rev ' + git.get('nnsdk', '?'),
            'all_locked': {f'{n} {v}': (s or 'path') for n, v, s in pk},
        },
        'toolchain': {'cargo_skyline': '3.5.0', 'compiler': 'rustc 1.95.0-nightly (a423f68a0 2026-02-13), cargo-skyline toolchain', 'target': 'aarch64-skyline-switch'},
        'build_command': 'bash mods/mii_customizer/build-plugin.sh   (= cd plugin && CARGO_TARGET_DIR=../builds/.cache/plugin-target cargo skyline build --release -- --offline)',
        'offline_checks': {'step0': 'scratch/2026-10-04_P4-OVERRIDE-SLICE/step0.py', 'build': 'scratch/2026-10-04_P4-OVERRIDE-SLICE/check_build.py',
                           'host_test': 'scratch/2026-10-04_P4-OVERRIDE-SLICE/run_host_test.sh', 'report': 'research/P4-OVERRIDE-SLICE.md'},
    }
    (PKG / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('wrote', (PKG / 'MANIFEST.json').relative_to(MOD).as_posix())
sys.exit(1 if bad else 0)
