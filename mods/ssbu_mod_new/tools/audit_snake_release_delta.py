"""Audit a Snake release against an immutable baseline (v1.0.0).

Usage/smoke: --baseline 0.20.10 --version 0.20.11 [--check].
Checks all retained clip files and motion-list rows, assembled sound payloads,
allowed changes/additions and auxiliary NRO equality. Writes BASELINE_DELTA.json
in the new package; offline regression evidence, not a console verdict.
"""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import build_snake_neutral_b_assets as sn
from smoke_snake_sound_preservation import verify

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',required=True);p.add_argument('--version',required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
    old=ROOT/'builds/pgwr'/a.baseline;new=ROOT/'builds/pgwr'/a.version
    old_manifest=json.loads((old/'MANIFEST.json').read_text());new_manifest=json.loads((new/'MANIFEST.json').read_text())
    b=old/'ultimate/mods/pyra_gamewatch_reskin';n=new/'ultimate/mods/pyra_gamewatch_reskin'
    before=old_manifest['mod_file_hashes'];after={f.relative_to(n).as_posix():digest(f) for f in sorted(n.rglob('*')) if f.is_file()}
    assert not set(before)-set(after)
    changed=sorted(k for k in before if before[k]!=after[k]);expected={'config.json','info.toml'}
    for slot in ('c06','c07'):
        expected.add(f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        expected.update(f'sound/bank/fighter/se_eflame_{slot}{ext}' for ext in ('.nus3audio','.nus3bank','.tonelabel'))
        rel=f'fighter/eflame/motion/body/{slot}/motion_list.bin';_,_,original=sn.base.parse_mlist(b/rel);_,_,result=sn.base.parse_mlist(n/rel)
        assert all(result[k]['raw']==v['raw'] for k,v in original.items()),slot
    assert set(changed)<=expected,changed
    added=sorted(set(after)-set(before));declared={rel for _,rel in sn.declared_clips()+sn.declared_pin_files()}
    declared.add('sound/sequence/fighter/eflame.sqb');assert set(added)==declared-set(before)
    verify(b,n)
    rel='atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libone_slot_eff.nro';assert digest(old/rel)==digest(new/rel)
    record={'date':'2026-09-30','tier':'B','hardware_validated':False,'baseline':a.baseline,
      'baseline_manifest_sha256':digest(old/'MANIFEST.json'),'version':a.version,
      'nro_sha256':new_manifest['artifacts']['reskin_nro']['sha256'],
      'changed_baseline_mod_files':changed,'added_mod_files':added,'removed_mod_files':[],
      'retained_motion_rows_byte_exact':True,'retained_audio_tone_records_byte_exact':True,
      'auxiliary_nro_byte_exact':True,'note':'Snake feature adds its own log/observer; global logging remains disabled.'}
    dest=new/'BASELINE_DELTA.json';content=json.dumps(record,indent=2)+'\n'
    if a.check:assert dest.read_text()==content
    else:dest.write_text(content)
    print(f'PASS: {len(changed)} intended overrides, {len(added)} additions; all other mod files/motions/sounds and auxiliary NRO retained')
if __name__=='__main__':main()
