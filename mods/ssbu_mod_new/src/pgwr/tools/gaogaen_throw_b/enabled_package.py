"""Package/check enabled Gaogaen back throw v0.3.0, without installation.

Reuses the recorded 0.20.20 collective tree and semantic asset merger. Smoke:
python -B src/pgwr/tools/gaogaen_throw_b/enabled_package.py prepare
python -B src/pgwr/tools/gaogaen_throw_b/enabled_package.py check
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parent))
import pipeline as assets

OUT = ROOT / 'builds/pgwr/gaogaen_throw_b-0.3.0'
BASE = ROOT / 'builds/pgwr/0.20.20/ultimate/mods/pyra_gamewatch_reskin'
MOD = OUT / 'ultimate/mods/pyra_gamewatch_reskin'
CACHE = ROOT / 'builds/.cache/gaogaen_throw_b'
NRO_REL = 'atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro'
EFF_REL = str(Path(NRO_REL).with_name('libone_slot_eff.nro')).replace('\\', '/')
BUILT = CACHE / 'runtime-target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro'
STATUS = 0x208

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def catalog(folder):
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
def tree_hash(files):
    return hashlib.sha256(''.join(f'{v}  ./{k}\n' for k,v in sorted(files.items())).encode()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def validate():
    report = json.loads((OUT / 'MANIFEST.json').read_text())
    assert report['tool_sha256'] == sha(Path(__file__))
    assert report['enabled'] and report['status_id'] == STATUS
    current = catalog(MOD)
    assert current == report['mod_files']
    assert tree_hash(current) == report['mod_tree_sha256']
    assert sha(OUT / NRO_REL) == report['nro_sha256'] == sha(BUILT)
    assert sha(OUT / NRO_REL) != sha(ROOT / 'builds/pgwr/0.20.20' / NRO_REL)
    baseline = catalog(BASE)
    assert baseline == report['baseline_files']
    allowed = set(report['asset_delta_paths'])
    changed = {k for k in baseline if k in current and baseline[k] != current[k]}
    added = set(current) - set(baseline)
    assert not (set(baseline) - set(current))
    assert changed | added == allowed
    assert len(changed) == 15 and len(added) == 2
    assert all(current[k] == v for k,v in baseline.items() if k not in allowed)
    for slot in ('c06','c07'):
        relative = f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        before = assets.mlist((BASE / relative).read_bytes())[2]
        after = assets.mlist((MOD / relative).read_bytes())[2]
        assert all(after[k]['raw'] == v['raw'] for k,v in before.items())
        assert after[assets.h40(assets.KIND)]['raw'] == (assets.OUT / 'motion_entry.bin').read_bytes()
        assert sha(MOD / f'fighter/eflame/motion/body/{slot}/{assets.CLIP}') == sha(assets.OUT / 'delta' / f'fighter/eflame/motion/body/{slot}/{assets.CLIP}')
    acmd = (ROOT / 'src/pgwr/plugin/src/acmd/gaogaen_throw_b.rs').read_text()
    for category in ('game','effect','sound','expression'):
        assert f'{category}_acmd("{category}_pgwrgaogaenthrowb"' in acmd
        assert f'{category}_pgwrgaogaenthrowb'.encode() in (OUT / NRO_REL).read_bytes()
    for relative, digest in report['source_snapshot'].items():
        assert sha(CACHE / 'enabled-plugin' / relative) == digest
    for part in ('acmd/mod.rs','status/mod.rs','status/gaogaen_throw_b.rs',
                 'status/gaogaen_throw_b_data.rs','acmd/gaogaen_throw_b.rs'):
        assert sha(ROOT / 'src/pgwr/plugin/src' / part) == sha(CACHE / 'enabled-plugin/src' / part)
    assert 'STATUS_GAOGAEN_THROW_B: i32 = 0x208' in (ROOT / 'src/pgwr/plugin/src/status/mod.rs').read_text()
    allocations = re.findall(r'pub const STATUS_\w+: i32 = (0x[0-9A-Fa-f]+);',
        (ROOT / 'src/pgwr/plugin/src/status/mod.rs').read_text())
    assert len(allocations) == len(set(allocations)), 'shared status allocation collision'
    assert 'option_env!' not in (ROOT / 'src/pgwr/plugin/src/status/gaogaen_throw_b.rs').read_text()
    assert b'REGISTERED status=' in (OUT / NRO_REL).read_bytes()
    assert sha(OUT / EFF_REL) == sha(ROOT / 'builds/pgwr/0.20.20' / EFF_REL) == report['unchanged_effect_plugin_sha256']
    assert report['cargo_target'] == 'gaogaen_throw_b/runtime-target'
    assert len(list((OUT / 'atmosphere').rglob('*.nro'))) == 2
    print('PASS enabled NRO equality/registrations/status allocation; 1990 baseline files preserved except 15 declared changes + 2 owned clips; full tree/source hashes')

def prepare():
    assets.check_pins()
    assert not OUT.exists(), 'Keep recorded packages intact'
    assert BUILT.is_file()
    source = CACHE / 'enabled-plugin'
    assert 'STATUS_GAOGAEN_THROW_B: i32 = 0x208' in (source / 'src/status/mod.rs').read_text()
    shutil.copytree(BASE, MOD)
    baseline = catalog(BASE)
    assets.merge(MOD)
    nro = OUT / NRO_REL
    nro.parent.mkdir(parents=True)
    shutil.copyfile(BUILT, nro)
    shutil.copyfile(ROOT / 'builds/pgwr/0.20.20' / EFF_REL, OUT / EFF_REL)
    shutil.copyfile(CACHE / 'enabled_build.txt', OUT / 'BUILD.txt')
    for name in ('merge_deltas.json','motion_entry.bin'):
        shutil.copyfile(assets.OUT / name, OUT / name)
    files = catalog(MOD)
    asset_manifest = json.loads((assets.OUT / 'MANIFEST.json').read_text())
    commit = subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}',
        'rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    report = {'state':'READY', 'enabled':True, 'installed':False, 'runtime':'unverified',
        'task_version':'0.3.0', 'plugin_version':'0.20.20', 'shared_version_bumped':False,
        'status_id':STATUS, 'status_hex':hex(STATUS), 'next_free_eflame':'0x209',
        'git_commit':commit, 'baseline':'builds/pgwr/0.20.20',
        'baseline_nro_sha256':sha(ROOT / 'builds/pgwr/0.20.20' / NRO_REL),
        'baseline_files':baseline, 'mod_files':files, 'mod_tree_sha256':tree_hash(files),
        'mod_file_count':len(files), 'nro_path':NRO_REL, 'nro_sha256':sha(nro),
        'nro_size':nro.stat().st_size, 'asset_delta_paths':[f['path'] for f in asset_manifest['files']],
        'cargo_target':'gaogaen_throw_b/runtime-target',
        'unchanged_effect_plugin_sha256':sha(OUT / EFF_REL),
        'source_snapshot':catalog(source), 'offline_build':True,
        'features':['snake-neutral-b','hero-side-b'], 'allocation_environment_required':False,
        'sound_merge':'append codec checked preceding samples/tones/labels during merge',
        'framework_plugins_included':False,
        'limitations':['Runtime and console behavior unverified',
            'SIMD Vector3 FFI warning follows the pinned native/binding ABI; runtime validation required'],
        'tool_sha256':sha(Path(__file__)), 'cargo_lock_sha256':sha(source / 'Cargo.lock')}
    write(OUT / 'MANIFEST.json', report)
    validate()
    print('Package',OUT.relative_to(ROOT),'manifest',sha(OUT / 'MANIFEST.json'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare','check'))
    args=parser.parse_args()
    prepare() if args.command == 'prepare' else validate()
