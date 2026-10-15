"""Verify local Hero neutral-B ACMD against the workspace's pinned upstream commit.

Version 1.0.0. Reads local scripts and upstream raw files; writes only provenance
to refs/brave_special_n/acmd_pin.json. No asset copying or builds.
Smoke test: --check checks saved digests against the local scripts, offline.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '59004685238a3f6f93bae905d3a4e079701c40b4'
REPO = 'https://github.com/WuBoytH/SSBU-Dumped-Scripts'
DEST = ROOT / 'refs/brave_special_n/acmd_pin.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        report = json.loads(DEST.read_text(encoding='utf-8'))
        assert report['all_match']
        for row in report['files']:
            assert hashlib.sha256((ROOT / row['local']).read_bytes()).hexdigest() == row['sha256']
        print('Pinned Hero ACMD local hash check OK')
        return
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    base = ROOT / cfg['dumps']['scripts']
    scripts = base / 'smashline/lua2cpp_brave'
    files = sorted(p for p in (scripts / 'brave').glob('*.txt')
                   if p.name.startswith(('SpecialN', 'SpecialAirN')))
    files += sorted((scripts / 'brave_fireball').glob('*.txt'))

    def verify(path):
        url = f'https://raw.githubusercontent.com/WuBoytH/SSBU-Dumped-Scripts/{COMMIT}/{path.relative_to(base).as_posix()}'
        local = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            remote = hashlib.sha256(urllib.request.urlopen(url, timeout=25).read()).hexdigest()
            return {'local': path.relative_to(ROOT).as_posix(), 'url': url,
                    'sha256': local, 'upstream_sha256': remote, 'match': local == remote}
        except Exception as error:
            return {'local': path.relative_to(ROOT).as_posix(), 'url': url,
                    'sha256': local, 'match': False, 'error': str(error)}

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(verify, files))
    report = {'date': '2026-09-30', 'repo': REPO, 'commit': COMMIT,
              'all_match': all(row['match'] for row in rows), 'files': rows}
    DEST.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'Hero ACMD pin: {sum(row["match"] for row in rows)}/{len(rows)} files match {COMMIT}')


if __name__ == '__main__':
    main()
