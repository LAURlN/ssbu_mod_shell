import zlib, struct, sys, os
def h(n): d=n.encode(); return struct.pack('<Q',(len(d)<<32)|zlib.crc32(d))
targets={n:h(n) for n in ['hand_hold_lr','head_diver','hand_hold_l','head_none','hand','rhand_hammer']}
roots=['export/fighter/gamewatch/model/body/c06','export/fighter/gamewatch/param','export/fighter/gamewatch/motion/body/c06','export/fighter/common/param','export/fighter/gamewatch/model/body/c00']
for r in roots:
    for dp,_,fs in os.walk(r):
        for f in fs:
            p=os.path.join(dp,f)
            if f.endswith('.nutexb') or os.path.getsize(p)>30_000_000: continue
            d=open(p,'rb').read()
            hit=[n for n,t in targets.items() if t in d[:]] + [n+'(str)' for n in targets if n.encode() in d]
            if hit: print(p,hit)
