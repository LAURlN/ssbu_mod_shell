"""Inventory the pinned Snake up-tilt (AttackHi3) donor material for Pyra c06/c07 (v1.0.0).

Usage:
    toolchains/py312/python.exe tools/audit_snake_hi3_donor.py
    toolchains/py312/python.exe tools/audit_snake_hi3_donor.py --smoke     # pins only, no recipient tree

What it answers
---------------
* Snake's own raw `attack_hi3` motion-list entry: cancel frame, flags, blend, game_script,
  and the animation name it points at (`c02attackhi3.nuanmb`).
* Whether the pinned clip belongs to the pinned donor skeleton (every Transform node
  should be a Snake bone; a mismatch means the two files are from different revisions).
* How many of the clip's Transform nodes exist on the **built** recipient skeleton
  (Pyra's skeleton grafted onto G&W's), i.e. how many nodes a retarget keeps or drops.
  This is the same test `src/pgwr/tools/build_robot_dtilt.py::retarget` applies.
* Whether every sound name the donor ACMD uses resolves in material already pinned
  (`se_snake_c00` bank in refs/snake_grenade, `snake.sqb` in refs/snake_grenade/sequence).

What it does NOT establish: that the ported move looks right on G&W's body. Node
coverage is an offline measurement (tier B); the visual result is tier D until a
console run. Nothing here is written outside `refs/snake_attack_hi3/inventory.json`.

Inputs: refs/snake_attack_hi3/ (live extraction, provenance in SOURCE.json),
dumps/scripts/.../lua2cpp_snake/snake/AttackHi3.txt, refs/snake_grenade/,
builds/pgwr/<version>/ultimate/mods/pyra_gamewatch_reskin/fighter/eflame/model/body/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib

import ssbh_data_py as s

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import merge_hero_neutral_b_sound as codec  # noqa: E402  the sound bank codec the merges use
REF = ROOT / 'refs/snake_attack_hi3'
DONOR_MOTION = REF / 'arc/fighter/snake/motion/body/c00'
KIND = 'attack_hi3'
CLIP = 'c02attackhi3.nuanmb'
ACMD = ROOT / 'dumps/scripts/SSBU-Dumped-Scripts-main/smashline/lua2cpp_snake/snake/AttackHi3.txt'
GW_ACMD = ROOT / 'dumps/scripts/SSBU-Dumped-Scripts-main/smashline/lua2cpp_gamewatch/gamewatch/AttackHi3.txt'
SE_STEM = ROOT / 'refs/snake_grenade/arc/sound/bank/fighter/se_snake_c00'
SQB = ROOT / 'refs/snake_grenade/sequence/arc/sound/sequence/fighter/snake.sqb'
RECIPIENTS = [
    ROOT / 'builds/pgwr/0.20.15/ultimate/mods/pyra_gamewatch_reskin/fighter/eflame/model/body/c06',
    ROOT / 'builds/pgwr/0.20.15/ultimate/mods/pyra_gamewatch_reskin/fighter/eflame/model/body/c07',
]


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def motion_entry(path: Path, kind: int) -> dict:
    """The raw motion-list entry for `kind`, read the way the game stores it."""
    data = path.read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError(f'{path} is not a motion list (magic {magic:#x})')
    offset = 24
    for _ in range(count):
        start = offset
        m_kind, game_script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        if m_kind == kind:
            cancel = struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None
            return {'kind': m_kind, 'game_script': game_script, 'flags': flags, 'blend': blend,
                    'n_anims': n_anims, 'anims': anims, 'size': size, 'cancel': cancel,
                    'raw_sha256': hashlib.sha256(data[start:end]).hexdigest()}
        offset = end
    raise RuntimeError(f'{path} has no motion kind {kind:#x}')


def clip_groups(path: Path) -> dict:
    with tempfile.NamedTemporaryFile(suffix='.nuanmb', delete=False) as fh:
        fh.write(path.read_bytes())
        tmp = fh.name
    try:
        anim = s.anim_data.read_anim(tmp)
        out = {}
        for group in anim.groups:
            out[group.group_type.name] = [n.name for n in group.nodes]
        return out
    finally:
        Path(tmp).unlink(missing_ok=True)


def acmd_bones(path: Path) -> list[str]:
    """Bone names an ACMD hangs its hitboxes on, in order."""
    import re
    text = path.read_text(encoding='utf-8', errors='replace')
    return list(dict.fromkeys(re.findall(r'ATTACK\(agent, \d+, \d+, Hash40::new\("([^"]+)"\)', text)))


def hitbox_bones() -> list[str]:
    return acmd_bones(ACMD)


def sound_names() -> list[str]:
    text = ACMD.read_text(encoding='utf-8', errors='replace')
    found, buf = [], ''
    for ch in text:
        if ch.isalnum() or ch == '_':
            buf += ch
        else:
            if buf.startswith(('se_', 'seq_', 'vc_')) and buf not in found:
                found.append(buf)
            buf = ''
    if buf.startswith(('se_', 'seq_', 'vc_')) and buf not in found:
        found.append(buf)
    return found


def sound_resolution(wanted: list[str]) -> dict:
    """Which of the ACMD's sound names resolve in material already pinned.

    Tone names are stored as CRC32 of the lowercase name, so this reads them the
    way the game does (`codec.labels_read`), not by grepping the label file.
    """
    out: dict = {'named_by_acmd': wanted, 'resolved': [], 'unresolved': wanted, 'where': {}}
    if not SE_STEM.with_suffix('.nus3audio').is_file():
        out['note'] = f'{SE_STEM} not pinned; nothing checked'
        return out
    donor = codec.audio_read(SE_STEM.with_suffix('.nus3audio').read_bytes())
    labels = dict(codec.labels_read(SE_STEM.with_suffix('.tonelabel').read_bytes(), [n for n, _ in donor]))
    available = {n.lower() for n, _ in donor}
    sqb_records = codec.sqb_read(SQB.read_bytes()) if SQB.is_file() else []
    sqb_names = {n for n in wanted if any(
        int.from_bytes(r[:8], 'little') == hash40(n) for r in sqb_records)}
    for name in wanted:
        if name.lower() in available:
            out['resolved'].append(name)
            out['where'][name] = f'se_snake_c00 tone ({len(labels)} labels in the pinned bank)'
        elif name in sqb_names:
            out['resolved'].append(name)
            out['where'][name] = 'snake.sqb sequence record'
    out['unresolved'] = [n for n in wanted if n not in out['resolved']]
    out['already_in_built_banks'] = already_merged(wanted)
    return out


def already_merged(wanted: list[str], build: str = '0.20.15') -> dict:
    """Are these donor names already in the recipient's own banks in a built tree?

    A tone only becomes playable on the target fighter once it is appended to that
    fighter's bank (`tools/merge_*_sound.py`); the Snake neutral-B merge added nine
    tones, so this says whether Snake's up-tilt ones are among them or still owed.
    """
    tree = ROOT / f'builds/pgwr/{build}/ultimate/mods/pyra_gamewatch_reskin'
    out: dict = {'build': build}
    if not tree.is_dir():
        out['note'] = f'{tree} not present'
        return out
    for slot in ('c06', 'c07'):
        bank = tree / f'sound/bank/fighter/se_eflame_{slot}.tonelabel'
        if not bank.is_file():
            out[slot] = 'no eflame bank in this build'
            continue
        # label file: u32 version, u32 count, then (crc32, name-length/index) pairs
        raw = bank.read_bytes()
        count = struct.unpack_from('<I', raw, 4)[0]
        crcs = {crc for crc, _ in struct.iter_unpack('<II', raw[8:8 + count * 8])}
        out[slot] = {n: (zlib.crc32(n.lower().encode()) in crcs) for n in wanted if n.startswith('se_')}
    sqb = tree / 'sound/sequence/fighter/eflame.sqb'
    if sqb.is_file():
        records = codec.sqb_read(sqb.read_bytes())
        out['eflame.sqb'] = {n: any(int.from_bytes(r[:8], 'little') == hash40(n) for r in records)
                             for n in wanted if n.startswith('seq_')}
    else:
        out['eflame.sqb'] = 'not in this build'
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--smoke', action='store_true',
                    help='pins and entry only; do not read a built recipient tree')
    args = ap.parse_args()

    clip = DONOR_MOTION / CLIP
    mlist = DONOR_MOTION / 'motion_list.bin'
    skel = REF / 'arc/fighter/snake/model/body/c00/model.nusktb'
    for p in (clip, mlist, skel):
        if not p.is_file():
            raise SystemExit(f'missing pinned donor file {p}; run tools/fetch_arc_files.py --set snake_attack_hi3')

    report: dict = {'date': '2026-10-01', 'move': 'Snake up tilt (AttackHi3) on Pyra c06/c07 (G&W)',
                    'tier': 'B (offline measurement; the console result is still D)',
                    'pins': {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in (clip, mlist, skel)}}

    entry = motion_entry(mlist, hash40(KIND))
    if entry['anims'] != (hash40(CLIP),):
        raise SystemExit(f"Snake {KIND} no longer names {CLIP}: {[hex(a) for a in entry['anims']]}")
    report['motion_entry'] = {**entry, 'kind': f'{entry["kind"]:#x}',
                              'anims': [f'{a:#x}' for a in entry['anims']],
                              'game_script': f'{entry["game_script"]:#x}'}

    groups = clip_groups(clip)
    report['clip_groups'] = {k: len(v) for k, v in groups.items()}
    report['clip_transform_nodes'] = len(groups.get('Transform', []))

    skel_path = REF / 'arc/fighter/snake/model/body/c00/model.nusktb'
    skel_obj = None
    with tempfile.NamedTemporaryFile(suffix='.nusktb', delete=False) as fh:
        fh.write(skel_path.read_bytes())
        tmp = fh.name
    try:
        skel_obj = s.skel_data.read_skel(tmp)
    finally:
        Path(tmp).unlink(missing_ok=True)
    donor_bone_names = {b.name for b in skel_obj.bones}
    orphan = [n for n in groups.get('Transform', []) if n not in donor_bone_names]
    report['donor_skeleton'] = {'bones': len(skel_obj.bones), 'clip_nodes_absent_from_skeleton': orphan}
    gw_bones = acmd_bones(GW_ACMD) if GW_ACMD.is_file() else []

    if not args.smoke:
        for recipient in RECIPIENTS:
            slot = recipient.name
            model = recipient / 'model.nusktb'
            if not model.is_file():
                report.setdefault('recipient', {})[slot] = 'not built here'
                continue
            with tempfile.NamedTemporaryFile(suffix='.nusktb', delete=False) as fh:
                fh.write(model.read_bytes())
                tmp = fh.name
            try:
                built = s.skel_data.read_skel(tmp)
            finally:
                Path(tmp).unlink(missing_ok=True)
            exact = {b.name for b in built.bones}
            bones = hitbox_bones()
            report.setdefault('hitbox_bones', {})[slot] = {
                'named_by_acmd': bones,
                'exact_on_recipient': [n for n in bones if n in exact],
                # eflame has `LegL`/`KneeL` where Snake's script writes `legl`/`kneel`, and
                # neither has a `top` bone. That is not a new problem: G&W's own up tilt,
                # which is what runs on c06/c07 today, writes `top` too. Compare rather
                # than "fix", or the port would diverge from the working convention.
                'not_named_on_recipient': [n for n in bones if n not in exact],
                'gamewatch_uptilt_bones': gw_bones}
            folded = {b.name.lower(): b.name for b in built.bones}
            kept = [n for n in groups.get('Transform', []) if n in exact]
            case_only = [n for n in groups.get('Transform', []) if n not in exact and n.lower() in folded]
            dropped = [n for n in groups.get('Transform', []) if n not in exact and n.lower() not in folded]
            report.setdefault('recipient', {})[slot] = {
                'bones': len(built.bones), 'transform_nodes': len(groups.get('Transform', [])),
                'kept': len(kept), 'case_only': case_only, 'dropped': dropped}

    report['sounds'] = sound_resolution(sound_names())

    out = REF / ('inventory_smoke.json' if args.smoke else 'inventory.json')
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    e = report['motion_entry']
    print(f"Snake {KIND}: cancel {e['cancel']}, flags {e['flags']:#x}, blend {e['blend']}, "
          f"game_script {e['game_script']}, anims {e['anims']}")
    print(f"clip groups {report['clip_groups']}; donor skeleton {report['donor_skeleton']['bones']} bones, "
          f"orphan transform nodes {report['donor_skeleton']['clip_nodes_absent_from_skeleton']}")
    for slot, rec in report.get('hitbox_bones', {}).items():
        print(f"  hitbox bones {slot}: named {rec['named_by_acmd']}; exact on recipient "
              f"{rec['exact_on_recipient']}, not named {rec['not_named_on_recipient']} "
              f"(G&W's own up tilt names {rec['gamewatch_uptilt_bones']})")
    for slot, rec in report.get('recipient', {}).items():
        if isinstance(rec, str):
            print(f"  recipient {slot}: {rec}")
        else:
            print(f"  recipient {slot}: {rec['kept']}/{rec['transform_nodes']} transform nodes kept, "
                  f"case-only {len(rec['case_only'])}, dropped {rec['dropped']}")
    print(f"sounds: {len(report['sounds']['resolved'])}/{len(report['sounds']['named_by_acmd'])} resolved, "
          f"unresolved {report['sounds']['unresolved']}")
    print(f'report: {out.relative_to(ROOT)}')
    return 1 if (report['sounds']['unresolved'] or orphan
                 or any(isinstance(v, dict) and v.get('case_only') for v in report.get('recipient', {}).values())
                 ) else 0


if __name__ == '__main__':
    raise SystemExit(main())