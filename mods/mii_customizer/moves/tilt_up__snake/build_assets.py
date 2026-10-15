#!/usr/bin/env python3
"""Build game assets for MV-tilt_up__snake: Snake's up tilt (attack_hi3) on Mii Gunner.

Run from anywhere; needs the data.arc extraction (done here if missing), ssbh_data_py and Python 3.11+.

Inputs (workspace-relative):
- gamedata/ssbu-13.0.4/data.arc, read only through tools/arc-extract/target/release/arc-extract.exe
- gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb (Gunner skeleton)

Outputs, all under gamedata/mii_customizer/moves/tilt_up__snake/:
- extracted/                      donor and base files pulled from data.arc (game-derived, pinned by sha256 here)
- package/fighter/miigunner/motion/body/c00/c02mcsnakeattackhi3.nuanmb
                                  Snake's attack_hi3 clip retargeted to the Gunner skeleton (owned by this unit)
- reference/motion_list_vanilla_plus_owned.bin
                                  vanilla Gunner motion list + the one owned entry (a reference, not a shipped copy)
- reference/sound/...             vanilla Gunner sound files + the Snake additions listed in manifest.json
                                  (se_miigunner and se_miigunner_c00, the 36 vc_mii_* banks that hold the
                                  Gunner attack voice, and miigunner.sqb). Reference only: the installer applies
                                  the additions to the live files; the whole files are not shipped as "the" file.
- manifest.json                   sizes, hashes, the owned entry, the retarget report, the bone map, sound additions

Offline only (tier B): nothing here shows the move in game.
"""
from __future__ import annotations

import glob
import hashlib
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

MOD_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = MOD_ROOT.parent.parent
UNIT = 'tilt_up__snake'
OUT_BASE = WORKSPACE / 'gamedata/mii_customizer/moves' / UNIT
EXTRACTED = OUT_BASE / 'extracted'
PACKAGE_DIR = OUT_BASE / 'package'
REFERENCE_DIR = OUT_BASE / 'reference'
SOUND_REF = REFERENCE_DIR
MANIFEST_PATH = OUT_BASE / 'manifest.json'

DATA_ARC = WORKSPACE / 'gamedata/ssbu-13.0.4/data.arc'
ARC_EXTRACT = WORKSPACE / 'tools/arc-extract/target/release/arc-extract.exe'
GUNNER_SKEL = WORKSPACE / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb'

# Owned names (prefix mc_snake_ / mcsnake, attackhi3 kept in every name)
OWNED_KIND = 'mc_snake_attack_hi3'
OWNED_CLIP = 'c02mcsnakeattackhi3.nuanmb'
DONOR_CLIP = 'fighter/snake/motion/body/c00/c02attackhi3.nuanmb'
GUNNER_CLIP_DIR = 'fighter/miigunner/motion/body/c00'
SNAKE_MLIST = 'fighter/snake/motion/body/c00/motion_list.bin'
GUNNER_MLIST = 'fighter/miigunner/motion/body/c00/motion_list.bin'

# Donor sound names (kept as they are: the same tones are appended to the Gunner's banks)
SE_DONOR_STEM = 'sound/bank/fighter/se_snake_c00'
# Both Gunner SE banks carry the same 89 tone names (measured); the costume bank and the shared bank get the tone.
SE_RECIPIENT_STEMS = ['sound/bank/fighter/se_miigunner', 'sound/bank/fighter/se_miigunner_c00']
SE_TONES = ['se_snake_attackhard_h01']
VC_DONOR_STEM = 'sound/bank/fighter_voice/vc_snake_c00'
VC_TONES = ['vc_snake_attack01', 'vc_snake_attack02', 'vc_snake_attack03', 'vc_snake_attack04']
MII_VOICE_STEMS = [
    'sound/bank/fighter_voice/vc_mii_cheer',
    'sound/bank/fighter_voice/vc_mii_f01_girl_high',
    'sound/bank/fighter_voice/vc_mii_f01_girl_low',
    'sound/bank/fighter_voice/vc_mii_f01_girl_mid',
    'sound/bank/fighter_voice/vc_mii_f02_young_high',
    'sound/bank/fighter_voice/vc_mii_f02_young_low',
    'sound/bank/fighter_voice/vc_mii_f02_young_mid',
    'sound/bank/fighter_voice/vc_mii_f03_active_high',
    'sound/bank/fighter_voice/vc_mii_f03_active_low',
    'sound/bank/fighter_voice/vc_mii_f03_active_mid',
    'sound/bank/fighter_voice/vc_mii_f04_beauty_high',
    'sound/bank/fighter_voice/vc_mii_f04_beauty_low',
    'sound/bank/fighter_voice/vc_mii_f04_beauty_mid',
    'sound/bank/fighter_voice/vc_mii_f05_gloomy_high',
    'sound/bank/fighter_voice/vc_mii_f05_gloomy_low',
    'sound/bank/fighter_voice/vc_mii_f05_gloomy_mid',
    'sound/bank/fighter_voice/vc_mii_f06_warrior_high',
    'sound/bank/fighter_voice/vc_mii_f06_warrior_low',
    'sound/bank/fighter_voice/vc_mii_f06_warrior_mid',
    'sound/bank/fighter_voice/vc_mii_m01_boy_high',
    'sound/bank/fighter_voice/vc_mii_m01_boy_low',
    'sound/bank/fighter_voice/vc_mii_m01_boy_mid',
    'sound/bank/fighter_voice/vc_mii_m02_young_high',
    'sound/bank/fighter_voice/vc_mii_m02_young_low',
    'sound/bank/fighter_voice/vc_mii_m02_young_mid',
    'sound/bank/fighter_voice/vc_mii_m03_passionate_high',
    'sound/bank/fighter_voice/vc_mii_m03_passionate_low',
    'sound/bank/fighter_voice/vc_mii_m03_passionate_mid',
    'sound/bank/fighter_voice/vc_mii_m04_rough_high',
    'sound/bank/fighter_voice/vc_mii_m04_rough_low',
    'sound/bank/fighter_voice/vc_mii_m04_rough_mid',
    'sound/bank/fighter_voice/vc_mii_m05_cool_high',
    'sound/bank/fighter_voice/vc_mii_m05_cool_low',
    'sound/bank/fighter_voice/vc_mii_m05_cool_mid',
    'sound/bank/fighter_voice/vc_mii_m06_warrior_high',
    'sound/bank/fighter_voice/vc_mii_m06_warrior_low',
    'sound/bank/fighter_voice/vc_mii_m06_warrior_mid',
]
VC_RECIPIENT_NEEDLE = 'vc_mii_attack'  # a bank takes the additions only if it holds the Gunner attack voice
SQB_DONOR = 'sound/sequence/fighter/snake.sqb'
SQB_RECIPIENT = 'sound/sequence/fighter/miigunner.sqb'
SEQUENCE = 'seq_snake_rnd_attack'

# SHA-256 pins of every input this build reads (re-pinned on the first extraction, checked afterwards)
PINS = {
    DONOR_CLIP: 'f5151e106cbf78764159adf326e36e761d1800dfa189c06cfd77bfd76d9f5f71',
    SNAKE_MLIST: 'b70e42ca1e6ea143301349e268af5a7e98d391d0321a39c79a4187ef6fd39c34',
    SE_DONOR_STEM + '.nus3bank': '4e09776aad72a942e317be17b809e4dc8b8fa55c6f5538ba1510a1bfd4f28fa0',
    VC_DONOR_STEM + '.nus3bank': 'b8a677da89ebb3fafd3eb718a2f3db2a404cc9f40f58c3a4f88adb0117d3a0a8',
    SQB_DONOR: '90370dcfeaed1e27498c1eaf4dc6e2a64d03d79e6a2df8ac1daa7f45df44ce0b',
}
GUNNER_SKEL_SHA = '1d66b6d1cc4ce3b1c0883a21194cf998531c4a92ccb1c6561f69e68fd671429d'

# Hitbox bones of the donor's attack_hi3 script (decoded, see tables/acmd_calls.json).
HITBOX_BONES = ['top', 'kneel', 'legl']
# Bones the script names that are engine anchors, absent from BOTH model.nusktb files (not remapped).
ENGINE_ANCHORS = ['top']


# ---------------------------------------------------------------------------
# Hashing and paths
# ---------------------------------------------------------------------------

def hash40(name: str) -> int:
    return (len(name) << 32) | (zlib.crc32(name.encode('utf-8')) & 0xFFFFFFFF)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha(path.read_bytes())


def rel(path: Path) -> str:
    return path.relative_to(WORKSPACE).as_posix()


# ---------------------------------------------------------------------------
# Extraction (data.arc is read only through arc-extract; nothing is written into dump/)
# ---------------------------------------------------------------------------

def sound_paths() -> list[str]:
    paths = []
    stems = [SE_DONOR_STEM, VC_DONOR_STEM] + SE_RECIPIENT_STEMS
    for stem in stems:
        paths += [f'{stem}.{ext}' for ext in ('nus3audio', 'nus3bank', 'tonelabel')]
    paths += [SQB_DONOR, SQB_RECIPIENT]
    return paths


def ensure_extracted() -> None:
    wanted = [DONOR_CLIP, SNAKE_MLIST, GUNNER_MLIST, 'fighter/snake/model/body/c00/model.nusktb']
    wanted += sound_paths()
    for stem in MII_VOICE_STEMS:
        wanted += [f'{stem}.{ext}' for ext in ('nus3audio', 'nus3bank', 'tonelabel')]
    missing = [p for p in wanted if not (EXTRACTED / p).is_file()]
    if missing:
        assert ARC_EXTRACT.is_file(), f'arc-extract missing: {ARC_EXTRACT}'
        assert DATA_ARC.is_file(), f'data.arc missing: {DATA_ARC}'
        subprocess.run([str(ARC_EXTRACT), '--arc', str(DATA_ARC), '--out', str(EXTRACTED)] + missing, check=True)
    for p in missing:
        assert (EXTRACTED / p).is_file(), f'extraction did not produce {p}'
    for p, digest in PINS.items():
        assert sha_file(EXTRACTED / p) == digest, f'{p} is not the pinned revision'
    assert sha_file(GUNNER_SKEL) == GUNNER_SKEL_SHA, 'Gunner skeleton is not the pinned revision'


# ---------------------------------------------------------------------------
# Clip retarget (same recipe as the snake grenade unit, scratch/2026-10-07_MV-special_neutral__snake)
# ---------------------------------------------------------------------------

def retarget_clip() -> dict:
    import ssbh_data_py as s

    gunner = {b.name.lower() for b in s.skel_data.read_skel(str(GUNNER_SKEL)).bones}
    anim = s.anim_data.read_anim(str(EXTRACTED / DONOR_CLIP))
    removed, kept, groups = [], {}, {}
    for g in anim.groups:
        gname = str(g.group_type)
        groups[gname] = len(g.nodes)
        keep = []
        for n in g.nodes:
            if 'Transform' in gname:
                if n.name.lower() in gunner:
                    keep.append(n)
                else:
                    removed.append(n.name)
            else:
                keep.append(n)  # Visibility and Material tracks are kept whole, as in the grenade unit
        g.nodes = keep
        kept[gname] = len(keep)
    out = PACKAGE_DIR / 'fighter/miigunner/motion/body/c00' / OWNED_CLIP
    out.parent.mkdir(parents=True, exist_ok=True)
    anim.save(str(out))
    kept_transform = sorted(n.name for g in anim.groups if 'Transform' in str(g.group_type) for n in g.nodes)
    # Gunner bones the clip no longer drives (they keep their skeleton pose)
    unanimated = sorted(b for b in gunner if b not in {k.lower() for k in kept_transform})
    report = {
        'donor_groups': groups,
        'kept_groups': kept,
        'transform_nodes_kept': len(kept_transform),
        'transform_nodes_removed': sorted(removed),
        'gunner_bones_not_driven_by_clip': unanimated,
        'hitbox_bones': {b: {'on_gunner_skeleton': b in gunner,
                             'engine_anchor': b in ENGINE_ANCHORS} for b in HITBOX_BONES},
        'package_clip_sha256': sha_file(out),
        'package_clip_bytes': out.stat().st_size,
    }
    # The leg chain and the hips must survive the filter, or the move loses its kick
    for must in ('Hip', 'Waist', 'LegL', 'KneeL', 'FootL', 'LegR', 'KneeR', 'FootR'):
        assert must.lower() in {k.lower() for k in kept_transform}, f'retarget dropped {must}'
    return report


# ---------------------------------------------------------------------------
# Motion list (reference = vanilla Gunner list + the one owned entry)
# ---------------------------------------------------------------------------

def parse_mlist(data: bytes):
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset, entries = 24, []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        entries.append({'index': i, 'kind': kind, 'flags': flags, 'raw': data[start:end],
                        'tail_offset': tail - start, 'n_anims': n_anims, 'size': size})
        offset = end
    assert offset == len(data), 'motion list does not parse to its end'
    return magic, motion_path, entries


def owned_entry(donor_raw: bytes, tail: int) -> bytes:
    raw = bytearray(donor_raw)
    struct.pack_into('<QQ', raw, 0, hash40(OWNED_KIND), hash40('game_mcsnakeattackhi3'))
    struct.pack_into('<Q', raw, 24, hash40(OWNED_CLIP))
    # tail: expression, sound, effect (same order the donor entry uses)
    struct.pack_into('<QQQ', raw, tail,
                     hash40('expression_mcsnakeattackhi3'),
                     hash40('sound_mcsnakeattackhi3'),
                     hash40('effect_mcsnakeattackhi3'))
    return bytes(raw)


def build_motion_list() -> dict:
    magic_g, path_g, gun = parse_mlist((EXTRACTED / GUNNER_MLIST).read_bytes())
    _, _, snake = parse_mlist((EXTRACTED / SNAKE_MLIST).read_bytes())
    donor = [e for e in snake if e['kind'] == hash40('attack_hi3')]
    assert len(donor) == 1, 'donor attack_hi3 entry not unique'
    donor = donor[0]
    assert donor['flags'] == 0x84 and donor['n_anims'] == 1
    tail = donor['tail_offset']
    cancel = struct.unpack_from('<H', donor['raw'], tail + 26)[0]
    assert cancel == 38, f'donor cancel frame is {cancel}, expected 38'
    assert not [e for e in gun if e['kind'] == hash40(OWNED_KIND)], 'owned kind already in the Gunner list'
    entry = owned_entry(donor['raw'], tail)
    all_raw = [e['raw'] for e in gun] + [entry]
    data = struct.pack('<QQQ', magic_g, path_g, len(all_raw)) + b''.join(all_raw)
    out = REFERENCE_DIR / 'motion_list_vanilla_plus_owned.bin'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    # Read the written file back and check it (the file is the artefact, not the buffer)
    _, _, back = parse_mlist(out.read_bytes())
    assert len(back) == len(gun) + 1 and back[-1]['raw'] == entry
    assert [e['raw'] for e in back[:-1]] == [e['raw'] for e in gun], 'a vanilla entry changed'
    return {
        'donor_index': donor['index'],
        'donor_kind': hex(donor['kind']),
        'donor_flags': hex(donor['flags']),
        'donor_cancel_frame': cancel,
        'donor_blend': 0,
        'donor_entry_raw_sha256': sha(donor['raw']),
        'owned_entry_raw_sha256': sha(entry),
        'owned_entry_index': len(gun),
        'gunner_entries_before': len(gun),
        'list_entries_after': len(back),
        'list_bytes': out.stat().st_size,
        'list_sha256': sha_file(out),
    }


# ---------------------------------------------------------------------------
# Sound additions (codec copied from mods/ssbu_mod_new/tools/merge_hero_neutral_b_sound.py)
# ---------------------------------------------------------------------------

u32 = lambda data, offset: struct.unpack_from('<I', data, offset)[0]
pack = lambda n: struct.pack('<I', n)


def chunk(tag, payload):
    return tag + pack(len(payload)) + payload


def audio_read(data):
    assert data[:4] == b'NUS3' and data[8:12] == b'AUDI'
    assert u32(data, 4) + 8 == len(data)
    offset, chunks = 12, {}
    while offset < len(data):
        tag = data[offset:offset + 4]
        size = u32(data, offset + 4)
        assert tag not in chunks and offset + 8 + size <= len(data)
        chunks[tag] = data[offset + 8:offset + 8 + size]
        offset += 8 + size
    assert set(chunks) == {b'INDX', b'TNID', b'NMOF', b'ADOF', b'TNNM', b'JUNK', b'PACK'}
    count = u32(chunks[b'INDX'], 0)
    ids = list(struct.unpack('<' + 'I' * count, chunks[b'TNID']))
    assert ids == list(range(count)), 'Nonsequential tone ids need a separate mapping'
    result = []
    for i in range(count):
        name_offset = u32(chunks[b'NMOF'], i * 4)
        name = data[name_offset:data.index(b'\0', name_offset)].decode()
        start, size = struct.unpack_from('<II', chunks[b'ADOF'], i * 8)
        assert start + size <= len(data)
        result.append((name, data[start:start + size]))
    assert len({n for n, _ in result}) == count
    return result


def audio_write(entries):
    count = len(entries)
    prefix = chunk(b'INDX', pack(count)) + chunk(b'TNID', b''.join(pack(i) for i in range(count)))
    name_start = 12 + len(prefix) + 8 + count * 4 + 8 + count * 8 + 8
    names, name_offsets = bytearray(), []
    for name, _ in entries:
        name_offsets.append(name_start + len(names))
        names += name.encode() + b'\0'
    prefix += chunk(b'NMOF', b''.join(pack(n) for n in name_offsets))
    name_chunk = chunk(b'TNNM', bytes(names))
    before_junk = 12 + len(prefix) + 8 + count * 8 + len(name_chunk)
    padding = (-before_junk - 16) % 16
    audio_start = before_junk + 8 + padding + 8
    payload, offsets = bytearray(), []
    for _, encoded in entries:
        offsets.append((audio_start + len(payload), len(encoded)))
        payload += encoded
        payload += b'\0' * (-len(payload) % 16)
    body = prefix + chunk(b'ADOF', b''.join(struct.pack('<II', *o) for o in offsets))
    body += name_chunk + chunk(b'JUNK', b'\0' * padding) + chunk(b'PACK', bytes(payload))
    result = b'NUS3' + pack(4 + len(body)) + b'AUDI' + body
    assert audio_read(result) == entries
    return result


def bank_read(data):
    assert data[:4] == b'NUS3' and data[8:16] == b'BANKTOC '
    assert u32(data, 4) + 8 == len(data)
    count = u32(data, 20)
    assert u32(data, 16) == 4 + count * 8
    offset, result = 20 + u32(data, 16), []
    for i in range(count):
        tag = data[offset:offset + 4]
        size = u32(data, offset + 4)
        assert data[24 + i * 8:32 + i * 8] == tag + pack(size)
        result.append((tag, data[offset + 8:offset + 8 + size]))
        offset += 8 + size
    assert offset == len(data)
    return result


def bank_write(chunks):
    body = b'BANKTOC ' + pack(4 + len(chunks) * 8) + pack(len(chunks))
    body += b''.join(tag + pack(len(data)) for tag, data in chunks)
    body += b''.join(chunk(tag, data) for tag, data in chunks)
    result = b'NUS3' + pack(len(body)) + body
    assert bank_read(result) == chunks
    return result


def tones_read(payload):
    count = u32(payload, 0)
    entries = []
    for i in range(count):
        off, size = struct.unpack_from('<II', payload, 4 + i * 8)
        assert off >= 4 + count * 8 and off + size <= len(payload)
        entries.append(payload[off:off + size])
    assert 4 + count * 8 + sum(map(len, entries)) == len(payload)
    return entries


def tones_write(entries):
    offset, table = 4 + len(entries) * 8, bytearray()
    for data in entries:
        table += struct.pack('<II', offset, len(data))
        offset += len(data)
    result = pack(len(entries)) + table + b''.join(entries)
    assert tones_read(result) == entries
    return result


def group_links(tone, names):
    """Kind 0 (single sample) returns []; kind 3 returns the child-index positions; others are refused."""
    name_at = 12 if u32(tone, 4) & 0x80000000 else 8
    size = tone[name_at]
    name = tone[name_at + 1:name_at + size].decode()
    assert name.lower() in {n.lower() for n in names}
    start = (name_at + 1 + size + 3) & ~3
    kind = u32(tone, start)
    if kind == 0:
        assert u32(tone, start + 4) == 8
        return []
    assert kind == 3, ('unsupported tone kind', name, kind)
    count = u32(tone, start + 8)
    payload_size = u32(tone, start + 4)
    assert payload_size == 8 + 16 * count and len(tone) == start + 8 + payload_size + 20
    links = []
    for row in range(count):
        at = start + 16 + 16 * row
        assert 0 <= struct.unpack_from('<f', tone, at + 4)[0] <= 1
        assert u32(tone, at + 8) in (1, 2)
        child = u32(tone, at + 12)
        assert child < len(names)
        links.append(at + 12)
    return links


def labels_read(data, names):
    assert u32(data, 0) == 1 and u32(data, 4) == len(names)
    entries = list(struct.iter_unpack('<II', data[8:]))
    assert {value >> 8 for _, value in entries} == set(range(len(names)))
    for crc, value in entries:
        assert crc == zlib.crc32(names[value >> 8].lower().encode())
        assert value & 0xff == len(names[value >> 8].encode())
    return entries


def sqb_read(data):
    assert data[:4] == b'SQB\0'
    version, count = struct.unpack_from('<HH', data, 4)
    assert version == 1 and u32(data, 8) == count * 4
    base = 12 + count * 4
    offsets = list(struct.unpack_from('<' + 'I' * count, data, 12)) + [len(data) - base]
    assert offsets[0] == 0 and offsets == sorted(offsets)
    return [data[base + offsets[i]:base + offsets[i + 1]] for i in range(count)]


def sqb_write(entries):
    offsets, off = [], 0
    for entry in entries:
        offsets.append(off)
        off += len(entry)
    return (b'SQB\0' + struct.pack('<HHI', 1, len(entries), 4 * len(entries))
            + b''.join(map(pack, offsets)) + b''.join(entries))


def labels_read_partial(data, names):
    """labels_read for a donor whose label table does not name every tone.

    Measured 2026-10-02 (other mod's tools/merge_snake_uptilt_sound.py): the pinned vc_snake_c00.tonelabel
    has 34 entries for 48 audio files. Every entry that is present is still checked against its name.
    """
    assert u32(data, 0) == 1
    entries = list(struct.iter_unpack('<II', data[8:]))
    assert u32(data, 4) == len(entries)
    for crc, value in entries:
        assert 0 <= (value >> 8) < len(names), f'label points outside the bank: {value:#x}'
        assert crc == zlib.crc32(names[value >> 8].lower().encode())
        assert value & 0xff == len(names[value >> 8].encode())
    return entries


def read_bank(stem: Path, partial_labels: bool = False):
    entries = audio_read(stem.with_suffix('.nus3audio').read_bytes())
    chunks = bank_read(stem.with_suffix('.nus3bank').read_bytes())
    reader = labels_read_partial if partial_labels else labels_read
    labels = reader(stem.with_suffix('.tonelabel').read_bytes(), [n for n, _ in entries])
    return entries, chunks, labels


def append_tones(donor_stem: Path, recipient_stem: Path, dest_stem: Path, wanted: list[str]) -> dict:
    """Append the named donor tones (sample bytes and tone records unchanged) to the recipient bank."""
    donor, chunks_d, labels_d = read_bank(donor_stem, partial_labels=True)
    names = [n for n, _ in donor]
    dc = dict(chunks_d)
    tones_d = tones_read(dc[b'TONE'])
    wanted_l = [w.lower() for w in wanted]
    selected = [names.index(next(n for n in names if n.lower() == w)) for w in wanted_l]
    for i in selected:
        assert group_links(tones_d[i], names) == [], f'{names[i]} is a group tone'

    original, chunks_r, labels_r = read_bank(recipient_stem)
    rc = dict(chunks_r)
    for tag in (b'GRP ', b'DTON', b'PACK'):
        assert rc[tag] == dc[tag], f'{recipient_stem.name}: {tag!r} differs from the donor bank'
    tones_r = tones_read(rc[b'TONE'])
    assert all(a.lower() not in wanted_l for a, _ in original), f'{recipient_stem.name}: a requested tone already exists'
    entries = original + [donor[i] for i in selected]
    assert len({n.lower() for n, _ in entries}) == len(entries), 'tone name collision'

    mapping = {i: len(original) + j for j, i in enumerate(selected)}
    # A donor label of an appended tone is rebased to its new index; kinds 0 only, so no child links exist.
    labels = list(labels_r) + [(crc, mapping[value >> 8] << 8 | (value & 255))
                               for crc, value in labels_d if value >> 8 in mapping]
    labels.sort()
    label_bytes = pack(1) + pack(len(labels)) + b''.join(struct.pack('<II', *p) for p in labels)
    labels_read(label_bytes, [n for n, _ in entries])
    merged_tones = tones_r + [tones_d[i] for i in selected]
    audio_bytes = audio_write(entries)
    bank_bytes = bank_write([(tag, tones_write(merged_tones) if tag == b'TONE' else data)
                             for tag, data in chunks_r])
    dest_stem.parent.mkdir(parents=True, exist_ok=True)
    dest_stem.with_suffix('.nus3audio').write_bytes(audio_bytes)
    dest_stem.with_suffix('.tonelabel').write_bytes(label_bytes)
    dest_stem.with_suffix('.nus3bank').write_bytes(bank_bytes)

    # Verify against the written files, and prove nothing pre-existing was lost.
    back, chunks_back, labels_back = read_bank(dest_stem)
    cb = dict(chunks_back)
    assert back[:len(original)] == original, 'a pre-existing sample changed'
    assert [n for n, _ in back] == [n for n, _ in entries]
    assert cb[b'BINF'] == rc[b'BINF'], 'recipient BINF identity changed'
    assert cb[b'PROP'] == rc[b'PROP']
    assert tones_read(cb[b'TONE'])[:len(tones_r)] == tones_r, 'a pre-existing tone record changed'
    kept = {(crc, value) for crc, value in labels_back if value >> 8 < len(original)}
    assert kept == set(labels_r), 'a pre-existing tone label was lost or rebased'
    resolved = {zlib.crc32(w.encode()) for w in wanted_l}
    assert resolved <= {crc for crc, _ in labels_back}, 'appended tones do not resolve'
    return {
        'recipient': recipient_stem.name,
        'retained_tones': len(original),
        'appended': [names[i] for i in selected],
        'output_sha256': {
            'nus3audio': sha(audio_bytes), 'nus3bank': sha(bank_bytes), 'tonelabel': sha(label_bytes)},
    }


def build_sound() -> dict:
    report = {'banks': [], 'sequence': SEQUENCE}
    # 1. SE: Snake's hard-attack tone into both Gunner SE banks (costume bank and shared bank)
    for stem in SE_RECIPIENT_STEMS:
        report['banks'].append(append_tones(
            EXTRACTED / SE_DONOR_STEM, EXTRACTED / stem, SOUND_REF / stem, SE_TONES)
            | {'folder': 'fighter', 'stem': stem})
    # 2. Voice: Snake's four attack lines into every Mii voice bank that holds the Gunner's attack voice
    donor_voice = [n for n, _ in audio_read((EXTRACTED / VC_DONOR_STEM).with_suffix('.nus3audio').read_bytes())]
    snake_seq = [r for r in sqb_read((EXTRACTED / SQB_DONOR).read_bytes()) if int.from_bytes(r[:8], 'little') == hash40(SEQUENCE)]
    measured = sorted(n for n in donor_voice if n.startswith('vc_snake_') and zlib.crc32(n.lower().encode()).to_bytes(4, 'little') in snake_seq[0])
    assert measured == sorted(VC_TONES), f'voice set measured from the record differs: {measured}'
    voice_banks = []
    for stem in MII_VOICE_STEMS:
        p = EXTRACTED / stem
        names = [n for n, _ in audio_read(p.with_suffix('.nus3audio').read_bytes())]
        if not any(n.lower().startswith(VC_RECIPIENT_NEEDLE) for n in names):
            continue
        voice_banks.append(stem)
        dest = SOUND_REF / stem
        report['banks'].append(append_tones(EXTRACTED / VC_DONOR_STEM, p, dest, VC_TONES) | {'folder': 'fighter_voice', 'stem': stem})
    report['voice_banks'] = voice_banks
    # 3. Sequence: the exact seq_snake_rnd_attack record into the Gunner's sequence file
    snake_recs = sqb_read((EXTRACTED / SQB_DONOR).read_bytes())
    key = hash40(SEQUENCE)
    recs = [r for r in snake_recs if int.from_bytes(r[:8], 'little') == key]
    assert len(recs) == 1, f'{SEQUENCE}: expected one donor record, found {len(recs)}'
    gun_bytes = (EXTRACTED / SQB_RECIPIENT).read_bytes()
    gun_recs = sqb_read(gun_bytes)
    assert not [r for r in gun_recs if int.from_bytes(r[:8], 'little') == key], 'Gunner sqb already has the record'
    merged = sqb_write(gun_recs + recs)
    assert sqb_read(merged) == gun_recs + recs
    dest = SOUND_REF / SQB_RECIPIENT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(merged)
    assert sqb_read(dest.read_bytes())[:len(gun_recs)] == gun_recs
    report['sqb_records_before'] = len(gun_recs)
    report['sqb_records_after'] = len(gun_recs) + 1
    report['sqb_sha256'] = sha_file(dest)
    report['sqb_donor_record_sha256'] = sha(recs[0])
    return report


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def main() -> None:
    print(f'Building MV-tilt_up__snake assets into {OUT_BASE}')
    ensure_extracted()
    retarget = retarget_clip()
    print(f"retarget: kept {retarget['transform_nodes_kept']} transform nodes, removed {len(retarget['transform_nodes_removed'])}")
    mlist = build_motion_list()
    print(f"motion list: {mlist['list_entries_after']} entries, owned entry index {mlist['owned_entry_index']}")
    sound = build_sound()
    print(f"sound: {len(sound['banks'])} banks, voice banks {len(sound['voice_banks'])}, sqb {sound['sqb_records_after']} records")

    files = {}
    for p in sorted(PACKAGE_DIR.rglob('*')) + sorted(REFERENCE_DIR.rglob('*')):
        if p.is_file():
            files[rel(p)] = {'bytes': p.stat().st_size, 'sha256': sha_file(p)}
    manifest = {
        'unit': 'tilt_up__snake',
        'task_id': 'MV-tilt_up__snake',
        'entry': 'tilt_up',
        'donor': 'snake',
        'donor_motion_kind': 'attack_hi3',
        'owned_motion_kind': OWNED_KIND,
        'owned_clip': OWNED_CLIP,
        'owned_script_names': {
            'game': 'game_mcsnakeattackhi3', 'effect': 'effect_mcsnakeattackhi3',
            'sound': 'sound_mcsnakeattackhi3', 'expression': 'expression_mcsnakeattackhi3'},
        'owned_script_hashes': {
            n: f'0x{hash40(n):010x}' for n in ('game_mcsnakeattackhi3', 'effect_mcsnakeattackhi3',
                                                'sound_mcsnakeattackhi3', 'expression_mcsnakeattackhi3')},
        'owned_clip_hash': f'0x{hash40(OWNED_CLIP):010x}',
        'owned_kind_hash': f'0x{hash40(OWNED_KIND):010x}',
        'statuses_taken_over': ['FIGHTER_STATUS_KIND_ATTACK_HI3 (43)'],
        'retarget': retarget,
        'motion_list': mlist,
        'sound': sound,
        'engine_anchors_not_remapped': ENGINE_ANCHORS,
        'inputs_pinned': {p: h for p, h in PINS.items()} | {'gunner_skeleton': GUNNER_SKEL_SHA},
        'files': files,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'manifest: {MANIFEST_PATH}')
    print('build complete')


if __name__ == '__main__':
    sys.exit(main())
