"""Validate review-only DK cargo deltas and pin their content. Never installs."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import audit
from audit import ROOT,OUT,INPUT,sha,h40,motion_entries
import stage
import merge_hero_neutral_b_sound as sound
import merge_snake_uptilt_sound as append

PACKAGE=stage.PACKAGE
BASE=stage.BASE

def verify():
    pins=json.loads((PACKAGE/'baseline_pins.json').read_text())
    for rel,value in pins.items():
        assert sha((BASE/rel).read_bytes())==value, 'Baseline drift: '+rel
    for row in json.loads((OUT/'local_inputs.json').read_text()):
        assert sha((audit.WS/row['path']).read_bytes())==row['sha256'],row['path']
    for row in json.loads((OUT/'public_sources.json').read_text()):
        assert sha((ROOT/row['file']).read_bytes())==row['sha256'],row['file']
    additions=json.loads((PACKAGE/'motion_list_additions.json').read_text())
    declarations=json.loads((PACKAGE/'config_additions.json').read_text())['new-dir-files']
    for slot,rows in additions.items():
        assert slot in ['c06','c07'] and len(rows)==14
        _,before=motion_entries(BASE/f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        kinds={x['kind'] for x in before}
        for row in rows:
            raw=bytes.fromhex(row['raw'])
            assert struct.unpack_from('<Q',raw,0)[0]==h40(row['kind'])
            assert hex(h40(row['kind'])) not in kinds
            assert struct.unpack_from('<Q',raw,8)[0]==h40(row['game'])
            assert struct.unpack_from('<Q',raw,24)[0]==h40(row['clip'])
            for mapping in row['script_map'].values():
                assert struct.unpack_from('<Q',raw,mapping['offset'])[0]==h40(mapping['owned'])
            rel=f'fighter/eflame/motion/body/{slot}/'+row['clip']
            assert rel in declarations[f'fighter/eflame/{slot}']
            assert (PACKAGE/'review_assets'/rel).is_file()
            assert row['handler_state']=='UNIMPLEMENTED'
    for folder,prefix in [('fighter','se_eflame'),('fighter_voice','vc_eflame')]:
        for slot in ['c06','c07']:
            rel=f'sound/bank/{folder}/{prefix}_{slot}'
            before,chunks,labels=append._read_bank(BASE/rel)
            after,achunks,alabels=append._read_bank(PACKAGE/'review_assets'/rel)
            assert after[:len(before)]==before
            assert sound.tones_read(dict(achunks)[b'TONE'])[:len(before)]==sound.tones_read(dict(chunks)[b'TONE'])
            assert set(labels)=={p for p in alabels if p[1]>>8<len(before)}
    rel='sound/sequence/fighter/eflame.sqb'
    original=sound.sqb_read((BASE/rel).read_bytes())
    assert sound.sqb_read((PACKAGE/'review_assets'/rel).read_bytes())[:len(original)]==original
    for report in json.loads((PACKAGE/'effect_audit.json').read_text()):
        assert report.get('decoded_emitter_fields_preserved')
        assert report['geometry_texture_shader_payloads_checked']
        rel='effect/fighter/eflame/ef_eflame_'+report['slot']+'.eff'
        assert report['output_sha256']==sha((PACKAGE/'review_assets'/rel).read_bytes())
    allowed=set()
    allowed.update(r['path'] for r in json.loads((PACKAGE/'animation_audit.json').read_text()))
    for folder,prefix in [('fighter','se_eflame'),('fighter_voice','vc_eflame')]:
        allowed.update(f'sound/bank/{folder}/{prefix}_{slot}{ext}' for slot in ['c06','c07'] for ext in ['.nus3audio','.nus3bank','.tonelabel'])
    allowed.add('sound/sequence/fighter/eflame.sqb')
    allowed.update(f'effect/fighter/eflame/ef_eflame_{s}.eff' for s in ['c06','c07'])
    allowed.add('effect/fighter/eflame/ef_eflame_c06.merge.json')
    actual={p.relative_to(PACKAGE/'review_assets').as_posix() for p in (PACKAGE/'review_assets').rglob('*') if p.is_file()}
    assert actual==allowed,(actual-allowed,allowed-actual)
    templates=json.loads((PACKAGE/'victim_template_animation_audit.json').read_text())
    assert len(templates)==30
    expected={x['path'] for x in templates}
    actual={p.relative_to(PACKAGE/'review_victim_templates').as_posix()
            for p in (PACKAGE/'review_victim_templates').rglob('*') if p.is_file()}
    assert actual==expected
    for row in templates:
        assert sha((PACKAGE/'review_victim_templates'/row['path']).read_bytes())==row['sha256']
        assert sha((INPUT/row['source']).read_bytes())==row['source_sha256']
        assert not row['hardware_pose_verified']
    victim_additions=json.loads((PACKAGE/'victim_template_motion_additions.json').read_text())
    victim_config=json.loads((PACKAGE/'victim_template_config_additions.json').read_text())['new-dir-files']
    for slot,rows in victim_additions.items():
        assert slot in ('c06','c07') and len(rows)==15
        for row in rows:
            raw=bytes.fromhex(row['raw'])
            assert struct.unpack_from('<Q',raw,0)[0]==h40(row['kind'])
            assert struct.unpack_from('<Q',raw,24)[0]==h40(row['clip'])
            for mapping in row['script_map'].values():
                assert struct.unpack_from('<Q',raw,mapping['offset'])[0]==h40(mapping['owned'])
            assert f'fighter/eflame/motion/body/{slot}/'+row['clip'] in victim_config[f'fighter/eflame/{slot}']
            assert row['handler_state']=='UNIMPLEMENTED'
            assert row['resolver_state']=='UNCONFIRMED_NOT_INSTALLABLE'
    dependency=json.loads((PACKAGE/'victim_dependencies.json').read_text())
    assert dependency['roster_victim_motion_lists']==94
    assert dependency['donor_unresolved_indirect_sites']==0
    assert dependency['victim_unresolved_indirect_sites']==0
    assert not dependency['graph_complete'] and not dependency['runtime_implemented'] and not dependency['ready']
    pose=json.loads((PACKAGE/'native_pose_route.json').read_text())
    assert not pose['complete'] and not pose['runtime_verified']
    assert '0x49f9e0' in pose['functions']
    for entry,row in pose['functions'].items():
        path=OUT/'semantic_asm'/('pose_route_'+entry[2:]+'.asm')
        assert sha(path.read_bytes())==row['asm_sha256']
    native=json.loads((PACKAGE/'native_message_sites.json').read_text())
    singleton=native['cut_in_manager_symbol']['exports']
    assert len(singleton)==1
    assert singleton[0]['name']=='_ZN3lib9SingletonIN3app19FighterCutInManagerEE9instance_E'
    assert singleton[0]['size']==8
    authorization=json.loads((PACKAGE/'native_authorization.json').read_text())
    assert {x['vtable_slot'] for x in authorization['authorized_extensions']}=={'0x170','0x210'}
    assert not authorization['framework_changes_authorized'] and not authorization['other_reserved_hooks_authorized']
    print('PASS: 30 additional template deltas, 94-kind victim matrix, explicit authorization and incomplete-runtime guards')
    print('PASS: pinned inputs, baseline guards, 28 motion deltas, append-only banks/sequence, checked effect metadata, exact file allowlist')

def manifest():
    paths=[p for p in PACKAGE.rglob('*') if p.is_file() and p.name!='MANIFEST.json']
    files={p.relative_to(PACKAGE).as_posix():sha(p.read_bytes()) for p in sorted(paths)}
    source_files=[p for p in OUT.rglob('*') if p.is_file()]+[p for p in Path(__file__).parent.glob('*') if p.is_file()]
    sources={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(source_files)}
    shared=['tools/main_image.py','tools/maindesc.py','tools/audit_event_slots.py',
        'tools/constmap.py','tools/dump_hero_mana_params.py',
        'tools/nro_decomp/nro_flatten.py','tools/nro_decomp/nro_util.py','tools/nro_decomp/status_table.py',
        'tools/merge_hero_neutral_b_sound.py','tools/merge_snake_uptilt_sound.py',
        'tools/merge_hero_neutral_b_effects.py']
    shared_hashes={p:sha((ROOT/p).read_bytes()) for p in shared}
    commit=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    data=dict(task='dk_cargo',package_version='research.1',status='INCOMPLETE_NOT_INSTALLABLE',
        date='2026-10-02',evidence_tier='B',baseline='builds/pgwr/0.20.19',
        baseline_manifest_sha256=sha((ROOT/'builds/pgwr/0.20.19/MANIFEST.json').read_bytes()),
        production_status_ids=None,attacker_status_count=15,victim_status_symbols=3,
        allocation_requirement='15 attacker slots; 3 slots per eligible victim table, including eflame. No production allocation.',
        git_commit=commit,shared_tool_dependencies=shared_hashes,
        toolchain={'python':sys.version,'capstone':'5.0.9','ssbh_data_py':'0.9.1',
                   'extractor':'stable-x86_64-pc-windows-gnu; offline release; task-local path fix'},
        runtime_implemented=False,donor_semantic_graph_complete=False,
        framework_changed=False,hardware_validated=False,files=files,sources=sources,
        tree_sha256=sha(''.join(f'{k}\0{v}\n' for k,v in sorted(files.items())).encode()))
    (PACKAGE/'MANIFEST.json').write_text(json.dumps(data,indent=2)+'\n')
    print('Manifest SHA256',sha((PACKAGE/'MANIFEST.json').read_bytes()))
    print('Package tree SHA256',data['tree_sha256'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',action='store_true')
    args=parser.parse_args();verify()
    if args.manifest:manifest()
