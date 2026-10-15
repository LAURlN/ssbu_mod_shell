import sys, struct
sys.argv=['x','pyra_mythra_clone/reference/dumps/images/main.bin','dis','0','1']
src=open('scratch/nro_dis.py').read()
exec(src.split("def h40")[0])
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
md2=Cs(CS_ARCH_ARM64, CS_MODE_ARM)
TARGET=0x52bb000; KNOWN=0x52b6000
lo,hi=0x100,0x39C8000
tgt=[];knw=0
buf=data[lo:hi]
prev={}
for ins in md2.disasm(buf, lo):
    op=ins.op_str
    if ins.mnemonic=='adrp':
        if op=='#0x%x'%TARGET: tgt.append(ins.address)
        elif op=='#0x%x'%KNOWN: knw+=1
print('VALIDATION: refs to known page 0x52b6000 in .text =', knw, '(must be > 0)')
print('refs to 0x52bb000 in .text =', len(tgt))
if not tgt: sys.exit()
res=[]
for a in tgt:
    win=data[a:a+48]
    ins=list(md2.disasm(win,a))
    for i,x in enumerate(ins):
        if '#0x3b0' in x.op_str and i<8:
            nx=ins[i+1] if i+1<len(ins) else None
            res.append((a,x.mnemonic,x.op_str,nx.mnemonic if nx else '',nx.op_str if nx else ''))
            break
print('sites referencing 0x52bb3b0 within 8 insns:',len(res))
for r in res:
    print(f'  {r[0]:#x}: {r[1]} {r[2]}   -> {r[3]} {r[4]}')
