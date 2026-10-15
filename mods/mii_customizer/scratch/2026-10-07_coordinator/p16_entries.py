# Coordinator review of P16: dump the three appended motion-list entries next to their donor
# entries and Gunner's own attack_s3_s, and check every hash against its name.
import struct, sys, zlib
from pathlib import Path
ws = Path(__file__).resolve().parents[4]
def h40(s): return (len(s) << 32) | (zlib.crc32(s.encode()) & 0xFFFFFFFF)
def parse(data):
    magic, path, count = struct.unpack_from('<QQQ', data, 0)
    off = 24; out = []
    for i in range(count):
        st = off
        kind, game, flags, blend, n, size = struct.unpack_from('<QQHBBI', data, off)
        anims = struct.unpack_from('<' + 'Q'*n, data, off+24)
        unk = data[off+24+8*n: off+24+9*n]
        tail = (st + 24 + n*9 + 3) & ~3
        out.append(dict(i=i, kind=kind, game=game, flags=flags, blend=blend, n=n, size=size, anims=anims, unk=unk, tail=data[tail:tail+size]))
        off = tail + size
    assert off == len(data), (off, len(data))
    return out
g = parse((ws/'gamedata/mii_customizer/P16-FTILT-MOVE/reference/motion_list_vanilla_plus_owned.bin').read_bytes())
b = parse((ws/'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin').read_bytes())
bk = {e['kind']: e for e in b}; gk = {e['kind']: e for e in g}
def show(tag, e):
    t = e['tail']
    hs = struct.unpack_from('<' + 'Q'*((len(t))//8), t, 0)
    print(tag, 'kind=%010x game=%010x flags=%04x blend=%d n=%d size=%d anims=%s unk=%s' % (e['kind'], e['game'], e['flags'], e['blend'], e['n'], e['size'], ['%010x' % a for a in e['anims']], e['unk'].hex()))
    print('    tail hashes', ['%010x' % h for h in hs], 'rest', t[len(hs)*8:].hex())
bad = 0
for suf in ('s', 'hi', 'lw'):
    d = bk[h40('attack_s3_' + suf)]; o = gk[h40('mc_attacks3_' + suf)]
    show('donor attack_s3_' + suf, d); show('owned mc_attacks3_' + suf, o)
    nm = 'mcattacks3' + suf
    exp = [h40('expression_' + nm), h40('sound_' + nm), h40('effect_' + nm)]
    got = list(struct.unpack_from('<QQQ', o['tail'], 0))
    ds = '' if suf == 's' else suf  # the donor's straight scripts carry no suffix
    dexp = [h40('expression_attacks3' + ds), h40('sound_attacks3' + ds), h40('effect_attacks3' + ds)]
    dgot = list(struct.unpack_from('<QQQ', d['tail'], 0))
    checks = [o['game'] == h40('game_' + nm), got == exp, dgot == dexp, d['game'] == h40('game_attacks3' + ds),
              o['anims'][0] == h40('c01' + nm + '.nuanmb'), d['anims'][0] == h40('c01attacks3' + suf + '.nuanmb'),
              o['tail'][24:] == d['tail'][24:], o['flags'] == d['flags'], o['blend'] == d['blend'], o['unk'] == d['unk'], o['n'] == 1]
    print('    checks', checks); bad += checks.count(False)
show('gunner attack_s3_s', gk[h40('attack_s3_s')])
print('gunner has attack_s3_hi/lw:', h40('attack_s3_hi') in gk, h40('attack_s3_lw') in gk)
print('kinds unique:', len(gk) == len(g))
print('FAIL' if bad else 'OK', bad); sys.exit(1 if bad else 0)
