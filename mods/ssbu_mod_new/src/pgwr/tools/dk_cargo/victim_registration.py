"""Recover exact vanilla common victim registrations, including GOT callbacks.

Usage: python -B src/pgwr/tools/dk_cargo/victim_registration.py
The old generic status_table helper omits LDR callback pointers. Decode those
from the relocated common NRO and reject guesses based on helper names.
"""
import re
import struct
from audit import ROOT, OUT, sha, write
from closure import image
import nro_util
import status_table

def run():
    path,raw,data,meta,labels,imports,slots=image('common')
    ns={'__file__':str(ROOT/'tools/constmap.py')}
    exec((ROOT/'tools/constmap.py').read_text().split('d=NRO_PATH.read_bytes()')[0],ns)
    names=re.findall(r'^\s+([A-Z_0-9a-z]+): ',(OUT/'lua_const.rs').read_text(),re.M)
    reverse={ns['xxh64'](n.encode()):n for n in names}
    def constant(offset):return reverse.get(struct.unpack_from('<Q',raw,0x6a5b70+offset//4*8)[0])
    sv=next(a for a,n in imports.items() if n==status_table.SV)
    callers=nro_util.bl_callers(data,meta['text_end'],sv)
    rows=[];registers={};values=[];pointer_source=None
    for ins in nro_util.disasm(data,callers[0]-0x80,callers[-1]-callers[0]+0x100):
        m,ops=ins.mnemonic,ins.op_str
        if m=='mov' and ops.startswith('w8, #'):registers['w8']=int(ops.split('#')[1],0)
        elif m=='ldr' and ops.startswith('w1,'):
            match=re.search(r'#(0x[0-9a-f]+|\d+)\]',ops)
            values.append(registers.get('w8',-1) if ops.endswith('x8]') else (int(match[1],0) if match else 0))
        elif m in ('adrp','adr'):
            r,v=ops.split(', #');registers[r]=int(v,0)
        elif m=='add' and ops.count('#')==1:
            p=[v.strip() for v in ops.split(',')]
            if p[1] in registers:registers[p[0]]=registers[p[1]]+int(p[2].lstrip('#'),0)
        elif m=='ldr' and ops.startswith('x3,'):
            match=re.fullmatch(r'x3, \[(x\d+), #(0x[0-9a-f]+|\d+)\]',ops)
            if match and match[1] in registers:
                pointer_source=registers[match[1]]+int(match[2],0)
                registers['x3']=struct.unpack_from('<Q',data,pointer_source)[0]
            else:
                pointer_source=None;registers.pop('x3',None)
        elif m=='bl' and int(ops.lstrip('#'),0)==sv:
            kind,condition=[constant(o) for o in values[-2:]]
            if kind and ('SHOULDERED_DONKEY' in kind or kind=='FIGHTER_STATUS_KIND_THROWN'):
                target=registers['x3'];assert labels.get(target),hex(target)
                rows.append({'status':kind,'condition':condition,'function':hex(target),'symbol':labels[target],
                             'registration_call':hex(ins.address),'pointer_slot':hex(pointer_source) if pointer_source else None})
    cargo=[r for r in rows if 'SHOULDERED_DONKEY' in r['status']]
    assert len(cargo)==18
    assert {r['condition'] for r in cargo}=={'LUA_SCRIPT_STATUS_FUNC_STATUS_PRE','LUA_SCRIPT_STATUS_FUNC_STATUS_MAIN',
       'LUA_SCRIPT_STATUS_FUNC_STATUS_END','LUA_SCRIPT_STATUS_FUNC_INIT_STATUS','LUA_SCRIPT_STATUS_FUNC_EXIT_STATUS','LUA_SCRIPT_STATUS_FUNC_CHECK_DAMAGE'}
    assert all('ShoulderedDonkey' in r['symbol'] for r in cargo)
    assert len({(r['status'],r['condition']) for r in cargo})==18
    for r in cargo:
        a=int(r['registration_call'],0)
        target=OUT/'semantic_asm'/f'victim_registration_{a:x}.asm'
        target.write_text('\n'.join(f'{i.address:#010x}: {i.mnemonic:8} {i.op_str}' for i in nro_util.disasm(data,a-64,68))+'\n')
        r['evidence']=target.relative_to(OUT).as_posix();r['evidence_sha256']=sha(target.read_bytes())
    write('victim_registration.json',{'tier':'B','input_sha256':sha(raw),'cargo':cargo,
          'ordinary_thrown_controls':[r for r in rows if r['status']=='FIGHTER_STATUS_KIND_THROWN'],
          'extra_exec_or_map_correction_callbacks':False,'runtime_verified':False})
    print('PASS: exact 18 common victim registrations/GOT callbacks; no guessed Exec/MapCorrection callbacks')

if __name__=='__main__':run()
