"""Create a private cargo build snapshot and narrow UNAPPLIED shared patch.

Usage: python -B src/pgwr/tools/dk_cargo/integration.py prepare
No shared registration changes, release bumps, builds, installation or framework
edits. Only task-owned runtime files are copied into an isolated compile tree.
"""
import argparse
import difflib
import json
import shutil
from audit import ROOT, OUT, sha, write

CACHE=ROOT/'builds/.cache/dk_cargo'
PRIVATE=CACHE/'test-plugin'
SOURCE=ROOT/'src/pgwr/plugin'
PATCH=ROOT/'src/pgwr/tools/dk_cargo/integration.patch'

def catalog(folder):return {p.relative_to(folder).as_posix():sha(p.read_bytes()) for p in sorted(folder.rglob('*')) if p.is_file()}
def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)

def edits():
    changes={}
    p='src/status/mod.rs';before=(SOURCE/p).read_text()
    after=replace(before,'pub mod gaogaen_throw_b;','pub mod gaogaen_throw_b;\npub mod dk_cargo;')
    after=replace(after,'    gaogaen_throw_b::install();','    gaogaen_throw_b::install();\n    dk_cargo::install();')
    changes[p]=(before,after)
    p='src/status/monkey_flip_capture.rs';before=(SOURCE/p).read_text()
    after=replace(before,'unsafe fn mapped(address: usize, size: usize, writable: bool)',
                  'pub(super) unsafe fn mapped(address: usize, size: usize, writable: bool)')
    # Keep unrelated non-capture events on the old fast-forward path. Only the
    # two authorized cargo event types enter the existing accessor range guard.
    after=replace(after,'    if kind != CAPTURE { return original(this, fighter, event); }',
        '    if kind != CAPTURE && kind != 0x21ba53a92c && kind != 0xb319a8b44 { return original(this, fighter, event); }')
    anchor='    if !crate::params::is_target_fighter(boma)\n        || StatusModule::status_kind(boma) != STATUS_MONKEY_FLIP_JUMP {'
    after=replace(after,anchor,'    if super::dk_cargo::on_event(boma, kind) { return 1; }\n'
        '    if kind != CAPTURE { return original(this, fighter, event); }\n'+anchor)
    changes[p]=(before,after)
    p='src/status/special_hi.rs';before=(SOURCE/p).read_text()
    anchor='        super::monkey_flip::refresh_locks(boma, "class event +0x210");'
    after=replace(before,anchor,anchor+'\n        super::dk_cargo::on_reset(boma);')
    changes[p]=(before,after)
    p='src/status/gaogaen_throw_b.rs';before=(SOURCE/p).read_text()
    anchor='unsafe extern "C" fn is_not_throw(fighter: &mut L2CFighterCommon, kind: L2CValue) -> L2CValue {'
    after=replace(before,anchor,anchor+'\n    if super::dk_cargo::owns_throw_kind(fighter, kind.get_i32()) { return false.into(); }')
    changes[p]=(before,after)
    return changes

def prepare():
    assert not PRIVATE.exists(),'Keep compile snapshots immutable; revise the task snapshot name for another candidate.'
    changes=edits()
    PRIVATE.mkdir(parents=True)
    for n in ['Cargo.toml','Cargo.lock']:shutil.copyfile(SOURCE/n,PRIVATE/n)
    shutil.copytree(SOURCE/'src',PRIVATE/'src')
    patches=[]
    for p,(before,after) in changes.items():
        (PRIVATE/p).write_text(after,encoding='utf-8')
        patches.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),
                       fromfile='a/src/pgwr/plugin/'+p,tofile='b/src/pgwr/plugin/'+p))
    PATCH.write_text(''.join(patches),encoding='utf-8')
    home=CACHE/'cargo-home'
    if not home.exists():
        shutil.copytree(ROOT/'builds/.cache/gaogaen_throw_b/cargo-home',home)
    report={'tier':'B','shared_edits_applied':False,'patch':PATCH.relative_to(ROOT).as_posix(),
      'patch_sha256':sha(PATCH.read_bytes()),'baseline':{p:sha((SOURCE/p).read_bytes()) for p in changes},
      'snapshot':PRIVATE.relative_to(ROOT).as_posix(),'source_files':catalog(PRIVATE),
      'production_ids':None,'private_test_allocation':'refs/donkey_cargo/test_allocation.json',
      'shared_version':'0.20.20','task_version':'0.1.0-test','framework_modified':False,
      'build_command':'cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline',
      'cargo_home':'builds/.cache/dk_cargo/cargo-home','cargo_target':'builds/.cache/dk_cargo/runtime-target'}
    write('integration_snapshot.json',report)
    print('PASS private source snapshot, isolated dependency cache and four-file UNAPPLIED integration patch')

def refresh_owned():
    # Before final packaging only. Preserve the fixed shared snapshot and copy
    # repaired task-owned source. Do not run while Cargo compiles this tree.
    destination=PRIVATE/'src/status/dk_cargo'
    for p in (SOURCE/'src/status/dk_cargo').rglob('*'):
        if p.is_file():shutil.copyfile(p,destination/p.relative_to(SOURCE/'src/status/dk_cargo'))
    report=json.loads((OUT/'integration_snapshot.json').read_text())
    report['source_files']=catalog(PRIVATE)
    write('integration_snapshot.json',report)
    print('PASS repaired task-owned source refreshed in pre-package snapshot')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','refresh-owned'])
    prepare() if parser.parse_args().command=='prepare' else refresh_owned()
