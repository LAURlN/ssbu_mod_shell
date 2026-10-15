#!/usr/bin/env python3
"""Build the game assets of the MV-normal_jab__miifighter unit (Mii Brawler's jab on Mii Gunner).

Unit: entry normal_jab, donor miifighter, owned stages mc_miifighter_attack_11 and mc_miifighter_attack_12,
and the rapid jab mc_miifighter_attack_100_start / _100 / _100_end (donor clips copied byte for byte).

Outputs, all under the workspace gamedata/mii_customizer/moves/normal_jab__miifighter/:
- package/fighter/miigunner/motion/body/c00/c01mcmiifighterattack11.nuanmb and ...attack12.nuanmb:
  byte copies of the donor clips c00attack11.nuanmb and c00attack12.nuanmb (no edits).
- reference/motion_list_vanilla_plus_owned.bin: the vanilla Gunner motion list with ONLY this unit's
  two entries appended. Each entry is the donor entry with kind, game, expression, sound, effect and
  clip hashes replaced. The coordinator merges all units into one patch; this file is the reference
  that patch must reproduce.
- manifest.json (this unit's folder): sizes and sha256 of every file above, and the added entries.

No motion_list.bin, motion_list.motdiff or config.json is written into package/ (another mod owns the
Gunner's motion_list.bin; see evidence/2026-10-07_session4/RESULT_boot2.md).

Usage (workspace root): python -I mods/mii_customizer/moves/normal_jab__miifighter/build_assets.py
"""
from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
import struct
import zlib
from pathlib import Path

MOD_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = MOD_ROOT.parent.parent

P11 = WORKSPACE / "gamedata/mii_customizer/P11-MOVE-PLAN"
GUNNER_MLIST_SRC = P11 / "fighter/miigunner/motion/body/c00/motion_list.bin"
DONOR_MLIST_SRC = P11 / "fighter/miifighter/motion/body/c00/motion_list.bin"
DONOR_BODY_DIR = P11 / "fighter/miifighter/motion/body/c00"

UNIT_DIR = WORKSPACE / "gamedata/mii_customizer/moves/normal_jab__miifighter"
PACKAGE_BODY_DIR = UNIT_DIR / "package/fighter/miigunner/motion/body/c00"
REFERENCE_MLIST = UNIT_DIR / "reference/motion_list_vanilla_plus_owned.bin"
MANIFEST_PATH = UNIT_DIR / "manifest.json"

# (donor kind name, donor clip, owned stage name, owned clip)
STAGES = [
    ("attack_11", "c00attack11.nuanmb", "mc_miifighter_attack_11", "c01mcmiifighterattack11.nuanmb"),
    ("attack_12", "c00attack12.nuanmb", "mc_miifighter_attack_12", "c01mcmiifighterattack12.nuanmb"),
    ("attack_100_start", "c00attack100start.nuanmb", "mc_miifighter_attack_100_start", "c01mcmiifighterattack100start.nuanmb"),
    ("attack_100", "c00attack100.nuanmb", "mc_miifighter_attack_100", "c01mcmiifighterattack100.nuanmb"),
    ("attack_100_end", "c00attackend.nuanmb", "mc_miifighter_attack_100_end", "c01mcmiifighterattack100end.nuanmb"),
]


def hash40(string: str) -> int:
    return (len(string) << 32) | (zlib.crc32(string.encode("utf-8")) & 0xFFFFFFFF)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_mlist(data: bytes):
    """Same layout as tools/move-package/build_p16_assets.py (round-trip checked by check.py)."""
    magic, motion_path, count = struct.unpack_from("<QQQ", data, 0)
    offset = 24
    entries = []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from("<QQHBBI", data, offset)
        offset += 24
        anims = struct.unpack_from("<" + "Q" * n_anims, data, offset)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        raw = data[start:end]
        offset = end
        entries.append({
            "index": i, "kind": kind, "game": game, "flags": flags, "blend": blend,
            "n_anims": n_anims, "anims": anims, "size": size, "raw": raw,
            "tail_offset": tail - start,
        })
    return magic, motion_path, entries


def owned_name_parts(owned: str):
    """mc_miifighter_attack_11 -> script suffix mcmiifighterattack11 (as the worked example does)."""
    return owned.replace("_", "")


def create_entry(donor_entry: dict, owned: str, clip: str) -> bytes:
    suffix = owned_name_parts(owned)
    raw = bytearray(donor_entry["raw"])
    struct.pack_into("<QQ", raw, 0, hash40(owned), hash40("game_" + suffix))
    struct.pack_into("<Q", raw, 24, hash40(clip))
    tail = donor_entry["tail_offset"]
    struct.pack_into("<QQQ", raw, tail,
                     hash40("expression_" + suffix),
                     hash40("sound_" + suffix),
                     hash40("effect_" + suffix))
    return bytes(raw)



REFERENCE_DIR = UNIT_DIR / 'reference'
OUT_BASE = UNIT_DIR
SOUND_REF = REFERENCE_DIR


def sha_file(path: Path) -> str:
    return sha256_file(path)


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



# ---------------------------------------------------------------------------
# Sounds (added to the Gunner's own banks, codec and layout from tilt_up__snake/build_assets.py)
# ---------------------------------------------------------------------------

SE_DONOR_STEM = 'sound/bank/fighter/se_miifighter'
SE_RECIPIENT_STEMS = ['sound/bank/fighter/se_miigunner', 'sound/bank/fighter/se_miigunner_c00']
# the Brawler's tones: the rapid hit, the finisher swing and the two stage swings (stage 1 uses _s, stage 2 uses _m)
SE_TONES = ['se_miifighter_attack100', 'se_miifighter_swing_l', 'se_miifighter_swing_s', 'se_miifighter_swing_m']
SQB_DONOR = 'sound/sequence/fighter/miifighter.sqb'
SQB_RECIPIENT = 'sound/sequence/fighter/miigunner.sqb'
SEQUENCES = ['seq_miifighter_rnd_attack100', 'seq_miifighter_rnd_attack02']
# Mii voice tones the two sequence records play (measured from the records, see voice_report)
VOICE_TONES = ['vc_mii_attack04', 'vc_mii_attack05', 'vc_mii_attack06', 'vc_mii_attack100']

EXTRACTED = OUT_BASE / 'extracted'                 # game-derived inputs, written by arc-extract only
DATA_ARC = WORKSPACE / 'gamedata/ssbu-13.0.4/data.arc'
ARC_EXTRACT = WORKSPACE / 'tools/arc-extract/target/release/arc-extract.exe'
ENGINE_DIR = WORKSPACE / 'mods/mii_customizer/scratch/2026-10-08_MV-normal_jab__miifighter/effect_merge'

EFFECT_DONOR = 'effect/fighter/miifighter/ef_miifighter.eff'
EFFECT_RECIPIENT = 'effect/fighter/miigunner/ef_miigunner.eff'
EFFECT_EMITTER = 'MIIFIGHTER_ATTACK100'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sound_input_paths() -> list[str]:
    stems = [SE_DONOR_STEM] + SE_RECIPIENT_STEMS
    paths = [f'{s}.{e}' for s in stems for e in ('nus3audio', 'nus3bank', 'tonelabel')]
    paths += [SQB_DONOR, SQB_RECIPIENT]
    paths += [f'{s}.nus3audio' for s in MII_VOICE_STEMS]
    return paths


def ensure_inputs() -> None:
    """Pull the sound and effect inputs from data.arc (arc-extract) when they are missing; nothing is written to dump/."""
    wanted = sound_input_paths() + [EFFECT_DONOR, EFFECT_RECIPIENT]
    missing = [p for p in wanted if not (EXTRACTED / p).is_file()]
    if missing:
        assert ARC_EXTRACT.is_file(), f'arc-extract missing: {ARC_EXTRACT}'
        assert DATA_ARC.is_file(), f'data.arc missing: {DATA_ARC}'
        subprocess.run([str(ARC_EXTRACT), '--arc', str(DATA_ARC), '--out', str(EXTRACTED)] + missing, check=True)
    for p in wanted:
        assert (EXTRACTED / p).is_file(), f'extraction did not produce {p}'


def voice_report() -> dict:
    """Which Mii voice banks hold the four tones the two rapid sequence records play (measured)."""
    # only banks that hold an attack voice are candidates (same rule as tilt_up__snake: VC_RECIPIENT_NEEDLE)
    per_bank, excluded = {}, []
    for stem in MII_VOICE_STEMS:
        names = {n.lower() for n, _ in audio_read((EXTRACTED / stem).with_suffix('.nus3audio').read_bytes())}
        if not any(n.startswith('vc_mii_attack') for n in names):
            excluded.append(stem)
            continue
        per_bank[stem] = [t for t in VOICE_TONES if t in names]
    complete = [s for s, found in per_bank.items() if len(found) == len(VOICE_TONES)]
    return {'tones': VOICE_TONES, 'banks_total': len(per_bank), 'banks_with_all_tones': len(complete),
            'banks_with_all_tones_list': complete, 'banks_excluded_no_attack_voice': excluded,
            'banks_missing_tones': [s for s in per_bank if s not in complete]}


def build_sound() -> dict:
    report = {'banks': [], 'sequences': []}
    for stem in SE_RECIPIENT_STEMS:
        report['banks'].append(append_tones(
            EXTRACTED / SE_DONOR_STEM, EXTRACTED / stem, SOUND_REF / stem, SE_TONES) | {'stem': stem})
    donor_recs = sqb_read((EXTRACTED / SQB_DONOR).read_bytes())
    gun_recs = sqb_read((EXTRACTED / SQB_RECIPIENT).read_bytes())
    additions = []
    for seq in SEQUENCES:
        key = hash40(seq)
        found = [r for r in donor_recs if int.from_bytes(r[:8], 'little') == key]
        assert len(found) == 1, f'{seq}: expected one donor record, found {len(found)}'
        assert not [r for r in gun_recs if int.from_bytes(r[:8], 'little') == key], f'{seq} already in the Gunner sqb'
        additions.append(found[0])
        report['sequences'].append({'name': seq, 'key': f'0x{key:010x}', 'bytes': len(found[0]),
                                    'record_sha256': sha(found[0])})
    merged = sqb_write(gun_recs + additions)
    assert sqb_read(merged) == gun_recs + additions
    dest = SOUND_REF / SQB_RECIPIENT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(merged)
    report['sqb_records_before'] = len(gun_recs)
    report['sqb_records_after'] = len(gun_recs) + len(additions)
    report['sqb_sha256'] = sha(merged)
    report['voice'] = voice_report()
    return report


# ---------------------------------------------------------------------------
# Effect: the Brawler's miifighter_attack100 emitter merged into the Gunner's own bank
# (engine: mods/ssbu_mod_new/tools/merge_hero_neutral_b_effects.py, copied to the scratch folder and
#  redirected to its own root; the merge logic is unchanged)
# ---------------------------------------------------------------------------

def build_effect() -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location('merge_hero_engine_copy', ENGINE_DIR / 'merge_hero_engine_copy.py')
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    donor = EXTRACTED / EFFECT_DONOR
    recipient = EXTRACTED / EFFECT_RECIPIENT
    out = ENGINE_DIR / 'builds' / 'ef_miigunner.eff'
    scratch = ENGINE_DIR / 'scratch'
    out.parent.mkdir(parents=True, exist_ok=True)
    engine.merge(recipient, out, donor_file=donor, effect_names={EFFECT_EMITTER},
                 donor_sha256=engine.sha(donor), scratch=str(scratch))
    record = json.loads(out.with_suffix('.merge.json').read_text())
    dest = REFERENCE_DIR / 'effect' / 'fighter' / 'miigunner' / 'ef_miigunner.eff'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(out.read_bytes())
    (dest.parent / 'ef_miigunner.merge.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return {'emitter': EFFECT_EMITTER, 'donor': EFFECT_DONOR, 'donor_sha256': sha(donor.read_bytes()),
            'recipient': EFFECT_RECIPIENT, 'recipient_sha256': sha(recipient.read_bytes()),
            'output_sha256': sha(dest.read_bytes()), 'output_bytes': dest.stat().st_size,
            'texture_id_relocations': len(record['texture_id_relocations']),
            'model_id_relocations': len(record['model_id_relocations']),
            'resource_names': record['resource_names'], 'engine_tier': record['evidence_tier']}


def main_sound_effect() -> None:
    ensure_inputs()
    sound = build_sound()
    effect = build_effect()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    manifest['sound'] = sound
    manifest['effect'] = effect
    manifest['inputs_sha256'] = {p: sha((EXTRACTED / p).read_bytes()) for p in
                                 sound_input_paths() + [EFFECT_DONOR, EFFECT_RECIPIENT]}
    manifest['files'] = {}
    for p in sorted(REFERENCE_DIR.rglob('*')) + sorted(PACKAGE_BODY_DIR.rglob('*')):
        if p.is_file():
            manifest['files'][p.relative_to(UNIT_DIR).as_posix()] = {'size': p.stat().st_size, 'sha256': sha_file(p)}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"sound: {len(sound['banks'])} banks, sqb {sound['sqb_records_before']} -> {sound['sqb_records_after']}")
    print(f"voice: {sound['voice']['banks_with_all_tones']}/{sound['voice']['banks_total']} voice banks hold all four tones")
    print(f"effect: {effect['emitter']} -> {effect['output_bytes']} bytes, sha256 {effect['output_sha256'][:16]}")


def build_motion():
    for p in (GUNNER_MLIST_SRC, DONOR_MLIST_SRC):
        assert p.is_file(), f"missing input {p}"
    PACKAGE_BODY_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_MLIST.parent.mkdir(parents=True, exist_ok=True)

    data_g = GUNNER_MLIST_SRC.read_bytes()
    magic_g, path_g, entries_g = parse_mlist(data_g)
    _, _, entries_d = parse_mlist(DONOR_MLIST_SRC.read_bytes())
    donor_by_kind = {e["kind"]: e for e in entries_d}

    added = []
    clip_files = []
    for donor_kind, donor_clip, owned, owned_clip in STAGES:
        donor_entry = donor_by_kind[hash40(donor_kind)]
        added.append(create_entry(donor_entry, owned, owned_clip))
        src = DONOR_BODY_DIR / donor_clip
        dst = PACKAGE_BODY_DIR / owned_clip
        assert src.is_file(), f"missing donor clip {src}"
        shutil.copy2(src, dst)
        clip_files.append(dst)

    new_count = len(entries_g) + len(added)
    rebuilt = struct.pack("<QQQ", magic_g, path_g, new_count) + b"".join(e["raw"] for e in entries_g) + b"".join(added)
    REFERENCE_MLIST.write_bytes(rebuilt)

    # Verify the reference list parses back to vanilla + only our entries.
    magic_c, path_c, entries_c = parse_mlist(rebuilt)
    assert magic_c == magic_g and path_c == path_g
    assert len(entries_c) == len(entries_g) + len(added), "entry count"
    for a, b in zip(entries_g, entries_c[: len(entries_g)]):
        assert a["raw"] == b["raw"], f"vanilla entry {a['index']} changed"

    files = {}
    for p in sorted(PACKAGE_BODY_DIR.rglob("*")) + [REFERENCE_MLIST]:
        if p.is_file():
            rel = p.relative_to(UNIT_DIR).as_posix()
            files[rel] = {"size": p.stat().st_size, "sha256": sha256_file(p)}

    manifest = {
        "unit": "normal_jab__miifighter",
        "task": "MV-normal_jab__miifighter",
        "vanilla_inputs": {
            "gunner_motion_list_sha256": sha256_file(GUNNER_MLIST_SRC),
            "gunner_motion_list_entries": len(entries_g),
            "donor_motion_list_sha256": sha256_file(DONOR_MLIST_SRC),
        },
        "files": files,
        "added_motions": {
            owned: {
                "kind_hash": f"0x{hash40(owned):010x}",
                "game_script": "game_" + owned_name_parts(owned),
                "game_hash": f"0x{hash40('game_' + owned_name_parts(owned)):010x}",
                "clip": owned_clip,
                "clip_hash": f"0x{hash40(owned_clip):010x}",
            }
            for _, _, owned, owned_clip in STAGES
        },
        "not_packaged": ["motion_list.bin", "motion_list.motdiff", "config.json"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"reference list: {REFERENCE_MLIST.relative_to(WORKSPACE).as_posix()} entries={len(entries_c)} (+{len(added)})")
    for f in clip_files:
        print(f"clip: {f.relative_to(WORKSPACE).as_posix()} sha256={sha256_file(f)}")
    print(f"manifest: {MANIFEST_PATH.relative_to(WORKSPACE).as_posix()}")


def main():
    build_motion()
    main_sound_effect()


if __name__ == "__main__":
    main()
