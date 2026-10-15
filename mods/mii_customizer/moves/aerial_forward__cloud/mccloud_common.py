"""Shared helpers for the two Cloud units (MV-aerial_forward__cloud, MV-special_up__cloud).

Pure Python, no game data inside. Imported by both units' build_assets.py and check.py.
Workspace-relative paths only.
"""
from __future__ import annotations

import hashlib
import struct
import zlib
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[4]
MOD = WORKSPACE / 'mods/mii_customizer'
G = WORKSPACE / 'gamedata/mii_customizer'
# Both units read Cloud's files from one place: the forward-air unit's donor/ folder.
SHARED = G / 'moves/aerial_forward__cloud'
DONOR = SHARED / 'donor'
RECIPIENT = SHARED / 'recipient'
ARC = WORKSPACE / 'gamedata/ssbu-13.0.4/data.arc'
LABELS_CSV = WORKSPACE / 'mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv'  # read-only reference


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path) -> str:
    return Path(path).resolve().relative_to(WORKSPACE).as_posix()


# ---------------------------------------------------------------------------
# param (.prc) reader: enough to read vl.prc values by name
# ---------------------------------------------------------------------------

def _labels() -> dict:
    out = {}
    with open(LABELS_CSV, encoding='utf-8') as f:
        for line in f:
            a, _, b = line.strip().partition(',')
            try:
                out[int(a, 16)] = b
            except ValueError:
                pass
    return out


def load_prc(path) -> dict:
    labels = _labels()
    d = Path(path).read_bytes()
    if d[:8] != b'paracobn':
        raise RuntimeError(f'{path}: not a param file')
    hs, rs = struct.unpack_from('<II', d, 8)
    hashes = struct.unpack_from('<' + 'Q' * (hs // 8), d, 16)
    refbase = 16 + hs
    base = refbase + rs

    def nm(h):
        return labels.get(h, hex(h))

    def rd(off):
        t = d[off]
        if t == 1:
            return bool(d[off + 1])
        if t == 2:
            return struct.unpack_from('<b', d, off + 1)[0]
        if t == 3:
            return d[off + 1]
        if t == 4:
            return struct.unpack_from('<h', d, off + 1)[0]
        if t == 5:
            return struct.unpack_from('<H', d, off + 1)[0]
        if t == 6:
            return struct.unpack_from('<i', d, off + 1)[0]
        if t == 7:
            return struct.unpack_from('<I', d, off + 1)[0]
        if t == 8:
            return struct.unpack_from('<f', d, off + 1)[0]
        if t == 9:
            return ('hash', nm(hashes[struct.unpack_from('<I', d, off + 1)[0]]))
        if t == 10:
            o = struct.unpack_from('<I', d, off + 1)[0]
            e = d.index(b'\0', refbase + o)
            return d[refbase + o:e].decode()
        if t == 11:
            n = struct.unpack_from('<I', d, off + 1)[0]
            offs = struct.unpack_from('<' + 'I' * n, d, off + 5)
            return [rd(off + o) for o in offs]
        if t == 12:
            n, ro = struct.unpack_from('<II', d, off + 1)
            out = {}
            for i in range(n):
                hi, po = struct.unpack_from('<II', d, refbase + ro + 8 * i)
                out[nm(hashes[hi])] = rd(off + po)
            return out
        raise ValueError(f'param type {t}')

    return rd(base)


# ---------------------------------------------------------------------------
# motion_list.bin (layout as tools/move-package/build_p16_assets.py)
# ---------------------------------------------------------------------------

def parse_mlist(data: bytes):
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset = 24
    entries = []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset + 24)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        entries.append({'index': i, 'kind': kind, 'game': game, 'flags': flags, 'blend': blend,
                        'n_anims': n_anims, 'anims': anims, 'size': size, 'raw': data[start:end],
                        'tail_offset': tail - start})
        offset = end
    if offset != len(data):
        raise RuntimeError(f'motion list: {len(data) - offset} trailing bytes after {count} entries')
    return magic, motion_path, entries


def entry_cancel(e) -> int:
    return struct.unpack_from('<H', e['raw'], e['tail_offset'] + 26)[0] if e['size'] >= 28 else -1


def owned_entry(donor: dict, kind: str, clip: str, suffix: str) -> bytes:
    """Donor entry copied whole; kind, the four script names and the clip name replaced by owned names."""
    if donor['n_anims'] != 1:
        raise RuntimeError('donor entry does not have exactly one animation')
    raw = bytearray(donor['raw'])
    struct.pack_into('<QQ', raw, 0, hash40(kind), hash40(f'game_{suffix}'))
    struct.pack_into('<Q', raw, 24, hash40(clip))
    t = donor['tail_offset']
    if donor['size'] >= 24:
        struct.pack_into('<QQQ', raw, t, hash40(f'expression_{suffix}'), hash40(f'sound_{suffix}'),
                         hash40(f'effect_{suffix}'))
    return bytes(raw)


def build_reference_list(vanilla: bytes, new_entries: list) -> bytes:
    magic, path, entries = parse_mlist(vanilla)
    have = {e['kind'] for e in entries}
    for raw in new_entries:
        if struct.unpack_from('<Q', raw, 0)[0] in have:
            raise RuntimeError('vanilla list already has an owned kind')
    return struct.pack('<QQQ', magic, path, len(entries) + len(new_entries)) + b''.join(
        e['raw'] for e in entries) + b''.join(new_entries)
