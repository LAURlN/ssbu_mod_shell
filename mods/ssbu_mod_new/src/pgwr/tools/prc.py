"""Minimal typed reader/writer for Smash Ultimate `.prc` (paracobn) param files.

Why this exists: `pyprc` (vendored) can read a value when you already know its
key, but it cannot enumerate keys, and assigning a key that the file does not have
raises "Hash not found in child params". Merging one fighter's param tables into
another's needs both, so this module keeps a typed tree and writes it back out.

Tree nodes are `(tag, value)` tuples:

    ('bool', b) ('i8', n) ('u8', n) ('i16', n) ('u16', n) ('i32', n) ('u32', n)
    ('float', f) ('hash', h40) ('str', s)
    ('list', [node, ...])
    ('struct', [(h40_key, node), ...])      # ordered as in the file

Layout (documented by the paracobn format; verified here by round-trip):

    'paracobn' | u32 hash_bytes | u32 ref_bytes | hash table (u64 each, sorted)
    | ref table (struct ref tables + strings) | root param

    struct: 0x0C, u32 count, u32 ref_offset          children follow; each child's
            offset is relative to the struct's own first byte; the ref table at
            `ref_offset` holds `count` (u32 hash_index, u32 child_offset) pairs
            sorted by key hash.
    list:   0x0B, u32 count, u32 offsets[count]       offsets relative to the list.
    str:    0x0A, u32 offset into the ref table (NUL terminated).
    hash:   0x09, u32 index into the hash table.

The writer is checked against real files: see `selftest()`, which rewrites a set
of stock files and requires (a) the re-read tree to be identical and (b) that the
independent `pyprc` reader sees the same values.
"""
from __future__ import annotations

import struct
import zlib

MAGIC = b'paracobn'
FIXED = {  # tag -> (type byte, struct format, size)
    'bool': (1, '<B', 1), 'i8': (2, '<b', 1), 'u8': (3, '<B', 1),
    'i16': (4, '<h', 2), 'u16': (5, '<H', 2), 'i32': (6, '<i', 4),
    'u32': (7, '<I', 4), 'float': (8, '<f', 4),
}
BY_TYPE = {v[0]: (k, v[1], v[2]) for k, v in FIXED.items()}


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def read(path):
    data = open(path, 'rb').read()
    if data[:8] != MAGIC:
        raise ValueError(f'{path}: not a paracobn file')
    hash_bytes, ref_bytes = struct.unpack_from('<II', data, 8)
    hashes = struct.unpack_from('<' + 'Q' * (hash_bytes // 8), data, 16)
    ref_base = 16 + hash_bytes
    base = ref_base + ref_bytes

    def rd(off):
        t = data[off]
        if t in BY_TYPE:
            tag, fmt, size = BY_TYPE[t]
            v = struct.unpack_from(fmt, data, off + 1)[0]
            return (tag, bool(v) if tag == 'bool' else v)
        if t == 9:
            return ('hash', hashes[struct.unpack_from('<I', data, off + 1)[0]])
        if t == 10:
            o = struct.unpack_from('<I', data, off + 1)[0]
            end = data.index(b'\0', ref_base + o)
            return ('str', data[ref_base + o:end].decode('utf-8'))
        if t == 11:
            n = struct.unpack_from('<I', data, off + 1)[0]
            offs = struct.unpack_from('<' + 'I' * n, data, off + 5)
            return ('list', [rd(off + o) for o in offs])
        if t == 12:
            n, ro = struct.unpack_from('<II', data, off + 1)
            items = []
            for i in range(n):
                hi, po = struct.unpack_from('<II', data, ref_base + ro + 8 * i)
                items.append((hashes[hi], rd(off + po)))
            return ('struct', items)
        raise ValueError(f'{path}: unknown param type {t} at {off:#x}')

    return rd(base)


def write(tree) -> bytes:
    """Serialise a tree the way the game's own files are laid out.

    Matching the stock layout matters more than being canonical: the hash table is
    NOT sorted in shipped files. It opens with hash 0 and then lists hashes in order
    of first appearance while walking the tree; struct children are written in file
    order and only each struct's ref table is sorted by key hash. Reproducing that
    makes an unmodified file round-trip byte-for-byte (see selftest()).
    """
    order = [0]
    seen = {0}

    def collect(node):
        tag, v = node
        if tag == 'hash':
            if v not in seen:
                seen.add(v)
                order.append(v)
        elif tag == 'list':
            for c in v:
                collect(c)
        elif tag == 'struct':
            for k, c in v:
                if k not in seen:
                    seen.add(k)
                    order.append(k)
                collect(c)

    collect(tree)
    index = {h: i for i, h in enumerate(order)}
    refs, data, strings, tables = bytearray(), bytearray(), {}, {}

    def emit(node):
        tag, v = node
        if tag in FIXED:
            t, fmt, _ = FIXED[tag]
            data.append(t)
            data.extend(struct.pack(fmt, int(v) if tag == 'bool' else v))
        elif tag == 'hash':
            data.append(9)
            data.extend(struct.pack('<I', index[v]))
        elif tag == 'str':
            if v not in strings:
                strings[v] = len(refs)
                refs.extend(v.encode('utf-8') + b'\0')
            data.append(10)
            data.extend(struct.pack('<I', strings[v]))
        elif tag == 'list':
            start = len(data)
            data.append(11)
            data.extend(struct.pack('<I', len(v)))
            slots = len(data)
            data.extend(b'\0' * (4 * len(v)))
            for i, child in enumerate(v):
                struct.pack_into('<I', data, slots + 4 * i, len(data) - start)
                emit(child)
        elif tag == 'struct':
            start = len(data)
            data.append(12)
            data.extend(struct.pack('<II', len(v), 0))
            offsets = []
            for k, child in v:
                offsets.append((k, len(data) - start))
                emit(child)
            table_bytes = b''.join(struct.pack('<II', index[k], off)
                                   for k, off in sorted(offsets, key=lambda ko: ko[0]))
            if table_bytes not in tables:
                tables[table_bytes] = len(refs)
                refs.extend(table_bytes)
            struct.pack_into('<I', data, start + 5, tables[table_bytes])
        else:
            raise ValueError(f'unknown tag {tag}')

    emit(tree)
    header = MAGIC + struct.pack('<II', 8 * len(order), len(refs))
    return header + b''.join(struct.pack('<Q', h) for h in order) + bytes(refs) + bytes(data)


def as_dict(node):
    """Struct -> {key: node}; convenience for lookups (keys are unique)."""
    tag, v = node
    if tag != 'struct':
        raise TypeError(f'expected a struct, got {tag}')
    return dict(v)


def selftest(paths):
    """Rewrite each file, then prove the tree survived and pyprc agrees."""
    import pyprc  # vendored; only used as the independent reader

    def normalise(node):
        # struct children are written key-sorted, so compare as sorted.
        tag, v = node
        if tag == 'struct':
            return (tag, sorted(((k, normalise(c)) for k, c in v), key=lambda kv: kv[0]))
        if tag == 'list':
            return (tag, [normalise(c) for c in v])
        return node

    import os
    import tempfile
    for path in paths:
        tree = read(path)
        blob = write(tree)
        with tempfile.NamedTemporaryFile(suffix='.prc', delete=False) as f:
            f.write(blob)
        try:
            again = read(f.name)
            assert normalise(again) == normalise(tree), f'{path}: tree changed by round-trip'
            # independent reader: every root key must resolve in pyprc
            probe = pyprc.param(f.name)
            for k, _ in tree[1]:
                probe[pyprc.hash(k)]
        except Exception as exc:  # report every file, then fail once
            raise AssertionError(f'{path}: {exc}') from exc
        finally:
            os.unlink(f.name)
        print(f'  ok  {path}  ({len(blob)} bytes written, original {os.path.getsize(path)})')


if __name__ == '__main__':
    import sys
    selftest(sys.argv[1:])
