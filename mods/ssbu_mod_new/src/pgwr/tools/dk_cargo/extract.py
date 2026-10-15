"""Reproduce task-local ARC extraction; never downloads game content."""
import json
from pathlib import Path
import shutil
import subprocess
import os

ROOT=Path(__file__).resolve().parents[4]
WS=ROOT.parents[1]
CACHE=ROOT/'builds/.cache/dk_cargo'

if __name__=='__main__':
    crate=CACHE/'arc-extract'
    (crate/'src').mkdir(parents=True,exist_ok=True)
    for name in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
        shutil.copyfile(WS/'tools/arc-extract'/name,crate/name)
    source=(WS/'tools/arc-extract/src/main.rs').read_text()
    old='path.replace("stream:/", "stream;/")'
    assert old in source
    (crate/'src/main.rs').write_text(source.replace(old,'path.replace(":/", ";/")'))
    env=dict(os.environ,CARGO_TARGET_DIR=str(CACHE/'arc-target'))
    subprocess.run(['cargo','+stable-x86_64-pc-windows-gnu','build','--release','--offline',
        '--manifest-path',str(crate/'Cargo.toml')],cwd=WS,env=env,check=True)
    inputs=json.loads((ROOT/'refs/donkey_cargo/local_inputs.json').read_text())
    prefix='gamedata/ssbu-13.0.4/dk_cargo/'
    paths=[r['path'].removeprefix(prefix).replace('prebuilt;/','prebuilt:/') for r in inputs]
    subprocess.run([str(CACHE/'arc-target/release/arc-extract.exe'),
        '--arc','gamedata/ssbu-13.0.4/data.arc','--out',prefix]+paths,cwd=WS,check=True)
