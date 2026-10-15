from pathlib import Path
import sys
import struct
ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
sys.path.insert(0, str(WORKSPACE / 'mod_files/mythra_gamewatch_swap/tools/analysis_lib'))
sys.path.insert(0, str(WORKSPACE / 'references/mythra_gamewatch_feasibility'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from inspect_nro import parse_nro
path = ROOT / 'downloads/libsmashline_plugin.nro'
data = path.read_bytes()
symbols = [s for s in parse_nro(path) if s['address'] and s['type'] == 2]
symbols.sort(key=lambda s:s['address'])
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
mod = struct.unpack_from('<I', data, 4)[0]
dyn = mod + struct.unpack_from('<i', data, mod+4)[0]
tags = {}
for off in range(dyn,len(data),16):
    tag,value = struct.unpack_from('<QQ',data,off)
    if not tag: break
    tags[tag]=value
relocs={}
for off in range(tags[7],tags[7]+tags[8],24):
    dest,info,addend=struct.unpack_from('<QQq',data,off)
    if (info & 0xffffffff)==1027: relocs[dest]=addend
for loc in [0x497a8]:
    ptr=relocs.get(loc,0)
    length,line,col=struct.unpack_from('<QII',data,loc+8)
    print('PANIC LOCATION',data[ptr:ptr+length],line,col)
if len(sys.argv)>1:
    start=int(sys.argv[1],0); end=int(sys.argv[2],0)
    for i in md.disasm(data[start:end],start):
        print(f'{i.address:#x}: {i.mnemonic} {i.op_str}')
    sys.exit()
for start, end in [(0x33190,0x33250),(0x33880,0x33930)]:
    print('\nRANGE',hex(start),hex(end))
    for s in symbols:
        if s['address'] <= end and s['address']+s['size'] >= start:
            print('SYMBOL',s)
    for i in md.disasm(data[start:end], start):
        print(f'{i.address:#x}: {i.mnemonic} {i.op_str}')
for start in [0x497a8,0x4b140,0x4b000,0x4aae0]:
    print('DATA',hex(start),repr(data[start:start+200]))
print('NEAR SYMBOLS')
for s in symbols:
    if 0x33000 <= s['address'] <= 0x33a00:
        print(s)
print('CALLERS of abort vicinity')
for i in md.disasm(data[0x80:0x37000],0x80):
    if i.mnemonic in ('bl','b') and i.op_str in ('#0x33214','#0x33220','#0x33224','#0x338cc','#0x338d0'):
        print(f'{i.address:#x}: {i.mnemonic} {i.op_str}')
