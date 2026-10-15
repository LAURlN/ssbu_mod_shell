"""Offline DK cargo dependency measurements. Does not install or edit shared inputs."""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[4]
WS = ROOT.parents[1]
INPUT = WS / 'gamedata/ssbu-13.0.4/dk_cargo'
OUT = ROOT / 'refs/donkey_cargo'
sys.path[:0] = [str(ROOT / 'builds/.cache/dk_cargo/python'),
                str(ROOT / 'tools'), str(ROOT / 'tools/nro_decomp')]
import capstone
from nro_flatten import flatten, parse
import nro_util
import status_table
from main_image import MainImage
from maindesc import descriptors, static_fighter_data
from audit_event_slots import vtables, owner_kind
from dump_hero_mana_params import read_prc, load_labels

def sha(data):
    return hashlib.sha256(data).hexdigest()

def h40(s):
    return len(s) << 32 | zlib.crc32(s.encode())

def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')

def cfg(data, start, labels, limit=20000):
    """Follow branch blocks past first RET; direct calls reported, not executed.

    Indirect branches are explicitly unresolved. This is an instruction graph,
    not a recovered semantic state machine.
    """
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    todo, seen, calls, unresolved, lines, regs, pointers = [start], set(), {}, [], {}, {}, set()
    while todo:
        pc = todo.pop()
        while pc not in seen and 0 <= pc < len(data) - 4:
            if len(seen) >= limit:
                unresolved.append({'at': hex(pc), 'reason': 'instruction limit'})
                todo.clear()
                break
            seen.add(pc)
            ins = next(iter(md.disasm(data[pc:pc+4], pc)), None)
            if ins is None:
                unresolved.append({'at': hex(pc), 'reason': 'undecodable'})
                break
            m, ops = ins.mnemonic, ins.op_str
            lines[pc] = f'{pc:#010x}: {m:8} {ops}'
            if m in ('adrp','adr'):
                r,v = ops.split(', #')
                regs[r] = int(v,0)
            elif m=='add' and ops.count('#')==1:
                p = [x.strip() for x in ops.split(',')]
                if p[1] in regs and p[2].startswith('#'):
                    regs[p[0]] = regs[p[1]] + int(p[2].lstrip('#'),0)
                    if 0x400<=regs[p[0]]<0x120000:
                        pointers.add(regs[p[0]])
            if m == 'bl':
                target = int(ops.lstrip('#'), 0)
                calls[hex(target)] = labels.get(target, 'local/unresolved')
            elif m == 'blr':
                unresolved.append({'at': hex(pc), 'instruction': m + ' ' + ops})
            elif m in ('ret', 'br', 'udf'):
                if m == 'br':
                    unresolved.append({'at': hex(pc), 'instruction': m + ' ' + ops})
                break
            elif m == 'b':
                target=int(ops.lstrip('#'),0)
                if target in labels:
                    calls[hex(target)]=labels[target]
                else:
                    todo.append(target)
                break
            elif m.startswith('b.') or m in ('cbz', 'cbnz', 'tbz', 'tbnz'):
                todo.append(int(ops.split('#')[-1], 0))
            pc += 4
    return {'entry': hex(start), 'instructions': len(lines), 'calls': calls,
            'address_candidates': [hex(x) for x in sorted(pointers)],
            'unresolved_indirect': unresolved}, '\n'.join(lines[x] for x in sorted(lines)) + '\n'

def motion_entries(path):
    data = path.read_bytes()
    magic, directory, count = struct.unpack_from('<QQQ', data)
    assert magic == h40('motion')
    rows, off = [], 24
    for _ in range(count):
        start = off
        kind, game, flags, blend, n, size = struct.unpack_from('<QQHBBI', data, off)
        anims = struct.unpack_from('<' + 'Q'*n, data, off+24)
        off = ((off+24+n*9+3)&~3) + size
        rows.append(dict(kind=hex(kind), game=hex(game), flags=hex(flags), blend=blend,
                         animations=[hex(x) for x in anims], raw=data[start:off].hex(),
                         cancel=struct.unpack_from('<H', data, off-2)[0] if size%8==4 else None))
    assert off == len(data)
    return directory, rows

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(INPUT.rglob('*')):
        if path.is_file():
            records.append(dict(path=path.relative_to(WS).as_posix(), bytes=path.stat().st_size,
                                sha256=sha(path.read_bytes())))
    write('local_inputs.json', records)
    # Reuse the constant hash algorithm without executing legacy external path reads.
    source = (ROOT / 'tools/constmap.py').read_text().split('d=NRO_PATH.read_bytes()')[0]
    ns = {'__file__': str(ROOT / 'tools/constmap.py')}
    exec(source, ns)
    names = re.findall(r'^\s+([A-Z_0-9a-z]+): ', (OUT/'lua_const.rs').read_text(), re.M)
    reverse = {ns['xxh64'](n.encode()): n for n in names}
    common = (INPUT/'prebuilt;/nro/release/lua2cpp_common.nro').read_bytes()
    def const(off):
        return reverse.get(struct.unpack_from('<Q',common,0x6a5b70+off//4*8)[0])
    nro_util.const_name = const
    donor, meta = flatten((INPUT/'prebuilt;/nro/release/lua2cpp_donkey.nro').read_bytes())
    table = status_table.table(donor, meta)
    write('status_table.json', [dict(status=s, condition=c, function=hex(f)) for s,c,f in table])
    labels = {int(a,0):n for a,n in meta['labels'].items()}
    labels.update(nro_util.plt_map(donor,meta['labels'],meta['text_end']))
    roots = [(s,c,f) for s,c,f in table if 'SHOULDER' in s or 'THROW_F_' in s or s=='FIGHTER_STATUS_KIND_THROW']
    graph = []
    asm_dir = OUT/'status_asm'
    asm_dir.mkdir(exist_ok=True)
    queue = sorted({f for _,_,f in roots})
    visited = set()
    while queue:
        f = queue.pop(0)
        if f in visited or f in labels or f >= meta['text_end']:
            continue
        visited.add(f)
        row, text = cfg(donor, f, labels)
        (asm_dir/f'{f:x}.asm').write_text(text)
        row['registrations'] = [dict(status=s,condition=c) for s,c,fn in roots if fn==f]
        graph.append(row)
        for target,name in row['calls'].items():
            if name=='local/unresolved':
                queue.append(int(target,0))
        queue.extend(int(x,0) for x in row['address_candidates'])
    write('status_instruction_graph.json',graph)
    common_img, common_meta = flatten(common)
    common_labels = {int(a,0):n for a,n in common_meta['labels'].items()}
    common_labels.update(nro_util.plt_map(common_img,common_meta['labels'],common_meta['text_end']))
    common_symbols,_,_ = parse(common)
    victim_graph = []
    victim_dir = OUT/'victim_asm'
    victim_dir.mkdir(exist_ok=True)
    for name,info,shn,address,size in common_symbols:
        if shn and ('ShoulderedDonkey' in name or 'shouldered_donkey' in name):
            rr,tt = cfg(common_img,address,common_labels)
            rr['symbol'] = name
            rr['symbol_size'] = size
            (victim_dir/f'{address:x}.asm').write_text(tt)
            victim_graph.append(rr)
    write('victim_instruction_graph.json',victim_graph)
    main = MainImage(WS/'gamedata/ssbu-13.0.4/main.bin')
    assert sha(main.data)=='f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
    regions = {}
    for name,kind in [('donkey',1),('eflame',0x5a)]:
        assert main.i32(static_fighter_data(main,kind))==kind
        inits = [x['init'] for x in descriptors(main,kind) if x['init']]
        if inits:
            regions[name] = (min(inits),max(inits))
    native = {'main_sha256':sha(main.data), 'classes':{}, 'tier':'B'}
    for vt in vtables(main):
        owner = 'donkey' if vt==0x4fa8c80 else owner_kind(main,vt,regions)
        if owner:
            methods = {hex(o):hex(main.ptr(vt+o)) for o in range(0,0x400,8)}
            f = main.ptr(vt+0x170)
            row,text = cfg(main.data,f,{})
            (OUT/f'{owner}_receiver.asm').write_text(text)
            native['classes'][owner] = dict(vtable=hex(vt),methods=methods,receiver=row,
                entry_signature=main.data[f:f+32].hex())
            if owner=='donkey':
                native['classes'][owner]['identity_evidence'] = 'Candidate class: own methods adjacent to exported FighterSpecializer_Donkey::apply_lift_param at 0x995040; status gates 0x1ea..0x1f3 match pinned DK constants. No article locality control (DK has no descriptors).'
                native['classes'][owner]['identity_tier'] = 'D pending constructor kind dispatch proof'
                for fn in sorted({int(a,0) for a in methods.values() if 0x993000<=int(a,0)<0x996000}):
                    rr,tt = cfg(main.data,fn,{})
                    (OUT/f'native_{fn:x}.asm').write_text(tt)
    write('native_receivers.json',native)
    rr,tt = cfg(main.data,0x995040,{})
    (OUT/'apply_lift_param.asm').write_text(tt)
    labels_prc = load_labels(ROOT)
    def label(v):
        if isinstance(v,dict): return {labels_prc.get(k,hex(k)):label(x) for k,x in v.items()}
        if isinstance(v,list): return [label(x) for x in v]
        return v
    for name in ['vl','expression_vl']:
        _,v = read_prc(INPUT/f'fighter/donkey/param/{name}.prc')
        write(name+'_decoded.json',label(v))
    for name in ['fighter_param','fighter_param_thrown','fighter_param_motion','common']:
        _,v = read_prc(INPUT/f'fighter/common/param/{name}.prc')
        decoded = label(v)
        found = {}
        def select(v,path=''):
            if isinstance(v,dict):
                for k,x in v.items():
                    p = path+'/'+k
                    if any(s in k.lower() for s in ['donkey','shoulder','capture','throw','escape','lift']):
                        found[p] = x
                    else: select(x,p)
            elif isinstance(v,list):
                for i,x in enumerate(v): select(x,path+f'[{i}]')
        select(decoded)
        write(name+'_cargo.json',found)
    motion_names = set()
    for path in (OUT/'donor_acmd').glob('*.txt'):
        motion_names.add(re.sub(r'(?<!^)(?=[A-Z])','_',path.stem).lower())
    motion_names.update('throw_f_'+x for x in ['wait','walk_slow','walk_middle','walk_fast','turn','jump_squat','jump','fall','landing','f','b','hi','lw'])
    directory,entries = motion_entries(INPUT/'fighter/donkey/motion/body/c00/motion_list.bin')
    index = (ROOT/'dumps/decoded/arc_files.tsv').read_text().splitlines()
    clip_names = {h40(Path(p).name):Path(p).name for p in index if p.endswith('.nuanmb')}
    selected = []
    for row in entries:
        resolved = [clip_names.get(int(x,0),x) for x in row['animations']]
        if any('throwf' in x or 'thrown' in x for x in resolved) or int(row['kind'],0) in {h40(x) for x in motion_names}:
            row['motion_name'] = next((x for x in motion_names if h40(x)==int(row['kind'],0)),None)
            row['clip_names'] = resolved
            selected.append(row)
    write('donor_motion_entries.json',selected)
    custom = sorted({s for s,c,f in roots if s.startswith('FIGHTER_DONKEY_STATUS_KIND_')})
    write('allocation_request.json',dict(carrier='eflame',costumes=[6,7], count=len(custom),
          names=custom, production_ids=None, common_entry='FIGHTER_STATUS_KIND_THROW',
          victim_common_statuses=['SHOULDERED_DONKEY_START','SHOULDERED_DONKEY','SHOULDERED_DONKEY_THROWN'],
          caveat='Victim routing/native semantics unresolved. No numeric IDs allocated.'))
    assert len(custom)==15
    assert {s.removeprefix('FIGHTER_DONKEY_STATUS_KIND_') for s in custom}=={
        'SHOULDER_START','SHOULDER_WAIT','SHOULDER_WALK','SHOULDER_TURN',
        'SHOULDER_JUMP_SQUAT','SHOULDER_JUMP_SQUAT_B','SHOULDER_JUMP','SHOULDER_FALL',
        'SHOULDER_LANDING','SHOULDER_PASS','SHOULDER_END','THROW_F_F','THROW_F_B','THROW_F_HI','THROW_F_LW'}
    # Constant-load annotations are restricted to the known constant-table base registers.
    for path in asm_dir.glob('*.asm'):
        text = path.read_text()
        if not re.search(r'ldr\s+x23, \[x23, #0x6b8\]',text):
            continue
        def annotate(match):
            offset=int(match.group(1),0)
            return match.group(0)+' ; '+str(const(offset))
        text = re.sub(r'ldr\s+w1, \[x23, #(0x[0-9a-f]+)\]',annotate,text)
        path.write_text(text)
    print(f'{len(table)} registrations; {len(custom)} cargo custom states; {len(graph)} reachable direct-call functions; {len(selected)} motion entries')
    print(json.dumps({k:{'vtable':v['vtable'],'receiver':v['receiver']['entry']} for k,v in native['classes'].items()}))

if __name__ == '__main__':
    run()
