"""Package vanilla Monkey Flip motions into the workspace's SD-card output.

Layout: ultimate-research/motion_lib @ 25dc4f94cb4f0587785820dc5d22318688f5b2df.
Preserve the recipient's motion path and all unrelated entries byte for byte.
"""
from pathlib import Path
import os
import hashlib
import json
import shutil
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
EXPORT = Path(os.environ.get('MGW_EXPORT', ROOT / 'dumps' / 'arc'))
OUT = ROOT / 'builds/.cache/mgw_swap/monkey_flip/fighter/gamewatch/motion/body/c07'
MOTIONS = (
    'special_s_start', 'special_air_s_start', 'special_air_s_jump',
    'special_air_s_kick', 'special_s_kick_landing', 'special_s_landing',
    'special_air_s_fall', 'special_s_stick', 'special_s_stick_attack',
    'special_s_stick_attack2', 'special_s_stick_jump', 'special_s_stick_jump2',
)

def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)

def parse_mlist(path):
    data = Path(path).read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data)
    if magic != hash40('motion'):
        raise ValueError(f'Invalid motion-list header: {path}')
    offset = 24
    motions = {}
    for _ in range(count):
        start = offset
        kind, game_script, flags, blend, animations, size = struct.unpack_from('<QQHBBI', data, offset)
        if animations > 3 or size % 8 not in (0, 4):
            raise ValueError(f'Invalid motion entry: {path} at {offset:#x}')
        offset += 24
        names = struct.unpack_from('<' + 'Q' * animations, data, offset)
        offset = (offset + animations * 9 + 3) & ~3
        end = offset + size
        if end > len(data) or kind in motions:
            raise ValueError(f'Truncated or duplicate motion: {path}, {kind:#x}')
        motions[kind] = {
            'raw': data[start:end], 'animations': names, 'game_script': game_script,
            'flags': flags, 'blend': blend,
            'cancel': data[end - 2] if size % 8 == 4 else None,
        }
        offset = end
    if offset != len(data):
        raise ValueError(f'Unexpected trailing data: {path}')
    return magic, motion_path, motions

def encode_mlist(magic, motion_path, motions):
    # Entries are four-byte aligned. Retain all variants, scripts, and flags.
    return struct.pack('<QQQ', magic, motion_path, len(motions)) + b''.join(m['raw'] for m in motions.values())

def build_assets(output=OUT):
    recipient = EXPORT / 'fighter/gamewatch/motion/body/c00/motion_list.bin'
    donor_dir = EXPORT / 'fighter/diddy/motion/body/c00'
    magic, path, baseline = parse_mlist(recipient)
    _, _, donor = parse_mlist(donor_dir / 'motion_list.bin')
    assert encode_mlist(magic, path, baseline) == recipient.read_bytes()
    motions = dict(baseline)
    animations = {hash40(p.name): p for p in donor_dir.glob('*.nuanmb')}
    copied = {}
    report = []
    for name in MOTIONS:
        entry = donor[hash40(name)]
        motions[hash40(name)] = entry
        for animation in entry['animations']:
            source = animations[animation]
            copied[source.name] = source
        report.append({'motion': name, 'cancel_frame': entry['cancel'],
                       'animations': [animations[h].name for h in entry['animations']]})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, source in copied.items():
        shutil.copy2(source, output / name)
    result = output / 'motion_list.bin'
    result.write_bytes(encode_mlist(magic, path, motions))
    _, _, check = parse_mlist(result)
    assert check == motions
    target_hashes = {hash40(n) for n in MOTIONS}
    assert all(check[k] == v for k, v in baseline.items() if k not in target_hashes)
    manifest = {'output': str(output), 'motions': report,
                'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in [result, *(output / n for n in copied)]}}
    (ROOT / 'references/diddy_specials/asset_manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'Validated {len(MOTIONS)} vanilla motions and {len(copied)} animations in {output}')
    return manifest

if __name__ == '__main__':
    build_assets()
