#!/usr/bin/env python3
"""Append Corrin's up-air sound tone to ANY Mii Gunner sound-effect bank (additions only).

A PLAY_SE on a Gunner resolves in the banks the Gunner loaded, so Corrin's tone has to be in
`sound/bank/fighter/se_miigunner.{nus3audio,nus3bank,tonelabel}`. This script takes a base bank (vanilla, or one
another unit already appended to) and writes base + the appended tones. It does not own the file.

    python -I mods/mii_customizer/moves/aerial_up__kamui/mckamui_sounds.py \
        --base <dir holding se_miigunner.*> --output <dir under gamedata/mii_customizer or builds/.cache>

Tones (donor bank `se_kamui_c00`, names as stored there; lookups are CRC32 of the lowercased name):
    se_kamui_attackair_H01   up air swing (sound_attackairhi frame 4, PLAY_SE)
The tone name is NOT given the mc_kamui_ prefix: the tone record and its sample are copied as bytes (the recipe the
Cloud units use, and the reference repo ran on the console); renaming would mean rewriting variable-length records.

Not ported: the donor's PLAY_SEQUENCE `seq_kamui_rnd_attack_air` (Corrin's voice sequence). A Mii has its own voice, so
the Gunner's own `seq_miigunner_rnd_attack02` plays on the same frame (Cloud's rule for voices). No sequence file
is changed here.

Method = the Cloud units' `mccloud_sounds.py` (append_tones: BINF/PROP/GRP/DTON/PACK of the recipient kept, donor tone must
be single-sample, labels rebased). Tier B; nothing here shows a sound playing.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mckamui_sound_codec as codec  # noqa: E402

WORKSPACE = HERE.parents[3]
G = WORKSPACE / 'gamedata/mii_customizer'
DONOR_STEM = G / 'moves/aerial_up__kamui/donor/sound/bank/fighter/se_kamui_c00'
WANTED = ('se_kamui_attackair_h01',)
BANK = 'se_miigunner'
EXTS = ('.nus3audio', '.nus3bank', '.tonelabel')


def rel(p: Path) -> str:
    return p.resolve().relative_to(WORKSPACE).as_posix()


def merge(base_dir: Path, out_dir: Path) -> dict:
    base_dir, out_dir = Path(base_dir).resolve(), Path(out_dir).resolve()
    if not (out_dir.is_relative_to(G) or out_dir.is_relative_to(HERE.parents[1] / 'builds/.cache')):
        raise RuntimeError('output must be under gamedata/mii_customizer or builds/.cache')
    recipient = base_dir / BANK
    donor = codec.audio_read(DONOR_STEM.with_suffix('.nus3audio').read_bytes())
    names_d = [n for n, _ in donor]
    chunks_d = dict(codec.bank_read(DONOR_STEM.with_suffix('.nus3bank').read_bytes()))
    tones_d = codec.tones_read(chunks_d[b'TONE'])
    labels_d = codec.labels_read_partial(DONOR_STEM.with_suffix('.tonelabel').read_bytes(), names_d)
    wanted = set(WANTED)
    selected = [i for i, n in enumerate(names_d) if n.lower() in wanted]
    if len(selected) != len(wanted):
        raise RuntimeError(f'se_kamui_c00: {len(selected)} of {len(wanted)} tones found')
    for i in selected:
        if codec.group_links(tones_d[i], names_d) != []:
            raise RuntimeError(f'{names_d[i]} is a group tone; its children would dangle')

    original = codec.audio_read(recipient.with_suffix('.nus3audio').read_bytes())
    names_r = [n for n, _ in original]
    chunks_r = codec.bank_read(recipient.with_suffix('.nus3bank').read_bytes())
    for tag in (b'GRP ', b'DTON', b'PACK'):
        if dict(chunks_r)[tag] != chunks_d[tag]:
            raise RuntimeError(f'{BANK}: section {tag!r} differs from the donor bank')
    tones_r = codec.tones_read(dict(chunks_r)[b'TONE'])
    if {n.lower() for n in names_r} & wanted:
        raise RuntimeError('the base bank already has these tones: merge onto a bank without them')
    entries = original + [donor[i] for i in selected]
    mapping = {i: len(original) + j for j, i in enumerate(selected)}
    labels_r = codec.labels_read_partial(recipient.with_suffix('.tonelabel').read_bytes(), names_r)
    labels = labels_r + [(crc, mapping[value >> 8] << 8 | (value & 255))
                         for crc, value in labels_d if value >> 8 in mapping]
    labels.sort()
    label_bytes = codec.pack(1) + codec.pack(len(labels)) + b''.join(struct.pack('<II', *p) for p in labels)
    merged_tones = tones_r + [tones_d[i] for i in selected]
    files = {'.nus3audio': codec.audio_write(entries), '.tonelabel': label_bytes,
             '.nus3bank': codec.bank_write([(tag, codec.tones_write(merged_tones) if tag == b'TONE' else data)
                                            for tag, data in chunks_r])}
    back = codec.audio_read(files['.nus3audio'])
    if back != entries or back[:len(original)] != original:
        raise RuntimeError('nus3audio round trip changed an entry')
    if codec.tones_read(dict(codec.bank_read(files['.nus3bank']))[b'TONE']) != merged_tones:
        raise RuntimeError('nus3bank round trip changed a tone')
    final_labels = codec.labels_read_partial(files['.tonelabel'], [n for n, _ in entries])
    if not {zlib.crc32(n.encode()) for n in wanted} <= {crc for crc, _ in final_labels}:
        raise RuntimeError('a wanted tone has no label')
    if not set(labels_r) <= set(final_labels):
        raise RuntimeError('a recipient label was lost')
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext, content in files.items():
        (out_dir / (BANK + ext)).write_bytes(content)
    record = {
        'tool': 'mckamui_sounds.py', 'evidence_tier': 'B', 'hardware_validated': False,
        'base': {ext: {'path': rel(recipient.with_suffix(ext)),
                       'sha256': codec.sha(recipient.with_suffix(ext).read_bytes())} for ext in EXTS},
        'donor': {ext: {'path': rel(DONOR_STEM.with_suffix(ext)),
                        'sha256': codec.sha(DONOR_STEM.with_suffix(ext).read_bytes())} for ext in EXTS},
        'output': {ext: {'path': rel(out_dir / (BANK + ext)), 'sha256': codec.sha(files[ext])} for ext in EXTS},
        'retained_tones': len(original), 'total_tones': len(entries),
        'appended': [{'name': names_d[i], 'index': mapping[i], 'sample_bytes': len(donor[i][1]),
                      'sample_sha256': codec.sha(donor[i][1]), 'tone_record_sha256': codec.sha(tones_d[i])}
                     for i in selected],
    }
    (out_dir / (BANK + '.merge.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    rec = merge(a.base, a.output)
    print(f"appended {len(rec['appended'])} tone(s) ({rec['retained_tones']} -> {rec['total_tones']}) into "
          f"{rec['output']['.nus3bank']['path']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
