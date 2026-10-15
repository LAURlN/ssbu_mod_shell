"""Retarget Cloud Forward Air (AttackAirF) and LandingAirF for Mr. Game & Watch on Pyra c06/c07.

Donor: Cloud (fighter/cloud)
Recipient: Pyra c06/c07 (eflame, reskinned to G&W)
Hitbox & Animation: Cloud's AttackAirF
Weapon: Pyra's sword (esword)
Sword trail: Respective Mythra sword trail effects
Cancel frames: attack_air_f = 54, landing_air_f = 20 (Cloud's native values from motion_list.bin)No sword track lives here. Until 2026-09-30 this module wrote a `Sword1` node into
the fair clip - a flipped grip plus the article's scale restored - on the theory
that the Aegis article hangs off the grafted body bone `Sword1` and is rigid along
it. Refuted on hardware: the blade did not move. The article is posed by its own
clips in `fighter/eflame/motion/esword/<slot>/`, which animate `HaveR`, `Sword1`
and `Sword_flameA..E`; a body clip can move the hand but cannot re-angle the
blade. `tools/build_esword_pose.py` now owns what the sword looks like. See
`handbook/graveyard.md` R-21.

Consequence worth knowing before touching this again: the old figures this module
quoted for "blade-to-hitbox distance" came from `tools/fair_sword_geometry.py`,
which models the blade as rigidly attached to the body bone. That model *is* the
refuted assumption, so those numbers measure the model rather than the game. Do
not quote them.
"""
from pathlib import Path
import hashlib
import struct
import zlib

import ssbh_data_py as s

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
EXPORT = ROOT / 'dumps/arc'
REFS = ROOT / 'refs/cloud_attack_air_f'

DONOR_CLIPS = {
    'c05attackairf.nuanmb': {
        'src': EXPORT / 'fighter/cloud/motion/body/c00/c05attackairf.nuanmb',
        'sha256': '4f44fce97c11ba16a97a4ff816a71cbfd800e54341519fe4617f205fda7f40dd',
        'bytes': 56472,
    },
    'c05landingairf.nuanmb': {
        'src': EXPORT / 'fighter/cloud/motion/body/c00/c05landingairf.nuanmb',
        'sha256': '63a1c10ada488ad0c7581b1548c035901f148fc8e868225672f48c0b87ce603f',
        'bytes': 39590,
    },
}

def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def get_cloud_motion_entry(target_kind):
    """Extract raw entry from Cloud's dumped motion_list.bin."""
    mlist_path = REFS / 'motion_list.bin'
    data = mlist_path.read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset = 24
    for _ in range(count):
        start = offset
        kind, game_script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = ((offset + n_anims * 9 + 3) & ~3)
        end = offset + size
        if kind == target_kind:
            cancel = None
            if size % 8 == 4:
                cancel = struct.unpack_from('<H', data, end - 2)[0]
            return {
                'raw': data[start:end],
                'kind': kind,
                'game_script': game_script,
                'flags': flags,
                'blend': blend,
                'n_anims': n_anims,
                'anims': anims,
                'size': size,
                'cancel': cancel
            }
        offset = end
    raise RuntimeError(f"Cloud motion list missing kind {target_kind:#x}")

def retarget_cloud_clip(clip_name, out_path, gw_slot='c00'):
    """Retarget one Cloud animation clip for G&W's skeleton and mesh visibility."""
    info = DONOR_CLIPS[clip_name]
    src = info['src']
    if not src.is_file() or sha(src) != info['sha256']:
        raise RuntimeError(f"Donor clip {src} missing or changed")
    
    gw_skel_path = EXPORT / f'fighter/gamewatch/model/body/{gw_slot}/model.nusktb'
    gw_idle_path = EXPORT / f'fighter/gamewatch/motion/body/{gw_slot}/a00wait1.nuanmb'
    
    gw_skel = s.skel_data.read_skel(str(gw_skel_path))
    gw_bones = {b.name for b in gw_skel.bones}
    
    gw_idle = s.anim_data.read_anim(str(gw_idle_path))
    gw_vis = next(g for g in gw_idle.groups if g.group_type.name == 'Visibility')
    
    anim = s.anim_data.read_anim(str(src))
    transform_group = next(g for g in anim.groups if g.group_type.name == 'Transform')
    
    # 1. Keep only recipient-valid bones
    kept_nodes = [n for n in transform_group.nodes if n.name in gw_bones]
    transform_group.nodes = kept_nodes
    
    # 2. Replicate G&W idle mesh visibility
    vis_nodes = []
    for node in gw_vis.nodes:
        val = node.tracks[0].values[0]
        vis_nodes.append(s.anim_data.NodeData(node.name, [s.anim_data.TrackData('Visibility', values=[val])]))
    vis_group = s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)
    
    # Cloud clips have Material groups for EyeL/EyeR which G&W does not have
    anim.groups = [transform_group, vis_group]

    # 3. No sword node: the article is posed by its own clips, not by this one
    #    (module docstring; graveyard R-21).
    expected = {n.name for n in kept_nodes}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    anim.save(str(out_path))

    # Round-trip verify
    check = s.anim_data.read_anim(str(out_path))
    check_transform = next(g for g in check.groups if g.group_type.name == 'Transform')
    if {n.name for n in check_transform.nodes} != expected:
        raise RuntimeError(f"Transform bone mismatch after saving {out_path}")
    return len(kept_nodes), len(vis_nodes)

def deploy_for_slot(slot, out_dir, gw_slot='c00'):
    """Deploy retargeted Cloud fair and landing clips to eflame slot."""
    report = {}
    for name in ('c05attackairf.nuanmb', 'c05landingairf.nuanmb'):
        dst = out_dir / name
        bones, vis = retarget_cloud_clip(name, dst, gw_slot)
        report[name] = {'bones_kept': bones, 'vis_nodes': vis, 'sha256': sha(dst)}
    return report

if __name__ == '__main__':
    print("Self-test: verifying Cloud motion entries...")
    fair_entry = get_cloud_motion_entry(hash40('attack_air_f'))
    landing_entry = get_cloud_motion_entry(hash40('landing_air_f'))
    print(f"Cloud AttackAirF cancel frame: {fair_entry['cancel']} (expected 54)")
    print(f"Cloud LandingAirF cancel frame: {landing_entry['cancel']} (expected 20)")
    assert fair_entry['cancel'] == 54
    assert landing_entry['cancel'] == 20
    print("Retargeting clips to scratch...")
    test_rep = deploy_for_slot('c06', Path('scratch/test_cloud_deploy'), 'c00')
    print("Test report:", test_rep)
    print("build_cloud_fair OK!")
