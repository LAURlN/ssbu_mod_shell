"""Locate native cargo message consumers without executing fighter code.

Run after semantic.py. Outputs candidate sites and their instruction windows;
a constant occurrence alone is not a recovered callback or an ownership proof.
"""
import json
import struct
import re
import audit
from audit import OUT, WS, sha, h40, cfg
from main_image import MainImage
from audit_mflip_capture_native import symbols


def run():
    img = MainImage(WS / 'gamedata/ssbu-13.0.4/main.bin')
    vocabulary = {h40(n): n for n in ('shoulder', 'shoulder_throw', 'capture_cut',
        'shouldered_donkey', 'thrown_f_donkey_f', 'thrown_f_donkey_b',
        'thrown_f_donkey_hi', 'thrown_f_donkey_lw')}
    vocabulary[0x21ba53a92c] = 'victim_mash_expiry_event'
    candidates = []
    # Filter raw MOVK #upper16, lsl #32 words, then decode the small window.
    upper = {v >> 32 for v in vocabulary}
    for a in range(0x100, 0x39c8000, 4):
        w = struct.unpack_from('<I', img.data, a)[0]
        if w & 0xffe00000 != 0xf2c00000 or (w >> 5) & 0xffff not in upper:
            continue
        regs = {}
        found = None
        for ins in img.disasm(max(0x100, a - 32), min(36, a - 0x100 + 4)):
            m = re.fullmatch(r'(x\d+), #(0x[0-9a-f]+|\d+)(?:, lsl #(\d+))?', ins.op_str)
            if ins.mnemonic not in ('mov', 'movk') or not m:
                continue
            reg, value, shift = m.groups()
            value, shift = int(value, 0), int(shift or 0)
            if ins.mnemonic == 'mov':
                regs[reg] = value
            elif reg in regs:
                regs[reg] = (regs[reg] & ~(0xffff << shift)) | (value << shift)
            if ins.address == a and regs.get(reg) in vocabulary:
                found = regs[reg]
        if found is None:
            continue
        name = vocabulary[found]
        text = '\n'.join(f'{i.address:#010x}: {i.mnemonic:8} {i.op_str}'
                         for i in img.disasm(a - 128, 384)) + '\n'
        target = OUT / 'semantic_asm' / f'message_{name}_{a:x}.asm'
        target.write_text(text)
        candidates.append({'at': hex(a), 'hash': hex(found), 'name': name,
                           'window': target.relative_to(OUT).as_posix(),
                           'window_sha256': sha(target.read_bytes())})
    result = {'tier': 'B', 'main_sha256': sha(img.data), 'candidates': candidates,
              'complete': False, 'runtime_verified': False,
              'limitation': 'Adjacent literal construction scan; not every producer/consumer.'}
    labels = {a: n for n, a, size in symbols(img) if a}
    exports = list(symbols(img))
    singleton = [dict(name=n, address=hex(a), size=size)
                 for n, a, size in exports
                 if n == '_ZN3lib9SingletonIN3app19FighterCutInManagerEE9instance_E']
    assert singleton == [{'name':'_ZN3lib9SingletonIN3app19FighterCutInManagerEE9instance_E',
                          'address':'0x52b8850','size':8}]
    result['cut_in_manager_symbol'] = {'exports': singleton,
        'route':'Bind the exported data symbol as an extern pointer; no hardcoded-offset lookup or new hook is needed for this proposed route.',
        'runtime_pointer_validation_required':True,'runtime_verified':False}
    branches = {}
    for a in (0x637fa4, 0x56963c):
        row, text = cfg(img.data, a, labels, limit=3000)
        (OUT / 'semantic_asm' / f'native_shoulder_branch_{a:x}.asm').write_text(text)
        branches[hex(a)] = row
    result['shoulder_branches'] = branches
    # Parameter row names are Hash40 fighter_kind_* labels, not numeric kinds.
    vocabulary_labels = json.loads((OUT / 'semantic_annotations.json').read_text())['hash_vocabulary']
    thrown = json.loads((OUT / 'fighter_param_thrown_cargo.json').read_text())
    result['thrown_row_names'] = [vocabulary_labels.get(hex(x['fighter_kind'][1]), hex(x['fighter_kind'][1]))
                                 for x in thrown['/fighter_param_thrown_table']]
    (OUT / 'native_message_sites.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Pinned', len(candidates), 'native literal sites; candidates only')


if __name__ == '__main__':
    run()
