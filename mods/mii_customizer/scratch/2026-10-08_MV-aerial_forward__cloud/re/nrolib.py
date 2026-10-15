"""Annotated disassembly of lua2cpp_<fighter>.nro functions (MV-aerial_forward__cloud / MV-special_up__cloud).

Run from the workspace root. Reads only; prints text.

    python -I mods/mii_customizer/scratch/2026-10-08_MV-aerial_forward__cloud/re/nrolib.py <nro> list [filter]
    python -I mods/mii_customizer/scratch/2026-10-08_MV-aerial_forward__cloud/re/nrolib.py <nro> dis <addr> [max_ins]
    python -I mods/mii_customizer/scratch/2026-10-08_MV-aerial_forward__cloud/re/nrolib.py <nro> status   (sv_set_status_func sites)

Annotations: bl targets -> import / export names, movz/movk constants -> hash40 label or float,
const_value_table loads -> lua const name and value, adrp+ldr literal floats.
"""
from __future__ import annotations

import re
import struct
import sys
import zlib
from pathlib import Path

WS = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/builds/.cache/dk_cargo/python'))
sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/tools/nro_decomp'))
import capstone  # noqa: E402
import nro_flatten as nf  # noqa: E402

COMMON = WS / 'gamedata/mii_customizer/moves/aerial_forward__cloud/donor/prebuilt;/nro/release/lua2cpp_common.nro'
LABELS_CSV = WS / 'mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv'

M = (1 << 64) - 1
P1 = 0x9E3779B185EBCA87; P2 = 0xC2B2AE3D27D4EB4F; P3 = 0x165667B19E3779F9
P4 = 0x85EBCA77C2B2AE63; P5 = 0x27D4EB2F165667C5
rotl = lambda x, r: ((x << r) | (x >> (64 - r))) & M


def rnd(acc, inp):
    acc = (acc + inp * P2) & M
    return (rotl(acc, 31) * P1) & M


def xxh64(b, seed=M):
    n = len(b); i = 0
    if n >= 32:
        v = [(seed + P1 + P2) & M, (seed + P2) & M, seed & M, (seed - P1) & M]
        while i + 32 <= n:
            for j in range(4):
                v[j] = rnd(v[j], struct.unpack_from('<Q', b, i + 8 * j)[0])
            i += 32
        h = (rotl(v[0], 1) + rotl(v[1], 7) + rotl(v[2], 12) + rotl(v[3], 18)) & M
        for x in v:
            h ^= rnd(0, x); h = (h * P1 + P4) & M
    else:
        h = (seed + P5) & M
    h = (h + n) & M
    while i + 8 <= n:
        h ^= rnd(0, struct.unpack_from('<Q', b, i)[0]); h = (rotl(h, 27) * P1 + P4) & M; i += 8
    if i + 4 <= n:
        h ^= (struct.unpack_from('<I', b, i)[0] * P1) & M; h = (rotl(h, 23) * P2 + P3) & M; i += 4
    while i < n:
        h ^= (b[i] * P5) & M; h = (rotl(h, 11) * P1) & M; i += 1
    h ^= h >> 33; h = (h * P2) & M; h ^= h >> 29; h = (h * P3) & M; h ^= h >> 32
    return h


def lua_const():
    cands = list((Path.home() / '.cargo/git/checkouts').glob('skyline-smash-*/**/src/lua_const.rs'))
    p = max(cands, key=lambda x: x.stat().st_mtime)
    out = {}
    for m in re.finditer(r'^\s+([A-Za-z_0-9]+):\s*(-?0x[0-9a-fA-F]+|-?\d+),', p.read_text(encoding='utf-8', errors='replace'), re.M):
        out[m.group(1)] = int(m.group(2), 0)
    return out


LUA_CONST = lua_const()
_REV = {xxh64(n.encode()): n for n in LUA_CONST}
_COMMON = COMMON.read_bytes()


def const_name(off):
    try:
        return _REV.get(struct.unpack_from('<Q', _COMMON, 0x6a5b70 + off // 4 * 8)[0])
    except struct.error:
        return None


def hash40(s):
    b = s.encode()
    return (len(b) << 32) | zlib.crc32(b)


LABELS = {}
with open(LABELS_CSV, encoding='utf-8') as f:
    for line in f:
        p = line.strip().split(',')
        if len(p) >= 2:
            try:
                LABELS[int(p[0], 16)] = p[1]
            except ValueError:
                pass
EXTRA = ['special_hi', 'special_air_hi', 'special_hi2', 'special_hi2_fall', 'special_hi2_end', 'special_hi2_landing',
         'special_hi_lb', 'special_air_hi_lb', 'landing_air_f', 'attack_air_f', 'have', 'haver', 'havel', 'top',
         'param_special_hi', 'invalid', 'rot', 'trans', 'hip']
for e in EXTRA:
    LABELS.setdefault(hash40(e), e)


def demangle(n):
    m = re.match(r'_ZN3app8lua_bind\d+(\w+?)__(\w+?)_implE', n)
    if m:
        return f'{m.group(1)}::{m.group(2)}'
    m = re.match(r'_ZN7lua2cpp(\d+)', n)
    if m:
        # nested name: classlen class funclen func
        rest = n[len('_ZN7lua2cpp'):]
        parts = []
        while rest and rest[0].isdigit():
            k = re.match(r'\d+', rest).group(0)
            parts.append(rest[len(k):len(k) + int(k)])
            rest = rest[len(k) + int(k):]
        return '::'.join(parts)
    m = re.match(r'_ZN3lib8L2CValue(\w+)', n)
    if m:
        return 'L2CValue::' + m.group(1)
    m = re.match(r'_ZN3app(\d+)', n)
    if m:
        rest = n[len('_ZN3app'):]
        parts = []
        while rest and rest[0].isdigit():
            k = re.match(r'\d+', rest).group(0)
            parts.append(rest[len(k):len(k) + int(k)])
            rest = rest[len(k) + int(k):]
        return 'app::' + '::'.join(parts)
    return n


class Nro:
    def __init__(self, path):
        self.raw = Path(path).read_bytes()
        self.img, meta = nf.flatten(self.raw)
        self.labels = {int(k, 16): v for k, v in meta['labels'].items()}
        self.text_end = meta['text_end']
        self.md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        self.md.detail = False
        self.plt = {}
        for a in range(0, self.text_end, 16):
            w0 = struct.unpack_from('<I', self.img, a)[0]
            if (w0 & 0x9f00001f) != 0x90000010:
                continue
            ins = list(self.md.disasm(self.img[a:a + 16], a))
            if len(ins) == 4 and ins[1].mnemonic == 'ldr' and ins[3].mnemonic == 'br':
                page = int(ins[0].op_str.split('#')[1], 0)
                m = re.search(r'#(0x[0-9a-f]+|\d+)\]', ins[1].op_str)
                off = int(m.group(1), 0) if m else 0
                tgt = struct.unpack_from('<Q', self.img, page + off)[0]
                if tgt in self.labels:
                    self.plt[a] = self.labels[tgt]
        # const_value_table GOT slot: imported symbol
        self.const_tbl = [a for a, n in self.labels.items() if 'const_value_table' in n]

    def name_at(self, a):
        if a in self.plt:
            return demangle(self.plt[a])
        if a in self.labels:
            return demangle(self.labels[a])
        return None

    def dis(self, addr, max_ins=4000, stop_at_ret=True):
        out = []
        regs = {}
        n = 0
        far = 0
        for ins in self.md.disasm(self.img[addr:addr + max_ins * 4], addr):
            n += 1
            note = ''
            mn, ops = ins.mnemonic, ins.op_str
            parts = [p.strip() for p in ops.split(',')]
            if mn in ('mov', 'movz') and len(parts) >= 2 and parts[1].startswith('#'):
                v = int(parts[1][1:], 0)
                if len(parts) == 3 and 'lsl' in parts[2]:
                    v <<= int(parts[2].split('#')[1], 0)
                regs[parts[0].replace('w', 'x', 1)] = v & M
                note = self.const_note(v & M, parts[0])
            elif mn == 'movk':
                r = parts[0].replace('w', 'x', 1)
                sh = int(parts[2].split('#')[1], 0) if len(parts) == 3 else 0
                v = int(parts[1][1:], 0)
                cur = regs.get(r, 0)
                cur = (cur & ~(0xffff << sh)) | (v << sh)
                regs[r] = cur & M
                note = self.const_note(cur & M, parts[0])
            elif mn == 'adrp':
                regs[parts[0]] = int(parts[1][1:], 0)
            elif mn == 'ldr' and '[' in ops:
                m = re.match(r'(\w+), \[(\w+)(?:, #(-?0x[0-9a-f]+|-?\d+))?\]', ops)
                if m:
                    dst, base, off = m.group(1), m.group(2), int(m.group(3) or '0', 0)
                    if base in regs and isinstance(regs[base], int) and base not in ('sp', 'x29'):
                        a = regs[base] + off
                        if 0 <= a < len(self.img) - 8:
                            val = struct.unpack_from('<Q', self.img, a)[0]
                            nm = self.labels.get(val)
                            if nm and 'const_value_table' in nm:
                                regs[dst] = ('ctab',)
                                note = 'const_value_table'
                            elif dst[0] in 'sd':
                                if dst[0] == 's':
                                    note = f'f32 {struct.unpack_from("<f", self.img, a)[0]!r}'
                                else:
                                    note = f'f64 {struct.unpack_from("<d", self.img, a)[0]!r}'
                            else:
                                regs[dst.replace('w', 'x', 1)] = val
                                nm2 = self.name_at(val)
                                note = f'-> {nm2 or hex(val)}'
                    elif regs.get(base) == ('ctab',):
                        nm = const_name(off)
                        note = f'CONST {nm} = {LUA_CONST.get(nm)!r}' if nm else f'CONST? off {off:#x}'
                    regs.pop(dst.replace('w', 'x', 1), None) if not note else None
                else:
                    m2 = re.match(r'(\w+), \[(\w+), (x\d+)\]', ops)
                    if m2 and regs.get(m2.group(2)) == ('ctab',) and isinstance(regs.get(m2.group(3)), int):
                        off = regs[m2.group(3)]
                        nm = const_name(off)
                        note = f'CONST {nm} = {LUA_CONST.get(nm)!r}' if nm else f'CONST? off {off:#x}'
            elif mn == 'add' and len(parts) == 3 and parts[2].startswith('#') and parts[1] in regs and isinstance(regs[parts[1]], int):
                regs[parts[0]] = regs[parts[1]] + int(parts[2][1:], 0)
                nm = self.name_at(regs[parts[0]])
                if nm:
                    note = f'&{nm}'
            elif mn == 'fmov' and len(parts) == 2 and parts[1].startswith('#'):
                note = f'f {parts[1][1:]}'
            elif mn == 'fmov' and len(parts) == 2 and parts[1].replace('w', 'x', 1) in regs and isinstance(regs[parts[1].replace('w', 'x', 1)], int):
                v = regs[parts[1].replace('w', 'x', 1)]
                if parts[1].startswith('w'):
                    note = f'f32 {struct.unpack("<f", struct.pack("<I", v & 0xffffffff))[0]!r}'
            if mn in ('bl', 'b') and ops.startswith('#'):
                t = int(ops[1:], 0)
                nm = self.name_at(t)
                if nm:
                    note = nm
                elif mn == 'bl':
                    note = f'sub_{t:x}'
            out.append((ins.address, mn, ops, note))
            if mn.startswith('b.') or mn in ('cbz', 'cbnz', 'tbz', 'tbnz') or (mn == 'b' and not note):
                try:
                    far = max(far, int(ops.split('#')[-1], 0))
                except ValueError:
                    pass
            if stop_at_ret and mn == 'ret' and ins.address >= far:
                break
        return out

    def const_note(self, v, reg):
        if v in LABELS and v > 0xffffffff:
            return f'hash40 "{LABELS[v]}"'
        if v > 0xffffffff and (v >> 40) == 0 and 0 < (v >> 32) < 64:
            return f'hash40? {v:#x}'
        if reg.startswith('w') and v > 0xffff:
            f = struct.unpack('<f', struct.pack('<I', v & 0xffffffff))[0]
            if 1e-4 < abs(f) < 1e6:
                return f'f32 {f!r}'
        return ''

    def show(self, addr, max_ins=4000):
        for a, mn, ops, note in self.dis(addr, max_ins):
            print(f'{a:08x}  {mn:7s} {ops:40s} {"; " + note if note else ""}')

    def bl_callers(self, target):
        out = []
        for a in range(0, self.text_end, 4):
            w = struct.unpack_from('<I', self.img, a)[0]
            if (w & 0xfc000000) == 0x94000000:
                off = (w & 0x3ffffff) << 2
                if off & (1 << 27):
                    off -= 1 << 28
                if a + off == target:
                    out.append(a)
        return out

    def stub(self, substr):
        return [a for a, n in self.plt.items() if substr in n]


if __name__ == '__main__':
    nro = Nro(sys.argv[1])
    cmd = sys.argv[2]
    if cmd == 'list':
        flt = sys.argv[3] if len(sys.argv) > 3 else ''
        for a, n in sorted(nro.labels.items()):
            if flt in n:
                print(f'{a:08x} {demangle(n)}   {n}')
    elif cmd == 'dis':
        nro.show(int(sys.argv[3], 0), int(sys.argv[4]) if len(sys.argv) > 4 else 4000)
    elif cmd == 'brief':
        skip = re.compile(r'D1Ev|as_integer|as_hash|C1Ei$|as_bool|C1Eb$|C1Ef$|as_number|C1EN3phx|C1ERKS0_|aSERKS0_|'
                          r'clear_lua_stack|L2CValue::C1Ej|L2CValue::C1Em|as_pointer|C1EPv|const_value_table$|push_lua_stack|pop_lua_stack')
        for a, mn, ops, note in nro.dis(int(sys.argv[3], 0), int(sys.argv[4]) if len(sys.argv) > 4 else 4000):
            br = mn.startswith('b.') or mn in ('cbz', 'cbnz', 'tbz', 'tbnz', 'b')
            if (note and not skip.search(note)) or (br and not note):
                print(f'{a:08x}  {mn:7s} {ops:34s} {"; " + note if note else ""}')
    elif cmd == 'callers':
        for st in nro.stub(sys.argv[3]):
            print(hex(st), nro.plt[st], [hex(x) for x in nro.bl_callers(st)])


def status_table(nro):
    """[(status const, cond const, fn addr, site)] for every sv_set_status_func call with static arguments."""
    out = []
    for st in nro.stub('sv_set_status_func'):
        for site in nro.bl_callers(st):
            consts, fn, page = [], None, None
            for a, mn, ops, note in nro.dis(site - 0x50, 21, stop_at_ret=False):
                if note.startswith('CONST'):
                    consts.append(note.split()[1])
                if mn == 'adrp' and ops.startswith('x3,'):
                    page = int(ops.split('#')[1], 16)
                if mn == "add" and ops.startswith("x3, x3") and page is not None:
                    fn = page + int(ops.split('#')[1], 16)
            out.append((consts, fn, site))
    return out
