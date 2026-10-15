"""Print what a built NRO actually is, so a deploy can be checked against it.

The pipeline has already shipped a stale NRO once: a PowerShell exit code masked a
failed cargo-skyline packaging step, cargo had printed "Finished" before it, and the
deploy then copied the *previous* build while reporting success. Exit codes and
"Finished" lines are therefore not evidence about a binary. Two questions have to be
answerable mechanically for every build instead:

  * which build banner is inside this NRO, and
  * does it contain the markers this round added?

Usage:
    python scratch/verify_nro.py path/to/<name>.nro
    python scratch/verify_nro.py path/to/release/*.nro
    python scratch/verify_nro.py --markers 2026-09-18.j,GRABDIS mod_output/<name>.nro

Shells differ, so globs are expanded here rather than by the caller.
"""
import glob
import hashlib
import sys
from pathlib import Path

DEFAULT_MARKERS = (
    'MGW-MFLIP',
    'build 2026-',
    'CATCH ACMD',
    'GRABARM',
    'GRABDIS',
    'CATCHBOX',
    'CATCHGEO',
    'CATCHW',
    'NOCATCH',
    'CATCH HANDOFF',
    'CLING',
    'centre0=',
    'rebound=',
)


def report(path, markers):
    if not path.is_file():
        print(f'{path}: no such file')
        return
    data = path.read_bytes()
    print(f'{path}')
    print(f'  sha256 {hashlib.sha256(data).hexdigest()}')
    print(f'  size   {len(data)} bytes')
    found = []
    print('  markers:')
    for marker in markers:
        count = data.count(marker.encode())
        print(f'    {marker:<14} {count}')
        if count:
            found.append(marker)
    banners = sorted({
        token for token in data.decode('utf-8', errors='ignore').split()
        if token.startswith('2026-') and token.endswith(':')
    })
    if banners:
        print('  build banners found inline (approximate, decoded from the binary):')
        for banner in banners:
            print(f'    {banner}')
    if not found:
        print('  NOTE: not one marker is present. This is almost certainly not the build')
        print('        that was just made, whatever the log said.')


def main(argv):
    markers = DEFAULT_MARKERS
    args = argv[1:]
    if '--markers' in args:
        index = args.index('--markers')
        markers = tuple(m for m in args[index + 1].split(',') if m)
        args = args[:index] + args[index + 2:]
    if not args:
        print(__doc__)
        return 1
    for arg in args:
        matched = sorted(glob.glob(arg, recursive=True))
        for name in (matched or [arg]):
            report(Path(name), markers)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
