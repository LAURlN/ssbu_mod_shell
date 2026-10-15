"""Build non-installable cargo asset deltas against a pinned release baseline.

No runtime is registered. Writes only builds/pgwr/dk_cargo-research.1.
The baseline bank snapshots must be rebased semantically by the collective installer.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import zlib

import audit
from audit import ROOT, WS, INPUT, OUT, sha, h40, motion_entries
import ssbh_data_py as ssbh
import merge_hero_neutral_b_sound as sound
import merge_snake_uptilt_sound as append
import merge_hero_neutral_b_effects as effect

BASE = ROOT/'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
PACKAGE = ROOT/'builds/pgwr/dk_cargo-research.1'

def digest(path): return sha(path.read_bytes())

def stage():
    PACKAGE.mkdir(parents=True,exist_ok=True)
    payload = PACKAGE/'review_assets'
    pins, animations, additions, declarations = {}, [], {}, {}
    donor_entries = json.loads((OUT/'donor_motion_entries.json').read_text())
    donor_entries = [r for r in donor_entries if any(n.startswith('e01throwf') for n in r['clip_names'])]
    assert len(donor_entries)==14
    resources = set()
    cargo_scripts = [p for p in (OUT/'donor_acmd').glob('*.txt') if p.stem.startswith(('Shoulder','ThrowF'))]
    for path in cargo_scripts:
        resources.update(re.findall(r'Hash40::new\("([^"\n]+)"\)',path.read_text()))
    se_wanted = {n for n in resources if n.startswith('se_donkey_')}
    sequences = {n for n in resources if n.startswith('seq_donkey_')}
    voice_wanted = {n for n in resources if n.startswith('vc_donkey_')}
    records = sound.sqb_read((INPUT/'sound/sequence/fighter/donkey.sqb').read_bytes())
    seq_selected = [r for r in records if int.from_bytes(r[:8],'little') in {h40(n) for n in sequences}]
    assert len(seq_selected)==len(sequences)
    donor_voice = sound.audio_read((INPUT/'sound/bank/fighter_voice/vc_donkey_c00.nus3audio').read_bytes())
    for record in seq_selected:
        voice_wanted.update(n for n,_ in donor_voice if zlib.crc32(n.lower().encode()).to_bytes(4,'little') in record)
    banks = []
    for slot in ['c06','c07']:
        skeleton = BASE/f'fighter/eflame/model/body/{slot}/model.nusktb'
        idle = BASE/f'fighter/eflame/motion/body/{slot}/a00wait1.nuanmb'
        for path in [skeleton,idle,BASE/f'fighter/eflame/motion/body/{slot}/motion_list.bin',BASE/'config.json']:
            pins[path.relative_to(BASE).as_posix()] = digest(path)
        bones = {b.name for b in ssbh.skel_data.read_skel(str(skeleton)).bones}
        idle_clip = ssbh.anim_data.read_anim(str(idle))
        visibility = [g for g in idle_clip.groups if g.group_type==ssbh.anim_data.GroupType.Visibility]
        additions[slot], declarations[f'fighter/eflame/{slot}'] = [], []
        _,base_entries = motion_entries(BASE/f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        baseline_kinds = {x['kind'] for x in base_entries}
        for row in donor_entries:
            donor_name = row['motion_name']
            assert donor_name
            own_kind = 'pgwr_dk_cargo_'+donor_name
            own_clip = 'pgwrdkcargo'+row['clip_names'][0].removesuffix('.nuanmb')+'.nuanmb'
            assert hex(h40(own_kind)) not in baseline_kinds
            src = INPUT/'fighter/donkey/motion/body/c00'/row['clip_names'][0]
            clip = ssbh.anim_data.read_anim(str(src))
            kept,dropped = [],[]
            groups = []
            for g in clip.groups:
                if g.group_type==ssbh.anim_data.GroupType.Transform:
                    dropped += [n.name for n in g.nodes if n.name not in bones]
                    g.nodes = [n for n in g.nodes if n.name in bones]
                    kept += [n.name for n in g.nodes]
                    groups.append(g)
            clip.groups = groups + visibility
            rel = f'fighter/eflame/motion/body/{slot}/{own_clip}'
            dest = payload/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            clip.save(str(dest))
            readback = ssbh.anim_data.read_anim(str(dest))
            assert readback.final_frame_index==clip.final_frame_index
            assert all(n.name in bones for g in readback.groups if g.group_type==ssbh.anim_data.GroupType.Transform for n in g.nodes)
            raw = bytearray.fromhex(row['raw'])
            # Preserve the complete donor timing/tail; change owned names only.
            struct.pack_into('<Q',raw,0,h40(own_kind))
            own_game = 'game_pgwr_dk_cargo_'+donor_name.replace('_','')
            script_map={}
            for category in ['game','effect','sound','expression']:
                old=category+'_'+donor_name.replace('_','')
                new=category+'_pgwr_dk_cargo_'+donor_name.replace('_','')
                position=raw.find(struct.pack('<Q',h40(old)))
                assert position>=0,(donor_name,category)
                script_map[category]=dict(donor=old,owned=new,offset=position)
                struct.pack_into('<Q',raw,position,h40(new))
            assert raw[19]==1
            struct.pack_into('<Q',raw,24,h40(own_clip))
            assert raw[16:24]==bytes.fromhex(row['raw'])[16:24]
            changed=set(range(0,16))|set(range(24,32))
            for mapping in script_map.values():changed.update(range(mapping['offset'],mapping['offset']+8))
            assert all(raw[i]==bytes.fromhex(row['raw'])[i] for i in range(len(raw)) if i not in changed)
            additions[slot].append(dict(kind=own_kind,game=own_game,raw=raw.hex(),clip=own_clip,
                donor_kind=donor_name,donor_raw_sha256=sha(bytes.fromhex(row['raw'])),
                script_map=script_map,handler_state='UNIMPLEMENTED',cancel=row['cancel']))
            declarations[f'fighter/eflame/{slot}'].append(rel)
            animations.append(dict(slot=slot,path=rel,sha256=digest(dest),source_sha256=digest(src),
                frames=readback.final_frame_index,kept=kept,dropped=dropped,
                visual_validation='UNVERIFIED; filtered donor tracks, no capture-anchor validation'))
        for folder,prefix,donor,wanted in [('fighter','se_eflame','se_donkey',se_wanted),('fighter_voice','vc_eflame','vc_donkey',voice_wanted)]:
            rel = f'sound/bank/{folder}/{prefix}_{slot}'
            recipient = BASE/rel
            for ext in ['.nus3audio','.nus3bank','.tonelabel']:
                pins[rel+ext] = digest(recipient.with_suffix(ext))
            rep = append.append_tones(INPUT/f'sound/bank/{folder}/{donor}_c00',recipient,payload/rel,wanted)
            banks.append(rep)
    sequence_path = 'sound/sequence/fighter/eflame.sqb'
    base_sqb = sound.sqb_read((BASE/sequence_path).read_bytes())
    assert not ({int.from_bytes(x[:8],'little') for x in base_sqb} & {int.from_bytes(x[:8],'little') for x in seq_selected})
    dest = payload/sequence_path
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(sound.sqb_write(base_sqb+seq_selected))
    assert sound.sqb_read(dest.read_bytes())[:len(base_sqb)]==base_sqb
    pins[sequence_path] = digest(BASE/sequence_path)
    effects = sorted({n.upper() for n in resources if n.startswith('donkey_')})
    effect_reports = []
    checked_effect = None
    for slot in ['c06','c07']:
        rel = f'effect/fighter/eflame/ef_eflame_{slot}.eff'
        pins[rel] = digest(BASE/rel)
        dest = payload/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        try:
            if checked_effect and checked_effect['recipient_sha256']==pins[rel]:
                shutil.copyfile(payload/'effect/fighter/eflame/ef_eflame_c06.eff',dest)
                report=dict(checked_effect,slot=slot,reused_identical_baseline=True)
                assert digest(dest)==report['output_sha256']
            else:
                metadata=dest.with_suffix('.merge.json')
                if metadata.exists() and dest.exists():
                    report=json.loads(metadata.read_text())
                    assert report['recipient_sha256']==pins[rel]
                    assert report['donor_sha256']==digest(INPUT/'effect/fighter/donkey/ef_donkey.eff')
                    assert report['resource_names']==effects and report['output_sha256']==digest(dest)
                else:
                    effect.merge(BASE/rel,dest,donor_file=INPUT/'effect/fighter/donkey/ef_donkey.eff',
                        effect_names=set(effects),donor_sha256=digest(INPUT/'effect/fighter/donkey/ef_donkey.eff'),
                        scratch=ROOT/'builds/.cache/dk_cargo/effects')
                    report=json.loads(metadata.read_text())
                checked_effect=report
                report=dict(report,slot=slot)
            effect_reports.append(report)
        except (AssertionError,RuntimeError,FileNotFoundError) as error:
            effect_reports.append(dict(slot=slot,status='BLOCKED',error=str(error)))
    for name,obj in [('baseline_pins.json',pins),('motion_list_additions.json',additions),
                     ('config_additions.json',{'new-dir-files':declarations}),
                     ('animation_audit.json',animations),('sound_audit.json',banks),
                     ('effect_audit.json',effect_reports),
                     ('resources.json',dict(all=sorted(resources),se=sorted(se_wanted),vc=sorted(voice_wanted),sequences=sorted(sequences),effects=effects))]:
        (PACKAGE/name).write_text(json.dumps(obj,indent=2)+'\n')
    print(f'Staged {len(animations)} clips; {len(banks)} sound banks; {len(seq_selected)} sequences; {len(effects)} requested effects. Runtime absent, NOT READY.')

if __name__=='__main__': stage()
