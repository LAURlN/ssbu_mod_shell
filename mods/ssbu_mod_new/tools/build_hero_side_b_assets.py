"""Prepare owned Hero side-B motions without altering dumps or the live package.

Version 1.0.0. --check checks pinned inputs, every retained body Transform track,
new motion/script names, exact donor flags/tails and article lists without writing
assets. --output is for a separately authorized package operation. Retarget by
case-sensitive model bone name; body Sword1 is not an esword pose (R-21).
Smoke test: toolchains/py312/python.exe tools/build_hero_side_b_assets.py --check.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((ROOT / 'paths.toml').read_text())
ARC = ROOT / CFG['dumps']['arc']
REF = ROOT / 'refs/brave_special_s'
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src/mgw_swap/tools'),
               str(ROOT / 'src/mgw_swap/tools/vendor')]
import ssbh_data_py as ssbh
from build_hero_neutral_b_assets import base, entry_bytes

VERSION = '1.0.0'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def motions():
    for air in (False, True):
        for phase in ('start', 'hold', '1', '2', '3', '32'):
            donor = ('special_air_s' if air else 'special_s')
            donor += ('_' if phase.isalpha() else '') + phase
            owned = 'pgwr_hero_' + donor
            yield donor, owned, owned.replace('_', '') + '.nuanmb'


def checked_inputs():
    extraction = json.loads((REF / 'extraction.json').read_text())['files']
    article = REF / 'article_motions'
    article_files = json.loads((article / 'extraction.json').read_text())['files']
    result = {}
    for slot in ('c06', 'c07'):
        donor_dir = REF / 'arc/fighter/brave/motion/body' / slot
        mlist = donor_dir / 'motion_list.bin'
        magic, path, entries = base.parse_mlist(mlist)
        assert base.encode_mlist(magic, path, entries) == mlist.read_bytes()
        assert sha(mlist) == extraction[mlist.relative_to(REF / 'arc').as_posix()]['sha256']
        bones = {b.name for b in ssbh.skel_data.read_skel(str(
            ARC / 'fighter/elight/model/body' / slot / 'model.nusktb')).bones}
        phases = []
        for name, owned, clip in motions():
            entry = entries[base.hash40(name)]
            assert len(entry['animations']) == 1, name
            candidates = [p for p in donor_dir.glob('*.nuanmb')
                          if base.hash40(p.name) == entry['animations'][0]]
            assert len(candidates) == 1, name
            src = candidates[0]
            assert sha(src) == extraction[src.relative_to(REF / 'arc').as_posix()]['sha256']
            groups = base.groups_by_type(ssbh.anim_data.read_anim(str(src)))
            nodes = list(groups['Transform'].nodes)
            kept = [node for node in nodes if node.name in bones]
            dropped = sorted(node.name for node in nodes if node.name not in bones)
            assert (len(nodes), len(kept), len(dropped)) == (125, 68, 57), src
            assert len([name for name in dropped if name.startswith('S_Mantle')]) == 12
            assert len([name for name in dropped if name.startswith('S_Skirt')]) == 40
            raw = entry_bytes(entry, owned, clip)
            # Every byte except explicit motion/script/clip hash replacements survives.
            assert raw[16:24] == entry['raw'][16:24]
            assert raw[32:36] == entry['raw'][32:36]
            assert raw[60:] == entry['raw'][60:]
            phases.append((src, entry, raw, owned, clip))
        result[slot] = phases
    for rel, record in article_files.items():
        src = article / 'arc' / rel
        assert sha(src) == record['sha256'] and src.stat().st_size == record['bytes']
        parsed = base.parse_mlist(src)
        assert base.encode_mlist(*parsed) == src.read_bytes()
        assert all(not entry['animations'] for entry in parsed[2].values())
    expected = {f'fighter/brave/motion/{kind}/c{slot:02d}/motion_list.bin'
                for kind in ('spark', 'lightning') for slot in range(8)}
    assert set(article_files) == expected
    return result, article_files


def build(output):
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / folder) for folder in ('builds', 'scratch'))
    phases, article_files = checked_inputs()
    records = []
    for slot, rows in phases.items():
        stock = ARC / 'fighter/elight/motion/body' / slot
        folder = output / 'fighter/elight/motion/body' / slot
        folder.mkdir(parents=True, exist_ok=True)
        mlist = folder / 'motion_list.bin'
        magic, path, entries = base.parse_mlist(mlist if mlist.is_file() else stock / 'motion_list.bin')
        bones = {b.name for b in ssbh.skel_data.read_skel(str(
            ARC / 'fighter/elight/model/body' / slot / 'model.nusktb')).bones}
        idle = base.groups_by_type(ssbh.anim_data.read_anim(str(stock / 'a00wait1.nuanmb')))
        for src, entry, raw, owned, clip in rows:
            anim = ssbh.anim_data.read_anim(str(src))
            transforms = base.groups_by_type(anim)['Transform']
            original = list(transforms.nodes)
            transforms.nodes = [node for node in original if node.name in bones]
            intended = base.collapse_series(base.node_series(transforms.nodes))
            frames = int(round(anim.final_frame_index)) + 1
            anim.groups = [transforms] + [base.build_group(idle[kind], frames)
                for kind in ('Visibility', 'Material') if kind in idle]
            dest = folder / clip
            anim.save(str(dest))
            reread = ssbh.anim_data.read_anim(str(dest))
            observed = base.collapse_series(base.node_series(base.groups_by_type(reread)['Transform'].nodes))
            assert intended.keys() == observed.keys()
            assert all(base.first_difference(name, intended[name], observed[name]) is None for name in intended)
            assert reread.final_frame_index == anim.final_frame_index
            entries[base.hash40(owned)] = {**entry, 'raw': raw}
            records.append({'slot': slot, 'motion': owned, 'clip': clip,
                'input': src.relative_to(ROOT).as_posix(), 'input_sha256': sha(src),
                'sha256': sha(dest), 'end_frame': anim.final_frame_index,
                'kept_bones': len(transforms.nodes), 'dropped_bones': sorted(
                    node.name for node in original if node.name not in bones)})
        mlist.write_bytes(base.encode_mlist(magic, path, entries))
        assert base.encode_mlist(*base.parse_mlist(mlist)) == mlist.read_bytes()
    for rel in article_files:
        src = REF / 'article_motions/arc' / rel
        parts = Path(rel).parts
        dest = output.joinpath('fighter', 'elight', 'motion', 'pgwr_hero_' + parts[3], *parts[4:])
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        assert sha(src) == sha(dest)
    report = {'date': '2026-09-30', 'tool_version': VERSION, 'tier': 'B',
              'hardware_validated': False, 'body_motions': records, 'article_files': article_files}
    (output / 'hero_side_b_assets.json').write_text(json.dumps(report, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.check:
        checked_inputs()
        print('PASS: 24 pinned body clips, exact 68/57 bone partitions, owned motion entries and 16 article lists; no assets written')
    elif args.output:
        build(args.output)
    else:
        parser.error('choose --check or separately authorized --output')


if __name__ == '__main__':
    main()
