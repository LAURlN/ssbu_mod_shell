"""Audit the two fighter-class event slots G&W uses to give his up-B back, on the 13.0.4 `main` image.

    toolchains/py312/python.exe tools/audit_event_slots.py            # report + write JSON
    toolchains/py312/python.exe tools/audit_event_slots.py --smoke    # assertions only

What it measures (tier B, on `dumps/exefs/13.0.4/main.bin`):

* Fighter-class vtables are found as every relocated table whose slot at +8 is the shared base method
  `0x68d5b0`. There is no RTTI (typeinfo pointer is 0), so a class is tied to a fighter by code
  locality: its own (non-base) methods sit in the same region as that fighter kind's native article
  initialisers (`tools/maindesc.py`).
* Slot +0x210 and +0x220 of each: the base defaults are `0x68d9c0` (`mov w0,#1; ret`) and `0x68d9e0`
  (`ret`). G&W's class overrides both with handlers that `off_flag` his instance flag
  `0x200000E2` (`FIGHTER_GAMEWATCH_INSTANCE_WORK_ID_FLAG_SPECIAL_HI`) on `[[x1+0x20]+0x50]`
  (the module accessor's WorkModule); the +0x220 one only when byte `[x2+0x18]` is non-zero.
  Pyra's class keeps both base defaults, which is why Pyra c06/c07 needs the plugin hook in
  `src/pgwr/plugin/src/status/special_hi.rs` to get the same behaviour.
* The 16 bytes at each base default (instruction + `udf` padding up to the next function) are the
  bytes the plugin hook verifies before installing; a skyline inline hook writes at most 16 bytes.

* Slot +0x168 (added 2026-09-30 for 0.19.1): G&W's `0xa835c0` returns when `[x2+0xc] == 2` (new
  situation AIR) and otherwise clears `0x200000E2` unless the status is SPECIAL_HI (0x1DE), plus
  `0x200000E3`. Pyra (`0xa0cdc0`) and Mythra (class `0x4fb1fa0`, `0xa29ed0`) override the slot with the
  same three-instruction forwarder to their own +0xf8; the base default is `ret` (`0x68d870`).

Console (A, 0.19.0 log): hits refreshed through +0x220; +0x210 never fired; landing did not refresh,
which is what +0x168 accounts for. The situation meaning of `[x2+0xc]` is inferred from the constant
(2 = SITUATION_KIND_AIR) and from Pyra's +0xf8 testing it against 0 (GROUND) - D until the 0.19.1 log.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main_image import MainImage, ROOT  # noqa: E402
import maindesc  # noqa: E402

BASE_SLOT1 = 0x68d5b0
SLOT_RESET, SLOT_DAMAGED = 0x210, 0x220
DEFAULT_RESET, DEFAULT_DAMAGED = 0x68d9c0, 0x68d9e0
EXPECT_BYTES = {DEFAULT_RESET: 'e0030032c0035fd60000000000000000',
                DEFAULT_DAMAGED: 'c0035fd6000000000000000000000000'}
KINDS = {'gamewatch': 0x1c, 'eflame': 0x5a, 'elight': 0x5b}
SLOT_SITUATION = 0x168
FORWARD_F8 = '080040f9037d40f960001fd6'
GW_FLAG_SPECIAL_HI = 0x200000E2
OUT = ROOT / 'refs' / 'gamewatch_special_hi' / 'event_slots.json'


def vtables(img: MainImage) -> list[int]:
    return sorted(o - 8 for o, a in img.relocs.items() if a == BASE_SLOT1)


def owner_kind(img: MainImage, vt: int, regions: dict[str, tuple[int, int]]) -> str | None:
    own = [f for f in (img.ptr(vt + o) for o in range(0, 0x400, 8))
           if f and not 0x68d000 <= f < 0x68e000]
    for name, (lo, hi) in regions.items():
        if own and all(lo - 0x4000 <= f <= hi + 0x4000 for f in own):
            return name
    return None


def audit() -> dict:
    img = MainImage()
    regions = {}
    for name, kind in KINDS.items():
        inits = [d['init'] for d in maindesc.descriptors(img, kind) if d['init']]
        regions[name] = (min(inits), max(inits))
    tables = vtables(img)
    by_kind = {}
    for vt in tables:
        k = owner_kind(img, vt, regions)
        if k:
            by_kind.setdefault(k, []).append(vt)
    rep = {'main_bin': str(img.path.relative_to(ROOT)).replace('\\', '/'),
           'vtables': len(tables),
           'default_users': {hex(SLOT_RESET): sum(img.ptr(v + SLOT_RESET) == DEFAULT_RESET for v in tables),
                             hex(SLOT_DAMAGED): sum(img.ptr(v + SLOT_DAMAGED) == DEFAULT_DAMAGED for v in tables)},
           'default_bytes': {hex(a): img.data[a:a + 16].hex() for a in EXPECT_BYTES},
           'classes': {}}
    for name, vts in by_kind.items():
        for vt in vts:
            h_reset, h_dmg = img.ptr(vt + SLOT_RESET), img.ptr(vt + SLOT_DAMAGED)
            h_sit = img.ptr(vt + SLOT_SITUATION)
            rep['classes'][name] = {
                'slot_0x168': hex(h_sit), 'slot_0x168_bytes': img.data[h_sit:h_sit + 12].hex(),
                'slot_0x168_code': img.function_text(h_sit),
                'vtable': hex(vt), 'slot_0x210': hex(h_reset), 'slot_0x220': hex(h_dmg),
                'slot_0x210_code': img.function_text(h_reset),
                'slot_0x220_code': img.function_text(h_dmg)}
    return rep


def check(rep: dict) -> None:
    for a, want in EXPECT_BYTES.items():
        assert rep['default_bytes'][hex(a)] == want, f'{a:#x} bytes changed'
    gw, ef = rep['classes']['gamewatch'], rep['classes']['eflame']
    assert ef['slot_0x210'] == hex(DEFAULT_RESET) and ef['slot_0x220'] == hex(DEFAULT_DAMAGED), ef
    for slot in ('slot_0x210_code', 'slot_0x220_code'):
        code = ' ; '.join(gw[slot])
        assert 'ldr x8, [x1, #0x20]' in code and 'mov w1, #0xe2' in code and 'movk w1, #0x2000, lsl #16' in code, code
        assert '#0x120]' in code, code  # WorkModule vtable +0x120 = off_flag
    assert 'ldrb w8, [x2, #0x18]' in gw['slot_0x220_code'][0]
    assert gw['slot_0x168'] == '0xa835c0' and gw['slot_0x168_code'][:2] == ['ldr w8, [x2, #0xc]', 'cmp w8, #2'], gw['slot_0x168_code']
    el = rep['classes']['elight']
    assert (ef['slot_0x168'], el['vtable'], el['slot_0x168']) == ('0xa0cdc0', '0x4fb1fa0', '0xa29ed0')
    assert ef['slot_0x168_bytes'] == FORWARD_F8 and el['slot_0x168_bytes'] == FORWARD_F8


def main() -> int:
    rep = audit()
    check(rep)
    if '--smoke' in sys.argv:
        print('audit_event_slots smoke: OK')
        return 0
    OUT.write_text(json.dumps(rep, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in rep.items() if k != 'classes'}, indent=1))
    for name, c in rep['classes'].items():
        print(name, c['vtable'], c['slot_0x210'], c['slot_0x220'])
    print(f'wrote {OUT.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
