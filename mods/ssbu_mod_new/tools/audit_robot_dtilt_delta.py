"""Audit a pgwr package against its baseline for the R.O.B. down-tilt change (v1.0.0).

    toolchains/py312/python.exe tools/audit_robot_dtilt_delta.py --baseline 0.20.11 --version 0.20.12

Proves, from the packaged bytes (tier B, offline; nothing here says how the move plays):
  * the file-level delta is exactly the intended set (no additions/removals);
  * c06/c07 motion lists differ from the baseline only in the `attack_lw3` entry, which equals
    R.O.B.'s raw donor entry; every other entry is byte-identical;
  * the retargeted clip exists for both slots with the pinned donor node subset and 29 frames;
  * the se/vc banks retain every baseline tone (names and sample bytes) and gain exactly the
    donor tones; eflame.sqb retains every baseline record and gains exactly the donor record;
  * c00-c05 Pyra files are untouched (they are not in the package delta at all).
Writes `ROBOT_DTILT_DELTA.json` in the new package.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import merge_hero_neutral_b_sound as codec  # noqa: E402
import merge_robot_dtilt_sound as rs  # noqa: E402
import build_robot_dtilt as rd  # noqa: E402
import ssbh_data_py as s  # noqa: E402

MOD = 'ultimate/mods/pyra_gamewatch_reskin'


def tree(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}


def entries(path):
    data = Path(path).read_bytes()
    _, _, count = __import__('struct').unpack_from('<QQQ', data, 0)
    import struct
    off, out = 24, {}
    for _ in range(count):
        start = off
        kind, _gs, _fl, _bl, n, size = struct.unpack_from('<QQHBBI', data, off)
        off = (off + 24 + n * 9 + 3) & ~3
        out[kind] = data[start:off + size]
        off += size
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', required=True)
    ap.add_argument('--version', required=True)
    args = ap.parse_args()
    base = ROOT / 'builds/pgwr' / args.baseline / MOD
    new_pkg = ROOT / 'builds/pgwr' / args.version
    new = new_pkg / MOD
    a, b = tree(base), tree(new)
    assert set(a) == set(b), (sorted(set(a) ^ set(b)))
    changed = sorted(k for k in a if a[k] != b[k])
    expected = {'info.toml', 'sound/sequence/fighter/eflame.sqb'}
    for slot in ('c06', 'c07'):
        expected |= {f'fighter/eflame/motion/body/{slot}/{f}' for f in ('motion_list.bin', rd.CLIP)}
        for folder, prefix in (('fighter', 'se'), ('fighter_voice', 'vc')):
            expected |= {f'sound/bank/{folder}/{prefix}_eflame_{slot}{e}' for e in ('.nus3audio', '.nus3bank', '.tonelabel')}
    assert set(changed) == expected, (sorted(set(changed) ^ expected))

    kind = rd.hash40(rd.KIND)
    donor = rd.get_entry()
    motion = {}
    for slot in ('c06', 'c07'):
        old = entries(base / f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        cur = entries(new / f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        assert set(old) == set(cur)
        diff = [k for k in old if old[k] != cur[k]]
        assert diff == [kind] and cur[kind] == donor['raw'], diff
        anim = s.anim_data.read_anim(str(new / f'fighter/eflame/motion/body/{slot}/{rd.CLIP}'))
        t = next(g for g in anim.groups if g.group_type.name == 'Transform')
        assert len(t.nodes) == 11 and len(t.nodes[0].tracks[0].values) == 29
        motion[slot] = {'entries': len(cur), 'changed_kinds': [hex(k) for k in diff],
                        'clip_sha256': b[f'fighter/eflame/motion/body/{slot}/{rd.CLIP}'],
                        'transform_nodes': sorted(n.name for n in t.nodes)}

    sound = {}
    for slot in ('c06', 'c07'):
        for folder, prefix, added in (('fighter', 'se', rs.SE_REQUIRED),
                                      ('fighter_voice', 'vc', {f'vc_robot_attack0{i}' for i in range(1, 5)})):
            stem = f'sound/bank/{folder}/{prefix}_eflame_{slot}'
            old = codec.audio_read((base / (stem + '.nus3audio')).read_bytes())
            cur = codec.audio_read((new / (stem + '.nus3audio')).read_bytes())
            assert cur[:len(old)] == old, f'{stem}: a baseline tone changed or moved'
            assert {n.lower() for n, _ in cur[len(old):]} == added, stem
            sound[f'{folder}/{slot}'] = {'retained': len(old), 'appended': sorted(n for n, _ in cur[len(old):])}
    old = codec.sqb_read((base / 'sound/sequence/fighter/eflame.sqb').read_bytes())
    cur = codec.sqb_read((new / 'sound/sequence/fighter/eflame.sqb').read_bytes())
    assert cur[:len(old)] == old and cur[len(old):] == [rs.sequence_record()]
    assert len(cur) == len(old) + 1

    report = {'tool': 'audit_robot_dtilt_delta.py 1.0.0', 'baseline': args.baseline, 'version': args.version,
              'files_baseline': len(a), 'files_new': len(b), 'added': [], 'removed': [],
              'changed': changed, 'motion_lists': motion, 'sound': sound,
              'sqb': {'baseline_records': len(old), 'new_records': len(cur), 'appended': rs.SEQUENCE},
              'evidence_tier': 'B', 'hardware_validated': False}
    (new_pkg / 'ROBOT_DTILT_DELTA.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {len(changed)} changed files, no additions/removals; attack_lw3 is the only motion-list change; '
          f'sound and sqb are append-only')


if __name__ == '__main__':
    main()
