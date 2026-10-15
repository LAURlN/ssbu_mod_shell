"""Read-only 13.0.4 native measurements; v0.1.0. No hook or runtime calls.

Run: python -B src/pgwr/tools/gaogaen_throw_b/native_audit.py
Needs project-local Capstone 5.0.7 in builds/.cache/gaogaen_throw_b/python.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'builds/.cache/gaogaen_throw_b/python'), str(ROOT / 'tools')]
from main_image import MainImage
from maindesc import descriptors
from audit_event_slots import vtables

OUT = ROOT / 'evidence/2026-10-02_pgwr_gaogaen_throw_b'
img = MainImage(ROOT.parents[1] / 'gamedata/ssbu-13.0.4/main.bin')
digest = hashlib.sha256(img.data).hexdigest()
assert digest == json.loads((ROOT / 'refs/gaogaen_throw_b/SOURCE.json').read_text())['native_main']['sha256']
# Kind comes from pinned skyline-smash 315e4e8 lua_const.rs, not the PRC row order.
init = [d['init'] for d in descriptors(img, 0x47)]
assert all(a == 0 or 0xab0000 < a < 0xac2000 for a in init)
vt = [v for v in vtables(img) if img.ptr(v + 0x158) == 0xab9140]
assert vt == [0x4fbd300]
assert img.ptr(vt[0] + 0x170) == 0xaba3e0
assert img.ptr(vt[0] + 0x1d0) == 0xabb020
assert [(i.mnemonic,i.op_str) for i in img.disasm(0xab9654,8)] == [('cmp','w0, #0x40'),('b.eq','#0xab91d4')]
assert [(i.mnemonic,i.op_str) for i in img.disasm(0xab91d4,12)] == [('mov','x0, x20'),('mov','w1, wzr'),('bl','#0xab86f0')]
# Status jump-table selects a Revenge row; retain the target instead of guessing
# field indexing from a decompiler. The donor throw enum is 0xA in pinned bindings.
table = 0x44cbb48
target = table + img.i32(table + (0x40 - 0x27) * 4)
assert 0xab9100 <= target < 0xab9970
ranges = [(0xab8f30,0xab9140),(0xab9140,0xab9970),(0xab9970,0xab9c50),
          (0xab9c50,0xaba3a0),(0xaba3e0,0xabb020),(0xabdfd0,0xabe550),
          (0xabb020,0xabdfd0)]
assembly = []
for start,end in ranges:
    p = OUT / 'native' / f'{hex(start)}.asm'
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in img.disasm(start,end-start))+'\n')
    assembly.append({'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                     'start':hex(start),'end_exclusive':hex(end),
                     'note':'inspection span, may include adjacent functions; no first-RET truncation'})
symbols = []
t = img.dynamic
for index in range(img.u32(t[4]+4)):
    name,_,_,section,value,size = struct.unpack_from('<IBBHQQ',img.data,t[6]+24*index)
    off = t[5]+name
    name = img.data[off:img.data.index(b'\0',off)].decode()
    if 'gaogaen' in name.lower():
        symbols.append({'name':name,'offset':hex(value),'size':size,'section':section})
report = {'tier':'B verified bytes; semantic interpretation explicitly bounded',
    'main_sha256':digest,'fighter_kind':'0x47','vtable':hex(vt[0]),'article_initializers':list(map(hex,init)),
    'throw_previous_status_branch':{'offset':'0xab9654','status':'0x40',
         'target':'0xab91d4','callee':'0xab86f0','callee_export':'FighterSpecializer_Gaogaen::revenge_off(Fighter&,bool)',
         'argument_w1':0,'meaning':'native Gaogaen has a THROW-related Revenge cleanup path outside ACMD'},
    'revenge_jump_table_throw_target':hex(target),
    'revenge_gate':{'offset':'0xab919c','work_id':'0x200000E8','name':'FIGHTER_GAOGAEN_INSTANCE_WORK_ID_FLAG_IS_REVENGE',
                    'pinned_bindings_commit':'315e4e8bebb460ebb9f02f30f07b0f13883ba3d6'},
    'intended_recipient':'unboosted throw only; no Revenge flag, timer, rate, or donor cleanup call ported',
    'followup_evidence':['ROUTES.json: common victim/attacker routing and offset provider',
                         'ENGINE.json: cursor expression handlers and SIMD provider ABI',
                         'RUNTIME_SOURCE.json: owned offset and runtime candidate'],
    'unresolved':['concrete CaptureModule custom attacker status assumptions',
                  'complete native collateral equivalence', 'runtime SIMD hook ABI'],
    'revenge_scope':'boosted donor scaling ABI not recreated; intended recipient is unboosted only',
    'symbols':symbols,'assembly':assembly,
    'nro_limit':'Gaogaen lua2cpp factories are undefined imports in main, value=0; main is not a replacement for that NRO'}
(OUT / 'NATIVE.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS native input hash, Gaogaen class, THROW branch, Revenge gate and cleanup call; remaining ABI unverified')
