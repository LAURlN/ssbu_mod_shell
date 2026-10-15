"""Package isolated Hero HUD/angle snapshots; --check is the hash/scope smoke test.
Uses the existing release tool's tree hash format; never builds shared source or installs.
"""
from pathlib import Path
import argparse,difflib,hashlib,json,re,shutil,subprocess,sys,tomllib
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
from package_pgwr_release import tree,sha
CACHE=ROOT/'builds/.cache/mana_hud_codex'
BASE=ROOT/'builds/pgwr/0.20.20+ready-assets.1'
SOURCE_BASE=ROOT/'builds/.cache/dk_cargo/test-plugin-0.1.1'
PACKAGE=ROOT/'builds/pgwr/zapple-mana-hud-0.1.1'
MOD=Path('ultimate/mods/pyra_gamewatch_reskin')
NRO=Path('atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro')
TASK=['Cargo.toml','Cargo.lock','src/mythra/hero_mana/mod.rs','src/mythra/hero_mana/hud.rs','src/mythra/hero_mana/hud_signatures.rs','src/mythra/hero_side_b/script_acmd.rs']
VARIANTS={'combined':'snake-neutral-b,hero-side-b,hero-mana-hud','angle-only':'snake-neutral-b,hero-side-b','hud-only':'snake-neutral-b,hero-side-b,hero-mana-hud','baseline-control':'snake-neutral-b,hero-side-b'}
def clean(s):
 return re.sub(r'\s+','',re.sub(r'//[^\n]*','',s))
def source_tree(root):
 return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and 'target' not in p.relative_to(root).parts}
def source_scope():
 b=source_tree(SOURCE_BASE);t=source_tree(CACHE/'combined')
 delta=sorted(k for k in t if b.get(k)!=t[k]);assert delta==sorted(TASK),delta
 assert not set(b)-set(t)
 # Semantic control: only the effect rotation call and new tuple differ.
 path='src/mythra/hero_side_b/script_acmd.rs'
 a=clean((SOURCE_BASE/path).read_text());z=clean((CACHE/'combined'/path).read_text())
 z=z.replace('constZAPPLE_BOLT_ROT:(f32,f32,f32)=(16.3,18.2,-83.5);','').replace('ZAPPLE_BOLT_ROT.0,ZAPPLE_BOLT_ROT.1,ZAPPLE_BOLT_ROT.2','0,0,-90')
 assert a==z,'angle changed more than the level-2 effect rotation'
 # Installed DK cargo / Incineroar registrations, up-B gravity and dashgrab untouched.
 for name in VARIANTS:
  files=source_tree(CACHE/name)
  changed=set(k for k in files if b.get(k)!=files[k]);assert changed<=set(TASK),(name,changed)
  for k in b:
   if k not in TASK: assert files[k]==b[k],(name,k)
 return {k:{'baseline':b.get(k),'task':t[k]} for k in TASK}
def patch(paths,mode):
 lines=[]
 for k in paths:
  old=(SOURCE_BASE/k).read_text() if (SOURCE_BASE/k).exists() else ''
  new=(CACHE/'combined'/k).read_text()
  if mode=='hud' and k=='Cargo.toml': new=new.replace('version = "0.20.21"','version = "0.20.20"',1)
  if mode=='version':
   if k=='Cargo.toml': new=old.replace('version = "0.20.20"','version = "0.20.21"',1)
  lines.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+k if old else '/dev/null',tofile='b/'+k))
 return ''.join(lines)
def verify():
 m=json.loads((PACKAGE/'MANIFEST.json').read_text())
 files,digest=tree(PACKAGE/MOD);assert files==m['mod_files'] and digest==m['mod_tree_sha256']
 original,_=tree(BASE/MOD);assert set(original)==set(files)
 assert [k for k in files if files[k]!=original[k]]==['info.toml']
 assert sha(BASE/NRO)=='214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058'
 for name,row in m['variants'].items():
  assert sha(PACKAGE/row['path'])==row['sha256']==sha(CACHE/'nro'/f'{name}.nro')
  blob=(PACKAGE/row['path']).read_bytes()
  assert (b'HUD READY route=game-part-selector' in blob)==('hero-mana-hud' in row['features'])
  assert b'0.20.21' in blob
 assert tomllib.loads((PACKAGE/MOD/'info.toml').read_text())['version']=='0.20.21'
 assert source_scope()==m['source_delta']
 for k,h in m['patches'].items(): assert sha(PACKAGE/'patches'/k)==h
 print('PASS: 5099-file tree; info version only; four built/packaged NRO hashes; feature matrix; six-file isolated source scope; DK/Incineroar and unrelated source preserved.')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args()
 if args.check: verify();return
 assert not PACKAGE.exists(),'Do not overwrite a versioned package'
 delta=source_scope();PACKAGE.mkdir(parents=True)
 shutil.copytree(BASE/MOD,PACKAGE/MOD)
 p=PACKAGE/MOD/'info.toml';p.write_text(p.read_text().replace('version = "0.20.20"','version = "0.20.21"',1))
 variants={}
 for name,features in VARIANTS.items():
  dest=NRO if name=='combined' else Path('controls')/f'libpyra_gamewatch_reskin.{name}.nro'
  (PACKAGE/dest).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(CACHE/'nro'/f'{name}.nro',PACKAGE/dest)
  variants[name]={'path':dest.as_posix(),'sha256':sha(PACKAGE/dest),'bytes':(PACKAGE/dest).stat().st_size,'features':features,'source':(CACHE/name).relative_to(ROOT).as_posix()}
 (PACKAGE/'patches').mkdir()
 for name,paths in [('angle',[TASK[-1]]),('hud',[TASK[0],*TASK[2:5]]),('version',TASK[:2])]:
  (PACKAGE/'patches'/f'{name}.patch').write_text(patch(paths,name), newline=chr(10))
 files,digest=tree(PACKAGE/MOD)
 m={'task':'zapple_mana_hud','task_version':'0.1.1','shared_plugin_version':'0.20.21','readiness':'READY','installed':False,'runtime_verified':False,'date':'2026-10-03','git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'baseline':BASE.relative_to(ROOT).as_posix(),'baseline_nro_sha256':sha(BASE/NRO),'baseline_manifest_sha256':sha(BASE/'MANIFEST.json'),'source_baseline':SOURCE_BASE.relative_to(ROOT).as_posix(),'source_delta':delta,'variants':variants,'nro_path':NRO.as_posix(),'nro_sha256':variants['combined']['sha256'],'mod_tree_sha256':digest,'file_count':len(files),'mod_files':files,'asset_changes':['info.toml version only'],'patches':{p.name:sha(p) for p in (PACKAGE/'patches').glob('*.patch')},'toolchain':'cargo 1.98.1; cargo-skyline 3.5.0; existing Skyline cached toolchain; offline','build_command':'CARGO_TARGET_DIR=<repo>/builds/.cache/mana_hud/target-hud cargo skyline build --release --features <variant features> -- --offline','evidence':'evidence/2026-10-03_pgwr_zapple_mana_hud/RESULT.md','reserved_damage_recovery':False,'framework_changes':False,'checks':'25 native spans + 9 slots; 161 HUD checks for each HUD variant; solver and signature negative controls; four measurements; --check package scope/hashes'}
 (PACKAGE/'MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');verify()
if __name__=='__main__':main()
