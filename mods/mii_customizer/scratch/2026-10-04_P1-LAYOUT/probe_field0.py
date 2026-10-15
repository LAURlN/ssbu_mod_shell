"""Try a batch of 32-bit hash functions on SARC entry field0, against name and data."""
import struct
import zlib

EDIT = 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc'
SPEC = 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc'


def entries(path):
    d = open(path, 'rb').read()
    c = struct.unpack_from('<H', d, 0x1A)[0]
    base = 0x20 + c * 16 + 8
    out = []
    for i in range(c):
        f0, f1, st, en = struct.unpack_from('<4I', d, 0x20 + i * 16)
        no = (f1 & 0xFFFFFF) * 4
        e = d.find(b'\x00', base + no)
        out.append((f0, d[base + no:e], d[0x2000 + st:0x2000 + en]))
    return out


def crc_ref(data, poly, init, refin, refout, xorout):
    crc = init
    for b in data:
        if refin:
            crc ^= b
            for _ in range(8):
                crc = (crc >> 1) ^ (poly if crc & 1 else 0)
        else:
            crc ^= b << 24
            for _ in range(8):
                crc = ((crc << 1) ^ (poly if crc & 0x80000000 else 0)) & 0xFFFFFFFF
    if refin != refout:
        r = 0
        for i in range(32):
            if crc >> i & 1:
                r |= 1 << (31 - i)
        crc = r
    return crc ^ xorout


CRC_VARIANTS = {
    'crc32/zlib': (0x04C11DB7, 0xFFFFFFFF, True, True, 0xFFFFFFFF),
    'crc32/bzip2': (0x04C11DB7, 0xFFFFFFFF, False, False, 0xFFFFFFFF),
    'crc32/mpeg2': (0x04C11DB7, 0xFFFFFFFF, False, False, 0x00000000),
    'crc32/posix': (0x04C11DB7, 0x00000000, False, False, 0xFFFFFFFF),
    'crc32/jamcrc': (0x04C11DB7, 0xFFFFFFFF, True, True, 0x00000000),
    'crc32/xfer': (0x000000AF, 0x00000000, False, False, 0x00000000),
    'crc32c': (0x1EDC6F41, 0xFFFFFFFF, True, True, 0xFFFFFFFF),
    'crc32d': (0xA833982B, 0xFFFFFFFF, True, True, 0xFFFFFFFF),
    'crc32/koopman': (0x741B8CD7, 0x00000000, True, True, 0xFFFFFFFF),
    'crc32/autosar': (0xF4ACFB13, 0xFFFFFFFF, True, True, 0xFFFFFFFF),
    'crc32/cdrom': (0x8001801B, 0x00000000, True, True, 0x00000000),
}


def fnv1a32(b):
    h = 0x811C9DC5
    for x in b:
        h = ((h ^ x) * 0x01000193) & 0xFFFFFFFF
    return h


def fnv1_32(b):
    h = 0x811C9DC5
    for x in b:
        h = ((h * 0x01000193) & 0xFFFFFFFF) ^ x
    return h


def fnv1a64_low(b):
    h = 0xCBF29CE484222325
    for x in b:
        h = ((h ^ x) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h & 0xFFFFFFFF


def fnv1a64_high(b):
    h = 0xCBF29CE484222325
    for x in b:
        h = ((h ^ x) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h >> 32


def murmur3_32(data, seed=0):
    c1, c2 = 0xCC9E2D51, 0x1B873593
    h, ln = seed, len(data)
    for i in range(0, ln - ln % 4, 4):
        k = struct.unpack_from('<I', data, i)[0]
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    k = 0
    for i, x in enumerate(data[ln - ln % 4:]):
        k |= x << (8 * i)
    tail = data[ln - ln % 4:]
    if tail:
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
    h ^= ln
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def djb2(b):
    h = 5381
    for x in b:
        h = ((h * 33) + x) & 0xFFFFFFFF
    return h


def djb2x(b):
    h = 5381
    for x in b:
        h = ((h * 33) ^ x) & 0xFFFFFFFF
    return h


def sdbm(b):
    h = 0
    for x in b:
        h = (x + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    return h


def all_hashes(b):
    out = {}
    for k, v in CRC_VARIANTS.items():
        out[k] = crc_ref(b, *v)
    out['fnv1a32'] = fnv1a32(b)
    out['fnv1_32'] = fnv1_32(b)
    out['fnv1a64_low'] = fnv1a64_low(b)
    out['fnv1a64_high'] = fnv1a64_high(b)
    out['murmur3_32'] = murmur3_32(b)
    out['djb2'] = djb2(b)
    out['djb2x'] = djb2x(b)
    out['sdbm'] = sdbm(b)
    return out


def main():
    ents = entries(EDIT)
    score_name = {}
    score_data = {}
    for f0, name, data in ents:
        for src, blob, score in (('name', name, score_name), ('data', data, score_data)):
            for k, v in all_hashes(blob).items():
                if v == f0:
                    score.setdefault(k, 0)
                    score[k] += 1
    print('editable entries:', len(ents))
    print('name-source hits:', score_name)
    print('data-source hits:', score_data)


if __name__ == '__main__':
    main()