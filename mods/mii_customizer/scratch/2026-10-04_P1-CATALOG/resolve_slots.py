"""P1-CATALOG scratch: resolve motion-list hashes to names for the Gunner (c00 body).

Joins, all by hash40, none of them a guess:

1. ParamLabels.csv (mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv), the label
   table the mod repo already uses for parameter hashes.
2. A fixed candidate list in the game's `snake_case` convention.
3. For kinds still unresolved: the entry's own clip name with its letter/digit
   prefix stripped, and every placement of up to four underscores in the
   remainder, each checked against the entry's kind hash. A name only appears in
   the output when its hash equals the file's, so this is a measured match.
   Where two placements collide the shortest name is kept and the collision is
   reported.

Game scripts resolve as hash40("game_" + kind_name_without_underscores), which is
checked per entry, not assumed.

Usage (workspace root):
  python mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/resolve_slots.py
"""
import itertools
import json
import os
import re
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
EVID = os.path.join(ROOT, 'mods', 'mii_customizer', 'evidence', 'P1-CATALOG')
LABELS = os.path.join(ROOT, 'mods', 'ssbu_mod_new', 'dumps', 'scripts', 'ParamLabels.csv')


def hash40(name):
    b = name.encode('utf-8')
    return (len(b) << 32) | zlib.crc32(b)


def load_labels():
    lab = {}
    with open(LABELS, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            h, _, n = line.partition(',')
            try:
                lab[int(h, 16)] = n
            except ValueError:
                pass
    return lab


def fixed_candidates():
    out = set()
    stems = ['attack', 'landing', 'special', 'throw', 'thrown', 'catch', 'capture',
             'damage', 'guard', 'fall', 'jump', 'step', 'wait', 'walk', 'run', 'dash',
             'turn', 'squat', 'escape', 'rebound', 'share', 'win', 'lose', 'menu',
             'appeal', 'swim', 'entry', 'sleep', 'down', 'cliff', 'passive', 'slip',
             'getup', 'rise', 'bounce', 'stop', 'item', 'swing', 'furafura',
             'swallowed', 'camerahit', 'edgecancelslide', 'misc', 'ladder']
    suffixes = ['', '_n', '_f', '_b', '_hi', '_lw', '_n_start', '_n_loop', '_n_end',
                '_n_hold', '_n_cancel', '_n_fire', '_n_fire_max', '_n1', '_n2', '_n3',
                '_n1_start', '_n1_loop', '_n1_end', '_n1_hold', '_n1_cancel',
                '_n1_fire', '_n1_fire_max', '_n1_jump_cancel',
                '_n2_start', '_n2_loop', '_n2_end', '_n3_start', '_n3_end',
                '_air_n', '_air_f', '_air_b', '_air_hi', '_air_lw',
                '_air_n_start', '_air_n_loop', '_air_n_end', '_air_n_hold',
                '_air_n_cancel', '_air_n_fire', '_air_n_fire_max',
                '_air_n_jump_cancel', '_air_n1', '_air_n1_start', '_air_n1_loop',
                '_air_n1_end', '_air_n1_hold', '_air_n1_cancel', '_air_n1_fire',
                '_air_n1_fire_max', '_air_n1_jump_cancel', '_air_n2_start',
                '_air_n2_loop', '_air_n2_end', '_air_n3_start', '_air_n3_end',
                '_s', '_s1', '_s2', '_s3', '_s1_1', '_s1_2', '_s2_start',
                '_s2_loop', '_s2_end', '_s3_1', '_s3_2',
                '_air_s', '_air_s1', '_air_s2', '_air_s2_start', '_air_s2_loop',
                '_air_s2_end', '_air_s3_1', '_air_s3_2',
                '_hi', '_hi1', '_hi2', '_hi3', '_hi2_squat', '_hi3_start', '_hi3_end',
                '_hi3_b', '_hi3_f',
                '_air_hi', '_air_hi1', '_air_hi2_squat', '_air_hi3_start',
                '_air_hi3_end',
                '_lw', '_lw1', '_lw2', '_lw3', '_lw1_start', '_lw1_loop', '_lw1_hit',
                '_lw1_end', '_lw1_start_l', '_lw1_loop_l', '_lw1_hit_l', '_lw1_end_l',
                '_lw3_start', '_lw3_hold', '_lw3_hit', '_lw3_end',
                '_air_lw', '_air_lw1', '_air_lw2', '_air_lw3', '_air_lw1_start',
                '_air_lw1_loop', '_air_lw1_hit', '_air_lw1_end', '_air_lw1_start_l',
                '_air_lw1_loop_l', '_air_lw1_hit_l', '_air_lw1_end_l',
                '_air_lw3_start', '_air_lw3_hold', '_air_lw3_hit', '_air_lw3_end',
                '_light', '_heavy', '_wait', '_wait1', '_wait2', '_dash', '_turn',
                '_up', '_down', '_attack', '_attack_u', '_attack_d', '_attack_quick',
                '_pulled_hi', '_pulled_lw', '_wait_hi', '_wait_lw', '_damage_hi',
                '_damage_lw', '_jump', '_climb', '_escape', '_end', '_start',
                '_final', '_u', '_d', '_l', '_r', '_hit']
    for s in stems:
        for suf in suffixes:
            out.add(s + suf)
    return out


def clip_stem_variants(stem, max_us=4):
    """Every name obtained by inserting up to `max_us` underscores into `stem`."""
    n = len(stem)
    if n < 2:
        return [stem]
    positions = range(n - 1)
    yield stem
    for k in range(1, max_us + 1):
        for combo in itertools.combinations(positions, k):
            parts = []
            prev = 0
            for p in combo:
                parts.append(stem[prev:p + 1])
                prev = p + 1
            parts.append(stem[prev:])
            yield '_'.join(parts)


def main():
    lab = load_labels()
    with open(os.path.join(EVID, 'gunner_body_c00_motion_list.json'), encoding='utf-8') as fh:
        d = json.load(fh)
    fixed = {hash40(c): c for c in fixed_candidates()}
    collisions = []
    for e in d['entries']:
        kind_h = int(e['kind_hash'], 16)
        name = lab.get(kind_h) or fixed.get(kind_h)
        source = 'ParamLabels.csv' if lab.get(kind_h) else ('candidate' if name else None)
        if name is None and e['anim_paths']:
            clip = os.path.basename(e['anim_paths'][0]).replace('.nuanmb', '')
            stem = re.sub(r'^[a-z]\d+', '', clip)
            hits = [v for v in clip_stem_variants(stem) if hash40(v) == kind_h]
            if hits:
                name = min(hits, key=lambda s: (len(s), s))
                source = 'clip-stem-underscores'
                if len(hits) > 1:
                    collisions.append((e['index'], name, sorted(hits)))
        e['kind_name'] = name
        e['kind_name_source'] = source
        gs_h = int(e['game_script_hash'], 16)
        sname = lab.get(gs_h)
        if sname is None and name:
            form = 'game_' + name.replace('_', '')
            if hash40(form) == gs_h:
                sname = form
        e['game_script_name'] = sname
    out = os.path.join(EVID, 'gunner_body_c00_motion_list_resolved.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, indent=1)
    resolved = sum(1 for e in d['entries'] if e['kind_name'])
    print(f'kinds resolved {resolved}/{len(d["entries"])}')
    print(f'game scripts resolved {sum(1 for e in d["entries"] if e["game_script_name"])}')
    print(f'clip-stem collisions {len(collisions)}')
    for e in d['entries']:
        anims = ','.join((p or '?').split('/')[-1].replace('.nuanmb', '') for p in e['anim_paths'])
        print(f'{e["index"]:3d} {(e["kind_name"] or "UNRESOLVED_"+e["kind_hash"]):36s} '
              f'{(e["game_script_name"] or "-"):32s} fl={e["flags"]} bl={e["blend"]} '
              f'n={e["n_anims"]} cancel={e["cancel"]} {anims}')
    if collisions:
        print('\ncollisions:')
        for idx, name, hits in collisions:
            print(idx, name, hits)


if __name__ == '__main__':
    main()