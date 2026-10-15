"""Stage owned cargo pose template deltas for review, never install.

The native sharing resolver and victim routing are NOT implemented. This package
captures the 15 actual donor templates (five poses, three body variants), rather
than substituting a universal pose for every victim. Each output is read back.
"""
import json
import struct
import audit
from audit import ROOT, INPUT, OUT, h40, sha
import stage
import ssbh_data_py as ssbh


def run():
    matrix = json.loads((OUT / 'victim_roster_motion_matrix.json').read_text())
    entries = matrix['matrix']['fighter/donkey/motion/body/c00/motion_list.bin']['entries']
    rows = [(name, row) for name, data in entries.items() for row in data
            if name.startswith('shouldered_donkey') or name.startswith('thrown_f_donkey_')]
    assert len(rows) == 15
    outputs, deltas, declarations = [], {}, {}
    for slot in ('c06', 'c07'):
        bones = {b.name for b in ssbh.skel_data.read_skel(str(stage.BASE / f'fighter/eflame/model/body/{slot}/model.nusktb')).bones}
        idle = ssbh.anim_data.read_anim(str(stage.BASE / f'fighter/eflame/motion/body/{slot}/a00wait1.nuanmb'))
        visibility = [g for g in idle.groups if g.group_type == ssbh.anim_data.GroupType.Visibility]
        deltas[slot] = []
        declarations[f'fighter/eflame/{slot}'] = []
        for name, row in rows:
            source_rel = row['resolved_clips'][0][0]
            clip = ssbh.anim_data.read_anim(str(INPUT / source_rel))
            dropped = []
            groups = []
            for group in clip.groups:
                if group.group_type == ssbh.anim_data.GroupType.Transform:
                    dropped.extend(n.name for n in group.nodes if n.name not in bones)
                    group.nodes = [n for n in group.nodes if n.name in bones]
                    groups.append(group)
            clip.groups = groups + visibility
            own_clip = 'pgwrdkcargovictim' + source_rel.rsplit('/', 1)[1]
            rel = f'fighter/eflame/motion/body/{slot}/{own_clip}'
            dest = stage.PACKAGE / 'review_victim_templates' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            clip.save(str(dest))
            readback = ssbh.anim_data.read_anim(str(dest))
            assert readback.final_frame_index == clip.final_frame_index
            assert all(n.name in bones for g in readback.groups
                       if g.group_type == ssbh.anim_data.GroupType.Transform for n in g.nodes)
            raw = bytearray.fromhex(row['raw'])
            own_kind = 'pgwr_dk_cargo_victim_' + name
            struct.pack_into('<Q', raw, 0, h40(own_kind))
            struct.pack_into('<Q', raw, 24, h40(own_clip))
            base = name.removesuffix('_dx').removesuffix('_girl')
            script_map = {}
            for category in ('game', 'effect', 'sound', 'expression'):
                old = category + '_' + base.replace('_', '')
                new = category + '_pgwr_dk_cargo_victim_' + base.replace('_', '')
                offset = raw.find(struct.pack('<Q', h40(old)))
                assert offset >= 0, (name, category, old)
                struct.pack_into('<Q', raw, offset, h40(new))
                script_map[category] = {'donor': old, 'owned': new, 'offset': offset}
            declarations[f'fighter/eflame/{slot}'].append(rel)
            deltas[slot].append({'donor_kind': name, 'kind': own_kind, 'clip': own_clip,
                                'raw': raw.hex(), 'script_map': script_map,
                                'handler_state': 'UNIMPLEMENTED',
                                'resolver_state': 'UNCONFIRMED_NOT_INSTALLABLE'})
            outputs.append({'path': rel, 'source': source_rel, 'source_sha256': sha((INPUT/source_rel).read_bytes()),
                            'sha256': sha(dest.read_bytes()), 'final_frame': readback.final_frame_index,
                            'dropped_transform_nodes': dropped, 'hardware_pose_verified': False})
    for name, obj in [('victim_template_animation_audit.json', outputs),
                      ('victim_template_motion_additions.json', deltas),
                      ('victim_template_config_additions.json', {'new-dir-files': declarations})]:
        (stage.PACKAGE/name).write_text(json.dumps(obj, indent=2) + '\n')
    print('PASS: 30 victim template clips read back; owned raw motion/script/clip names; routing UNIMPLEMENTED')


if __name__ == '__main__':
    run()
