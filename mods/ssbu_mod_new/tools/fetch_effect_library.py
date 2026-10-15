"""Clone the pinned EffectLibrary source the effect converter is built from (v1.0.0).

Why this exists
---------------
`tools/build_hero_effect_converter.py` needs the C# sources of
EffectLibrary / EffectConverter at one exact commit. That source is not part of
this repository and was absent from the tree until 2026-10-02, which blocked
every effect merge (T-0033, T-0050). This tool puts it back reproducibly
instead of leaving a directory that only exists because someone cloned it once.

Pinned
------
    https://github.com/KillzXGaming/EffectLibrary
    d5491138d645221ec92189eeff3ded8c43fd0a1a   (MIT)
That commit is the tree's `refs/brave_special_n/effect_library` and the value
`build_hero_effect_converter.py` asserts before it patches anything.

Usage
-----
    python tools/fetch_effect_library.py            # clone if absent, verify if present
    python tools/fetch_effect_library.py --check    # verify only, no network
    python tools/fetch_effect_library.py --json OUT # write a provenance record

Writes only into `refs/brave_special_n/effect_library/`. The clone is the pinned
input; `build_hero_effect_converter.py` copies it into `builds/.cache/` before
patching, so this directory is never modified by a build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'refs/brave_special_n/effect_library'
REPO = 'https://github.com/KillzXGaming/EffectLibrary'
PIN = 'd5491138d645221ec92189eeff3ded8c43fd0a1a'
LICENSE = 'MIT'


def head() -> str:
    return subprocess.check_output(['git', '-C', str(DEST), 'rev-parse', 'HEAD'], text=True).strip()


def tree_hash() -> str:
    """Content hash of the checked-out sources, .git excluded, path-sorted."""
    digest = hashlib.sha256()
    for path in sorted(p for p in DEST.rglob('*') if p.is_file() and '.git' not in p.parts):
        digest.update(path.relative_to(DEST).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify only, no network access')
    parser.add_argument('--json', type=Path, help='write a provenance record here')
    args = parser.parse_args()
    if not (DEST / '.git').exists():
        if args.check:
            print(f'FAIL: {DEST.relative_to(ROOT)} is not a clone of {REPO}')
            return 1
        DEST.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--quiet', REPO, str(DEST)], check=True)
    commit = head()
    assert commit == PIN, f'pinned commit is {PIN}, checkout is {commit}'
    record = {'date': '2026-10-02', 'repo': REPO, 'commit': commit, 'license': LICENSE,
              'path': DEST.relative_to(ROOT).as_posix(), 'source_tree_sha256': tree_hash(),
              'built_by': 'tools/build_hero_effect_converter.py --from-source',
              'hardware_validated': False}
    print(json.dumps(record, indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
