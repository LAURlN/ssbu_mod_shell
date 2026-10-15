import sys, struct
sys.argv=['x','pyra_mythra_clone/reference/dumps/images/main.bin','dis','0','1']
src=open('scratch/nro_dis.py').read()
exec(src.split("def h40")[0])
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
PAGE=0x52bb000
md2=Cs(CS_ARCH_ARM64, CS_MODE_ARM)
hits=[]
# scan .text for adrp targeting PAGE, then look ahead 8 insns for +0x3b0
start,end=0x100,0x39C8000
CH=0x200000
pos=start
while pos<end:
    chunk=data[pos:min(pos+CH,end)]
    for ins in md2.disasm(chunk,pos):
        if ins.mnemonic=='adrp' and ins.op_str.startswith('#0x52bb'):
            hits.append(ins.address)
    pos+=CH-0x1000
print('adrp->0x52bb page sites:',len(hits))
found=[]
for a in hits:
    win=data[a:a+40]
    ins=list(md2.disasm(win,a))
    for i,x in enumerate(ins):
        if '#0x3b0' in x.op_str and i<8:
            found.append((a,x.mnemonic,x.op_str,ins[min(i+1,len(ins)-1)].mnemonic,ins[min(i+1,len(ins)-1)].op_str))
            break
print('sites touching +0x3b0 within 8 insns:',len(found))
for f in found[:40]:
    print(f'  {f[0]:#x}: {f[1]} {f[2]}  |  next: {f[3]} {f[4]}')
