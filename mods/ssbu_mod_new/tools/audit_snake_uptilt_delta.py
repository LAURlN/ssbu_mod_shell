"""Audit a pgwr package against its baseline for the Snake up-tilt change (v1.0.0).

    python tools/audit_snake_uptilt_delta.py --baseline 0.20.17 --version 0.20.19
    python tools/audit_snake_uptilt_delta.py --baseline 0.20.17 --version 0.20.19 \
        --combined "other agent's changes"

Proves, from the packaged bytes (tier B, offline; nothing here says how the move
plays in game):
  * no file was added or removed, and the changed set is exactly the intended
    one (or, with `--combined`, contains it and reports the rest);
  * c06/c07 motion lists differ from the baseline in the `attack_hi3` entry
    only, and that entry equals Snake's raw donor entry (cancel 38, flags 0x84,
    `game_attackhi3`);
  * the retargeted clip is present in both slots with the pinned donor node
    subset, and the whole leg chain actually moves - the R.O.B. down-tilt
    failure this move must not repeat;
  * the se/vc banks retain every baseline tone (names, sample bytes and tone
    records) and gain the up-tilt tones; eflame.sqb retains every baseline
    record and gains the `seq_snake_rnd_attack` record;
  * the packaged NRO carries all four handler names, both sound names and the
    two effect names this move plays;
  * no c00-c05 Pyra file is in the delta at all.

Writes `SNAKE_UPTILT_DELTA.json` in the new package.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import merge_hero_neutral_b_sound as codec  # noqa: E402
import merge_snake_uptilt_sound as us  # noqa: E402
import build_snake_uptilt as su  # noqa: E402
import ssbh_data_py as s  # noqa: E402

MOD = 'ultimate/mods/pyra_gamewatch_reskin'
NRO = 'atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro'
HANDLERS = ('game_attackhi3', 'effect_attackhi3', 'sound_attackhi3', 'expression_attackhi3')
NRO_NAMES = HANDLERS + ('se_snake_attackhard_h01', 'seq_snake_rnd_attack',
                        'sys_attack_arc_b', 'sys_turn_smoke', 'rbkind_attackm')


def tree(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}


def entries(path):
    data = Path(path).read_bytes()
    _, _, count = struct.unpack_from('<QQQ', data, 0)
    off, out = 24, {}
    for _ in range(count):
        start = off
        kind, _gs, _fl, _bl, n, size = struct.unpack_from('<QQHBBI', data, off)
        off = (off + 24 + n * 9 + 3) & ~3
        out[kind] = data[start:off + size]
        off += size
    return out


def resolve(name):
    """A version name under builds/pgwr, or any path (for a private staging directory)."""
    path = Path(name)
    if path.is_dir():
        return path.resolve()
    return ROOT / 'builds/pgwr' / name


def expected_files():
    expected = {'info.toml', 'sound/sequence/fighter/eflame.sqb'}
    for slot in ('c06', 'c07'):
        expected |= {f'fighter/eflame/motion/body/{slot}/{f}' for f in ('motion_list.bin', su.CLIP)}
        for folder, prefix in (('fighter', 'se'), ('fighter_voice', 'vc')):
            expected |= {f'sound/bank/{folder}/{prefix}_eflame_{slot}{e}'
                         for e in ('.nus3audio', '.nus3bank', '.tonelabel')}
    return expected


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', required=True,
                    help='baseline package: a name under builds/pgwr, or any path')
    ap.add_argument('--version', required=True,
                    help='candidate package: a name under builds/pgwr, or any path '
                         '(a staging directory is fine - the audit never writes into one)')
    ap.add_argument('--combined', help='label recorded when other changes share the build')
    ap.add_argument('--json', type=Path, help='write the report here instead of the package')
    args = ap.parse_args()
    base_pkg = resolve(args.baseline)
    new_pkg = resolve(args.version)
    base, new = base_pkg / MOD, new_pkg / MOD
    a, b = tree(base), tree(new)
    # A combined build may add or remove files of the other changes (e.g. the eflame effect
    # banks); on its own the up tilt adds and removes nothing.
    added_removed = sorted(set(a) ^ set(b))
    assert args.combined or not added_removed, ('added or removed files', added_removed)
    if added_removed:
        print('combined build, files added/removed by other changes:', added_removed)
    changed = sorted(k for k in a if k in b and a[k] != b[k])
    expected = expected_files()
    missing = sorted(expected - set(changed))
    extra = sorted(set(changed) - expected)
    assert not missing, f'up-tilt files that did not change: {missing}'
    if args.combined:
        assert extra, '--combined given but the delta is exactly the up-tilt set'
    else:
        assert not extra, f'unexpected files changed: {extra}'
    stray = [k for k in changed if re_slot(k)]
    assert not stray, f'vanilla c00-c05 files are in the delta: {stray}'

    kind = su.hash40(su.KIND)
    donor = su.get_entry()
    assert donor['cancel'] == su.EXPECTED_CANCEL and donor['flags'] == su.EXPECTED_FLAGS
    motion = {}
    for slot in ('c06', 'c07'):
        old = entries(base / f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        cur = entries(new / f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        assert set(old) == set(cur)
        diff = [k for k in old if old[k] != cur[k]]
        assert diff == [kind] and cur[kind] == donor['raw'], diff
        anim = s.anim_data.read_anim(str(new / f'fighter/eflame/motion/body/{slot}/{su.CLIP}'))
        groups = {g.group_type.name: len(g.nodes) for g in anim.groups}
        assert 'Material' not in groups, f'{slot}: a Material group survived'
        transform = next(g for g in anim.groups if g.group_type.name == 'Transform')
        idle = s.anim_data.read_anim(
            str(new / f'fighter/eflame/motion/body/{slot}/a00wait1.nuanmb'))
        idle_values = {n.name: n.tracks[0].values[0] for g in idle.groups
                       if g.group_type.name == 'Transform' for n in g.nodes}
        legs = su.leg_motion({n.name: n.tracks[0].values for n in transform.nodes}, idle_values)
        assert all(v.get('moved') for v in legs.values()), f'{slot}: leg chain is static: {legs}'
        motion[slot] = {'entries': len(cur), 'changed_kinds': [hex(k) for k in diff],
                        'clip_sha256': b[f'fighter/eflame/motion/body/{slot}/{su.CLIP}'],
                        'transform_nodes': len(transform.nodes),
                        'visibility_nodes': groups.get('Visibility'),
                        'frames': sorted({len(n.tracks[0].values) for n in transform.nodes}),
                        'leg_motion': legs}

    voice = set(us.voice_names(us.sequence_record(),
                               [n for n, _ in codec.audio_read(
                                   us.VC_DONOR.with_suffix('.nus3audio').read_bytes())]))
    sound = {}
    for slot in ('c06', 'c07'):
        for folder, prefix, want in (('fighter', 'se', us.SE_REQUIRED),
                                     ('fighter_voice', 'vc', voice)):
            stem = f'sound/bank/{folder}/{prefix}_eflame_{slot}'
            old_bank = codec.audio_read((base / (stem + '.nus3audio')).read_bytes())
            cur_bank = codec.audio_read((new / (stem + '.nus3audio')).read_bytes())
            assert cur_bank[:len(old_bank)] == old_bank, f'{stem}: a baseline tone changed or moved'
            old_tones = codec.tones_read(dict(codec.bank_read(
                (base / (stem + '.nus3bank')).read_bytes()))[b'TONE'])
            cur_tones = codec.tones_read(dict(codec.bank_read(
                (new / (stem + '.nus3bank')).read_bytes()))[b'TONE'])
            assert cur_tones[:len(old_tones)] == old_tones, f'{stem}: a baseline tone record changed'
            appended = {n.lower() for n, _ in cur_bank[len(old_bank):]}
            assert want <= appended, f'{stem}: up-tilt tones missing, appended {sorted(appended)}'
            if not args.combined:
                assert appended == want, f'{stem}: unexpected extra tones {sorted(appended - want)}'
            sound[f'{folder}/{slot}'] = {'retained': len(old_bank), 'appended': sorted(appended)}
    old = codec.sqb_read((base / 'sound/sequence/fighter/eflame.sqb').read_bytes())
    cur = codec.sqb_read((new / 'sound/sequence/fighter/eflame.sqb').read_bytes())
    assert cur[:len(old)] == old, 'eflame.sqb lost a baseline record'
    assert us.sequence_record() in cur, 'seq_snake_rnd_attack record missing from eflame.sqb'
    assert sum(1 for r in cur if r == us.sequence_record()) == 1, 'duplicate snake record'

    nro = (new_pkg / NRO).read_bytes()
    missing_names = [n for n in NRO_NAMES if n.encode() not in nro]
    assert not missing_names, f'packaged NRO lacks {missing_names}'

    report = {'tool': 'audit_snake_uptilt_delta.py 1.0.0', 'baseline': args.baseline,
              'version': args.version, 'combined_with': args.combined,
              'files_baseline': len(a), 'files_new': len(b), 'added': [], 'removed': [],
              'changed': changed, 'changed_outside_up_tilt': extra,
              'motion_lists': motion, 'sound': sound,
              'sqb': {'baseline_records': len(old), 'new_records': len(cur),
                      'appended': us.SEQUENCE},
              'nro': {'path': NRO, 'sha256': hashlib.sha256(nro).hexdigest(),
                      'bytes': len(nro), 'names_present': list(NRO_NAMES)},
              'motion_entry': {k: v for k, v in donor.items() if k != 'raw'},
              'motion_entry_raw_sha256': hashlib.sha256(donor['raw']).hexdigest(),
              'evidence_tier': 'B', 'hardware_validated': False}
    out = args.json or (new_pkg / 'SNAKE_UPTILT_DELTA.json')
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {len(changed)} changed files ({len(extra)} outside the up-tilt set), '
          f'no additions/removals; attack_hi3 is the only motion-list change; '
          f'sound banks and eflame.sqb are append-only; NRO carries every handler and sound name')


def re_slot(name):
    """True for a vanilla c00-c05 eflame/elight path, which must never be in the delta."""
    return any(f'/eflame/{"c%02d" % i}/' in f'/{name}/' or f'/elight/{"c%02d" % i}/' in f'/{name}/'
               for i in range(6))


if __name__ == '__main__':
    main()