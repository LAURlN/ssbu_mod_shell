"""Dump Hero's `param_special_s` out of the pinned 13.0.4 `fighter/brave/param/vl.prc`.

Tier B: a measurement of bytes already in `dumps/`, with a smoke test, not a claim
about behaviour. The charge thresholds this move needs live in this table.

Usage:
    python dump_param_special_s.py            # write refs/brave_special_s/param_special_s.json
    python dump_param_special_s.py --check    # re-derive and compare, write nothing

The same decoder the neutral-B port used (`src/pgwr/tools/prc.py`, by
`gen_hero_fireball_initializer.py`), so `param_special_n` read here means what it
means there.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import prc  # noqa: E402

VL = ROOT / 'dumps/arc/fighter/brave/param/vl.prc'
LABELS = ROOT / 'dumps/scripts/ParamLabels.csv'
OUT = ROOT / 'refs/brave_special_s/param_special_s.json'
VERSION = '1.0.0'


def labels():
    """hash40 -> name, so the dump is readable instead of a wall of decimals."""
    out = {}
    for line in LABELS.read_text(encoding='utf-8').splitlines():
        h, _, name = line.partition(',')
        try:
            out[int(h, 16)] = name
        except ValueError:
            pass
    return out


def as_dict(node, names):
    """prc nodes are (type, value) tuples keyed by hash40 ints; name them."""
    kind, value = node[0], node[1]
    if kind == 'struct':
        return {names.get(k, f'0x{k:x}'): as_dict(v, names) for k, v in value}
    if kind in ('list', 'listf'):
        return [as_dict(v, names) for v in value]
    if kind == 'hash':
        return {'__hash__': f'0x{value:x}'}
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    names = labels()
    key = prc.hash40('param_special_s')
    table = prc.read(VL)[1]
    pairs = table.items() if hasattr(table, 'items') else table
    hit = [v for k, v in pairs if k == key]
    assert hit, 'param_special_s not present in the pinned vl.prc'
    value = as_dict(hit[0], names)

    doc = {
        'tool': f'tools/dump_param_special_s.py v{VERSION}',
        'tier': 'B',
        'source': 'dumps/arc/fighter/brave/param/vl.prc (13.0.4, region 2 dump)',
        'param': 'param_special_s',
        'hash40': f'0x{key:x}',
        'entries': value,
        'not_established': (
            'Values only. Which entry is read at which charge level, and whether the '
            'Special-Move gauge is consulted at all, are not established here.'),
    }
    text = json.dumps(doc, indent=2) + '\n'

    if args.check:
        assert OUT.is_file(), f'{OUT} missing'
        prior = json.loads(OUT.read_text())
        assert prior == doc, 're-derived param_special_s differs from the pinned copy'
        print(f'OK {OUT.name} matches ({len(value)} entries)')
        return

    OUT.write_text(text, encoding='utf-8')
    print(f'wrote {OUT.relative_to(ROOT)}: {len(value)} entries, hash40 0x{key:x}')


if __name__ == '__main__':
    main()
