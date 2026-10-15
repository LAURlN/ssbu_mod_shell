"""Inventory the complete cargo callback instruction closure and data operands.

Usage: python -B src/pgwr/tools/dk_cargo/closure.py
This does not emit or register runtime code. Imported PLT tails stop at the
import boundary; local calls and function-pointer operands are followed.
Every data operand and indirect call is retained for the ownership review.
The assertions are its smoke test, not capture/release validation.
"""
import json
import re
import struct
from audit import OUT, INPUT, cfg, sha, write
from nro_flatten import flatten, parse
import nro_util


def image(kind):
    path = INPUT / f'prebuilt;/nro/release/lua2cpp_{kind}.nro'
    raw = path.read_bytes()
    data, meta = flatten(raw)
    syms, relocs, _ = parse(raw)
    labels = {int(a, 0): n for a, n in meta['labels'].items()}
    imports = nro_util.plt_map(data, meta['labels'], meta['text_end'])
    labels.update(imports)
    # PLT alignment is not uniformly sixteen bytes in these two NROs.
    # Resolve every call candidate independently against relocated GOT slots.
    import_slots = {off: syms[info >> 32][0] for off, info, add in relocs
                    if info & 0xffffffff != 1027 and syms[info >> 32][2] == 0}
    for a in range(0, meta['text_end'] - 16, 4):
        w = struct.unpack_from('<I', data, a)[0]
        if w & 0x9f00001f != 0x90000010:
            continue
        ins = list(nro_util.disasm(data, a, 16))
        if len(ins) != 4 or ins[1].mnemonic != 'ldr' or ins[3].op_str != 'x17':
            continue
        page = int(ins[0].op_str.split('#')[1], 0)
        m = re.search(r'#(0x[0-9a-f]+|\d+)\]', ins[1].op_str)
        slot = page + (int(m[1], 0) if m else 0)
        if slot in import_slots:
            imports[a] = import_slots[slot]
            labels[a] = import_slots[slot]
    return path, raw, data, meta, labels, imports, import_slots


def run():
    donor = image('donkey')
    common = image('common')
    constants = (OUT / 'semantic_annotations.json')
    registration = json.loads((OUT / 'status_table.json').read_text())
    roles = [r for r in registration if '_SHOULDER_' in r['status']
             or '_THROW_F_' in r['status']]
    assert len({r['status'] for r in roles}) == 15
    roots = {int(r['function'], 0) for r in roles}
    victim_rows = json.loads((OUT / 'victim_instruction_graph.json').read_text())
    victim_roots = {int(r['entry'], 0) for r in victim_rows}
    # Own the walk helpers too: DK installs three 1.1 modifiers in its native
    # constructor. Their parameter reads must be translated, not delegated to
    # that fighter-specific constructor on an eflame object.
    walk_prefix = '_ZN7lua2cpp16L2CFighterCommon'
    walk_names = {n for a, n in common[4].items() if n.startswith(walk_prefix)
                  and ('sub_walk_uniq_process_init_common' in n
                       or 'sub_walk_uniq_process_main_common' in n)}
    common_exports = {n: a for a, n in common[4].items() if a not in common[5]}
    victim_roots.update(common_exports[n] for n in walk_names)
    output = {'tier': 'B', 'runtime_verified': False,
              'semantic_review_complete': False, 'roles': roles, 'images': {}}
    for kind, source, initial in [('donkey', donor, roots), ('common', common, victim_roots)]:
        path, raw, data, meta, labels, imports, slots = source
        todo = list(initial)
        seen = set()
        functions = []
        while todo:
            start = todo.pop()
            if start in seen or start in imports:
                continue
            assert 0x400 <= start < meta['text_end'], (kind, hex(start))
            seen.add(start)
            row, text = cfg(data, start, labels)
            lines = []
            # cfg follows an imported tail BR through its PLT. Clip imported
            # stub instructions; the outgoing branch itself remains evidence.
            addresses = []
            for line in text.splitlines():
                a = int(line.split(':', 1)[0], 0)
                if any(p <= a < p + 16 for p in imports):
                    continue
                addresses.append(a)
                lines.append(line)
            text = '\n'.join(lines) + '\n'
            instructions = {a: next(nro_util.disasm(data, a, 4)) for a in addresses}
            calls, pointers, data_reads, indirect = {}, [], [], []
            pages = {}
            for a, ins in sorted(instructions.items()):
                m, ops = ins.mnemonic, ins.op_str
                if m in ('bl', 'b') and ops.startswith('#'):
                    target = int(ops[1:], 0)
                    if target in imports:
                        calls[hex(target)] = {'import': imports[target]}
                        if kind == 'common' and imports[target] in walk_names:
                            todo.append(common_exports[imports[target]])
                    elif m == 'bl':
                        calls[hex(target)] = {'local': hex(target)}
                        todo.append(target)
                elif m in ('blr', 'br'):
                    indirect.append({'at': hex(a), 'operand': ops})
                elif m == 'adrp':
                    reg, value = ops.split(', #')
                    pages[reg] = int(value, 0)
                elif m == 'add':
                    mm = re.fullmatch(r'(x\d+), (x\d+), #(0x[0-9a-f]+|\d+)', ops)
                    if mm and mm[2] in pages:
                        target = pages[mm[2]] + int(mm[3], 0)
                        pages[mm[1]] = target
                        if 0x400 <= target < meta['text_end'] and target not in imports:
                            pointers.append({'at': hex(a), 'target': hex(target)})
                            todo.append(target)
                elif m == 'ldr':
                    mm = re.fullmatch(r'([xwsdq]\d+), \[(x\d+), #(0x[0-9a-f]+|\d+)\]', ops)
                    if mm and mm[2] in pages:
                        target = pages[mm[2]] + int(mm[3], 0)
                        if target >= meta['text_end']:
                            width = {'x': 8, 'w': 4, 's': 4, 'd': 8, 'q': 16}[mm[1][0]]
                            value = data[target:target + width]
                            data_reads.append({'at': hex(a), 'address': hex(target),
                                'width': width, 'bytes': value.hex(),
                                'import': slots.get(target)})
                            if mm[1].startswith('x'):
                                pages.pop(mm[1], None)
            dest = OUT / 'closure_asm' / f'{kind}_{start:x}.asm'
            dest.parent.mkdir(exist_ok=True)
            dest.write_text(text, encoding='utf-8')
            functions.append({'entry': hex(start), 'symbol': labels.get(start),
                'instructions': len(addresses), 'calls': calls,
                'function_pointers': pointers, 'data_reads': data_reads,
                'indirect_calls': indirect, 'asm': dest.relative_to(OUT).as_posix(),
                'asm_sha256': sha(dest.read_bytes())})
        output['images'][kind] = {'input': path.relative_to(INPUT).as_posix(),
            'sha256': sha(raw), 'functions': sorted(functions, key=lambda r: int(r['entry'], 0)),
            'import_boundaries': sorted({c['import'] for r in functions for c in r['calls'].values() if 'import' in c})}
    output['parameter_contract'] = {'path': 'parameter_contract.json',
        'sha256': sha((OUT / 'parameter_contract.json').read_bytes())}
    output['motion_sharing_contract'] = {'path': 'native_pose_route.json',
        'sha256': sha((OUT / 'native_pose_route.json').read_bytes())}
    write('callback_closure.json', output)
    for kind, rows in output['images'].items():
        print(kind, len(rows['functions']), 'functions;', len(rows['import_boundaries']), 'import boundaries')
    print('PASS: instruction/data closure captured; semantic ownership review remains a separate gate')


if __name__ == '__main__':
    run()
