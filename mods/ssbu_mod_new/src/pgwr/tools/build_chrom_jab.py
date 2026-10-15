"""Retarget Chrom's jab (Attack11) for Mr. Game & Watch on Pyra c06/c07.

Donor: Chrom (`refs/chrom_jab/arc/fighter/chrom`, live-extracted 2026-09-30).
Recipient: Pyra c06/c07 (eflame, reskinned to G&W).
Weapon: Pyra's own Aegis esword - one of eflame's five native articles, not a
clone. 0.16.0 used a cloned `chrom_sword` article here and it never rendered on
hardware; see `handbook/graveyard.md` R-22 and `plugin/src/acmd/chrom_jab.rs`.
Cancel frame: `attack_11` = 23, taken whole from Chrom's own motion list.

# Why the retarget is still worth doing, with Pyra's blade instead

The Aegis esword *owns its pose*: its own clips animate `HaveR`, `Sword1` and
`Sword_flameA..E`, so the blade does not simply follow the body - which is why
`tools/build_esword_pose.py` had to place it (graveyard R-20/R-21). The retarget
does not exist to aim the blade, then. It exists because Chrom's jab *animation*
is the thing being ported: the 42-frame clip is what swings the arm, and the arm
is what carries the hitboxes' parent chain. The `Sword1`/`Sword2` tracks are kept
because they sit on the same chain the Aegis article hangs off, so the hand ends
up where Chrom's own animation put it.

# Why the filter is the built skeleton, not G&W's

`build_cloud_fair.py` filters donor nodes against G&W's own 45 bones and keeps 36
of Cloud's. That is sufficient there because the only visible mesh is G&W's. Here it
is not sufficient: Chrom's jab clip animates `Sword1`/`Sword2` (12 of its 96 nodes
are arm/weapon chain the Aegis work kept dropping), and those bones exist on the
recipient because `build_skeleton` grafted Pyra's whole skeleton on. Filtering
against the *built* model keeps 80 of 96, so the arm and the weapon chain are
animated rather than dropped and left to the bind pose.

# What is not here

No sword track is written into the clip: the article is posed by its own clips
(graveyard R-21), so a body-side track would be redundant at best. The Mythra
trail lives in the ACMD module - see `plugin/src/acmd/chrom_jab.rs`.
"""
from pathlib import Path
import hashlib
import struct
import zlib

import ssbh_data_py as s

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
EXPORT = ROOT / 'dumps/arc'
REF = ROOT / 'refs/chrom_jab'
DONOR = REF / 'arc/fighter/chrom'

# Pinned donor data. The clip is in dumps/ rather than refs/ because the ArcExplorer
# export already had it; the motion list is one of the files this session extracted.
DONOR_CLIPS = {
    'c00attack11.nuanmb': {
        'src': EXPORT / 'fighter/chrom/motion/body/c00/c00attack11.nuanmb',
        'sha256': '60cf775fb9a91fbc33ede13dffec5efce55afdb5453f391f6c66b7ae050bfe4b',
        'bytes': 42872,
    },
}
# Chrom's *body* motion list, unlike his sword's, is already in the ArcExplorer export,
# so it is read from there and pinned rather than copied into refs/.
DONOR_MOTION_LIST = EXPORT / 'fighter/chrom/motion/body/c00/motion_list.bin'
DONOR_MOTION_LIST_SHA256 = '1105ad54d66ea0728afcfbc6fe397cde3a3d64cc08d8568c9436c6e2d47ae730'
JAB_KIND = 'attack_11'
JAB_CLIP = 'c00attack11.nuanmb'


def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def get_chrom_motion_entry(target_kind=hash40(JAB_KIND)):
    """Chrom's own raw `attack_11` entry, whole, from the extracted motion list.

    Like the Cloud fair, the donor's entry is used rather than G&W's: it carries
    Chrom's cancel frame (23 against G&W's 16), blend and flags. The animation-name
    field is left as the donor wrote it, and asserted below to name the same file
    hash this build writes, so no alias round-trip is needed.
    """
    data = DONOR_MOTION_LIST.read_bytes()
    if hashlib.sha256(data).hexdigest() != DONOR_MOTION_LIST_SHA256:
        raise RuntimeError(f'{DONOR_MOTION_LIST} is not the pinned revision')
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError(f'{DONOR_MOTION_LIST} is not a motion list')
    offset = 24
    for _ in range(count):
        start = offset
        kind, game_script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        if kind == target_kind:
            cancel = struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None
            if anims != (hash40(JAB_CLIP),):
                raise RuntimeError(
                    f"Chrom's {JAB_KIND} no longer names {JAB_CLIP}: {[hex(a) for a in anims]}")
            return {'raw': data[start:end], 'kind': kind, 'game_script': game_script,
                    'flags': flags, 'blend': blend, 'n_anims': n_anims, 'anims': anims,
                    'size': size, 'cancel': cancel}
        offset = end
    raise RuntimeError(f'Chrom motion list has no kind {target_kind:#x}')


def retarget(model_dir, out_path, gw_slot='c06'):
    """Retarget Chrom's jab clip onto the recipient's built skeleton and G&W's mesh visibility."""
    info = DONOR_CLIPS[JAB_CLIP]
    src = info['src']
    if not src.is_file() or sha(src) != info['sha256'] or src.stat().st_size != info['bytes']:
        raise RuntimeError(f'Donor clip {src} missing or changed')

    skel = s.skel_data.read_skel(str(Path(model_dir) / 'model.nusktb'))
    exact = {b.name for b in skel.bones}
    folded = {b.name.lower(): b.name for b in skel.bones}

    gw_idle = s.anim_data.read_anim(
        str(EXPORT / f'fighter/gamewatch/motion/body/{gw_slot}/a00wait1.nuanmb'))
    gw_vis = next(g for g in gw_idle.groups if g.group_type.name == 'Visibility')

    anim = s.anim_data.read_anim(str(src))
    transform = next(g for g in anim.groups if g.group_type.name == 'Transform')

    kept, dropped, case_only = [], [], []
    for node in transform.nodes:
        if node.name in exact:
            kept.append(node)
        elif node.name.lower() in folded:
            case_only.append((node.name, folded[node.name.lower()]))
        else:
            dropped.append(node.name)
    transform.nodes = kept

    # G&W's idle mesh-visibility states, replicated: Chrom's own vis group names 35
    # of his face/mouth/eye meshes (and `SayaM`, `fal_L/R/e`), none of which exist on
    # the recipient, and his 2 Material groups have no counterpart either.
    vis_nodes = []
    for node in gw_vis.nodes:
        vis_nodes.append(s.anim_data.NodeData(
            node.name, [s.anim_data.TrackData('Visibility', values=[node.tracks[0].values[0]])]))
    vis_group = s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)
    anim.groups = [transform, vis_group]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    anim.save(str(out_path))

    check = s.anim_data.read_anim(str(out_path))
    got = {n.name for n in next(g for g in check.groups if g.group_type.name == 'Transform').nodes}
    if got != {n.name for n in kept}:
        raise RuntimeError(f'Transform node set changed after saving {out_path}')
    frames = len(kept[0].tracks[0].values) if kept and kept[0].tracks else 0
    return {'bones_kept': len(kept), 'bones_dropped': dropped, 'case_only': case_only,
            'vis_nodes': len(vis_nodes), 'frames': frames, 'sha256': sha(out_path)}


def deploy_for_slot(slot, out_dir, gw_slot='c06', model_dir=None):
    """Write the retargeted jab over eflame's own `c00attack11.nuanmb` for one slot."""
    if model_dir is None:
        model_dir = ROOT / 'builds/pgwr/pyra_gamewatch_reskin/ultimate/mods/pyra_gamewatch_reskin' \
                           f'/fighter/eflame/model/body/{slot}'
    dst = Path(out_dir) / JAB_CLIP
    report = retarget(model_dir, dst, gw_slot)
    if report['case_only']:
        raise RuntimeError(f'nodes matched only case-insensitively: {report["case_only"]}')
    return {JAB_CLIP: report, 'motion_entry': {JAB_KIND: get_chrom_motion_entry()['cancel']},
            'dropped': report['bones_dropped']}


if __name__ == '__main__':
    import tempfile
    entry = get_chrom_motion_entry()
    print(f"Chrom attack_11: cancel frame {entry['cancel']}, flags {entry['flags']:#x}, "
          f"anims {[hex(a) for a in entry['anims']]}")
    assert entry['cancel'] == 23, entry['cancel']
    model = ROOT / 'builds/pgwr/pyra_gamewatch_reskin/ultimate/mods/pyra_gamewatch_reskin' \
                  '/fighter/eflame/model/body/c06'
    assert model.is_dir(), f'need a built c06 model first ({model})'
    with tempfile.TemporaryDirectory() as tmp:
        rep = deploy_for_slot('c06', tmp, 'c06', model)
    clip = rep['c00attack11.nuanmb']
    print(f"retarget: {clip['bones_kept']} bones kept, {clip['vis_nodes']} visibility nodes, "
          f"{clip['frames']} frames, sha256 {clip['sha256']}")
    print(f"dropped (not on the recipient): {clip['bones_dropped']}")
    assert clip['bones_kept'] > 36, 'expected the built-skeleton filter to keep more than G&W-only'
    print('build_chrom_jab OK')
