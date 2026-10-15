"""Record the supplied neutral-B clips and raw Snake parameters without guessing labels."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent / 'runtime_lib'))
import pyprc


def record(path):
    result = {'path': str(path.relative_to(ROOT)), 'exists': path.is_file()}
    if path.is_file():
        data = path.read_bytes()
        result.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    return result


def main():
    refs = ROOT / 'references/snake_grenade'
    listing = refs / 'motion/fighter__snake__motion__body__c00__motion_list.yml'
    blocks = re.findall(r'^  (\w+):\n(.*?)(?=^  \w+:|\Z)', listing.read_text(), re.M | re.S)
    motions = []
    for name, body in blocks:
        if name.startswith(('special_n', 'special_air_n')):
            for filename in re.findall(r'- name: (.*)', body):
                motions.append({'motion': name, **record(ROOT / 'export/fighter/snake/motion/body/c00' / filename)})
    vl = ROOT / 'export/fighter/snake/param/vl.prc'
    special_n = pyprc.param(str(vl))[pyprc.hash('param_special_n')]
    params = [{str(key): {'type': str(value.type), 'value': value.value} for key, value in row}
              for row in special_n]
    result = {
        'motion_list_reference': record(listing), 'motions': motions,
        'skeleton': record(ROOT / 'export/fighter/snake/model/body/c00/model.nusktb'),
        'binary_motion_list': record(ROOT / 'export/fighter/snake/motion/body/c00/motion_list.bin'),
        'parameters': record(vl), 'param_special_n_rows': params,
        'notes': [
            'Raw parameter hashes retained until their uses are traced; no guessed throw velocities.',
            'SpecialNThrow__main.c queries 0x129fad2ee0 and 0x12602bfa52 to select throw animation.',
            'The native item fuse initializes itself; prototype does not modify the lifetime or attacks.',
        ],
    }
    out = refs / 'asset_audit.json'
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {out}; {sum(m["exists"] for m in motions)}/{len(motions)} body motion references available')


if __name__ == '__main__':
    main()
