"""Read smash-script's CATCH macro at the revision this project pins.

Why this matters
----------------
monkey_flip.rs does not call smash_script::macros::CATCH. It hand-rolls the push
and then calls smash::app::sv_animcmd::CATCH directly, on the stated grounds that
the macro

    "always pushes ELEVEN arguments: for each of x2/y2/z2 that is None it emits
     a bare L2CValue::new(), an empty value, rather than omitting the argument
     ... the engine is handed eleven arguments with three empty ones where it
     expects box-2 offsets"

The donor dumps do not settle the argument count by themselves.
references/diddy_specials/donor_acmd/SpecialAirSJump.txt prints eight values for
the leap, while donor_acmd/Catch.txt prints eleven for a normal grab with the
three extra wrapped in Some(...). So "does None mean the same as omitted" is a
question only the macro can answer, and the answer decides whether the hand-roll
reproduces the donor or shortens its stack.

~/.cargo/git/checkouts does not exist on this machine (the target directory was
copied from the machine that built the deployed NRO, which is also why rustc is
not on PATH). The pinned revision was recovered from that old checkout folder
name: smash-script-cb158d447e5f0892/fdc6144. So the source is fetched from the
pinned revision rather than read locally.
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'scratch' / 'vendor'
REPO = 'WuBoytH/smash-script'
REV = 'fdc6144'


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'mgw-reference-probe'})
    return urllib.request.urlopen(request, timeout=45).read()


print(f'resolving {REPO}@ {REV}')
try:
    tree = json.loads(get(f'https://api.github.com/repos/{REPO}/git/trees/{REV}?recursive=1'))
except urllib.error.HTTPError as error:
    print(f'  FAILED to read tree: HTTP {error.code}')
    raise SystemExit(1)

print(f"  commit {tree.get('sha')}")
paths = [entry['path'] for entry in tree.get('tree', []) if entry.get('type') == 'blob']
print(f'  {len(paths)} blobs')
print()

VENDOR.mkdir(parents=True, exist_ok=True)
wanted = [p for p in paths if p.endswith('.rs') or p == 'Cargo.toml']
print('--- fetched files containing CATCH ---')
for path in wanted[:200]:
    url = f'https://raw.githubusercontent.com/{REPO}/{tree["sha"]}/{path}'
    try:
        data = get(url)
    except urllib.error.HTTPError:
        continue
    text = data.decode('utf-8', errors='replace')
    if 'CATCH' not in text:
        continue
    dest = VENDOR / (path.replace('/', '__'))
    dest.write_bytes(data)
    print(f'  {path} ({len(data)} bytes) -> {dest.name}')

print()
print('--- the CATCH macro / function definition, with context ---')
for file in sorted(VENDOR.glob('*')):
    lines = file.read_text(encoding='utf-8', errors='replace').splitlines()
    for index, line in enumerate(lines):
        if 'CATCH' not in line:
            continue
        if not any(token in line for token in ('macro_rules', 'fn CATCH', 'CATCH!', 'pub use', 'macro')):
            continue
        low = max(0, index - 2)
        high = min(len(lines), index + 22)
        print(f'=== {file.name}:{index + 1} ===')
        for number in range(low, high):
            print(f'  {number + 1}: {lines[number]}')
        print()
