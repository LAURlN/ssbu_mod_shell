"""Generate owned native side-B initialization/collision code (v1.1.0).

Complete 13.0.4 instruction spans are relocated, including error paths. Only
the three user-approved entry interceptions are used by these copies; the
lightning map copy is for an owned weapon script, not another interception.
Hero fighter state reads become named callbacks. Genuine weapon layout and
generic engine calls remain unchanged. Spark's class parameter fields are
decoded from the native vl decoder and pinned PRC, including its unusual small
level half-width read from the medium field. --check is the source smoke test.
The complete port additionally needs recipient event handling; see the pinned
link_event_native_audit. No build, package or installation is performed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import tomllib
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src/pgwr/tools')]
from main_image import MainImage
import prc

SPANS = [('spark_init', 0x85d580, 0x85dad0),
         ('lightning_init', 0x85dad0, 0x85e040),
         ('spark_class', 0x33cbb20, 0x33cbbfc),
         ('lightning_map', 0x33cabd0, 0x33cb1d8),
         ('lightning_effect', 0x33ca910, 0x33caa70),
         ('lightning_log_alloc', 0x855b00, 0x855ba8),
         ('link_receiver', 0x8555a0, 0x855b00),
         ('lightning_log_release', 0x851ac0, 0x851c30)]
OUT = ROOT / 'src/pgwr/plugin/src/mythra/hero_side_b'


def generate():
    image = MainImage()
    assert hashlib.sha256(image.data).hexdigest() == 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    vl_path = ROOT / cfg['dumps']['arc'] / 'fighter/brave/param/vl.prc'
    vl = dict(prc.read(vl_path)[1])
    regs, parent, fallback, fields = {}, None, None, {}
    keys = (0x24394ee70, 0x41cff903b, 0xab2607d2e)  # up, down, half_width
    # This is the spark portion of the native decoder, beyond fireball's range.
    for i in image.disasm(0x880000, 0x2700):
        args = i.op_str.split(', ')
        if i.mnemonic == 'mov' and len(args) == 2 and args[1].startswith('#'):
            regs[args[0]] = int(args[1][1:], 0) & ((1 << 64) - 1)
        elif i.mnemonic == 'movk':
            shift = int(args[2].split('#')[1]) if len(args) == 3 else 0
            regs[args[0]] = ((regs.get(args[0], 0) & ~(65535 << shift)) | (int(args[1][1:], 0) << shift))
            value = regs[args[0]]
            if shift == 32 and value in vl and vl[value][0] == 'struct' and set(keys).issubset(dict(vl[value][1])):
                parent = value
        elif i.mnemonic == 'fmov' and args[0] == 's0' and args[1].startswith('#'):
            fallback = float(args[1][1:])
        elif i.mnemonic == 'str' and i.op_str.startswith('s0, [x16, #'):
            offset = int(i.op_str.split('#')[1].rstrip(']'), 0)
            if offset in (0x23c, 0x240, 0x244, 0x24c, 0x250, 0x254, 0x25c, 0x260, 0x264):
                column = ((offset - 0x23c) % 0x10) // 4
                kind, value = dict(vl[parent][1])[keys[column]]
                assert kind == 'float' and value == fallback, (hex(offset), hex(parent), value, fallback)
                fields[offset] = {'parent_hash': hex(parent), 'child_hash': hex(keys[column]), 'value': value,
                                  'decoder_store': hex(i.address)}
    assert len(fields) == 9
    callbacks = {a: 'pgwr_hero_s_special_float' for a in (0x85d640, 0x85d67c, 0x85d6b8, 0x85db90, 0x85dbbc)}
    callbacks.update({0x85d704: 'pgwr_hero_s_generate_x', 0x85d724: 'pgwr_hero_s_generate_y',
                      0x85d75c: 'pgwr_hero_s_generate_lr', 0x85d934: 'pgwr_hero_s_spark_log_get',
                      0x85d9a4: 'pgwr_hero_s_spark_log_set', 0x85d9b8: 'pgwr_hero_s_spark_log_get',
                      0x85d9d0: 'pgwr_hero_s_spark_log_ref', 0x85dce0: 'pgwr_hero_s_lightning_offset',
                      0x85dd7c: 'pgwr_hero_s_lightning_owner', 0x85dd94: 'pgwr_hero_s_lightning_team',
                      0x33cae14: 'pgwr_hero_s_explosion_get', 0x33cae74: 'pgwr_hero_s_explosion_set',
                      0x85defc: 'pgwr_hero_s_lightning_article_count',
                      0x85df18: 'pgwr_hero_s_lightning_article_count',
                      0x855b20: 'pgwr_hero_s_lightning_log_get',
                      0x8556f8: 'pgwr_hero_s_lightning_owner_set',
                      0x855710: 'pgwr_hero_s_lightning_team_set',
                      0x855730: 'pgwr_hero_s_lightning_log_get',
                      0x8557a0: 'pgwr_hero_s_lightning_log_set',
                      0x855854: 'pgwr_hero_s_lightning_log_get',
                      0x8558bc: 'pgwr_hero_s_spark_log_ref_get',
                      0x8558d8: 'pgwr_hero_s_spark_log_ref_set',
                      0x855900: 'pgwr_hero_s_spark_log_get',
                      0x855adc: 'pgwr_hero_s_spark_log_set',
                      0x851af8: 'pgwr_hero_s_lightning_log_get'})
    changes = {0x85d604: 'cmp w0, #0x1fa', 0x85d60c: 'cmp w0, #0x1fb', 0x85d614: 'cmp w0, #0x1fd',
               0x33cbb38: 'adrp x21, PGWR_HERO_S_SPARK_PARAMS',
               0x33cbb3c: 'add x21, x21, :lo12:PGWR_HERO_S_SPARK_PARAMS',
               0x33cbb40: 'nop // Removed Hero parameter-manager dereference',
               0x855ba4: 'b pgwr_hero_s_lightning_log_set',
               0x8556cc: 'cmp w8, #0x1fc',
               0x851c24: 'b pgwr_hero_s_lightning_log_set'}
    # Only the approved wrapper enters this copy, for four measured event kinds.
    # Recipient article IDs are allocated by clone_weapon, never Hero's slot 2.
    for a in (0x8557ac, 0x8557d0, 0x855944, 0x855974,
              0x8559b8, 0x8559e8, 0x851b0c, 0x851b2c, 0x851b74):
        changes[a] = ('adrp x16, PGWR_HERO_S_LIGHTNING_SLOT\n'
                      'ldr w1, [x16, :lo12:PGWR_HERO_S_LIGHTNING_SLOT]')
    helpers, replaced = set(), set()
    asm = ['// Generated by tools/gen_hero_side_b_native.py v1.1.0.', '.text',
           '.hidden PGWR_HERO_S_GAME_BASE', '.hidden PGWR_HERO_S_SPARK_PARAMS',
           '.hidden PGWR_HERO_S_LIGHTNING_SLOT']

    def address(reg, offset):
        return [f'adrp {reg}, PGWR_HERO_S_GAME_BASE', f'ldr {reg}, [{reg}, :lo12:PGWR_HERO_S_GAME_BASE]',
                f'movz x16, #{offset & 65535}', f'movk x16, #{offset >> 16}, lsl #16', f'add {reg}, {reg}, x16']

    for name, start, end in SPANS:
        instructions = image.disasm(start, end - start)
        assert len(instructions) * 4 == end - start
        assert not any(re.search(r'\b[wx]16\b', i.op_str) for i in instructions), name
        addresses = {i.address for i in instructions}
        symbol = 'pgwr_hero_s_owned_' + name
        asm += ['.balign 4', '.global ' + symbol, '.type ' + symbol + ', %function', symbol + ':']
        for i in instructions:
            asm.append(f'.Lhero_s_{i.address:x}:')
            if i.address in changes:
                replaced.add(i.address); asm.append(changes[i.address])
            elif i.address in callbacks:
                assert i.mnemonic == 'blr', hex(i.address)
                replaced.add(i.address); asm.append('bl ' + callbacks[i.address])
            elif i.mnemonic in ('adrp', 'adr'):
                reg, target = i.op_str.split(', ')
                asm.extend(address(reg, int(target[1:], 0)))
            elif i.mnemonic in ('b', 'bl', 'cbz', 'cbnz', 'tbz', 'tbnz') or i.mnemonic.startswith('b.'):
                target = int(i.op_str.split('#')[-1], 0)
                if target in addresses:
                    asm.append(i.mnemonic + ' ' + i.op_str.rsplit('#', 1)[0] + f'.Lhero_s_{target:x}')
                elif target in {start for _, start, _ in SPANS}:
                    name = next(name for name, start, _ in SPANS if start == target)
                    assert i.mnemonic == 'bl'
                    asm.append('bl pgwr_hero_s_owned_' + name)
                else:
                    assert i.mnemonic == 'bl', (hex(i.address), i.mnemonic, hex(target))
                    helpers.add(target); asm.extend(address('x17', target)); asm.append('blr x17')
            elif i.mnemonic == 'udf':
                asm.append(f'.inst 0x{int.from_bytes(i.bytes, "little"):08x}')
            else:
                assert not (i.mnemonic.startswith('ldr') and ', #' in i.op_str and '[' not in i.op_str)
                asm.append(i.mnemonic + ' ' + i.op_str)
        asm.append('.size ' + symbol + ', .-' + symbol)
    assert replaced == set(callbacks) | set(changes)
    signatures = [(start, image.data[start:end]) for _, start, end in SPANS]
    signatures += [(a, image.data[a:a + 32]) for a in sorted(helpers)]
    signatures += [(0xa2a000, image.data[0xa2a000:0xa2a270])]
    rust = ['// Generated by tools/gen_hero_side_b_native.py.', 'pub(super) const SIGNATURES: &[(usize, &[u8])] = &[']
    rust += [f'    (0x{offset:x}, &[' + ','.join(f'0x{b:02x}' for b in data) + ']),' for offset, data in signatures]
    rust.append('];')
    words = [0] * (0x268 // 4)
    for offset, record in fields.items(): words[offset // 4] = struct.unpack('<I', struct.pack('<f', record['value']))[0]
    params = ['// Native field view generated from the pinned vl.prc + native decoder.',
              '#[no_mangle]', 'pub(super) static PGWR_HERO_S_SPARK_PARAMS: [u32; 154] = [',
              ','.join(f'0x{word:08x}' for word in words), '];']
    tables = ['// Owned parameter values generated from pinned Hero vl.prc; no mana fields.',
              'pub(super) const HOLD_FRAME_M: i32 = 9;',
              'pub(super) const HOLD_FRAME_L: i32 = 26;',
              'pub(super) const HOLD_FRAME_MAX: i32 = 26;']
    table_records = {}
    for name in ('param_special_s', 'param_spark', 'param_lightning'):
        key = len(name) << 32 | zlib.crc32(name.encode())
        assert vl[key][0] == 'list'
        first = dict(vl[key][1][0][1])
        table_records[name] = {hex(child): value for child, value in first.items()}
        for kind, rust_type in (('float', 'f32'), ('i32', 'i32')):
            tables += [f'pub(super) fn {name}_{rust_type}(key: u64) -> Option<{rust_type}> {{', '    match key {']
            for child, (actual, value) in first.items():
                if actual == kind:
                    literal = f'f32::from_bits(0x{struct.unpack("<I", struct.pack("<f", value))[0]:08x})' if kind == 'float' else str(value)
                    tables.append(f'        0x{child:x} => Some({literal}),')
            tables += ['        _ => None,', '    }', '}']
    measured = json.loads((ROOT / 'refs/brave_special_s/param_special_s.json').read_text())['entries'][0]
    assert (measured['hold_frame_m'], measured['hold_frame_l'], measured['hold_frame_max']) == (9, 26, 26)
    record = {'date': '2026-09-30', 'tier': 'B', 'tool_version': '1.1.0',
              'main_sha256': hashlib.sha256(image.data).hexdigest(), 'vl_sha256': hashlib.sha256(vl_path.read_bytes()).hexdigest(),
              'spark_fields': {hex(offset): value for offset, value in fields.items()},
              'parameter_tables': table_records,
              'small_level_half_width': 'Native constructor loads +0x254, the medium half_width; preserved exactly.',
              'owned_callbacks': {hex(a): name for a, name in callbacks.items()},
              'authorized_hook_sites': ['0x85d580', '0x85dad0', '0x33cbb20'],
              'hardware_validated': False}
    return {OUT / 'native_1304.s': '\n'.join(asm) + '\n',
            OUT / 'native_signatures.rs': '\n'.join(rust) + '\n',
            OUT / 'native_params.rs': '\n'.join(params) + '\n',
            OUT / 'params.rs': '\n'.join(tables) + '\n',
            ROOT / 'refs/brave_special_s/owned_native_audit.json': json.dumps(record, indent=2) + '\n'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for path, text in generate().items():
        if args.check: assert path.read_text() == text, 'stale ' + path.relative_to(ROOT).as_posix()
        else: path.write_text(text)
    print('PASS: complete relocated native spans, owned owner-state callbacks, spark decoder/PRC fields and signatures; source only')


if __name__ == '__main__': main()
