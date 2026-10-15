"""Generate a recipient-owned copy of the audited 13.0.4 fireball initializer.

Version 1.1.0. Relocates every PC-relative instruction and every branch in the
complete donor function, including its out-of-line singleton/error paths.
Replaces the Hero-specific charge read and special-N parameter getters with
plugin-owned callbacks. Generic engine helpers stay engine helpers. No donor
fighter Lua code or donor fighter work id is called from the generated copy.

1.1.0: the fireball class constructor (vtable slot +0x30 at 0x33c8ea0) reads
map_collision_fireball{,_m,_l} from Hero's decoded vl.prc object
*(*(main+0x52bb3b0)+0x1298), which is null without a real Hero in the match
(crash reports 01790734050/01790734167). Emits those values from the pinned
vl.prc and checks the decoder stores, the constructor loads and its bytes.

--check compares generated output and verifies branch coverage/pinned bytes.
This is a source generation check, not proof of console behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'toolchains/python_tools'))
import capstone

START, END = 0x85cf70, 0x85d580
EFFECT_START, EFFECT_END = 0x33c94f0, 0x33c9db4
CTOR_START, CTOR_END = 0x33c8ea0, 0x33c8f80
DECODER_START, DECODER_END = 0x878800, 0x8792ec
MAP_COLLISION = ('map_collision_fireball', 'map_collision_fireball_m', 'map_collision_fireball_l')
MAP_FIELDS = ('up', 'down', 'half_width')
OUT = ROOT / 'src/pgwr/plugin/src/mythra/hero_neutral_b'


def hash40(name):
    return len(name) << 32 | zlib.crc32(name.encode())


def check_map_collision(data, md, vl):
    """Verify object offsets of map_collision_fireball* and the constructor's reads of them."""
    labels = {hash40(n): n for n in MAP_COLLISION + MAP_FIELDS}
    regs, events = {}, []
    for i in md.disasm(data[DECODER_START:DECODER_END], DECODER_START):
        if i.mnemonic == 'mov' and ', #' in i.op_str:
            reg, value = i.op_str.split(', #')
            try:
                regs[reg] = int(value, 0) & (2**64 - 1)
            except ValueError:
                pass
        elif i.mnemonic == 'movk':
            part = i.op_str.split(', ')
            shift = int(part[2].split('#')[1]) if len(part) > 2 else 0
            regs[part[0]] = (regs.get(part[0], 0) & ~(0xffff << shift)) | (int(part[1][1:], 0) << shift)
            if shift == 32 and regs[part[0]] in labels:
                events.append(('key', labels[regs[part[0]]]))
        elif i.mnemonic == 'fmov' and ', #' in i.op_str:
            events.append(('default', float(i.op_str.split('#')[1])))
        elif i.mnemonic == 'str' and i.op_str.startswith('s0, [x16, #'):
            events.append(('store', int(i.op_str.split('#')[1].rstrip(']'), 0)))
    blocks, current = {}, None
    for kind, value in events:
        if kind == 'key' and value in MAP_COLLISION:
            current = blocks.setdefault(value, {'keys': [], 'defaults': [], 'stores': []})
        elif current is not None:
            current[kind + 's'].append(value)
    values = []
    for level, name in enumerate(MAP_COLLISION):
        block, base = blocks[name], 0x194 + 0x10 * level
        assert block['stores'] == [base, base + 4, base + 8], (name, block)
        assert set(block['keys']) == set(MAP_FIELDS), (name, block)
        fields = dict(vl[hash40(name)][1])
        assert all(fields[hash40(f)][0] == 'float' for f in MAP_FIELDS)
        row = [fields[hash40(f)][1] for f in MAP_FIELDS]
        # Decoder fallbacks equal the donor values: independent check of field order.
        assert block['defaults'] == row, (name, block['defaults'], row)
        values.append(row)
    # Level s builds each field key immediately before its store.
    assert blocks[MAP_COLLISION[0]]['keys'] == list(MAP_FIELDS)
    ctor = {i.address: f'{i.mnemonic} {i.op_str}' for i in md.disasm(data[CTOR_START:CTOR_END], CTOR_START)}
    assert ctor[0x33c8eb8] == 'adrp x8, #0x52bb000' and ctor[0x33c8ebc] == 'ldr x8, [x8, #0x3b0]'
    assert ctor[0x33c8ec0] == 'ldr x21, [x8, #0x1298]'
    assert ctor[0x33c8ec4] == 'ldr w8, [x2, #0x28]'
    assert [ctor[a] for a in (0x33c8ef4, 0x33c8f3c, 0x33c8f18)] == [
        f'ldr s0, [x21, #0x{0x194 + 0x10 * level:x}]' for level in range(3)]
    reads = sorted({int(m, 0) for t in ctor.values() for m in re.findall(r'\[x21, #(0x[0-9a-f]+)\]', t)})
    assert reads == [0x194 + 0x10 * level + 4 * f for level in range(3) for f in range(3)], reads
    return values


def generate():
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    main = ROOT / cfg['dumps']['exefs'] / 'main.bin'
    data = main.read_bytes()
    audit = json.loads((ROOT / 'refs/brave_special_n/fireball_native.json').read_text())
    assert hashlib.sha256(data).hexdigest() == audit['sha256']
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
    import prc
    vl_file = ROOT / cfg['dumps']['arc'] / 'fighter/brave/param/vl.prc'
    map_collision = check_map_collision(data, md, dict(prc.read(vl_file)[1]))
    instructions = list(md.disasm(data[START:END], START))
    instructions += list(md.disasm(data[EFFECT_START:EFFECT_END], EFFECT_START))
    assert len(instructions) * 4 == END - START + EFFECT_END - EFFECT_START
    # x16 carries a param hash only in this straight-line, call-free interval.
    uses_x16 = [i.address for i in instructions if re.search(r'\b[wx]16\b', i.op_str)]
    assert uses_x16 == [0x85d0f8, 0x85d0fc, 0x85d10c, 0x85d114]
    assert not any(i.mnemonic in ('adrp', 'adr', 'bl', 'blr')
                   for i in instructions if 0x85d0f8 <= i.address <= 0x85d114)
    addresses = {i.address for i in instructions}
    lines = ['// Generated by tools/gen_hero_fireball_initializer.py v1.1.0.',
             '// Own copy; charge and move params are plugin callbacks.',
             '.text', '.hidden PGWR_HERO_GAME_BASE', '.balign 4', '.global pgwr_hero_fireball_owned_init',
             '.type pgwr_hero_fireball_owned_init, %function',
             'pgwr_hero_fireball_owned_init:']
    helpers = set()

    def address(reg, offset):
        return [f'adrp {reg}, PGWR_HERO_GAME_BASE',
                f'ldr {reg}, [{reg}, :lo12:PGWR_HERO_GAME_BASE]',
                f'movz x16, #{offset & 0xffff}',
                f'movk x16, #{(offset >> 16) & 0xffff}, lsl #16',
                f'add {reg}, {reg}, x16']

    replace = {0x85d000: 'pgwr_hero_n_charge',
               0x85d024: 'pgwr_hero_n_param_int', 0x85d048: 'pgwr_hero_n_param_int',
               0x85d158: 'pgwr_hero_n_param_float', 0x85d174: 'pgwr_hero_n_param_float'}
    replace.update({a: 'pgwr_hero_fireball_param_int' for a in (0x33c9634, 0x33c9650)})
    replace.update({a: 'pgwr_hero_fireball_param_float' for a in (0x33c967c, 0x33c99c0, 0x33c9b00)})
    for i in instructions:
        if i.address == EFFECT_START:
            lines += ['.size pgwr_hero_fireball_owned_init, .-pgwr_hero_fireball_owned_init',
                      '.balign 4', '.global pgwr_hero_fireball_owned_effect',
                      '.type pgwr_hero_fireball_owned_effect, %function',
                      'pgwr_hero_fireball_owned_effect:']
        lines.append(f'.Lhero_{i.address:x}:')
        if i.address == 0x85cff4:
            lines.append('nop // Removed Hero work id argument')
        elif i.address == 0x85cff8:
            lines.append('mov x0, x22 // Pass actual recipient module accessor')
        elif i.address in replace:
            assert i.mnemonic == 'blr'
            lines.append('bl ' + replace[i.address])
        elif i.mnemonic in ('adrp', 'adr'):
            reg, target = i.op_str.split(', ')
            lines.extend(address(reg, int(target.lstrip('#'), 0)))
        elif i.mnemonic in ('b', 'bl', 'cbz', 'cbnz', 'tbz', 'tbnz') or i.mnemonic.startswith('b.'):
            target = int(i.op_str.split('#')[-1], 0)
            if target in addresses:
                lines.append(i.mnemonic + ' ' + i.op_str.rsplit('#', 1)[0] + f'.Lhero_{target:x}')
            else:
                assert i.mnemonic == 'bl', (i.address, i.mnemonic, target)
                assert not START <= target < END
                helpers.add(target)
                lines.extend(address('x17', target))
                lines.append('blr x17')
        elif i.mnemonic == 'udf':
            lines.append(f'.inst 0x{int.from_bytes(i.bytes, "little"):08x}')
        else:
            # No unhandled literal loads or PC-relative instructions allowed.
            assert not (i.mnemonic.startswith('ldr') and ', #' in i.op_str and '[' not in i.op_str)
            lines.append(i.mnemonic + ' ' + i.op_str)
    lines.append('.size pgwr_hero_fireball_owned_effect, .-pgwr_hero_fireball_owned_effect')
    signatures = [(START, data[START:END]), (EFFECT_START, data[EFFECT_START:EFFECT_END]),
                  (CTOR_START, data[CTOR_START:CTOR_END])] + [(a, data[a:a + 32]) for a in sorted(helpers)]
    rust = ['// Generated by tools/gen_hero_fireball_initializer.py v1.1.0.',
            'pub const SIGNATURES: &[(usize, &[u8])] = &[']
    for offset, sig in signatures:
        rust.append(f'    (0x{offset:x}, &[' + ','.join(f'0x{x:02x}' for x in sig) + ']),')
    rust.append('];')
    tables = json.loads((ROOT / 'refs/brave_special_n/DEPENDENCIES.json').read_text())['donor_parameter_tables']
    params = ['// Generated from pinned Hero vl.prc by gen_hero_fireball_initializer.py.',
              '// Mana prices excluded. Offline source values; no runtime claim.']
    common_file = ROOT / cfg['dumps']['arc'] / 'fighter/common/param/fighter_param.prc'
    common_tree = dict(prc.read(common_file)[1])
    common_rows = common_tree[hash40('fighter_param_table')][1]
    row = next(dict(r[1]) for r in common_rows
               if dict(r[1])[hash40('fighter_kind')][1] == hash40('fighter_kind_brave'))
    params += ['// Source: ' + common_file.relative_to(ROOT).as_posix(),
               '// SHA256: ' + hashlib.sha256(common_file.read_bytes()).hexdigest(),
               'pub fn common_f32(key: u64) -> Option<f32> {', '    match key {']
    for name in ('air_accel_y', 'air_speed_y_stable', 'air_speed_x_stable',
                 'air_accel_x_mul', 'air_accel_x_add', 'air_brake_x'):
        kind, value = row[hash40(name)]
        assert kind == 'float'
        params.append(f'        0x{hash40(name):x} => Some({value!r}f32), // {name}')
    params += ['        _ => None,', '    }', '}']
    params += ['// Source: ' + vl_file.relative_to(ROOT).as_posix(),
               '// SHA256: ' + hashlib.sha256(vl_file.read_bytes()).hexdigest(),
               '// [up, down, half_width] per level s/m/l; native object +0x194/+0x1a4/+0x1b4.',
               'pub const MAP_COLLISION_FIREBALL: [[f32; 3]; 3] = [']
    for name, row in zip(MAP_COLLISION, map_collision):
        params.append('    [' + ', '.join(f'{v!r}f32' for v in row) + f'], // {name}')
    params += ['];']
    for parent, table in tables.items():
        if parent not in ('param_fireball', 'param_special_n'):
            continue
        values = table['value'][0]['value']
        for rusttype, kind in [('i32', 'i32'), ('f32', 'float')]:
            params += [f'pub fn {parent}_{rusttype}(key: u64) -> Option<{rusttype}> {{', '    match key {']
            for key, value in values.items():
                if value['type'] != kind or key.startswith('sp_special_n'):
                    continue
                literal = repr(value['value']) + ('f32' if kind == 'float' else '')
                params.append(f'        0x{hash40(key):x} => Some({literal}), // {key}')
            params += ['        _ => None,', '    }', '}']
    report = {'date': '2026-09-30', 'tool_version': '1.1.0', 'evidence_tier': 'B',
              'main_sha256': audit['sha256'], 'owned_function_span': [hex(START), hex(END)],
              'owned_effect_helper_span': [hex(EFFECT_START), hex(EFFECT_END)],
              'native_effect_resources': ['brave_fire3_ember'],
              'replaced_calls': {hex(k): v for k, v in replace.items()},
              'generic_engine_helpers': [hex(x) for x in sorted(helpers)],
              'fireball_constructor': {
                  'span': [hex(CTOR_START), hex(CTOR_END)], 'vtable_slot': '0x51b1078',
                  'missing_object': '*(*(main+0x52bb3b0)+0x1298), Hero decoded vl.prc',
                  'bridge_hook': '0x33c8ec4, after ldr x21, [x8, #0x1298]',
                  'decoder_span': [hex(DECODER_START), hex(DECODER_END)],
                  'vl_prc': vl_file.relative_to(ROOT).as_posix(),
                  'vl_prc_sha256': hashlib.sha256(vl_file.read_bytes()).hexdigest(),
                  'map_collision_up_down_half_width': dict(zip(MAP_COLLISION, map_collision))},
              'instruction_count': len(instructions), 'hardware_validated': False}
    return {'initializer_1304.s': '\n'.join(lines) + '\n',
            'signatures.rs': '\n'.join(rust) + '\n',
            'donor_params.rs': '\n'.join(params) + '\n'}, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files, report = generate()
    files = {OUT / k: v for k, v in files.items()}
    files[ROOT / 'refs/brave_special_n/owned_initializer.json'] = json.dumps(report, indent=2) + '\n'
    for path, content in files.items():
        if args.check:
            assert path.read_text() == content, f'Stale output: {path.relative_to(ROOT)}'
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print('PASS: full initializer branch coverage, pinned native bytes, owned charge/parameter callbacks')


if __name__ == '__main__':
    main()
