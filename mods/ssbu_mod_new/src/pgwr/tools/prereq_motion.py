"""Pre-flight for the prerequisite: one new G&W motion kind on eflame c06/c07.

Answers, from the dumps only:
  * is `special_s_1` absent from eflame's motion list (so adding it is a real
    addition, not an overwrite)?
  * what does G&W's own `special_s_1` entry look like, and which clip does it
    name? Does that clip exist in both of G&W's c06 and c07?
  * does that clip carry a Visibility group, and which meshes does it toggle?
    This decides whether the pose will be right with a verbatim copy.
  * does eflame c06 already contain every clip its own motion list references?
    A "no" here is the failure class the old swap hit (a motion entry naming a
    file that exists nowhere).
"""
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
EXPORT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'dumps' / 'arc')

sys.path.insert(0, str(ROOT / 'toolchains' / 'py312' / 'Lib' / 'site-packages'))
import ssbh_data_py as s  # noqa: E402

TARGET = 'special_s_1'


def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def parse_mlist(path):
    data = Path(path).read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data)
    assert magic == hash40('motion'), f'bad magic in {path}'
    offset, motions = 24, {}
    for _ in range(count):
        start = offset
        kind, _gs, _flags, _blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        assert n_anims <= 3 and size % 8 in (0, 4), f'bad entry at {offset:#x} in {path}'
        offset += 24
        names = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        assert end <= len(data), f'truncated entry in {path}'
        motions[kind] = {'raw': data[start:end], 'anims': names, 'size': size}
        offset = end
    assert offset == len(data), f'trailing data in {path}'
    return motion_path, motions


def main():
    # 1. Is the kind absent from eflame, and what does G&W's entry look like?
    for slot in ('c06', 'c07'):
        eflame_dir = EXPORT / 'fighter/eflame/motion/body' / slot
        _path, eflame = parse_mlist(eflame_dir / 'motion_list.bin')
        print(f'eflame {slot}: {len(eflame)} entries, '
              f'special_s_1 present={hash40(TARGET) in eflame}')

        gw_dir = EXPORT / 'fighter/gamewatch/motion/body' / slot
        _path, gw = parse_mlist(gw_dir / 'motion_list.bin')
        entry = gw.get(hash40(TARGET))
        if entry is None:
            print(f'  gamewatch {slot}: NO {TARGET} entry')
            continue
        print(f'  gamewatch {slot}: {TARGET} -> '
              f'{[hex(a) for a in entry["anims"]]} size={entry["size"]}')

        # 2. Do those clips exist on both sides?
        for anim in entry['anims']:
            hit = [p for p in gw_dir.glob('*.nuanmb') if hash40(p.name) == anim]
            print(f'    clip {hit[0].name if hit else "<missing>"}: '
                  f'gamewatch/{slot} exists={bool(hit)} '
                  f'eflame/{slot} exists='
                  f'{any(hash40(p.name) == anim for p in eflame_dir.glob("*.nuanmb"))}')
            if not hit:
                continue
            # 3. Visibility coverage of that clip.
            anim_data = s.anim_data.read_anim(str(hit[0]))
            vis = [g for g in anim_data.groups if g.group_type.name == 'Visibility']
            print(f'    groups={[g.name for g in anim_data.groups]}')
            for group in vis:
                on = [n.name for n in group.nodes
                      if n.tracks and n.tracks[0].values[0]]
                print(f'    visibility group {group.name!r}: '
                      f'{len(group.nodes)} nodes, on at frame 0: {sorted(on)}')

    # 4. The old failure class: does eflame c06 already cover its own list?
    for slot in ('c06', 'c07'):
        d = EXPORT / 'fighter/eflame/motion/body' / slot
        have = {hash40(p.name) for p in d.glob('*.nuanmb')}
        _path, motions = parse_mlist(d / 'motion_list.bin')
        missing = sorted({a for e in motions.values() for a in e['anims']} - have)
        print(f'eflame {slot}: clips referenced but absent from the folder: '
              f'{len(missing)} {[hex(m) for m in missing]}')


if __name__ == '__main__':
    main()
