"""Generate owned Hero neutral-B motions and fireball assets for Mythra.

Version 1.0.0. Uses the pinned inventory in refs/brave_special_n/SOURCE.json.
Donor dumps are never written. Body motion names, scripts and clip names are
new; donor entry timing is preserved. Recipient visibility/material tracks
come from the recipient idle, not from Hero's model. Every retained transform
is compared after SSBH serialization. This is offline validation only.

Smoke test: --check validates inputs, thirteen donor registrations and round-trip
motion-list encoding without generating a package. --output must point inside
builds/ or scratch/. Generated files are recorded in hero_neutral_b_assets.json.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((ROOT / 'paths.toml').read_text())
ARC = ROOT / CFG['dumps']['arc']
sys.path[:0] = [str(ROOT / 'src/mgw_swap/tools'),
               str(ROOT / 'src/mgw_swap/tools/vendor')]
import ssbh_data_py as ssbh
import build_hero_spin_assets as base

VERSION = '1.0.0'
PHASES = ('start', 'hold', 'cancel', '1', '2', '3')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def motions():
    for air in (False, True):
        for phase in PHASES:
            donor = ('special_air_n' if air else 'special_n')
            donor += ('_' if phase.isalpha() else '') + phase
            owned = 'pgwr_hero_' + donor
            yield donor, owned, owned.replace('_', '') + '.nuanmb'
    # Hero's jump-cancel entry shares the air cancel clip but owns its scripts.
    donor = 'special_air_n_jump_cancel'
    owned = 'pgwr_hero_' + donor
    yield donor, owned, owned.replace('_', '') + '.nuanmb'


def checked_inputs():
    source = json.loads((ROOT / 'refs/brave_special_n/SOURCE.json').read_text())
    _, _, donor = base.parse_mlist(ROOT / 'refs/brave_special_n/motion_list.bin')
    for name, _, _ in motions():
        entry = donor[base.hash40(name)]
        assert len(entry['animations']) == 1, name
        candidates = [p for p in (ARC / 'fighter/brave/motion/body/c00').glob('*.nuanmb')
                      if base.hash40(p.name) == entry['animations'][0]]
        assert len(candidates) == 1, name
        path = candidates[0]
        assert sha(path) == source['inputs'][path.relative_to(ROOT).as_posix()]['sha256'], path
    return source, donor


def entry_bytes(entry, owned, clip):
    raw = bytearray(entry['raw'])
    # Keep flags, blend, timing tail and animation auxiliary bytes unchanged.
    struct.pack_into('<QQ', raw, 0, base.hash40(owned), base.hash40('game_' + owned.replace('_', '')))
    struct.pack_into('<Q', raw, 24, base.hash40(clip))
    tail = (24 + len(entry['animations']) * 9 + 3) & ~3
    if entry['size'] >= 24:
        for index, category in enumerate(('expression', 'sound', 'effect')):
            if struct.unpack_from('<Q', raw, tail + index * 8)[0]:
                struct.pack_into('<Q', raw, tail + index * 8,
                                 base.hash40(category + '_' + owned.replace('_', '')))
    return bytes(raw)


def build(output):
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / name) for name in ('builds', 'scratch')), output
    source, donor = checked_inputs()
    records = []
    for slot in ('c06', 'c07'):
        folder = output / 'fighter/elight/motion/body' / slot
        folder.mkdir(parents=True, exist_ok=True)
        stock = ARC / 'fighter/elight/motion/body' / slot
        # Preserve entries produced by another move generator if this is a package.
        mlist = folder / 'motion_list.bin'
        magic, path, entries = base.parse_mlist(mlist if mlist.exists() else stock / 'motion_list.bin')
        skeleton = ssbh.skel_data.read_skel(str(ARC / 'fighter/elight/model/body' / slot / 'model.nusktb'))
        bones = {b.name for b in skeleton.bones}
        idle = ssbh.anim_data.read_anim(str(stock / 'a00wait1.nuanmb'))
        recipient_groups = base.groups_by_type(idle)
        for donor_name, owned, clip in motions():
            original_entry = donor[base.hash40(donor_name)]
            src = next(p for p in (ARC / 'fighter/brave/motion/body/c00').glob('*.nuanmb')
                       if base.hash40(p.name) == original_entry['animations'][0])
            anim = ssbh.anim_data.read_anim(str(src))
            groups = base.groups_by_type(anim)
            transforms = groups['Transform']
            original_nodes = list(transforms.nodes)
            transforms.nodes = [n for n in original_nodes if n.name in bones]
            intended = base.collapse_series(base.node_series(transforms.nodes))
            frames = int(round(anim.final_frame_index)) + 1
            anim.groups = [transforms] + [base.build_group(recipient_groups[g], frames)
                                        for g in ('Visibility', 'Material') if g in recipient_groups]
            dest = folder / clip
            anim.save(str(dest))
            reread = ssbh.anim_data.read_anim(str(dest))
            observed = base.collapse_series(base.node_series(base.groups_by_type(reread)['Transform'].nodes))
            assert intended.keys() == observed.keys()
            for name in intended:
                difference = base.first_difference(name, intended[name], observed[name])
                assert difference is None, (src.name, difference)
            assert reread.final_frame_index == anim.final_frame_index
            raw = entry_bytes(original_entry, owned, clip)
            entries[base.hash40(owned)] = {**original_entry, 'raw': raw}
            records.append({'slot': slot, 'motion': owned, 'clip': clip,
                            'donor': src.relative_to(ROOT).as_posix(), 'donor_sha256': sha(src),
                            'sha256': sha(dest), 'end_frame': reread.final_frame_index,
                            'kept_bones': len(transforms.nodes),
                            'dropped_bones': sorted(n.name for n in original_nodes if n.name not in bones),
                            'cancel': original_entry['cancel'], 'flags': original_entry['flags']})
        mlist.write_bytes(base.encode_mlist(magic, path, entries))
        loaded = base.parse_mlist(mlist)
        assert base.encode_mlist(*loaded) == mlist.read_bytes()
        for _, owned, clip in motions():
            assert loaded[2][base.hash40(owned)]['animations'] == (base.hash40(clip),)
    article = []
    for slot_id in range(8):
        slot = f'c{slot_id:02}'
        for kind in ('model', 'motion'):
            donor_dir = ARC / 'fighter/brave' / kind / 'fireball' / slot
            for src in sorted(donor_dir.rglob('*')):
                if not src.is_file():
                    continue
                relative = Path('fighter/elight') / kind / 'pgwr_hero_fireball' / slot / src.relative_to(donor_dir)
                dest = output / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
                assert sha(src) == sha(dest)
                article.append({'path': relative.as_posix(), 'sha256': sha(dest)})
    record = {'date': '2026-09-30', 'tool_version': VERSION, 'evidence_tier': 'B',
              'hardware_validated': False, 'source_sha256': sha(ROOT / 'refs/brave_special_n/SOURCE.json'),
              'motions': records, 'article_files': article}
    (output / 'hero_neutral_b_assets.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.check:
        _, entries = checked_inputs()
        magic, path, original = base.parse_mlist(ROOT / 'refs/brave_special_n/motion_list.bin')
        assert base.encode_mlist(magic, path, original) == (ROOT / 'refs/brave_special_n/motion_list.bin').read_bytes()
        print('PASS: thirteen donor motion registrations, twelve pinned clips, motion-list round trip')
    elif args.output:
        record = build(args.output)
        print(f"Validated {len(record['motions'])} retargeted clips and {len(record['article_files'])} article files")
    else:
        parser.error('choose --check or --output')


if __name__ == '__main__':
    main()
