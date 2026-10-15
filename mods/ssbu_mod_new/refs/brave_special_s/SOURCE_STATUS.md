# Hero side-B status table - provenance

Measured 2026-09-30 by Buffy. Tier **B** (measured offline by scripts that still exist).

## What this is

`status_table.txt` (247 rows) is every `(status kind, condition, function)` pair that
`lua2cpp_brave.nro` registers through `sv_set_status_func`. It is the input to the Mythra
status-id allocation in `projects/pgwr/TODO.md`.

## How it was produced

```
toolchains/py312/python.exe tools/nro_decomp/nro_flatten.py \
    dumps/arc/prebuilt/nro/release/lua2cpp_brave.nro  brave_flat.bin  brave_labels.json
toolchains/py312/python.exe tools/nro_decomp/status_table.py \
    brave_flat.bin brave_labels.json > status_table.txt
```

Input: `dumps/arc/prebuilt/nro/release/lua2cpp_brave.nro` (13.0.4, region 2).
Flatten reported 657 labels. No Ghidra run: the status *table* is a data-flow question
(`sv_set_status_func` call sites + their two constant loads), not a decompilation, so
`run_ghidra.sh` is not needed for the table itself. Function *bodies* still need Ghidra.

Working copies were in `scratch/2026-09-30_buffy/`; only the table was promoted here.

## Control

The same run reproduces the already-pinned neutral-B table
`refs/brave_special_n/status_table.txt` byte-for-byte on the shared `SPECIAL_N` rows -
e.g. `FIGHTER_BRAVE_STATUS_KIND_SPECIAL_N_SHOOT ... STATUS_PRE 0x31a10` in both. A different
flatten of the same NRO landing on the same addresses is what makes these addresses usable;
without it the table would be a claim rather than a measurement.

## The side-B rows

| status kind | lua_const value | conditions registered |
| --- | --- | --- |
| `FIGHTER_STATUS_KIND_SPECIAL_S` (common) | `0x1DD` | PRE `0x31eb0`, MAIN `0xd8a0`, END `0x8600` |
| `FIGHTER_BRAVE_STATUS_KIND_SPECIAL_S_HOLD` | `0x1E6` | PRE `0x32290`, MAIN `0xe530`, END `0x86d0`, EXEC `0x58f0` |
| `FIGHTER_BRAVE_STATUS_KIND_SPECIAL_S_ATTACK1` | `0x1E7` | PRE `0x32660`, MAIN `0xe780`, END `0x8820`, EXEC `0x5b00`, CHECK_ATTACK `0x3500` |
| `FIGHTER_BRAVE_STATUS_KIND_SPECIAL_S_ATTACK2` | `0x1E8` | PRE `0x32a40`, MAIN `0xea00`, END `0x88a0`, EXEC `0x5b00`, CHECK_ATTACK `0x3500` |
| `FIGHTER_BRAVE_STATUS_KIND_SPECIAL_S_ATTACK3` | `0x1E9` | PRE `0x32e20`, MAIN `0xec80`, END `0x8920` |
| `FIGHTER_BRAVE_STATUS_KIND_SPECIAL_S_ATTACK3_APPEND` | `0x1EA` | PRE `0x33200`, MAIN `0xf100`, END `0x89f0`, EXEC `0x5b00`, CHECK_ATTACK `0x3500` |

Six statuses, no more. Two facts that shape the port:

- **There is no air-specific side-B status.** `lua_const.rs` has no
  `FIGHTER_BRAVE_STATUS_KIND_AIR_S*` at all, and the `d01specialairs*` clips are reached from the
  same six states. Air is a situation difference inside these statuses, not a parallel table -
  so the allocation does not double for air.
- **`CHECK_ATTACK` is registered on 1, 2 and 3_APPEND but not on 3.** A reader that assumes
  uniform conditions across the chain will mis-port the third hit.

`lua_const` values are from the pinned toolchain,
`skyline-smash 315e4e8` (`src/pgwr/plugin/Cargo.toml` line 36):
`~/.cargo/git/checkouts/skyline-smash-f820da3599566683/315e4e8/src/lua_const.rs`.
`FIGHTER_BRAVE_STATUS_KIND_NUM` there is `0x1FE`; `FIGHTER_ELIGHT_STATUS_KIND_NUM` is `0x1F1`.

## Not established here

The table says which function is registered, never what it does. Charge thresholds, motion
names, article generation, the mana/SP gate and the cancel windows all need the function bodies
(Ghidra) or the ACMD text. Nothing in this file is evidence of behaviour on hardware.

---

# Addendum 2026-09-30: `param_special_s`, the HOLD exec body, and where the mana gate is not

Same session, same flatten. Tier **B**, except where marked.

## 1. `param_special_s` - `refs/brave_special_s/param_special_s.json`

`tools/dump_param_special_s.py v1.0.0`, `--check` re-derives and compares. hash40 `0xfea97fe73`,
group hash for the field lookup `0x535b9ad8` = **`hold_frame_m`**. Four entries, only entry 0 populated:

| field | value |
| --- | --- |
| `hold_frame_m` | 9 |
| `hold_frame_l` | 26 |
| `hold_frame_max` | 26 |
| `activate_wait_frame_s` / `_m` / `_l` | 3 / 3 / 3 |
| `hit_stop_mul_s` / `_m` / `_l` | 0.2 / 0.0 / 0.5 |
| `speed_lightning` | -10.0 |
| `offset_x_lightning` / `offset_y_lightning` | 0.0 / 85.0 |
| `hit_speed_y_air` / `hit_accel_y_air` | 0.6 / 0.03 |
| `start_speed_x_mul` (ground) / `_air` | 0.5 / 0.8 |
| `start_speed_y_mul_air` | 0.8 |

No mana/gauge/price/cost-labelled field was decoded in `param_special_s`. This alone
does not locate the SP decision: the separately recovered helper below compares SP.

Cross-check on the hash function: `prc.hash40('param_special_n')` = `0xf899192aa`, and the literal
`0x899192aa` appears in the independently pinned `refs/brave_special_n/neutral_b_status.c`. Same
group hash `0x535b9ad8` is used there. So the decoder and the hash agree with an existing pin.

## 2. `SPECIAL_S_HOLD` `EXEC_STATUS` at `0x58f0` - decoded

`special_s_hold_exec.asm.txt` is the raw listing. Symbol names come from the flatten's PLT map
(`nro_util.plt_map`), const names from `tools/constmap.py` via `nro_util.const_name`.

```
inc_int(ma, SPECIAL_S_WORK_INT_HOLD_FRAME);
p = get_param_int(ma, "param_special_s", "hold_frame_m");
h = get_int(ma, SPECIAL_S_WORK_INT_HOLD_FRAME);
if (h == p) call_script_single(ma, FIGHTER_ANIMCMD_EFFECT, 0x14d29f9c6e, -1);
return int(0);
```

Two details that a paraphrase would lose:

- The compare is **`==`, not `>=`** (`L2CValue::operator==` at PLT `0x23a170`). The charge-complete
  effect therefore fires on the single frame the counter equals 9, which is what makes it fire once
  rather than every frame past the threshold. A port using `>=` would re-trigger it.
- `FIGHTER_ANIMCMD_EFFECT` (`0xd30`) is being *called* here; this function is a one-shot trigger,
  not the per-frame body.

**No gauge is read in this function.**

## 3. Where `FLAG_SUCCESS_SP` is touched

Const-table offsets recovered by scanning `const_name` over the whole table: `FLAG_SUCCESS_SP`
`0xc914`, `WORK_INT_HOLD_FRAME` `0xc958`, `FLAG_ACTIVATE_LIGHTNING` `0xc98c`. (The map itself is a
regenerable cache and is deliberately not pinned here.)

The const offsets reach the code as `mov w8, #0xNNNN` + `ldr w1, [x22, x8]` - **not** as an `ldr`
immediate. Searching for the immediate finds **zero** references and looks like a null result; this
is the exact trap `handbook/06_statuses.md` warns about ("Ghidra drops ... `global_table` indices").

All references, matched to the status table in this directory:

| const | references |
| --- | --- |
| `FLAG_SUCCESS_SP` | ATTACK1 MAIN `0xe814`, ATTACK2 MAIN `0xea94`, ATTACK3 MAIN `0xed64` pass the flag to `0x16db0`; anonymous readers at `0x28d00`, `0x29820` |
| `WORK_INT_HOLD_FRAME` | HOLD EXEC `0x5910` and `0x59a8`, common `SPECIAL_S` MAIN `0xd92c` |
| `FLAG_ACTIVATE_LIGHTNING` | one anonymous function |

**`FLAG_SUCCESS_SP` is referenced in the three attack MAIN bodies and nowhere in HOLD's
PRE/MAIN/END/EXEC.** HOLD neither sets nor clears it.

## 4. SP decision recovered inside the NRO (2026-09-30 correction)

Tier B: `tools/audit_hero_side_b.py` 1.1.0 re-flattens the pinned NRO, reproduces all
247 status rows, resolves constant names against the shipped common NRO and checks
the setter's instructions/PLT targets. Inputs and full hashes:
`native_dependency_audit.json`; instructions: `native_dependency_audit.asm.txt`.

ATTACK1/2/3 call `0x16db0`, which calls `0x1a230`. The latter reads
`FIGHTER_BRAVE_INSTANCE_WORK_ID_FLOAT_SP` and `...FLOAT_MAX_SP`; `amount <= SP`
selects `on_flag` for the passed success flag, otherwise `off_flag`. Neutral-B's
call at `0xce38` is the offline control for the shared helper. The prior inference
that the gate was outside this NRO is retracted (handbook graveyard R-HERO-S-1).
No gauge read was decoded in HOLD EXEC; that limited finding remains valid.

The user's decision remains: retain hold timing, replace this decision with owned
unconditional success, and omit all recipient SP reads, prices and failure branches.
Visible-gauge reachability is unestablished here and outside this port's scope.

## 5. Helpers and owned implementation progress

Tier B: `0x28ce0` (site `0x28d00`) reads success, compares it to false, and branches
to the epilogue when false. Success true continues into spark handling. Brief A's
original prose inverted this guard; its C listing and fresh instructions agree.
`0x29760` is ATTACK3's shifted MAIN with success/lightning reads; `0x2ac80`
is HOLD's shifted MAIN and site `0x2ad40` names HOLD_FRAME, not SUCCESS_SP.
Setter location: `0x16db0 -> 0x1a230`, not these three readers.

Tier B native audit: Hero spark/lightning descriptors retain initializers
`main+0x85d580` / `main+0x85dad0`; these contain Hero owner status/work reads.
The measured clone source copies the descriptor callback even when donor Lua
code is disabled. Spark class callback `main+0x33cbb20` also reads Hero's decoded
parameter object at manager slot `+0x1298`. Foreign-owner safety is unverified.

The user authorized plugin-local hooks at `0x85d580`, `0x85dad0`, `0x33cbb20`
on 2026-09-30; additional hook sites remain reserved under AGENTS rule 17.
Tier B audit v1.1.0 traces lightning `exec_map_collection` from NRO call site
`0x45768` to main `0x33cabd0`; it reads owner flag `0x21000015`. An owned
weapon-script caller can use an owned replacement without adding an interception
for this call. This is not a complete class-callback coverage claim.
Source contains the 25-callback topology, allocation assertion, hold/attack EXEC,
native-checked S1/S2/S32 game ACMD and S3's frame-10 activation dispatch. It remains
disconnected; complete status loops, article scripts and resources are pending.
`tools/gen_hero_side_b_native.py --check` verifies complete relocated initializer,
spark constructor and lightning collision spans, including the owned spark PRC
field view. Three approved interception wrappers, scoped callbacks and independent
file logging are source only; Rust compilation and hardware behavior are unverified.
The article-list request is resolved: all 16 spark/lightning lists c00..c07 were
extracted with user authorization. Provenance: `article_motions/SOURCE.json` and
`article_motions/extraction.json`. `tools/build_hero_side_b_assets.py --check`
checks these and all 24 body clips, retaining 68/125 matched Transform tracks.
No build, package, installation or new hardware result is included.

## 6. Native ACMD measurement (tier B, 2026-09-30)

`tools/audit_hero_side_b_acmd.py` resolves 41 native side-B/regular registrations
in the pinned NRO (sha256
`dc5edcde314f0c461ba0ab08d9e9deef5ede9d5b4ed324141678b9966d43b7a2`).
Ground/air game S3 both resolve to `0x115590`: the complete body through its
return contains no direct ATTACK call and activates lightning at frame 10.
The earlier blanket claim that its zero ATTACK count was a dump artifact is
retracted. This fighter dispatch is not evidence that the lightning weapon has
no hitboxes; its scripts remain an essential dependency.
`tools/audit_hero_side_b_hitboxes.py` checks the native 36-argument ATTACK helper
and compares all branch argument multisets: S1=6, S2=1, S32=8. This comparison
validates values, not branch timing. `acmd_game.c`, `acmd_native_registrations.json`
and `hitbox_native_audit.json` record the measurement. Successful game ACMD source
omits the failed-SP branch and uses owned state without recipient Hero work IDs.

## 7. Native recipient event dependency (tier B, 2026-10-01)

`tools/audit_hero_side_b_link_events.py --check` reproduces the measurement in
`link_event_native_audit.{json,asm.txt}` against main SHA256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.
Lightning's native class callback `0x33caa70` (pointer slot `0x51b1800`)
sends event `0x214e64eedd` through LinkModule. Hero's fighter receiver
`0x8555a0`, class +0x170, recognizes it and enters `0x85593c`: it accesses
Hero article slot 2 and conditionally calls helper `0x851ac0`.
Mythra's receiver `0xa2a000` has different event comparisons. The measured
lightning event follows its unmatched return path `0xa2a214`, returning 1.
Offline controls verify that the lightning kind misses those comparisons and
Mythra's own `0x21f012fc72` matches. These are static dispatch controls, not
hardware results or evidence about the helper's complete runtime effects.

The three approved initialization/constructor interception sites do not cover
this engine callback/recipient route. Proposed additional reserved interception:
Mythra fighter class +0x170, pointer slot `main+0x4fb2110`, original function
`main+0xa2a000`. A gated wrapper would translate required donor event payloads
into owned state and allocated article slots, retain original handling for
unrelated events, verify signatures and log failures. Full event payload and
helper translation remains implementation work after approval. No fourth
interception has been implemented. Rule 17 requires hand-back before proceeding.
