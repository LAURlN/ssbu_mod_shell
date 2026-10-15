"""Retarget Little Mac's forward smash for Mr. Game & Watch on Pyra c06/c07 (v1.0.0).

Donor: Little Mac (`refs/littlemac_attack_s4/arc/fighter/littlemac`, live-extracted
2026-09-30, provenance `refs/littlemac_attack_s4/SOURCE.json`).
Recipient: Pyra c06/c07 (eflame, reskinned to G&W).
Hitboxes/effects/sound/rumble: `plugin/src/acmd/littlemac_attack_s4.rs`.

Scope: the forward smash itself (`attack_s4_s`), its charge hold
(`attack_s4_hold`), and the two up/down-angled variants (`attack_s4_hi` /
`attack_s4_lw`).

# Why the angled variants are here, and what is still unproven

An earlier revision of this file refused to install `attack_s4_hi` /
`attack_s4_lw`, on the grounds that no name or hash for them exists in
`main.bin`. That reasoning was wrong, and this section records why so the
mistake is not repeated.

*Measured (tier B):* the strings `attack_s4_hi`, `attack_s4_lw` and the ASCII
`SMASH_S` / `SMASH_HI` / `SMASH_LW` do **not** appear in `main.bin`, and neither
does `hash40` of any of them as a u64. So the engine does not select the angled
variant by a name compiled into `main`.

*Also measured (tier B):* 65 of the 72 fighters with a c00 motion list on disk
**do** carry `attack_s4_hi` and `attack_s4_lw`, pointing at their own
`c03attacks4hi` / `c03attacks4lw` clips, with the same `game_script` split
(`game_attacks4` / `game_attacks4hi` / `game_attacks4lw` / `game_attacks4charge`)
this donor has. The 7 that lack the pair are `chrom diddy eflame elight
gamewatch miiswordsman younglink`.

A convention that 65 shipped fighters follow and 7 do not is a *content*
difference - those 7 characters' angled forward smash simply was never authored -
not an engine limitation. If the engine could not reach the angled kinds, the
entries would be dead weight in 65 fighters' own files, which they are not: Little
Mac's angled f-smash is a real, working, played move in the base game.

So the entries plus the clips plus the four scripts per variant are the whole
mechanism, and all three are things this port can supply: the motion entries come
from the pinned donor list, the clips from `retarget()` below, and the scripts
from `plugin/src/acmd/littlemac_attack_s4.rs`. No native hook is involved.

*Still unproven (tier D, and the reason this needs a console run):* whether the
engine asks for the angled kinds on the recipient at all. That is the one
question this build is staged to answer, and the answer is the hardware test -
not a claim made here.

# What this does, and does not, establish

* The donor's raw `attack_s4_s` and `attack_s4_hold` entries replace the
  recipient's, whole: donor kind, game script, flags, blend and cancel frame.
  Both name clips whose file names already exist in eflame, so no alias is
  consumed and the retargeted clip is written over G&W's own punch.
* The clips are retargeted onto the **built** recipient skeleton (Pyra's grafted
  onto G&W's), keeping only transform nodes that exist there, and take G&W's
  idle mesh-visibility group; Little Mac's Material group is dropped. Same filter
  as `build_chrom_jab.py` and `build_robot_dtilt.py`.
* Measured on the built c06 skeleton: 46 of Little Mac's 50 bones survive, and
  the 4 that do not (`H_ClavicleR/L`, `H_SholderR/L`) are helper bones, not part
  of the arm chain the hitboxes hang off. `armr` - the bone every hitbox in this
  move is parented to - is kept. Every kept bone has the **same parent** on the
  recipient as on the donor, so the retargeted pose is the donor's pose.
* What the retargeted punch *looks like* on G&W's body is unverified. Tier D until
  a console run: compilation, hashing and geometry say nothing about how it plays.
"""
from pathlib import Path
import hashlib
import struct
import zlib

import ssbh_data_py as s

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
EXPORT = ROOT / 'dumps/arc'
DONOR = ROOT / 'refs/littlemac_attack_s4/arc/fighter/littlemac/motion/body/c00'

# The four kinds this move installs. Kinds are the motion-list `kind` field, and
# the motion kind is NOT the status id: `attack_s4_s` is the motion kind whose
# game_script is `game_attacks4`.
#
# `c03attacks4hi` / `c03attacks4lw` are clip names eflame does **not** have, so
# they are new files and need a `config.json` declaration (see
# `new_clip_names()` and build.py's `declared_new_clips`). The other two names
# already exist in eflame c06/c07 and are overwrites.
KINDS = {
    'attack_s4_s': 'c03attacks4s.nuanmb',
    'attack_s4_hold': 'c03attacks4charge.nuanmb',
    'attack_s4_hi': 'c03attacks4hi.nuanmb',
    'attack_s4_lw': 'c03attacks4lw.nuanmb',
}

# Pinned donor bytes. These come from the 2026-09-30 live extraction; a change
# here means the donor dump changed and the readings below must be re-checked.
PINS = {
    'c03attacks4s.nuanmb': ('0dbe20c7d02ecad5229bed65b79c287ba31224ad6276bb4d51fdd735443ddf74', 30719),
    'c03attacks4charge.nuanmb': ('d6ad2b1d02b3c79d01ee8dfcfed9d081809a35a6c6f813120010a0db6dd42f9e', 29960),
    'c03attacks4hi.nuanmb': ('9f076d8f1a2e07d5ce986c66e430f1a0841c5489f758ca456f9ff4b5021e6b9b', 38304),
    'c03attacks4lw.nuanmb': ('4307545f0a2d75fac95f59e23b47a85b4f07e1bfb3b233484d8446a7d8ac53e5', 34066),
    'motion_list.bin': ('9141817eb56e91e874df049fca2119f917b91ad4ef5314fb02f98dc6364be19e', 45208),
}

# Read from the pinned motion_list.bin on 2026-09-30. `attack_s4_hold` has cancel
# 0 by construction (it is the held state). All four differ from the recipient:
# G&W's `attack_s4_hold` carries flags 0x80 where the donor's is 0x84, and G&W
# has no angled entry at all to compare against.
EXPECTED = {
    'attack_s4_s': {'cancel': 44, 'flags': 0x84},
    'attack_s4_hold': {'cancel': 0, 'flags': 0x84},
    'attack_s4_hi': {'cancel': 44, 'flags': 0x84},
    'attack_s4_lw': {'cancel': 44, 'flags': 0x84},
}


def new_clip_names(recipient_slot_dir):
    """Which of this move's clip names the recipient does not already have.

    Those are real new files, so `config.json` has to declare them: a motion entry
    that names a file the base game does not ship is only found if the loader is
    told the file exists. Same rule the Judge probe clip follows.
    """
    existing = {p.name for p in Path(recipient_slot_dir).glob('*.nuanmb')}
    return sorted(clip for clip in KINDS.values() if clip not in existing)


def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pinned(name):
    path = DONOR / name
    digest, size = PINS[name]
    if not path.is_file() or path.stat().st_size != size or sha(path) != digest:
        raise RuntimeError(f'{path} missing or not the pinned revision')
    return path


def get_entry(kind_name):
    """Little Mac's own raw motion entry for one kind, whole, from the pinned list.

    The donor's entry is used rather than the recipient's because it carries the
    donor's cancel frame and flags. The animation-name field is left exactly as
    the donor wrote it and asserted below to name the same file this build writes,
    so no alias round-trip is needed: the two neutral names are ones eflame and
    G&W both already call, and the two angled names are declared as new files.
    """
    if kind_name not in KINDS:
        raise KeyError(kind_name)
    clip = KINDS[kind_name]
    data = _pinned('motion_list.bin').read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError('littlemac motion_list.bin is not a motion list')
    offset = 24
    for _ in range(count):
        start = offset
        kind, game_script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        if kind == hash40(kind_name):
            cancel = struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None
            if anims != (hash40(clip),):
                raise RuntimeError(
                    f'Little Mac {kind_name} no longer names {clip}: {[hex(a) for a in anims]}')
            want = EXPECTED[kind_name]
            if cancel != want['cancel'] or flags != want['flags']:
                raise RuntimeError(
                    f'Little Mac {kind_name}: cancel {cancel} flags {flags:#x} '
                    f'differ from the pinned reading {want}')
            return {'raw': data[start:end], 'kind': kind, 'game_script': game_script,
                    'flags': flags, 'blend': blend, 'n_anims': n_anims, 'anims': anims,
                    'size': size, 'cancel': cancel}
        offset = end
    raise RuntimeError(f'Little Mac motion list has no kind {kind_name!r}')


def retarget(model_dir, out_path, gw_slot='c06'):
    """Retarget one donor clip onto the recipient's built skeleton and G&W's visibility.

    `model_dir` must be the *built* model (Pyra's skeleton grafted onto G&W's),
    not the raw G&W model: filtering against the built skeleton is what keeps the
    finger and elbow helper bones the Pyra graft contributed, which is the same
    reason `build_chrom_jab.py` uses it.
    """
    out_path = Path(out_path)
    clip_name = out_path.name
    if clip_name not in PINS:
        raise KeyError(f'{clip_name} is not a pinned donor clip')
    src = _pinned(clip_name)

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
    if not kept:
        raise RuntimeError(f'{clip_name}: no transform node survived the filter')

    # G&W's idle mesh-visibility states, replicated. Little Mac's own Visibility
    # group names 54 of his face/eye/glove meshes, none of which exist on the
    # recipient, and his 2 Material groups have no counterpart either.
    vis_nodes = [s.anim_data.NodeData(
        node.name, [s.anim_data.TrackData('Visibility', values=[node.tracks[0].values[0]])])
        for node in gw_vis.nodes]
    vis_group = s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)
    anim.groups = [transform, vis_group]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    anim.save(str(out_path))

    check = s.anim_data.read_anim(str(out_path))
    got = {n.name for n in next(g for g in check.groups
                                if g.group_type.name == 'Transform').nodes}
    if got != {n.name for n in kept}:
        raise RuntimeError(f'Transform node set changed after saving {out_path}')
    frames = len(kept[0].tracks[0].values) if kept[0].tracks else 0
    return {'bones_kept': len(kept), 'bones_dropped': sorted(dropped), 'case_only': case_only,
            'vis_nodes': len(vis_nodes), 'frames': frames, 'sha256': sha(out_path)}


def deploy_for_slot(slot, out_dir, gw_slot, model_dir):
    """Write the retargeted clips for one slot, over eflame's own files where it
    has them.

    `c03attacks4s` / `c03attacks4charge` already exist in eflame c06/c07, so
    those are overwrites of files the recipient's own motion list already reaches
    and no alias is consumed. `c03attacks4hi` / `c03attacks4lw` are new file
    names, reported per slot so build.py can declare them in `config.json`.
    """
    out_dir = Path(out_dir)
    clips, entries = {}, {}
    for kind_name, clip in KINDS.items():
        report = retarget(model_dir, out_dir / clip, gw_slot)
        if report['case_only']:
            raise RuntimeError(f'nodes matched only case-insensitively: {report["case_only"]}')
        clips[clip] = report
        entries[kind_name] = {'cancel': get_entry(kind_name)['cancel'],
                              'flags': get_entry(kind_name)['flags']}
    return {'clips': clips, 'motion_entries': entries,
            'new_clips': new_clip_names(out_dir),
            'dropped': sorted({b for c in clips.values() for b in c['bones_dropped']})}


def audit_recipient_bones(model_dir):
    """Which donor bones survive onto the built recipient, and do the parents agree?

    This is the check that makes the retarget trustworthy: a kept bone whose
    parent differs would silently re-parent the pose, and the hitboxes are
    parented to `armr`, so the arm chain specifically has to line up.
    """
    skel = s.skel_data.read_skel(str(Path(model_dir) / 'model.nusktb'))
    rcpt = {b.name: b for b in skel.bones}
    parent = {}
    for i, b in enumerate(skel.bones):
        p = b.parent_index
        parent[b.name] = skel.bones[p].name if isinstance(p, int) and 0 <= p < len(skel.bones) and p != i else None

    donor = s.skel_data.read_skel(
        str(ROOT / 'refs/littlemac_attack_s4/arc/fighter/littlemac/model/body/c00/model.nusktb'))
    dparent = {}
    for i, b in enumerate(donor.bones):
        p = b.parent_index
        dparent[b.name] = donor.bones[p].name if isinstance(p, int) and 0 <= p < len(donor.bones) and p != i else None

    kept = [b.name for b in donor.bones if b.name in rcpt]
    dropped = [b.name for b in donor.bones if b.name not in rcpt]
    mismatched = [(n, dparent[n], parent[n]) for n in kept if dparent[n] != parent[n]]
    arm_chain = ('ClavicleC', 'ClavicleR', 'ShoulderR', 'ArmR', 'HandR', 'HaveR')
    return {
        'recipient_bones': len(rcpt),
        'donor_bones': len(donor.bones),
        'kept': kept,
        'dropped': dropped,
        'parent_mismatches': mismatched,
        'arm_chain_ok': all(n in kept and dparent[n] == parent[n] for n in arm_chain),
        'armr_present': 'armr' in {n.lower() for n in rcpt},
    }


if __name__ == '__main__':
    import sys
    import tempfile
    for kind_name in KINDS:
        e = get_entry(kind_name)
        print(f"Little Mac {kind_name}: cancel frame {e['cancel']}, flags {e['flags']:#x}, "
              f"game_script {e['game_script']:#x}, anims {[hex(a) for a in e['anims']]}")
    model = ROOT / 'builds/pgwr/0.20.12/ultimate/mods/pyra_gamewatch_reskin' \
                  '/fighter/eflame/model/body/c06'
    if not model.is_dir():
        sys.exit(f'need a built c06 model first ({model}); entry check only passed')
    a = audit_recipient_bones(model)
    print(f"bones: {len(a['kept'])}/{a['donor_bones']} kept on a {a['recipient_bones']}-bone "
          f"recipient; dropped {a['dropped']}")
    print(f"parent mismatches: {a['parent_mismatches'] or 'none'}; "
          f"arm chain ok: {a['arm_chain_ok']}; armr present: {a['armr_present']}")
    assert a['arm_chain_ok'] and a['armr_present'], 'arm chain does not line up'
    with tempfile.TemporaryDirectory() as tmp:
        rep = deploy_for_slot('c06', tmp, 'c06', model)
    for clip, c in rep['clips'].items():
        print(f"retarget {clip}: {c['bones_kept']} bones, {c['vis_nodes']} vis nodes, "
              f"{c['frames']} frames, sha256 {c['sha256']}")
    print('build_littlemac_fsmash OK')
