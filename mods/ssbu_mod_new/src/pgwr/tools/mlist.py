"""Byte-faithful `motion_list.bin` reader/rewriter.

Promoted out of `scratch/` for the Ness back throw (`throw_b`) on Mythra c06/c07,
where the entire motion-list delta is one cancel-frame byte and therefore has to
be *proved* to be exactly one byte. `encode(parse(x)) == x` is the round-trip
property that turns "nothing else changed" into something checkable instead of
something asserted; `tools/audit_ness_throw_b.py` checks it on every run.

Format (handbook/04_motion_lists_animation.md; validated against
`src/pgwr/build.py:parse_mlist_entries` and `tools/inject_monkey_flip.py`):

    u64 magic = hash40("motion")
    u64 motion_path          # NOT the folder clips load from (handbook/04 trap 6)
    u64 count
    then `count` entries, each:
        u64 kind, u64 game_script, u16 flags, u8 blend, u8 n_anims, u32 size
        n_anims * u64 animation hash (name includes the extension), padded to 4
        `size` bytes of tail; when size % 8 == 4 the trailing u16 is the cancel
        frame

Entries are kept as raw byte slices rather than re-encoded field by field,
because only copying the donor's bytes can reproduce an entry exactly - the tail
differs per kind and is not fully decoded here. That is deliberate: this module
is a reader plus a byte-patcher, not a motion-list author.
"""
import struct
import tempfile
import zlib
from pathlib import Path


def hash40(name):
    """The game hash of a string. Motion names hash WITH the file extension."""
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def parse(path):
    """Read a motion list into entries carrying their raw bytes and offsets."""
    data = Path(path).read_bytes()
    return parse_bytes(data, str(path))


def parse_bytes(data, name='<memory>'):
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError(f'{name}: bad magic {magic:#x}, not a motion list')
    off = 24
    entries = []
    for _ in range(count):
        start = off
        kind, game_script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, off)
        if n_anims > 3 or size % 8 not in (0, 4):
            raise RuntimeError(f'{name}: malformed entry at offset {off}')
        off += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, off)
        off = (off + n_anims * 9 + 3) & ~3
        end = off + size
        if end > len(data):
            raise RuntimeError(f'{name}: entry truncated at offset {start}')
        cancel = struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None
        entries.append(dict(kind=kind, gs=game_script, flags=flags, blend=blend,
                            n=n_anims, size=size, anims=anims, cancel=cancel,
                            raw=data[start:end], start=start, end=end))
        off = end
    if off != len(data):
        raise RuntimeError(f'{name}: {len(data) - off} bytes of trailing data')
    return dict(path=name, data=data, magic=magic, motion_path=motion_path, entries=entries)


def encode(ml):
    """Re-encode. Must equal `ml['data']` for an unmodified list - that is the
    round-trip property callers rely on to prove they changed only what they meant."""
    out = bytearray(struct.pack('<QQQ', ml['magic'], ml['motion_path'], len(ml['entries'])))
    for entry in ml['entries']:
        out += entry['raw']
    return bytes(out)


def find(ml, kind_name):
    """The entry for a motion kind by name, e.g. `find(ml, 'throw_b')`."""
    wanted = hash40(kind_name)
    for entry in ml['entries']:
        if entry['kind'] == wanted:
            return entry
    raise KeyError(f'{ml.get("path")}: no motion kind {kind_name!r} ({wanted:#x})')


def diff_offsets(a, b):
    """Offsets at which two equal-length entries differ."""
    if len(a) != len(b):
        return None
    return [i for i in range(len(a)) if a[i] != b[i]]


def reread(data):
    """Re-parse bytes through `parse_bytes`, without touching the filesystem."""
    return parse_bytes(data)['entries']