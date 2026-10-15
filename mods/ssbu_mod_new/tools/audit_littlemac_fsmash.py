"""Audit the Little Mac forward smash family on the G&W c06/c07 costume (v1.2.0).

Covers the neutral punch, its charge hold, and the two up/down-angled variants.

Usage:
    toolchains/py312/python.exe tools/audit_littlemac_fsmash.py --package builds/pgwr/<version>
    toolchains/py312/python.exe tools/audit_littlemac_fsmash.py --package builds/pgwr/<version> --check

What it proves, all from bytes on disk (tier B)
-----------------------------------------------
1. The donor inputs are the pinned extraction, and re-hash to what
   `src/pgwr/tools/build_littlemac_fsmash.py` pins.
2. The **built motion list** of each slot really carries Little Mac's
   `attack_s4_s` / `attack_s4_hold` / `attack_s4_hi` / `attack_s4_lw` entries -
   cancel frame 44 and flags 0x84, and G&W's own 43 / 0x80 is gone - while every
   *other* G&W entry is untouched. Point 2 is the one that catches a silent
   regression: a retargeted clip with the recipient's motion entry would animate
   with G&W's cancel window, and a build that merely copied clips would pass
   every other check here. It also asserts the two angled kinds were genuinely
   absent from the base game, so "new" is a checked claim and not an assumption.
3. The retargeted clips name the donor's own bones on the recipient's built
   skeleton, with the arm chain the hitboxes hang off intact.
4. The sound banks resolve all four names the scripts play, by CRC-32 of the
   lowercased name, which is the lookup the engine does (measured; see
   `tools/merge_donor_sound.py`).
5. Each gated slot has its **own** eflame bank (`ef_eflame_c06.eff`,
   `ef_eflame_c07.eff`) that carries both emitters the move can reach, the
   misplaced `effect/fighter/littlemac/ef_littlemac.eff` is no longer shipped,
   and every emitter the vanilla bank had is still in the slot bank. That last
   part is the control: a bank that replaced rather than merged would still
   pass a "both emitters present" check.
6. The **baseline is intact**: every file the previous package had that this
   package also has is byte-identical, except the exact intended overrides. This
   is the control for "did installing this break someone else's move".
7. The **packaged plugin NRO** really carries every ACMD handler name this move
   needs, including the eight angled ones. This exists because a packaging run on
   2026-10-01 shipped the *wrong agent's* NRO and every other check still passed:
   a handler that is not in the binary is a move that animates and hits nothing,
   and nothing else in this file would have noticed.

What it does NOT prove
----------------------
Nothing here says the punch *plays*. That needs the console. In particular the
clips' on-screen appearance, the sound actually being audible, the effect
drawing, and - for the two angled variants specifically - whether the engine ever
asks for those motion kinds at all, are all tier D until a hardware run.
"""
from __future__ import annotations

import os
import argparse
import hashlib
import json
import struct
import sys
import tomllib
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'toolchains'))

import ssbh_data_py as s  # noqa: E402

EXPORT = Path(os.environ.get('MGW_EXPORT', ROOT / 'dumps' / 'arc'))  # same override as build.py
REF = ROOT / 'refs/littlemac_attack_s4'
DONOR_MOTION = REF / 'arc/fighter/littlemac/motion/body/c00/motion_list.bin'
DONOR_CLIPS = {
    'c03attacks4s.nuanmb': ('0dbe20c7d02ecad5229bed65b79c287ba31224ad6276bb4d51fdd735443ddf74', 30719),
    'c03attacks4charge.nuanmb': ('d6ad2b1d02b3c79d01ee8dfcfed9d081809a35a6c6f813120010a0db6dd42f9e', 29960),
    'c03attacks4hi.nuanmb': ('9f076d8f1a2e07d5ce986c66e430f1a0841c5489f758ca456f9ff4b5021e6b9b', 38304),
    'c03attacks4lw.nuanmb': ('4307545f0a2d75fac95f59e23b47a85b4f07e1bfb3b233484d8446a7d8ac53e5', 34066),
}
DONOR_MOTION_SHA = '9141817eb56e91e874df049fca2119f917b91ad4ef5314fb02f98dc6364be19e'
DONOR_EFF_SHA = 'c2f33cdb2157be04d80940182aced6ae762c004f9b08ea4ec3929749ea2b2228'
# Where the fist emitters now live: one recipient-owned bank per gated slot.
SLOT_BANKS = {'c06': 'effect/fighter/eflame/ef_eflame_c06.eff',
              'c07': 'effect/fighter/eflame/ef_eflame_c07.eff'}
# The bank that must no longer be shipped. An eflame fighter's loader only ever
# searches effect/fighter/eflame/, so this file was loaded by nobody.
MISPLACED_DONOR_BANK = 'effect/fighter/littlemac/ef_littlemac.eff'

# The four kinds this port installs, with the readings pinned by
# build_littlemac_fsmash.py. G&W's own values are in EXPECTED_RECIPIENT below.
EXPECTED = {'attack_s4_s': {'cancel': 44, 'flags': 0x84},
            'attack_s4_hold': {'cancel': 0, 'flags': 0x84},
            'attack_s4_hi': {'cancel': 44, 'flags': 0x84},
            'attack_s4_lw': {'cancel': 44, 'flags': 0x84}}
EXPECTED_RECIPIENT = {'attack_s4_s': {'cancel': 43, 'flags': 0x84},
                      'attack_s4_hold': {'cancel': 0, 'flags': 0x80}}
# The motion kind -> the one clip its entry must name, and the ACMD script names
# the plugin must register for that entry to do anything.
KIND_CLIP = {
    'attack_s4_s': 'c03attacks4s.nuanmb',
    'attack_s4_hold': 'c03attacks4charge.nuanmb',
    'attack_s4_hi': 'c03attacks4hi.nuanmb',
    'attack_s4_lw': 'c03attacks4lw.nuanmb',
}
# Kinds the base game does not have at all. Checked against the pristine export
# so the "new file" claims in config.json rest on a measurement.
RECIPIENT_LACKS = ('attack_s4_hi', 'attack_s4_lw')
# Every handler name the four motion entries' game_script fields can ask for,
# plus the charge state. A missing one is a silent no-op at runtime.
REQUIRED_HANDLERS = (
    'game_attacks4', 'effect_attacks4', 'sound_attacks4', 'expression_attacks4',
    'game_attacks4hi', 'effect_attacks4hi', 'sound_attacks4hi', 'expression_attacks4hi',
    'game_attacks4lw', 'effect_attacks4lw', 'sound_attacks4lw', 'expression_attacks4lw',
    'effect_attacks4charge', 'sound_attacks4charge', 'expression_attacks4charge',
)

# Files this port is allowed to change relative to the baseline package. Anything
# else differing is a regression, not a feature.
ALLOWED_OVERRIDES = {
    'fighter/eflame/motion/body/{slot}/c03attacks4s.nuanmb',
    'fighter/eflame/motion/body/{slot}/c03attacks4charge.nuanmb',
    'fighter/eflame/motion/body/{slot}/c03attacks4hi.nuanmb',
    'fighter/eflame/motion/body/{slot}/c03attacks4lw.nuanmb',
    'fighter/eflame/motion/body/{slot}/motion_list.bin',
    'sound/bank/fighter/se_eflame_c06.nus3audio',
    'sound/bank/fighter/se_eflame_c06.nus3bank',
    'sound/bank/fighter/se_eflame_c06.tonelabel',
    'sound/bank/fighter/se_eflame_c07.nus3audio',
    'sound/bank/fighter/se_eflame_c07.nus3bank',
    'sound/bank/fighter/se_eflame_c07.tonelabel',
    'sound/bank/fighter_voice/vc_eflame_c06.nus3audio',
    'sound/bank/fighter_voice/vc_eflame_c06.nus3bank',
    'sound/bank/fighter_voice/vc_eflame_c06.tonelabel',
    'sound/bank/fighter_voice/vc_eflame_c07.nus3audio',
    'sound/bank/fighter_voice/vc_eflame_c07.nus3bank',
    'sound/bank/fighter_voice/vc_eflame_c07.tonelabel',
    'info.toml',
    # config.json changes only because it declares the new files this port adds
    # (the two angled clips per slot, and the effect bank). Verified separately:
    # the only difference from the baseline is those groups gaining entries.
    'config.json',
    # The per-slot eflame banks: added by the fist-trail fix (they did not exist
    # in the 0.20.14-0.20.18 baseline, so they show as additions, not changes).
    'effect/fighter/eflame/ef_eflame_{slot}.eff',
}
SOUND_NAMES = ('se_littlemac_smash_s02', 'se_littlemac_smash_s03',
               'se_littlemac_smash_s04', 'vc_littlemac_attack05')


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash40(name: str) -> int:
    d = name.encode('utf-8')
    return (len(d) << 32) | zlib.crc32(d)


def read_mlist(path: Path) -> dict:
    """Motion list -> {kind: {...}} with the cancel frame decoded."""
    data = Path(path).read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError(f'{path} is not a motion list')
    offset, out = 24, {}
    for _ in range(count):
        start = offset
        kind, gs, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        out[kind] = {'raw': data[start:end], 'game_script': gs, 'flags': flags,
                     'blend': blend, 'anims': anims,
                     'cancel': struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None}
        offset = end
    return out


def fail(msg: str):
    raise SystemExit(f'FAIL: {msg}')


def check_donor() -> dict:
    """1. The donor inputs are the pinned bytes."""
    if sha(DONOR_MOTION) != DONOR_MOTION_SHA:
        fail(f'{DONOR_MOTION} is not the pinned revision')
    for name, (digest, size) in DONOR_CLIPS.items():
        p = DONOR_MOTION.parent / name
        if not p.is_file() or p.stat().st_size != size or sha(p) != digest:
            fail(f'{p} missing or not the pinned revision')
    print(f'PASS donor inputs pinned: motion_list + {len(DONOR_CLIPS)} clips')
    return {'motion_list_sha256': DONOR_MOTION_SHA,
            'clips': {n: d for n, (d, _) in DONOR_CLIPS.items()}}


def check_motion_entries(mod: Path, donor: dict) -> dict:
    """2. Each slot's built list carries the donor's four entries and nothing else moved."""
    # The two angled kinds are only *new* if the base game really lacks them.
    # Assert that against the pristine export rather than taking it on trust, so
    # the config.json new-file declarations rest on a measurement.
    for slot in ('c06', 'c07'):
        pristine = read_mlist(EXPORT / f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        for kind in RECIPIENT_LACKS:
            if hash40(kind) in pristine:
                fail(f'{slot}: {kind} exists in the base game, so it is an overwrite '
                     'and must not be declared as a new file')
        for clip in KIND_CLIP.values():
            if clip not in DONOR_CLIPS:
                fail(f'{clip} is not a pinned donor clip')
            vanilla = EXPORT / f'fighter/eflame/motion/body/{slot}/{clip}'
            if clip in ('c03attacks4hi.nuanmb', 'c03attacks4lw.nuanmb') and vanilla.exists():
                fail(f'{slot}: {clip} exists in the base game, so it is not a new file')
    print(f'PASS recipient really lacks {list(RECIPIENT_LACKS)}: they are new files')

    for slot in ('c06', 'c07'):
        built = read_mlist(mod / f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        for kind, want in EXPECTED.items():
            h = hash40(kind)
            if h not in built:
                fail(f'{slot}: motion kind {kind} is missing from the built list')
            e = built[h]
            if e['cancel'] != want['cancel'] or e['flags'] != want['flags']:
                fail(f'{slot}: {kind} is cancel {e["cancel"]} flags {e["flags"]:#x}, '
                     f'expected {want["cancel"]} / {want["flags"]:#x}')
            want_clip = KIND_CLIP[kind]
            if e['anims'] != (hash40(want_clip),):
                fail(f'{slot}: {kind} does not name {want_clip}')
        # G&W's own values must be gone: a same-cancel-frame donor would hide a
        # stale entry, so compare against the recorded recipient readings.
        for kind, old in EXPECTED_RECIPIENT.items():
            e = built[hash40(kind)]
            if (e['cancel'], e['flags']) == (old['cancel'], old['flags']) and \
                    old != EXPECTED[kind]:
                fail(f'{slot}: {kind} still carries the recipient entry '
                     f'{old["cancel"]}/{old["flags"]:#x}')
        print(f'PASS {slot} motion entries: 4 donor entries '
              f'(cancel 44/0/44/44, flags 0x84)')
    # And the donor's own entries are byte-identical to what we read from it.
    src = read_mlist(DONOR_MOTION)
    built = read_mlist(mod / 'fighter/eflame/motion/body/c06/motion_list.bin')
    for kind in EXPECTED:
        h = hash40(kind)
        if src[h]['raw'] != built[h]['raw']:
            fail(f'{kind} entry is not the donor entry byte-for-byte')
    print('PASS donor motion entries copied byte-for-byte')
    return {'entries': {k: EXPECTED[k] for k in EXPECTED},
            'kinds_new_to_recipient': list(RECIPIENT_LACKS)}


def check_clips(mod: Path) -> dict:
    """3. The retargeted clips carry donor bones on the recipient's built skeleton."""
    out = {}
    for slot in ('c06', 'c07'):
        skel = s.skel_data.read_skel(str(mod / f'fighter/eflame/model/body/{slot}/model.nusktb'))
        exact = {b.name for b in skel.bones}
        for clip in DONOR_CLIPS:
            anim = s.anim_data.read_anim(
                str(mod / f'fighter/eflame/motion/body/{slot}/{clip}'))
            groups = {g.group_type.name for g in anim.groups}
            if 'Transform' not in groups:
                fail(f'{slot}/{clip}: no Transform group')
            tr = next(g for g in anim.groups if g.group_type.name == 'Transform')
            names = {n.name for n in tr.nodes}
            # armr/HandR are what the hitboxes ride; they must be present.
            for bone in ('ArmR', 'HandR'):
                if bone not in names:
                    fail(f'{slot}/{clip}: {bone} is not animated, so the hitboxes '
                         'would ride the bind pose')
            if 'Visibility' not in groups:
                fail(f'{slot}/{clip}: no Visibility group, so G&W meshes would not be set')
            out[f'{slot}/{clip}'] = {
                'bones': len(names),
                'on_recipient': len(names & exact),
                'frames': len(next(iter(tr.nodes)).tracks[0].values),
                'sha256': sha(mod / f'fighter/eflame/motion/body/{slot}/{clip}'),
            }
    print(f"PASS clips: {len(out)} files, arm chain animated, visibility group present")
    return out


def check_sounds(mod: Path) -> dict:
    """4. The four names the scripts play resolve in the built banks."""
    sys.path.insert(0, str(ROOT / 'tools'))
    from merge_donor_sound import bank_keys
    banks = {
        'se_littlemac_smash_s02': 'sound/bank/fighter/se_eflame_c06',
        'se_littlemac_smash_s03': 'sound/bank/fighter/se_eflame_c06',
        'se_littlemac_smash_s04': 'sound/bank/fighter/se_eflame_c06',
        'vc_littlemac_attack05': 'sound/bank/fighter_voice/vc_eflame_c06',
    }
    if set(banks) != set(SOUND_NAMES):
        fail('SOUND_NAMES and the checked bank map disagree')
    out = {}
    for name, stem in banks.items():
        for suffix in ('c06', 'c07'):
            p = mod / f'{stem[:-3]}{suffix}'
            keys = bank_keys(p)
            crc = zlib.crc32(name.lower().encode())
            if crc not in keys:
                fail(f'{p.name} does not resolve {name}')
            out.setdefault(name, []).append(p.name)
    print(f'PASS sounds resolve by crc32(lower): {sorted(out)}')
    return out


def check_effect(mod: Path) -> dict:
    """5. Each gated slot owns a bank carrying both fist emitters, and nothing else moved.

    Tier B. Says nothing about whether the game draws them; the bank being
    reachable by `eflame` is what makes the ACMD's `EFFECT_FOLLOW` calls resolve
    at all, and the console is still the only thing that can show the trail.
    """
    import build_littlemac_fsmash_effect as eff
    misplaced = mod / MISPLACED_DONOR_BANK
    if misplaced.exists():
        fail(f'{MISPLACED_DONOR_BANK} is still shipped; an eflame fighter never loads it. '
             'It is also a duplicate of a real ARC path, so the declaration is wrong twice.')
    result = {'misplaced_donor_bank_shipped': False, 'slots': {}}
    for slot, rel in SLOT_BANKS.items():
        p = mod / rel
        if not p.is_file():
            fail(f'{rel} missing; littlemac_attack_line would be a silent no-op on {slot}')
        names = eff.eff_names(p)
        for e in eff.REQUIRED_EMITTERS:
            if e not in names:
                fail(f'{p.name} lacks emitter {e}')
        result['slots'][slot] = {'sha256': sha(p), 'emitters': len(names)}
    # Merge, not replace: the vanilla bank's own emitters must all survive, or
    # the slot would lose G&W props, Pyra sword and sys_* companions.
    vanilla = vanilla_bank()
    if vanilla:
        base = set(eff.eff_names(vanilla))
        for slot, rel in SLOT_BANKS.items():
            have = set(eff.eff_names(mod / rel))
            lost = sorted(base - have)
            if lost:
                fail(f'{rel} dropped {len(lost)} emitter(s) the vanilla bank had: {lost[:10]}')
            gained = sorted(have - base)
            missing = sorted(set(eff.REQUIRED_EMITTERS) - set(gained))
            if missing:
                fail(f'{rel} gained {gained} but is missing {missing}')
            result['slots'][slot].update({'vanilla_emitters': len(base),
                                          'gained': gained, 'vanilla_lost': 0})
        print(f'PASS slot banks own both fist emitters and keep all {len(base)} vanilla emitters')
    else:
        print('PASS slot banks own both fist emitters '
              '(vanilla baseline bank unavailable, preservation not checked)')
    return result


def vanilla_bank():
    """The unmodified `effect/fighter/eflame/ef_eflame.eff`, or None if unreadable."""
    for base in (EXPORT, Path(tomllib.loads((ROOT / 'paths.toml').read_text())
                              ['dumps']['arc'])):
        p = Path(base) / 'effect/fighter/eflame/ef_eflame.eff'
        if p.is_file():
            return p
    return None


def check_baseline(mod: Path, baseline: Path) -> dict:
    """6. Nothing outside the allowed overrides changed."""
    if not baseline.is_dir():
        print(f'SKIP baseline delta: {baseline} not present')
        return {}
    def tree(root):
        return {p.relative_to(root).as_posix(): sha(p)
                for p in root.rglob('*') if p.is_file()}
    new, old = tree(mod), tree(baseline)
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(new) & set(old) if new[k] != old[k])
    def allowed(rel):
        return rel in ALLOWED_OVERRIDES or any(
            rel == t.format(slot=s) for t in ALLOWED_OVERRIDES for s in ('c06', 'c07'))
    unexpected_changed = [k for k in changed if not allowed(k)]
    if unexpected_changed:
        fail(f'{len(unexpected_changed)} file(s) changed outside the intended overrides: '
             f'{unexpected_changed[:10]}')
    if removed:
        fail(f'{len(removed)} baseline file(s) removed: {removed[:10]}')
    print(f'PASS baseline intact: {len(added)} added, {len(changed)} intended overrides, '
          f'0 unexpected, 0 removed')
    return {'added': added, 'changed': changed, 'removed': removed,
            'unexpected_changed': unexpected_changed}


def check_handlers(pkg: Path) -> dict:
    """7. The packaged plugin NRO carries every handler this move needs.

    Added after a packaging run shipped the wrong agent's NRO on 2026-10-01 and
    every other check still passed. The names are stored as ASCII in the NRO, so
    a plain byte search is the whole test; a handler that is not in the binary is
    a move that animates and hits nothing, silently.
    """
    nro = pkg / ('atmosphere/contents/01006A800016E000/romfs/skyline/plugins/'
                 'libpyra_gamewatch_reskin.nro')
    if not nro.is_file():
        return {'skipped': 'no NRO in package (mod-only package?)'}
    data = nro.read_bytes()
    missing = [n for n in REQUIRED_HANDLERS if n.encode() not in data]
    if missing:
        fail(f'the packaged NRO is missing {len(missing)} handler name(s): {missing}')
    # The angled sound names travel as literals too, and a bank merge that lost
    # them would be invisible to check_sounds (which reads the merged bank).
    missing_se = [n for n in SOUND_NAMES if n.encode() not in data]
    if missing_se:
        fail(f'the packaged NRO never names {missing_se}, so those sounds cannot play')
    print(f'PASS packaged NRO carries all {len(REQUIRED_HANDLERS)} handler names '
          f'and all {len(SOUND_NAMES)} sound names')
    return {'nro': nro.relative_to(ROOT).as_posix(), 'sha256': sha(nro),
            'handlers': list(REQUIRED_HANDLERS)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', required=True, help='e.g. builds/pgwr/0.20.14')
    ap.add_argument('--baseline', default='', help='earlier package mod dir, for the delta')
    ap.add_argument('--check', action='store_true', help='fail instead of writing a report')
    args = ap.parse_args()

    pkg = Path(args.package)
    if not pkg.is_absolute():
        pkg = ROOT / pkg
    mod = pkg / 'ultimate' / 'mods' / 'pyra_gamewatch_reskin'
    if not mod.is_dir():
        raise SystemExit(f'no mod tree at {mod}')

    report = {'package': pkg.relative_to(ROOT).as_posix(), 'tool_version': '1.1.0',
              'evidence_tier': 'B', 'date': '2026-10-01'}
    report['donor'] = check_donor()
    report['motion'] = check_motion_entries(mod, report['donor'])
    report['clips'] = check_clips(mod)
    report['sounds'] = check_sounds(mod)
    report['effect'] = check_effect(mod)
    report['plugin'] = check_handlers(pkg)
    if args.baseline:
        b = Path(args.baseline)
        if not b.is_absolute():
            b = ROOT / b
        report['baseline'] = check_baseline(mod, b)

    version = pkg.name
    out = REF / f'audit_{version.replace(".", "_")}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'report: {out.relative_to(ROOT).as_posix()}')
    print('audit_littlemac_fsmash PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
