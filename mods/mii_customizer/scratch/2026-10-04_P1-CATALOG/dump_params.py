"""P1-CATALOG scratch: decode a `.prc` param tree and label its Hash40 keys.

Reads with the mod repo's typed reader
(mods/ssbu_mod_new/src/pgwr/tools/prc.py, read-only import) and joins every
struct key and `hash` value against ParamLabels.csv by hash40. Unlabelled keys
are printed with their raw hash so nothing is invented.

Usage (workspace root):
  python mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/dump_params.py \
      gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/param/vl.prc
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
PRC = os.path.join(ROOT, 'mods', 'ssbu_mod_new', 'src', 'pgwr', 'tools', 'prc.py')
LABELS = os.path.join(ROOT, 'mods', 'ssbu_mod_new', 'dumps', 'scripts', 'ParamLabels.csv')


def load_prc():
    spec = importlib.util.spec_from_file_location('pgwr_prc', PRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_labels():
    lab = {}
    with open(LABELS, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            h, _, n = line.partition(',')
            try:
                lab[int(h, 16)] = n
            except ValueError:
                pass
    return lab


def label(h, lab):
    return f'{lab.get(h, "")}#{h:#012x}'


def walk(node, lab, path='', out=None, depth=0):
    if out is None:
        out = []
    tag = node[0]
    if tag == 'struct':
        for key, child in node[1]:
            name = label(key, lab)
            walk(child, lab, f'{path}/{name}', out, depth + 1)
    elif tag == 'list':
        for i, child in enumerate(node[1]):
            walk(child, lab, f'{path}[{i}]', out, depth + 1)
    else:
        value = node[1]
        if tag == 'hash':
            value = label(value, lab)
        out.append((path, tag, value))
    return out


def main():
    prc = load_prc()
    lab = load_labels()
    path = sys.argv[1]
    tree = prc.read(path)
    rows = walk(tree, lab)
    scalar = [r for r in rows if r[1] != 'struct']
    print(f'{path}: {len(scalar)} scalar values, '
          f'{sum(1 for r in scalar if not r[0].split("/")[-1].split("#")[0])} unlabelled keys')
    for p, tag, value in scalar:
        print(f'{p}\t{tag}\t{value}')


if __name__ == '__main__':
    main()