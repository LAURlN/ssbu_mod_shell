"""Resolve cargo call/constant evidence and generic throw entry, offline only.

Run from the mod root: python -B src/pgwr/tools/dk_cargo/semantic.py
No runtime calls, hooks, registrations or shared builds. Assertions are byte
controls, not gameplay validation. Labels are annotations, not decompilation.
"""
import json
import re
import struct
import audit
from audit import ROOT, OUT, INPUT, WS, sha, h40, cfg
from nro_flatten import flatten, parse
import nro_util
from main_image import MainImage
from audit_mflip_capture_native import symbols


def run():
    source = (ROOT/'tools/constmap.py').read_text().split('d=NRO_PATH.read_bytes()')[0]
    ns = {'__file__': str(ROOT/'tools/constmap.py')}
    exec(source, ns)
    names = re.findall(r'^\s+([A-Z_0-9a-z]+): ', (OUT/'lua_const.rs').read_text(), re.M)
    reverse = {ns['xxh64'](n.encode()): n for n in names}
    raw = (INPUT/'prebuilt;/nro/release/lua2cpp_common.nro').read_bytes()
    def const(off):
        return reverse.get(struct.unpack_from('<Q',raw,0x6a5b70+off//4*8)[0])
    known = set()
    for p in (OUT/'donor_acmd').glob('*.txt'):
        known.update(re.findall(r'"([a-zA-Z0-9_]+)"',p.read_text()))
    # Hash vocabulary is explicit. Unknown hashes stay numeric.
    known.update(('throw_f shoulder_wait shoulder_walk_slow shoulder_walk_middle '
        'shoulder_walk_fast shoulder_turn shoulder_jump_squat shoulder_jump '
        'shoulder_fall shoulder_landing shoulder_damage throw_f_f throw_f_b '
        'throw_f_hi throw_f_lw thrown_f thrown_b thrown_hi thrown_lw '
        'shouldered_donkey thrown_f_donkey_lw capture catch capture_cut final '
        'shouldered_donkey_start shoulder shoulder_end throw item_lift common '
        'param_motion invalid capture_clatter_frame capture_clatter_frame_mul '
        'shouldered_donkey_frame_add shouldered_donkey_frame_mul '
        'capture_shouldered_donkey capture_shouldered_donkey_start').split())
    for p in OUT.glob('*_cargo.json'):
        known.update(re.findall(r'"([a-zA-Z0-9_]+)"\s*:',p.read_text()))
    hashes = {h40(n):n for n in known}
    # Existing pinned parameter-label vocabulary resolves complete keys, not
    # just top-level JSON keys. Re-hash every label rather than trust its ID.
    vocabulary=ROOT/'refs/diddy_monkey_flip/source_audit/ParamLabels.csv'
    for line in vocabulary.read_text().splitlines():
        if ',' in line:
            value,name=line.split(',',1)
            if re.fullmatch(r'0x[0-9a-fA-F]+',value) and h40(name)==int(value,0):
                hashes[int(value,0)]=name
    output = OUT/'semantic_asm'; output.mkdir(exist_ok=True)
    result = {'tier':'B','runtime_verified':False,'complete':False,'images':{}}
    for kind,graph_file in [('donkey','status_instruction_graph.json'),('common','victim_instruction_graph.json')]:
        path = INPUT/f'prebuilt;/nro/release/lua2cpp_{kind}.nro'
        data,meta = flatten(path.read_bytes())
        labels = {int(a,0):n for a,n in meta['labels'].items()}
        labels.update(nro_util.plt_map(data,meta['labels'],meta['text_end']))
        graph = json.loads((OUT/graph_file).read_text())
        if kind=='donkey':
            # Constructor and initialization callbacks are absent from the
            # cargo status registration roots. Follow local calls/pointers.
            seen={int(row['entry'],0) for row in graph}
            # 0x175018 is the relocated Lua fighter vtable written by 0x4d8.
            # This is distinct from the native fighter-class vtable in main.
            queue=[0x480]+[struct.unpack_from('<Q',data,0x175018+off)[0]
                          for off in range(0,0x78,8)]
            while queue:
                a=queue.pop(0)
                if a in seen or a<0x400 or a>=meta['text_end']: continue
                seen.add(a); row,text=cfg(data,a,labels)
                row['role']='constructor/callback candidate; inspect before use'
                graph.append(row)
                queue.extend(int(t,0) for t,n in row['calls'].items() if n=='local/unresolved')
                queue.extend(int(t,0) for t in row['address_candidates'])
        if kind=='common':
            for n,info,shn,a,size in parse(raw)[0]:
                if shn and re.search(r'(status_pre_Throw|status_Throw|Throw_Main|Throw_Init|Throw_Exec|Throw_Exit|sub_throw|status_CatchPull|status_CatchWait|catch_wait|CatchWait|ThrowUniq|CatchCont|sub_is_.*throw_status_kind)',n):
                    row,text = cfg(data,a,labels)
                    row.update(symbol=n,symbol_size=size)
                    graph.append(row)
        summaries=[]
        for row in graph:
            start=int(row['entry'],0)
            _,text=cfg(data,start,labels)
            tables=set(); values={}; annotations=[]; lines=[]
            for line in text.splitlines():
                code=line.split(': ',1)[1]; note=[]
                m=re.match(r'ldr\s+(x\d+), \[\1, #(0x[0-9a-f]+)\]',code)
                if m and int(m[2],0)==(0x6b8 if kind=='donkey' else 0x578): tables.add(m[1])
                m=re.match(r'ldr\s+w\d+, \[(x\d+), #(0x[0-9a-f]+)\]',code)
                if m and m[1] in tables:
                    n=const(int(m[2],0))
                    if n: note.append(n)
                m=re.match(r'(mov|movk)\s+([xw]\d+), #(0x[0-9a-f]+|\d+)(?:, lsl #(\d+))?$',code)
                if m:
                    op,r,v,shift=m.groups(); v=int(v,0); shift=int(shift or 0)
                    if op=='mov': values[r]=v
                    elif r in values: values[r]=(values[r]&~(0xffff<<shift))|(v<<shift)
                    n=hashes.get(values.get(r))
                    if n: note.append('Hash40 '+n)
                m=re.match(r'bl\s+#(0x[0-9a-f]+)',code)
                if m and int(m[1],0) in labels: note.append(labels[int(m[1],0)])
                if note: annotations.append({'at':line.split(':')[0],'labels':note})
                lines.append(line+(' ; '+' | '.join(note) if note else ''))
                # Table-register annotations must not survive a destination
                # overwrite or an ABI-volatile call clobber.
                dest=re.match(r'\w+\s+([xw]\d+),',code)
                if dest:
                    r=dest[1].replace('w','x')
                    is_table_load=re.match(r'ldr\s+(x\d+), \[\1, #(0x[0-9a-f]+)\]',code)
                    if not (is_table_load and int(is_table_load[2],0)==(0x6b8 if kind=='donkey' else 0x578)):
                        tables.discard(r)
                if code.startswith('bl '):
                    tables.difference_update('x'+str(i) for i in range(19))
            (output/f'{kind}_{start:x}.asm').write_text('\n'.join(lines)+'\n')
            summaries.append({**row,'annotations':annotations})
        result['images'][kind]={'input_sha256':sha(path.read_bytes()),'functions':summaries}
    main=MainImage(WS/'gamedata/ssbu-13.0.4/main.bin')
    allsymbols={a:n for n,a,size in symbols(main) if a}
    wanted={n:(a,size) for n,a,size in symbols(main) if a and any(x in n for x in
        ('donkey_thrown_offset','FighterSpecializer_Donkey','sv_module_access7capture'))}
    native={}
    for n,(a,size) in wanted.items():
        row,text=cfg(main.data,a,allsymbols)
        (output/f'main_{a:x}.asm').write_text(text)
        native[n]={'entry':hex(a),'symbol_size':size,'graph':row}
    result['native_exports']=native
    # Scan instruction encodings for exact ADRP/ADD references to the candidate
    # native class vtable; no installed disassembler/decompiler required.
    target=0x4fa8c80; refs=[]
    target_slots={target,0x4fa8c68,0x529bfd8}
    target_pages={x&~0xfff for x in target_slots}
    for a in range(0x100,0x39c8000-12,4):
        w=struct.unpack_from('<I',main.data,a)[0]
        if w&0x9f000000!=0x90000000: continue
        imm=((w>>5)&0x7ffff)<<2 | ((w>>29)&3)
        if imm&0x100000: imm-=0x200000
        page=(a&~0xfff)+(imm<<12)
        if page not in target_pages: continue
        reg=w&31
        for b in range(a+4,min(a+260,0x39c8000),4):
            add=struct.unpack_from('<I',main.data,b)[0]
            v=None
            if add&0xffc00000==0x91000000 and (add>>5)&31==reg:
                v=page+((add>>10)&0xfff)
            elif add&0xffc00000==0xf9400000 and (add>>5)&31==reg:
                v=page+(((add>>10)&0xfff)<<3)
            if v in target_slots:
                    refs.append(hex(a))
                    text='\n'.join(f'{i.address:#010x}: {i.mnemonic:8} {i.op_str}' for i in main.disasm(a-48,128))+'\n'
                    (output/f'vtable_xref_{a:x}.asm').write_text(text)
    result['native_vtable_exact_adrp_add_xrefs']=refs
    result['native_class_descriptor_relocations']={hex(a):hex(main.ptr(a))
        for a in (0x4fa8c60,0x4fa8c68,0x529bfd8)}
    result['hash_vocabulary']={hex(k):v for k,v in sorted(hashes.items())}
    (OUT/'semantic_annotations.json').write_text(json.dumps(result,indent=2)+'\n')
    # Distinguish cargo entry from the unrelated Final Smash event.
    assert h40('final')==0x5ecd55cc6
    print('PASS: explicit hash control final=0x5ecd55cc6; annotated',
          {k:len(v['functions']) for k,v in result['images'].items()},'functions;',len(native),'native exports')


if __name__=='__main__': run()
