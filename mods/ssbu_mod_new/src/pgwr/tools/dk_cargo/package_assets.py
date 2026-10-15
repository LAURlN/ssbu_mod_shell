"""Stage cargo's mergeable asset deltas on the checked collective + Gaogaen tree.

Usage: python -B src/pgwr/tools/dk_cargo/package_assets.py
Extract exact ARC inputs into gamedata; never modify dump or shared releases.
Retain native victim metadata flags/overlays and all shared-template transforms.
"""
import json
import shutil
import struct
import subprocess
import argparse
from pathlib import Path
from audit import ROOT, WS, INPUT, OUT, h40, sha, motion_entries
import stage
import ssbh_data_py as ssbh

PACKAGE=ROOT/'builds/pgwr/dk_cargo-0.1.0-test'
BASE_PACKAGE=ROOT/'builds/pgwr/gaogaen_throw_b-0.3.0'
BASE=BASE_PACKAGE/'ultimate/mods/pyra_gamewatch_reskin'
MOD=PACKAGE/'ultimate/mods/pyra_gamewatch_reskin'
BASES=['thrown_f','shouldered_donkey','thrown_f_donkey_f','thrown_f_donkey_b','thrown_f_donkey_hi','thrown_f_donkey_lw']
NAMES=[n+s for n in BASES for s in ['', '_dx','_girl']]

def catalog(folder):return {p.relative_to(folder).as_posix():sha(p.read_bytes()) for p in sorted(folder.rglob('*')) if p.is_file()}
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def extract(paths):
    wanted=[p for p in sorted(set(paths)) if not (INPUT/p).is_file()]
    exe=ROOT/'builds/.cache/dk_cargo/arc-target/release/arc-extract.exe'
    for offset in range(0,len(wanted),48):
        result=subprocess.run([str(exe),'--arc','gamedata/ssbu-13.0.4/data.arc','--out',str(INPUT)]+wanted[offset:offset+48],
                              cwd=WS,text=True,capture_output=True)
        assert result.returncode==0,result.stderr
        assert all((INPUT/p).is_file() for p in wanted[offset:offset+48])
    if wanted:print('Extracted exact task inputs:',len(wanted),flush=True)

def aliases(row,name,clip_names=None,owned_scripts=True):
    raw=bytearray.fromhex(row['raw'])
    struct.pack_into('<Q',raw,0,h40('pgwr_dk_cargo_victim_'+name))
    if clip_names:
        assert len(clip_names)==raw[19]
        for index,clip in enumerate(clip_names):struct.pack_into('<Q',raw,24+8*index,h40(clip))
    if owned_scripts:
        base=name.removesuffix('_dx').removesuffix('_girl')
        for family in ['game','effect','sound','expression']:
            old=family+'_'+base.replace('_','');new=family+'_pgwr_dk_cargo_victim_'+base.replace('_','')
            needle=struct.pack('<Q',h40(old));assert raw.count(needle)==1,(name,family)
            struct.pack_into('<Q',raw,raw.index(needle),h40(new))
    assert raw[16:24]==bytes.fromhex(row['raw'])[16:24]
    return bytes(raw)

def merge_list(relative,source,additions):
    current=MOD/relative
    if (BASE/relative).exists():before=current.read_bytes();baseline='collective'
    else:before=(INPUT/source).read_bytes();baseline='local ARC'
    # Reparse the actual target list, not a template from another costume.
    temporary=PACKAGE/'list-input.bin';temporary.write_bytes(before)
    directory,rows=motion_entries(temporary);temporary.unlink()
    kinds={int(r['kind'],0) for r in rows}
    assert not kinds.intersection(struct.unpack_from('<Q',r)[0] for r in additions)
    after=before[:16]+struct.pack('<Q',len(rows)+len(additions))+before[24:]+b''.join(additions)
    current.parent.mkdir(parents=True,exist_ok=True);current.write_bytes(after)
    _,checked=motion_entries(current)
    assert [r['raw'] for r in checked[:len(rows)]]==[r['raw'] for r in rows]
    return {'path':relative,'input_source':baseline,'input_arc_path':source,'before_sha256':sha(before),
            'after_sha256':sha(after),'original_entries':len(rows),'additions':[r.hex() for r in additions]}

def run(retry=False):
    assert not (PACKAGE/'MANIFEST.json').exists(),'Keep completed package trees immutable.'
    assert not MOD.exists() or retry,'Use --retry-prepackage only for an unmanifested stage correction.'
    base_manifest=json.loads((BASE_PACKAGE/'MANIFEST.json').read_text())
    baseline=catalog(BASE);assert baseline==base_manifest['mod_files']
    PACKAGE.mkdir(parents=True,exist_ok=True)
    shutil.copytree(BASE,MOD,dirs_exist_ok=retry)
    stage.BASE=BASE;stage.PACKAGE=PACKAGE;stage.stage()
    effects=json.loads((PACKAGE/'effect_audit.json').read_text())
    assert all(x.get('status')!='BLOCKED' for x in effects),effects
    # Add the task-only attacker output; .merge.json is evidence, never shipped.
    for p in (PACKAGE/'review_assets').rglob('*'):
        if p.is_file() and not p.name.endswith('.merge.json'):
            target=MOD/p.relative_to(PACKAGE/'review_assets');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    config=json.loads((MOD/'config.json').read_text())
    declarations=json.loads((PACKAGE/'config_additions.json').read_text())['new-dir-files']
    changes=[];clips=[];inputs={}
    for slot,rows in json.loads((PACKAGE/'motion_list_additions.json').read_text()).items():
        relative=f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        changes.append(merge_list(relative,relative,[bytes.fromhex(r['raw']) for r in rows]))
    index={x.split('\t')[0].strip() for x in (ROOT/'dumps/decoded/arc_files.tsv').read_text().splitlines()}
    matrix=json.loads((OUT/'victim_roster_motion_matrix.json').read_text())['matrix']
    donor=matrix['fighter/donkey/motion/body/c00/motion_list.bin']['entries']
    templates=[(n,r) for n,rows in donor.items() for r in rows]
    assert len(templates)==18
    donor_files={r['animations'][0]:r['resolved_clips'][0][0] for n,r in templates}
    extract(donor_files.values())
    # Shared poses are consumed by the actual victim skeleton: retaining only
    # G&W bone intersections here would discard required victim limb tracks.
    for slot in ['c06','c07']:
        own_rows=[];group=f'fighter/eflame/{slot}'
        for name,row in templates:
            source=row['resolved_clips'][0][0];own_clip='pgwrdkcargovictim'+source.rsplit('/',1)[1]
            relative=f'fighter/eflame/motion/body/{slot}/{own_clip}'
            animation=ssbh.anim_data.read_anim(str(INPUT/source))
            transforms=[g for g in animation.groups if g.group_type==ssbh.anim_data.GroupType.Transform]
            original_nodes=[n.name for g in transforms for n in g.nodes]
            animation.groups=transforms;animation.save(str(MOD/relative))
            check=ssbh.anim_data.read_anim(str(MOD/relative))
            assert [n.name for g in check.groups for n in g.nodes]==original_nodes
            clips.append({'path':relative,'source':source,'source_sha256':sha((INPUT/source).read_bytes()),
                          'sha256':sha((MOD/relative).read_bytes()),'transform_nodes':len(original_nodes),
                          'shared_template':True,'appearance_groups_removed':True,'final_frame':check.final_frame_index})
            own_rows.append(aliases(row,name,[own_clip],owned_scripts=name.removesuffix('_dx').removesuffix('_girl')!='thrown_f'))
            declarations.setdefault(group,[]).append(relative)
        relative=f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        changes.append(merge_list(relative,relative,own_rows))
    # Resolve every victim's actual costume list and every locally retained
    # animation. The c00 matrix identifies the dependency names, not replacement
    # bytes for other costumes. Existing collective list entries remain exact.
    fighters={path.split('/')[1] for path in matrix}
    lists=sorted(p for p in index if p.endswith('/motion_list.bin') and p.split('/')[1] in fighters
                 and '/motion/body/c' in p and len(p.split('/')[-2])==3)
    extract(lists)
    list_aliases=[];local_copies=[]
    for path in lists:
        if path in ['fighter/eflame/motion/body/c06/motion_list.bin','fighter/eflame/motion/body/c07/motion_list.bin']:
            # This table already supplies the captor's complete shared pose
            # bank and therefore its own victim aliases. A local Pyra pickup
            # copy with the same filename would overwrite that shared bank.
            continue
        _,rows=motion_entries(INPUT/path);named={r['kind']:r for r in rows};prefix=path.removesuffix('motion_list.bin')
        additions=[];group=f'fighter/{path.split("/")[1]}/{path.split("/")[-2]}'
        available={hex(h40(p.rsplit('/',1)[1])):p for p in index if p.startswith(prefix) and p.endswith('.nuanmb')}
        for name in NAMES:
            row=named.get(hex(h40(name)))
            if row is None:continue
            rewritten=[]
            for number,hash in enumerate(row['animations']):
                # Pickel's shared first resource comes from the captor; all
                # subsequent overlay resources stay local and are copied.
                if int(row['flags'],0)&0x1000 and number==0:
                    assert hash in donor_files,(path,name,hash)
                    rewritten.append('pgwrdkcargovictim'+donor_files[hash].rsplit('/',1)[1])
                else:
                    source=available.get(hash);assert source,(path,name,hash)
                    clip='pgwrdkcargovictim'+source.rsplit('/',1)[1]
                    destination=prefix+clip
                    local_copies.append((source,destination))
                    declarations.setdefault(group,[]).append(destination);rewritten.append(clip)
            # Pickup keeps the victim's own native script hash dependencies;
            # these run on that victim's actual kind, never DK code on eflame.
            additions.append(aliases(row,name,rewritten,owned_scripts=name.removesuffix('_dx').removesuffix('_girl')!='thrown_f'))
        if additions:list_aliases.append((path,additions))
    extract(source for source,dest in local_copies)
    for source,destination in sorted(set(local_copies)):
        target=MOD/destination;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(INPUT/source,target)
        inputs[source]=sha((INPUT/source).read_bytes())
        clips.append({'path':destination,'source':source,'source_sha256':inputs[source],
                      'sha256':sha(target.read_bytes()),'shared_template':False,'native_victim_local_resource':True})
    for path,additions in list_aliases:
        # Eflame c06/c07 already includes its own complete parent templates.
        # They also form its victim aliases; no duplicate kind is appended.
        if path in ['fighter/eflame/motion/body/c06/motion_list.bin','fighter/eflame/motion/body/c07/motion_list.bin']:continue
        changes.append(merge_list(path,path,additions));inputs[path]=sha((INPUT/path).read_bytes())
    for group,names in declarations.items():
        old=config['new-dir-files'].setdefault(group,[])
        config['new-dir-files'][group]=old+sorted(set(names)-set(old))
    write(MOD/'config.json',config)
    files=catalog(MOD)
    delta={p:d for p,d in files.items() if baseline.get(p)!=d}
    assert not set(baseline)-set(files)
    write(PACKAGE/'ASSET_DELTA.json',{'baseline_package':BASE_PACKAGE.relative_to(ROOT).as_posix(),
       'baseline_manifest_sha256':sha((BASE_PACKAGE/'MANIFEST.json').read_bytes()),'baseline_files':baseline,
       'delta':delta,'motion_lists':changes,'clips':clips,'new_dir_additions':declarations,'input_files':inputs,
       'runtime_verified':False,'pickup_script_dependency':'Native per-victim thrown_f family; preserved hashes, actual victim kind only.'})
    print('PASS:',len(delta),'asset deltas;',len(changes),'motion-list additions;',len(clips),'owned clips; baseline preserved',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--retry-prepackage',action='store_true')
    run(parser.parse_args().retry_prepackage)
