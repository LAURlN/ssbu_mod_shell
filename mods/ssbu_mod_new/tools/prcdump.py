import struct, sys
labels={}
for line in open('references/ParamLabels.csv',encoding='utf-8'):
    a,_,b=line.strip().partition(',')
    try: labels[int(a,16)]=b
    except: pass
def nm(h): return labels.get(h, hex(h))
def load(path):
    d=open(path,'rb').read(); assert d[:8]==b'paracobn'
    hs,rs=struct.unpack_from('<II',d,8)
    hashes=struct.unpack_from('<'+'Q'*(hs//8),d,16)
    refbase=16+hs; base=refbase+rs
    def rd(off):
        t=d[off]
        if t==1: return bool(d[off+1]),off+2
        if t==2: return struct.unpack_from('<b',d,off+1)[0],off+2
        if t==3: return d[off+1],off+2
        if t==4: return struct.unpack_from('<h',d,off+1)[0],off+3
        if t==5: return struct.unpack_from('<H',d,off+1)[0],off+3
        if t==6: return struct.unpack_from('<i',d,off+1)[0],off+5
        if t==7: return struct.unpack_from('<I',d,off+1)[0],off+5
        if t==8: return round(struct.unpack_from('<f',d,off+1)[0],5),off+5
        if t==9: return ('H',nm(hashes[struct.unpack_from('<I',d,off+1)[0]])),off+5
        if t==10:
            o=struct.unpack_from('<I',d,off+1)[0]; e=d.index(b'\0',refbase+o)
            return d[refbase+o:e].decode(),off+5
        if t==11:
            n=struct.unpack_from('<I',d,off+1)[0]; offs=struct.unpack_from('<'+'I'*n,d,off+5)
            return [rd(off+o)[0] for o in offs],off+5+4*n
        if t==12:
            n,ro=struct.unpack_from('<II',d,off+1); out={}
            for i in range(n):
                hi,po=struct.unpack_from('<II',d,refbase+ro+8*i)
                out[nm(hashes[hi])]=rd(off+po)[0]
            return out,off+9
        raise ValueError(t)
    return rd(base)[0]
def show(v,ind=0,lim=12):
    pad='  '*ind
    if isinstance(v,dict):
        for k,x in v.items():
            if isinstance(x,(dict,list)): print(pad+k+':'); show(x,ind+1,lim)
            else: print(pad+k+' = '+str(x))
    elif isinstance(v,list):
        for i,x in enumerate(v[:lim]):
            if isinstance(x,(dict,list)): print(pad+f'[{i}]:'); show(x,ind+1,lim)
            else: print(pad+f'[{i}] = {x}')
        if len(v)>lim: print(pad+f'... {len(v)} items')
    else: print(pad+str(v))
if __name__=='__main__':
    for f in sys.argv[1:]:
        print('=====',f); show(load(f))
