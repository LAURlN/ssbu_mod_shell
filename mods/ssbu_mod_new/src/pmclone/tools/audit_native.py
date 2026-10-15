"""Inventory exact NRO symbols and relocations, without patching executable code."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
from prepare import ROOT, NAMES, materialize, write_json


def parse_nro(path):
    data = path.read_bytes()
    if data[0x10:0x14] != b'NRO0':
        raise ValueError('Not an NRO: ' + str(path))
    declared = struct.unpack_from('<I', data, 0x18)[0]
    if declared != len(data):
        raise ValueError('Unexpected NRO declared size')
    mod = struct.unpack_from('<I', data, 4)[0]
    if data[mod:mod + 4] != b'MOD0':
        raise ValueError('Missing MOD0')
    at = mod + struct.unpack_from('<i', data, mod + 4)[0]
    tags = {}
    while True:
        tag, value = struct.unpack_from('<QQ', data, at)
        at += 16
        if tag == 0:
            break
        tags[tag] = value
    if tags[11] != 24:
        raise ValueError('Unexpected symbol size')
    count = struct.unpack_from('<I', data, tags[4] + 4)[0]  # DT_HASH nchain
    strings = data[tags[5]:tags[5] + tags[10]]
    symbols = []
    for index in range(count):
        name, info, other, section, value, size = struct.unpack_from('<IBBHQQ', data, tags[6] + index * 24)
        end = strings.index(0, name)
        label = strings[name:end].decode('utf8')
        symbols.append({'index': index, 'name': label, 'type': info & 15,
                        'binding': info >> 4, 'section': section, 'value': value, 'size': size})
    relocations = []
    for table, size_tag in ((7, 8), (23, 2)):
        if table not in tags:
            continue
        if tags[size_tag] % 24:
            raise ValueError('Invalid RELA size')
        for offset in range(tags[table], tags[table] + tags[size_tag], 24):
            target, info, addend = struct.unpack_from('<QQq', data, offset)
            symbol = info >> 32
            if symbol >= count:
                raise ValueError('Relocation has invalid symbol index')
            relocations.append({'table': table, 'offset': target, 'type': info & 0xffffffff,
                                'symbol': symbol, 'name': symbols[symbol]['name'], 'addend': addend})
    imports = [s for s in symbols if s['section'] == 0 and s['name']]
    exports = [s for s in symbols if s['section'] != 0 and s['name']]
    specific = [s for s in imports if re.search('eflame|elight|element', s['name'], re.I)]
    return {'file': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'symbol_count': count, 'defined_symbols': exports, 'imports': imports,
            'character_specific_imports': specific,
            'relocation_types': dict(Counter(str(r['type']) for r in relocations)),
            'relocations': relocations,
            'runtime_copy_loaded': False,
            'notes': 'A renamed file alone does not change symbol binding, hardcoded kinds, hash literals, or calls into main.'}


def main():
    summary = []
    for original, clone in NAMES.items():
        path = ROOT / 'editable/prebuilt/nro/release' / ('lua2cpp_' + clone + '.nro')
        result = parse_nro(path)
        write_json('native-' + clone + '.json', result)
        summary.append({'original': original, 'clone': clone, 'sha256': result['sha256'],
                        'defined_symbols': len(result['defined_symbols']),
                        'imports': len(result['imports']),
                        'character_specific_imports': [s['name'] for s in result['character_specific_imports']],
                        'relocations': len(result['relocations'])})
    main_path = ROOT.parent / 'references/mythra_gamewatch_feasibility/main_memory.bin'
    if main_path.is_file():
        data = main_path.read_bytes()
        write_json('main-dump.json', {'sha256': hashlib.sha256(data).hexdigest(),
                                    'bytes': len(data), 'copy_status': 'reference_only',
                                    'source': str(main_path),
                                    'provenance': 'Existing user dump; not freshly verified against running console'})
    write_json('native-summary.json', summary)
    for row in summary:
        print(row['clone'], 'defined', row['defined_symbols'], 'imports', row['imports'],
              'fighter-specific imports', len(row['character_specific_imports']), 'relocations', row['relocations'])


if __name__ == '__main__':
    main()
