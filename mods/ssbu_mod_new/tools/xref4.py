import sys, struct
sys.argv=['x','pyra_mythra_clone/reference/dumps/images/main.bin','dis','0','1']
src=open('scratch/nro_dis.py').read()
exec(src.split("def h40")[0])
lo,hi=0x100,0x39C8000
def adrp_target(w, pc):
    if (w & 0x9F000000) != 0x90000000: return None
    immlo=(w>>29)&3; immhi=(w>>5)&0x7FFFF
    imm=((immhi<<2)|immlo)<<12
    if imm & (1<<32): imm -= (1<<33)
    return ((pc & ~0xFFF) + imm) & 0xFFFFFFFF
TARGET=0x52bb000; KNOWN=0x52b6000
tgt=[];knw=0
for pc in range(lo,hi,4):
    w=struct.unpack_from('<I',data,pc)[0]
    t=adrp_target(w,pc)
    if t==TARGET: tgt.append(pc)
    elif t==KNOWN: knw+=1
print('VALIDATION refs to 0x52b6000:',knw)
print('refs (adrp) to page 0x52bb000:',len(tgt))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
md2=Cs(CS_ARCH_ARM64, CS_MODE_ARM)
res=[]
for a in tgt:
    ins=list(md2.disasm(data[a:a+48],a))
    for i,x in enumerate(ins):
        if '#0x3b0' in x.op_str and i<8:
            nx=ins[i+1] if i+1<len(ins) else None
            res.append((a,x.mnemonic,x.op_str,nx.mnemonic if nx else '',nx.op_str if nx else ''))
            break
print('=== sites that build 0x52bb3b0 within 8 insns ===')
for r in res: print(f'  {r[0]:#x}: {r[1]} {r[2]}  ->  {r[3]} {r[4]}')
