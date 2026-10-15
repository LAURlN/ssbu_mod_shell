"""Pin public vanilla ACMD and bindings; no game content is downloaded."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'refs/donkey_cargo'
COMMIT = '59004685238a3f6f93bae905d3a4e079701c40b4'

def fetch(path):
    url = f'https://raw.githubusercontent.com/WuBoytH/SSBU-Dumped-Scripts/{COMMIT}/{path}'
    data = urllib.request.urlopen(url, timeout=45).read()
    target = OUT / 'donor_acmd' / Path(path).name
    target.write_bytes(data)
    return dict(file=target.relative_to(ROOT).as_posix(), url=url, commit=COMMIT,
                sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), tier='C')

if __name__ == '__main__':
    paths = json.loads((OUT / 'acmd_paths.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, paths))
    url = 'https://raw.githubusercontent.com/ultimate-research/skyline-smash/315e4e8bebb460ebb9f02f30f07b0f13883ba3d6/src/lua_const.rs'
    data = urllib.request.urlopen(url, timeout=45).read()
    (OUT / 'lua_const.rs').write_bytes(data)
    records.append(dict(file='refs/donkey_cargo/lua_const.rs', url=url,
                        commit='315e4e8bebb460ebb9f02f30f07b0f13883ba3d6',
                        sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), tier='C'))
    (OUT / 'public_sources.json').write_text(json.dumps(records, indent=2) + '\n')
    print(f'Pinned {len(records)} public sources')
