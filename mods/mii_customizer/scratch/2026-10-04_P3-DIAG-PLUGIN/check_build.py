"""P3-DIAG-PLUGIN step 2: offline checks of the staged 0.1.0-diag NRO, then (re)write its MANIFEST.json.
usage: python check_build.py [--write-manifest]      exit 0 = all checks pass
Reads builds/0.1.0-diag/libmii_customizer.nro, plugin/ and build-plugin.sh. Runs nothing."""
import hashlib, json, re, struct, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
WS = MOD.parents[1]
sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/builds/.cache/dk_cargo/python'))
import capstone
PKG = MOD / 'builds/0.1.0-diag'
NRO = PKG / 'libmii_customizer.nro'
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


SITES = [
    ('param', 0x4e53e0, [0xf9401c00, 0xf9400008, 0xf9401903, 0xd61f0060], 'L3/L4/L5', 'f32 getter thunk, vtable 0x4f89490/0x4f73738 slot +0x270'),
    ('store', 0x179e440, [0xf81e0ff3, 0xa9017bfd, 0x910043fd, 0x7100203f], 'L1', 'per-player record store (x0 = T, w1 = player, x2 = local struct)'),
    ('load', 0x17c8210, [0xa9bd57f6, 0xa9014ff4, 0xa9027bfd, 0x910083fd], 'L2', 'saved-fighter record loader (x0 = manager, w1 = id, x2 = out)'),
]

print('== container')
check('NRO0 magic at 0x10', d[0x10:0x14] == b'NRO0')
mod0 = u32(4)
check('MOD0 magic at header offset', d[mod0:mod0 + 4] == b'MOD0', hex(mod0))
check('file size equals NRO size field', u32(0x18) == len(d), len(d))
text_end = u32(0x24)

print('== hook table in the binary')
rec = b''.join(struct.pack('<Q4I', off, *w) for _, off, w, _, _ in SITES)
at = d.find(rec)
check('MC_SITES: three contiguous {u64 offset, u32 words[4]} records', at >= 0, hex(at))
for name, off, words, _, _ in SITES:
    check(f'  {name}: offset 0x{off:x} and its 4 expected words present', d.find(struct.pack('<Q4I', off, *words)) >= 0)
check('record order is param, store, load (index used by install_site)', at >= 0 and d.count(rec) == 1)

print('== entry stubs')
STUB = [0xa9bf7bfd, 0x910003fd, 0xd10043ff, 0xf90003fe, None, 0x910043ff, 0xa8c17bfd, 0xd65f03c0]
stubs = []
for a in range(0, text_end, 4):
    if all(s is None or u32(a + 4 * k) == s for k, s in enumerate(STUB)):
        w = u32(a + 16)
        if w >> 26 == 0x25:
            stubs.append((a, a + 16 + (sx(w & 0x3ffffff, 26) << 2)))
print('   stubs (address -> bl target):', [(hex(a), hex(t)) for a, t in stubs])
check('exactly three stubs: stp x29,x30 / mov x29,sp / sub sp,16 / str x30,[sp] / bl / add sp,16 / ldp / ret', len(stubs) == 3)
check('stub bl targets are three distinct addresses inside .text', len({t for _, t in stubs}) == 3 and all(0 < t < text_end for _, t in stubs))


def body(a, n=57):  # 57 words = the param impl up to its final `br`; the others are shorter
    out = []
    for k in range(n):
        w = u32(a + 4 * k)
        i = next(md.disasm(d[a + 4 * k:a + 4 * k + 4], a + 4 * k), None)
        out.append((a + 4 * k, w, i.mnemonic if i else '', i.op_str if i else ''))
    return out


def consts(ins):
    regs, found = {}, set()
    for _, w, m, o in ins:
        if (w & 0xff800000) == 0xd2800000:  # movz x
            regs[w & 31] = ((w >> 5) & 0xffff) << (((w >> 21) & 3) * 16)
        elif (w & 0xff800000) == 0xf2800000:  # movk x
            r = w & 31
            sh = ((w >> 21) & 3) * 16
            regs[r] = (regs.get(r, 0) & ~(0xffff << sh)) | (((w >> 5) & 0xffff) << sh)
        for v in regs.values():
            found.add(v)
    return found


param = None
for a, t in stubs:
    ins = body(t)
    c = consts(ins[:16])  # the constants are built in the prologue; a longer window would run into the next function
    if 0x0607cd5541 in c and 0x0ee2ec2860 in c and param is None:
        param = (a, t, ins)
check('one impl builds both hashes 0x0607cd5541 and 0x0ee2ec2860', param is not None, hex(param[1]) if param else '')
if param:
    ins = param[2]
    first_branch = next((k for k, x in enumerate(ins) if x[2] in ('bl', 'blr', 'br', 'ret')), None)
    cmp_at = next((k for k, x in enumerate(ins) if x[2] in ('cmp', 'ccmp')), None)
    check('param impl: hash compare happens before any call', cmp_at is not None and first_branch is not None and cmp_at < first_branch,
          f'cmp at +{cmp_at * 4:#x}, first call/branch-reg at +{first_branch * 4:#x}')
    check('param impl: has a tail `br` (pass-through path) and a `blr` (logged path)',
          any(x[2] == 'br' for x in ins) and any(x[2] == 'blr' for x in ins))
    check('param impl: reads the 9th argument from the caller stack before any call',
          any(x[2] == 'ldr' and '[sp, #0x' in x[3] for x in ins[:first_branch]))

print('== strings')
for s in (b'sd:/ultimate/mii_customizer_log.txt', b'mc|', b'0.1.0', b'diag', b'mii_customizer', b'words_differ',
          b'weight', b'walk_speed_max'):
    check(f'string {s.decode()!r} present', d.find(s) >= 0)

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
imports = []
for i in range((strtab - symtab) // 24):
    name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', d, symtab + 24 * i)
    e = d.find(b'\0', strtab + name)
    s = d[strtab + name:e].decode('latin1')
    if s and shndx == 0:
        imports.append(s)
print('   ' + ' '.join(imports))
check('imports A64HookFunction and getRegionAddress', 'A64HookFunction' in imports and 'getRegionAddress' in imports)
check('does not import A64InlineHook, sky_memcpy or any thread-creation symbol',
      not any(x in imports for x in ('A64InlineHook', 'sky_memcpy', 'pthread_create')) and not any('CreateThread' in x for x in imports))
ALLOWED = re.compile(r'^(__nro_header_start|skyline_tcp_send_raw|A64HookFunction|getRegionAddress|free|malloc|memset|memcpy|posix_memalign|pthread_\w+|_ZN2nn2fs\w+)$')
other = [x for x in imports if not ALLOWED.match(x)]
check('no imported game (lua_bind / app::) symbol; only skyline, libc, pthread and nn::fs', not other, other)

print('== source rules')
src = ''
for f in sorted((MOD / 'plugin/src').glob('*.rs')):
    for line in f.read_text().splitlines():
        code = line.split('//')[0]
        src += code + '\n'
for pat, why in ((r'\.unwrap\(\)', 'unwrap'), (r'\.expect\(', 'expect'), (r'\bpanic!', 'panic!'), (r'unreachable!|todo!|unimplemented!|assert!|assert_eq!', 'panicking macro'),
                 (r'skyline::hook|install_hook', 'skyline hook macro (its expansion unwraps)'), (r'\bMutex\b|\bRwLock\b|thread::|\bVec<|\bBox<|format!|String::', 'lock/thread/heap type'),
                 (r'Patch::|patching', 'instruction patching'), (r'\w\[[^\]]*\](?!\s*[;=,)])', 'unchecked indexing expression')):
    hits = re.findall(pat, src)
    check(f'no {why} in plugin/src code', not hits, hits[:3])
check('files in plugin/src', sorted(p.name for p in (MOD / 'plugin/src').glob('*')) == ['lib.rs', 'logic.rs'])

print('== crate')
toml = (MOD / 'plugin/Cargo.toml').read_text()
lock = (MOD / 'plugin/Cargo.lock').read_text()
check('crate version 0.1.0', 'version = "0.1.0"' in toml)
REV = '6b52d321275639f26c2371d8142550ba0013a5e4'
check('skyline pinned to 6b52d32 in Cargo.toml and Cargo.lock', REV in toml and f'skyline-rs?rev={REV}#{REV}' in lock)
check('no smashline / skyline_smash / smash dependency', not re.search(r'smashline|skyline.smash|name = "smash', lock))
deps = dict(re.findall(r'name = "([^"]+)"\nversion = "([^"]+)"', lock))
print('   lock:', deps)

print(f'\n{ok} passed, {bad} failed')
if '--write-manifest' in sys.argv and not bad:
    manifest = {
        'name': 'mii_customizer',
        'version': '0.1.0',
        'variant': 'diag',
        'status': 'not installed, not tested on hardware',
        'purpose': 'LOG-ONLY diagnostic for the first console gate; calls each original with unchanged arguments and returns its result unchanged',
        'date': '2026-10-04',
        'nro': {'file': 'libmii_customizer.nro', 'sha256': sha(NRO), 'size': len(d)},
        'log_file': 'sd:/ultimate/mii_customizer_log.txt',
        'target_image': {'title': 'SSBU 13.0.4 main', 'flat_image': 'gamedata/ssbu-13.0.4/main.bin (workspace-relative)',
                         'sha256': 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'},
        'hooks': [{'name': n, 'offset': f'0x{o:x}', 'kind': 'replace (A64HookFunction), installed only if the 4 words match',
                   'expected_words': [f'0x{w:08x}' for w in ws], 'log_events': ev, 'what': what} for n, o, ws, ev, what in SITES],
        'static_reads': {'T': '0x5307760', 'saved_fighter_id_u32': 'T + 0xe58 + p*0x240', 'special_bytes_4': 'T + 0xa2 + p*0x1c8', 'p': '0..7'},
        'crate': {'cargo_toml_sha256': sha(MOD / 'plugin/Cargo.toml'), 'cargo_lock_sha256': sha(MOD / 'plugin/Cargo.lock'),
                  'lib_rs_sha256': sha(MOD / 'plugin/src/lib.rs'), 'logic_rs_sha256': sha(MOD / 'plugin/src/logic.rs'),
                  'build_script_sha256': sha(MOD / 'build-plugin.sh')},
        'dependencies': {'skyline': f'0.6.0 git https://github.com/ultimate-research/skyline-rs rev {REV}',
                         'skyline_macro': deps.get('skyline_macro'), 'libc-nnsdk': deps.get('libc-nnsdk'), 'nnsdk': deps.get('nnsdk')},
        'toolchain': {'cargo_skyline': '3.5.0', 'compiler': 'rustc 1.95.0-nightly (a423f68a0 2026-02-13), cargo-skyline toolchain', 'target': 'aarch64-skyline-switch'},
        'build_command': 'bash mods/mii_customizer/build-plugin.sh   (= cd plugin && CARGO_TARGET_DIR=../builds/.cache/plugin-target cargo skyline build --release -- --offline)',
        'offline_checks': {'step0': 'scratch/2026-10-04_P3-DIAG-PLUGIN/step0.py', 'build': 'scratch/2026-10-04_P3-DIAG-PLUGIN/check_build.py',
                           'host_test': 'scratch/2026-10-04_P3-DIAG-PLUGIN/run_host_test.sh', 'report': 'research/P3-DIAG-PLUGIN.md'},
        'variants_not_built': ['0.1.0-override: its condition (entry id through an exported function the pinned bindings declare) is not met'],
    }
    (PKG / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('wrote', (PKG / 'MANIFEST.json').relative_to(MOD).as_posix())
sys.exit(1 if bad else 0)
