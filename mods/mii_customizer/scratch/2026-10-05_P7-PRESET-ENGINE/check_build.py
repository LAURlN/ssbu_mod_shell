"""P7-PRESET-ENGINE: offline checks of the staged 0.3.0-presets NRO, then (re)write its MANIFEST.json.
usage: python check_build.py [--write-manifest]      exit 0 = all checks pass
Reads builds/0.3.0-presets/, plugin/ and build-plugin.sh. Runs nothing."""
import hashlib, json, re, struct, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
WS = MOD.parents[1]
sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/builds/.cache/dk_cargo/python'))
import capstone
PKG = MOD / 'builds/0.3.0-presets'
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


def b_target(a):
    w = u32(a)
    return a + (sx(w & 0x3ffffff, 26) << 2) if w >> 26 == 0x05 else None


SITE = ('param', 0x4e53e0, [0xf9401c00, 0xf9400008, 0xf9401903, 0xd61f0060], 'RQ/L3/OV/L4/L5/F5/X2',
        'f32 getter thunk, slot +0x270 of vtables 0x4f89490/0x4f73738; the only hook',
        'replace (A64HookFunction): unknown hash or x2 != 0 -> tail jump to the original; otherwise original called first, its result returned unless every override condition holds')
REMOVED_CUSTOM = [0xf9401c00, 0xf9400008, 0xf9401d03, 0xd61f0060]
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
MIX = 0x9e3779b97f4a7c15

print('== container')
check('NRO0 magic at 0x10', d[0x10:0x14] == b'NRO0')
mod0 = u32(4)
check('MOD0 magic at header offset', d[mod0:mod0 + 4] == b'MOD0', hex(mod0))
check('file size equals NRO size field', u32(0x18) == len(d), len(d))
text_end = u32(0x24)
bss_size = u32(0x38)
check('bss holds the three file buffers (512 KiB + 16 KiB + 16 KiB) and the tables', 512 * 1024 + 2 * 16 * 1024 < bss_size < 1024 * 1024, bss_size)

print('== hook table in the binary')
rec = struct.pack('<Q4I', SITE[1], *SITE[2])
at = d.find(rec)
check('MC_SITES: exactly one {u64 offset, u32 words[4]} record, for 0x4e53e0', at >= 0 and d.count(rec) == 1, hex(at))
check('no site record for 0x4e53f0 (log-only hook of 0.2.0) or the 0.1.0 sites',
      all(d.find(struct.pack('<Q', o)) < 0 for o in (0x4e53f0, 0x179e440, 0x17c8210)))
check('the four instruction words of 0x4e53f0 occur nowhere (its stub and fallback are gone)',
      d.find(struct.pack('<4I', *REMOVED_CUSTOM)) < 0)

print('== imports and exports')
dyn = mod0 + struct.unpack_from('<i', d, mod0 + 4)[0]
tags = {}
while True:
    t, v = struct.unpack_from('<QQ', d, dyn)
    dyn += 16
    if t == 0:
        break
    tags[t] = v
symtab, strtab = tags[6], tags[5]
syms = []
for i in range((strtab - symtab) // 24):
    name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', d, symtab + 24 * i)
    e = d.find(b'\0', strtab + name)
    syms.append((d[strtab + name:e].decode('latin1'), shndx, value))
names = [(s, shndx) for s, shndx, _ in syms]
imports = [s for s, shndx in names if s and shndx == 0]
exports = {s: v for s, shndx, v in syms if s and shndx != 0}
print('   imports: ' + ' '.join(imports))
print('   exports: ' + ' '.join(f'{s}@{v:#x}' for s, v in exports.items()))
check('imports A64HookFunction and getRegionAddress', 'A64HookFunction' in imports and 'getRegionAddress' in imports)
check('does not import A64InlineHook, sky_memcpy or any thread-creation symbol',
      not any(x in imports for x in ('A64InlineHook', 'sky_memcpy', 'pthread_create')) and not any('CreateThread' in x for x in imports))
game = sorted(x for x in imports if x.startswith('_ZN3app') or x.startswith('_ZN3lib'))
check('game symbols imported: exactly the six identity functions of 0.2.0', game == sorted(GAME_IMPORTS), game)
ALLOWED = re.compile(r'^(__nro_header_start|skyline_tcp_send_raw|A64HookFunction|getRegionAddress|free|malloc|realloc|calloc|memset|memcpy|memmove|memcmp|bcmp|strlen|posix_memalign|pthread_\w+|_ZN2nn2fs\w+)$')
other = [x for x in imports if not ALLOWED.match(x) and x not in GAME_IMPORTS]
check('everything else imported is skyline, libc, pthread or nn::fs', not other, other)
fs = sorted(re.sub(r'^_ZN2nn2fs\d+', '', x) for x in imports if x.startswith('_ZN2nn2fs'))
fs_short = [re.match(r'[A-Za-z]+?(?=E[A-Z]|Ev|EP|ER|$)', x).group(0) if re.match(r'[A-Za-z]+?(?=E[A-Z]|Ev|EP|ER|$)', x) else x for x in fs]
print('   nn::fs: ' + ' '.join(fs_short))
check('nn::fs imports: DeleteFile and RenameFile are present (save_loadouts), no directory creation or deletion',
      any(x.startswith('DeleteFile') for x in fs) and any(x.startswith('RenameFile') for x in fs)
      and not any(re.match(r'CreateDirectory|DeleteDirectory|CleanDirectory', x) for x in fs), fs_short)

# PLT stubs of the imports: adrp x16 ; ldr x17,[x16,#imm] ; add x16 ; br x17
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

print('== entry stub')
PARAM_STUB = [0xa9bf7bfd, 0x910003fd, 0xd10043ff, 0xf90003fe, None, 0x910043ff, 0xa8c17bfd, 0xd65f03c0]
pstubs = [a for a in range(0, text_end, 4) if all(s is None or u32(a + 4 * k) == s for k, s in enumerate(PARAM_STUB)) and bl_target(a + 16)]
check('exactly one param stub: stp x29,x30 / mov x29,sp / sub sp,16 / str x30,[sp] / bl / add sp,16 / ldp / ret (unchanged since 0.1.0)', len(pstubs) == 1, [hex(a) for a in pstubs])
check('no second stub that saves q0-q7 (the 0.2.0 custom stub)', 'stp q0, q1, [sp, #0x60]' not in dis(pstubs[0], 48) if pstubs else False)


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


print('== hot path: mc_param_impl up to its first `br` (every request for an unknown hash)')
pimpl = bl_target(pstubs[0] + 16) if pstubs else 0
pi = dis(pimpl, 64)
k_br = next((k for k, x in enumerate(pi) if x.startswith('br ')), None)
head = pi[:k_br + 1] if k_br is not None else []
for k, x in enumerate(head):
    print(f'   {pimpl + 4 * k:#x}: {x}')
mn = [x.split()[0] for x in head]
check('miss path is straight-line code of at most 32 instructions ending in `br`', 0 < len(head) <= 32, len(head))
check('miss path: no call (bl/blr), no return, no stack write, no sp change, no exclusive (atomic RMW) instruction',
      not any(m in ('bl', 'blr', 'ret', 'stp', 'str', 'strb', 'stur', 'sub', 'ldxr', 'stxr', 'ldaxr', 'stlxr', 'svc') and (m != 'sub' or 'sp' in x) for m, x in zip(mn, head))
      and not any(re.search(r'\[sp[^\]]*\]!|\], #', x) for x in head), [x for x in head if x.split()[0] in ('bl', 'blr', 'str', 'stp')])
check('miss path: builds the mix constant 0x9e3779b97f4a7c15 and has exactly one multiply', MIX in consts(pimpl, len(head)) and mn.count('mul') == 1)
loads = [x for x in head if x.split()[0] in ('ldr', 'ldrb')]
check('miss path: four loads (caller return address, probe bound, table key, trampoline pointer)', len(loads) == 4 and any('[sp]' in x for x in loads), loads)
k_loop = [k for k, x in enumerate(head) if x.startswith('cbnz w') and int(x.split('#')[1], 16) < pimpl + 4 * k]
k_key = next((k for k, x in enumerate(head) if re.fullmatch(r'ldr x\d+, \[x\d+, #0x[0-9a-f]+\]', x)), None)
check('miss path: one backward branch (the probe loop), bounded by a counter that is decremented',
      len(k_loop) == 1 and any(re.fullmatch(r'sub w\d+, w\d+, #1', x) for x in head), [head[k] for k in k_loop])
empty_exit = head[k_key + 1] if k_key is not None else ''
check('miss path: an empty slot (key 0) leaves the loop at once (`cbz` right after the key load)', empty_exit.startswith('cbz x'), empty_exit)
check('miss path: the probe bound 0 (no table) skips the loop', any(x.startswith('cbz w') for x in head[:k_key or 0]))
check('miss path: ends by loading the trampoline pointer and `br` to it when it is not null',
      head[-3].startswith('ldr x') and head[-2].startswith('cbz x') and head[-1].startswith('br x'), head[-3:])
exit_at = int(empty_exit.split('#')[1], 16) if empty_exit.startswith('cbz') else 0
k_exit = (exit_at - pimpl) // 4
n_first = (k_key + 2) + (len(head) - k_exit) if k_key is not None else -1
loop_start = int(head[k_loop[0]].split('#')[1], 16) if k_loop else 0
per_slot = k_loop[0] - (loop_start - pimpl) // 4 + 1 if k_loop else -1
print(f'   instructions on a miss: {n_first} when the home slot is empty; {per_slot} more per further examined slot (bounded by probe_max)')
check('miss path cost as documented: 20 instructions with an empty home slot, 9 per further slot', (n_first, per_slot) == (20, 9), (n_first, per_slot))
hit = dis(pimpl + 4 * len(head), 8)
k_tail = next((k for k, x in enumerate(hit) if x.startswith('b #')), None)
known = b_target(pimpl + 4 * (len(head) + k_tail)) if k_tail is not None else None
check('a known hash leaves by a tail jump (`b`) to the second function, with the stack argument put back',
      known is not None and 0 < known < text_end and any(x == 'str x8, [sp]' for x in hit[:k_tail]), hit[:(k_tail or 0) + 1])

print('== known_request / decision function')
kn = dis(known, 140) if known else []
k_call = next((k for k, x in enumerate(kn) if x.startswith('blr ')), None)
check('known_request: tests x2 before the original is called (`cbz x2` / `cbnz x2`)',
      k_call is not None and any(re.match(r'cbn?z x2,', x) for x in kn[:k_call]), [x for x in kn[:k_call or 0] if 'x2' in x][:3])
check('known_request: has a tail `br` (x2 != 0: original result untouched) and a `blr` (x2 == 0: original called first)',
      any(x.startswith('br ') for x in kn) and k_call is not None)
NO_DEST = ('str', 'stp', 'strb', 'cmp', 'tst', 'cbz', 'cbnz', 'b', 'bl', 'br', 'blr', 'ret', 'nop', 'stxr', 'stlxr')
before_call = kn[:k_call + 1] if k_call is not None else []
arg_writes = [x for x in before_call if not x.startswith(NO_DEST + ('b.',)) and re.match(r'\w+ [xw][2-7]\b', x)]
check('known_request: up to the call of the original nothing writes x2-x7 except `mov x2, xzr` on the x2 == 0 path, and no float register is touched',
      arg_writes == ['mov x2, xzr'] and not any(re.search(r'\b[dsqv][0-7]\b', x) for x in before_call), arg_writes)
frag = sorted({bl_target(known + 4 * k) for k, x in enumerate(before_call) if x.startswith('bl #')})
frag_dis = {hex(t): dis(t, 4)[:next((k for k, x in enumerate(dis(t, 4)) if x == 'ret'), 3) + 1] for t in frag}
check('known_request: the `bl` targets before that call are outlined fragments of at most three instructions and `ret` that touch only x0/x1 copies, saved registers or a counter',
      all(v[-1] == 'ret' and all(re.match(r'(mov x(19|20), x[01]|ldp x2\d, x\d+, \[sp, #0x[12]0\]|ldxr w9, \[x8\]|add w9, w9, #1|stxr w10, w9, \[x8\]|ret)$', x) for x in v) for v in frag_dis.values()), frag_dis)
ev = next((b_target(known + 4 * k) for k, x in enumerate(kn) if x.startswith('b #') and k_call is not None and k > k_call), None)
check('known_request ends with a tail jump to the decision function', ev is not None and 0 < ev < text_end, hex(ev or 0))

print('== identity function (resolve), unchanged from 0.2.0')
callers = {}
for a in range(0, text_end, 4):
    t = bl_target(a)
    if t in gplt:
        callers.setdefault(gplt[t], []).append(a)
check('each game import is called from exactly one place', all(len(callers.get(n, [])) == 1 for n in GAME_IMPORTS), {n[8:36]: [hex(a) for a in v] for n, v in callers.items()})
order = [n for _, n in sorted((v[0], n) for n, v in callers.items())]
check('call order in the code: module_accessor, category, kind, entry_id, then get_kind and get_int (accessor-taking calls last)',
      order == GAME_IMPORTS, [n[8:36] for n in order])
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
check('resolve has exactly one caller, inside the decision function', len(rcall) == 1 and ev is not None and ev < rcall[0], [hex(a) for a in rcall])
if rcall and ev:
    span = dis(ev, (rcall[0] - ev) // 4)
    check('decision function: reads tpidrro_el0 (per-thread guard) before calling resolve', any(x.startswith('mrs') and 'tpidrro_el0' in x for x in span))
    check('decision function: [x0+8] parent and [parent+0x50] back-pointer loads precede the resolve call',
          any(re.fullmatch(r'ldr x\d+, \[x\d+, #8\]', x) for x in span) and any(re.fullmatch(r'ldr x\d+, \[x\d+, #0x50\]', x) for x in span))
wide = set()
for a in range(0, text_end - 4, 4):
    w, w2 = u32(a), u32(a + 4)
    if (w & 0x7f800000) == 0x52800000 and (w2 & 0x7f800000) == 0x72800000 and (w & 31) == (w2 & 31) and ((w2 >> 21) & 3) == 1:
        wide.add(((w >> 5) & 0xffff) | (((w2 >> 5) & 0xffff) << 16))
check('vtable constants 0x4f89490 and 0x4f73738 are built in the code (mov/movk pairs)', {0x4f89490, 0x4f73738} <= wide,
      sorted(hex(v) for v in wide if 0x4f00000 <= v < 0x5000000))

print('== save_loadouts: compiled in, not called')
save = exports.get('mc_save_loadouts')
check('`mc_save_loadouts` is an exported function inside .text', save is not None and 0 < save < text_end, hex(save or 0))
direct = [a for a in range(0, text_end, 4) if save and (bl_target(a) == save or b_target(a) == save)]
check('no `bl` / `b` anywhere in .text targets it', not direct, [hex(a) for a in direct])
ptrs = [a for a in range(0, len(d) - 7, 8) if save and struct.unpack_from('<Q', d, a)[0] == save]
in_symtab = [a for a in ptrs if symtab <= a < strtab]
check('its address is stored nowhere except its own symbol-table entry (no function pointer, no relocation addend)',
      save is not None and len(ptrs) == len(in_symtab) == 1, [hex(a) for a in ptrs])
check('the temporary file name occurs once', d.count(b'sd:/ultimate/mii_customizer/loadouts.new') == 1)

print('== strings')
for s in (b'sd:/ultimate/mii_customizer_log.txt', b'sd:/ultimate/mii_customizer/loadouts.txt', b'sd:/ultimate/mii_customizer/presets.txt',
          b'mc_loadouts 1', b'mc_loadouts 2', b'mc_presets 1', b'mc|', b'0.3.0', b'presets', b'mii_customizer', b'words_differ',
          b'weight', b'walk_speed_max', b'loadout_reject', b'presets_reject', b'out_of_range', b'too_many_ids', b'bad_version_line',
          b'unknown_preset', b'too_many_presets', b'too_many_hashes', b'dup_name', b'no_preset', b'explicit', b'|x2nz=', b'read_back_differs'):
    check(f'string {s.decode()!r} present', d.find(s) >= 0)
check('no L6 event text and no `hook_custom` left', d.find(b'hook_custom') < 0 and d.find(b'|l6=') < 0)

print('== source rules')
files = sorted((MOD / 'plugin/src').glob('*.rs'))
code = {}
for f in files:
    code[f.name] = ''.join(line.split('//')[0] + '\n' for line in f.read_text(encoding='utf-8').splitlines())
src = ''.join(code.values())
for pat, why in ((r'\.unwrap\(\)', 'unwrap'), (r'\.expect\(', 'expect'), (r'\bpanic!', 'panic!'), (r'unreachable!|todo!|unimplemented!|assert!|assert_eq!|debug_assert', 'panicking macro'),
                 (r'skyline::hook\b|#\[\s*hook|install_hook', 'skyline hook macro (its expansion unwraps)'), (r'\bMutex\b|\bRwLock\b|thread::|\bVec<|\bBox<|format!|String::|to_string\(|to_owned\(', 'lock/thread/heap type'),
                 (r'Patch::|patching', 'instruction patching'), (r'\w\[[^\]]*\](?!\s*[;=,)])', 'unchecked indexing expression'),
                 (r'\bstatic mut\b', 'static mut'), (r'\.parse::<|parse\(\)\s*\.', 'std number parsing (accepts inf/nan/exponents)'),
                 (r'fs::write|create_dir|remove_dir|\.truncate\(', 'directory change or whole-file write helper')):
    hits = re.findall(pat, src)
    check(f'no {why} in plugin/src code', not hits, hits[:3])
check('files in plugin/src', [p.name for p in files] == ['lib.rs', 'loadout.rs', 'logic.rs', 'preset.rs'])
lib = code['lib.rs']
a_save, b_save = lib.find('unsafe fn save_locked'), lib.find('fn save_loadouts')
outside = lib[:a_save] + lib[b_save:]
check('file creation, removal, rename and sync appear only inside `save_locked`',
      0 < a_save < b_save and not re.search(r'File::create|remove_file|fs::rename|sync_all|LOADOUT_TMP_PATH\b(?!:)', outside)
      and all(x in lib[a_save:b_save] for x in ('File::create(LOADOUT_TMP_PATH)', 'remove_file(LOADOUT_PATH)', 'fs::rename(LOADOUT_TMP_PATH, LOADOUT_PATH)')))
check('`save_locked` has one caller (`save_loadouts`), `save_loadouts` has one caller (`mc_save_loadouts`), which has none',
      len(re.findall(r'\bsave_locked\(', lib)) == 2 and len(re.findall(r'(?<!mc_)\bsave_loadouts\(', lib)) == 2 and len(re.findall(r'\bmc_save_loadouts\b', lib)) == 1,
      (len(re.findall(r'\bsave_locked\(', lib)), len(re.findall(r'(?<!mc_)\bsave_loadouts\(', lib)), len(re.findall(r'\bmc_save_loadouts\b', lib))))
check('the preset file is only read (`read_file(PRESET_PATH`), the log is the only OpenOptions user',
      len(re.findall(r'PRESET_PATH', lib)) == 4 and 'read_file(PRESET_PATH, buf)' in lib and len(re.findall(r'OpenOptions', lib)) == 1 and '.open(LOG_PATH)' in lib,
      len(re.findall(r'PRESET_PATH', lib)))
check('the hook table lookup precedes everything else in `mc_param_impl`',
      re.search(r'lr: u64,\n\) -> f32 \{\n(\s*\n)*\s*if PRESETS\.fields\.find\(x1\)\.is_none\(\) \{\n\s*return call_param\(', lib) is not None)
check('smash:: items used in lib.rs are the documented ones only',
      sorted(set(x.rstrip(':') for x in re.findall(r'smash::[\w:]+', src))) == ['smash::app', 'smash::app::lua_bind::WorkModule', 'smash::lib::lua_const'] and
      sorted(set(re.findall(r'(?:sv_battle_object|utility|WorkModule)::(\w+)', src))) == ['category', 'entry_id', 'get_category', 'get_int', 'get_kind', 'kind', 'module_accessor'])
check('pure modules use no skyline/smash/std item and no unsafe', not re.search(r'\b(skyline|smash|std)::|\bunsafe\b', code['logic.rs'] + code['loadout.rs'] + code['preset.rs']))
check('accepted kinds are one constant array in logic.rs, used by the one decide() call',
      'pub const ACCEPTED_KINDS: [i32; 1] = [KIND_MIIGUNNER];' in code['logic.rs'] and 'logic::decide(&ident, &logic::ACCEPTED_KINDS,' in lib)

print('== crate')
toml = (MOD / 'plugin/Cargo.toml').read_text(encoding='utf-8')
lock = (MOD / 'plugin/Cargo.lock').read_text(encoding='utf-8')
check('crate version 0.3.0', 'version = "0.3.0"' in toml and 'name = "mii_customizer"\nversion = "0.3.0"' in lock)
pk = re.findall(r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"\n(?:source = "([^"]+)"\n)?', lock)
skl = [p for p in pk if p[0] == 'skyline']
check('Cargo.lock has a single `skyline` package, at 6b52d32 through the bare git URL',
      len(skl) == 1 and skl[0][2] == f'git+https://github.com/ultimate-research/skyline-rs#{SKYLINE_REV}', skl)
sm = [p for p in pk if p[0] == 'skyline_smash']
check('Cargo.lock has a single `skyline_smash` package, at 315e4e8', len(sm) == 1 and sm[0][2] == f'git+https://github.com/ultimate-research/skyline-smash#{SMASH_REV}', sm)
old_lock = None
m = (MOD / 'builds/0.2.0-override/MANIFEST.json')
if m.is_file():
    old_lock = json.loads(m.read_text(encoding='utf-8'))['dependencies']['all_locked']
now_lock = {f'{n} {v}': (s or 'path') for n, v, s in pk}
check('locked dependencies are exactly those of 0.2.0 (only the crate itself changed version)',
      old_lock is not None and {k: v for k, v in now_lock.items() if not k.startswith('mii_customizer')} == {k: v for k, v in old_lock.items() if not k.startswith('mii_customizer')})
check('no smashline / smash_script / acmd dependency', not re.search(r'smashline|smash_script|acmd', lock))
git = {p[0]: p[2].split('#')[-1] for p in pk if p[2].startswith('git+')}

print('== example loadout file')
ex = EXAMPLE.read_bytes()
lines = ex.decode('utf-8').split('\n')
vals = [l.split() for l in lines[1:] if l.strip() and not l.lstrip().startswith('#')]
check('example: first line `mc_loadouts 2`, LF endings, ASCII, no BOM, under 16 KiB',
      lines[0] == 'mc_loadouts 2' and b'\r' not in ex and ex.isascii() and len(ex) <= 16384)
check('example: exactly one active line, `0000f589 preset <placeholder>`; 0000f58b has no line',
      vals == [['0000f589', 'preset', 'replace_with_preset_name']], vals)

print(f'\n{ok} passed, {bad} failed')
if '--write-manifest' in sys.argv and not bad:
    manifest = {
        'name': 'mii_customizer',
        'version': '0.3.0',
        'variant': 'presets',
        'status': 'not installed, not tested on hardware',
        'purpose': 'character stat presets per saved Mii: a Mii Gunner gets, for every field hash of the preset file, the value of the preset its saved-fighter ID names in the loadout file (explicit weight / walk_speed_max lines win); everything else returns the original value',
        'date': '2026-10-05',
        'nro': {'file': 'libmii_customizer.nro', 'sha256': sha(NRO), 'size': len(d),
                'card_path': 'atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro (replaces 0.2.0-override)'},
        'example_loadout': {'file': 'example/loadouts.txt', 'sha256': sha(EXAMPLE), 'size': len(ex),
                            'card_path': 'ultimate/mii_customizer/loadouts.txt', 'format': 'mc_loadouts 2 (prompts/P7-PRESET-ENGINE.md, contract B)',
                            'content': {'0000f589': 'preset replace_with_preset_name  <- PLACEHOLDER: replace with a name from presets.txt before installing; as delivered the line is rejected (unknown_preset) and the Mii is vanilla',
                                        '0000f58b': 'absent on purpose (vanilla control)'}},
        'preset_file': {'card_path': 'ultimate/mii_customizer/presets.txt', 'format': 'mc_presets 1 (contract A)',
                        'not_in_this_package': 'generated from the user\'s own game file by tools/stat-presets into workspace gamedata/mii_customizer/P6-PRESET-DATA/presets.txt; the coordinator copies it to the card',
                        'limits': {'bytes': 512 * 1024, 'presets': 128, 'fields_per_preset': 48, 'distinct_field_hashes': 48, 'name': '[a-z0-9_]{1,31}'}},
        'log_file': 'sd:/ultimate/mii_customizer_log.txt (append)',
        'files_read_once_at_load': ['sd:/ultimate/mii_customizer/presets.txt', 'sd:/ultimate/mii_customizer/loadouts.txt'],
        'files_written': 'the log only. save_loadouts (export mc_save_loadouts) would write loadouts.new and replace loadouts.txt, but nothing in 0.3.0 calls it',
        'target_image': {'title': 'SSBU 13.0.4 main', 'flat_image': 'gamedata/ssbu-13.0.4/main.bin (workspace-relative)',
                         'sha256': 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'},
        'hooks': [{'name': SITE[0], 'offset': f'0x{SITE[1]:x}', 'kind': SITE[5], 'installed_only_if_words_match': True,
                   'expected_words': [f'0x{w:08x}' for w in SITE[2]], 'log_events': SITE[3], 'what': SITE[4]}],
        'hooks_removed_since_0.2.0': ['0x4e53f0 (L6, log-only)'],
        'override': {
            'requests': 'x1 = a field hash of the loaded preset file or one of the two named keys, and x2 == 0',
            'named_keys': {'weight': '0x0607cd5541', 'walk_speed_max': '0x0ee2ec2860'},
            'explicit_ranges_proposal_not_declared_safe': {'weight': [60.0, 140.0], 'walk_speed_max': [0.5, 2.0]},
            'preset_values': 'finite, not range-limited',
            'resolution': 'explicit line for (id, hash) > value of the id\'s preset for the hash > the game\'s value',
            'accepted_kinds': [74],
            'object_guard': '[x0] == base+0x4f89490, parent = [x0+8] != 0, [parent+0x50] == x0',
            'identity': 'as 0.2.0 (skyline_smash 315e4e8, six exported functions + the binding\'s battle_object_id field)',
            'cache': 'none; identity and slot ID are re-read on every request for a known hash',
            'hot_path': f'unknown hash: {n_first} instructions when its home slot in the 256-slot table is empty, {per_slot} more per further examined slot (at most probe_max slots, logged in L0 `fields`; 1 for the ten-field preset file); no call, no stack frame, no write',
        },
        'game_imports': GAME_IMPORTS,
        'exports': sorted(exports),
        'static_reads': {'T': '0x5307760', 'saved_fighter_id_u32': 'T + 0xe58 + p*0x240', 'special_bytes_4 (L4 only)': 'T + 0xa2 + p*0x1c8', 'p': '0..7'},
        'crate': {'cargo_toml_sha256': sha(MOD / 'plugin/Cargo.toml'), 'cargo_lock_sha256': sha(MOD / 'plugin/Cargo.lock'),
                  'lib_rs_sha256': sha(MOD / 'plugin/src/lib.rs'), 'logic_rs_sha256': sha(MOD / 'plugin/src/logic.rs'),
                  'loadout_rs_sha256': sha(MOD / 'plugin/src/loadout.rs'), 'preset_rs_sha256': sha(MOD / 'plugin/src/preset.rs'),
                  'build_script_sha256': sha(MOD / 'build-plugin.sh')},
        'dependencies': {
            'skyline': f'0.6.0 git https://github.com/ultimate-research/skyline-rs rev {SKYLINE_REV}',
            'skyline_smash': f'0.1.0 git https://github.com/ultimate-research/skyline-smash rev {SMASH_REV} (feature weak_l2cvalue)',
            'nnsdk (via skyline_smash)': '0.6.2 git https://github.com/ultimate-research/nnsdk-rs rev ' + git.get('nnsdk', '?'),
            'all_locked': now_lock,
        },
        'toolchain': {'cargo_skyline': '3.5.0', 'compiler': 'rustc 1.95.0-nightly (a423f68a0 2026-02-13), cargo-skyline toolchain', 'target': 'aarch64-skyline-switch'},
        'build_command': 'bash mods/mii_customizer/build-plugin.sh   (= cd plugin && CARGO_TARGET_DIR=../builds/.cache/plugin-target cargo skyline build --release -- --offline)',
        'offline_checks': {'build': 'scratch/2026-10-05_P7-PRESET-ENGINE/check_build.py', 'host_test': 'scratch/2026-10-05_P7-PRESET-ENGINE/run_host_test.sh',
                           'mutation_control': 'scratch/2026-10-05_P7-PRESET-ENGINE/mutation_control.sh',
                           'real_preset_file': 'scratch/2026-10-05_P7-PRESET-ENGINE/check_real_presets.py',
                           'image_facts (unchanged site)': 'scratch/2026-10-04_P4-OVERRIDE-SLICE/step0.py', 'report': 'research/P7-PRESET-ENGINE.md'},
    }
    (PKG / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('wrote', (PKG / 'MANIFEST.json').relative_to(MOD).as_posix())
sys.exit(1 if bad else 0)
