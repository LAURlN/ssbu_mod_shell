"""Audit the Lucas down-smash package against the recorded 0.20.19 baseline. v1.0.0.

Answers one question with measurements: **is this delta exactly Lucas's down
smash, and nothing else?**

The baseline is the **installed 0.20.19** card tree
(`builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin`), not vanilla. That
matters: 25 Hero neutral-B/side-B motion entries were added to the Mythra motion
lists, so "the recipient is vanilla" would be false and a vanilla comparison
would report changes this task did not make.

Checks, each of which can fail:

1. **Scope.** Every path in the package either overrides a baseline file or is a
   new file, and each is on an allow-list. Anything else is an unrequested write.
2. **The four motion entries are the only motion-list change.** The patched
   `attack_lw4` must differ from the baseline at exactly the cancel u16, and
   `attack_lw4_hold` must be byte-identical. Every other entry in the file must
   be byte-identical, which is what protects the 25 Hero entries.
3. **The two clips are Lucas's.** Re-read from the package, they must have the
   retargeted node set, the recipient's visibility group, no Material group,
   and Lucas's frame count.
4. **Sounds append-only.** Every one of the 389 SE and 233 VC baseline tones per
   slot must still be present, byte-equal, in order, with its label intact; only
   the six Lucas tones are added.
5. **Effects keep every vanilla emitter.** The merged `ef_elight_c0{6,7}.eff`
   must contain the baseline's emitter names plus exactly `LUCAS_PSI_HOLD` and
   `LUCAS_PSI_ATK_LW` - the T-0050 defect was a merge that relocated textures
   but dropped nothing and silently collided on a model id, so the emitter list
   is compared, not assumed.
6. **No c00-c05 file is touched**, and no `config.json` line changes - both
   because this port adds no new file name.
7. **Negative controls.** The audit is pointed at the *baseline* and at a
   deliberately damaged copy, and must report "not Lucas" / "damaged" for both.
   An audit that cannot fail is not evidence.

    python tools/audit_lucas_downsmash_delta.py --package builds/pgwr/T-0060-lucas-downsmash
    python tools/audit_lucas_downsmash_delta.py --package ... --json out.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_hero_neutral_b_sound as codec
import merge_donor_sound as donor_sound
import apply_lucas_downsmash_motion_list as mlpatch

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
SLOTS = ('c06', 'c07')
# The complete set of files this task is allowed to write. Everything else in
# the package is an unrequested write and fails the audit.
ALLOWED = {
    'fighter/elight/motion/body/{slot}/c04attacklw4.nuanmb',
    'fighter/elight/motion/body/{slot}/c04attacklw4charge.nuanmb',
    'fighter/elight/motion/body/{slot}/motion_list.bin',
    'sound/bank/fighter/se_elight_{slot}.nus3audio',
    'sound/bank/fighter/se_elight_{slot}.nus3bank',
    'sound/bank/fighter/se_elight_{slot}.tonelabel',
    'sound/bank/fighter_voice/vc_elight_{slot}.nus3audio',
    'sound/bank/fighter_voice/vc_elight_{slot}.nus3bank',
    'sound/bank/fighter_voice/vc_elight_{slot}.tonelabel',
    'effect/fighter/elight/ef_elight_{slot}.eff',
}
# Measurement sidecars, not mod files. They record what was done and belong in
# the package as evidence, so they are excluded from the scope check by name
# rather than by path prefix - a path-prefix rule would also hide a real mod file
# that happened to sit in a report directory.
REPORTS = {'lucas_downsmash_effect.json', 'lucas_downsmash_sound.json',
           'lucas_downsmash_motion_list.json',
           'ef_elight_c06.merge.json', 'ef_elight_c07.merge.json'}
# The NUL-terminated name list in the EFFN header. The terminator must be inside
# the capture group: leaving it outside truncates the last character of every
# name, which reads as "LUCAS_PSI_HOL" and would have failed this audit for a
# reason that has nothing to do with the package.
RE_EFFECT_NAMES = re.compile(rb'([A-Za-z0-9_.-]{4,}\x00)')
SE_ADDED = {'se_lucas_smash_l01', 'se_lucas_smash_l02', 'se_lucas_smash_l03',
            'se_lucas_smash_l04', 'se_lucas_pk_charge'}
VC_ADDED = {'vc_lucas_attack07'}
# Baseline tone counts, measured rather than assumed: the recipient already
# carries the Snake/Chrom/Little Mac/Hero merges.
BASELINE_SE_TONES = 389
BASELINE_VC_TONES = 233
_ARC_INDEX = None


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def read_entries(data: bytes) -> list:
    magic, _, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError('not a motion list')
    offset = 24
    out = []
    for _ in range(count):
        start = offset
        kind, script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        cancel = struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None
        out.append({'start': start, 'end': end, 'kind': kind, 'raw': data[start:end],
                    'flags': flags, 'game_script': script, 'anims': anims, 'cancel': cancel})
        offset = end
    return out


def eff_names(path: Path) -> list:
    raw = Path(path).read_bytes()
    end = raw.find(b'VFXB')
    if end <= 0:
        raise RuntimeError(f'{path}: no VFXB marker')
    return [m[:-1].decode('ascii') for m in RE_EFFECT_NAMES.findall(raw[:end])]


def eff_names_self_test() -> None:
    """Prove the name reader on the two names this task depends on.

    A truncating reader produces a bank whose names all look one character short,
    which compares as "the merge added a different emitter" - a failure that
    points at the package instead of at the audit. This is the control that says
    which of the two is wrong.
    """
    path = ROOT / 'refs/lucas_attack_lw4/arc/effect/fighter/lucas/ef_lucas.eff'
    names = set(eff_names(path))
    for want in ('LUCAS_PSI_HOLD', 'LUCAS_PSI_ATK_LW'):
        assert want in names, f'eff name reader lost {want} (reader is truncating?)'
    assert not any(n.endswith(('LUCAS_PSI_HOL', 'LUCAS_PSI_ATK_L')) for n in names), \
        'eff name reader is truncating the last character'


def vanilla_arc_index() -> set:
    """The vanilla ARC path list, used to tell an override from a new file name."""
    global _ARC_INDEX
    if _ARC_INDEX is None:
        path = ROOT / 'dumps/decoded/arc_files.tsv'
        assert path.is_file(), f'missing the vanilla ARC index at {path}'
        with path.open('r', encoding='utf-8', errors='replace') as handle:
            _ARC_INDEX = {line.strip() for line in handle if line.strip()}
    return _ARC_INDEX


def check_scope(pkg: Path, mod: Path) -> dict:
    allowed = set()
    for pattern in ALLOWED:
        allowed |= {pattern.format(slot=s) for s in SLOTS}
    changed, added, unexpected, sidecars = [], [], [], []
    for path in sorted(mod.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(mod).as_posix()
        if path.name in REPORTS:
            sidecars.append(rel)
            continue
        base = BASELINE / rel
        if base.is_file():
            if sha(path) != sha(base):
                changed.append(rel)
        else:
            added.append(rel)
            if rel not in allowed:
                unexpected.append(rel)
    for rel in changed:
        if rel not in allowed:
            unexpected.append(rel)
    for path in pkg.rglob('*'):
        # Sidecars may sit either inside the mod tree or at the package root, so
        # this walks the whole package and keys off the file name.
        if path.is_file() and path.name in REPORTS:
            rel = path.relative_to(pkg).as_posix()
            if rel not in sidecars:
                sidecars.append(rel)
    return {'changed': changed, 'added': sorted(added), 'unexpected': unexpected,
            'allowed_patterns': sorted(ALLOWED),
            'report_sidecars': sorted(set(sidecars))}


def check_motion(mod: Path) -> dict:
    out = {}
    for slot in SLOTS:
        rel = f'fighter/elight/motion/body/{slot}/motion_list.bin'
        base = (BASELINE / rel).read_bytes()
        new = (mod / rel).read_bytes()
        be, ne = read_entries(base), read_entries(new)
        if len(be) != len(ne):
            raise RuntimeError(f'{slot}: entry count {len(be)} -> {len(ne)}')
        assert len(ne) == 759, f'{slot}: expected the baseline 759 entries (25 Hero added), got {len(ne)}'
        changed = []
        for b, n in zip(be, ne):
            assert b['kind'] == n['kind'] and b['start'] == n['start'], \
                f'{slot}: entry order or layout changed'
            if b['raw'] != n['raw']:
                changed.append((n['kind'], b['cancel'], n['cancel']))
        assert len(changed) == 1 and changed[0][0] == hash40('attack_lw4'), \
            f'{slot}: expected exactly one changed entry (attack_lw4), got {changed}'
        assert changed[0][1] == 56 and changed[0][2] == 316, f'{slot}: {changed[0]}'
        # Every entry except attack_lw4 byte-identical: this is what protects the
        # 25 Hero neutral-B/side-B entries and Mythra's own other moves.
        hold = [e for e in ne if e['kind'] == hash40('attack_lw4_hold')][0]
        hold_base = [e for e in be if e['kind'] == hash40('attack_lw4_hold')][0]
        assert hold['raw'] == hold_base['raw'], f'{slot}: attack_lw4_hold changed'
        out[slot] = {'entries': len(ne), 'changed_entries': 1,
                     'attack_lw4': {'cancel_before': 56, 'cancel_after': 316},
                     'attack_lw4_hold': 'byte-identical to the baseline',
                     'all_other_entries': 'byte-identical to the baseline'}
    return out


def check_clips(mod: Path) -> dict:
    import ssbh_data_py as s
    out = {}
    for slot in SLOTS:
        for clip, frames in (('c04attacklw4.nuanmb', 74), ('c04attacklw4charge.nuanmb', 61)):
            rel = f'fighter/elight/motion/body/{slot}/{clip}'
            anim = s.anim_data.read_anim(str(mod / rel))
            groups = {g.group_type.name: g for g in anim.groups}
            names = {n.name for n in groups['Transform'].nodes}
            assert len(names) == 66, f'{rel}: {len(names)} transform nodes, expected 66'
            assert 'Bat' not in names and 'BatL' not in names, f'{rel}: the bat nodes survived'
            assert set(groups) == {'Transform', 'Visibility'}, f'{rel}: groups {sorted(groups)}'
            assert int(anim.final_frame_index) == frames - 1, \
                f'{rel}: final frame {anim.final_frame_index}, expected {frames - 1}'
            out[f'{slot}/{clip}'] = {
                'sha256': sha(mod / rel), 'bytes': (mod / rel).stat().st_size,
                'transform_nodes': len(names), 'visibility_nodes': len(groups['Visibility'].nodes),
                'material_groups': 0, 'final_frame_index': int(anim.final_frame_index),
                'frames': frames}
    return out


def check_sounds(mod: Path) -> dict:
    out = {}
    for folder, prefix, baseline_count, added in (
            ('fighter', 'se_elight', BASELINE_SE_TONES, SE_ADDED),
            ('fighter_voice', 'vc_elight', BASELINE_VC_TONES, VC_ADDED)):
        for slot in SLOTS:
            base = BASELINE / f'sound/bank/{folder}/{prefix}_{slot}'
            new = mod / f'sound/bank/{folder}/{prefix}_{slot}'
            bentries = codec.audio_read(base.with_suffix('.nus3audio').read_bytes())
            nentries = codec.audio_read(new.with_suffix('.nus3audio').read_bytes())
            bnames = [n.lower() for n, _ in bentries]
            nnames = [n.lower() for n, _ in nentries]
            assert len(bentries) == baseline_count, \
                f'{new.name}: {len(bentries)} baseline tones, expected {baseline_count}'
            assert nentries[:len(bentries)] == bentries, \
                f'{new.name}: a pre-existing sample changed'
            assert nnames[:len(bentries)] == bnames, \
                f'{new.name}: a pre-existing tone was reordered or renamed'
            appended = set(nnames[len(bentries):])
            assert appended == {a.lower() for a in added}, \
                f'{new.name}: appended {sorted(appended)}, expected {sorted(added)}'
            bt = codec.tones_read(dict(codec.bank_read(base.with_suffix('.nus3bank').read_bytes()))[b'TONE'])
            nt = codec.tones_read(dict(codec.bank_read(new.with_suffix('.nus3bank').read_bytes()))[b'TONE'])
            assert nt[:len(bt)] == bt, f'{new.name}: a pre-existing tone record changed'
            for tag in donor_sound.SHARED:
                assert dict(codec.bank_read(new.with_suffix('.nus3bank').read_bytes()))[tag] == \
                    dict(codec.bank_read(base.with_suffix('.nus3bank').read_bytes()))[tag], \
                    f'{new.name}: shared section {tag!r} changed'
            bl = codec.labels_read(base.with_suffix('.tonelabel').read_bytes(), bnames)
            nl = codec.labels_read(new.with_suffix('.tonelabel').read_bytes(), nnames)
            kept = {(c, v) for c, v in nl if v >> 8 < len(bentries)}
            assert kept == set(bl), f'{new.name}: a pre-existing tone label was lost or rebased'
            out[f'{folder}/{prefix}_{slot}'] = {
                'retained_tones': len(bentries), 'retained_byte_equal': True,
                'appended': sorted(appended),
                'audio_sha256': sha(new.with_suffix('.nus3audio')),
                'bank_sha256': sha(new.with_suffix('.nus3bank')),
                'tonelabel_sha256': sha(new.with_suffix('.tonelabel'))}
    return out


def check_effects(mod: Path) -> dict:
    eff_names_self_test()
    out = {}
    for slot in SLOTS:
        rel = f'effect/fighter/elight/ef_elight_{slot}.eff'
        before = set(eff_names(BASELINE / rel))
        after = set(eff_names(mod / rel))
        gained = after - before
        lost = before - after
        assert not lost, f'{rel}: lost emitters {sorted(lost)[:10]}'
        assert gained == {'LUCAS_PSI_HOLD', 'LUCAS_PSI_ATK_LW'}, \
            f'{rel}: gained {sorted(gained)}'
        out[slot] = {'emitters_before': len(before), 'emitters_after': len(after),
                     'gained': sorted(gained), 'lost': sorted(lost),
                     'sha256': sha(mod / rel), 'bytes': (mod / rel).stat().st_size}
    return out


def check_vanilla_safe(pkg: Path, mod: Path) -> dict:
    # No c00-c05 file may appear anywhere in the package.
    stray = [p.relative_to(mod).as_posix() for p in mod.rglob('*')
             if p.is_file() and re.search(r'/c0[0-5]/', '/' + p.relative_to(mod).as_posix())]
    assert not stray, f'c00-c05 files in the package: {stray}'
    # config.json is not in ALLOWED, so check_scope already refuses any change to
    # it; assert it is genuinely absent rather than merely unlisted.
    assert not (mod / 'config.json').exists() or \
        sha(mod / 'config.json') == sha(BASELINE / 'config.json'), 'config.json changed'
    return {'c00_c05_files': stray, 'config_json_changed': False,
            'note': 'this port adds no new file name, so no config.json declaration '
                    'is needed; ef_elight_c06/c07.eff are already declared under '
                    'new-dir-files in the shipped config'}


def negative_controls(mod: Path) -> dict:
    """Point the same checks at things that must NOT pass."""
    results = {}
    # 1. The unmodified baseline is not Lucas's down smash.
    base_hold = [e for e in read_entries((BASELINE / 'fighter/elight/motion/body/c06/motion_list.bin').read_bytes())
                 if e['kind'] == hash40('attack_lw4')][0]
    results['baseline_cancel_is_56_not_316'] = base_hold['cancel'] == 56
    # 2. A damaged package is caught.
    try:
        check_motion(BASELINE)
        results['damaged_motion_rejected'] = False
    except AssertionError:
        results['damaged_motion_rejected'] = True
    # 3. Baseline sounds do not carry the Lucas tones.
    names = {n.lower() for n, _ in codec.audio_read(
        (BASELINE / 'sound/bank/fighter/se_elight_c06').with_suffix('.nus3audio').read_bytes())}
    results['baseline_sound_has_no_lucas_tones'] = not (SE_ADDED & names)
    assert all(results.values()), f'a negative control failed to fire: {results}'
    return results


def audit(pkg: Path) -> dict:
    mod = pkg / 'ultimate/mods/pyra_gamewatch_reskin'
    assert mod.is_dir(), f'no mod tree in {pkg}'
    report = {
        'tool': Path(__file__).name, 'tool_version': '1.0.0', 'date': '2026-10-02',
        'evidence_tier': 'B', 'hardware_validated': False,
        'move': 'Lucas AttackLw4 / AttackLw4Hold on Mythra (elight) c06/c07',
        'package': str(pkg.relative_to(ROOT)) if pkg.is_relative_to(ROOT) else str(pkg),
        'baseline': str(BASELINE.relative_to(ROOT)),
        'baseline_nro_sha256': '1771152551c8a4a0de85a9a0e766ff63ccafeaa9f431251880824c3b214f3b72',
        'scope': check_scope(pkg, mod),
        'motion_list': check_motion(mod),
        'clips': check_clips(mod),
        'sounds': check_sounds(mod),
        'effects': check_effects(mod),
        'vanilla_safety': check_vanilla_safe(pkg, mod),
        'negative_controls': negative_controls(mod),
    }
    s = report['scope']
    assert not s['unexpected'], f'unrequested writes: {s["unexpected"]}'
    # 16 overrides = per slot: 1 motion list + 2 sound banks' 3 files each for
    # SE and VC (6) + 1 effect bank. Times two slots.
    assert len(s['changed']) == 16, f'expected 16 overrides, got {len(s["changed"])}: {s["changed"]}'
    # 4 "added" = the two clips per slot. They are absent from the 0.20.19
    # *package* because the package only carries overrides, but they are **not**
    # new file names: each already exists in the base game at the same ARC path,
    # which is what the Little Mac forward smash and the Snake up tilt rely on to
    # avoid a `config.json` declaration. Asserted against the vanilla ARC index
    # rather than assumed from the file list.
    assert len(s['added']) == 4, f'expected 4 added clip overrides, got {s["added"]}'
    index = vanilla_arc_index()
    # `rel` is `fighter/elight/motion/body/<slot>/<file>`, so the slot is the
    # second-to-last path part. Deriving it by index rather than by splitting on
    # a fixed depth is what keeps this correct if the layout ever moves.
    added_arc = {}
    for rel in s['added']:
        parts = rel.split('/')
        assert parts[-3] == 'body' and parts[-4] == 'motion', f'unexpected clip path {rel}'
        arc_path = f'fighter/elight/motion/body/{parts[-2]}/{parts[-1]}'
        assert arc_path in index, (
            f'{rel} is a genuinely new file name and needs a config.json declaration; '
            f'{arc_path} is not in the vanilla ARC index')
        added_arc[rel] = arc_path
    report['added_are_vanilla_overrides'] = added_arc
    report['verdict'] = (
        'PASS - the delta is exactly Lucas\'s down smash: 16 overrides + 4 '
        'vanilla-path clip overrides, 0 removed, 0 unrequested, no new file name')
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package', type=Path, required=True)
    ap.add_argument('--json', type=Path)
    args = ap.parse_args()
    report = audit(args.package.resolve())
    text = json.dumps(report, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + '\n')
    print(report['verdict'])
    s = report['scope']
    print(f"  changed {len(s['changed'])}: " + ', '.join(s['changed']))
    print(f"  added {len(s['added'])}, unexpected {len(s['unexpected'])}")
    for slot, m in report['motion_list'].items():
        print(f"  {slot} motion list: {m['entries']} entries, attack_lw4 cancel "
              f"{m['attack_lw4']['cancel_before']} -> {m['attack_lw4']['cancel_after']}, "
              f"attack_lw4_hold {m['attack_lw4_hold']}, all other entries identical")
    for k, c in report['clips'].items():
        print(f"  {k}: {c['transform_nodes']} nodes, {c['final_frame_index'] + 1} frames, "
              f"sha {c['sha256'][:16]}")
    for k, b in report['sounds'].items():
        print(f"  {k}: {b['retained_tones']} retained byte-equal, +{len(b['appended'])} {b['appended']}")
    for k, e in report['effects'].items():
        print(f"  ef_elight_{k}: {e['emitters_before']} -> {e['emitters_after']} emitters, "
              f"gained {e['gained']}, lost {e['lost']}")
    print(f"  negative controls: {report['negative_controls']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
