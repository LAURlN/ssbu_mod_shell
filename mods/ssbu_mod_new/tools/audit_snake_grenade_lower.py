"""Audit Snake lower-body translations against pinned 13.0.4 inputs (v1.0.0).

--pin promotes byte-input-matched Ghidra evidence; --check verifies its hashes.
Registration hashes are recovered independently from native instruction operands.
Smoke: run --pin once, then --check. This is offline evidence, not runtime proof.
"""
from pathlib import Path
import argparse,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/nro_decomp')]
import nro_flatten,nro_util
import gen_snake_neutral_b as gen
import build_snake_neutral_b_assets as assets

def sha(data): return hashlib.sha256(data).hexdigest()
def registration_map(image,meta):
    plt=nro_util.plt_map(image,meta['labels'],meta['text_end'])
    stub=next(a for a,n in plt.items() if n=='_ZN3lib8L2CAgent20sv_set_function_hashEPvN3phx6Hash40E')
    result={}
    for call in nro_util.bl_callers(image,meta['text_end'],stub):
        regs={}
        for ins in nro_util.disasm(image,call-64,64):
            match=re.fullmatch(r'([wx]\d+), #(0x[0-9a-f]+|-?\d+)(?:, lsl #(\d+))?',ins.op_str)
            if ins.mnemonic in ('mov','movz','adrp','adr') and match:
                regs[match[1].replace('w','x')]=int(match[2],0)
            elif ins.mnemonic=='movk' and match:
                key=match[1].replace('w','x');shift=int(match[3] or 0)
                regs[key]=(regs.get(key,0)&~(65535<<shift))|(int(match[2],0)<<shift)
            elif ins.mnemonic=='add':
                m=re.fullmatch(r'(x\d+), (x\d+), #(0x[0-9a-f]+|\d+)',ins.op_str)
                if m and m[2] in regs: regs[m[1]]=regs[m[2]]+int(m[3],0)
        if 'x1' in regs and 'x2' in regs: result[regs['x2']]=regs['x1']
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pin',action='store_true');parser.add_argument('--check',action='store_true');args=parser.parse_args()
    path=assets.ARC/'prebuilt/nro/release/lua2cpp_snake.nro';data=path.read_bytes();image,meta=nro_flatten.flatten(data)
    # flatten's metadata has the labels/PLT bounds used by the independent audit.
    regs=registration_map(image,meta);rows=[]
    for stem,kind in gen.LOWER_SOURCES:
        text=(gen.DONOR/(stem+'.txt')).read_text()
        for name in gen.split_functions(text):
            pointer=regs[assets.base.hash40(name)]
            rows.append({'script':name,'motion':kind,'wrapper':hex(pointer),'wrapper_32_bytes_sha256':sha(image[pointer:pointer+32])})
    assert len(rows)==30
    dest=ROOT/'refs/snake_grenade/common_owned';record_path=ROOT/'refs/snake_grenade/lower_translation_audit.json'
    if args.pin:
        dest.mkdir(exist_ok=True)
        scratch=ROOT/'scratch/2026-09-30_codex_snake'
        assert (ROOT/'scratch/2026-09-30_claude_snakegren/snake_ghidra/nro.bin').read_bytes()==image
        common=assets.ARC/'prebuilt/nro/release/lua2cpp_common.nro';common_image,_=nro_flatten.flatten(common.read_bytes())
        assert (scratch/'common_ghidra/nro.bin').read_bytes()==common_image
        names=['sub_ftStatusUniqProcessShoot_initShoot_Common','sub_ftStatusUniqProcessShoot_execShoot_Common','sub_ItemShootDashF_Common','sub_ItemShootDashB_Common','sub_ItemShootWalkFBrake_Common','sub_ItemShootWalkBBrake_Common','sub_ItemShootJumpSquat_Common','sub_ItemShootLanding_Common']
        files={}
        for name in names:
            source=scratch/'common_ghidra/selected'/(name+'.c');target=dest/source.name;target.write_bytes(source.read_bytes());files[target.relative_to(ROOT).as_posix()]=sha(target.read_bytes())
        source=scratch/'lower_acmd_annotated.c';target=dest/'lower_acmd.c';target.write_bytes(source.read_bytes());files[target.relative_to(ROOT).as_posix()]=sha(target.read_bytes())
        record={'tool_version':'1.0.0','date':'2026-09-30','tier':'B','hardware_validated':False,
          'snake_input':path.relative_to(ROOT).as_posix(),'snake_sha256':sha(data),
          'common_input':common.relative_to(ROOT).as_posix(),'common_sha256':sha(common.read_bytes()),
          'tool':'Ghidra 11.1.2, tools/nro_decomp; native registration operand audit',
          'note':'C has dropped Lua operands; owned Rust uses assembly/const table to resolve them. No donor fighter code is called.',
          'native_lower_acmd_registrations':rows,'evidence_sha256':files,
          'measured_constants':{'brake_speed_threshold':0.001,'set_walk_motion_arg6':'L2CValue::NIL','air_inherit_status_const_offset':'0x1f10 (JUMP_AERIAL)'}}
        record_path.write_text(json.dumps(record,indent=2)+'\n')
    record=json.loads(record_path.read_text());assert record['snake_sha256']==sha(data)
    assert record['common_sha256']==sha((ROOT/record['common_input']).read_bytes())
    assert record['native_lower_acmd_registrations']==rows
    for name,digest in record['evidence_sha256'].items():assert sha((ROOT/name).read_bytes())==digest,name
    acmd=(gen.OUT_DIR/'acmd.rs').read_text();registered=set(re.findall(r'_acmd\("([^"]+)"',acmd))
    _,_,donor=assets.base.parse_mlist(assets.DONOR_MLIST)
    for stem,kind in gen.LOWER_SOURCES:
        entry=donor[assets.base.hash40(kind)];tail=(24+len(entry['animations'])*9+3)&~3
        scripts=gen.split_functions((gen.DONOR/(stem+'.txt')).read_text())
        for category in ('expression','sound','effect'):
            import struct
            value=struct.unpack_from('<Q',entry['raw'],tail+('expression','sound','effect').index(category)*8)[0]
            name=category+'_'+stem.lower()
            if name in scripts:
                assert value==assets.base.hash40(name),(kind,category,hex(value))
                assert category+'_pgwrsnake'+kind.replace('_','') in registered
    assert 'loc.imp' not in acmd and 'methodlib' not in acmd
    print('PASS: 30 native registrations, 8 common translations, lower motion/script bindings and evidence hashes')
if __name__=='__main__':main()
