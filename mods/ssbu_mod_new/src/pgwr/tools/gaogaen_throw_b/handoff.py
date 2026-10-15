"""v0.2.0: check collective asset preservation and package the pending owned runtime.

Run from the mod root. Writes only gaogaen_throw_b outputs and private caches.
No status allocation, live registration, installation or game execution.
"""
from pathlib import Path
import difflib
import argparse
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parent))
import pipeline as p

OUT = ROOT / 'builds/pgwr/gaogaen_throw_b-0.2.0'
EVID = ROOT / 'evidence/2026-10-02_pgwr_gaogaen_throw_b'
BASE = ROOT / 'builds/pgwr/0.20.20/ultimate/mods/pyra_gamewatch_reskin'
CACHE = ROOT / 'builds/.cache/gaogaen_throw_b'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n')
def files(root):
    return [{'path': f.relative_to(root).as_posix(), 'sha256': sha(f), 'bytes': f.stat().st_size}
            for f in sorted(root.rglob('*')) if f.is_file()]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    p.check()
    if args.check:
        report = json.loads((OUT / 'PACKAGE.json').read_text())
        assert report['status_id'] is None and not report['compile']['installable']
        for f in report['files']:
            assert sha(OUT / f['path']) == f['sha256'], f['path']
        for f in report['compile']['snapshot']:
            assert sha(CACHE / 'runtime-plugin' / f['path']) == f['sha256'], f['path']
        for f in report['asset_baseline_0_20_20']:
            assert sha(BASE / f['path']) == f['sha256'], f['path']
        print('PASS package hashes, compiled snapshot, current collective baseline and disabled allocation')
        return
    assert not OUT.exists(), 'Do not replace a recorded package'
    target = CACHE / 'merge-current-smoke'
    assert not target.exists(), 'Use a fresh task cache'
    target.mkdir(parents=True)
    old = json.loads((p.OUT / 'MANIFEST.json').read_text())
    baselines = []
    for f in old['files']:
        if f['baseline_sha256'] is not None:
            src = BASE / f['path']
            dst = target / f['path']
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            baselines.append({'path': f['path'], 'sha256': sha(src)})
    original_config = json.loads((target / 'config.json').read_text())
    motions = {}
    for slot in ('c06', 'c07'):
        relative = f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        motions[relative] = p.mlist((target / relative).read_bytes())[2]
    p.merge(target)
    for relative, before in motions.items():
        after = p.mlist((target / relative).read_bytes())[2]
        assert set(after) == set(before) | {p.h40(p.KIND)}
        assert all(after[k]['raw'] == v['raw'] for k, v in before.items())
    config = json.loads((target / 'config.json').read_text())
    for key, value in original_config.items():
        if key != 'new-dir-files': assert config[key] == value
        else:
            for group, names in value.items():
                assert all(n in config[key][group] for n in names)
    # append_tones verifies every preceding audio sample, tone and label itself.
    # Repeating the merge must detect a collision before changing any bytes.
    before_retry = files(target)
    rejected = False
    try: p.merge(target)
    except AssertionError as error:
        assert 'Already merged or collision' in str(error)
        rejected = True
    assert rejected and files(target) == before_retry
    assert all(sha(BASE / f['path']) == f['sha256'] for f in baselines)
    OUT.mkdir(parents=True)
    for name in ('delta',): shutil.copytree(p.OUT / name, OUT / name)
    for name in ('motion_entry.bin', 'merge_deltas.json', 'MANIFEST.json', 'CHECK.json', 'SMOKE.json'):
        shutil.copyfile(p.OUT / name, OUT / ('ASSET_' + name if name.endswith('.json') else name))
    private = CACHE / 'runtime-plugin'
    own = ('acmd/gaogaen_throw_b.rs', 'status/gaogaen_throw_b.rs', 'status/gaogaen_throw_b_data.rs')
    for part in own:
        src = ROOT / 'src/pgwr/plugin/src' / part
        assert sha(src) == sha(private / 'src' / part)
        dst = OUT / 'source' / part
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    patch, registration = [], []
    for part in ('acmd/mod.rs', 'status/mod.rs'):
        src = ROOT / 'src/pgwr/plugin/src' / part
        before = src.read_text()
        assert 'mod gaogaen_throw_b;' not in before
        after = before.replace('pub fn install() {',
            'pub mod gaogaen_throw_b;\n\npub fn install() {\n    gaogaen_throw_b::install();', 1)
        relative = src.relative_to(ROOT).as_posix()
        patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                          fromfile='a/' + relative, tofile='b/' + relative))
        registration.append({'path': relative, 'sha256': sha(src)})
    (OUT / 'integration.patch').write_text(''.join(patch))
    nro = CACHE / 'runtime-target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro'
    (OUT / 'compile-only-disabled').mkdir()
    shutil.copyfile(nro, OUT / 'compile-only-disabled/libpyra_gamewatch_reskin.nro')
    shutil.copyfile(CACHE / 'runtime_compile_errors.txt', OUT / 'BUILD_LOG.txt')
    report = {'state': 'PENDING', 'runtime': 'unverified', 'status_id': None,
        'needed': 'one collectively allocated eflame custom status; enabled rebuild and native capture audit',
        'compile': {'offline': True, 'features': ['snake-neutral-b', 'hero-side-b'],
                    'status_environment': None, 'installable': False, 'snapshot': files(private)},
        'registration_baselines': registration, 'asset_baseline_0_20_20': baselines,
        'preservation': {'motion_entries': True, 'audio_samples_tones_labels': True,
                         'config_existing_values': True, 'collision_preflight_no_mutation': True,
                         'shared_baseline_unchanged': True},
        'limitations': ['No enabled runtime NRO: allocation deliberately unset',
            'CaptureModule concrete engine status assumptions not fully resolved',
            'SIMD exported hook ABI follows pinned bindings/native return but has compiler FFI warning',
            'No non-catch-only collateral box is present in pinned donor script; native collateral equivalence unverified'],
        'files': files(OUT)}
    write(OUT / 'PACKAGE.json', report)
    write(EVID / 'RUNTIME_SOURCE.json', {'state': 'PENDING', 'status_allocation': None,
        'table_rows_checked': 94, 'donor_offset_float_bits': 282,
        'private_snapshot': private.relative_to(ROOT).as_posix(), 'snapshot_files': files(private)})
    print('PASS current collective preservation and collision preflight; pending package',
          OUT.relative_to(ROOT).as_posix(), sha(OUT / 'PACKAGE.json'))

if __name__ == '__main__': main()
