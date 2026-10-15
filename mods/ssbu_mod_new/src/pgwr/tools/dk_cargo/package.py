"""Finalize/check the isolated cargo test package. Smoke: package.py --check.

No installation, shared builds, framework edits or production ID allocation.
"""
import argparse
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path
from audit import ROOT, OUT, INPUT, sha, motion_entries, parse
from integration import PRIVATE, PATCH, catalog
from package_assets import PACKAGE, BASE_PACKAGE, BASE, MOD
import ssbh_data_py as ssbh
from audit_pgwr_svc_guard import functions
import merge_hero_neutral_b_sound as sound
import merge_snake_uptilt_sound as bank

TARGET=ROOT/'builds/.cache/dk_cargo/runtime-target/aarch64-skyline-switch/release'
NRO='atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def tree_hash(files):return sha(''.join(f'{p}\t{h}\n' for p,h in sorted(files.items())).encode())

def measurements():
    snapshot=read(OUT/'integration_snapshot.json')
    assert catalog(PRIVATE)==snapshot['source_files'],'Private compile source drift'
    assert sha(PATCH.read_bytes())==snapshot['patch_sha256']
    gaog=read(BASE_PACKAGE/'MANIFEST.json')
    shared={p:h for p,h in snapshot['source_files'].items() if '/dk_cargo/' not in p}
    original=gaog['source_snapshot']
    # The baseline package may store the snapshot inside a wrapper.
    if 'source_files' in original:original=original['source_files']
    changed={p for p in shared if shared[p]!=original.get(p)}
    assert changed==set(snapshot['baseline']),changed
    assert set(shared)==set(original),'Unexpected shared source additions/removals'
    for p,h in snapshot['source_files'].items():
        if '/dk_cargo/' in p:assert sha((ROOT/'src/pgwr/plugin'/p).read_bytes())==h,p
    allocation=read(OUT/'test_allocation.json')
    ids=[int(v,0) for v in allocation['roles'].values()]
    assert ids==list(range(0x400,0x412)) and min(ids)>allocation['max_native_status_count']
    assert not set(ids)&set(allocation['shared_ids']) and allocation['production_ids'] is None
    native=read(OUT/'victim_registration.json')['cargo']
    assert len(native)==18 and not any('EXEC' in r['condition'] or 'MAP_CORRECTION' in r['condition'] for r in native)
    registration=(PRIVATE/'src/status/dk_cargo/registration.rs').read_text()
    assert registration.count('.status(')==97 # 94 own + three stock Pre bridges
    for row in native:
        assert 'pgwr_dkc_common_'+format(int(row['function'],0),'x') in registration
    translation=read(OUT/'callback_translation.json')
    assembly=(PRIVATE/'src/status/dk_cargo/callbacks.S').read_text()
    assert sha(assembly.encode())==translation['asm_sha256']
    blob=(TARGET/'libpyra_gamewatch_reskin.nro').read_bytes()
    imports=[s[0] for s in parse(blob)[0] if s[2]==0 and s[0]]
    forbidden=[n for n in imports if 'FighterSpecializer_Donkey' in n or 'donkey_thrown_offset' in n or 'ShoulderedDonkey' in n]
    assert not forbidden,forbidden
    elf=(TARGET/'libpyra_gamewatch_reskin.so').read_bytes(); funcs=functions(elf)
    guard=funcs['pgwr_capture_query_memory'][1][:20]
    assert guard==bytes.fromhex('e10f1ff8c10000d4e20741f8410000b9c0035fd6')
    offset=funcs['pgwr_dkc_thrown_offset']
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    instructions=list(md.disasm(offset[1],offset[0]))
    # The native caller consumes a 128-bit SIMD result in q0. Inspect the
    # linked adapter, including every return path, instead of assuming layout.
    returns=[i for i,x in enumerate(instructions) if x.mnemonic=='ret']
    assert returns
    assert any('v0' in x.op_str or 'q0' in x.op_str for x in instructions)
    vector_asm=[f'{x.address:#x}: {x.mnemonic} {x.op_str}' for x in instructions]
    delta=read(PACKAGE/'ASSET_DELTA.json'); baseline=catalog(BASE)
    assert baseline==delta['baseline_files']==gaog['mod_files']
    assert sha((BASE_PACKAGE/'MANIFEST.json').read_bytes())==delta['baseline_manifest_sha256']
    files=catalog(MOD);assert not set(baseline)-set(files)
    assert {p:h for p,h in files.items() if baseline.get(p)!=h}==delta['delta']
    for row in delta['motion_lists']:
        path=MOD/row['path']
        last=next(r for r in reversed(delta['motion_lists']) if r['path']==row['path'])
        assert sha(path.read_bytes())==last['after_sha256']
        _,rows=motion_entries(path); count=row['original_entries'];additions=row['additions']
        assert [r['raw'] for r in rows[count:count+len(additions)]]==additions
        keys=[r['kind'] for r in rows];assert len(keys)==len(set(keys)),row['path']
        prior=BASE/row['path'] if row['input_source']=='collective' else INPUT/row['input_arc_path']
        _,before=motion_entries(prior)
        # Eflame's second append includes the first attacker append. Compare
        # the native/collective prefix, then the recorded first append above.
        assert [r['raw'] for r in rows[:len(before)]]==[r['raw'] for r in before]
    config=read(MOD/'config.json');oldconfig=read(BASE/'config.json')
    assert {k:v for k,v in config.items() if k!='new-dir-files'}=={k:v for k,v in oldconfig.items() if k!='new-dir-files'}
    for group,paths in oldconfig['new-dir-files'].items():assert set(paths)<=set(config['new-dir-files'][group])
    for group,paths in delta['new_dir_additions'].items():
        assert set(paths)<=set(config['new-dir-files'][group])
        assert all((MOD/p).is_file() for p in paths)
    assert len({r['path'] for r in delta['clips']})==len(delta['clips'])
    shared_count=0
    for row in delta['clips']:
        assert sha((MOD/row['path']).read_bytes())==row['sha256']
        assert sha((INPUT/row['source']).read_bytes())==row['source_sha256']
        if row['shared_template']:
            anim=ssbh.anim_data.read_anim(str(MOD/row['path']))
            assert all(g.group_type==ssbh.anim_data.GroupType.Transform for g in anim.groups)
            source=ssbh.anim_data.read_anim(str(INPUT/row['source']))
            native_nodes=[n.name for g in source.groups if g.group_type==ssbh.anim_data.GroupType.Transform for n in g.nodes]
            assert [n.name for g in anim.groups for n in g.nodes]==native_nodes
            assert len(native_nodes)==row['transform_nodes'] and native_nodes
            shared_count+=1
        else:assert row['sha256']==row['source_sha256']
    assert shared_count==36
    for p,h in delta['input_files'].items():assert sha((INPUT/p).read_bytes())==h
    effects=read(PACKAGE/'effect_audit.json');assert not any(r.get('status')=='BLOCKED' for r in effects)
    for folder,prefix in [('fighter','se_eflame'),('fighter_voice','vc_eflame')]:
        for slot in ['c06','c07']:
            rel=f'sound/bank/{folder}/{prefix}_{slot}'
            before,chunks,labels=bank._read_bank(BASE/rel)
            after,achunks,alabels=bank._read_bank(MOD/rel)
            assert after[:len(before)]==before
            assert sound.tones_read(dict(achunks)[b'TONE'])[:len(before)]==sound.tones_read(dict(chunks)[b'TONE'])
            assert set(labels)=={p for p in alabels if p[1]>>8<len(before)}
    sqb='sound/sequence/fighter/eflame.sqb';before=sound.sqb_read((BASE/sqb).read_bytes())
    assert sound.sqb_read((MOD/sqb).read_bytes())[:len(before)]==before
    for row in effects:
        assert row['decoded_emitter_fields_preserved'] and row['geometry_texture_shader_payloads_checked']
        rel='effect/fighter/eflame/ef_eflame_'+row['slot']+'.eff'
        assert row['output_sha256']==sha((MOD/rel).read_bytes())
    assert 'Finished `release`' in (ROOT/'builds/.cache/dk_cargo/BUILD.txt').read_text()
    return {'tier':'B','runtime_verified':False,'source_snapshot_verified':True,
       'shared_source_patch_files':sorted(changed),'native_victim_callbacks':18,'own_status_callbacks':94,
       'translated_functions':sum(r['functions'] for r in translation['images']),
       'translated_instructions':sum(r['instructions'] for r in translation['images']),
       'forbidden_donor_imports':forbidden,'generic_import_count':len(imports),
       'svc_guard_sha256':sha(guard),'vector_adapter_disassembly':vector_asm,
       'vector_adapter_abi_limit':'SIMD instruction output inspected; Rust unspecified-layout warning retained. Console ABI unverified.',
       'asset_delta_count':len(delta['delta']),'motion_list_appends':len(delta['motion_lists']),
       'owned_victim_clips':len(delta['clips']),'complete_shared_templates':shared_count,
       'mod_files':files,'mod_tree_sha256':tree_hash(files),'file_count':len(files),
       'nro_sha256':sha(blob),'nro_size':len(blob),'elf_sha256':sha(elf)}

def finalize():
    assert not (PACKAGE/'MANIFEST.json').exists(),'Completed packages are immutable'
    report=measurements();save(PACKAGE/'CHECKS.json',report)
    target=PACKAGE/NRO;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(TARGET/'libpyra_gamewatch_reskin.nro',target)
    helper=BASE_PACKAGE/str(Path(NRO).parent)/'libone_slot_eff.nro'
    if helper.is_file():shutil.copyfile(helper,target.parent/helper.name)
    shutil.copyfile(PATCH,PACKAGE/'integration.patch')
    shutil.copyfile(ROOT/'builds/.cache/dk_cargo/BUILD.txt',PACKAGE/'BUILD.txt')
    contracts=PACKAGE/'contracts';contracts.mkdir()
    for name in ['integration_snapshot.json','test_allocation.json','ownership_contract.json',
                 'callback_translation.json','victim_registration.json','native_authorization.json']:
        shutil.copyfile(OUT/name,contracts/name)
    pins={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for directory in [ROOT/'src/pgwr/tools/dk_cargo',
           ROOT/'src/pgwr/plugin/src/status/dk_cargo',OUT] for p in directory.rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    manifest={'task':'dk_cargo','task_version':'0.1.0-test','shared_plugin_version':'0.20.20',
       'readiness':'READY_FOR_HARDWARE_TEST','installed':False,'runtime_verified':False,
       'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'toolchain':'cargo-skyline 3.5.0; task-isolated cached Skyline Rust toolchain',
       'baseline':str(BASE_PACKAGE.relative_to(ROOT)).replace('\\','/'),
       'baseline_manifest_sha256':sha((BASE_PACKAGE/'MANIFEST.json').read_bytes()),
       'nro_path':NRO,'nro_sha256':report['nro_sha256'],'nro_size':report['nro_size'],
       'mod_tree_sha256':report['mod_tree_sha256'],'file_count':report['file_count'],'mod_files':report['mod_files'],
       'status_allocation':read(OUT/'test_allocation.json'),'source_tool_pins':pins,
       'payload_files':{p.relative_to(PACKAGE).as_posix():sha(p.read_bytes()) for p in (PACKAGE/'atmosphere').rglob('*') if p.is_file()},
       'production_blocker':'Collectively allocate 15 attacker + 3 victim roles per eligible table; 18 on eflame. Private 0x400..0x411 is test-only.',
       'limitations':['No console/emulator capture, victim routing, release or cleanup verification.',
           'Host G&W baseline movement physics retained; native cargo kinetics and 1.1 walk modifiers owned.',
           'Retargeted attacker geometry and victim attachment alignment require console review.',
           'Generic engine capture/link/shared-motion interfaces remain engine dependencies; no framework changes.',
           'Pickup uses actual victim native thrown_f script family; all cargo-specific victim families owned.',
           'Rust SIMD Vector3 layout warning; linked SIMD output inspected, runtime ABI unverified.']}
    save(PACKAGE/'MANIFEST.json',manifest)
    check()

def check():
    report=measurements();manifest=read(PACKAGE/'MANIFEST.json')
    for key in ['mod_tree_sha256','file_count','mod_files','nro_sha256','nro_size']:assert manifest[key]==report[key],key
    assert sha((PACKAGE/NRO).read_bytes())==report['nro_sha256']
    for p,h in manifest['payload_files'].items():assert sha((PACKAGE/p).read_bytes())==h
    assert not any(p.name in ['libsmashline_plugin.nro','libarcropolis.nro','libarc_network.nro','libnro_hook.nro'] for p in (PACKAGE/'atmosphere').rglob('*'))
    print('PASS checked cargo candidate:',report['file_count'],'files;',report['asset_delta_count'],'asset deltas')
    print('NRO',report['nro_sha256'],report['nro_size'])
    print('TREE',report['mod_tree_sha256'])
    print('MANIFEST',sha((PACKAGE/'MANIFEST.json').read_bytes()))

if __name__=='__main__':
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    check() if parser.parse_args().check else finalize()
