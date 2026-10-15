"""Corrin's Omega Yato as a Gunner article `mckamuisword` (built from Corrin's own body model).

Same construction as the Cloud units' `mccloud_build.py::build_sword` (research/moves/aerial_forward__cloud.md, section 3),
with Corrin's meshes:

* The Omega Yato is three rigid mesh objects `Kamui_Weapon_VIS_O_OBJShape` (subindex 0, 1, 2) in
  `fighter/kamui/model/body/c00/model.numshb`, each single-bound (no skin weights) to `HaveR`, vertices already in the
  hand bone's space (blade along +Y, about 13.3 units). They are renamed `mckamui_sword_VIS_O_OBJShape` and re-parented to
  one bone `Have` (identity). Their three materials def_sword_001/002/003 are renamed mckamui_sword_001/002/003; the
  texture files are copied unchanged.
* Visibility: one one-frame clip `a00mckamuisword.nuanmb` (motion kind `mc_kamui_sword`) whose Visibility track
  `mckamui_sword` is True. Corrin's own Visibility group `Kamui_Weapon` is the same mesh set; the article's clip is the
  lever that draws it (reference repo handbook/08).
* Article shell: `model.xmb`, `update.prc` and the `normal_weapon` motion-list entry shape are G&W's article files,
  copied or templated unchanged (as the Cloud article does).

Run through the Gunner's article registration (`mckamui.rs`), which registers the article only when its model file is
found on the card. Tier B for the files; whether the article renders is tier D.
"""
from __future__ import annotations

import shutil
import struct
import zlib
from pathlib import Path

import numpy as np
import ssbh_data_py as s

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / 'gamedata/mii_customizer/moves/aerial_up__kamui'
DONOR = OUT / 'donor'
KAMUI_BODY = DONOR / 'fighter/kamui/model/body/c00'
GW_MODEL = DONOR / 'fighter/gamewatch/model/normal_weapon/c00'
GW_MOTION = DONOR / 'fighter/gamewatch/motion/normal_weapon/c00'

ARTICLE = 'mckamuisword'
ROOT = 'Have'
MESH_PREFIX = 'mckamui_sword'
OBJ_NAME = MESH_PREFIX + '_VIS_O_OBJShape'
DONOR_OBJ = 'Kamui_Weapon_VIS_O_OBJShape'
MATERIALS = {'def_sword_001': 'mckamui_sword_001', 'def_sword_002': 'mckamui_sword_002', 'def_sword_003': 'mckamui_sword_003'}
MATERIAL_TEXTURES = {
    'def_sword_001': ['def_sword_001_col', 'def_sword_001_nor', 'def_sword_001_prm'],
    'def_sword_002': ['def_sword_002_col', 'def_sword_002_nor', 'def_sword_002_prm'],
    'def_sword_003': ['default_Normal', 'def_sword_003_col'],
}
TEXTURE_FILES = {'default_Normal': 'default_normal'}  # donor file name on disk (case differs from the material ref)
MOTION_KIND = 'mc_kamui_sword'
CLIP = 'a00mckamuisword.nuanmb'
SCRIPT_SUFFIX = 'mckamuisword'


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def build_sword(package: Path) -> dict:
    model_dir = package / f'fighter/miigunner/model/{ARTICLE}/c00'
    motion_dir = package / f'fighter/miigunner/motion/{ARTICLE}/c00'
    for d in (model_dir, motion_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    mesh = s.mesh_data.read_mesh(str(KAMUI_BODY / 'model.numshb'))
    objs, stats = [], []
    for o in mesh.objects:
        if o.name != DONOR_OBJ:
            continue
        if o.bone_influences or o.parent_bone_name != 'HaveR':
            raise RuntimeError(f'{o.name} {o.subindex}: expected a rigid mesh parented to HaveR')
        pos = [list(map(float, p)) for p in o.positions[0].data]
        stats.append({'subindex': o.subindex, 'vertices': len(pos),
                      'min': [round(min(p[i] for p in pos), 4) for i in range(3)],
                      'max': [round(max(p[i] for p in pos), 4) for i in range(3)]})
        o.name = OBJ_NAME
        o.parent_bone_name = ROOT
        objs.append(o)
    if len(objs) != 3:
        raise RuntimeError(f'found {len(objs)} Omega Yato mesh objects in Corrin\'s body model, expected 3')
    mesh.objects = objs
    mesh.save(str(model_dir / 'model.numshb'))

    ident = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
                     dtype='float32')
    skel = s.skel_data.read_skel(str(KAMUI_BODY / 'model.nusktb'))
    skel.bones = [s.skel_data.BoneData(ROOT, ident, None)]
    skel.save(str(model_dir / 'model.nusktb'))

    matl = s.matl_data.read_matl(str(KAMUI_BODY / 'model.numatb'))
    wanted = [e for e in matl.entries if e.material_label in MATERIALS]
    if sorted(e.material_label for e in wanted) != sorted(MATERIALS):
        raise RuntimeError('Omega Yato materials not found in Corrin\'s model.numatb')
    for e in wanted:
        tex = sorted(t.data for t in e.textures if not t.data.startswith('#'))
        if sorted(tex) != sorted(MATERIAL_TEXTURES[e.material_label]):
            raise RuntimeError(f'{e.material_label} textures are {tex}')
        e.material_label = MATERIALS[e.material_label]
    matl.entries = wanted
    matl.save(str(model_dir / 'model.numatb'))
    for donor_mat in MATERIAL_TEXTURES.values():
        for t in donor_mat:
            src = KAMUI_BODY / f'{TEXTURE_FILES.get(t, t)}.nutexb'
            shutil.copyfile(src, model_dir / f'{t}.nutexb')

    modl = s.modl_data.read_modl(str(KAMUI_BODY / 'model.numdlb'))
    donor_map = {(e.mesh_object_name, e.mesh_object_subindex): e.material_label for e in modl.entries}
    modl.entries = [s.modl_data.ModlEntryData(o.name, o.subindex, MATERIALS[donor_map[(DONOR_OBJ, o.subindex)]])
                    for o in objs]
    modl.animation_file_name = None
    modl.save(str(model_dir / 'model.numdlb'))
    shutil.copyfile(model_dir / 'model.numdlb', model_dir / 'model.nusrcmdlb')

    s.meshex_data.MeshExData.from_mesh_objects(objs).save(str(model_dir / 'model.numshexb'))
    hlpb = s.hlpb_data.read_hlpb(str(KAMUI_BODY / 'model.nuhlpb'))
    hlpb.aim_constraints = []
    hlpb.orient_constraints = []
    hlpb.save(str(model_dir / 'model.nuhlpb'))
    shutil.copyfile(GW_MODEL / 'model.xmb', model_dir / 'model.xmb')

    # one-frame clip: the blade is drawn by this Visibility track
    template = s.anim_data.read_anim(str(GW_MOTION / 'c05attackairn.nuanmb'))
    template.final_frame_index = 0.0
    template.groups = [
        s.anim_data.GroupData(s.anim_data.GroupType.Transform, [s.anim_data.NodeData(ROOT, [
            s.anim_data.TrackData('Transform', values=[s.anim_data.Transform(
                [1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0])])])]),
        s.anim_data.GroupData(s.anim_data.GroupType.Visibility, [
            s.anim_data.NodeData(MESH_PREFIX, [s.anim_data.TrackData('Visibility', values=[True])])]),
    ]
    template.save(str(motion_dir / CLIP))

    # article motion list: one entry, layout copied from G&W's article list (tail = sound, effect hashes)
    gw = (GW_MOTION / 'motion_list.bin').read_bytes()
    magic, _path, count = struct.unpack_from('<QQQ', gw, 0)
    off, tmpl = 24, None
    for _ in range(count):
        start = off
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', gw, off)
        off += 24
        off += 8 * n_anims
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        if n_anims == 1 and flags == 0 and size == 16 and tmpl is None:
            tmpl = gw[start:end]
            tmpl_tail = tail - start
        off = end
    if tmpl is None:
        raise RuntimeError('G&W article list has no 16-byte-tail single-animation entry')
    raw = bytearray(tmpl)
    struct.pack_into('<QQ', raw, 0, hash40(MOTION_KIND), hash40(f'game_{SCRIPT_SUFFIX}'))
    struct.pack_into('<Q', raw, 24, hash40(CLIP))
    struct.pack_into('<QQ', raw, tmpl_tail, hash40(f'sound_{SCRIPT_SUFFIX}'), hash40(f'effect_{SCRIPT_SUFFIX}'))
    mlist = struct.pack('<QQQ', magic, hash40(f'fighter/miigunner/motion/{ARTICLE}/c00'), 1) + bytes(raw)
    (motion_dir / 'motion_list.bin').write_bytes(mlist)
    shutil.copyfile(GW_MOTION / 'update.prc', motion_dir / 'update.prc')

    back = s.mesh_data.read_mesh(str(model_dir / 'model.numshb'))
    if [o.name for o in back.objects] != [OBJ_NAME] * 3 or any(o.parent_bone_name != ROOT for o in back.objects):
        raise RuntimeError('sword mesh did not round-trip')
    if [b.name for b in s.skel_data.read_skel(str(model_dir / 'model.nusktb')).bones] != [ROOT]:
        raise RuntimeError('sword skeleton did not round-trip')
    if [e.material_label for e in s.matl_data.read_matl(str(model_dir / 'model.numatb')).entries] != list(MATERIALS.values()):
        raise RuntimeError('sword material list did not round-trip')
    return {'article': ARTICLE, 'objects': stats, 'root_bone': ROOT, 'materials': list(MATERIALS.values()),
            'motion_kind': MOTION_KIND, 'clip': CLIP, 'visibility_node': MESH_PREFIX,
            'modl_entries': [(o.name, o.subindex) for o in objs]}
