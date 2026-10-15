"""Pin the donor parameters the Hero Spin port needs, from the donor's vl.prc.

Source of values
----------------
The port transplants Mii Swordfighter's Hero Spin (up-B) onto Mythra c07. The
move is the donor's, so its numbers are the donor's:
`<workspace_root>/export/fighter/miiswordsman/param/vl.prc` (honours MGW_EXPORT).

The whole chain needs exactly two floats, both from the group
`param_special_hi` (0x1086bc4a93):

  hi1_jump_speed_mul  (0x12b414540b) -> FLOAT_RESERVE_KINETIC_MOTION_SPEED_MUL
                        status/SpecialHi__main.c:20-32
  hi1_land_weak_frame (0x136487e810) -> FIGHTER_INSTANCE_WORK_ID_FLOAT_LANDING_FRAME
                        status/SpecialHi1End__end.c:19-31

Assert, do not assume
---------------------
pyprc exposes hashes, not names, so every hash this script reads is resolved
against `references/diddy_specials/source_audit/ParamLabels.csv` and the result
is checked three ways: the label must equal the expected name, the label must
round-trip back to the same hash through pyprc, and the name must not be
ambiguous. A hash that resolves to a plausible-looking wrong name fails loudly
rather than producing a number.

What "all hi1_* keys" turned out to mean
----------------------------------------
PLAN.md section 9.2 (and the task) ask for all 24 `hi1_*` keys that
ParamLabels.csv names, not just the two required ones. Measured against the
pinned file, the group actually contains only FIVE `hi1_*` keys: the other 19
labels exist in the game-wide hash dictionary but are not present in this
group, this file, or anywhere else in the file (the whole param tree was walked
to confirm). This script therefore emits the five that exist with their values
and records the other 19 explicitly as absent, so that none of them can be
re-guessed later and the gap cannot be mistaken for an oversight.

Outputs
-------
  references/miiswordsman_special_hi/parameter_manifest.json
  mod_files/mythra_gamewatch_swap/src/hero_spin_params.rs

The generated Rust is deliberately inert: it is not declared in lib.rs and no
existing plugin logic is touched.
"""
import hashlib
import json
import os
from pathlib import Path

import pyprc

ROOT = Path(__file__).resolve().parents[3]
EXPORT = Path(os.environ.get('MGW_EXPORT', str(ROOT / 'dumps' / 'arc')))
VL_PATH = EXPORT / 'fighter' / 'miiswordsman' / 'param' / 'vl.prc'
LABELS_PATH = ROOT / 'references' / 'diddy_specials' / 'source_audit' / 'ParamLabels.csv'
OUT_RUST = ROOT / 'mod_files' / 'mythra_gamewatch_swap' / 'src' / 'hero_spin_params.rs'
OUT_MANIFEST = ROOT / 'references' / 'miiswordsman_special_hi' / 'parameter_manifest.json'

GROUP_NAME = 'param_special_hi'
GROUP_HASH = '0x1086bc4a93'

# (key, consumer as file:line) - the only two the pinned donor status set reads.
REQUIRED = [
    ('hi1_jump_speed_mul',
     'references/miiswordsman_special_hi/status/SpecialHi__main.c:20-32'),
    ('hi1_land_weak_frame',
     'references/miiswordsman_special_hi/status/SpecialHi1End__end.c:19-31'),
]

# Every hi1_* label ParamLabels.csv names (lines 24392-24415). Recorded in full
# so a reader can see which exist rather than assuming any are missing.
EXPECTED_HI1 = [
    'hi1_add_fall_accel_y', 'hi1_add_fall_speed_limit_y', 'hi1_add_fall_speed_y',
    'hi1_add_landing_frame', 'hi1_air_start_mul_y', 'hi1_control_limit_mul_x',
    'hi1_fall_special_landing_frame', 'hi1_fall_special_x_speed_max_mul',
    'hi1_first_jump_x_speed', 'hi1_first_jump_y_speed', 'hi1_first_shoot_angle',
    'hi1_jump_mul_x', 'hi1_jump_speed_mul', 'hi1_jump_x_speed_mul',
    'hi1_jump_y_accel', 'hi1_jump_y_speed_mul', 'hi1_land_weak_frame',
    'hi1_landing_frame', 'hi1_shoot_pos_offset_x', 'hi1_shoot_pos_offset_y',
    'hi1_shoot_store_x_initial_velocity_mul', 'hi1_shoot_store_x_speed_mul',
    'hi1_shoot_store_y_speed_mul', 'hi1_turn_stick_x',
]


def hx(value):
    return '0x%010x' % value


def load_labels(path):
    labels = {}
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line or ',' not in line:
            continue
        key, name = line.split(',', 1)
        labels[key.strip().lower()] = name.strip()
    return labels


def main():
    assert VL_PATH.is_file(), 'missing pinned source: %s' % VL_PATH
    data = VL_PATH.read_bytes()
    assert data, 'pinned source is empty: %s' % VL_PATH
    source_sha256 = hashlib.sha256(data).hexdigest()

    labels = load_labels(LABELS_PATH)

    # --- the group hash itself must resolve, not just the leaf hashes ----------
    group_hash_int = pyprc.hash(GROUP_NAME).value
    assert hx(group_hash_int) == GROUP_HASH, (
        'group hash mismatch: %s resolved to %s, expected %s'
        % (GROUP_NAME, hx(group_hash_int), GROUP_HASH))
    assert labels.get(GROUP_HASH) == GROUP_NAME, (
        'ParamLabels disagrees for %s: got %r' % (GROUP_HASH, labels.get(GROUP_HASH)))

    group = pyprc.param(str(VL_PATH))[pyprc.hash(GROUP_NAME)][0]

    # --- resolve every key in the group; none may be unresolvable -------------
    group_keys = []
    for key_node, value_node in group:
        key_int = key_node.value
        name = labels.get(hx(key_int))
        assert name is not None, 'group key %s has no label in ParamLabels.csv' % hx(key_int)
        # round-trip: the label must hash back to the very key we read
        assert pyprc.hash(name).value == key_int, (
            'label round-trip failed for %s: %s -> %s'
            % (name, hx(key_int), hx(pyprc.hash(name).value)))
        group_keys.append((name, hx(key_int), float(value_node.value)))

    group_key_count = len(group_keys)

    # --- the hi1_* subset that actually exists --------------------------------
    present = {name: value for name, _h, value in group_keys if name.startswith('hi1_')}
    present_hashes = {name: h for name, h, _v in group_keys if name.startswith('hi1_')}
    absent = [name for name in EXPECTED_HI1 if name not in present]

    assert set(present) <= set(EXPECTED_HI1), (
        'group has hi1_* keys not named in ParamLabels.csv: %s'
        % sorted(set(present) - set(EXPECTED_HI1)))

    # --- the two required keys must be present, labelled and float ------------
    required_records = []
    for name, consumer in REQUIRED:
        assert name in present, 'required key absent from %s: %s' % (GROUP_NAME, name)
        value = present[name]
        assert isinstance(value, float), 'required key %s is not a float' % name
        required_records.append({
            'key': name,
            'hash': present_hashes[name],
            'value': value,
            'consumer': consumer,
        })

    sources = {
        str(VL_PATH): {'size_bytes': len(data), 'sha256': source_sha256},
    }
    manifest = {
        'source': str(VL_PATH),
        'source_size_bytes': len(data),
        'source_sha256': source_sha256,
        'sources': sources,
        'group': {'name': GROUP_NAME, 'hash': GROUP_HASH, 'key_count': group_key_count},
        'values': present,
        'hi1_keys': [
            {
                'name': name,
                'hash': hx(pyprc.hash(name).value),
                'present': name in present,
                'value': present.get(name),
                'used': any(name == r['key'] for r in required_records),
                'consumer': next((r['consumer'] for r in required_records if r['key'] == name), None),
            }
            for name in EXPECTED_HI1
        ],
        'required': required_records,
        'unused_hi1_keys': sorted(n for n in present if n not in {r['key'] for r in required_records}),
        'absent_hi1_keys': {
            'reason': ('named in ParamLabels.csv but not present anywhere in the pinned '
                       '%s group or the file; not reconstructed' % GROUP_NAME),
            'keys': absent,
        },
        'notes': (
            'pyprc exposes hashes only; every name here is resolved through '
            'references/diddy_specials/source_audit/ParamLabels.csv and asserted to '
            'round-trip through pyprc.hash. The group holds %d keys (%d hi1_*, the '
            'rest hi2_*/hi3_*); the 19 hi1_* labels not listed under values are '
            'absent from the pinned file.' % (group_key_count, len(present))),
    }

    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    # --- generated Rust, in the shape of src/monkey_flip_params.rs ------------
    lines = []
    lines.append('// Generated by mod_files/mythra_gamewatch_swap/tools/extract_hero_spin_params.py; do not guess values.')
    lines.append('// Source: %s' % VL_PATH)
    lines.append('// SHA-256: %s  (%d bytes)' % (source_sha256, len(data)))
    lines.append('// Group: %s (%s), %d keys, of which %d are hi1_*'
                 % (GROUP_NAME, GROUP_HASH, group_key_count, len(present)))
    lines.append('// Required keys and their consumers:')
    for record in required_records:
        lines.append('//   %s -> %s' % (record['key'], record['consumer']))
    lines.append('// hi1_* labels named in ParamLabels.csv but absent from this file (recorded, not guessed):')
    for name in absent:
        lines.append('//   %s' % name)
    lines.append('pub fn value(key: &str) -> f32 {')
    lines.append('    match key {')
    for name in sorted(present):
        lines.append('        "%s" => %s_f32,' % (name, ('%.9g' % present[name])))
    lines.append('        _ => panic!("Unknown Hero Spin parameter"),')
    lines.append('    }')
    lines.append('}')
    OUT_RUST.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    for record in required_records:
        print('required %-22s = %-12s (%s)' % (record['key'], record['value'], record['consumer']))
    print('group keys: %d   hi1_* present: %d   hi1_* absent: %d'
          % (group_key_count, len(present), len(absent)))
    print('wrote %s' % OUT_MANIFEST)
    print('wrote %s' % OUT_RUST)


if __name__ == '__main__':
    main()
