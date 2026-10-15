"""Independent linked SIMD ABI check. Smoke: python -B .../verify_linked.py.

Checks the final cargo ELF and outlines used by its Vector3 return path.
This is offline ABI evidence, never a capture/release or hardware result.
"""
from audit import ROOT, sha
from audit_pgwr_svc_guard import functions
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
import json

def run():
    package=ROOT/'builds/pgwr/dk_cargo-0.1.0-test'
    manifest=json.loads((package/'MANIFEST.json').read_text())
    target=ROOT/'builds/.cache/dk_cargo/runtime-target/aarch64-skyline-switch/release'
    assert sha((target/'libpyra_gamewatch_reskin.nro').read_bytes())==manifest['nro_sha256']
    blob=(target/'libpyra_gamewatch_reskin.so').read_bytes();symbols=functions(blob)
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    address,code=symbols['pgwr_dkc_thrown_offset'];instructions=list(md.disasm(code,address))
    outlines=[]
    for ins in instructions:
        if ins.mnemonic!='bl':continue
        dest=int(ins.op_str.lstrip('#'),0)
        match=next(((name,row) for name,row in symbols.items() if row[0]==dest),None)
        if not match:continue
        name,(start,raw)=match
        decoded=[(x.mnemonic,x.op_str) for x in md.disasm(raw,start)]
        if decoded==[('ldr','s0, [x8]'),('add','x9, x8, #4'),('add','x8, x8, #8'),
                     ('ld1','{v0.s}[1], [x9]'),('ld1','{v0.s}[2], [x8]'),('ret','')]:
            outlines.append({'name':name,'address':hex(start),'instructions':decoded})
            # Supported offsets branch directly to the common epilogue after
            # loading v0, so logging/zero fallback cannot clobber that result.
            index=instructions.index(ins);branch=instructions[index+1]
            assert branch.mnemonic=='b'
            epilogue=int(branch.op_str.lstrip('#'),0)
            path=[x for x in instructions if epilogue<=x.address<epilogue+12]
            assert [x.mnemonic for x in path]==['ldr','add','ret']
    assert len(outlines)==1,'Expected one verified SIMD result outline'
    report={'tier':'B','verified_offline':True,'runtime_verified':False,
        'nro_sha256':manifest['nro_sha256'],'elf_sha256':sha(blob),'simd_result_outline':outlines,
        'supported_return':'s0 then v0.s[1] and v0.s[2], followed by epilogue without result mutation',
        'limitation':'Rust unspecified-layout warning remains; this exact compiled artifact was inspected. Console behavior unverified.'}
    folder=ROOT/'evidence/2026-10-03_pgwr_dk_cargo';folder.mkdir(exist_ok=True)
    (folder/'LINKED_ABI.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS linked cargo offset SIMD return and epilogue; console unverified')

if __name__=='__main__':run()
