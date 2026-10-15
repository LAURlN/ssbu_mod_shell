"""Generate owned Snake neutral-B (grenade) body motions for Pyra c06/c07 (the G&W costume).

Version 1.2.0. Donor: Snake's 13.0.4 body motion list (`refs/snake_grenade/arc/fighter/snake/
motion/body/c00/motion_list.bin`, live extraction, sha256 pinned below) and his fourteen
`special_(air_)n_*` entries' clips plus fifteen extracted `item_shoot_legs_*` clips. Donor files are
never written.

Same shape as `tools/build_hero_neutral_b_assets.py` (Hero on Mythra):

* every donor entry is copied **whole** (flags, blend, cancel frame, tail) and only its kind, its
  game/effect/sound/expression script hashes and its clip name are repointed at owned names
  `pgwr_snake_<donor kind>` / `pgwrsnake<donor kind without _>.nuanmb`. Owned names cannot collide
  with Pyra's four same-named Blazing End kinds (`special_n_start` ...), with G&W's, or with Hero's
  `pgwr_hero_*`; new names declared in `config.json` load on hardware (graveyard R-25).
* each owned motion gets its own clip file, including the two donor entries that share a clip
  (`special_n_throw_fail` = `throw_m`, `special_air_n_jump_aerial` = `air_n_hold`), so no two
  statuses depend on one file.
* the retarget keeps the donor transform tracks whose bone names exist on G&W's skeleton (the
  eflame c06/c07 body is G&W's skeleton plus grafted Pyra bones; `build_monkey_flip.py`), drops the
  donor's Visibility/Material groups and installs G&W's own idle visibility group, pinned by layout
  id. Every kept transform is compared after serialisation (tolerance and reason:
  `build_hero_spin_assets.first_difference`).

Measured 2026-09-30 (B): 87 donor tracks per clip keep 36 (`d00specialnhold` 76 -> 25: it is the
upper-body layer Snake plays over his legs). Both counts are asserted, so a changed dump or
skeleton fails the build instead of shipping a wrong pose.

Offline only: nothing here shows the clip plays on hardware. Check the log's clip end frame.

Usage: `--check` validates inputs and the entry rewrite without writing; `--output <dir>` (inside
builds/ or scratch/) writes clips + the eflame c06/c07 motion lists found there (or stock ones).
Library: `build(mod_root)` from `src/pgwr/build.py`, after `build_motion`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import shutil
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((ROOT / 'paths.toml').read_text())
ARC = ROOT / CFG['dumps']['arc']
sys.path[:0] = [str(ROOT / 'src/mgw_swap/tools'), str(ROOT / 'src/mgw_swap/tools/vendor'),
                str(ROOT / 'src/pgwr/tools')]
import ssbh_data_py as ssbh  # noqa: E402
import build_hero_spin_assets as base  # noqa: E402  (mlist codec, series comparison)
import build_monkey_flip as mflip  # noqa: E402  (G&W bones + validated idle visibility)

VERSION = '1.2.0'
DONOR_MLIST = ROOT / 'refs/snake_grenade/arc/fighter/snake/motion/body/c00/motion_list.bin'
DONOR_MLIST_SHA256 = None  # filled from refs/snake_grenade/extraction.json at run time
DONOR_CLIPS = ARC / 'fighter/snake/motion/body/c00'
SLOTS = {'c06': 'c06', 'c07': 'c07'}  # eflame slot -> gamewatch slot it was built from

# Donor kinds in the donor list's order. All fourteen are registered even though the first
# plugin stage drives only some of them: an entry costs nothing and keeps the port whole.
KINDS = (
    'special_n_start', 'special_n_hold', 'special_n_throw_lw', 'special_n_throw_m',
    'special_n_throw_hi', 'special_n_close', 'special_n_throw_fail',
    'special_air_n_start', 'special_air_n_hold', 'special_air_n_jump_aerial',
    'special_air_n_throw_lw', 'special_air_n_throw_m', 'special_air_n_throw_hi',
    'special_air_n_throw_fail',
)
EXPECTED_TRACKS = {'d00specialnhold.nuanmb': (76, 25)}
DEFAULT_TRACKS = (87, 36)
PIN_MODEL = ROOT / 'refs/snake_grenade/arc/fighter/snake/model/grenade/c00'
PIN_MOTION = ARC / 'fighter/snake/motion/grenade/c00'
PIN_KINDS = {'special_n_start': 'pgwr_snake_pin_start',
             'special_air_n_start': 'pgwr_snake_pin_air_start',
             'special_n_start_kirby': 'pgwr_snake_pin_start_kirby'}
# Packaging stays closed until common dispatch and donor lower ACMD use owned names.
LOWER_RUNTIME_TRANSLATED = True
LOWER_PARTS = ('wait', 'walk_f', 'walk_b', 'dash_f', 'dash_b', 'brake_f', 'brake_b',
               'jump_squat', 'landing', 'slow_f', 'middle_f', 'fast_f', 'slow_b', 'middle_b', 'fast_b')


def lower_dependencies():
    """Resolve lower clips by donor hashes and exact ARC index paths; no guessed filenames."""
    _, _, entries = base.parse_mlist(DONOR_MLIST)
    prefix = 'fighter/snake/motion/body/c00/'
    index = (ROOT / 'dumps/decoded/arc_files.tsv').read_text().splitlines()
    paths = [line.split('\t')[0] for line in index if line.startswith(prefix) and line.split('\t')[0].endswith('.nuanmb')]
    by_hash = {base.hash40(Path(path).name): path for path in paths}
    result = []
    for part in LOWER_PARTS:
        kind = 'item_shoot_legs_' + part
        entry = entries[base.hash40(kind)]
        assert len(entry['animations']) == 1
        path = by_hash[entry['animations'][0]]
        present = next((p for p in (ARC / path, ROOT / 'refs/snake_grenade/lower_body/arc' / path) if p.is_file()), None)
        result.append({'motion': kind, 'arc_path': path,
                       'present': present.relative_to(ROOT).as_posix() if present else None,
                       'sha256': sha(present) if present else None})
    return result


def checked_lower_inputs():
    dependencies = lower_dependencies()
    missing = [entry['arc_path'] for entry in dependencies if not entry['present']]
    assert not missing, 'Missing Snake lower-body clips; see dumps/MISSING.md: ' + ', '.join(missing)
    extraction = json.loads((ROOT / 'refs/snake_grenade/lower_body/extraction.json').read_text())
    for entry in dependencies:
        if entry['present'].startswith('refs/'):
            assert entry['sha256'] == extraction['files'][entry['arc_path']]['sha256']
    return dependencies


def pin_inputs():
    """Validate exact extracted pin files and the donor's own animation tracks."""
    report = json.loads((ROOT / 'refs/snake_grenade/extraction.json').read_text())
    models = sorted(p for p in PIN_MODEL.iterdir() if p.is_file())
    assert len(models) == 15
    for path in models:
        arc_path = 'fighter/snake/model/grenade/c00/' + path.name
        assert sha(path) == report['files'][arc_path]['sha256']
    _, _, entries = base.parse_mlist(PIN_MOTION / 'motion_list.bin')
    assert set(entries) == {base.hash40(kind) for kind in PIN_KINDS}
    files = {base.hash40(p.name): p for p in PIN_MOTION.glob('*.nuanmb')}
    assert len(files) == 3
    assert [bone.name for bone in ssbh.skel_data.read_skel(str(PIN_MODEL / 'model.nusktb')).bones] == ['Root', 'Ring', 'Trigger']
    tracks = {}
    for kind in PIN_KINDS:
        entry = entries[base.hash40(kind)]
        assert len(entry['animations']) == 1 and entry['animations'][0] in files
        anim = ssbh.anim_data.read_anim(str(files[entry['animations'][0]]))
        # The donor itself animates the two pin meshes through their bones.
        tracks[kind] = {group.group_type.name: [node.name for node in group.nodes] for group in anim.groups}
        assert tracks[kind] == {'Transform': ['Ring', 'Trigger']}
    return models, files, entries, tracks


def build_pin(mod_root):
    models, clips, entries, tracks = pin_inputs()
    source_list = PIN_MOTION / 'motion_list.bin'
    magic, path, _ = base.parse_mlist(source_list)
    owned_entries = {}
    for original, owned_kind in PIN_KINDS.items():
        entry = entries[base.hash40(original)]
        raw = bytearray(entry['raw'])
        struct.pack_into('<Q', raw, 0, base.hash40(owned_kind))
        owned_entries[base.hash40(owned_kind)] = {**entry, 'raw': bytes(raw)}
    list_bytes = base.encode_mlist(magic, path, owned_entries)
    records = []
    for slot_id in range(8):
        slot = f'c{slot_id:02}'
        for category, sources in [('model', models), ('motion', sorted(clips.values()))]:
            for source in sources:
                rel = f'fighter/eflame/{category}/pgwr_snake_pin/{slot}/{source.name}'
                dest = mod_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
                assert source.read_bytes() == dest.read_bytes()
                records.append({'path': rel, 'sha256': sha(dest), 'source': source.relative_to(ROOT).as_posix()})
        rel = f'fighter/eflame/motion/pgwr_snake_pin/{slot}/motion_list.bin'
        dest = mod_root / rel
        dest.write_bytes(list_bytes)
        loaded = base.parse_mlist(dest)
        assert base.encode_mlist(*loaded) == list_bytes
        records.append({'path': rel, 'sha256': sha(dest), 'source': source_list.relative_to(ROOT).as_posix(),
                        'source_sha256': sha(source_list), 'rewrite': 'motion kinds only'})
    return records, tracks


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def owned(kind: str) -> str:
    return 'pgwr_snake_' + kind


def clip_name(kind: str) -> str:
    return owned(kind).replace('_', '') + '.nuanmb'


def motions():
    """Primary and lower-body registrations, all with owned names."""
    return [(k, owned(k), clip_name(k)) for k in KINDS + tuple('item_shoot_legs_' + part for part in LOWER_PARTS)]


def donor_mlist_sha() -> str:
    report = json.loads((ROOT / 'refs/snake_grenade/extraction.json').read_text())
    rel = 'fighter/snake/motion/body/c00/motion_list.bin'
    return report['files'][rel]['sha256']


def checked_inputs():
    """The donor entries, each with its single clip resolved to a file in dumps/."""
    assert sha(DONOR_MLIST) == donor_mlist_sha(), 'Snake motion list does not match its extraction record'
    _, _, donor = base.parse_mlist(DONOR_MLIST)
    files = {base.hash40(p.name): p for p in DONOR_CLIPS.glob('*.nuanmb')}
    out = {}
    for kind in KINDS:
        entry = donor.get(base.hash40(kind))
        assert entry is not None, f'donor list has no {kind}'
        assert len(entry['animations']) == 1, kind
        assert entry['game_script'] == base.hash40('game_' + kind.replace('_', '')), kind
        src = files.get(entry['animations'][0])
        assert src is not None, f'{kind}: donor clip not in {DONOR_CLIPS}'
        out[kind] = (entry, src)
    for dependency in checked_lower_inputs():
        kind = dependency['motion']
        out[kind] = (donor[base.hash40(kind)], ROOT / dependency['present'])
    return out


def entry_bytes(entry, owned_kind, clip):
    """The donor entry with kind, scripts and clip repointed; everything else byte-identical."""
    raw = bytearray(entry['raw'])
    stem = owned_kind.replace('_', '')
    struct.pack_into('<QQ', raw, 0, base.hash40(owned_kind), base.hash40('game_' + stem))
    struct.pack_into('<Q', raw, 24, base.hash40(clip))
    tail = (24 + len(entry['animations']) * 9 + 3) & ~3
    if entry['size'] >= 24:
        for index, category in enumerate(('expression', 'sound', 'effect')):
            if struct.unpack_from('<Q', raw, tail + index * 8)[0]:
                struct.pack_into('<Q', raw, tail + index * 8, base.hash40(f'{category}_{stem}'))
    out = bytes(raw)
    # Only the repointed fields may differ from the donor.
    changed = [i for i in range(len(out)) if out[i] != entry['raw'][i]]
    allowed = set(range(0, 16)) | set(range(24, 32)) | set(range(tail, tail + 24))
    assert set(changed) <= allowed, (owned_kind, changed)
    return out


def retarget(src: Path, dest: Path, bones: set, vis_group) -> dict:
    anim = ssbh.anim_data.read_anim(str(src))
    groups = base.groups_by_type(anim)
    for required in ('Transform', 'Visibility'):
        assert required in groups, f'{src.name}: no {required} group'
    donor_nodes = list(groups['Transform'].nodes)
    kept = [n for n in donor_nodes if n.name in bones]
    want = EXPECTED_TRACKS.get(src.name, DEFAULT_TRACKS)
    assert (len(donor_nodes), len(kept)) == want, (src.name, len(donor_nodes), len(kept), want)
    groups['Transform'].nodes = kept
    intended = base.collapse_series(base.node_series(kept))
    frames = int(round(anim.final_frame_index)) + 1
    anim.groups = [groups['Transform'], mflip._donor.build_visibility_group(vis_group, frames)]
    dest.parent.mkdir(parents=True, exist_ok=True)
    anim.save(str(dest))
    reread = ssbh.anim_data.read_anim(str(dest))
    found = base.groups_by_type(reread)
    assert set(found) == {'Transform', 'Visibility'}, (dest.name, sorted(found))
    assert reread.final_frame_index == anim.final_frame_index, dest.name
    observed = base.collapse_series(base.node_series(found['Transform'].nodes))
    assert intended.keys() == observed.keys(), dest.name
    for name in intended:
        diff = base.first_difference(name, intended[name], observed[name])
        assert diff is None, (src.name, diff)
    return {'clip': dest.name, 'donor': src.relative_to(ROOT).as_posix(), 'donor_sha256': sha(src),
            'sha256': sha(dest), 'end_frame': reread.final_frame_index,
            'transform_tracks_in': len(donor_nodes), 'transform_tracks_kept': len(kept),
            'dropped_bones': sorted(n.name for n in donor_nodes if n.name not in bones)}


def build(mod_root) -> dict:
    """Write clips and extend the eflame c06/c07 lists already under `mod_root` (or stock ones)."""
    mod_root = Path(mod_root).resolve()
    inputs = checked_inputs()
    records = []
    for slot, gw_slot in SLOTS.items():
        folder = mod_root / 'fighter/eflame/motion/body' / slot
        mlist = folder / 'motion_list.bin'
        magic, path, entries = base.parse_mlist(
            mlist if mlist.exists() else ARC / 'fighter/eflame/motion/body' / slot / 'motion_list.bin')
        clashes = [o for _, o, _ in motions() if base.hash40(o) in entries]
        assert not clashes, f'{slot}: owned kinds already present {clashes}'
        bones = set(mflip.recipient_bones(gw_slot))
        vis = mflip.visibility_group(gw_slot)
        existing = {base.hash40(p.name) for p in folder.glob('*.nuanmb')}
        for kind, owned_kind, clip in motions():
            assert base.hash40(clip) not in existing, f'{slot}: {clip} would overwrite a file'
            entry, src = inputs[kind]
            rec = retarget(src, folder / clip, bones, vis)
            entries[base.hash40(owned_kind)] = {**entry, 'raw': entry_bytes(entry, owned_kind, clip)}
            rec.update({'slot': slot, 'motion': owned_kind, 'donor_kind': kind,
                        'cancel': entry['cancel'], 'flags': entry['flags'], 'blend': entry['blend']})
            records.append(rec)
        mlist.parent.mkdir(parents=True, exist_ok=True)
        mlist.write_bytes(base.encode_mlist(magic, path, entries))
        loaded = base.parse_mlist(mlist)
        assert base.encode_mlist(*loaded) == mlist.read_bytes(), slot
        for kind, owned_kind, clip in motions():
            got = loaded[2][base.hash40(owned_kind)]
            assert got['animations'] == (base.hash40(clip),), (slot, owned_kind)
            assert got['cancel'] == inputs[kind][0]['cancel'], (slot, owned_kind)
    pin_files, pin_tracks = build_pin(mod_root)
    return {'date': '2026-09-30', 'tool_version': VERSION, 'evidence_tier': 'B',
            'hardware_validated': False, 'donor_motion_list_sha256': sha(DONOR_MLIST),
            'motions': records, 'pin_files': pin_files, 'pin_donor_tracks': pin_tracks}


def declared_clips():
    """(slot, relative path) of every new file `build` writes, for config.json."""
    return [(slot, f'fighter/eflame/motion/body/{slot}/{clip}')
            for slot in SLOTS for _, _, clip in motions()]


def declared_pin_files():
    models, clips, _, _ = pin_inputs()
    return [(f'c{i:02}', f'fighter/eflame/{kind}/pgwr_snake_pin/c{i:02}/{name}')
            for i in range(8) for kind, names in (
                ('model', [p.name for p in models]),
                ('motion', [p.name for p in sorted(clips.values())] + ['motion_list.bin']))
            for name in names]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    if args.check:
        pin_inputs()
        inputs = checked_inputs()
        for kind, (entry, _) in inputs.items():
            entry_bytes(entry, owned(kind), clip_name(kind))
        magic, path, donor = base.parse_mlist(DONOR_MLIST)
        assert base.encode_mlist(magic, path, donor) == DONOR_MLIST.read_bytes()
        print(f'PASS: {len(inputs)} donor registrations, clips resolved, entry rewrite confined, list round trip')
        return
    if not args.output:
        ap.error('choose --check or --output')
    out = args.output.resolve()
    assert any(out.is_relative_to(ROOT / d) for d in ('builds', 'scratch')), out
    record = build(out)
    (out / 'snake_neutral_b_assets.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f"Validated {len(record['motions'])} retargeted clips")


if __name__ == '__main__':
    main()
