import sys, struct
sys.argv=['x','pyra_mythra_clone/reference/dumps/images/main.bin','dis','0','1']
src=open('scratch/nro_dis.py').read()
exec(src.split("def h40")[0])
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
md2=Cs(CS_ARCH_ARM64, CS_MODE_ARM); md2.skipdata=True
# VALIDATE: 0x52b6000 is definitely referenced at 0xa805dc
win=data[0xa805d0:0xa805f0]
print('validate on known code:', [ (hex(i.address),i.mnemonic,i.op_str) for i in md2.disasm(win,0xa805d0) ])
def scan(page, lo, hi):
    out=[]
    for a in range(lo, hi, 4):
        try:
            i=next(md2.disasm(data[a:a+4], a))
        except StopIteration:
            continue
        if i.mnemonic=='adrp' and i.op_str=='#0x%x'%page:
            out.append(a)
    return out
v=scan(0x52b6000, 0xa80200, 0xa81000)
print('known page 0x52b6000 refs in 0xa80200-0xa81000:', len(v), [hex(a) for a in v])
t=scan(0x52bb000, 0xa80200, 0xa81000)
print('page 0x52bb000 refs in same range:', len(t), [hex(a) for a in t])
