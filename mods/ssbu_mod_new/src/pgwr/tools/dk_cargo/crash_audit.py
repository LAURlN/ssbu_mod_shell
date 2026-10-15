"""Preserve and decode cargo 0.1.0 console evidence; card read-only.

Usage: crash_audit.py --card <mounted drive root>. No installation or game run.
"""
import argparse
import json
import re
import shutil
from pathlib import Path
from audit import ROOT, WS, sha, MainImage, h40

DEST=ROOT/'evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_hardware'

def run(card):
    assert not (DEST/'CAPTURE.json').exists(),'Preserve immutable hardware capture'
    DEST.mkdir(exist_ok=True)
    plugin=card/'atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro'
    assert sha(plugin.read_bytes())=='270bc6723393767b7ae0dd639faae821fe0ffde6357938a552bed41a7faa7795'
    names=['01791012191','01791012352','01791012515']
    inputs=[card/'ultimate/pgwr_dk_cargo_log.txt']
    inputs.extend(card/'atmosphere/crash_reports'/f'{n}_01006a800016e000.log' for n in names)
    entries=[]
    for source in inputs:
        shutil.copyfile(source,DEST/source.name)
        text=source.read_text(encoding='utf-8');entry={'file':source.name,'sha256':sha(source.read_bytes())}
        if source.suffix=='.log':
            assert 'cross2_Release.nss + 0x483130' in text
            assert 'status_ShoulderedDonkeyThrownEv + 0x270' in text
            assert re.search(r'X\[21\]:\s+0000000000000000',text)
            entry['fault']='main+0x483130, stock common victim Thrown Main+0x270, capture object X8=0; X21=0 is link slot index'
            entry['motion_hash']=re.search(r'X\[19\]:\s+([0-9a-f]+)',text).group(1)
        entries.append(entry)
    image=MainImage(WS/'gamedata/ssbu-13.0.4/main.bin')
    windows={}
    for start,length in [(0x4830c0,0x90),(0x49a540,0x80)]:
        lines=[f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in image.disasm(start,length)]
        path=DEST/f'main_{start:x}.asm';path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        windows[path.name]=sha(path.read_bytes())
    report={'tier':'A hardware crashes/log; B instruction interpretation; D proposed cause until controlled retest',
       'nro_sha256':sha(plugin.read_bytes()),'files':entries,'native_windows':windows,
       'motions':{n:hex(h40('pgwr_dk_cargo_victim_'+n)) for n in ['thrown_f_donkey_f','thrown_f_donkey_b','thrown_f_donkey_hi','thrown_f_donkey_lw']},
       'user_observed_pass':['pickup','walking with captive','jumping with captive','grab release'],
       'user_observed_failure':'Cargo directional throws crash.',
       'log_observations':'Owned START/CARRY, walk/squat/jump/fall/landing and clatter expiry release; no c7 -> owned411 route logged before the three crashes.',
       'hypothesis':'Owned Carry End/Exit recognize only relocated owned next-state IDs; native shoulder_throw queues stock c7 before Pre bridge, so cleanup cuts capture before bridge can recognize parent.'}
    (DEST/'CAPTURE.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Preserved three matching hardware crashes and cargo log; null capture parent at victim thrown motion lookup')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--card',required=True)
    run(Path(parser.parse_args().card))
