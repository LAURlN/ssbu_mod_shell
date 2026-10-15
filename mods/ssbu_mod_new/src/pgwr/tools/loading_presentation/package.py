"""Loading presentation 0.1.0: reproducible semantic union, never install.

Smoke test: python -B src/pgwr/tools/loading_presentation/package.py prepare
Integration: ... apply --candidate builds/<installer>/ultimate/mods/pyra_gamewatch_reskin
Only writes under builds; existing complete packages and installed baseline are immutable.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[4]
WORKSPACE = ROOT.parents[1]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import prc

VERSION = '0.1.0'
BASE = ROOT / 'builds/pgwr/dk_cargo-0.1.1-test/ultimate/mods/pyra_gamewatch_reskin'
GAME = WORKSPACE / 'gamedata/ssbu-13.0.4/loading-presentation'
OUT = ROOT / 'builds/pgwr/loading-presentation-0.1.0'
DB = 'ui/param/database/ui_chara_db.prc'
LAYOUT = 'ui/param/database/ui_layout_db.prc'
IDS = {'eflame_first': 'ui_chara_flame_first', 'eflame_only': 'ui_chara_flame_only'}
TARGETS = [f'ui/replace_patch/chara/chara_3/chara_3_eflame_first_{slot:02d}.bntx' for slot in (6, 7)]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rows(tree):
    return dict(tree[1])[prc.hash40('db_root')][1]

def row(tree, key, value):
    found = [r for r in rows(tree) if dict(r[1]).get(prc.hash40(key)) == value]
    assert len(found) == 1, (key, value, len(found))
    return found[0]

def loading_keys():
    labels = (ROOT / 'dumps/scripts/ParamLabels.csv').read_text().splitlines()
    return {int(h, 16): s for line in labels if ',' in line for h, s in [line.split(',', 1)]
            if s.startswith(('chara_3_', 'eye_0_', 'eye_1_', 'eye_2_'))}

def union(chara, layout):
    """Preserve current unrelated fields and append only four owned layout rows."""
    before = copy.deepcopy(chara), copy.deepcopy(layout)
    donor = dict(row(layout, 'ui_chara_id', ('hash', prc.hash40('ui_chara_gamewatch')))[1])
    keys = loading_keys()
    assert len(keys) == 57, len(keys)
    changes = []
    for name, ident in IDS.items():
        target = row(chara, 'name_id', ('str', name))
        base_rows = [r for r in rows(layout) if dict(r[1]).get(prc.hash40('ui_chara_id')) == ('hash', prc.hash40(ident))
                     and dict(r[1]).get(prc.hash40('chara_color')) == ('u8', 0)]
        assert len(base_rows) == 1
        base = dict(base_rows[0][1])
        assert base[prc.hash40('ui_layout_id')] == ('hash', prc.hash40(ident + '_00'))
        for slot in (6, 7):
            index = prc.hash40(f'c{slot:02d}_index')
            assert dict(target[1])[index] in [('u8', 0), ('u8', slot)], 'owned route conflict'
            target[1][:] = [(k, ('u8', slot) if k == index else v) for k, v in target[1]]
            expected = copy.deepcopy(base)
            expected[prc.hash40('chara_color')] = ('u8', slot)
            expected[prc.hash40('ui_layout_id')] = ('hash', prc.hash40(f'{ident}_{slot:02d}'))
            for k in keys:
                assert k in base and k in donor
                expected[k] = donor[k]
            matches = [r for r in rows(layout) if dict(r[1]).get(prc.hash40('ui_chara_id')) == ('hash', prc.hash40(ident))
                       and dict(r[1]).get(prc.hash40('chara_color')) == ('u8', slot)]
            assert len(matches) <= 1
            if matches:
                assert dict(matches[0][1]) == expected, 'owned layout conflict'
            else:
                rows(layout).append(('struct', list(expected.items())))
            changes.append(f'{name}/c{slot:02d}')
    # Verify all original rows and fields, except exactly four route values.
    for old, new in zip(rows(before[0]), rows(chara)):
        allowed = {prc.hash40('c06_index'), prc.hash40('c07_index')} if dict(old[1]).get(prc.hash40('name_id')) in [('str', n) for n in IDS] else set()
        assert [(k,v) for k,v in old[1] if k not in allowed] == [(k,v) for k,v in new[1] if k not in allowed]
    assert rows(layout)[:len(rows(before[1]))] == rows(before[1])
    return changes, keys

def inspect_bntx(p):
    d = p.read_bytes()
    assert d[:4] == b'BNTX'
    count = struct.unpack_from('<I', d, 0x24)[0]
    assert count == 1
    table = struct.unpack_from('<Q', d, 0x28)[0]
    brti = struct.unpack_from('<Q', d, table)[0]
    assert d[brti:brti+4] == b'BRTI'
    w,h = struct.unpack_from('<II', d, brti+0x24)
    assert w > 0 and h > 0
    return {'width': w, 'height': h, 'sha256': sha(p)}

def apply(candidate):
    candidate = candidate.resolve()
    assert candidate.is_relative_to((ROOT / 'builds').resolve())
    assert candidate != BASE.resolve() and not candidate.is_relative_to(OUT.resolve())
    assert candidate.is_dir()
    initial = {p.relative_to(candidate).as_posix(): sha(p) for p in candidate.rglob('*') if p.is_file()}
    chara = prc.read(candidate / DB)
    source_layout = candidate / LAYOUT if (candidate / LAYOUT).exists() else GAME / LAYOUT
    layout = prc.read(source_layout)
    changes, keys = union(chara, layout)
    payloads = {DB: prc.write(chara), LAYOUT: prc.write(layout)}
    for slot, rel in zip((6,7), TARGETS):
        source = BASE / rel.replace('_first_', '_only_')
        inspect_bntx(source)
        # Refuse concurrent edits to owned portraits; accept our idempotent result.
        assert sha(candidate / rel) in [sha(BASE / rel), sha(source)], 'portrait conflict'
        payloads[rel] = source.read_bytes()
    index = set((ROOT / 'dumps/decoded/arc_files.tsv').read_text().splitlines())
    assert all(rel in index for rel in payloads), 'no config/new-files guess permitted'
    for rel,data in payloads.items():
        p = candidate / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    assert prc.read(candidate / DB) == chara and prc.read(candidate / LAYOUT) == layout
    final = {p.relative_to(candidate).as_posix(): sha(p) for p in candidate.rglob('*') if p.is_file()}
    assert all(final.get(p) == h for p,h in initial.items() if p not in payloads)
    assert set(final) - set(initial) <= {LAYOUT}
    return {'routes': changes, 'loading_fields_per_row': len(keys), 'files': {p: final[p] for p in payloads},
            'preserved_files': len(initial)-len(set(initial)&set(payloads)), 'added_files': sorted(set(final)-set(initial))}

def prepare():
    assert not OUT.exists(), 'complete package is immutable; choose a new task version for revisions'
    candidate = ROOT / 'builds/.cache/loading-presentation' / OUT.name / 'candidate'
    assert not (candidate / 'CHECKS.json').exists()
    # Only copy UI inputs; gameplay/NRO are inherited, never replaced by this task.
    import shutil
    for rel in [DB, LAYOUT] + TARGETS:
        if (BASE / rel).exists():
            dst = candidate / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(BASE / rel, dst)
    report = apply(candidate)
    delta = OUT / 'delta'
    for rel in report['files']:
        dst = delta / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate / rel, dst)
    # Positive idempotency + negative collision controls.
    assert apply(candidate)['files'] == report['files']
    c,l = prc.read(candidate / DB),prc.read(candidate / LAYOUT)
    target = row(c,'name_id',('str','eflame_first'))
    target[1][:] = [(k,('u8',5) if k==prc.hash40('c06_index') else v) for k,v in target[1]]
    try:
        union(c,l)
    except AssertionError:
        report['negative_route_control'] = 'PASS'
    else:
        raise AssertionError('negative route control missed')
    report['idempotency'] = 'PASS'
    report['bntx'] = {rel: inspect_bntx(delta / rel) for rel in TARGETS}
    report['tier'] = 'B verified offline; runtime unverified'
    report['baseline'] = BASE.relative_to(ROOT).as_posix()
    report['loading_keys'] = sorted(loading_keys().values())
    (OUT / 'CHECKS.json').write_text(json.dumps(report,indent=2)+'\n')
    import subprocess
    commit = subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    manifest = {'task_version': VERSION, 'collective_version': 'installer owned', 'git_commit': commit,
                'toolchain': {'python': sys.version, 'prc': sha(ROOT / 'src/pgwr/tools/prc.py')},
                'file_count': 4, 'mod_files': report['files'], 'baseline': report['baseline'],
                'nro': 'unchanged: inherit collective package including Incineroar and DK cargo',
                'baseline_manifest_sha256': sha(BASE.parents[2] / 'MANIFEST.json')}
    (OUT / 'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','apply'])
    parser.add_argument('--candidate',type=Path)
    parser.add_argument('--output',type=Path,help='Fresh task package under builds/pgwr for reproduction')
    args=parser.parse_args()
    if args.output:
        OUT=args.output.resolve()
        assert OUT.is_relative_to((ROOT/'builds/pgwr').resolve()) and OUT != BASE.parents[2].resolve()
    if args.action=='prepare': prepare()
    else:
        assert args.candidate
        print(json.dumps(apply(args.candidate),indent=2))
