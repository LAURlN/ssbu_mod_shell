import os
import struct, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NRO_PATH = ROOT / 'dumps' / 'arc' / 'prebuilt' / 'nro' / 'release' / 'lua2cpp_common.nro'
M=(1<<64)-1
P1=0x9E3779B185EBCA87;P2=0xC2B2AE3D27D4EB4F;P3=0x165667B19E3779F9;P4=0x85EBCA77C2B2AE63;P5=0x27D4EB2F165667C5
rotl=lambda x,r:((x<<r)|(x>>(64-r)))&M
def rnd(acc,inp): acc=(acc+inp*P2)&M; acc=rotl(acc,31); return (acc*P1)&M
def merge(acc,v): acc^=rnd(0,v); return (acc*P1+P4)&M
def xxh64(b,seed=M):
    n=len(b);i=0
    if n>=32:
        v=[(seed+P1+P2)&M,(seed+P2)&M,seed&M,(seed-P1)&M]
        while i+32<=n:
            for j in range(4): v[j]=rnd(v[j],struct.unpack_from('<Q',b,i+8*j)[0])
            i+=32
        h=(rotl(v[0],1)+rotl(v[1],7)+rotl(v[2],12)+rotl(v[3],18))&M
        for x in v: h=merge(h,x)
    else: h=(seed+P5)&M
    h=(h+n)&M
    while i+8<=n:
        h^=rnd(0,struct.unpack_from('<Q',b,i)[0]); h=(rotl(h,27)*P1+P4)&M; i+=8
    if i+4<=n:
        h^=(struct.unpack_from('<I',b,i)[0]*P1)&M; h=(rotl(h,23)*P2+P3)&M; i+=4
    while i<n:
        h^=(b[i]*P5)&M; h=(rotl(h,11)*P1)&M; i+=1
    h^=h>>33; h=(h*P2)&M; h^=h>>29; h=(h*P3)&M; h^=h>>32
    return h
def lua_const_path():
    configured = os.environ.get('SKYLINE_SMASH_LUA_CONST')
    if configured:
        return Path(configured)
    checkout_root = Path.home() / '.cargo' / 'git' / 'checkouts'
    candidates = list(checkout_root.glob('skyline-smash-*/**/src/lua_const.rs'))
    if not candidates:
        raise SystemExit('Set SKYLINE_SMASH_LUA_CONST to the installed skyline-smash lua_const.rs')
    return max(candidates, key=lambda p: p.stat().st_mtime)

d=NRO_PATH.read_bytes()
names=re.findall(r'^\s+([A-Z_0-9a-z]+): ', lua_const_path().read_text(), re.M)
rev={xxh64(n.encode()):n for n in names}
def name(off): return rev.get(struct.unpack_from('<Q',d,0x6a5b70+off//4*8)[0])
if __name__=='__main__':
    for a in sys.argv[1:]: print(a, name(int(a,16)))
