import sys, struct, zlib, collections
sys.path.insert(0,'mod_files/pyra_gamewatch_reskin')
from build import hash40, EXPORT, load_labels
labels=load_labels()
def entries(path):
    d=open(path,'rb').read(); _,_,n=struct.unpack_from('<QQQ',d); off=24; out={}
    for _ in range(n):
        kind,gs,flags,blend,na,size=struct.unpack_from('<QQHBBI',d,off); off+=24
        anims=struct.unpack_from('<'+'Q'*na,d,off); off=((off+na*9+3)&~3)
        out[kind]=(gs,flags,blend,anims,size,d[off:off+size]); off+=size
    return out
P=entries(EXPORT/'fighter/eflame/motion/body/c06/motion_list.bin'); G=entries(EXPORT/'fighter/gamewatch/motion/body/c06/motion_list.bin')
L=lambda h: labels.get(h,hex(h))
diff=[(L(k),L(P[k][0]),L(G[k][0])) for k in P if k in G and P[k][0]!=G[k][0]]
print('common kinds:',sum(1 for k in P if k in G),' game_script name differs:',len(diff))
for d in diff: print('  kind',d[0],'| pyra script',d[1],'| gw script',d[2])
# flags / blend / cancel-frame differences on common kinds
fl=[(L(k),P[k][1],G[k][1],P[k][2],G[k][2]) for k in P if k in G and (P[k][1]!=G[k][1] or P[k][2]!=G[k][2])]
print('common kinds with different flags/blend:',len(fl)); print(fl[:12])
print()
print('%-28s %-12s %-12s %s'%('kind','pyra flags','gw flags','blend p/g   pyra_extra_len/gw_extra_len'))
for k in P:
    if k in G and (P[k][1]!=G[k][1] or P[k][2]!=G[k][2]):
        print('%-28s %-12s %-12s %d/%d   %d/%d'%(L(k),format(P[k][1],'012b'),format(G[k][1],'012b'),P[k][2],G[k][2],P[k][4],G[k][4]))
# extra bytes (cancel frame etc.) differences
ex=[(L(k),P[k][5][-4:].hex(),G[k][5][-4:].hex()) for k in P if k in G and P[k][5]!=G[k][5]]
print('\ncommon kinds whose trailing data (cancel frame etc.) differ:',len(ex))
print(ex[:40])
# anim file-name identity
same=sum(1 for k in P if k in G and P[k][3]==G[k][3]); print('\ncommon kinds with identical clip file names:',same,'of',sum(1 for k in P if k in G))
