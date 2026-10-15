"""Asset builders shared by MV-aerial_forward__cloud and MV-special_up__cloud.

Everything is rebuilt from the user's own game files (extracted from gamedata/ssbu-13.0.4/data.arc into
gamedata/mii_customizer/moves/aerial_forward__cloud/{donor,recipient}/). Nothing is written outside
gamedata/mii_customizer/moves/<unit>/.

Shared Cloud assets (built once, by the forward-air unit, used by both):
  * the Buster Sword as a Gunner article `mccloudsword` (model + two one-frame clips),
  * two trail textures for Climhazzard,
  * the effect bank and sound bank additions (mccloud_effects.py, mccloud_sounds.py).
"""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mccloud_common import (WORKSPACE, MOD, G, SHARED, DONOR, RECIPIENT, ARC, hash40, sha256, rel, parse_mlist,
                            owned_entry, build_reference_list, entry_cancel, load_prc)  # noqa: E402

import ssbh_data_py as s  # noqa: E402

ARTICLE = 'mccloudsword'
CLOUD_BODY = DONOR / 'fighter/cloud/model/body/c00'
GW_ARTICLE_MODEL = DONOR / 'fighter/gamewatch/model/normal_weapon/c00'
GW_ARTICLE_MOTION = DONOR / 'fighter/gamewatch/motion/normal_weapon/c00'
VANILLA_MLIST = RECIPIENT / 'fighter/miigunner/motion/body/c00/motion_list.bin'
DONOR_MLIST = DONOR / 'fighter/cloud/motion/body/c00/motion_list.bin'
INDEX = WORKSPACE / 'mods/ssbu_mod_new/dumps/decoded/arc_files.tsv'  # read-only ARC path index

SWORD_MESHES = {'bastar_sword_R_VIS_O_OBJShape': 'mccloud_sword_r', 'bastar_sword_L_VIS_O_OBJShape': 'mccloud_sword_l'}
SWORD_MATERIAL_DONOR = 'def_cloud_004'
SWORD_MATERIAL = 'mccloud_sword'
SWORD_TEXTURES = ('def_cloud_004_col', 'def_cloud_004_nor', 'def_cloud_004_prm')
SWORD_ROOT = 'Have'
# article motion kinds: which hand's blade is drawn
SWORD_MOTIONS = {'mc_cloud_sword_r': ('a00mccloudswordr.nuanmb', 'mccloudswordr', (True, False)),
                 'mc_cloud_sword_l': ('a00mccloudswordl.nuanmb', 'mccloudswordl', (False, True))}

TRAILS = {'tex_cloud_sword1_red': 'tex_mc_cloud_sword1_red', 'tex_cloud_sword2': 'tex_mc_cloud_sword2'}

# files this build needs from the archive (ARC path, donor/recipient root)
EXTRACT = {
    'donor': ['fighter/cloud/model/body/c00/', 'fighter/cloud/motion/body/c00/a00wait1.nuanmb',
              'fighter/cloud/motion/body/c00/c05attackairf.nuanmb', 'fighter/cloud/motion/body/c00/c05landingairf.nuanmb',
              'fighter/cloud/motion/body/c00/d02special*', 'fighter/cloud/motion/body/c00/motion_list.bin',
              'fighter/cloud/param/vl.prc', 'effect/fighter/cloud/ef_cloud.eff', 'effect/fighter/cloud/trail/',
              'sound/bank/fighter/se_cloud.nus3audio', 'sound/bank/fighter/se_cloud.nus3bank',
              'sound/bank/fighter/se_cloud.tonelabel', 'fighter/gamewatch/model/normal_weapon/c00/',
              'fighter/gamewatch/motion/normal_weapon/c00/', 'prebuilt:/nro/release/lua2cpp_cloud.nro',
              'prebuilt:/nro/release/lua2cpp_common.nro'],
    'recipient': ['effect/fighter/miigunner/ef_miigunner.eff', 'sound/bank/fighter/se_miigunner.nus3audio',
                  'sound/bank/fighter/se_miigunner.nus3bank', 'sound/bank/fighter/se_miigunner.tonelabel',
                  'fighter/miigunner/motion/body/c00/motion_list.bin',
                  'fighter/miigunner/motion/body/c00/a00wait1.nuanmb'],
}


def extract_inputs() -> None:
    """Pull the inputs from the user's data.arc when they are not on disk yet (private arc-extract copy)."""
    need = [DONOR / 'effect/fighter/cloud/ef_cloud.eff', CLOUD_BODY / 'model.numshb',
            RECIPIENT / 'effect/fighter/miigunner/ef_miigunner.eff', VANILLA_MLIST,
            GW_ARTICLE_MODEL / 'model.xmb', DONOR / 'fighter/cloud/param/vl.prc']
    if all(p.is_file() for p in need):
        return
    exe = MOD / 'builds/.cache/MV-aerial_forward__cloud-target/arc-extract/release/arc-extract.exe'
    if not exe.is_file():
        raise RuntimeError(f'{rel(exe)} missing: build scratch/2026-10-07_MV-aerial_forward__cloud/arc-extract '
                           f'(cargo build --release, CARGO_TARGET_DIR=builds/.cache/MV-aerial_forward__cloud-target/arc-extract)')
    for root, paths in EXTRACT.items():
        r = subprocess.run([str(exe), '--arc', str(ARC), '--out', str(SHARED / root), '--index', str(INDEX)] + paths,
                           capture_output=True, text=True)
        if r.returncode != 0 or ', 0 failed' not in r.stdout:
            raise RuntimeError(f'arc-extract failed: {r.stdout[-500:]} {r.stderr[-500:]}')


# ---------------------------------------------------------------------------
# Buster Sword article
# ---------------------------------------------------------------------------

def build_sword(package: Path) -> dict:
    """Cloud's two sword meshes (one per hand, both bound to a hand bone in his body model) as a stand-alone model.

    The vertices are in the hand bone's space already (single-bound, parent HaveR / HaveL), so the article has
    one bone, `Have`, and both meshes hang off it unchanged. Which blade is drawn is the clip's Visibility track.
    """
    model_dir = package / f'fighter/miigunner/model/{ARTICLE}/c00'
    motion_dir = package / f'fighter/miigunner/motion/{ARTICLE}/c00'
    for d in (model_dir, motion_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    mesh = s.mesh_data.read_mesh(str(CLOUD_BODY / 'model.numshb'))
    objs = []
    stats = {}
    for o in mesh.objects:
        if o.name in SWORD_MESHES:
            if o.bone_influences or o.parent_bone_name not in ('HaveR', 'HaveL'):
                raise RuntimeError(f'{o.name}: expected a mesh single-bound to a hand bone')
            donor_parent = o.parent_bone_name
            pos = [list(map(float, p)) for p in o.positions[0].data]
            o.name = SWORD_MESHES[o.name] + '_VIS_O_OBJShape'
            o.subindex = 0
            o.parent_bone_name = SWORD_ROOT
            objs.append(o)
            stats[o.name] = {'donor_parent_bone': donor_parent, 'vertices': len(pos),
                             'min': [min(p[i] for p in pos) for i in range(3)],
                             'max': [max(p[i] for p in pos) for i in range(3)]}
    if len(objs) != 2:
        raise RuntimeError(f'found {len(objs)} sword meshes in Cloud\'s body model, expected 2')
    objs.sort(key=lambda o: o.name, reverse=True)  # r first
    mesh.objects = objs
    mesh.save(str(model_dir / 'model.numshb'))

    skel = s.skel_data.read_skel(str(CLOUD_BODY / 'model.nusktb'))
    ident = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    skel.bones = [s.skel_data.BoneData(SWORD_ROOT, __import__('numpy').array(ident, dtype='float32'), None)]
    skel.save(str(model_dir / 'model.nusktb'))

    matl = s.matl_data.read_matl(str(CLOUD_BODY / 'model.numatb'))
    entry = [e for e in matl.entries if e.material_label == SWORD_MATERIAL_DONOR]
    if len(entry) != 1:
        raise RuntimeError('Cloud\'s sword material def_cloud_004 not found')
    entry[0].material_label = SWORD_MATERIAL
    tex = sorted(t.data for t in entry[0].textures if not t.data.startswith('#'))
    if tex != sorted(SWORD_TEXTURES):
        raise RuntimeError(f'sword material textures are {tex}')
    matl.entries = entry
    matl.save(str(model_dir / 'model.numatb'))
    for t in SWORD_TEXTURES:
        shutil.copyfile(CLOUD_BODY / f'{t}.nutexb', model_dir / f'{t}.nutexb')

    modl = s.modl_data.read_modl(str(CLOUD_BODY / 'model.numdlb'))
    modl.entries = [s.modl_data.ModlEntryData(o.name, 0, SWORD_MATERIAL) for o in objs]
    modl.animation_file_name = None
    modl.save(str(model_dir / 'model.numdlb'))
    shutil.copyfile(model_dir / 'model.numdlb', model_dir / 'model.nusrcmdlb')

    meshex = s.meshex_data.MeshExData.from_mesh_objects(objs)
    meshex.save(str(model_dir / 'model.numshexb'))
    hlpb = s.hlpb_data.read_hlpb(str(CLOUD_BODY / 'model.nuhlpb'))
    hlpb.aim_constraints = []
    hlpb.orient_constraints = []
    hlpb.save(str(model_dir / 'model.nuhlpb'))
    # model.xmb holds model-wide draw settings (type "fighter", lightset, shadow), no mesh names: the donor
    # article's file is shipped unchanged, like update.prc below.
    shutil.copyfile(GW_ARTICLE_MODEL / 'model.xmb', model_dir / 'model.xmb')

    # motion: two kinds, one frame each
    template = s.anim_data.read_anim(str(GW_ARTICLE_MOTION / 'c05attackairn.nuanmb'))
    for kind, (clip, _suffix, (vis_r, vis_l)) in SWORD_MOTIONS.items():
        anim = template
        anim.final_frame_index = 0.0
        anim.groups = [
            s.anim_data.GroupData(s.anim_data.GroupType.Transform, [s.anim_data.NodeData(SWORD_ROOT, [
                s.anim_data.TrackData('Transform', values=[s.anim_data.Transform(
                    [1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0])])])]),
            s.anim_data.GroupData(s.anim_data.GroupType.Visibility, [
                s.anim_data.NodeData('mccloud_sword_l', [s.anim_data.TrackData('Visibility', values=[vis_l])]),
                s.anim_data.NodeData('mccloud_sword_r', [s.anim_data.TrackData('Visibility', values=[vis_r])])]),
        ]
        anim.save(str(motion_dir / clip))
    gw_magic, _gw_path, gw_entries = parse_mlist((GW_ARTICLE_MOTION / 'motion_list.bin').read_bytes())
    tmpl = next(e for e in gw_entries if e['n_anims'] == 1 and e['flags'] == 0)
    if tmpl['size'] != 16:
        raise RuntimeError('donor article motion entry is not the 16-byte-tail form')
    raws = []
    for kind, (clip, suffix, _vis) in SWORD_MOTIONS.items():
        raw = bytearray(tmpl['raw'])
        struct.pack_into('<QQ', raw, 0, hash40(kind), hash40(f'game_{suffix}'))
        struct.pack_into('<Q', raw, 24, hash40(clip))
        struct.pack_into('<QQ', raw, tmpl['tail_offset'], hash40(f'sound_{suffix}'), hash40(f'effect_{suffix}'))
        raws.append(bytes(raw))
    mlist = struct.pack('<QQQ', gw_magic, hash40(f'fighter/miigunner/motion/{ARTICLE}/c00'), len(raws)) + b''.join(raws)
    parse_mlist(mlist)
    (motion_dir / 'motion_list.bin').write_bytes(mlist)
    shutil.copyfile(GW_ARTICLE_MOTION / 'update.prc', motion_dir / 'update.prc')

    # read back
    back = s.mesh_data.read_mesh(str(model_dir / 'model.numshb'))
    if [o.name for o in back.objects] != [o.name for o in objs] or any(o.parent_bone_name != SWORD_ROOT for o in back.objects):
        raise RuntimeError('sword mesh did not round-trip')
    if [b.name for b in s.skel_data.read_skel(str(model_dir / 'model.nusktb')).bones] != [SWORD_ROOT]:
        raise RuntimeError('sword skeleton did not round-trip')
    return {'article': ARTICLE, 'meshes': stats, 'root_bone': SWORD_ROOT, 'material': SWORD_MATERIAL,
            'textures': list(SWORD_TEXTURES),
            'motion_kinds': {k: {'clip': v[0], 'sword_r': v[2][0], 'sword_l': v[2][1]} for k, v in SWORD_MOTIONS.items()},
            'donor_model': rel(CLOUD_BODY), 'unchanged_copies': {
                'model.xmb': rel(GW_ARTICLE_MODEL / 'model.xmb'), 'update.prc': rel(GW_ARTICLE_MOTION / 'update.prc'),
                **{f'{t}.nutexb': rel(CLOUD_BODY / f'{t}.nutexb') for t in SWORD_TEXTURES}}}


# ---------------------------------------------------------------------------
# Trail textures (Climhazzard)
# ---------------------------------------------------------------------------

def build_trails(package: Path) -> dict:
    """Cloud's two ribbon textures under the Gunner's own trail folder, internal name = file name = owned name.

    The engine asks for a trail by the hash of the NUTEXB footer name (reference repo, handbook/10). Only the
    64-byte name field is rewritten; every pixel byte is the donor's.
    """
    out_dir = package / 'effect/fighter/miigunner/trail'
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for donor, owned in TRAILS.items():
        d = bytearray((DONOR / f'effect/fighter/cloud/trail/{donor}.nutexb').read_bytes())
        if d[-0x70:-0x6c] != b' XNT' or d[-8:-4] != b' XET':
            raise RuntimeError(f'{donor}: unexpected NUTEXB footer')
        name = bytes(d[-0x6c:-0x2c]).rstrip(b'\0').decode()
        if name != donor.upper():
            raise RuntimeError(f'{donor}: footer name is {name}')
        new = owned.upper().encode()
        d[-0x6c:-0x2c] = new + b'\0' * (0x40 - len(new))
        (out_dir / f'{owned}.nutexb').write_bytes(d)
        report[owned] = {'donor': donor, 'footer_name': owned.upper(), 'request_hash': f'0x{hash40(owned):010x}',
                         'bytes_changed': 'footer name field only'}
    return report


# ---------------------------------------------------------------------------
# Body clips + motion list entries
# ---------------------------------------------------------------------------

def build_body_clips(package: Path, clips: dict, reference: Path) -> dict:
    """clips: owned kind -> (donor kind, donor clip, owned clip, script suffix, trans_scale, require_limb_motion)."""
    import mccloud_retarget as rt
    body = package / 'fighter/miigunner/motion/body/c00'
    body.mkdir(parents=True, exist_ok=True)
    _, _, donor_entries = parse_mlist(DONOR_MLIST.read_bytes())
    by_kind = {e['kind']: e for e in donor_entries}
    report = {}
    raws = []
    for owned_kind, (donor_kind, donor_clip, owned_clip, suffix, trans_scale, need_limbs) in clips.items():
        e = by_kind[hash40(donor_kind)]
        if e['anims'] != (hash40(donor_clip),):
            raise RuntimeError(f'donor {donor_kind} does not name {donor_clip}')
        rep = rt.retarget(DONOR / 'fighter/cloud/motion/body/c00' / donor_clip, body / owned_clip,
                          trans_scale=trans_scale, require_limb_motion=need_limbs)
        raw = owned_entry(e, owned_kind, owned_clip, suffix)
        raws.append(raw)
        rep['motion_entry'] = {
            'owned_kind': owned_kind, 'owned_kind_hash': f'0x{hash40(owned_kind):010x}',
            'donor_kind': donor_kind, 'donor_clip': donor_clip, 'donor_clip_sha256': sha256(
                DONOR / 'fighter/cloud/motion/body/c00' / donor_clip),
            'owned_clip': owned_clip, 'owned_clip_hash': f'0x{hash40(owned_clip):010x}',
            'scripts': {c: f'{c}_{suffix}' for c in ('game', 'expression', 'sound', 'effect')},
            'flags': f'0x{e["flags"]:04x}', 'blend': e['blend'], 'cancel_field': entry_cancel(e), 'size': e['size'],
            'entry_sha256': __import__('hashlib').sha256(raw).hexdigest(),
        }
        report[owned_kind] = rep
    ref = build_reference_list(VANILLA_MLIST.read_bytes(), raws)
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_bytes(ref)
    _, _, ref_entries = parse_mlist(ref)
    vanilla_n = len(ref_entries) - len(raws)
    return {'clips': report, 'reference_list': {'path': rel(reference), 'sha256': sha256(reference),
                                                'entries': len(ref_entries), 'vanilla_entries': vanilla_n,
                                                'vanilla_sha256': sha256(VANILLA_MLIST)}}


def manifest_files(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): {'size': p.stat().st_size, 'sha256': sha256(p)}
            for p in sorted(root.rglob('*')) if p.is_file()}


def cloud_params() -> dict:
    vl = load_prc(DONOR / 'fighter/cloud/param/vl.prc')
    hi = vl['param_special_hi'][0]
    fp = load_prc(WORKSPACE / 'gamedata/ssbu-13.0.4/files/fighter/common/param/fighter_param.prc')['fighter_param_table']
    rows = {r['fighter_kind'][1]: r for r in fp if isinstance(r.get('fighter_kind'), tuple)}
    cloud, gunner = rows['fighter_kind_cloud'], rows['fighter_kind_miigunner']
    return {'param_special_hi': hi,
            'cloud': {k: cloud[k] for k in ('scale', 'landing_attack_air_frame_f', 'air_speed_x_stable')},
            'miigunner': {k: gunner[k] for k in ('scale', 'landing_attack_air_frame_f', 'air_speed_x_stable')}}
