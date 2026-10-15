"""Deterministic Shadow Purple / Golden Light texture and one-slot effect build.

NUTEXB resource names, BNTX containers, alpha channels, normal/parameter maps,
particle timing, and effect topology are preserved. Only colour data is edited.
The .eff colour offsets follow J0K3V/smash-effect-editor/src/eff.rs.
"""
from pathlib import Path
import colorsys
import hashlib
import json
import math
import shutil
import struct
import subprocess
import tempfile

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
CLI = HERE / 'texture_cli/ultimate_tex_cli.exe'
CACHE = HERE.parent / 'assets/color_themes'
REVISION = 'c07-white-gold-pink-sparkles-2'
NUTEXB_FORMATS = {0x400: 'Rgba8Unorm', 0x405: 'Rgba8UnormSrgb',
                 0x450: 'Bgra8Unorm', 0x455: 'Bgra8UnormSrgb',
                 0x480: 'BC1RgbaUnorm', 0x485: 'BC1RgbaUnormSrgb',
                 0x490: 'BC2RgbaUnorm', 0x495: 'BC2RgbaUnormSrgb',
                 0x4a0: 'BC3RgbaUnorm', 0x4a5: 'BC3RgbaUnormSrgb',
                 0x4e0: 'BC7RgbaUnorm', 0x4e5: 'BC7RgbaUnormSrgb'}
CACHE_USED = set()
BNTX_FORMATS = {0x1a01: 'BC1RgbaUnorm', 0x1a06: 'BC1RgbaUnormSrgb',
                0x1b01: 'BC2RgbaUnorm', 0x1b06: 'BC2RgbaUnormSrgb',
                0x1c01: 'BC3RgbaUnorm', 0x1c06: 'BC3RgbaUnormSrgb',
                0x2001: 'BC7RgbaUnorm', 0x2006: 'BC7RgbaUnormSrgb',
                0xb01: 'Rgba8Unorm', 0xb06: 'Rgba8UnormSrgb'}


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def u64(data, offset):
    return struct.unpack_from('<Q', data, offset)[0]


def convert(src, dst, fmt=None, no_mips=False):
    args = [str(CLI), str(src), str(dst)]
    if fmt:
        args += ['-f', fmt]
    if no_mips:
        args += ['--no-mipmaps']
    subprocess.run(args, check=True, capture_output=True)


GW_PALETTES = {
    'shadow': {'black_ha_col': [20, 19, 26], 'grayb_ha_col': [70, 67, 80],
               'gray_ha_col': [149, 145, 160], 'gray_tes_001_col_1': [20, 19, 26]},
    'gold': {'black_ha_col': [235, 233, 222], 'grayb_ha_col': [73, 71, 63],
             'gray_ha_col': [153, 149, 132], 'gray_tes_001_col_1': [235, 233, 222]},
}


def effect_rgb(rgb, theme):
    """Shift only Mythra's green/cyan accents; preserve HSV value.

    Neutral highlights, darkness, other hues and HDR values remain unchanged.
    The same operation is used for particle colour keys and trail pixels.
    """
    rgb = np.asarray(rgb, dtype=np.float64)
    hi, lo = rgb.max(axis=-1), rgb.min(axis=-1)
    span = hi - lo
    green = ((rgb[..., 1] == hi) | ((rgb[..., 2] == hi) & (rgb[..., 1] >= rgb[..., 0])))
    selected = green & (rgb[..., 1] >= hi * .5) & (span > np.maximum(hi * .08, 1e-8))
    hue = np.where(rgb[..., 1] == hi,
                   120 + 60 * (rgb[..., 2] - rgb[..., 0]) / np.maximum(span, 1e-20),
                   240 + 60 * (rgb[..., 0] - rgb[..., 1]) / np.maximum(span, 1e-20))
    target = (48 if theme == 'gold' else 278) + (hue - 150) * .18
    h = (target % 360) / 60
    x = 1 - np.abs(h % 2 - 1)
    palette = np.zeros(rgb.shape, dtype=np.float64)
    if theme == 'gold':
        palette[..., 0], palette[..., 1] = 1, x
    else:
        palette[..., 0], palette[..., 2] = x, 1
    shifted = lo[..., None] + span[..., None] * palette
    if theme == 'gold':
        # White-dominant champagne: reduce only the coloured accent's saturation.
        shifted = hi[..., None] + (shifted - hi[..., None]) * .30
    return np.where(selected[..., None], shifted, rgb)


def colour(image, mode):
    a = np.array(image.convert('RGBA'))
    rgb = a[..., :3].astype(np.float32) / 255
    hi = rgb.max(axis=-1)
    lo = rgb.min(axis=-1)
    lum = rgb @ np.array([.2126, .7152, .0722])
    if mode.startswith('gw_'):
        _, theme, role = mode.split('_', 2)
        palette = GW_PALETTES[theme]
        if role == 'portrait':
            # Vanilla black artwork preserves its body and two outline shades.
            anchors = np.array([8, 66, 132, 255]) / 255
            colours = np.array([palette['black_ha_col'], palette['grayb_ha_col'],
                                palette['gray_ha_col'], [255, 255, 255]]) / 255
            out = np.stack([np.interp(lum, anchors, colours[:, c]) for c in range(3)], axis=-1)
        else:
            base = np.array(palette[role]) / 255
            out = base + (lum - lum.mean())[..., None] * .2
        out = np.where((a[..., 3] == 0)[..., None], 0, out)
    elif mode in ('fx_gold', 'fx_shadow'):
        out = effect_rgb(rgb, mode[3:])
    elif mode == 'gold_fx':
        # Black remains black for additive blending; white cores remain luminous.
        white = np.clip((lo / np.maximum(hi, .001) - .65) / .35, 0, 1)
        gold = np.array([1., .76, .12])
        out = hi[..., None] * (gold + white[..., None] * (np.array([1., .96, .78]) - gold))
    elif mode == 'c07_trail_gold':
        # Transform c06's dark crimson/magenta trails to white and radiant light gold.
        # In c06 trail, non-zero pixels have R ~50-134, G ~0-50, B ~0-99.
        lum = rgb @ np.array([.50, .20, .30])
        t = np.clip((lum - 0.10) / (0.42 - 0.10), 0.0, 1.0)
        edge_gold = np.array([248.0, 215.0, 140.0]) / 255.0
        mid_gold  = np.array([255.0, 235.0, 170.0]) / 255.0
        core_white = np.array([255.0, 255.0, 255.0]) / 255.0
        mask_low = (t < 0.5)[..., None]
        t_low = (t / 0.5)[..., None]
        t_high = (np.maximum(0.0, (t - 0.5) / 0.5) ** 0.8)[..., None]
        out = np.where(mask_low,
                       edge_gold + (mid_gold - edge_gold) * t_low,
                       mid_gold + (core_white - mid_gold) * t_high)
        out = np.where((a[..., 3] == 0)[..., None], 0, out)
    else:
        # Neutral armour/hair becomes ivory; coloured trims and crystals become gold.
        sat = hi - lo
        gold = np.array([1., .78, .22])
        ivory = np.array([1., .97, .85])
        shade = np.clip(.12 + .88 * lum, 0, 1)
        if mode in ('gold_armour', 'gold_hair', 'gold_portrait_ivory'):
            # Lift midtones for ivory metal and luminous hair, retaining deep shadows.
            shade = np.where(lum < .08, lum * 1.5, .28 + .72 * np.sqrt(lum))
        accent = np.clip(sat * 4, 0, 1)
        if mode == 'gold_hair':
            accent = np.maximum(accent, .6)
        out = shade[..., None] * (ivory + accent[..., None] * (gold - ivory))
        if mode == 'gold_portrait_ivory':
            # Portrait skin/lips keep the donor's natural colour, matching the model.
            skin = ((rgb[..., 0] > rgb[..., 1] * 1.12)
                    & (rgb[..., 1] > rgb[..., 2] * 1.12)
                    & (rgb[..., 0] > .24) & (sat < .6))
            lips = ((rgb[..., 0] > rgb[..., 1] * 1.5)
                    & (rgb[..., 0] > rgb[..., 2] * 1.2))
            out = np.where((skin | lips)[..., None], rgb, out)
    a[..., :3] = np.rint(np.clip(out, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(a, 'RGBA')


def cached(src, dst, mode, operation):
    key = hashlib.sha256(src.read_bytes() + (REVISION + mode).encode()).hexdigest()
    cache = CACHE / (key + src.suffix)
    CACHE_USED.add(cache.name)
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        operation(src, cache, mode)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cache, dst)


def nutexb(src, dst, mode):
    def run(source, target, theme):
        raw = source.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            convert(source, td / 'source.png')
            fmt = NUTEXB_FORMATS[u32(raw, len(raw)-32)]
            original_image = Image.open(td / 'source.png').convert('RGBA')
            themed_image = colour(original_image, theme)
            if np.array_equal(np.array(original_image), np.array(themed_image)):
                target.write_bytes(raw)
                return
            themed_image.save(td / 'new.png')
            convert(td / 'new.png', td / 'new.nutexb', fmt, u32(raw, len(raw)-24) == 1)
            new = bytearray((td / 'new.nutexb').read_bytes())
            # Resource names are independent of the output filename and slot.
            new[-108:-44] = raw[-108:-44]
            assert new[-44:-28] == raw[-44:-28], f'NUTEXB dimensions/format changed: {source}: {raw[-44:-28].hex()} -> {new[-44:-28].hex()} ({fmt})'
            assert new[-24:-20] == raw[-24:-20], 'NUTEXB mip count changed'
            target.write_bytes(new)
    cached(src, dst, mode, run)


def brtis(data):
    table = u64(data, 0x28)
    return [u64(data, table + i * 8) for i in range(u32(data, 0x24))]


def gob_offsets(width, height, bpp, block_height):
    """Tegra block-linear byte addresses for one 2D mip (in format blocks)."""
    x = np.arange(width * bpp, dtype=np.int64)[None, :]
    y = np.arange(height, dtype=np.int64)[:, None]
    stride = (width * bpp + 63) // 64
    return ((y // (8 * block_height)) * 512 * block_height * stride
            + (x // 64) * 512 * block_height + ((y % (8 * block_height)) // 8) * 512
            + ((x % 64) // 32) * 256 + ((y % 8) // 2) * 64
            + ((x % 32) // 16) * 32 + (y % 2) * 16 + x % 16).ravel()


def replace_bntx_texture(original, brti, encoded):
    nb = brtis(encoded)[0]
    assert original[brti+0x1c:brti+0x34] == encoded[nb+0x1c:nb+0x34]
    assert original[brti+0x12:brti+0x14] == encoded[nb+0x12:nb+0x14] == b'\0\0'
    count = struct.unpack_from('<H', original, brti+0x16)[0]
    new_count = struct.unpack_from('<H', encoded, nb+0x16)[0]
    assert new_count >= count
    width, height = u32(original, brti+0x24), u32(original, brti+0x28)
    fmt = u32(original, brti+0x1c)
    compressed = fmt >> 8 >= 0x1a
    bpp = (8 if fmt >> 8 == 0x1a else 16) if compressed else 4
    old_mips, new_mips = u64(original, brti+0x70), u64(encoded, nb+0x70)
    for level in range(count):
        w, h = max(width >> level, 1), max(height >> level, 1)
        if compressed:
            w, h = (w+3)//4, (h+3)//4
        # Block height shrinks at each mip; both containers may choose different bases.
        target_bh = min(1 << u32(original, brti+0x34), 1 << max(0, ((h+7)//8-1).bit_length()))
        source_bh = min(1 << u32(encoded, nb+0x34), 1 << max(0, ((h+7)//8-1).bit_length()))
        to = u64(original, old_mips + level * 8)
        fr = u64(encoded, new_mips + level * 8)
        target_indexes = to + gob_offsets(w, h, bpp, target_bh)
        source_indexes = fr + gob_offsets(w, h, bpp, source_bh)
        np.frombuffer(original, dtype=np.uint8)[target_indexes] = np.frombuffer(encoded, dtype=np.uint8)[source_indexes]


def bntx_data(raw, mode):
    result = bytearray(raw)
    count = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for brti in brtis(raw):
            fmt = u32(raw, brti+0x1c)
            if fmt not in BNTX_FORMATS:
                # Scalar/normal masks carry no RGB colour and remain byte-identical.
                continue
            single = bytearray(raw)
            struct.pack_into('<I', single, 0x24, 1)
            struct.pack_into('<Q', single, u64(raw, 0x28), brti)
            (td / 'source.bntx').write_bytes(single)
            convert(td / 'source.bntx', td / 'source.png')
            original_image = Image.open(td / 'source.png').convert('RGBA')
            themed_image = colour(original_image, mode)
            if np.array_equal(np.array(original_image), np.array(themed_image)):
                continue
            themed_image.save(td / 'new.png')
            mips = struct.unpack_from('<H', raw, brti+0x16)[0]
            convert(td / 'new.png', td / 'new.bntx', BNTX_FORMATS[fmt], mips == 1)
            replace_bntx_texture(result, brti, (td / 'new.bntx').read_bytes())
            count += 1
    assert len(result) == len(raw)
    return result, count


def bntx(src, dst, mode):
    cached(src, dst, mode, lambda source, target, theme:
           target.write_bytes(bntx_data(source.read_bytes(), theme)[0]))


PURE_WHITE = np.array([1.0, 1.0, 1.0])
LIGHT_IVORY = np.array([1.0, 0.98, 0.94])
LIGHT_GOLD = np.array([1.0, 0.88, 0.55])
CHAMPAGNE_GOLD = np.array([0.98, 0.82, 0.44])
PALE_GOLD = np.array([1.0, 0.92, 0.68])
LIGHT_PINK = np.array([1.0, 0.78, 0.88])
SOFT_PINK = np.array([1.0, 0.82, 0.90])
BLUSH_PINK = np.array([0.98, 0.72, 0.84])


def emitter_hierarchy(raw):
    """Walk VFXB section links, yielding (eset_name, emtr_name, data, const)."""
    vfx = raw.index(b'VFXB')
    version = struct.unpack_from('<H', raw, vfx+10)[0]
    const = 2392 if version >= 37 or version <= 21 else 2384

    def siblings(pos, limit):
        seen = set()
        for _ in range(limit):
            assert pos not in seen and pos + 32 <= len(raw)
            seen.add(pos)
            yield pos
            step = u32(raw, pos+12)
            if step == 0xffffffff:
                return
            assert step > 0
            pos += step

    section = vfx + struct.unpack_from('<H', raw, vfx+22)[0]
    for pos in siblings(section, 100):
        if raw[pos:pos+4] != b'ESTA':
            continue
        for eset in siblings(pos+u32(raw, pos+8), max(1, u32(raw, pos+28))):
            assert raw[eset:eset+4] == b'ESET'
            eset_name = raw[eset+0x30:eset+0x70].split(b'\x00')[0].decode('latin1', 'replace')
            sub = u32(raw, eset+8)
            if sub == 0xffffffff:
                continue
            for emtr in siblings(eset+sub, max(1, u32(raw, eset+28))):
                assert raw[emtr:emtr+4] == b'EMTR'
                emtr_name_offset = emtr + u32(raw, emtr+20) + 16
                emtr_name = raw[emtr_name_offset:emtr_name_offset+32].split(b'\x00')[0].decode('latin1', 'replace')
                data = emtr_name_offset + 64
                assert data + const + 32 <= len(raw)
                yield eset_name, emtr_name, data, const


def emitter_data(raw):
    for _, _, data, const in emitter_hierarchy(raw):
        yield data, const


def classify_emitter(eset_name, emtr_name):
    if 'Change' in eset_name:
        return 'switch'
    if any(k in emtr_name.lower() for k in ['spark', 'star', 'flashparticle', 'sparkline']):
        return 'sparkle'
    if 'Light' in eset_name and any(k in emtr_name.lower() for k in ['spark', 'pointlight', 'flash']):
        return 'sparkle'
    if eset_name == 'P_ElightAppealSpark':
        return 'sparkle'
    return 'sword_dark'


def transform_c07_emitter_rgb(rgb, eset_name, emtr_name, role):
    rgb = np.array(rgb, dtype=np.float32)
    max_c = rgb.max()
    min_c = rgb.min()
    span = max_c - min_c

    if max_c < 1e-4:
        return rgb
    if span < max_c * 0.05:
        return rgb

    norm_rgb = np.clip(rgb / max_c, 0, 1)
    h, s, v = colorsys.rgb_to_hsv(norm_rgb[0], norm_rgb[1], norm_rgb[2])
    hue_deg = h * 360.0

    if role in ('switch', 'sparkle'):
        # Sparkle & Switch effects: white, light gold, and a bit of light pink
        if 250 <= hue_deg <= 350 or hue_deg < 15 or hue_deg > 350:
            # Magenta / Purple / Red-Pink -> Light Pink
            pink = LIGHT_PINK if max_c >= 0.8 else BLUSH_PINK
            white_blend = np.clip((0.25 - s) / 0.25, 0, 1)
            out = pink * (1 - white_blend) + PURE_WHITE * white_blend
            return out * max_c
        elif 15 <= hue_deg < 75:
            # Gold / amber / orange -> Light Gold
            gold = PALE_GOLD if max_c >= 0.8 else LIGHT_GOLD
            white_blend = np.clip((0.25 - s) / 0.25, 0, 1)
            out = gold * (1 - white_blend) + PURE_WHITE * white_blend
            return out * max_c
        else:
            return PALE_GOLD * max_c
    else:
        # Sword / dark effects: white / light gold
        lifted_val = max(max_c, 0.70 + 0.30 * max_c)
        is_core = any(k in emtr_name for k in ['center', 'root', 'Add', 'sword2']) or min_c > 0.05 or s < 0.4

        if is_core:
            # Brilliant White / Light Ivory core
            blend = np.clip(s, 0.0, 1.0)
            out = PURE_WHITE * (1 - 0.20 * blend) + PALE_GOLD * (0.20 * blend)
            return out * max(0.95, lifted_val)
        else:
            # Radiant Light Gold body / aura
            is_aura = any(k in emtr_name.lower() for k in ['aura', 'ring', 'wind', 'tornado', 'flare'])
            gold = CHAMPAGNE_GOLD if is_aura else LIGHT_GOLD
            white_blend = np.clip((0.3 - s) / 0.3, 0, 1)
            out = gold * (1 - white_blend) + LIGHT_IVORY * white_blend
            return out * lifted_val


def build_c07_effect_bank(src, dst, vanilla_path):
    def run(source, target, theme):
        raw = bytearray(source.read_bytes())
        vanilla_raw = vanilla_path.read_bytes()

        modified_emitters = 0
        changed_offsets = set()

        for eset_name, emtr_name, data, const in emitter_hierarchy(raw):
            counts = struct.unpack_from('<4I', raw, data+16)
            assert all(n <= 8 for n in counts)
            offsets = [data+const, data+const+16]
            offsets += [data+880+channel*128+key*16
                        for channel in (0, 2) for key in range(counts[channel])]

            is_mod = False
            for off in offsets:
                c_rgb = struct.unpack_from('<3f', raw, off)
                v_rgb = struct.unpack_from('<3f', vanilla_raw, off)
                if not np.allclose(c_rgb, v_rgb, atol=1e-4):
                    is_mod = True
                    break

            if is_mod:
                role = classify_emitter(eset_name, emtr_name)
                for off in offsets:
                    c_rgb = struct.unpack_from('<3f', raw, off)
                    new_rgb = transform_c07_emitter_rgb(c_rgb, eset_name, emtr_name, role)
                    struct.pack_into('<3f', raw, off, *new_rgb)
                    changed_offsets.update(range(off, off+12))
                modified_emitters += 1

        assert modified_emitters > 0

        # RGB texture payloads inside BNTX
        start = raw.index(b'BNTX')
        size = u32(raw, start+0x1c)
        colours, textures = bntx_data(raw[start:start+size], 'fx_gold')
        raw[start:start+size] = colours

        original = source.read_bytes()
        assert all(original[i] == raw[i] for i in range(len(raw))
                   if i not in changed_offsets and not start <= i < start+size)
        assert len(original) == len(raw)
        target.write_bytes(raw)
        print(f'c07 effect bank: {modified_emitters} emitters updated to white/gold/light pink; {textures} RGB textures')

    cached(src, dst, 'c07_white_gold_pink_sparkles_bank', run)


def gw_texture(src, dst, slot):
    theme = 'shadow' if slot == 'c06' else 'gold'
    nutexb(src, dst, f'gw_{theme}_{src.stem}')


def build(export, mod, package, mythra_skin):
    record = {'effect_slots': {}, 'mythra_c07': {}, 'ui': {}}
    for kind in ('body', 'esword'):
        src = export / f'fighter/elight/model/{kind}/c07'
        dst = mod / f'fighter/elight/model/{kind}/c07'
        files = []
        for texture in sorted(src.glob('*.nutexb')):
            name = texture.name
            # Skin, eyes, normals and material parameters retain the vanilla data.
            if ('_col.' in name or '_emi.' in name) and not name.startswith(('skin_', 'eye_')):
                mode = 'gold_hair' if name == 'def_light_002_col.nutexb' else 'gold_armour'
                if '_emi.' in name or name == 'def_light_004_col.nutexb':
                    mode = 'gold_fx'
                if kind == 'esword' and (name == 'alp_light_002_col.nutexb'
                                         or name == 'def_light_004_col.nutexb'
                                         or '_emi.' in name):
                    # Sword glow/edge masks use the same champagne palette as particles.
                    # Preserve black instead of lifting it to brown with armour shading.
                    mode = 'fx_gold'
                nutexb(texture, dst / name, mode)
                files.append(name)
        record['mythra_c07'][kind] = files
    for slot in ('c06', 'c07'):
        # Both c06 and c07 start from the Black & Pink Mythra dark effects donor bank & trails.
        src = mythra_skin / 'effect/fighter/elight'
        dst = mod / 'effect/fighter/elight'
        dst.mkdir(parents=True, exist_ok=True)
        eff = dst / f'ef_elight_{slot}.eff'
        if slot == 'c06':
            shutil.copy2(src / 'ef_elight.eff', eff)
        else:
            build_c07_effect_bank(src / 'ef_elight.eff', eff, export / 'effect/fighter/elight/ef_elight.eff')
        trail_names = []
        for texture in sorted((src / 'trail').glob('*.nutexb')):
            target = dst / f'trail_{slot}' / texture.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if slot == 'c06':
                shutil.copy2(texture, target)
            else:
                if texture.name in ('tex_elight_sword2.nutexb', 'tex_elight_sword5.nutexb'):
                    shutil.copy2(texture, target)
                else:
                    nutexb(texture, target, 'c07_trail_gold')
            trail_names.append(texture.name)
        # One file per internal resource name in the eflame slot folder (T-0054): the old
        # tex_eflame_* byte-copy aliases and unrequestable sword4/5 made two files register
        # the same TEX_*_C<slot> name. Cloud's ribbon pair, Mythra's five and eflame's three.
        import build_cloud_trail
        record.setdefault('eflame_trails', {})[slot] = build_cloud_trail.build_eflame_trail_folder(
            dst / f'trail_{slot}', mod / f'effect/fighter/eflame/trail_{slot}', slot)
        assert trail_names
        record['effect_slots'][slot] = {'bank': eff.relative_to(mod).as_posix(), 'trails': trail_names}
    # Recolour the existing G&W portraits after the UI copy step.
    ui = mod / 'ui/replace_patch/chara'
    for slot in ('06', '07'):
        portraits = list(ui.rglob(f'*eflame*_{slot}.bntx'))
        for portrait in portraits:
            bntx(portrait, portrait, 'gw_shadow_portrait' if slot == '06' else 'gw_gold_portrait')
        record['ui']['eflame_c'+slot] = len(portraits)
    count = 0
    for source in sorted((export / 'ui/replace_patch/chara').rglob('*elight*_07.bntx')):
        target = ui / source.relative_to(export / 'ui/replace_patch/chara')
        bntx(source, target, 'gold_portrait_ivory')
        count += 1
    assert count > 0
    record['ui']['elight_c07'] = count
    plugin = HERE / 'one_slot_effects/libone_slot_eff.nro'
    assert plugin.is_file(), '13.0.4 One Slot Effects plugin missing'
    target = package / 'atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libone_slot_eff.nro'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(plugin, target)
    assert not (mod / 'effect/fighter/elight/ef_elight.eff').exists()
    assert not (mod / 'effect/fighter/elight/trail').exists()
    record['plugin_sha256'] = hashlib.sha256(plugin.read_bytes()).hexdigest()
    record['transform_revision'] = REVISION
    record['cache_files'] = sorted(CACHE_USED)
    return record
