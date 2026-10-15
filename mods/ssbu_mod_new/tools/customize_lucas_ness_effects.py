"""Costume-theme the Lucas down-smash and Ness back-throw PSI effects. v1.0.0.

Mythra (`elight`) c06/c07 play three donor emitter sets that were merged into the
recipient-owned per-slot banks with the donors' stock colours:

  * `LUCAS_PSI_HOLD`   / `P_LucasPsiHold`      - down-smash charge orb
  * `LUCAS_PSI_ATK_LW` / `P_LucasPsiAttackLw`  - down-smash three-hit burst
  * `NESS_PSI_RUSH`    / `P_NessPsiRush`       - back-throw PSI

This tool re-colours exactly those sets so they sit inside each costume's
existing effect palette, measured on the installed banks (2026-10-03):

  * c06 - deep crimson / scarlet, magenta, violet, white-hot cores
  * c07 - white, ivory, pale and champagne gold, light pink

It is a **semantic merge**, not a file copy: the recipient bank is decoded with
the pinned EffectConverter, only the three sets are edited, and the bank is
re-exported. Any emitter set, texture or model another task added to the same
bank is carried through untouched, so this delta can be applied to a later bank
than the one it was developed on. What may change is closed:

  * `ParticleColor.Color0/1 R,G,B`, the X/Y/Z of the live `Color0`/`Color1`
    keys, and `EmitterStatic.ColorScale` of the emitters listed in `THEMES`;
  * the pixels (never the alpha, size, format or mip count) of the two colour
    baked textures in `TEXTURES`, which no other emitter set may use.

Key times, alpha, scale, emission, shapes, shaders, models, the `EASL`/`CADP`
side blocks and every other set are asserted unchanged, three ways: the decoded
fields of the re-exported bank, a field-level diff of the edited sets, and an
independent byte diff of the raw `.eff` that does not use the converter.
Gameplay (ACMD, hitboxes, timing, animation, sound) lives outside the bank and
is not touched by this tool.

    python -B tools/customize_lucas_ness_effects.py --check
    python -B tools/customize_lucas_ness_effects.py --slot c06 \
        --recipient <ef_elight_c06.eff> --output <dir under builds/>/ef_elight_c06.eff
    python -B tools/customize_lucas_ness_effects.py --package builds/pgwr/<name>
    python -B tools/customize_lucas_ness_effects.py --verify-package builds/pgwr/<name>

`--package` builds both slots from the recorded input (`RECORDED_INPUT`), runs
the negative controls and the loader-resolution check, and writes MANIFEST.json.
`--recipient` accepts any bank that still holds the three sets with their donor
or already-themed colours; re-applying to its own output is byte-identical.

Evidence tier: **B** for bytes and decoded fields. Whether the colours look
right in game is tier D until a console run; no offline check shows that.
"""
from __future__ import annotations

import argparse
import colorsys
import hashlib
import json
import shutil
import struct
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))

import build_color_themes as themes  # noqa: E402  (texture codec, raw VFXB walk)
import merge_hero_neutral_b_effects as engine  # noqa: E402  (converter driver)

VERSION = '1.0.0'
TASK = 'lucas_ness_effect_theme'
CACHE = ROOT / 'builds/.cache' / TASK
MOD_REL = 'ultimate/mods/pyra_gamewatch_reskin'
BANK_REL = 'effect/fighter/elight/ef_elight_{slot}.eff'
SLOTS = ('c06', 'c07')

# The latest recorded installed package (CURRENT_INSTALL.md, 2026-10-03): DK cargo
# 0.1.1-test over Incineroar 0.3.0 over shared 0.20.20.
RECORDED_BASELINE = 'builds/pgwr/dk_cargo-0.1.1-test'
RECORDED_BASELINE_TREE = 'dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e'
RECORDED_INPUT = {
    'c06': 'fcdd6caa49b5d8b7c50a9c44a612acfba757556560b7b79d5561af4b41ecbc17',
    'c07': '1734bb5443e28b956c5c7bb478aac94030dbaee2b22a319ea13d3f37ef26648b',
}

# bank resource name -> emitter set folder. The ACMD asks for the lower-case name.
RESOURCES = {
    'LUCAS_PSI_HOLD': 'P_LucasPsiHold',
    'LUCAS_PSI_ATK_LW': 'P_LucasPsiAttackLw',
    'NESS_PSI_RUSH': 'P_NessPsiRush',
}
OURS = tuple(RESOURCES.values())

# --- palettes, taken from what each costume's own bank already uses -----------
# c06 (Black & Pink Mythra bank): hue 0 saturated 590 keys, violet 180, magenta 122.
SCARLET = (1.0, 0.07, 0.12)
CRIMSON = (0.80, 0.0, 0.10)
BLOOD = (0.45, 0.0, 0.03)
MAGENTA = (1.0, 0.09, 0.78)
VIOLET = (0.59, 0.0, 1.0)
ROSE_CORE = (1.0, 0.74, 0.78)
# c07 (white/gold bank): white 657 keys, pale gold 313, light pink 264.
WHITE = (1.0, 1.0, 1.0)
WARM_WHITE = (1.0, 1.0, 0.97)
IVORY = (1.0, 0.98, 0.94)
PALE_GOLD = (1.0, 0.92, 0.68)
LIGHT_GOLD = (1.0, 0.88, 0.55)
GOLD = (1.0, 0.84, 0.46)
CHAMPAGNE = (0.98, 0.82, 0.44)
LIGHT_PINK = (1.0, 0.78, 0.88)

# set -> emitter -> edit. `c0`/`c1` are the constant colours, `k0` the live
# Color0 keys (count must equal the emitter's own NumColor0Keys; times are kept),
# `scale` is ColorScale. An emitter not listed, or a field not given, is kept.
THEMES = {
    'c06': {
        'P_LucasPsiAttackLw': {
            'flare1': {'c0': (0.85, 0.0, 0.22), 'k0': [(1.0, 0.04, 0.22), (0.55, 0.0, 0.10)]},
            'flash1_f': {'c0': (1.0, 0.08, 0.16), 'k0': [SCARLET, MAGENTA]},
            'flash_atk': {'c0': ROSE_CORE, 'c1': CRIMSON},
            'hex_L': {'c0': (0.75, 0.05, 0.60), 'k0': [VIOLET, SCARLET, MAGENTA], 'scale': 1.3},
            'hex_L_2': {'c0': (0.75, 0.05, 0.60), 'k0': [VIOLET, SCARLET, MAGENTA], 'scale': 1.3},
            'hex_S': {'c0': SCARLET, 'k0': [SCARLET, BLOOD, (1.0, 0.09, 0.55)], 'scale': 1.3},
            'hex_S_2': {'c0': SCARLET, 'k0': [SCARLET, BLOOD, (1.0, 0.09, 0.55)], 'scale': 1.3},
        },
        'P_LucasPsiHold': {
            'flare2': {'c0': (1.0, 0.03, 0.10), 'c1': (0.90, 0.0, 0.40)},
            'flash1': {'c0': ROSE_CORE, 'c1': (0.90, 0.0, 0.14)},
            'flash2_flare': {'c0': (1.0, 0.08, 0.16), 'k0': [SCARLET, MAGENTA, VIOLET]},
        },
        'P_NessPsiRush': {
            'flare1': {'c0': (1.0, 0.20, 0.40), 'c1': (0.85, 0.0, 0.30),
                       'k0': [(1.0, 0.0, 0.22), (1.0, 0.40, 0.62)]},
            'flare2': {'c0': (0.80, 0.0, 0.12), 'c1': (1.0, 0.10, 0.55)},
            'flash1': {'c0': (1.0, 0.76, 0.86), 'c1': (0.90, 0.0, 0.45)},
            'flash2_flare': {'c0': MAGENTA, 'k0': [MAGENTA, VIOLET, (1.0, 0.07, 0.25)]},
            'line1': {'c0': (1.0, 0.20, 0.25), 'c1': BLOOD,
                      'k0': [(1.0, 0.86, 0.88), (1.0, 0.05, 0.12)]},
            'ring1': {'c0': (1.0, 0.15, 0.60), 'c1': (0.55, 0.0, 0.30),
                      'k0': [(1.0, 0.22, 0.50), (0.69, 0.09, 1.0)]},
            'ring2': {'c0': (1.0, 0.15, 0.60), 'c1': (0.55, 0.0, 0.30),
                      'k0': [(1.0, 0.22, 0.50), (0.69, 0.09, 1.0)]},
        },
    },
    'c07': {
        'P_LucasPsiAttackLw': {
            'flare1': {'c0': LIGHT_GOLD, 'k0': [PALE_GOLD, (1.0, 0.82, 0.44)]},
            'flash1_f': {'c0': PALE_GOLD, 'k0': [(1.0, 0.98, 0.90), LIGHT_GOLD]},
            'flash_atk': {'c0': WARM_WHITE, 'c1': GOLD, 'scale': 1.4},
            'hex_L': {'c0': PALE_GOLD, 'k0': [LIGHT_GOLD, WHITE, LIGHT_PINK], 'scale': 1.35},
            'hex_L_2': {'c0': PALE_GOLD, 'k0': [LIGHT_GOLD, WHITE, LIGHT_PINK], 'scale': 1.35},
            'hex_S': {'c0': IVORY, 'k0': [WHITE, LIGHT_PINK, PALE_GOLD], 'scale': 1.35},
            'hex_S_2': {'c0': IVORY, 'k0': [WHITE, LIGHT_PINK, PALE_GOLD], 'scale': 1.35},
        },
        'P_LucasPsiHold': {
            'flare2': {'c0': (1.0, 0.86, 0.50), 'c1': PALE_GOLD},
            'flash1': {'c0': WARM_WHITE, 'c1': GOLD, 'scale': 1.4},
            'flash2_flare': {'c0': PALE_GOLD, 'k0': [PALE_GOLD, LIGHT_PINK, WHITE]},
        },
        'P_NessPsiRush': {
            'flare1': {'c0': (1.0, 0.90, 0.70), 'c1': (1.0, 0.86, 0.55),
                       'k0': [(1.0, 0.84, 0.50), (1.0, 0.97, 0.86)]},
            'flare2': {'c0': (1.0, 0.90, 0.62), 'c1': (1.0, 0.96, 0.84)},
            'flash1': {'c0': WARM_WHITE, 'c1': LIGHT_PINK, 'scale': 1.4},
            'flash2_flare': {'c0': LIGHT_PINK, 'k0': [LIGHT_PINK, PALE_GOLD, WHITE]},
            'line1': {'c0': (1.0, 0.94, 0.76), 'c1': CHAMPAGNE,
                      'k0': [WHITE, LIGHT_GOLD], 'scale': 1.45},
            'ring1': {'c0': (1.0, 0.85, 0.92), 'c1': LIGHT_GOLD,
                      'k0': [(1.0, 0.93, 0.96), LIGHT_PINK], 'scale': 1.45},
            'ring2': {'c0': (1.0, 0.85, 0.92), 'c1': LIGHT_GOLD,
                      'k0': [(1.0, 0.93, 0.96), LIGHT_PINK], 'scale': 1.45},
        },
    },
}

# The two sprites whose colour is in the texture (their emitters draw the
# texture with a white constant). `primary` replaces the sprite's main hue,
# `secondary` its orange cross-rays; `sat` scales how far from white it goes.
TEXTURES = {
    '621195579': {   # ef_lucas star: P_LucasPsiAttackLw/flash1, P_LucasPsiHold/flash2
        'c06': {'primary': (1.0, 0.04, 0.14), 'secondary': (0.80, 0.10, 1.0), 'sat': 1.0},
        'c07': {'primary': (1.0, 0.84, 0.48), 'secondary': (1.0, 0.70, 0.86), 'sat': 0.80},
    },
    '97457052': {    # ef_ness_flash00 star: P_NessPsiRush/flash2
        'c06': {'primary': (1.0, 0.06, 0.72), 'secondary': (1.0, 0.22, 0.28), 'sat': 1.3},
        'c07': {'primary': (1.0, 0.72, 0.86), 'secondary': (1.0, 0.86, 0.50), 'sat': 0.80},
    },
}
# Pinned payloads (sha256 of the converter's single-texture .bntx export). The
# originals identify the donor texture; the themed ones make a second application
# a no-op and make an encoder that stops being deterministic fail loudly.
TEXTURE_PINS = {
    '621195579': {
        'original': '9f225f7567591639ac503991480a0a3278449a5bc08b793293f8b083df404dc5',
        'c06': '3b51f3a3936427967d12215f325db6893fd404038846eaef3c4630ac1331cee6',
        'c07': 'e0420d4f746d508ca13a8eff92b3b13771b8499f522b051ccf691b8abef08e6a'},
    '97457052': {
        'original': '93cb510298611cc04453eb0d081aaeb144822f7079924b64154ee42a6315e330',
        'c06': '00f7ac895f02bc0109c4e5694681b2914aa40286fad952d72d48ef9daabdcaeb',
        'c07': '0be5bbedb9a1af4c0dae83c701753cbb99da09c740ea6b30ddc9fd68ace33c35'},
}

# Every decoded-field path this tool may alter inside an edited emitter.
ALLOWED_FIELDS = (
    {f'ParticleColor/Color{c}{x}' for c in '01' for x in 'RGB'}
    | {f'EmitterStatic/Color{c}/Keys[{i}]/{x}' for c in '01' for i in range(8) for x in 'XYZ'}
    | {'EmitterStatic/ColorScale'})


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_bytes(data) -> str:
    return hashlib.sha256(bytes(data)).hexdigest()


def f32(value) -> float:
    """A JSON number as the bank stores it: the shortest text of the 32-bit float."""
    return float(str(np.float32(value)))


def canon(value):
    """Decoded fields with every float reduced to its 32-bit value."""
    if isinstance(value, dict):
        return {k: canon(v) for k, v in value.items()}
    if isinstance(value, list):
        return [canon(v) for v in value]
    if isinstance(value, float):
        return float(np.float32(value))
    return value


def flatten(value, prefix=''):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, f'{prefix}/{key}' if prefix else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from flatten(item, f'{prefix}[{index}]')
    else:
        yield prefix, value


# --- textures ----------------------------------------------------------------

def recolour_pixels(rgba, spec):
    """Re-hue a colour-baked star sprite; value, white core and alpha are kept."""
    a = np.asarray(rgba).astype(np.float64)
    rgb = a[..., :3] / 255.0
    hi, lo = rgb.max(-1), rgb.min(-1)
    span = hi - lo
    sat = np.where(hi > 1e-6, span / np.maximum(hi, 1e-6), 0.0)
    safe = np.maximum(span, 1e-9)
    hue = np.where(rgb[..., 0] == hi, ((rgb[..., 1] - rgb[..., 2]) / safe) % 6,
                   np.where(rgb[..., 1] == hi, (rgb[..., 2] - rgb[..., 0]) / safe + 2,
                            (rgb[..., 0] - rgb[..., 1]) / safe + 4)) * 60.0
    # The cross-rays are the only orange/yellow pixels of either sprite.
    weight = np.clip(1.0 - np.abs(hue - 42.0) / 30.0, 0.0, 1.0)[..., None]
    target = (np.array(spec['primary']) * (1 - weight) + np.array(spec['secondary']) * weight)
    target = target / target.max(-1, keepdims=True)
    amount = np.clip(sat * spec['sat'], 0.0, 1.0)[..., None]
    out = hi[..., None] * (1.0 - amount + amount * target)
    result = np.asarray(rgba).copy()
    result[..., :3] = np.rint(np.clip(out, 0, 1) * 255).astype(np.uint8)
    return result


def recolour_bntx(raw: bytes, spec) -> bytes:
    """Same container, name, format, size and mip count; only pixel data moves."""
    offsets = themes.brtis(raw)
    assert len(offsets) == 1, 'expected the converter\'s single-texture export'
    brti = offsets[0]
    fmt = themes.u32(raw, brti + 0x1c)
    assert fmt in themes.BNTX_FORMATS, hex(fmt)
    mips = struct.unpack_from('<H', raw, brti + 0x16)[0]
    result = bytearray(raw)
    with tempfile.TemporaryDirectory(dir=str(scratch_root())) as tmp:
        tmp = Path(tmp)
        (tmp / 'source.bntx').write_bytes(raw)
        themes.convert(tmp / 'source.bntx', tmp / 'source.png')
        original = np.array(Image.open(tmp / 'source.png').convert('RGBA'))
        themed = recolour_pixels(original, spec)
        assert np.array_equal(original[..., 3], themed[..., 3]), 'alpha must not move'
        Image.fromarray(themed, 'RGBA').save(tmp / 'new.png')
        themes.convert(tmp / 'new.png', tmp / 'new.bntx', themes.BNTX_FORMATS[fmt], mips == 1)
        themes.replace_bntx_texture(result, brti, (tmp / 'new.bntx').read_bytes())
    assert len(result) == len(raw)
    return bytes(result)


def texture_name(raw: bytes) -> bytes:
    brti = themes.brtis(raw)[0]
    pointer = themes.u64(raw, brti + 0x60)
    length = struct.unpack_from('<H', raw, pointer)[0]
    return raw[pointer + 2:pointer + 2 + length]


def decode_bntx(raw: bytes):
    with tempfile.TemporaryDirectory(dir=str(scratch_root())) as tmp:
        tmp = Path(tmp)
        (tmp / 't.bntx').write_bytes(raw)
        themes.convert(tmp / 't.bntx', tmp / 't.png')
        return np.array(Image.open(tmp / 't.png').convert('RGBA'))


# --- decoded-bank helpers ----------------------------------------------------

def scratch_root() -> Path:
    path = CACHE / 'work'
    path.mkdir(parents=True, exist_ok=True)
    return path


def semantic(folder: Path) -> dict:
    """engine.semantic_emitters plus the ordering/header text files."""
    result = engine.semantic_emitters(folder)
    for path in folder.rglob('*.txt'):
        result[path.relative_to(folder).as_posix()] = path.read_text()
    result['NamcoFile.json'] = engine.json_read(folder / 'NamcoFile.json')
    return result


def texture_users(folder: Path) -> dict:
    users = {}
    for path in folder.rglob('*.bntx'):
        users.setdefault(path.stem, set()).add(path.parts[-3])
    return users


def resolve_resources(folder: Path) -> dict:
    """Name -> emitter set, exactly as the bank's own tables say."""
    entries = engine.json_read(folder / 'NamcoFile.json')
    order = engine.json_read(folder / 'EmitterSetInfo.txt')['Order']
    found = {}
    for name, expected in RESOURCES.items():
        hits = [e for e in entries if e['Name'] == name]
        assert len(hits) == 1, f'{name}: {len(hits)} bank entries, expected exactly 1'
        actual = order[hits[0]['EmitterSet_ID'] - 1]
        assert actual == expected, f'{name} resolves to {actual}, expected {expected}'
        assert (folder / expected).is_dir(), expected
        found[name] = {'emitter_set': expected, 'emitter_set_id': hits[0]['EmitterSet_ID'],
                       'kind': hits[0]['Kind']}
    return found


def edit_emitter(data: dict, spec: dict, where: str) -> dict:
    data = json.loads(json.dumps(data))
    static, colour = data['EmitterStatic'], data['ParticleColor']
    for channel in '01':
        constant = spec.get('c' + channel)
        if constant is not None:
            for axis, value in zip('RGB', constant):
                colour[f'Color{channel}{axis}'] = f32(value)
        keys = spec.get('k' + channel)
        live = static[f'NumColor{channel}Keys']
        if keys is None:
            # A live colour curve left at donor colours would defeat the theme.
            assert live == 0 or colour[f'Color{channel}Type'] == 'Constant', \
                f'{where}: Color{channel} has {live} live keys and no themed keys'
            continue
        assert len(keys) == live, f'{where}: {len(keys)} themed keys, emitter has {live}'
        for key, value in zip(static[f'Color{channel}']['Keys'], keys):
            key['X'], key['Y'], key['Z'] = (f32(v) for v in value)
    if 'scale' in spec:
        static['ColorScale'] = f32(spec['scale'])
    return data


def emitter_changes(before: dict, after: dict) -> list:
    old, new = dict(flatten(canon(before))), dict(flatten(canon(after)))
    assert old.keys() == new.keys()
    return sorted(k for k in old if old[k] != new[k])


# --- the merge ---------------------------------------------------------------

def apply(recipient, output, slot, *, keep_work=False) -> dict:
    """Theme the three sets of `recipient` for `slot`; write `output` + record."""
    assert slot in SLOTS, slot
    recipient, output = Path(recipient).resolve(), Path(output).resolve()
    assert output.is_relative_to(ROOT / 'builds'), 'output must be under builds/'
    assert output != recipient, 'refusing to overwrite the recipient'
    assert engine.CONVERTER.is_file(), f'missing converter {engine.CONVERTER}'
    input_sha = sha(recipient)
    work = Path(tempfile.mkdtemp(prefix=f'{slot}_{input_sha[:12]}_', dir=scratch_root()))
    local = work / f'ef_elight_{slot}.eff'
    shutil.copyfile(recipient, local)
    target = engine.dump(local, work / 'recipient')
    baseline = semantic(target)
    resources = resolve_resources(target)

    # The converter must reproduce the untouched bank, or nothing below is a
    # statement about the recipient.
    pristine = work / 'pristine'
    shutil.copytree(target, pristine / target.name)
    engine.convert(pristine / target.name, pristine)
    assert sha(pristine / (target.name + '_NEW.eff')) == input_sha, \
        'converter does not round-trip this recipient byte-for-byte'

    theme = THEMES[slot]
    expected = dict(baseline)
    field_changes, emitters_edited = {}, 0
    for set_name in OURS:
        present = {p.parent.name for p in (target / set_name).glob('*/EmitterData.json')}
        assert set(theme[set_name]) <= present, (set_name, set(theme[set_name]) - present)
        for emitter in sorted(present):
            path = target / set_name / emitter / 'EmitterData.json'
            before = engine.json_read(path)
            spec = theme[set_name].get(emitter)
            if spec is None:
                # Unlisted emitters draw a colour-baked texture with white constants.
                samplers = {str(before[f'Sampler{i}']['TextureID']) for i in range(3)}
                assert samplers & set(TEXTURES), f'{set_name}/{emitter} has no theme entry'
                continue
            after = edit_emitter(before, spec, f'{set_name}/{emitter}')
            changed = emitter_changes(before, after)
            assert set(changed) <= ALLOWED_FIELDS, set(changed) - ALLOWED_FIELDS
            path.write_text(json.dumps(after, indent=2))
            key = f'{set_name}/{emitter}/EmitterData.json'
            # Compare after the same shader-index normalisation the baseline got.
            expected[key] = {k: v for k, v in baseline[key].items()}
            for field in ('EmitterStatic', 'ParticleColor'):
                expected[key][field] = after[field]
            field_changes[f'{set_name}/{emitter}'] = changed
            emitters_edited += 1

    users = texture_users(target)
    textures = []
    for texture_id, spec in TEXTURES.items():
        outside = sorted(users.get(texture_id, set()) - set(OURS))
        assert not outside, (f'texture {texture_id} is also used by {outside}; it is no longer '
                             'owned by this task alone, so re-colouring it would change another '
                             'effect. Stop and relocate it to a new id first.')
        copies = sorted(target.glob(f'*/*/{texture_id}.bntx'))
        assert copies, f'texture {texture_id} is not in the recipient bank'
        payloads = {p.read_bytes() for p in copies}
        assert len(payloads) == 1, f'texture {texture_id} has differing copies'
        raw = payloads.pop()
        pins = TEXTURE_PINS[texture_id]
        current = sha_bytes(raw)
        if current == pins['original']:
            new = recolour_bntx(raw, spec[slot])
            assert sha_bytes(new) == pins[slot], \
                (f'texture {texture_id} {slot}: encoder output {sha_bytes(new)} is not the '
                 f'pinned {pins[slot]}')
            state = 'recoloured'
        elif current == pins[slot]:
            new, state = raw, 'already themed'
        else:
            raise AssertionError(f'texture {texture_id} is neither the donor original nor the '
                                 f'{slot} theme (sha256 {current})')
        for path in copies:
            path.write_bytes(new)
            expected[path.relative_to(target).as_posix()] = sha_bytes(new)
        textures.append({'texture_id': texture_id, 'name': texture_name(raw).decode(),
                         'state': state, 'before_sha256': current,
                         'after_sha256': sha_bytes(new),
                         'used_by': sorted(p.relative_to(target).parent.as_posix()
                                           for p in copies)})

    engine.convert(target, work)
    packed = work / (target.name + '_NEW.eff')
    assert packed.is_file()
    reread = engine.dump(packed, work / 'verification')
    observed = semantic(reread)

    def same(a, b):
        return json.dumps(canon(a), sort_keys=True) == json.dumps(canon(b), sort_keys=True)

    assert expected.keys() == observed.keys(), \
        sorted(set(expected) ^ set(observed))[:8]
    drift = [k for k in expected if not same(expected[k], observed[k])]
    assert not drift, ('re-exported bank differs from the intended one', drift[:8])
    unrelated = [k for k in baseline if not k.startswith(OURS)]
    assert all(same(baseline[k], observed[k]) for k in unrelated)
    assert resolve_resources(reread) == resources
    verify_theme(reread, slot)

    raw_in, raw_out = recipient.read_bytes(), packed.read_bytes()
    scope = byte_scope(raw_in, raw_out)

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(packed, output)
    record = {
        'tool': f'tools/customize_lucas_ness_effects.py {VERSION}', 'date': '2026-10-03',
        'evidence_tier': 'B', 'hardware_validated': False, 'slot': slot,
        'recipient_sha256': input_sha,
        'recipient_is_recorded_input': input_sha == RECORDED_INPUT[slot],
        'output_sha256': sha(output), 'output_bytes': output.stat().st_size,
        'effect_library_commit': engine.PIN, 'converter_sha256': sha(engine.CONVERTER),
        'library_sha256': sha(engine.CONVERTER.with_name('EffectLibrary.dll')),
        'converter_roundtrips_recipient_bytes': True,
        'resources': resources, 'emitters_edited': emitters_edited,
        'changed_fields': field_changes, 'textures': textures,
        'decoded_entries_compared': len(observed),
        'unrelated_decoded_entries_identical': len(unrelated),
        'emitter_sets_total': len(engine.json_read(reread / 'EmitterSetInfo.txt')['Order']),
        'byte_scope': scope,
    }
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return record


def verify_theme(folder: Path, slot: str) -> None:
    """The decoded bank carries exactly this slot's theme. Raises if not."""
    for set_name, emitters in THEMES[slot].items():
        for emitter, spec in emitters.items():
            data = engine.json_read(folder / set_name / emitter / 'EmitterData.json')
            assert emitter_changes(data, edit_emitter(data, spec, emitter)) == [], \
                f'{slot} {set_name}/{emitter} does not carry the theme'
    for texture_id in TEXTURES:
        for path in folder.glob(f'*/*/{texture_id}.bntx'):
            assert sha(path) == TEXTURE_PINS[texture_id][slot], \
                f'{slot} texture {texture_id} is not the themed payload'


# --- independent raw-byte check (no converter involved) ----------------------

def raw_layout(raw: bytes) -> dict:
    emitters = [(eset, name, data, data + const + 32)
                for eset, name, data, const in themes.emitter_hierarchy(raw)]
    start = raw.index(b'BNTX')
    assert raw.count(b'BNTX') == 1
    size = themes.u32(raw, start + 0x1c)
    bank = raw[start:start + size]
    textures = []
    for brti in themes.brtis(bank):
        pointer = themes.u64(bank, brti + 0x60)
        length = struct.unpack_from('<H', bank, pointer)[0]
        first = themes.u64(bank, themes.u64(bank, brti + 0x70))
        textures.append((bank[pointer + 2:pointer + 2 + length].decode('latin1'),
                         start + first, start + first + themes.u32(bank, brti + 0x50),
                         bank[brti:brti + 0x50]))
    return {'emitters': emitters, 'bntx': (start, start + size), 'textures': textures}


def byte_scope(raw_in: bytes, raw_out: bytes, owned_textures=None) -> dict:
    """Every differing byte lies in an owned emitter block or an owned texture."""
    assert len(raw_in) == len(raw_out), (len(raw_in), len(raw_out))
    before, after = raw_layout(raw_in), raw_layout(raw_out)
    assert before['emitters'] == after['emitters'], 'emitter table moved'
    assert before['bntx'] == after['bntx']
    assert before['textures'] == after['textures'], \
        'texture table, a texture header or a texture size changed'
    if owned_textures is None:
        owned_textures = set(TEXTURE_NAMES.values())
    permitted = np.zeros(len(raw_in), dtype=bool)
    for eset, _, start, end in before['emitters']:
        if eset in OURS:
            permitted[start:end] = True
    for name, start, end, _ in before['textures']:
        if name in owned_textures:
            permitted[start:end] = True
    a = np.frombuffer(raw_in, dtype=np.uint8)
    b = np.frombuffer(raw_out, dtype=np.uint8)
    different = a != b
    stray = np.flatnonzero(different & ~permitted)
    assert stray.size == 0, f'{stray.size} changed bytes outside the owned ranges, first at {int(stray[0])}'
    return {'bank_bytes': len(raw_in), 'changed_bytes': int(different.sum()),
            'changed_bytes_outside_owned_ranges': 0,
            'emitter_blocks_total': len(before['emitters']),
            'emitter_blocks_owned': sum(1 for e in before['emitters'] if e[0] in OURS),
            'textures_total': len(before['textures']),
            'textures_owned': sorted(owned_textures)}


# BNTX names of the two owned textures (the converter names exports by id).
TEXTURE_NAMES = {'621195579': 'ef_lucas_flash00', '97457052': 'ef_ness_flash00'}


# --- loader resolution -------------------------------------------------------

def loader_resolution(baseline: Path, slot: str, record: dict) -> dict:
    """The themed bank is the file the elight c0x loader is already routed to."""
    mod = baseline / MOD_REL
    rel = BANK_REL.format(slot=slot)
    config = json.loads((mod / 'config.json').read_text())['new-dir-files']
    group = f'fighter/elight/{slot}'
    assert rel in config[group], f'{rel} is not declared under {group}'
    elsewhere = [k for k, v in config.items() if k != group and rel in v]
    assert not elsewhere, elsewhere
    banks = sorted(p.name for p in (mod / 'effect/fighter/elight').glob('*.eff'))
    assert banks == [f'ef_elight_{s}.eff' for s in SLOTS], banks
    assert not list((mod / 'effect/fighter').glob('lucas/*')), 'a donor folder loads nothing'
    assert not list((mod / 'effect/fighter').glob('ness/*')), 'a donor folder loads nothing'
    plugins = baseline / 'atmosphere/contents/01006A800016E000/romfs/skyline/plugins'
    one_slot = plugins / 'libone_slot_eff.nro'
    assert one_slot.is_file(), 'per-slot banks need the One Slot Effects plugin'
    nro = (plugins / 'libpyra_gamewatch_reskin.nro').read_bytes()
    requested = {}
    for name in RESOURCES:
        needle = name.lower().encode()
        assert needle in nro, f'the packaged plugin never asks for {name.lower()}'
        requested[name.lower()] = nro.count(needle)
    return {'bank_path': rel, 'config_group': group, 'declared_only_there': True,
            'elight_banks_in_package': banks, 'donor_folders_shipped': False,
            'one_slot_effects_sha256': sha(one_slot),
            'plugin_sha256': sha_bytes(nro), 'plugin_requests': requested,
            'bank_entries': record['resources'],
            'config_json_change': 'none'}


# --- package -----------------------------------------------------------------

def tree_hash(mod: Path) -> str:
    """Same convention as the dk_cargo manifest: sorted path TAB sha256 LF."""
    lines = [f'{p.relative_to(mod).as_posix()}\t{sha(p)}\n'
             for p in sorted(mod.rglob('*')) if p.is_file()]
    return hashlib.sha256(''.join(lines).encode()).hexdigest()


def negative_controls(raw_in: bytes, raw_out: bytes, slot: str, reread_input: Path) -> dict:
    layout = raw_layout(raw_out)
    results = {}
    # 1. one colour float of an unrelated emitter moves.
    eset, name, start, end = next(e for e in layout['emitters'] if e[0] not in OURS)
    tampered = bytearray(raw_out)
    tampered[end - 32] ^= 0x40
    try:
        byte_scope(raw_in, bytes(tampered))
        results['unrelated_emitter_byte'] = 'NOT DETECTED'
    except AssertionError:
        results['unrelated_emitter_byte'] = f'detected ({eset}/{name})'
    # 2. one pixel byte of a texture this task does not own moves.
    owned = set(TEXTURE_NAMES.values())
    tex = next(t for t in layout['textures'] if t[0] not in owned)
    tampered = bytearray(raw_out)
    tampered[tex[1] + 8] ^= 0x01
    try:
        byte_scope(raw_in, bytes(tampered))
        results['unrelated_texture_byte'] = 'NOT DETECTED'
    except AssertionError:
        results['unrelated_texture_byte'] = f'detected ({tex[0]})'
    # 3. the untouched recipient must not pass as themed.
    try:
        verify_theme(reread_input, slot)
        results['unthemed_input_rejected'] = 'NOT DETECTED'
    except AssertionError:
        results['unthemed_input_rejected'] = 'detected'
    assert all(v.startswith('detected') for v in results.values()), results
    return results


def package(out: Path, baseline: Path = None) -> dict:
    out = Path(out).resolve()
    assert out.is_relative_to(ROOT / 'builds/pgwr'), 'package goes under builds/pgwr/'
    assert not out.exists() or not any(out.iterdir()), f'{out} is not empty; packages are immutable'
    baseline = (ROOT / RECORDED_BASELINE) if baseline is None else Path(baseline).resolve()
    check()
    slots, files = {}, {}
    for slot in SLOTS:
        rel = BANK_REL.format(slot=slot)
        recipient = baseline / MOD_REL / rel
        assert sha(recipient) == RECORDED_INPUT[slot], \
            f'{recipient} is not the recorded input {RECORDED_INPUT[slot]}'
        dest = out / MOD_REL / rel
        record = apply(recipient, dest, slot)
        # Reproducible: a second run from the same input gives the same bytes.
        again = CACHE / 'repro' / f'ef_elight_{slot}.eff'
        assert apply(recipient, again, slot)['output_sha256'] == record['output_sha256']
        # Idempotent: the merge applied to its own output changes nothing.
        twice = CACHE / 'repro' / f'ef_elight_{slot}.twice.eff'
        second = apply(dest, twice, slot)
        assert second['output_sha256'] == record['output_sha256']
        assert second['byte_scope']['changed_bytes'] == 0
        assert all(t['state'] == 'already themed' for t in second['textures'])
        record['reproduced_sha256'] = record['output_sha256']
        record['idempotent_on_own_output'] = True
        work = Path(tempfile.mkdtemp(prefix=f'neg_{slot}_', dir=scratch_root()))
        local = work / f'ef_elight_{slot}.eff'
        shutil.copyfile(recipient, local)
        record['negative_controls'] = negative_controls(
            recipient.read_bytes(), dest.read_bytes(), slot, engine.dump(local, work / 'in'))
        shutil.rmtree(work, ignore_errors=True)
        record['loader_resolution'] = loader_resolution(baseline, slot, record)
        slots[slot] = record
        files[rel] = record['output_sha256']
        print(f'  {slot}: {record["emitters_edited"]} emitters, '
              f'{len(record["textures"])} textures, '
              f'{record["byte_scope"]["changed_bytes"]} bytes changed, '
              f'sha256 {record["output_sha256"]}')
    shutil.rmtree(CACHE / 'repro', ignore_errors=True)
    manifest = {
        'task': TASK, 'task_version': out.name.split('-', 1)[-1],
        'tool': f'tools/customize_lucas_ness_effects.py {VERSION}',
        'tool_sha256': sha(__file__), 'date': '2026-10-03',
        'kind': 'asset delta overlay (2 files); no NRO, no config.json, no motion or sound',
        'readiness': 'READY', 'installed': False, 'runtime_verified': False,
        'evidence_tier': 'B',
        'baseline': baseline.relative_to(ROOT).as_posix(),
        'baseline_mod_tree_sha256': tree_hash(baseline / MOD_REL),
        'recorded_inputs': RECORDED_INPUT,
        'mod_files': files, 'file_count': len(files),
        'mod_tree_sha256': tree_hash(out / MOD_REL),
        'nro': 'unchanged - this delta ships no plugin',
        'texture_pins': TEXTURE_PINS,
        'slots': slots,
    }
    (out / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'PASS: package {out.relative_to(ROOT).as_posix()} '
          f'mod tree {manifest["mod_tree_sha256"]}')
    return manifest


def verify_package(out: Path) -> None:
    """Re-check a finished package against its manifest and its baseline."""
    out = Path(out).resolve()
    manifest = json.loads((out / 'MANIFEST.json').read_text())
    baseline = ROOT / manifest['baseline']
    shipped = sorted(p.relative_to(out / MOD_REL).as_posix()
                     for p in (out / MOD_REL).rglob('*') if p.is_file())
    assert shipped == sorted(manifest['mod_files']), shipped
    assert tree_hash(out / MOD_REL) == manifest['mod_tree_sha256']
    for slot in SLOTS:
        rel = BANK_REL.format(slot=slot)
        assert sha(out / MOD_REL / rel) == manifest['mod_files'][rel]
        recipient = baseline / MOD_REL / rel
        assert sha(recipient) == manifest['recorded_inputs'][slot], 'baseline moved'
        scope = byte_scope(recipient.read_bytes(), (out / MOD_REL / rel).read_bytes())
        assert scope == manifest['slots'][slot]['byte_scope']
        loader_resolution(baseline, slot, manifest['slots'][slot])
        print(f'  {slot}: {scope["changed_bytes"]} changed bytes, all inside '
              f'{scope["emitter_blocks_owned"]} owned emitter blocks / '
              f'{len(scope["textures_owned"])} owned textures; bank declared for the loader')
    print('PASS: package matches its manifest; preservation and loader resolution hold')


# --- preview -----------------------------------------------------------------

def preview(path: Path, baseline: Path = None) -> None:
    """Contact sheet: donor vs themed sprites and the emitter palettes."""
    baseline = (ROOT / RECORDED_BASELINE) if baseline is None else Path(baseline)
    work = Path(tempfile.mkdtemp(prefix='preview_', dir=scratch_root()))
    local = work / 'ef_elight_c06.eff'
    shutil.copyfile(baseline / MOD_REL / BANK_REL.format(slot='c06'), local)
    folder = engine.dump(local, work / 'in')
    sprites = {}
    for texture_id in TEXTURES:
        raw = next(folder.glob(f'*/*/{texture_id}.bntx')).read_bytes()
        sprites[texture_id] = {'donor': decode_bntx(raw)}
        for slot in SLOTS:
            sprites[texture_id][slot] = decode_bntx(recolour_bntx(raw, TEXTURES[texture_id][slot]))
    donor_palette = {}
    for set_name in OURS:
        for emitter in THEMES['c06'][set_name]:
            data = engine.json_read(folder / set_name / emitter / 'EmitterData.json')
            donor_palette[(set_name, emitter)] = emitter_swatches(data)
    cell, pad, label = 132, 8, 250
    rows = [(s, e) for s in OURS for e in THEMES['c06'][s]]
    width = label + 3 * (5 * 30 + 24)
    height = 40 + 2 * (cell + 26) + 22 * len(rows) + 40
    canvas = Image.new('RGB', (width, height), (18, 16, 22))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 8), 'Lucas down smash / Ness back throw effect themes  '
                        '(donor | c06 scarlet-dark | c07 luminous)', fill='white')
    y = 30
    for texture_id in TEXTURES:
        draw.text((pad, y + cell // 2), f'texture {texture_id}', fill=(200, 200, 200))
        for column, variant in enumerate(('donor', 'c06', 'c07')):
            rgba = sprites[texture_id][variant].astype(np.float64)
            # Additive preview on the dark background, as the emitters blend it.
            glow = rgba[..., :3] * (rgba[..., 3:4] / 255.0)
            tile = np.clip(np.array([18, 16, 22]) + glow, 0, 255).astype(np.uint8)
            image = Image.fromarray(tile, 'RGB').resize((cell, cell))
            canvas.paste(image, (label + column * (5 * 30 + 24), y))
        y += cell + 26
    for set_name, emitter in rows:
        draw.text((pad, y + 3), f'{set_name[2:]}/{emitter}', fill=(200, 200, 200))
        data = engine.json_read(folder / set_name / emitter / 'EmitterData.json')
        variants = [donor_palette[(set_name, emitter)]]
        for slot in SLOTS:
            variants.append(emitter_swatches(
                edit_emitter(data, THEMES[slot][set_name][emitter], emitter)))
        for column, colours in enumerate(variants):
            for index, rgb in enumerate(colours[:5]):
                x = label + column * (5 * 30 + 24) + index * 30
                fill = tuple(int(round(min(1.0, max(0.0, c)) * 255)) for c in rgb)
                draw.rectangle((x, y, x + 26, y + 16), fill=fill, outline=(70, 70, 70))
        y += 22
    draw.text((pad, y + 8), 'swatches: constant Color0 (or its live keys), then Color1. '
                            'Offline preview only - not a game capture.', fill=(150, 150, 150))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    shutil.rmtree(work, ignore_errors=True)
    print(f'wrote {path}')


def emitter_swatches(data: dict) -> list:
    static, colour = data['EmitterStatic'], data['ParticleColor']
    out = []
    for channel in '01':
        live = static[f'NumColor{channel}Keys']
        if live and colour[f'Color{channel}Type'] != 'Constant':
            out += [(k['X'], k['Y'], k['Z']) for k in static[f'Color{channel}']['Keys'][:live]]
        else:
            out.append(tuple(colour[f'Color{channel}{x}'] for x in 'RGB'))
    return out


# --- smoke test --------------------------------------------------------------

def check() -> None:
    """Toolchain, table sanity and palette membership. Writes nothing shipped."""
    assert engine.CONVERTER.is_file(), (
        f'converter not built at {engine.CONVERTER}; run '
        'python tools/build_hero_effect_converter.py --from-source')
    assert themes.CLI.is_file(), f'missing texture codec {themes.CLI}'
    assert set(THEMES) == set(SLOTS)
    for slot in SLOTS:
        assert set(THEMES[slot]) == set(OURS)
        assert {s: set(e) for s, e in THEMES[slot].items()} == \
            {s: set(e) for s, e in THEMES['c06'].items()}, 'slots must theme the same emitters'
        for set_name, emitters in THEMES[slot].items():
            for emitter, spec in emitters.items():
                assert set(spec) <= {'c0', 'c1', 'k0', 'k1', 'scale'}, spec
                colours = [spec[k] for k in ('c0', 'c1') if k in spec]
                colours += [c for k in ('k0', 'k1') for c in spec.get(k, [])]
                for rgb in colours:
                    assert len(rgb) == 3 and all(0.0 <= c <= 1.0 for c in rgb), rgb
                    hue, sat, _ = colorsys.rgb_to_hsv(*[c / max(rgb) for c in rgb])
                    hue *= 360
                    if slot == 'c06':
                        # red, magenta and violet only; never the donors' green/blue/yellow.
                        assert sat < 0.12 or hue >= 268 or hue <= 8, (slot, emitter, rgb)
                    else:
                        # white, gold (30-55 deg) or light pink; always pale.
                        assert sat <= 0.56 and min(rgb) >= 0.44, (slot, emitter, rgb)
                        assert sat < 0.05 or 30 <= hue <= 62 or 320 <= hue <= 345, \
                            (slot, emitter, rgb)
                assert 1.0 <= spec.get('scale', 1.0) <= 1.5
    for texture_id, pins in TEXTURE_PINS.items():
        assert all(len(v) == 64 for v in pins.values()), f'texture {texture_id} is not pinned'
        assert TEXTURE_NAMES[texture_id]
    # recolour_pixels keeps alpha, value and neutral pixels.
    sample = np.zeros((2, 3, 4), dtype=np.uint8)
    sample[0, 0] = (255, 255, 255, 200)
    sample[0, 1] = (255, 40, 140, 90)
    sample[0, 2] = (255, 200, 80, 255)
    sample[1, 0] = (40, 60, 250, 17)
    themed = recolour_pixels(sample, TEXTURES['621195579']['c06'])
    assert np.array_equal(themed[..., 3], sample[..., 3])
    assert tuple(themed[0, 0]) == (255, 255, 255, 200) and tuple(themed[1, 1]) == (0, 0, 0, 0)
    assert np.array_equal(themed[..., :3].max(-1), sample[..., :3].max(-1))
    print(f'PASS: converter and texture codec present; {sum(len(e) for e in THEMES["c06"].values())} '
          f'emitters x {len(SLOTS)} slots themed inside their costume palettes; '
          f'{len(TEXTURES)} owned textures pinned')


def print_pins() -> None:
    """Bootstrap/audit aid: the payload hashes TEXTURE_PINS should hold."""
    work = Path(tempfile.mkdtemp(prefix='pins_', dir=scratch_root()))
    local = work / 'ef_elight_c06.eff'
    shutil.copyfile(ROOT / RECORDED_BASELINE / MOD_REL / BANK_REL.format(slot='c06'), local)
    folder = engine.dump(local, work / 'in')
    for texture_id, spec in TEXTURES.items():
        raw = next(folder.glob(f'*/*/{texture_id}.bntx')).read_bytes()
        pins = {'original': sha_bytes(raw)}
        for slot in SLOTS:
            first, second = recolour_bntx(raw, spec[slot]), recolour_bntx(raw, spec[slot])
            assert first == second, 'texture encoder is not deterministic'
            pins[slot] = sha_bytes(first)
        print(texture_id, texture_name(raw).decode(), json.dumps(pins, indent=1))
    shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--slot', choices=SLOTS)
    parser.add_argument('--recipient', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--verify-package', type=Path)
    parser.add_argument('--baseline', type=Path, help='package root holding the recorded inputs')
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--print-pins', action='store_true')
    args = parser.parse_args()
    if args.check:
        check()
    elif args.print_pins:
        print_pins()
    elif args.package:
        package(args.package, args.baseline)
    elif args.verify_package:
        verify_package(args.verify_package)
    elif args.preview:
        preview(args.preview, args.baseline)
    elif args.slot and args.recipient and args.output:
        check()
        record = apply(args.recipient, args.output, args.slot)
        Path(args.output).with_suffix('.theme.json').write_text(json.dumps(record, indent=2) + '\n')
        print(f'PASS: {args.slot} themed, sha256 {record["output_sha256"]}; '
              f'recorded input: {record["recipient_is_recorded_input"]}')
    else:
        parser.error('choose --check, --package, --verify-package, --preview, '
                     'or --slot with --recipient and --output')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
