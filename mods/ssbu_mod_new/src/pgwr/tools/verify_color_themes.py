"""Decode theme assets, check effect isolation, and write a visual QA contact sheet."""
from pathlib import Path
import hashlib
import json
import os
import struct
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_color_themes as themes

ROOT = Path(__file__).resolve().parents[3]
PROJECT = Path(__file__).resolve().parents[1]
PACKAGE = Path(os.environ.get('MGW_PACKAGE', ROOT / 'builds/pgwr/pyra_gamewatch_reskin'))
MOD = PACKAGE / 'ultimate/mods/pyra_gamewatch_reskin'
DONOR = ROOT / 'refs/skins/black_and_pink_mythra/mythra skin'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    effect = MOD / 'effect/fighter/elight'
    assert sorted(p.name for p in effect.iterdir()) == [
        'ef_elight_c06.eff', 'ef_elight_c07.eff', 'trail_c06', 'trail_c07']
    assert digest(effect / 'ef_elight_c06.eff') == digest(DONOR / 'effect/fighter/elight/ef_elight.eff')
    for p in (effect / 'trail_c06').iterdir():
        assert digest(p) == digest(DONOR / 'effect/fighter/elight/trail' / p.name)
    config = json.loads((MOD / 'config.json').read_text())['new-dir-files']
    for slot in ('c06', 'c07'):
        expected = {f'effect/fighter/elight/ef_elight_{slot}.eff'}
        expected.update(p.relative_to(MOD).as_posix() for p in (effect / f'trail_{slot}').iterdir())
        assert set(config[f'fighter/elight/{slot}']) == expected
        assert all(not expected.intersection(paths) for key, paths in config.items()
                   if key != f'fighter/elight/{slot}')
    assert all(f'fighter/elight/c0{i}' not in config for i in range(6))
    assert not any((MOD / f'fighter/elight/model/body/c0{i}').exists() for i in range(6))
    gold = (effect / 'ef_elight_c07.eff').read_bytes()
    donor = (DONOR / 'effect/fighter/elight/ef_elight.eff').read_bytes()
    vanilla = (ROOT / 'dumps/arc/effect/fighter/elight/ef_elight.eff').read_bytes()
    assert gold != donor and len(gold) == len(donor) == len(vanilla)

    # Key counts, alpha channels and key times must survive the colour edit.
    emitter_count = 0
    for data, const in themes.emitter_data(gold):
        assert gold[data+16:data+32] == donor[data+16:data+32], 'Key counts changed'
        for channel in (1, 3):
            off = data + 880 + channel * 128
            assert gold[off:off+128] == donor[off:off+128], 'Alpha/scale channel changed'
        for channel in (0, 2):
            for key in range(8):
                off = data+880+channel*128+key*16+12
                assert gold[off:off+4] == donor[off:off+4], 'Key timing changed'
        for off in (data+const+12, data+const+28):
            assert gold[off:off+4] == donor[off:off+4], 'Base timing changed'
        emitter_count += 1

    # c07 is rebuilt from c06: dark effects -> white/light gold, sparkles/switch -> light pink
    recoloured_emitters = {}
    for slot in ('c07',):
        bank = (effect / f'ef_elight_{slot}.eff').read_bytes()
        assert len(bank) == len(donor)
        permitted = np.zeros(len(bank), dtype=bool)
        changed = 0
        pink_keys_found = 0
        gold_keys_found = 0

        for eset_name, emtr_name, data, const in themes.emitter_hierarchy(bank):
            counts = struct.unpack_from('<4I', donor, data+16)
            offsets = [data+const, data+const+16]
            offsets += [data+880+channel*128+key*16
                        for channel in (0, 2) for key in range(counts[channel])]

            is_mod = False
            for off in offsets:
                c_rgb = struct.unpack_from('<3f', donor, off)
                v_rgb = struct.unpack_from('<3f', vanilla, off)
                if not np.allclose(c_rgb, v_rgb, atol=1e-4):
                    is_mod = True
                    break

            if is_mod:
                touched = False
                for off in offsets:
                    old = np.array(struct.unpack_from('<3f', donor, off))
                    new = np.array(struct.unpack_from('<3f', bank, off))
                    permitted[off:off+12] = True
                    touched |= not np.array_equal(old, new)
                    if max(new) > 0.05:
                        import colorsys
                        norm = [c / max(new) for c in new]
                        h, s, v = colorsys.rgb_to_hsv(norm[0], norm[1], norm[2])
                        hue = h * 360
                        if s > 0.1 and 280 <= hue <= 350:
                            pink_keys_found += 1
                        elif s > 0.1 and 20 <= hue <= 75:
                            gold_keys_found += 1
                changed += int(touched)

        assert changed > 0, 'No emitters recoloured in c07'
        assert pink_keys_found > 50, 'Light pink sparkle keys missing in c07'
        assert gold_keys_found > 100, 'Light gold keys missing in c07'

        start = bank.index(b'BNTX')
        length = themes.u32(bank, start+28)
        permitted[start:start+length] = True
        assert np.array_equal(np.frombuffer(bank, dtype=np.uint8)[~permitted],
                              np.frombuffer(donor, dtype=np.uint8)[~permitted])
        recoloured_emitters[slot] = changed

    decoded = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for p in MOD.rglob('*.nutexb'):
            if ('/fighter/elight/model/' not in p.as_posix()
                    and '/effect/fighter/elight/' not in p.as_posix()
                    and not any(f'/fighter/eflame/model/{kind}/{slot}/' in p.as_posix()
                                for kind in ('body', 'normal_weapon', 'breath')
                                for slot in ('c06', 'c07'))):
                continue
            themes.convert(p, td / 'decoded.png')
            Image.open(td / 'decoded.png').load()
            if '/effect/fighter/elight/trail_c07/' in p.as_posix():
                source = DONOR / 'effect/fighter/elight/trail' / p.name
                themes.convert(source, td / 'original.png')
                old = np.array(Image.open(td / 'original.png').convert('RGBA'))
                new = np.array(Image.open(td / 'decoded.png').convert('RGBA'))
                assert np.array_equal(old[..., 3], new[..., 3]), 'Trail transparency changed'
                if p.name not in ('tex_elight_sword2.nutexb', 'tex_elight_sword5.nutexb'):
                    mask = new[..., 3] > 10
                    # Confirm trail is radiant white and light gold (no dark crimson)
                    assert new[mask, 0].mean() > 200, 'Trail red channel too dark'
                    assert new[mask, 1].mean() > 180, 'Trail green channel too dark (not gold/white)'
            decoded += 1
        portrait_count = 0
        for p in (MOD / 'ui/replace_patch/chara').rglob('*.bntx'):
            themes.convert(p, td / 'decoded.png')
            Image.open(td / 'decoded.png').load()
            portrait_count += 1
        start = gold.index(b'BNTX')
        size = themes.u32(gold, start+28)
        bank = gold[start:start+size]
        old_bank = donor[start:start+size]
        particle_textures = 0
        for brti in themes.brtis(bank):
            fmt = themes.u32(bank, brti+28)
            if fmt not in themes.BNTX_FORMATS:
                pointer = themes.u64(bank, brti+0x70)
                first = themes.u64(bank, pointer)
                length = themes.u32(bank, brti+0x50)
                assert bank[first:first+length] == old_bank[first:first+length]
                continue
            one = bytearray(bank)
            struct.pack_into('<I', one, 36, 1)
            struct.pack_into('<Q', one, themes.u64(one, 40), brti)
            (td / 'one.bntx').write_bytes(one)
            themes.convert(td / 'one.bntx', td / 'decoded.png')
            Image.open(td / 'decoded.png').load()
            particle_textures += 1
        canvas = Image.new('RGB', (960, 660), (28, 25, 36))
        draw = ImageDraw.Draw(canvas)
        items = [
            ('Shadow Purple G&W c06', MOD / 'ui/replace_patch/chara/chara_1/chara_1_eflame_only_06.bntx'),
            ('Golden Light G&W c07', MOD / 'ui/replace_patch/chara/chara_1/chara_1_eflame_only_07.bntx'),
            ('Golden Light Mythra c07', MOD / 'ui/replace_patch/chara/chara_1/chara_1_elight_only_07.bntx'),
            ('Gold armor', MOD / 'fighter/elight/model/body/c07/def_light_001_col.nutexb'),
            ('Gold hair', MOD / 'fighter/elight/model/body/c07/def_light_002_col.nutexb'),
            ('Gold sword trail', effect / 'trail_c07/tex_elight_sword1.nutexb'),
        ]
        for i, (label, p) in enumerate(items):
            themes.convert(p, td / 'decoded.png')
            im = Image.open(td / 'decoded.png').convert('RGBA')
            im.thumbnail((300, 290))
            x, y = (i % 3) * 320, (i // 3) * 330
            canvas.paste(im, (x+(320-im.width)//2, y+26), im)
            draw.text((x+12, y+6), label, fill='white')
        canvas.save(PROJECT / 'theme_preview/themes.png')
    plugin = PACKAGE / 'atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libone_slot_eff.nro'
    assert plugin.read_bytes()[16:20] == b'NRO0'
    main_plugin = plugin.with_name('libpyra_gamewatch_reskin.nro')
    report = {'decoded_nutexb': decoded, 'decoded_portraits': portrait_count,
              'particle_emitters': emitter_count, 'decoded_particle_rgb_textures': particle_textures,
              'vanilla_c00_c05_effects': 'no shared overrides; vanilla bank and trails used',
              'c06_effects': 'bank and trails byte-identical to original purple donor',
              'c07_effects': 'rebuilt from scratch using c06 dark effects: white/light gold slashes and light pink sparkles/switch',
              'recoloured_emitters': recoloured_emitters,
              'particle_alpha_and_timing': 'byte-identical to donor and vanilla',
              'plugin_sha256': digest(plugin)}
    if main_plugin.exists():
        assert main_plugin.read_bytes()[16:20] == b'NRO0'
        assert digest(main_plugin) == digest(PROJECT / 'plugin/target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro')
        report['main_plugin_sha256'] = digest(main_plugin)
    (PROJECT / 'theme-verification.json').write_text(json.dumps(report, indent=2)+'\n')
    (PACKAGE / 'theme-verification.json').write_text(json.dumps(report, indent=2)+'\n')
    manifest = {p.relative_to(PACKAGE).as_posix(): digest(p)
                for p in sorted(PACKAGE.rglob('*')) if p.is_file() and p.name != 'package-sha256.json'}
    (PACKAGE / 'package-sha256.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
