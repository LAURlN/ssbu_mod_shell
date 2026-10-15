"""Evaluate the compiled cleanup comparison branch logic with semantic controls.

Smoke: python -B .../check_transition.py. Scalar ARM64 branch evaluation only;
does not simulate capture, native routing or hardware. No card access/writes.
"""
import json
from audit import sha
from revision import TARGET,EVIDENCE,PRIVATE,ROOT
from audit_pgwr_svc_guard import functions
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM

def run():
    elf=(TARGET/'aarch64-skyline-switch/release/libpyra_gamewatch_reskin.so').read_bytes()
    address,code=functions(elf)['pgwr_dkc_cleanup_status_eq']
    ins=list(Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(code,address));by_pc={x.address:x for x in ins}
    entry=next(x.address for x in ins if x.mnemonic=='cmp' and x.op_str=='w19, w0')
    def evaluate(left,right):
        regs={'w19':left,'w0':right};equal=False;pc=entry
        def value(s):return int(s[1:],0) if s.startswith('#') else regs[s]
        for _ in range(32):
            x=by_pc[pc];pc+=4;parts=x.op_str.split(', ')
            if x.mnemonic=='cmp':equal=value(parts[0])==value(parts[1])
            elif x.mnemonic=='ccmp':
                assert parts[3]=='eq' and parts[2]=='#0'
                equal=(value(parts[0])==value(parts[1])) if equal else False
            elif x.mnemonic in ['b','b.eq','b.ne']:
                if x.mnemonic=='b' or (x.mnemonic=='b.eq' and equal) or (x.mnemonic=='b.ne' and not equal):pc=int(x.op_str[1:],0)
            elif x.mnemonic=='mov':regs[parts[0]]=value(parts[1])
            elif x.mnemonic=='cset':assert parts[1]=='eq';regs[parts[0]]=int(equal)
            elif x.mnemonic=='ldp':return bool(regs['w0']) # reached native epilogue
            else:raise AssertionError((x.mnemonic,x.op_str))
        raise AssertionError('Comparison loop exceeded bound')
    count=0
    for left in range(0x420):
        for right in [0x410,0x411,0x40f,0xc6,0xc7,0x44,0x3e,0x401]:
            expected=left==right or (left,right) in [(0xc6,0x410),(0xc7,0x411)]
            assert evaluate(left,right)==expected,(left,right)
            count+=1
    result={'tier':'B','runtime_verified':False,'elf_sha256':sha(elf),'cases':count,
       'controls':['native queued carry -> owned carry retains capture','native queued thrown -> owned thrown retains capture',
          'same-state comparisons unchanged','unrelated next states remain false and retain donor cleanup'],
       'scope':'Evaluates exact compiled cmp/ccmp/cset/branch block after native integer extraction; not capture simulation.'}
    (EVIDENCE/'TRANSITION_CHECK.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS',count,'compiled comparison cases; actual capture/release unverified')

if __name__=='__main__':run()
