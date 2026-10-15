"""Extract native inputs using an isolated ARC extractor with Windows namespace fix."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[4]
LAB = ROOT.parents[1]
OUT = LAB / 'gamedata/ssbu-13.0.4/gaogaen_throw_b/native'

def main():
    import os
    cache = ROOT / 'builds/.cache/gaogaen_throw_b'
    source = cache / 'arc-extract'
    (source / 'src').mkdir(parents=True, exist_ok=True)
    for name in ('Cargo.toml', 'Cargo.lock'):
        shutil.copyfile(LAB / 'tools/arc-extract' / name, source / name)
    original = (LAB / 'tools/arc-extract/src/main.rs').read_text()
    old = 'path.replace("stream:/", "stream;/")'
    assert original.count(old) == 1
    (source / 'src/main.rs').write_text(original.replace(old, 'path.replace(":/", ";/")'))
    env = dict(os.environ, CARGO_HOME=str(cache / 'cargo-home'), CARGO_TARGET_DIR=str(cache / 'arc-target'))
    subprocess.run(['cargo', '+stable-x86_64-pc-windows-gnu', 'build', '--manifest-path', str(source / 'Cargo.toml'), '--release', '--offline'], env=env, check=True)
    uris = [f'prebuilt:/nro/release/lua2cpp_{fighter}.nro' for fighter in ('gaogaen', 'common')]
    subprocess.run([str(cache / 'arc-target/release/arc-extract.exe'), '--arc', str(LAB / 'gamedata/ssbu-13.0.4/data.arc'), '--out', str(OUT), *uris], check=True)
    records = []
    for uri in uris:
        path = OUT / uri.replace(':/', ';/')
        data = path.read_bytes()
        assert data[16:20] == b'NRO0', 'Unexpected NRO header'
        records.append(dict(archive_path=uri, local_path=path.relative_to(LAB).as_posix(), size=len(data), sha256=hashlib.sha256(data).hexdigest()))
    manifest = ROOT / 'evidence/2026-10-02_pgwr_gaogaen_throw_b/NATIVE_INPUTS.json'
    manifest.write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(records, indent=2))

if __name__ == '__main__':
    main()
