"""Make Ghidra C output of a flattened lua2cpp NRO readable.

Usage: python annotate_c.py <flat.bin> <labels.json> <in.c> <out.c>
* `*(int *)(<const table ptr> + 0xNN)` -> `_<LUA_CONST_NAME>` (lua2cpp_common const table)
* `func_0x00102xxx` PLT calls -> demangled import name (needs `c++filt` on PATH; see paths.toml msys2_mingw)
* blank lines removed. Ghidra truncates 40-bit hash40 constants to their low 32 bits: re-add the length byte by hand.
"""
import json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import nro_util as u


def annotate(img, meta, t):
    tbl = set(re.findall(r'(\w+) = (PTR_const_value_table_\w+);', t))
    for var in {a for a, _ in tbl} | {b for _, b in tbl}:
        t = re.sub(r'\*\(\w+ \*\)\(%s \+ (0x[0-9a-f]+|\d+)\)' % re.escape(var),
                   lambda m: '_' + (u.const_name(int(m.group(1), 0)) or m.group(0)), t)
    plt = u.plt_map(img, meta['labels'], meta['text_end'])
    names = sorted(set(plt.values()))
    dem = subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True).stdout.split('\n')
    dm = {n: re.sub(r'\(.*$', '', d) for n, d in zip(names, dem)}
    t = re.sub(r'func_0x00([0-9a-f]{6})', lambda m: dm.get(plt.get(int(m.group(1), 16), ''), m.group(0)), t)
    return re.sub(r'\n\s*\n', '\n', t)


if __name__ == '__main__':
    img = open(sys.argv[1], 'rb').read(); meta = json.load(open(sys.argv[2]))
    open(sys.argv[4], 'w').write(annotate(img, meta, open(sys.argv[3]).read()))
