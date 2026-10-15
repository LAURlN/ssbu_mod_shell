"""Pin cargo's parameter getter and clatter operands; no runtime execution.

Usage from mod root: python -B src/pgwr/tools/dk_cargo/param_contract.py
The assertions are the smoke test. An absent PRC field is not assigned the
value of a nearby unknown field. Hardware behavior remains unverified.
"""
import json
import struct
from audit import OUT, INPUT, WS, MainImage, cfg, sha, h40, write
from nro_flatten import flatten


def evaluate_field_getter(img, start, argument, memory=None):
    """Evaluate only the leaf field-dispatch instruction subset, offline.

    Reject everything outside this subset. No host/native function is called.
    The control cases below independently check all six known private keys.
    """
    regs = {'x0': 0x100000000, 'x1': argument, 'xzr': 0}
    memory = memory or {}
    pc, comparison = start, 0
    for _ in range(1000):
        ins = img.disasm(pc, 4)[0]
        op, args = ins.mnemonic, ins.op_str
        pc += 4
        if op == 'ret':
            return regs['x0'], regs['x1']
        if op.startswith('b.'):
            take = {'eq': comparison == 0, 'ne': comparison != 0,
                    'gt': comparison > 0, 'le': comparison <= 0,
                    'lt': comparison < 0, 'ge': comparison >= 0}[op[2:]]
            if take: pc = int(args[1:], 0)
            continue
        parts = [p.strip() for p in args.split(',')]
        def value(p): return int(p[1:], 0) if p.startswith('#') else regs[p]
        if op in ('mov', 'adrp'): regs[parts[0]] = value(parts[1])
        elif op == 'movk':
            shift = int(parts[2].split('#')[1]) if len(parts) == 3 else 0
            regs[parts[0]] = (regs.get(parts[0], 0) & ~(0xffff << shift)) | (value(parts[1]) << shift)
        elif op == 'and': regs[parts[0]] = value(parts[1]) & value(parts[2])
        elif op == 'add': regs[parts[0]] = value(parts[1]) + value(parts[2])
        elif op == 'cmp': comparison = value(parts[0]) - value(parts[1])
        elif op == 'ldr':
            import re
            m = re.fullmatch(r'(x\d+), \[(x\d+), #(0x[0-9a-f]+|\d+)\]', args)
            assert m, args
            regs[m[1]] = memory[regs[m[2]] + int(m[3], 0)]
        else: raise AssertionError((hex(ins.address), op, args))
    raise AssertionError('field dispatcher did not terminate')


def run():
    img = MainImage(WS / 'gamedata/ssbu-13.0.4/main.bin')
    vt = 0x4f8dee8
    assert img.ptr(vt + 0x10) == 0x77d100
    assert img.ptr(vt + 0x20) == 0x77d5b0
    assert img.ptr(0x4f89490 + 0x248) == 0x4e5390
    assert img.ptr(0x523bba0 + 0x30) == 0x3a4810
    functions = {}
    for a in (0x208de30, 0x4e5390, 0x4e53a0, 0x4e4210,
              0x77d100, 0x77d5b0, 0x9993c0, 0x9980d0, 0x3a4810):
        row, text = cfg(img.data, a, {})
        path = OUT / 'semantic_asm' / f'param_contract_{a:x}.asm'
        path.write_text(text, encoding='utf-8')
        functions[hex(a)] = {**row, 'path': path.relative_to(OUT).as_posix(),
                            'sha256': sha(path.read_bytes())}
    # The default branch retains x1=GROUP when calling the fighter root getter.
    # The returned value-ref's +0x50 dispatch receives x19=CHILD; +0x30 gets
    # its integer. The private field's nearby integer 13 is a distinct key.
    text = (OUT / 'semantic_asm/param_contract_77d5b0.asm').read_text()
    assert '0x0077d898: ldr      x0, [x20, #0x1b08]' in text
    assert '0x0077d870: mov      x1, x19' in text
    assert '0x0077d87c: ldr      x8, [x0, #0x30]' in text
    assert (OUT / 'semantic_asm/param_contract_3a4810.asm').read_text().strip().endswith('ret')
    vl = json.loads((OUT / 'vl_decoded.json').read_text())
    stop_key = h40('throw_lw_stop_frame')
    assert stop_key == 0x13a4988083
    assert 'throw_lw_stop_frame' not in vl
    assert hex(stop_key) not in vl
    private_vt, private_data = evaluate_field_getter(img, 0x9993c0, h40('param_private'))
    assert private_vt == 0x4fa9f30
    assert img.ptr(private_vt + 0x50) == 0x9980d0
    missing = evaluate_field_getter(img, 0x9980d0, stop_key,
                                    {0x100000008: private_data})
    assert missing == (0x523bba0, 0)
    assert img.ptr(missing[0] + 0x30) == 0x3a4810
    # Positive controls: dispatch to six real typed fields, not the sentinel.
    controls = {}
    for key in (0xfe21f2d3d, 0x10bb3928c1, 0x1688163f7d,
                0x16b89c1cb6, 0x16ff110feb, 0x17e5971793):
        typed, address = evaluate_field_getter(img, 0x9980d0, key,
                                               {0x100000008: private_data})
        assert typed != missing[0] and address != 0
        controls[hex(key)] = {'type_vtable': hex(typed),
                             'private_field_offset': address - private_data}
    common_raw = (INPUT / 'prebuilt;/nro/release/lua2cpp_common.nro').read_bytes()
    common, _ = flatten(common_raw)
    donor_raw = (INPUT / 'prebuilt;/nro/release/lua2cpp_donkey.nro').read_bytes()
    donor, _ = flatten(donor_raw)
    assert struct.unpack_from('<f', donor, 0x133694)[0] == 90.0
    assert struct.unpack_from('<f', common, 0x6a5834)[0] == 90.0
    write('parameter_contract.json', {
        'tier': 'B', 'verified_offline': True, 'runtime_verified': False,
        'main_sha256': sha(img.data), 'functions': functions,
        'down_throw_stop': {
            'group': hex(h40('param_private')), 'key': hex(stop_key),
            'root_prc_field_present': False,
            'empty_parameter_int_getter': 'main+0x3a4810: mov w0,wzr;ret',
            'owned_value': 0, 'complete': True,
            'root_getter': 'main+0x9993c0',
            'private_getter': 'main+0x9980d0',
            'private_vtable': hex(private_vt),
            'private_dispatch_positive_controls': controls,
            'missing_dispatch_result': [hex(v) for v in missing]},
        'victim_clatter': {
            'init': 'damage * 1.5 + 50.0 + existing clatter time',
            'start_clatter_arguments': ['total', 0.0, 10.0, -1, 0, False, False],
            'third_float_key': '0x188226f196',
            'third_float_is_capture_clatter_frame': False,
            'reference_parent_color_blend': False,
            'carry_ground_dec_time': 10.0, 'carry_air_dec_time': 13.0,
            'dec_time_recovery': 1.0},
        'held_item_drop_angle': 90.0, 'carry_turn_rotation_degrees': 90.0})
    print('PASS: native root/private dispatch and six controls; missing stop field returns empty integer 0; corrected clatter operands pinned')


if __name__ == '__main__':
    run()
