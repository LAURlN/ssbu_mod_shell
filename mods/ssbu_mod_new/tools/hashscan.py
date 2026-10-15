import struct, zlib, sys
data=open('export/prebuilt/nro/release/lua2cpp_gamewatch.nro','rb').read()
words=struct.unpack_from('<%dI'%(len(data)//4),data)
def h40(s): b=s.encode(); return (len(b)<<32)|zlib.crc32(b)
# index movz/movk: (imm16, hw) -> positions
idx={}
for i,w in enumerate(words):
    if (w & 0x7f800000) in (0x52800000,0x72800000):  # movz/movk (sf any)
        hw=(w>>21)&3; imm=(w>>5)&0xffff
        idx.setdefault((imm,hw),[]).append(i)
def find(name):
    h=h40(name); parts=[(h&0xffff,0),((h>>16)&0xffff,1),((h>>32)&0xffff,2)]
    a=idx.get(parts[0],[]); b=set(idx.get(parts[1],[]))
    hits=[p for p in a if any(q in b for q in range(p-8,p+9))]
    raw=data.count(struct.pack('<Q',h))
    return len(hits), raw
for n in sys.argv[1:]: print(n, hex(h40(n)), find(n))
