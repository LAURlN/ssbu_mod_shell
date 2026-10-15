"""Prepare/finalize the single-change 0.1.1 cargo cleanup test candidate.

Usage: revision.py prepare|package|check. No shared build/install/framework edit.
Inherits the exact 0.1.0 asset tree; three owned comparison call sites change.
"""
import argparse
import json
import shutil
import os
from pathlib import Path
from audit import ROOT, OUT, sha
from integration import catalog
from package import tree_hash, NRO
from nro_flatten import parse

CACHE=ROOT/'builds/.cache/dk_cargo'
OLD=CACHE/'test-plugin'
PRIVATE=CACHE/'test-plugin-0.1.1'
TARGET=CACHE/'runtime-target-0.1.1'
BASE=ROOT/'builds/pgwr/dk_cargo-0.1.0-test'
PACKAGE=ROOT/'builds/pgwr/dk_cargo-0.1.1-test'
EVIDENCE=ROOT/'evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test'
SITES=['25c748','25dd2c','25dd64']

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def built():return TARGET/'aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro'

def prepare():
    assert not PRIVATE.exists() and not TARGET.exists()
    source=ROOT/'src/pgwr/plugin/src/status/dk_cargo'
    old_asm=(OLD/'src/status/dk_cargo/callbacks.S').read_text()
    expected=old_asm
    for site in SITES:
        anchor=f'pgwr_dkc_common_{site}:\nbl _ZNK3lib8L2CValueeqERKS0_'
        assert expected.count(anchor)==1
        expected=expected.replace(anchor,f'pgwr_dkc_common_{site}:\nbl pgwr_dkc_cleanup_status_eq',1)
    assert (source/'callbacks.S').read_text()==expected,'Unexpected callback changes'
    shutil.copytree(OLD,PRIVATE)
    for name in ['mod.rs','callbacks.S']:shutil.copyfile(source/name,PRIVATE/'src/status/dk_cargo'/name)
    before=catalog(OLD);after=catalog(PRIVATE)
    assert set(before)==set(after)
    assert {p for p in before if before[p]!=after[p]}=={'src/status/dk_cargo/mod.rs','src/status/dk_cargo/callbacks.S'}
    shutil.copytree(CACHE/'runtime-target',TARGET)
    EVIDENCE.mkdir(exist_ok=True)
    save(EVIDENCE/'SOURCE.json',{'tier':'B','task_version':'0.1.1-test','source_files':after,
       'previous_source_files':before,'comparison_sites':SITES,'shared_source_changed':False,
       'test_allocation':'0x400..0x411 unchanged','framework_changed':False,
       'cargo_target':TARGET.relative_to(ROOT).as_posix(),'private_source':PRIVATE.relative_to(ROOT).as_posix(),
       'build_command':'cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline',
       'hypothesis':'Keep capture during native stock c7 -> owned 411 bridge by recognizing semantic aliases only in owned cleanup comparisons.'})
    print('PASS single-change source snapshot and independent task target; old snapshot/artifacts preserved')

def verify():
    report=read(EVIDENCE/'SOURCE.json');assert catalog(PRIVATE)==report['source_files']
    old_asm=(OLD/'src/status/dk_cargo/callbacks.S').read_text();new_asm=(PRIVATE/'src/status/dk_cargo/callbacks.S').read_text()
    expected=old_asm
    for site in SITES:expected=expected.replace(f'pgwr_dkc_common_{site}:\nbl _ZNK3lib8L2CValueeqERKS0_',f'pgwr_dkc_common_{site}:\nbl pgwr_dkc_cleanup_status_eq',1)
    assert new_asm==expected and new_asm.count('bl pgwr_dkc_cleanup_status_eq')==3
    raw=built().read_bytes();imports=[s[0] for s in parse(raw)[0] if s[2]==0]
    assert not any('FighterSpecializer_Donkey' in n or 'donkey_thrown_offset' in n or 'ShoulderedDonkey' in n for n in imports)
    assert sha(raw)!=read(BASE/'MANIFEST.json')['nro_sha256']
    assert b'dk_cargo-0.1.1-test' in raw
    # Pin the pure scalar adapter's compiled branch decisions. All three caller
    # sites retain the native pointer arguments and scalar bool return ABI.
    from audit_pgwr_svc_guard import functions
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
    elf=(built().with_suffix('.so')).read_bytes();funcs=functions(elf)
    address,code=funcs['pgwr_dkc_cleanup_status_eq']
    ins=list(Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(code,address))
    assert ins and any(x.mnemonic=='ret' for x in ins)
    asm=[f'{x.address:#x}: {x.mnemonic} {x.op_str}' for x in ins]
    assert funcs['pgwr_capture_query_memory'][1][:20]==bytes.fromhex('e10f1ff8c10000d4e20741f8410000b9c0035fd6')
    return {'tier':'B','runtime_verified':False,'nro_sha256':sha(raw),'nro_size':len(raw),
        'elf_sha256':sha(elf),'comparison_call_sites':SITES,'adapter_disassembly':asm,
        'asset_changes':0,'status_allocation_changes':0,'framework_changes':False}

def package():
    assert not PACKAGE.exists()
    checks=verify();base=read(BASE/'MANIFEST.json')
    PACKAGE.mkdir();mod=PACKAGE/'ultimate/mods/pyra_gamewatch_reskin'
    shutil.copytree(BASE/'ultimate/mods/pyra_gamewatch_reskin',mod,copy_function=os.link)
    assert catalog(mod)==base['mod_files']
    plugin=PACKAGE/NRO;plugin.parent.mkdir(parents=True)
    shutil.copyfile(built(),plugin)
    shutil.copyfile(BASE/Path(NRO).parent/'libone_slot_eff.nro',plugin.parent/'libone_slot_eff.nro')
    shutil.copyfile(BASE/'integration.patch',PACKAGE/'integration.patch')
    shutil.copyfile(EVIDENCE/'SOURCE.json',PACKAGE/'SOURCE.json')
    shutil.copyfile(CACHE/'BUILD-0.1.1.txt',PACKAGE/'BUILD.txt')
    save(PACKAGE/'CHECKS.json',checks)
    save(PACKAGE/'ASSET_DELTA.json',{'baseline_package':BASE.relative_to(ROOT).as_posix(),
         'baseline_manifest_sha256':sha((BASE/'MANIFEST.json').read_bytes()),'delta':{},
         'mod_files':base['mod_files'],'inherited_asset_delta':(BASE/'ASSET_DELTA.json').relative_to(ROOT).as_posix(),
         'inherited_asset_delta_sha256':sha((BASE/'ASSET_DELTA.json').read_bytes())})
    manifest={**base,'task_version':'0.1.1-test','readiness':'READY_FOR_CONTROLLED_RETEST',
        'installed':False,'runtime_verified':False,'baseline':BASE.relative_to(ROOT).as_posix(),
        'baseline_manifest_sha256':sha((BASE/'MANIFEST.json').read_bytes()),
        'nro_sha256':checks['nro_sha256'],'nro_size':checks['nro_size'],
        'source_snapshot':read(EVIDENCE/'SOURCE.json')['source_files'],
        'cargo_target':TARGET.relative_to(ROOT).as_posix(),'source_tool_pins':{
             p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in [Path(__file__),ROOT/'src/pgwr/tools/dk_cargo/emit_callbacks.py',
                 ROOT/'src/pgwr/plugin/src/status/dk_cargo/mod.rs',ROOT/'src/pgwr/plugin/src/status/dk_cargo/callbacks.S']},
        'payload_files':{p.relative_to(PACKAGE).as_posix():sha(p.read_bytes()) for p in (PACKAGE/'atmosphere').rglob('*') if p.is_file()},
        'controlled_change':'Three owned End/Exit comparison call sites accept queued stock victim carry/thrown semantic aliases, preserving capture until owned Pre routing.'}
    save(PACKAGE/'MANIFEST.json',manifest);check()

def check():
    report=verify();m=read(PACKAGE/'MANIFEST.json');files=catalog(PACKAGE/'ultimate/mods/pyra_gamewatch_reskin')
    assert files==m['mod_files']==read(BASE/'MANIFEST.json')['mod_files']
    assert tree_hash(files)==m['mod_tree_sha256']
    assert sha((PACKAGE/NRO).read_bytes())==report['nro_sha256']==m['nro_sha256']
    for p,h in m['payload_files'].items():assert sha((PACKAGE/p).read_bytes())==h
    print('PASS 0.1.1 controlled retest package; three comparison sites; 0 assets/status IDs/framework changes')
    print('NRO',m['nro_sha256'],m['nro_size']);print('MANIFEST',sha((PACKAGE/'MANIFEST.json').read_bytes()))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','package','check'])
    {'prepare':prepare,'package':package,'check':check}[parser.parse_args().command]()
