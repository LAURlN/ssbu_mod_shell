import sys, struct
sys.argv=['x','pyra_mythra_clone/reference/dumps/images/main.bin','dis','0','1']
src=open('scratch/nro_dis.py').read()
exec(src.split("def h40")[0])
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
md2=Cs(CS_ARCH_ARM64, CS_MODE_ARM)
lo,hi=0x100,0x39C8000
def adrp_target(w, pc):
    if (w & 0x9F000000) != 0x90000000: return None
    immlo=(w>>29)&3; immhi=(w>>5)&0x7FFFF
    imm=((immhi<<2)|immlo)<<12
    if imm & (1<<32): imm -= (1<<33)
    return ((pc & ~0xFFF) + imm) & 0xFFFFFFFF
TARGET=0x52bb000
tgt=[]
for pc in range(lo,hi,4):
    if adrp_target(struct.unpack_from('<I',data,pc)[0],pc)==TARGET: tgt.append(pc)
print('adrp->0x52bb000 sites:',len(tgt))
W=0x400
writers_mgr=[]; writers_690=[]
for a in tgt:
    ins=list(md2.disasm(data[a:a+W],a))
    # is the adrp's dest register used for a str with 0x3b0 ?
    dest=ins[0].op_str.split(',')[0].strip()
    for i,x in enumerate(ins[1:],1):
        if x.mnemonic.startswith('str') and '#0x3b0' in x.op_str and x.op_str.split(',')[0].strip()==dest:
            writers_mgr.append((a,x.address,x.op_str))
        if x.mnemonic.startswith('str') and '#0x690' in x.op_str:
            writers_690.append((a,x.address,x.op_str))
print('=== WRITES to manager ptr 0x52bb3b0 ===')
for w in writers_mgr: print(f'  build {w[0]:#x}  store {w[1]:#x}: {w[2]}')
print('=== WRITES to a +0x690 field near a 0x52bb000 adrp ===')
for w in writers_690[:25]: print(f'  build {w[0]:#x}  store {w[1]:#x}: {w[2]}')
print('  (count %d)'%len(writers_690))
