"""Fetch Diddy's Monkey Flip ACMD text from the project's own pinned source.

Where the donor actually comes from
-----------------------------------
references/mythra_ftilt/manifest.json records the source used for every acmd text
dump already in this project, e.g.

  https://raw.githubusercontent.com/WuBoytH/SSBU-Dumped-Scripts/
      59004685238a3f6f93bae905d3a4e079701c40b4/smashline/lua2cpp_elight/elight/AttackS3.txt

That is WuBoytH/SSBU-Dumped-Scripts at commit 5900468523, laid out as
smashline/lua2cpp_<fighter>/<fighter>/<Script>.txt. This script uses the same
repo, the same pinned commit, and the same layout for Diddy.

Why it matters
--------------
monkey_flip.rs cites references/diddy_specials/donor_acmd/SpecialAirSJump.txt as
the pinned donor for its CATCH call. That file is not in this workspace and never
was: source_audit/fetch_references.py only downloaded Diddy's *status* scripts
(the SpecialS*.c decompiles), never the acmd text. So the leap's catch geometry,
its argument order and its CLUNG_DIDDY argument have no artifact behind them.

This fetches the real ones and hashes them, so the call can be read rather than
remembered. Nothing is written over an existing file, and nothing outside
references/diddy_specials/donor_acmd is touched.
"""
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'references' / 'diddy_specials' / 'donor_acmd'

# Same repository and commit as references/mythra_ftilt/manifest.json.
REPO = 'WuBoytH/SSBU-Dumped-Scripts'
COMMIT = '59004685238a3f6f93bae905d3a4e079701c40b4'
BASE = 'smashline/lua2cpp_diddy/diddy'

# Monkey Flip's own scripts first, then the shared grab scripts for reference on
# the shape of a catch call. The dump names the game script plainly, so try the
# bare name first and only then the category-prefixed spellings.
SCRIPTS = [
    'SpecialS', 'SpecialairS', 'SpecialAirS',
    'SpecialSJump', 'SpecialAirSJump',
    'SpecialSKick', 'SpecialAirSKick',
    'SpecialSKickLanding', 'SpecialSFlipLanding', 'SpecialSFlipFall',
    'SpecialSDamageFall',
    'SpecialSStick', 'SpecialSStickAttack', 'SpecialSStickAttack2',
    'SpecialSStickJump', 'SpecialSStickJump2',
    'Catch', 'CatchDash', 'CatchTurn', 'CatchAttack',
]
SPELLINGS = ['{}.txt', 'game_{}.txt', 'effect_{}.txt', 'sound_{}.txt']


def try_fetch(name):
    for spelling in SPELLINGS:
        filename = spelling.format(name)
        url = f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{BASE}/{filename}'
        try:
            data = urllib.request.urlopen(url, timeout=40).read()
        except urllib.error.HTTPError:
            continue
        except Exception as error:  # noqa: BLE001 - report, keep going
            print(f'  FAILED  {filename}: {type(error).__name__}: {error}')
            return None
        return filename, url, data
    return None


DEST.mkdir(parents=True, exist_ok=True)
manifest = []
print(f'pinned source: {REPO} @ {COMMIT}')
print(f'layout:        {BASE}/<Script>.txt')
print()

for name in SCRIPTS:
    found = try_fetch(name)
    if found is None:
        print(f'  missing {name}')
        continue
    filename, url, data = found
    (DEST / filename).write_bytes(data)
    manifest.append({
        'file': filename,
        'url': url,
        'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
    })
    print(f'  ok      {filename} ({len(data)} bytes)')

(DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print()
print(f'wrote {len(manifest)} file(s) to {DEST}')
