"""Find native class methods using this dump's relocated tables and unwind data.

Does not infer that copying these methods closes the dependency graph. Reports
all external branches, PC-relative data uses and indirect calls for review.
"""
import bisect
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys
from prepare import ROOT, write_json

sys.path.insert(0, str(ROOT.parent / 'references/mythra_gamewatch_feasibility/python_tools'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from capstone.arm64_const import ARM64_OP_IMM


def main():
    data = (ROOT.parent / 'references/mythra_gamewatch_feasibility/main_memory.bin').read_bytes()
    expected = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Unsupported main image; do not apply this offset profile')
    mod = struct.unpack_from('<I', data, 4)[0]
    at = mod + struct.unpack_from('<i', data, mod + 4)[0]
    tags = {}
    while True:
        tag, value = struct.unpack_from('<QQ', data, at)
        at += 16
        if not tag: break
        tags[tag] = value
    reloc = {}
    for at in range(tags[7], tags[7] + tags[8], 24):
        address, info, addend = struct.unpack_from('<QQq', data, at)
        if info & 0xffffffff == 1027:
            reloc[address] = addend

    def pointer(address):
        return reloc.get(address, struct.unpack_from('<Q', data, address)[0])

    def string(address):
        return data[address:data.index(0, address)].decode('ascii')

    header = mod + struct.unpack_from('<i', data, mod + 16)[0]
    if data[header:header + 4] != bytes.fromhex('011b033b'):
        raise ValueError('Unsupported unwind-header encoding')
    count = struct.unpack_from('<I', data, header + 8)[0]
    functions = {}
    for i in range(count):
        start, fde = struct.unpack_from('<ii', data, header + 12 + i * 8)
        start += header
        fde += header
        pc_relative, size = struct.unpack_from('<iI', data, fde + 8)
        if fde + 8 + pc_relative != start or size <= 0 or start + size > len(data):
            raise ValueError('Unwind record does not match header entry')
        functions[start] = size
    starts = sorted(functions)

    def enclosing(address):
        i = bisect.bisect_right(starts, address) - 1
        if i < 0: return None
        start = starts[i]
        return start if address < start + functions[start] else None

    names = {s['address']: s['name'] for s in json.loads(
        (ROOT.parent / 'references/mythra_gamewatch_feasibility/main_symbols.json').read_text())
        if s['section'] and s['type'] == 2}
    classes, outside, unavailable_classes = [], set(), []
    for space, number, table, slots in [('fighter', 94, 0x529bfd0, 147), ('weapon', 0x267, 0x529c400, 104)]:
        for kind in range(number):
            owner = None
            label = str(kind)
            if space == 'fighter':
                selected = kind in (90, 91)
                if selected: owner = 'eflame' if kind == 90 else 'elight'
            else:
                owner = string(pointer(0x5188240 + kind * 8))
                label = string(pointer(0x5185bd0 + kind * 8))
                selected = owner in ('eflame', 'elight', 'element')
            cls = pointer(table + kind * 8)
            if not cls:
                continue
            if not 0 < cls < len(data) - 8:
                unavailable_classes.append(dict(space=space, kind=kind, selected=selected, class_offset=cls))
                continue
            vt = pointer(cls)
            if not 0 < vt < len(data) - slots * 8:
                raise ValueError('Class table is not valid for this main dump')
            entries = [pointer(vt + i * 8) for i in range(slots)]
            if selected:
                classes.append(dict(space=space, kind=kind, owner=owner, name=label,
                                    class_offset=cls, vtable_offset=vt, entries=entries))
            else:
                outside.update(entries)
    roots = set()
    for cls in classes:
        cls['character_specific_slots'] = [i for i, p in enumerate(cls['entries']) if p and p not in outside]
        roots.update(cls['entries'][i] for i in cls['character_specific_slots'])
    for name in ('cflame', 'clight', 'clement'):
        native = json.loads((ROOT / 'reports' / ('native-' + name + '.json')).read_text())
        imported = {s['name'] for s in native['character_specific_imports']}
        roots.update(address for address, name in names.items() if name in imported)
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = True
    inventory, unknown = [], []
    folder = ROOT / 'native/class-functions'
    folder.mkdir(parents=True, exist_ok=True)
    for address in sorted(roots):
        start = enclosing(address)
        if start is None:
            unknown.append(address)
            continue
        size = functions[start]
        body = data[start:start + size]
        instructions = list(md.disasm(body, start))
        if sum(i.size for i in instructions) != size:
            raise ValueError('Incomplete disassembly at ' + hex(start))
        branches, pc_data, indirect = [], [], []
        for ins in instructions:
            if ins.mnemonic in ('b', 'bl', 'cbz', 'cbnz', 'tbz', 'tbnz') or ins.mnemonic.startswith('b.'):
                operands = [o.imm for o in ins.operands if o.type == ARM64_OP_IMM]
                target = operands[-1]
                if not start <= target < start + size:
                    branches.append(dict(at=ins.address, mnemonic=ins.mnemonic, target=target,
                                         named_target=names.get(target), selected_root=target in roots,
                                         target_function=enclosing(target)))
            elif ins.mnemonic in ('adr', 'adrp') or (ins.mnemonic in ('ldr', 'ldrsw', 'prfm') and any(o.type == ARM64_OP_IMM for o in ins.operands)):
                pc_data.append(dict(at=ins.address, mnemonic=ins.mnemonic, operands=ins.op_str))
            elif ins.mnemonic in ('br', 'blr'):
                indirect.append(dict(at=ins.address, mnemonic=ins.mnemonic, operands=ins.op_str))
        (folder / ('{:08x}.bin'.format(start))).write_bytes(body)
        inventory.append(dict(entry=address, function_start=start, bytes=size, name=names.get(address),
                              sha256=hashlib.sha256(body).hexdigest(), external_branches=branches,
                              pc_relative_data=pc_data, indirect_control_flow=indirect))
    result = dict(main_sha256=expected, unwind_function_count=len(functions), classes=classes,
                  unavailable_classes=unavailable_classes,
                  root_count=len(roots), uncovered_roots=unknown, functions=inventory,
                  dependency_closure_complete=False, executable_copies=False,
                  notes='Methods shared with unrelated class vtables are classified as shared engine candidates, not automatically proven generic. Anonymous callees/data and indirect targets still require review.')
    write_json('native-classes.json', result)
    print('Unwind functions:', len(functions), 'owned classes:', len(classes), 'candidate method roots:', len(roots))
    print('Roots without unwind coverage:', [hex(x) for x in unknown])
    print('External branches:', sum(len(x['external_branches']) for x in inventory),
          'PC-relative references:', sum(len(x['pc_relative_data']) for x in inventory),
          'indirect transfers:', sum(len(x['indirect_control_flow']) for x in inventory))


if __name__ == '__main__':
    main()
