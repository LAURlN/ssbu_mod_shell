"""Read Snake's attack_hi3 motion entry from the extracted donor motion list (read-only, scratch)."""
import struct, sys, zlib, json
from pathlib import Path

def h40(s): return len(s) << 32 | zlib.crc32(s.encode())

def parse_mlist(data):
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset, entries = 24, []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        raw = data[start:end]
        offset = end
        entries.append(dict(index=i, kind=kind, game=game, flags=flags, blend=blend, n_anims=n_anims,
                            anims=anims, size=size, raw=raw, tail_offset=tail - start))
    assert offset == len(data), (offset, len(data))
    return magic, motion_path, entries

if __name__ == '__main__':
    src = Path(sys.argv[1])
    data = src.read_bytes()
    magic, mpath, entries = parse_mlist(data)
    e = [x for x in entries if x['kind'] == h40('attack_hi3')]
    print('entries', len(entries), 'attack_hi3 matches', len(e))
    x = e[0]
    t = x['tail_offset']
    raw = x['raw']
    print('index', x['index'], 'kind', hex(x['kind']), 'game', hex(x['game']), 'flags', hex(x['flags']),
          'blend', x['blend'], 'n_anims', x['n_anims'], 'anims', [hex(a) for a in x['anims']], 'size', x['size'],
          'raw_len', len(raw), 'tail_offset', t)
    print('tail words', [hex(v) for v in struct.unpack_from('<QQQ', raw, t)])
    print('u16 at tail+24/+26', struct.unpack_from('<HH', raw, t + 24))
    print('raw tail bytes', raw[t:].hex())
    print('names: game', hex(h40('game_attackhi3')), 'effect', hex(h40('effect_attackhi3')), 'sound', hex(h40('sound_attackhi3')), 'expression', hex(h40('expression_attackhi3')), 'clip', hex(h40('c02attackhi3.nuanmb')))
