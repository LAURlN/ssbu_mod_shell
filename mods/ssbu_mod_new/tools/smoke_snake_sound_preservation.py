"""Regression smoke: Snake sound append preserves every assembled baseline tone (v1.0.0).

Usage: --baseline 0.20.10 [--package 0.20.11]. With no package, merges in a
TemporaryDirectory under dated scratch and removes it afterwards. Compares
names, encoded samples, complete original tone records and sequence rows;
offline serialization evidence only, never playback proof.
"""
from pathlib import Path
import argparse,datetime,json,shutil,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import merge_snake_neutral_b_sound as sn
c=sn.codec

def verify(baseline, output):
    for slot in ('c06','c07'):
        rel=f'sound/bank/fighter/se_eflame_{slot}'
        old=baseline/rel;new=output/rel
        audio=c.audio_read(old.with_suffix('.nus3audio').read_bytes())
        result=c.audio_read(new.with_suffix('.nus3audio').read_bytes())
        assert result[:len(audio)]==audio,slot
        assert {n.lower() for n,_ in result[len(audio):]}==sn.REQUIRED,slot
        old_chunks=c.bank_read(old.with_suffix('.nus3bank').read_bytes());new_chunks=c.bank_read(new.with_suffix('.nus3bank').read_bytes())
        tones=c.tones_read(dict(old_chunks)[b'TONE']);new_tones=c.tones_read(dict(new_chunks)[b'TONE'])
        assert new_tones[:len(tones)]==tones,slot
        assert [(t,v) for t,v in old_chunks if t!=b'TONE']==[(t,v) for t,v in new_chunks if t!=b'TONE'],slot
        names=[n for n,_ in audio];new_names=[n for n,_ in result]
        labels=c.labels_read(old.with_suffix('.tonelabel').read_bytes(),names)
        new_labels=c.labels_read(new.with_suffix('.tonelabel').read_bytes(),new_names)
        assert set(labels)<=set(new_labels),slot
    rel='sound/sequence/fighter/eflame.sqb';old=baseline/rel
    if not old.is_file():old=c.ARC/rel
    before=c.sqb_read(old.read_bytes());after=c.sqb_read((output/rel).read_bytes())
    assert after[:len(before)]==before

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',required=True);p.add_argument('--package');a=p.parse_args()
    baseline=ROOT/'builds/pgwr'/a.baseline/'ultimate/mods/pyra_gamewatch_reskin'
    if a.package:verify(baseline,ROOT/'builds/pgwr'/a.package/'ultimate/mods/pyra_gamewatch_reskin')
    else:
        scratch=ROOT/'scratch'/(str(datetime.date.today())+'_codex_snake');scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            output=Path(tmp)
            for slot in ('c06','c07'):
                for ext in ('.nus3audio','.nus3bank','.tonelabel'):
                    rel=f'sound/bank/fighter/se_eflame_{slot}{ext}';target=output/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(baseline/rel,target)
            rel='sound/sequence/fighter/eflame.sqb'
            if (baseline/rel).is_file():
                (output/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(baseline/rel,output/rel)
            sn.build(output);verify(baseline,output)
    print('PASS: all baseline audio, tone records, bank chunks, labels and sequence rows retained')
if __name__=='__main__':main()
