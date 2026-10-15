"""v0.1.0: offline, symbol-bounded native throw route audit on pinned 13.0.4 NROs."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
LAB = ROOT.parents[1]
OUT = ROOT / 'evidence/2026-10-02_pgwr_gaogaen_throw_b'
sys.path[:0] = [str(ROOT / 'builds/.cache/gaogaen_throw_b/python'), str(ROOT / 'tools/nro_decomp')]
from nro_flatten import flatten, parse
import nro_util as u
import status_table

def main():
    pins = json.loads((OUT / 'NATIVE_INPUTS.json').read_text())
    native = {}
    for pin in pins:
        data = (LAB / pin['local_path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == pin['sha256']
        native[Path(pin['local_path']).stem] = data
    ns = {'__file__': str(ROOT / 'tools/constmap.py')}
    const_source = (ROOT / 'tools/constmap.py').read_text().split("if __name__")[0]
    const_source = const_source.replace('d=NRO_PATH.read_bytes()', 'd=native_common')
    ns['native_common'] = native['lua2cpp_common']
    exec(compile(const_source, 'constmap.py', 'exec'), ns)
    u.const_name = ns['name']
    image, meta = flatten(native['lua2cpp_gaogaen'])
    rows = status_table.table(image, meta)
    throw_rows = [row for row in rows if row[0] == 'FIGHTER_STATUS_KIND_THROW']
    assert throw_rows == [('FIGHTER_STATUS_KIND_THROW', 'LUA_SCRIPT_STATUS_FUNC_STATUS_PRE', 0x10da0)]
    (OUT / 'GAOGAEN_STATUS_TABLE.json').write_text(json.dumps(rows, indent=2) + '\n')
    report = {'inputs': pins, 'gaogaen_throw_registrations': throw_rows, 'functions': []}
    for fighter, data in native.items():
        image, meta = flatten(data)
        plt = u.plt_map(image, meta['labels'], meta['text_end'])
        labels = {int(a, 16): n for a, n in meta['labels'].items()}
        labels.update(plt)
        symbols, _, _ = parse(data)
        selected = [(n, a, size) for n, _, sh, a, size in symbols if sh and 'bind_' not in n and
                    re.search(r'status_(pre_|end_)?ThrowEv|status_Throw_(Main|Sub)|sub_throw|ThrowUniq|ProcessThrown|status_Thrown(Ev|_common)|sub_Thrown|sub_thrown|sub_is_not_throw_status_kind', n)]
        if fighter == 'lua2cpp_gaogaen':
            selected = [('gaogaen_Throw_pre', 0x10da0, 0x31c),
                ('gaogaen_game_throwb_registration', 0x28a70, 0x1c),
                ('gaogaen_game_throwb_wrapper', 0x9afb0, 0x90),
                ('gaogaen_game_throwb_body', 0xddba0, 0x1030)]
        for name, address, size in selected:
            lines, calls, constants = [], [], []
            for ins in u.disasm(image, address, size):
                note = ''
                if ins.mnemonic in ('bl', 'b'):
                    target = int(ins.op_str.lstrip('#'), 0)
                    note = labels.get(target, 'local/unresolved')
                    calls.append({'site': hex(ins.address), 'target': hex(target), 'name': note})
                if ins.mnemonic == 'ldr' and ins.op_str.startswith('w1,'):
                    m = re.search(r'#(0x[0-9a-f]+|\d+)\]', ins.op_str)
                    if m:
                        value = u.const_name(int(m[1], 0))
                        if value:
                            note += ' [candidate constant ' + value + ']'
                            constants.append({'site': hex(ins.address), 'candidate': value})
                lines.append(f'{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str} ; {note}')
            path = OUT / 'native' / f'{fighter}_{address:x}.asm'
            path.write_text('\n'.join(lines) + '\n')
            report['functions'].append({'name': name, 'address': hex(address), 'size': size,
                'assembly': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'calls': calls, 'candidate_constants': constants})
    (OUT / 'ROUTES.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Pinned NROs and Gaogaen THROW registration checked;', len(report['functions']), 'bounded functions recorded.')

if __name__ == '__main__':
    main()
