"""Build and package all assets required for Shulk's Fair on Game & Watch c07.

1. Updates G&W c07 motion_list.bin with fair cancel_frame (42) and landing cancel_frame (12).
2. Injects SwordR bone into G&W c07 skeleton (model.nusktb) parented to HaveR.
3. Injects Mythra's Aegis sword mesh (SwordM, 4 subindices) scaled to 1.17 (tip = 12.72)
   into G&W c07 model (numshb, numdlb, numatb, numshexb) matching the hitboxes.
4. Packages Mythra Aegis sword textures (11 nutexb files) into G&W c07 model directory.
5. Retargets c05attackairf.nuanmb with G&W clean body visibility + SwordM visibility enabled.
"""
from pathlib import Path
import os
import shutil
import struct
import zlib
import numpy as np
import ssbh_data_py as s

WORKSPACE = Path(__file__).resolve().parents[3]
# Same configurable dump as build_monkey_flip_assets.py; see the note there.
# Defaults to <workspace_root>/export rather than the drive letter the dump
# happened to have on the machine this was originally written on.
EXPORT = Path(os.environ.get('MGW_EXPORT', WORKSPACE / 'dumps' / 'arc'))
if not EXPORT.is_dir():
    raise SystemExit(
        f'Game dump not found at {EXPORT}. The dump is expected at '
        f'<workspace_root>/export; set MGW_EXPORT to the ArcExplorer export '
        f'directory if it lives somewhere else.')
MOD_OUT = WORKSPACE / 'mod_output/ultimate/mods/mythra_gamewatch_swap'

def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)

def parse_mlist(path):
    data = Path(path).read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data)
    if magic != hash40('motion'):
        raise ValueError(f'Invalid motion-list header: {path}')
    offset = 24
    motions = {}
    for _ in range(count):
        start = offset
        kind, game_script, flags, blend, animations, size = struct.unpack_from('<QQHBBI', data, offset)
        if animations > 3 or size % 8 not in (0, 4):
            raise ValueError(f'Invalid motion entry: {path} at {offset:#x}')
        offset += 24
        names = struct.unpack_from('<' + 'Q' * animations, data, offset)
        offset = (offset + animations * 9 + 3) & ~3
        end = offset + size
        motions[kind] = {
            'raw': data[start:end], 'animations': names, 'game_script': game_script,
            'flags': flags, 'blend': blend,
            'cancel': data[end - 2] if size % 8 == 4 else None,
        }
        offset = end
    return magic, motion_path, motions

def encode_mlist(magic, motion_path, motions):
    return struct.pack('<QQQ', magic, motion_path, len(motions)) + b''.join(m['raw'] for m in motions.values())

def build_assets():
    gw_c07_model = MOD_OUT / 'fighter/gamewatch/model/body/c07'
    gw_c07_motion = MOD_OUT / 'fighter/gamewatch/motion/body/c07'
    gw_c07_model.mkdir(parents=True, exist_ok=True)
    gw_c07_motion.mkdir(parents=True, exist_ok=True)

    print('[1/5] Patching G&W c07 motion_list.bin (fair cancel: 42, landing cancel: 12)...')
    mlist_path = gw_c07_motion / 'motion_list.bin'
    if not mlist_path.exists():
        source_mlist = EXPORT / 'fighter/gamewatch/motion/body/c07/motion_list.bin'
        shutil.copy2(source_mlist, mlist_path)
    
    magic, motion_path, motions = parse_mlist(mlist_path)
    entry = motions[hash40('attack_air_f')]
    raw = bytearray(entry['raw'])
    old_cancel = raw[-2]
    raw[-2] = 42
    entry['raw'] = bytes(raw)
    entry['cancel'] = 42
    landing = motions[hash40('landing_air_f')]
    landing_raw = bytearray(landing['raw'])
    old_landing_cancel = landing_raw[-2]
    landing_raw[-2] = 12
    landing['raw'] = bytes(landing_raw)
    landing['cancel'] = 12
    mlist_path.write_bytes(encode_mlist(magic, motion_path, motions))
    print(f'      Updated attack_air_f cancel_frame from {old_cancel} -> 42')
    print(f'      Updated landing_air_f cancel_frame from {old_landing_cancel} -> 12')

    print('[2/5] Injecting SwordR bone into G&W c07 skeleton (model.nusktb)...')
    skel_shulk = s.skel_data.read_skel(str(EXPORT / 'fighter/shulk/model/body/c00/model.nusktb'))
    b_shulk = next(b for b in skel_shulk.bones if b.name == 'SwordR')
    skel_gw = s.skel_data.read_skel(str(EXPORT / 'fighter/gamewatch/model/body/c07/model.nusktb'))
    haver_idx = next(i for i, b in enumerate(skel_gw.bones) if b.name == 'HaveR')
    
    if not any(b.name == 'SwordR' for b in skel_gw.bones):
        new_bone = s.skel_data.BoneData('SwordR', b_shulk.transform, haver_idx, b_shulk.billboard_type)
        skel_gw.bones.append(new_bone)
        out_skel = gw_c07_model / 'model.nusktb'
        skel_gw.save(str(out_skel))
        print(f'      Saved updated skeleton with SwordR: {out_skel} ({len(skel_gw.bones)} bones)')
    else:
        print('      SwordR already present in skeleton.')

    print('[3/5] Injecting Mythra Aegis sword mesh (SwordM) into G&W c07 model...')
    esword_dir = EXPORT / 'fighter/elight/model/esword/c07'
    esword_mesh = s.mesh_data.read_mesh(str(esword_dir / 'model.numshb'))
    vis_objs = [o for o in esword_mesh.objects if 'VIS' in o.name]

    rot = np.array([
        [0.0, 0.0, -1.0],
        [0.0, 1.0,  0.0],
        [1.0, 0.0,  0.0]
    ], dtype=np.float32)
    scale = 1.82 # Enlarges the visible sword to cover the fair hitbox reach.

    new_objs = []
    for o in vis_objs:
        pos = o.positions[0].data
        o.positions[0].data = (pos @ rot * scale).astype(np.float32)
        o.normals[0].data[:, :3] = (o.normals[0].data[:, :3] @ rot).astype(np.float32)
        o.tangents[0].data[:, :3] = (o.tangents[0].data[:, :3] @ rot).astype(np.float32)
        o.name = 'SwordM_VIS_O_OBJ_O_NOSORT_AS_OPAQUEShape'
        o.parent_bone_name = 'SwordR'
        o.bone_influences = []
        new_objs.append(o)

    # Mesh
    gw_mesh = s.mesh_data.read_mesh(str(EXPORT / 'fighter/gamewatch/model/body/c07/model.numshb'))
    gw_mesh.objects = [o for o in gw_mesh.objects if not o.name.startswith('SwordM')]
    gw_mesh.objects.extend(new_objs)
    gw_mesh.save(str(gw_c07_model / 'model.numshb'))
    print(f'      Saved model.numshb with Mythra sword ({len(gw_mesh.objects)} objects)')

    # Modl
    gw_modl = s.modl_data.read_modl(str(EXPORT / 'fighter/gamewatch/model/body/c07/model.numdlb'))
    gw_modl.entries = [e for e in gw_modl.entries if not e.mesh_object_name.startswith('SwordM')]
    mat_labels = ['alp_light_002', 'def_light_004', 'def_light_005', 'def_light_006']
    for i, mat in enumerate(mat_labels):
        gw_modl.entries.append(s.modl_data.ModlEntryData(
            mesh_object_name='SwordM_VIS_O_OBJ_O_NOSORT_AS_OPAQUEShape',
            mesh_object_subindex=i,
            material_label=mat
        ))
    gw_modl.save(str(gw_c07_model / 'model.numdlb'))
    print(f'      Saved model.numdlb ({len(gw_modl.entries)} entries)')

    # Matl
    gw_matl = s.matl_data.read_matl(str(EXPORT / 'fighter/gamewatch/model/body/c07/model.numatb'))
    esword_matl = s.matl_data.read_matl(str(esword_dir / 'model.numatb'))
    existing_labels = {e.material_label for e in gw_matl.entries}
    for e in esword_matl.entries:
        if e.material_label not in existing_labels:
            if e.material_label == 'alp_light_002':
                e.shader_label = 'SFX_PBS_010000000a008269_opaque'
            gw_matl.entries.append(e)
            existing_labels.add(e.material_label)
    # Remove old metal_shulk_001 if present
    gw_matl.entries = [e for e in gw_matl.entries if e.material_label != 'metal_shulk_001']
    gw_matl.save(str(gw_c07_model / 'model.numatb'))
    print(f'      Saved model.numatb ({len(gw_matl.entries)} entries)')

    # Meshex
    gw_meshex = s.meshex_data.read_meshex(str(EXPORT / 'fighter/gamewatch/model/body/c07/model.numshexb'))
    gw_meshex.mesh_object_groups = [g for g in gw_meshex.mesh_object_groups if g.mesh_object_name != 'SwordM']
    sphere = s.meshex_data.BoundingSphere([6.53, 0.0, 0.0], 11.0)
    flags = [s.meshex_data.EntryFlags(True, True)] * 4
    gw_meshex.mesh_object_groups.append(s.meshex_data.MeshObjectGroupData(
        sphere, 'SwordM', 'SwordM_VIS_O_OBJ_O_NOSORT_AS_OPAQUEShape', flags
    ))
    gw_meshex.save(str(gw_c07_model / 'model.numshexb'))
    print(f'      Saved model.numshexb ({len(gw_meshex.mesh_object_groups)} groups)')

    print('[4/5] Copying Mythra Aegis sword textures to G&W c07...')
    # Clean up old shulk textures if present
    for old_tex in gw_c07_model.glob('metal_shulk_001_*.nutexb'):
        old_tex.unlink()
    # Copy all 11 esword textures
    for tex in esword_dir.glob('*.nutexb'):
        shutil.copy2(tex, gw_c07_model / tex.name)
    print(f'      Copied {len(list(gw_c07_model.glob("*.nutexb")))} texture files.')

    print('[5/5] Retargeting animation with SwordM visibility...')
    shulk_anim_path = EXPORT / 'fighter/shulk/motion/body/c00/c05attackairf.nuanmb'
    gw_anim_path = EXPORT / 'fighter/gamewatch/motion/body/c00/c05attackairf.nuanmb'
    anim_shulk = s.anim_data.read_anim(str(shulk_anim_path))
    anim_gw = s.anim_data.read_anim(str(gw_anim_path))
    
    # Extract G&W clean visibility group
    vis_gw = next(g for g in anim_gw.groups if g.group_type == s.anim_data.GroupType.Visibility)
    sample_flags = vis_gw.nodes[0].tracks[0].transform_flags

    # Remove Shulk-specific visibility and face materials
    anim_shulk.groups = [g for g in anim_shulk.groups 
                         if g.group_type != s.anim_data.GroupType.Visibility 
                         and g.group_type != s.anim_data.GroupType.Material]
    
    # Keep the sword hidden until the swing begins, visible through the
    # active portion of fair, then hidden again before the motion ends.
    vis_gw.nodes = [n for n in vis_gw.nodes if n.name != 'SwordM']
    fair_visibility = [False] * 6 + [True] * 36 + [False] * 18
    new_track = s.anim_data.TrackData('Visibility', False, sample_flags, fair_visibility)
    vis_gw.nodes.append(s.anim_data.NodeData('SwordM', [new_track]))
    anim_shulk.groups.append(vis_gw)
    
    out_anim = gw_c07_motion / 'c05attackairf.nuanmb'
    anim_shulk.save(str(out_anim))
    print(f'      Saved retargeted animation with SwordM: {out_anim}')

    print('\n[SUCCESS] All Fair assets built and packaged successfully!')

if __name__ == '__main__':
    build_assets()
