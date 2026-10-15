"""Pin native Snake grenade status and motion-list references for the c07 port."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'references/snake_grenade'
STATUS_REPO = 'Coolsonickirby/SSBU-Dumped-Status-Scripts'
STATUS_REV = 'b6bb1fecf7a0a3ee872cea73c94acccccadf8133'
MOTION_REPO = 'WuBoytH/SSBU-Dumped-Motion-Lists'


def read(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'c07-grenade-research'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def listing(repo, path, rev):
    return json.loads(read(f'https://api.github.com/repos/{repo}/contents/{path}?ref={rev}'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = 'ghidra_scripts/lua2cpp_snake.nro/snake/snake/status'
    phases = [x for x in listing(STATUS_REPO, base, STATUS_REV) if x['name'].startswith('SpecialN')]
    jobs = []
    for phase in phases:
        for item in listing(STATUS_REPO, phase['path'], STATUS_REV):
            if item['type'] == 'file' and item['name'].endswith('.c'):
                jobs.append((item['download_url'], OUT / 'status' / f"{phase['name']}__{item['name']}", STATUS_REV))
    motion_rev = json.loads(read(f'https://api.github.com/repos/{MOTION_REPO}/commits/main'))['sha']
    pending = ['fighter/snake/motion']
    while pending:
        for item in listing(MOTION_REPO, pending.pop(), motion_rev):
            if item['type'] == 'dir':
                pending.append(item['path'])
            elif item['name'].endswith('.yml'):
                jobs.append((item['download_url'], OUT / 'motion' / item['path'].replace('/', '__'), motion_rev))

    def save(job):
        url, path, rev = job
        data = read(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {'file': str(path.relative_to(OUT)), 'url': url, 'commit': rev,
                'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

    with ThreadPoolExecutor(max_workers=4) as pool:
        manifest = list(pool.map(save, jobs))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Pinned {len(manifest)} files in {OUT}')


if __name__ == '__main__':
    main()
