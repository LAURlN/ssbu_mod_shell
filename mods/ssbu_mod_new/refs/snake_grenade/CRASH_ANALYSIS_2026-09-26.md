# Snake grenade crash: 2026-09-26.p1

> **SUPERSEDED 2026-09-26. Do not act on the null-deref theory below.**
> The .p1/.p2 crash at `0x1674e9c` was read as a null read in
> `snakegrenade::life()`. It is not, and `life()` is not where .p3 dies. The
> .p3 fault is at `cross2+0x395fba4`, ~14 MB away, in a bare function
> prologue, with thousands of recursive frames at `cross2+0x4deff8`. The
> current analysis and the .p4 bisect are in
> `mod_files/mythra_gamewatch_swap/DIAGNOSIS.md`. This file is kept only as a
> record of what was tried.

The attached Atmosphere report identifies a data abort in the native Snake
grenade item script:

- Result: `0x4A8 (2168-0002)`
- Fault address: `0`
- PC: `cross2_Release.nss+0x1674e9c`
- Function: `app::snakegrenade::life()+0xc`
- Caller: `lua2cpp_item.nrs`

Disassembly of the matching game build shows the faulting instruction is a
load through a pointer in the Snake grenade fuse-parameter lookup chain. The
item script reaches `life()` during native grenade creation, so the crash is
before the item can finish initializing. Since the crash occurred with no Snake
fighter loaded, the strongest diagnosis is that the Snake `param_special_n`
cache was never populated. This diagnosis is based on the faulting path and
test setup; the proposed cache initialization still needs hardware verification.

The follow-up report from the .p2 test has the same fault at the same
instruction. Its supplied log excerpt shows the item creation attempt but does
not include the expected preload diagnostic, so it cannot confirm that the
preload branch ran. In either case, the resource preload did not prevent the
same null dereference.

The function accesses the `FighterParamAccessor2` singleton at main-image
symbol `0x52bb3b0`; the crash has X8 equal to zero while executing the load
from `[x8+0xf0]`. The preceding lookup at singleton offset `0x7e0` therefore
returned a null Snake-specific entry. The .p3 build hooks
`snakegrenade::life()` at `0x1674e90` and returns the stock 150-frame fuse
value. This bypasses the missing lookup while keeping the game's native item
script and explosion. The hook is global while the plugin is loaded and needs
Switch verification.

The crashing .p1 payload SHA-256 was
`23bf74b4236d2cd95dfeb98e7511c40da1d851a898bd8c3e27ac2e91d4e2d238`; .p2
also crashed at the same instruction (SHA-256
`33bc430f9d067475e6a9b417b7cb77fe5c7128e5325e1dcbc1fa8f4a811d396b`). The
verified .p3 package SHA-256 is
`3315323b8e8884448384f9e674902d1c07445a921271d576cc4baa4affcd23368`.
