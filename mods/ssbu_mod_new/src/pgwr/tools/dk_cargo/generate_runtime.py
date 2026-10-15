"""Generate cargo registration/data/ACMD from the pinned ownership contract.

Usage: python -B src/pgwr/tools/dk_cargo/generate_runtime.py --test-base 0x400
Numbers are PRIVATE TEST allocations; production remains collectively allocated.
No shared registration file is edited. Assertions audit IDs and source coverage.
"""
import argparse
import json
import re
import struct
from audit import ROOT, OUT, INPUT, h40, sha, read_prc, write
from emit_callbacks import DEST, ROLES, OWN_CONST, label

def f32(v):return 'f32::from_bits(0x%08x)'%struct.unpack('<I',struct.pack('<f',v))[0]

def run(base):
    contract=json.loads((OUT/'ownership_contract.json').read_text())
    assert contract['state_graph_reviewed']
    for n,d in contract['pins'].items():assert sha((OUT/n).read_bytes())==d,n
    const={n:int(v,0) for n,v in re.findall(r'^\s+(\w+): (0x[0-9a-fA-F]+|\d+),',(OUT/'lua_const.rs').read_text(),re.M)}
    counts={n:v for n,v in const.items() if n.startswith('FIGHTER_') and n.endswith('_STATUS_KIND_NUM')}
    assert base>=max(counts.values()),(hex(base),max(counts,key=counts.get))
    shared=(ROOT/'src/pgwr/plugin/src/status/mod.rs').read_text()
    shared_ids={int(v,0) for v in re.findall(r'pub const STATUS_\w+: i32 = (0x[0-9a-fA-F]+);',shared)}
    assert not shared_ids.intersection(range(base,base+18))
    write('test_allocation.json',{'private_test':True,'base':hex(base),'roles':{n:hex(base+i) for n,i in OWN_CONST.items()},
          'production_ids':None,'max_native_status_count':max(counts.values()),
          'max_native_symbol':max(counts,key=counts.get),'shared_ids':sorted(shared_ids),
          'shared_table_sha256':sha(shared.encode()),'full_requirement':'15 attacker and 3 victim states per eligible table; 18 on eflame'})
    definitions=['// Generated; private test allocation, no production numbers.','pub const BASE: i32 = '+str(base)+';',
                 'pub const READY_FLAG: i32 = 0x7ffd0001;']
    for i in range(19):
        value=base+i if i<18 else 0x7ffd0001
        definitions.append(f'#[no_mangle] pub static pgwr_dkc_id_{i}: i32 = {value};')
    # Own all scalar common decision parameters; leave victim param_motion/body
    # type on the victim's own generic parameter interface.
    _,common=read_prc(INPUT/'fighter/common/param/common.prc')
    scalar={k:v for k,v in common.items() if isinstance(v,(int,float))}
    definitions.append('pub fn common_param(key: u64) -> Option<f32> { match key {')
    definitions.extend(f'{hex(k)} => Some({f32(v)}),' for k,v in sorted(scalar.items()))
    definitions.append('_ => None } }')
    matrix=json.loads((OUT/'victim_roster_motion_matrix.json').read_text())
    definitions.append('pub unsafe fn offset(kind:i32, direction:i32) -> Option<[f32;3]> { let rows = match kind {')
    offsets=matrix['owned_thrown_offsets']['values']
    for symbol,dirs in offsets.items():
        if symbol=='FIGHTER_KIND_NANA':continue
        names=[symbol]
        if symbol=='FIGHTER_KIND_POPO':names.append('FIGHTER_KIND_NANA')
        for name in names:
            definitions.append(f'k if k == *smash::lib::lua_const::{name} => [')
            for d in ['f','b','hi','lw']:definitions.append('['+', '.join(f32(v) for v in dirs[d])+'],')
            definitions.append('],')
    definitions.append('_ => return None }; if (0..4).contains(&direction) { Some(rows[direction as usize]) } else { None } }')
    motions=[r['motion_name'] for r in json.loads((OUT/'donor_motion_entries.json').read_text())
             if any(n.startswith('e01throwf') for n in r['clip_names'])]
    assert len(motions)==14
    victim_bases=['thrown_f','shouldered_donkey','thrown_f_donkey_f','thrown_f_donkey_b','thrown_f_donkey_hi','thrown_f_donkey_lw']
    definitions.append('pub fn own_hash(hash:u64) -> u64 { match hash {')
    for n in motions:definitions.append(f'{hex(h40(n))} => {hex(h40("pgwr_dk_cargo_"+n))},')
    for b in victim_bases:
        for suffix in ['', '_dx','_girl']:
            n=b+suffix
            definitions.append(f'{hex(h40(n))} => {hex(h40("pgwr_dk_cargo_victim_"+n))},')
    definitions.append('_ => hash } }')
    fighters=sorted({p.split('/')[1] for p in matrix['matrix']})
    definitions.append('pub const VICTIM_AGENTS:&[&str]=&['+', '.join('"'+n+'"' for n in fighters)+'];')
    (DEST/'data.rs').write_text('\n'.join(definitions)+'\n',encoding='utf-8')
    # Direct status pointers retain the native 16-byte C++ result ABI. No Rust
    # function invokes these with a guessed native return layout.
    rows=json.loads((OUT/'callback_closure.json').read_text())['roles']
    conditions={'INIT_STATUS':'Init','EXEC_STATUS':'Exec','EXIT_STATUS':'Exit',
       'PRE':'Pre','STATUS_PRE':'Pre','STATUS':'Main','STATUS_MAIN':'Main','STATUS_END':'End','END':'End','CHECK_DAMAGE':'CheckDamage',
       'EXEC_STOP':'ExecStop','EXEC_FIX_POS':'MapCorrection'}
    native_victims=json.loads((OUT/'victim_registration.json').read_text())['cargo']
    victim_rows=[(OWN_CONST[r['status']],conditions[r['condition'].removeprefix('LUA_SCRIPT_STATUS_FUNC_')],
                  int(r['function'],0)) for r in native_victims]
    assert len(victim_rows)==18
    register=[]
    for r in rows:
        role=OWN_CONST[r['status']]
        condition=conditions[r['condition'].removeprefix('LUA_SCRIPT_STATUS_FUNC_')]
        register.append((role,condition,label('donkey',int(r['function'],0))))
    register += [(r,c,label('common',a)) for r,c,a in victim_rows]
    shims=['// Generated C++ status ABI shims.', '.section .text.pgwr_dkc_shims,"ax",%progbits']
    wrapped={}
    for role,condition,target in register:
        if (role==0 and condition=='Init') or (role<15 and condition=='Exit'):
            name=target+'_lifetime'
            if target not in wrapped:
                wrapped[target]=name
                shims.extend(['.p2align 2',f'.global {name}',f'.hidden {name}',f'{name}:',
                              'stp x29,x30,[sp,#-32]!','stp x0,x8,[sp,#16]'])
                if condition=='Init':
                    shims.extend(['bl pgwr_dkc_reset_storage','ldp x0,x8,[sp,#16]',
                                  'ldp x29,x30,[sp],#32',f'b {target}'])
                else:
                    shims.extend([f'bl {target}','ldr x0,[sp,#16]','bl pgwr_dkc_exit_storage',
                                  'ldp x29,x30,[sp],#32','ret'])
    register=[(r,c,wrapped.get(n,n)) for r,c,n in register]
    (DEST/'lifetime.S').write_text('\n'.join(shims)+'\n',encoding='utf-8')
    functions={name:condition for role,condition,name in register}
    assert all(not (c=='CheckDamage' and any(x[2]==n and x[1]!='CheckDamage' for x in register)) for n,c in functions.items())
    src=['// Generated registrations; preserve shared direction dispatch.', 'extern "C" {']
    for name,condition in sorted(functions.items()):
        extra=', info: &L2CValue' if condition=='CheckDamage' else ''
        src.append(f'fn {name}(fighter: &mut L2CFighterCommon{extra}) -> L2CValue;')
    src.append('}')
    src.append('unsafe fn register_attacker(agent:&mut Agent) {')
    for role,c,name in register:
        if role<15:src.append(f'agent.status({c}, data::BASE+{role}, {name});')
    src.append('}')
    src.append('unsafe fn register_victim(agent:&mut Agent) {')
    for role,c,name in register:
        if role>=15:src.append(f'agent.status({c}, data::BASE+{role}, {name});')
    for stock,fn in [('SHOULDERED_DONKEY_START','bridge_start'),('SHOULDERED_DONKEY','bridge_carry'),('SHOULDERED_DONKEY_THROWN','bridge_thrown')]:
        src.append(f'agent.status(Pre, *FIGHTER_STATUS_KIND_{stock}, {fn});')
    src.append('}')
    (DEST/'registration.rs').write_text('\n'.join(src)+'\n',encoding='utf-8')
    # Public dump bodies are transformed mechanically; empty script families
    # receive owned empty registrations. Every transformation is recorded.
    acmd=['// Generated by generate_runtime.py from pinned public vanilla bodies.',
       'use smash::{app::{self, lua_bind::*, sv_animcmd},lib::lua_const::*,lua2cpp::L2CAgentBase,phx::{Hash40,Vector3f}};',
       'use smash_script::{*,macros}; use smash::app::sv_animcmd::{frame,wait}; use smashline::*;',
       'use super::{data,pgwr_dkc_on_flag,cutin};']
    attacker_scripts=[];victim_scripts=[];sources=[]
    for name,is_victim in [(n,False) for n in motions]+[(n,True) for n in victim_bases]:
        key=name.replace('_','')
        path=next((p for p in (OUT/'donor_acmd').glob('*.txt') if p.stem.lower()==key),None)
        body=path.read_text() if path else ''
        if path:sources.append({'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes())})
        bodies={}
        for match in re.finditer(r'unsafe extern "C" fn (\w+)\(agent: &mut L2CAgentBase\) \{',body):
            start=match.end();depth=1;end=start
            while depth:
                depth += (body[end]=='{')-(body[end]=='}');end+=1
            bodies[match[1]]=body[start:end-1]
        for family in ['game','effect','sound','expression']:
            prefix='pgwr_dk_cargo_victim_' if is_victim else 'pgwr_dk_cargo_'
            own=family+'_'+prefix+key
            text=bodies.get(family+'_'+key,'')
            text=text.replace('wait_loop_sync_mot();','sv_animcmd::wait_loop_sync_mot(agent.lua_state_agent);')
            text=text.replace('WorkModule::on_flag(agent.module_accessor, *FIGHTER_DONKEY_STATUS_SHOULDER_START_FLAG_SHOULDER_WAIT);',
                              'pgwr_dkc_on_flag(agent.module_accessor, data::READY_FLAG);')
            text=text.replace('lua_bind::FighterCutInManager::','FighterCutInManager::')
            text=text.replace('singletons::FighterCutInManager()','cutin()')
            assert 'FIGHTER_DONKEY_' not in text,(name,family)
            acmd.append(f'unsafe extern "C" fn {own}(agent:&mut L2CAgentBase) {{{text}\n}}')
            (victim_scripts if is_victim else attacker_scripts).append((family,own))
    acmd.append('pub fn register_attacker(agent:&mut Agent) {')
    for family,own in attacker_scripts:acmd.append(f'agent.{family}_acmd("{own}", {own}, Priority::High);')
    acmd.append('}')
    acmd.append('pub fn register_victim(agent:&mut Agent) {')
    for family,own in victim_scripts:acmd.append(f'agent.{family}_acmd("{own}", {own}, Priority::High);')
    acmd.append('}')
    (DEST/'acmd.rs').write_text('\n'.join(acmd)+'\n',encoding='utf-8')
    write('runtime_generation.json',{'tier':'B/C','production_ids':None,'private_test_base':hex(base),
       'native_status_callbacks':len(register),'victim_callbacks':victim_rows,'attacker_scripts':attacker_scripts,
       'victim_scripts':victim_scripts,'public_sources':sources,'scalar_common_params':len(scalar),
       'absence_policy':'Missing public families are empty owned scripts; pickup victim thrown_f retains the native status pose, no invented catch behavior.',
       'runtime_verified':False,'ready':False})
    print('PASS: private IDs audited; registration/data and',len(attacker_scripts)+len(victim_scripts),'owned script families generated')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--test-base',type=lambda x:int(x,0),required=True)
    run(parser.parse_args().test_base)
