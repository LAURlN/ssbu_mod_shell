"""Catalogue the sounds a `eflame` fighter in c06/c07 can actually hear, and
propose substitutes for the G&W ones that cannot load.

Why this exists
---------------
`PLAY_SE(Hash40::new("se_gamewatch_wave04_mi"))` resolves by hashing the name
and looking it up in the banks the *current fighter* loaded. A Pyra in c06/c07
is still `eflame`, so only eflame's banks plus the always-resident system banks
are resident: every `se_gamewatch_*` name silently plays nothing. The handoff
asks to substitute only "where a substitute is obvious", which needs the real
bank contents rather than a guess.

Layout (measured, not documented)
--------------------------------
Two files per bank, used together because each holds something the other lacks:

* `<bank>.tonelabel`  - `u32 version(1)`, `u32 count`, then `2*count` u32 keys,
  and nothing else. Verified on `se_gamewatch.tonelabel`: 8 + 70*8 == 568 == its
  size. The key is the low 32 bits of Hash40 (zlib.crc32), so it proves
  membership but carries no name.
* `<bank>.nus3audio`  - an `AUDIINDX` chunk holding a NUL-terminated name table.
  Readable, but it can contain entries the bank does not actually key on.

Names are therefore taken from the audio file and then *validated* against the
tonelabel, so a name is only reported as available when both agree.

Costume banks `se_<fighter>_c0N` collapse onto `se_<fighter>`: a fighter loads
its own set for whichever costume is selected.

Run with the cp312 interpreter:
    toolchains/py312/python.exe src/pgwr/tools/sound_names.py --index
    toolchains/py312/python.exe src/pgwr/tools/sound_names.py NAME [NAME...]
    toolchains/py312/python.exe src/pgwr/tools/sound_names.py --find hit
"""
from __future__ import annotations

import json
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BANK_ROOT = ROOT / 'dumps' / 'arc' / 'sound' / 'bank'
OUT = Path(__file__).resolve().parents[1] / 'sound-inventory.json'

# Sound identifiers are lowercase, start with a letter, and contain no spaces.
NAME_RE = re.compile(rb'[a-z][a-z0-9_]{4,63}')


def hash40_low(name: str) -> int:
    """Low 32 bits of Hash40, which is what the bank keys on."""
    return zlib.crc32(name.encode('utf-8')) & 0xFFFFFFFF


def bank_key(path: Path) -> str:
    key = path.relative_to(BANK_ROOT).with_suffix('').as_posix()
    return re.sub(r'_c\d\d$', '', key)  # costume banks share their fighter's entry


def read_keys(tonelabel: Path) -> set[int]:
    data = tonelabel.read_bytes()
    version, count = struct.unpack_from('<II', data, 0)
    if version != 1:
        raise ValueError(f'{tonelabel}: unexpected version {version}')
    if 8 + count * 8 != len(data):
        raise ValueError(f'{tonelabel}: expected {8 + count * 8} bytes, file is {len(data)}')
    return set(struct.unpack_from(f'<{2 * count}I', data, 8))


def read_names(nus3audio: Path) -> set[str]:
    data = nus3audio.read_bytes()
    start = data.find(b'AUDIINDX')
    if start < 0:
        return set()
    return {m.group().decode() for m in NAME_RE.finditer(data, start)}


def load_banks() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return (validated names per bank, raw hashes per bank)."""
    raw: dict[str, set[int]] = {}
    names: dict[str, set[str]] = {}
    for tonelabel in sorted(BANK_ROOT.rglob('*.tonelabel')):
        key = bank_key(tonelabel)
        raw.setdefault(key, set()).update(read_keys(tonelabel))
    for nus3audio in sorted(BANK_ROOT.rglob('*.nus3audio')):
        key = bank_key(nus3audio)
        if key not in raw:
            continue  # no tonelabel for this bank; membership cannot be proven
        names.setdefault(key, set()).update(read_names(nus3audio))
    # Keep only names the bank actually keys on.
    validated = {k: {n for n in v if hash40_low(n) in raw[k]} for k, v in names.items()}
    return validated, raw


def main() -> int:
    if not BANK_ROOT.is_dir():
        print(f'error: no sound bank export at {BANK_ROOT} (set MGW_EXPORT)', file=sys.stderr)
        return 2
    banks, raw = load_banks()

    def union(pred) -> set[str]:
        return {n for key, ns in banks.items() if pred(key) for n in ns}

    eflame = union(lambda k: k.startswith('fighter/se_eflame'))
    gamewatch = union(lambda k: k.startswith('fighter/se_gamewatch'))
    # NOTE: this export contains no always-resident common/system SFX bank. The
    # only non-`fighter/se_*` banks here are fighter_voice and narration, which
    # are not usable as move-sound substitutes, so they are excluded rather than
    # mislabelled. The consequence is recorded in the handoff: `sys_*` /
    # `se_common_*` substitutes are the obvious choice but cannot be *verified*
    # from this dump, so only eflame's own bank is treated as proven resident.
    available = eflame

    if '--index' in sys.argv:
        OUT.write_text(json.dumps({
            'banks': sorted(banks),
            'counts': {'eflame': len(eflame), 'gamewatch': len(gamewatch),
                       'available_to_eflame': len(available)},
            'gamewatch_only': sorted(gamewatch - available),
            'available_to_eflame': sorted(available),
            'caveat': 'no common/system SFX bank in this export; only eflame is proven resident',
        }, indent=1) + '\n', encoding='utf-8')
        print(f'{len(banks)} banks -> eflame {len(eflame)} proven available; '
              f'{len(gamewatch - available)} G&W sounds unreachable')
        print(f'wrote {OUT.relative_to(ROOT)}')
        return 0

    if '--find' in sys.argv:
        terms = [a for a in sys.argv[sys.argv.index('--find') + 1:] if not a.startswith('--')]
        hits = sorted(n for n in available if all(t in n for t in terms))
        for n in hits[:200]:
            print(f'  {n}')
        print(f'{len(hits)} available sounds match {terms}', file=sys.stderr)
        return 0

    names = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not names:
        print(__doc__, file=sys.stderr)
        return 2
    for name in names:
        verdict = ('PLAYS (eflame)' if name in eflame
                   else 'G&W-ONLY, will be SILENT' if name in gamewatch
                   else 'not in this export')
        print(f'  {name:38s} 0x{hash40_low(name):08x}  {verdict}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
