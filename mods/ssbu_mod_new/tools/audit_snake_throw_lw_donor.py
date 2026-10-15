"""Inventory the pinned Snake down-throw donor material for Pyra c06/c07 (v1.0.0).

Usage:
    python tools/audit_snake_throw_lw_donor.py
    python tools/audit_snake_throw_lw_donor.py --smoke   # pins + entries, no recipient tree

What it answers
---------------
* Which move ``throw_lw`` actually is, measured rather than assumed: Snake's own
  motion list gives the kind/script/clip/cancel for ``throw_lw`` *and* for
  ``attack_lw4``, so the reader can see the down throw and the down smash side by
  side and that the port touched only one of them.
* Every sound name Snake's ``sound_throwlw`` names, whether it resolves in the
  pinned donor bank, and the **tone closure** it drags in (the kind-1 sequence
  tone and its two children) with their kind-1 child indices in the donor.
* How many of the clip's Transform nodes exist on the **built** recipient
  skeleton, i.e. how many a retarget keeps or drops.
* Which of the bones the donor's scripts name exist on the recipient.

What it does NOT establish: that the ported move looks right or behaves right on
G&W's body. That is tier D until a console run. Nothing here is written outside
``refs/snake_throw_lw/inventory.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import ssbh_data_py as s

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import merge_snake_throw_lw_sound as sound  # noqa: E402
import build_snake_throw_lw as builder  # noqa: E402

REF = ROOT / 'refs/snake_throw_lw'
DONOR_MOTION = REF / 'arc/fighter/snake/motion/body/c00'
ACMD = REF / 'donor_acmd/snake__ThrowLw.txt'
CONTROL = REF / 'donor_acmd/snake__AttackLw4.txt'
DONOR_SKEL = REF / 'arc/fighter/snake/model/body/c00/model.nusktb'
DONOR_AI = REF / 'arc/fighter/snake/ai/param/attack_data_param.prc'
RECIPIENT = ROOT / ('builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
                    '/fighter/eflame/model/body/c06')


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def entries_of(path: Path) -> dict:
    data = Path(path).read_bytes()
    _, _, entries = builder.parse_entries(data)
    return {e['kind']: e for e in entries}


def clip_groups(path: Path) -> dict:
    with tempfile.NamedTemporaryFile(suffix='.nuanmb', delete=False) as fh:
        fh.write(Path(path).read_bytes())
        tmp = fh.name
    try:
        anim = s.anim_data.read_anim(tmp)
        return {g.group_type.name: [n.name for n in g.nodes] for g in anim.groups}
    finally:
        Path(tmp).unlink(missing_ok=True)


def acmd_facts(path: Path) -> dict:
    text = path.read_text(encoding='utf-8', errors='replace')
    out = {
        'defines': sorted(set(__import__('re').findall(r'fn (\w+)\(', text))),
        'attack_abs': text.count('macros::ATTACK_ABS('),
        'attack': text.count('macros::ATTACK(agent'),
        'effect_calls': text.count('macros::EFFECT(') + text.count('macros::FOOT_EFFECT(')
                         + text.count('macros::LANDING_EFFECT(')
                         + text.count('macros::EFFECT_FOLLOW('),
        'play_se': text.count('macros::PLAY_SE(agent'),
        'play_sequence': text.count('macros::PLAY_SEQUENCE(agent'),
        'atk_hit_abs': text.count('macros::ATK_HIT_ABS('),
        'clear_all': text.count('AttackModule::clear_all('),
        'collision_attrs': sorted(set(__import__('re').findall(
            r'Hash40::new\("(collision_attr_[a-z_]+)"\)', text))),
    }
    return out


def prc_load(path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'pgwr_prcread', str(REF / 'tools/prcread.py'))
    module = importlib.util.module_from_spec(spec)
    os_cwd = Path.cwd()
    try:
        import os
        os.chdir(ROOT)
        spec.loader.exec_module(module)
    finally:
        import os
        os.chdir(os_cwd)
    return module.load(str(path))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--smoke', action='store_true',
                    help='pins and entry only; do not read a built recipient tree')
    args = ap.parse_args()

    mlist = DONOR_MOTION / 'motion_list.bin'
    clip = DONOR_MOTION / builder.CLIP
    for p in (mlist, clip, DONOR_SKEL, ACMD, CONTROL):
        if not p.is_file():
            raise SystemExit(f'missing pinned donor file {p}')

    donor = entries_of(mlist)
    kinds = {}
    for name in ('throw_lw', 'attack_lw4', 'attack_hi4', 'throw_f', 'throw_b', 'throw_hi'):
        e = donor.get(builder.hash40(name))
        if e is None:
            continue
        script = next((f'{p}_{n}' for p in ('game', 'effect', 'sound', 'expression')
                       for n in ('throwlw', 'throwf', 'throwb', 'throwhi',
                                 'attacklw4', 'attackhi4')
                       if builder.hash40(f'{p}_{n}') == e['game_script']), None)
        kinds[name] = {
            'kind_hash': hex(e['kind']), 'game_script': hex(e['game_script']),
            'game_script_name': script, 'flags': hex(e['flags']), 'blend': e['blend'],
            'cancel': e['cancel'], 'n_anims': e['n_anims'],
            'anims': [hex(a) for a in e['anims']],
            'anims_resolved': [next((n for n in (builder.CLIP, 'c04attacklw4.nuanmb',
                                                'e01throwf.nuanmb', 'e01throwb.nuanmb',
                                                'e01throwhi.nuanmb', 'c04attackhi4.nuanmb')
                                     if builder.hash40(n) == a), hex(a)) for a in e['anims']],
        }

    report: dict = {
        'set': 'snake_throw_lw', 'date': '2026-10-02', 'evidence_tier': 'B',
        'hardware_validated': False,
        'identity': {
            'down_throw_kind': 'throw_lw',
            'down_throw_game_script': 'game_throwlw',
            'down_throw_clip': builder.CLIP,
            'down_smash_kind': 'attack_lw4',
            'down_smash_game_script': 'game_attacklw4',
            'down_smash_clip': 'c04attacklw4.nuanmb',
            'note': ('throw_lw and attack_lw4 differ by one word and both exist in '
                     'Snake. attack_data_param.prc lists an attack_lw4 AI record with '
                     'cancel_frame 56 and no throw_lw record, and game_attacklw4 '
                     'opens with START_SMASH_HOLD / smash_start_02 / rbkind_smashhold1 '
                     '/ PHYSICS_START_CHARGE with an AttackLw4Charge follow-up: those '
                     'are down-smash marks.'),
        },
        'motion_entries': kinds,
        'pins': {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                 for p in (mlist, clip, DONOR_SKEL, ACMD, CONTROL, DONOR_AI)},
    }

    # Sounds: what the donor ACMD names, and the closure it drags in.
    donor_stem = sound.SE_DONOR
    dnames = [n for n, _ in sound.codec.audio_read(
        donor_stem.with_suffix('.nus3audio').read_bytes())]
    dtones = sound.codec.tones_read(dict(sound.codec.bank_read(
        donor_stem.with_suffix('.nus3bank').read_bytes()))[b'TONE'])
    idx = {n.lower(): i for i, n in enumerate(dnames)}
    named = __import__('re').findall(
        r'macros::PLAY_SE\(agent, Hash40::new\("([^"]+)"\)\)',
        ACMD.read_text(encoding='utf-8'))
    sequences = __import__('re').findall(
        r'macros::PLAY_SEQUENCE\(agent, Hash40::new\("([^"]+)"\)\)',
        ACMD.read_text(encoding='utf-8'))
    assert not sequences, f'the donor plays a sequence ({sequences}); eflame.sqb ' \
                          f'would need a matching record, which this move does not do'
    closure = sound.closure(dnames, dtones, set(named))
    seq_tones = []
    for i in closure:
        _, _, start = sound.tone_record(dtones[i])
        kind = sound.codec.u32(dtones[i], start)
        entry = {'name': dnames[i], 'kind': kind, 'len': len(dtones[i])}
        if kind == 1:
            entry['children'] = [{'offset': at, 'index': child, 'name': dnames[child]}
                                 for at, child in sound.kind1_links(dtones[i], dnames, start)]
        seq_tones.append(entry)
    report['sounds'] = {
        'se_bank': str(donor_stem.relative_to(ROOT)),
        'named_by_acmd': named,
        'all_named_resolve': all(n.lower() in idx for n in named),
        'sequences_played': sequences,
        'closure_size': len(closure),
        'closure': [dnames[i] for i in closure],
        'tone_kinds': seq_tones,
        'already_in_baseline_banks': {
            slot: [n for n in named
                   if n.lower() in [x.lower() for x, _ in sound.codec.audio_read(
                       (ROOT / f'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
                              f'/sound/bank/fighter/se_eflame_{slot}.nus3audio'
                       ).read_bytes())]]
            for slot in ('c06', 'c07')
        } if not args.smoke else 'not read (--smoke)',
    }

    # AI params, for the identity argument.
    try:
        ai = prc_load(DONOR_AI)
        rows = [r for r in ai['attack_data']
                if r.get('motion_kind', [None, None])[1] in ('attack_lw4', 'throw_lw')]
        report['ai_attack_data'] = [
            {'motion_kind': r['motion_kind'][1], 'cancel_frame': r['cancel_frame'],
             'start_frame': r['start_frame'], 'end_frame': r['end_frame']} for r in rows]
        report['ai_has_throw_lw_record'] = any(
            r['motion_kind'][1] == 'throw_lw' for r in ai['attack_data'])
    except Exception as exc:  # the PRC reader is a scratch helper
        report['ai_attack_data'] = f'not decoded: {exc}'

    if not args.smoke:
        groups = clip_groups(clip)
        skel = s.skel_data.read_skel(str(RECIPIENT / 'model.nusktb'))
        names = {b.name for b in skel.bones}
        transform = groups.get('Transform', [])
        dropped = [n for n in transform if n not in names]
        report['clip'] = {
            'groups': {k: len(v) for k, v in groups.items()},
            'transform_nodes': len(transform),
            'bones_kept': len(transform) - len(dropped),
            'bones_dropped': dropped,
            'case_only_matches': [],
        }
        acmd_bones = sorted(set(__import__('re').findall(
            r'Hash40::new\("(top|throw|kneel|legl|hip|handl|handr|footl|footr)"\)',
            ACMD.read_text(encoding='utf-8'))))
        report['script_bones_on_recipient'] = {b: (b in names) for b in acmd_bones}
        report['script_bones_note'] = (
            "'throw' is named by ATK_HIT_ABS and is absent here; it is one of the "
            "engine's built-in fighter anchors (like 'top'), not a skeleton bone, so "
            "it does not depend on the grafted skeleton. G&W's own down throw names "
            "the same anchor and is what runs on c06/c07 today.")

    negative_control = False
    try:
        # The identity measurement must be able to fail: assert that throw_lw's
        # game_script is NOT the down-smash script. If the two ever merged in a
        # future game revision, this is what notices.
        e = donor[builder.hash40('throw_lw')]
        negative_control = e['game_script'] != builder.hash40('game_attacklw4')
        assert negative_control, 'throw_lw and attack_lw4 name the same script'
    except AssertionError:
        raise

    report['negative_control_identity_distinct'] = negative_control
    report['not_established'] = ('Anything about how the move looks, how long it '
                                 'takes, whether the victim is released or lies '
                                 'prone and gets up, or whether it hits. Tier D '
                                 'until a console run.')
    (REF / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"down throw  = throw_lw -> game_throwlw -> {builder.CLIP}, "
          f"cancel {kinds['throw_lw']['cancel']}, flags {kinds['throw_lw']['flags']}")
    print(f"down smash  = attack_lw4 -> game_attacklw4 -> "
          f"{kinds['attack_lw4']['anims_resolved'][0]}, cancel {kinds['attack_lw4']['cancel']}")
    print(f"sounds: named {named}, closure {[dnames[i] for i in closure]}")
    print(f"wrote {REF / 'inventory.json'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())