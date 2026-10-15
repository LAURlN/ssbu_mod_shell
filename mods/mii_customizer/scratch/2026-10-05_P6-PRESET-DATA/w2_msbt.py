import struct, sys, re, collections
def read_msbt(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'MsgStdBn' and d[8:10] == b'\xff\xfe' and d[12] == 1
    o = 32; labels = {}; strings = []
    while o + 16 <= len(d):
        magic = d[o:o+4]; size = struct.unpack_from('<I', d, o+4)[0]; body = o + 16
        if magic == b'LBL1':
            gc = struct.unpack_from('<I', d, body)[0]
            for g in range(gc):
                cnt, off = struct.unpack_from('<II', d, body + 4 + 8*g)
                p = body + off
                for _ in range(cnt):
                    nl = d[p]; name = d[p+1:p+1+nl].decode('ascii'); idx = struct.unpack_from('<I', d, p+1+nl)[0]
                    labels[name] = idx; p += 5 + nl
        elif magic == b'TXT2':
            n = struct.unpack_from('<I', d, body)[0]
            offs = list(struct.unpack_from('<%dI' % n, d, body+4)) + [size]
            strings = [d[body+offs[i]:body+offs[i+1]] for i in range(n)]
        o = (body + size + 15) & ~15
    return {k: strings[i].decode('utf-16-le').rstrip('\0') for k, i in labels.items()}
m = read_msbt(sys.argv[1])
print('labels', len(m))
pref = collections.Counter(re.sub(r'[^_]+$', '', k) for k in m)
for k, v in pref.most_common(40): print(v, k)
for k in sorted(m):
    if k.endswith('_mario') or k.endswith('_miigunner') or k.endswith('_koopag') or k.endswith('_pzenigame') or k.endswith('_miienemyg') or k.endswith('_popo') or k.endswith('_nana') or k.endswith('_eflame')or k.endswith('_ptrainer') or k.endswith('_ice_climber'):
        print(k, ascii(m[k]))
