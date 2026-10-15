# P4-STAT-SITES - for every stat candidate, the code sites that request it and the slot they call

Task: `P4-STAT-SITES`. Worker: Space Bunny Alpha. Date: 2026-10-05.
Prompt: `prompts/P4-STAT-SITES.md`. Coordinator review:
`research/COORDINATOR-2026-10-04.md`.

**One question.** For each of the 12 stat candidates recorded in
`evidence/P1-DATASET/gunner_catalog.json`, which code sites in the 13.0.4
executable build that Hash40, and what does each site call afterwards?

**This is a locating report.** It names no function purpose, connects no site to
a fighter kind or to a Mii, states no value range, and says nothing about when
any site runs or how often. No ranking of the candidates and no
recommendation about which to make editable appear anywhere here.

Evidence tiers: **B** offline measurement of a local file; **C** pinned external
source (used only to compare the `0x270` operand with a number); **D**
hypothesis. **No tier A.** No emulator, no console, no game run.

## Input

| item | value |
|---|---|
| file | `gamedata/ssbu-13.0.4/main.bin` (workspace-relative) |
| sha256 (rehashed at the start of this task) | `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` |
| expected sha256 (from the prompt) | `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` |
| size | 86672752 bytes |
| layout | flat decompressed NSO, address == file offset |
| code range scanned | `0x100` .. `0x39C8000` |
| catalogue | `evidence/P1-DATASET/gunner_catalog.json`, key `stat_candidates` |
| disassembler | `d.py`, copied from `scratch/2026-10-04_P1-ID-REVIEW/` |
| capstone | 5.0.7, via `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python` |

**Hash matched, so the task was not BLOCKED.** `check_stat_sites.py` rehashes
the file on every run and exits nonzero on a mismatch.

## Commands

```
sha256sum gamedata/ssbu-13.0.4/main.bin
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-04_P4-STAT-SITES/scan_all.py validate
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-04_P4-STAT-SITES/scan_all.py scan
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/evidence/P4-STAT-SITES/check_stat_sites.py
```

`python` (3.12.3) throughout. `stat_reads.py`, `report.py` and `d.py` were
copied from `scratch/2026-10-04_P2-STAT-READS/` into this task's scratch
folder; the copies are byte-identical to the originals (sha256 below) and the
originals were not edited.

| file | sha256 (original = copy) |
|---|---|
| `stat_reads.py` | `28126c1bb703ecc7f79b7cc71b32d24db6b711c00bbb5f781b4dc01d44fd9a6d` |
| `report.py` | `983338dce1c03f8eafaf0a4f181eb31abcdede4979c4ffba32141c95ba69949c` |
| `d.py` | `ea3a8a67077f2f6a6f2ff1c78dd51b3c1af55b125139497d90d5d7cc3cdf3544` |

The survey itself is `scratch/2026-10-04_P4-STAT-SITES/scan_all.py`, which
imports the copied `stat_reads.py` for the scanner and adds the 12-hash survey
and the call classification.

## 1. The candidates

The catalogue's `stat_candidates` list holds **12** entries. All 12 are
surveyed; none was added, none dropped, none merged. Name, Hash40 and
`decoded_type` are taken exactly as recorded, and `type_matches` is `true` for
all 12 in the catalogue.

| # | stat_id | parameter_name | hash | decoded_type |
|---|---|---|---|---|
| 1 | stat_weight | `weight` | `0x0607cd5541` | float |
| 2 | stat_scale | `scale` | `0x05ec462584` | float |
| 3 | stat_walk_speed_max | `walk_speed_max` | `0x0ee2ec2860` | float |
| 4 | stat_run_speed_max | `run_speed_max` | `0x0d5aaabf9b` | float |
| 5 | stat_dash_speed | `dash_speed` | `0x0adec47ea3` | float |
| 6 | stat_air_speed_x_stable | `air_speed_x_stable` | `0x1220fc2660` | float |
| 7 | stat_air_speed_y_stable | `air_speed_y_stable` | `0x12ec5626fe` | float |
| 8 | stat_air_accel_y | `air_accel_y` | `0x0ba18057d9` | float |
| 9 | stat_air_accel_x_mul | `air_accel_x_mul` | `0x0f71f4d4f8` | float |
| 10 | stat_jump_y | `jump_y` | `0x06a0d82dad` | float |
| 11 | stat_jump_speed_x | `jump_speed_x` | `0x0cc9d2f2da` | float |
| 12 | stat_jump_count_max | `jump_count_max` | `0x0e35ca3d82` | i32 |

All 12 hashes are distinct, and all twelve are below `2^40`, so all twelve are
representable by the two 16-bit halves a `movz` + two `movk` build supplies.

### Controls

`weight` and `walk_speed_max` are in this list as controls. The survey
reproduces `research/P2-STAT-READS.md` exactly for both:

| stat | P2-STAT-READS code sites | this survey |
|---|---|---|
| `weight` | 37 | **37** (same 37 addresses, same order) |
| `walk_speed_max` | 18 | **18** (same 18 addresses, same order) |

The control did not fail, so the survey continued. The per-site first-call
classification also matches P2's table for every site P2 listed: 14 `weight`
and 6 `walk_speed_max` sites that P2 recorded as `blr` with producer
`ldr x8, [x8, #0x270]` are the same 14 and 6 here.

## 2. Method

Exactly the P2-STAT-READS method, unchanged:

* **Code sites.** A 40-bit constant is composed by `movz` (or `mov`) plus one
  or two `movk` on the same register. Accepted forms: `MOVZ` 64 `0xD2800000`,
  `MOVK` 64 `0xF2800000`, `MOVZ` 32 `0x52800000`, `MOVK` 32 `0x72800000`. A
  sequence is accepted when the composing instructions are adjacent or
  separated by at most **4** instructions, none of which writes the carrying
  register; a `bl`/`blr` counts as writing `x0`-`x18`, so no sequence spans a
  call. The site address is the `movz` seed, not the completing `movk`.
* **Data sites.** Raw 8-byte little-endian match at any offset, plus the
  low-40-bits match at 8-byte alignment.
* **What follows.** The first `bl` or `blr` at or after the completing `movk`,
  within **0x400 bytes** (`start = complete + 4`, `limit = start + 0x400`) -
  P2's span, so the "first call" column is comparable with P2's.
* **Classification.** `blr xN` with `xN` produced by `ldr xN,[xM,#D]` or
  `ldur xN,[xM,#D]` within the preceding **20** instructions (P2's producer
  lookback) is class `indirect` and its displacement `D` is recorded.
  `blr` whose producer is anything else is class `indirect_other_producer` or
  `indirect_no_producer`. `bl` is class `direct_bl` and its computed target is
  recorded. No call in the span is class `none`.
* **Extra observations requested by the prompt.** For indirect sites: whether
  the base register `xM` was itself produced by `ldr xM,[x0]` within the
  preceding **12** instructions and whether `x0` was then loaded by an
  `ldr x0,[x?,#0x50]` within 12 instructions of that; and the value moved into
  `x2` before the call when the closest `x2`-writing instruction within 8
  instructions moves an immediate. `mov x2, xzr` is encoded `orr x2, xzr, xzr`
  and is reported as the immediate 0.

**Validation.** `scan_all.py validate` re-runs the copied scanner's own
self-test: **33 checks, all pass, exit 0** (planted adjacent, gap-3, gap-4 and
interleaved-other-register positives for both control hashes, plus the
overwrite-between and gap-too-large negatives, plus three assertions that
`dest_regs` really reports writers so the negatives cannot pass vacuously).

**Two scanners.** As in P2, a second independently written scanner
(`scan_sequences_strict` in the copied `stat_reads.py`) is run over the same
range for the same 12 targets. The two agree on **every** hash: identical
per-hash counts and identical address sets for all 12 (recorded as
`scanners_agree: true` for each candidate in `evidence/P4-STAT-SITES/sites.json`).

## 3. Overall table

| stat | type in the catalogue | sites total | sites via +0x270 | via +0x250 | via other displacement | direct `bl` | none |
|---|---|---|---|---|---|---|---|
| `weight` | `float` | 37 | 23 | 0 | 1 | 9 | 4 |
| `scale` | `float` | 306 | 13 | 0 | 6 | 249 | 38 |
| `walk_speed_max` | `float` | 18 | 6 | 0 | 0 | 8 | 4 |
| `run_speed_max` | `float` | 18 | 6 | 0 | 0 | 8 | 4 |
| `dash_speed` | `float` | 27 | 3 | 0 | 0 | 16 | 8 |
| `air_speed_x_stable` | `float` | 29 | 19 | 0 | 0 | 8 | 2 |
| `air_speed_y_stable` | `float` | 22 | 10 | 0 | 0 | 4 | 8 |
| `air_accel_y` | `float` | 102 | 28 | 0 | 1 | 15 | 56 |
| `air_accel_x_mul` | `float` | 22 | 7 | 0 | 0 | 9 | 6 |
| `jump_y` | `float` | 10 | 3 | 0 | 0 | 5 | 2 |
| `jump_speed_x` | `float` | 25 | 6 | 0 | 1 | 4 | 13 |
| `jump_count_max` | `i32` | 5 | 0 | 1 | 0 | 1 | 3 |

Reading the columns: "sites via +0x270" counts sites whose first call is an
indirect `blr` whose target register was loaded by `ldr xN,[xM,#0x270]`.
"via other displacement" counts indirect sites whose feeding `ldr` uses any
other displacement (and includes `indirect_other_producer` sites, whose
producer is not a `ldr` with a displacement at all). "direct `bl`" and "none"
are the non-indirect classes, so the six numbers sum to the total.

Data-site counts, same rules as P2:

| stat | data sites, raw 8-byte LE | data sites, low 40 bits at 8-byte alignment |
|---|---|---|
| `weight` | 0 | 0 |
| `scale` | 0 | 0 |
| `walk_speed_max` | 1 (`0x453d0e0`) | 1 (`0x453d0e0`) |
| `run_speed_max` | 1 (`0x453d1a8`) | 1 (`0x453d1a8`) |
| `dash_speed` | 1 (`0x453d130`) | 1 (`0x453d130`) |
| `air_speed_x_stable` | 1 (`0x453d220`) | 1 (`0x453d220`) |
| `air_speed_y_stable` | 1 (`0x453d298`) | 1 (`0x453d298`) |
| `air_accel_y` | 1 (`0x453d270`) | 1 (`0x453d270`) |
| `air_accel_x_mul` | 1 (`0x453d1d0`) | 1 (`0x453d1d0`) |
| `jump_y` | 0 | 0 |
| `jump_speed_x` | 1 (`0x453d2e8`) | 1 (`0x453d2e8`) |
| `jump_count_max` | 0 | 0 |

## 4. Displacements other than `0x270`

The prompt expected `0x250`, `0x260` and `0x270` and asked for whatever is
there. Across all 12 candidates, **137** sites are class `indirect` or
`indirect_other_producer`, and **134** of them are fed by a
displacement-bearing 64-bit `ldr`. Those 134 displacements are:

| displacement | sites | which candidates |
|---|---|---|
| `0x270` | 124 | all candidates except `jump_count_max` |
| `0x250` | 1 | `jump_count_max` (`0x622960`) |
| `0x260` | 0 | - |
| `0x130` | 1 | `air_accel_y` (`0x9dea84`) |
| `0x110` | 1 | `scale` (`0x664d5c`) |
| `0x108` | 1 | `jump_speed_x` (`0x13163a4`) |
| `0x98` | 2 | `scale` (`0x15b4e78`, `0x15b4eb8`) |
| `0xb0` | 2 | `scale` (`0x4730e4`, `0x474cf0`) |
| `0x50` | 1 | `scale` (`0x131c014`) |
| `0x20` | 1 | `weight` (`0x36d8c98`) |
| not a displacement-bearing 64-bit `ldr` | 3 | `air_accel_y` `0x6c3d64`, `0x6d21fc`, `jump_speed_x` `0x1124c0c` |

The last row is the three sites whose producer is not an `ldr` with a
displacement at all: `air_accel_y` `0x6c3d64` (producer
`ldr w8, [x22, #0x98]`, a 32-bit load), `air_accel_y` `0x6d21fc`
(producer `bl`) and `jump_speed_x` `0x1124c0c` (producer `blr x8`). The
displacement rows therefore sum to 134 and the three non-displacement sites
bring the indirect total to 137. No site in any candidate feeds the indirect
call through `0x260`.

The three displacement values P2-STAT-HOOKPOINT section 2.6 describes as
thunks (`0x4e5390..0x4e53fc`: `+0x250` -> `0x4e53a0`, `+0x260` -> `0x4e53c0`,
`+0x270` -> `0x4e53e0`) are compared here as **numbers only**. No vtable was
resolved, no slot was dereferenced, and no function identity is claimed. The
statement "`+0x250` is a number this image also uses in one site" is a numeric
coincidence observation (B for the operand, C for the declaration), nothing
more.

## 5. The `[x0]` / `#0x50` chain and the `x2` argument

Per candidate, over its indirect sites:

| stat | indirect sites | base register came from `ldr xM,[x0]` | and `x0` also loaded by displacement `#0x50` | `x2` immediate `0` before the call | `x2` register move | no `x2` write within 8 instructions |
|---|---|---|---|---|---|---|
| `weight` | 24 | 23 | 22 | 23 | 0 | 1 |
| `scale` | 19 | 11 | 9 | 7 | 6 | 6 |
| `walk_speed_max` | 6 | 0 | 0 | 5 | 1 | 0 |
| `run_speed_max` | 6 | 1 | 1 | 6 | 0 | 0 |
| `dash_speed` | 3 | 2 | 2 | 3 | 0 | 0 |
| `air_speed_x_stable` | 19 | 5 | 5 | 19 | 0 | 0 |
| `air_speed_y_stable` | 10 | 2 | 2 | 9 | 0 | 1 |
| `air_accel_y` | 31 | 6 | 5 | 28 | 3 | 0 |
| `air_accel_x_mul` | 7 | 0 | 0 | 7 | 0 | 0 |
| `jump_y` | 3 | 1 | 0 | 3 | 0 | 0 |
| `jump_speed_x` | 8 | 0 | 0 | 5 | 2 | 1 |
| `jump_count_max` | 1 | 0 | 0 | 1 | 0 | 0 |

For `weight` the chain holds at 22 of its 23 `0x270` sites. For every other
candidate it holds at fewer than half of its `0x270` sites, and for five
candidates (`walk_speed_max`, `air_accel_x_mul`, `jump_speed_x`,
`jump_count_max`, and `jump_y`) it never holds, even though one `jump_y`
indirect site does load its base register with `ldr xM,[x0]`. This is a
statement about the shape of the preceding 12 instructions, nothing about what
object is being addressed.

## 6. Per-stat tables

Every site named here has its address in
`evidence/P4-STAT-SITES/sites.json` (`stats.<name>.sites[].site`, plus
`complete`, `call`, `producer`, `from_x0_chain`, `x2_immediate`). Counts only
are reproduced below.

### weight

hash `0x0607cd5541`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 9 |
| `indirect` | 24 |
| `none` | 4 |
| **total** | **37** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 23 |
| `0x20` | 1 (`0x36d8c98`) |
| no indirect class (direct `bl` or no call) | 13 |

data: raw 8-byte LE 0; low-40-bits 8-byte aligned 0.

### scale

hash `0x05ec462584`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 249 |
| `indirect` | 19 |
| `none` | 38 |
| **total** | **306** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 13 |
| `0x110` | 1 (`0x664d5c`) |
| `0x98` | 2 (`0x15b4e78`, `0x15b4eb8`) |
| `0xb0` | 2 (`0x4730e4`, `0x474cf0`) |
| `0x50` | 1 (`0x131c014`) |
| no indirect class (direct `bl` or no call) | 287 |

data: raw 8-byte LE 0; low-40-bits 8-byte aligned 0.

### walk_speed_max

hash `0x0ee2ec2860`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 8 |
| `indirect` | 6 |
| `none` | 4 |
| **total** | **18** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 6 |
| no indirect class (direct `bl` or no call) | 12 |

data: 1 raw 8-byte LE hit at `0x453d0e0`, also the single aligned hit.

### run_speed_max

hash `0x0d5aaabf9b`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 8 |
| `indirect` | 6 |
| `none` | 4 |
| **total** | **18** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 6 |
| no indirect class (direct `bl` or no call) | 12 |

data: 1 raw hit at `0x453d1a8`, also the single aligned hit.

### dash_speed

hash `0x0adec47ea3`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 16 |
| `indirect` | 3 |
| `none` | 8 |
| **total** | **27** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 3 |
| no indirect class (direct `bl` or no call) | 24 |

data: 1 raw hit at `0x453d130`, also the single aligned hit.

### air_speed_x_stable

hash `0x1220fc2660`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 8 |
| `indirect` | 19 |
| `none` | 2 |
| **total** | **29** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 19 |
| no indirect class (direct `bl` or no call) | 10 |

data: 1 raw hit at `0x453d220`, also the single aligned hit.

### air_speed_y_stable

hash `0x12ec5626fe`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 4 |
| `indirect` | 10 |
| `none` | 8 |
| **total** | **22** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 10 |
| no indirect class (direct `bl` or no call) | 12 |

data: 1 raw hit at `0x453d298`, also the single aligned hit.

### air_accel_y

hash `0x0ba18057d9`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 15 |
| `indirect` | 29 |
| `indirect_other_producer` | 2 |
| `none` | 56 |
| **total** | **102** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 28 |
| `0x130` | 1 (`0x9dea84`) |
| producer not a displacement-bearing 64-bit `ldr` | 2 (`0x6c3d64`, `0x6d21fc`) |
| no indirect class (direct `bl` or no call) | 71 |

data: 1 raw hit at `0x453d270`, also the single aligned hit.

### air_accel_x_mul

hash `0x0f71f4d4f8`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 9 |
| `indirect` | 7 |
| `none` | 6 |
| **total** | **22** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 7 |
| no indirect class (direct `bl` or no call) | 15 |

data: 1 raw hit at `0x453d1d0`, also the single aligned hit.

### jump_y

hash `0x06a0d82dad`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 5 |
| `indirect` | 3 |
| `none` | 2 |
| **total** | **10** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 3 |
| no indirect class (direct `bl` or no call) | 7 |

data: raw 8-byte LE 0; low-40-bits 8-byte aligned 0.

### jump_speed_x

hash `0x0cc9d2f2da`, catalogue type `float`

| class | count |
|---|---|
| `direct_bl` | 4 |
| `indirect` | 7 |
| `indirect_other_producer` | 1 |
| `none` | 13 |
| **total** | **25** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x270` | 6 |
| `0x108` | 1 (`0x13163a4`) |
| producer not a displacement-bearing 64-bit `ldr` | 1 (`0x1124c0c`) |
| no indirect class (direct `bl` or no call) | 17 |

data: 1 raw hit at `0x453d2e8`, also the single aligned hit.

### jump_count_max

hash `0x0e35ca3d82`, catalogue type `i32`

| class | count |
|---|---|
| `direct_bl` | 1 |
| `indirect` | 1 |
| `none` | 3 |
| **total** | **5** |

| feeding `ldr` displacement | sites |
|---|---|
| `0x250` | 1 (`0x622960`) |
| no indirect class (direct `bl` or no call) | 4 |

This is the only candidate with **no** `0x270` site at all.

data: raw 8-byte LE 0; low-40-bits 8-byte aligned 0.

## 7. Candidates with zero code sites

**None.** All 12 candidates have at least one `movz`/`movk` code site; the
smallest is `jump_count_max` with 5. The zero-code-site case in step 5 of the
prompt therefore does not arise and no speculation about an unread candidate is
offered.

For completeness, the candidates whose hash has **no** data occurrence at all
(0 raw, 0 aligned) are `weight`, `scale`, `jump_y` and `jump_count_max`. For the
other eight the single aligned hit listed in section 3 is the only occurrence,
and in every case it is the same value as the raw hit (top 24 bits zero). The
eight aligned hits sit between `0x453d0e0` and `0x453d2e8`. **The region is not
interpreted here**, per the prompt; no claim is made about what those qwords
are.

## 8. Five example windows

Chosen to cover the distinct shapes. Full 12-before / 20-after text for each,
plus every distinct (class, displacement) pair found anywhere, is in
`evidence/P4-STAT-SITES/win_*.txt` (12 files) with the index in
`evidence/P4-STAT-SITES/examples.json`.

### 8.1 `weight` at `0x0069d018` - indirect, `0x270`, `x2 = 0`

```
[15 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
```

This is the shape the tier-A console log showed for `weight`, at a site P2 did
not list. The base register `x8` here was not produced by `ldr xM,[x0]` inside
12 instructions, so this site is **not** in the `+0x50` chain count.

### 8.2 `jump_count_max` at `0x00622960` - indirect, `0x250`, `x2 = 0`

```
[14 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
```

The only `0x250` site in the whole survey. The neighbouring calls in this
function use `0xa0`. Recorded as a displacement; no identity is claimed.

### 8.3 `weight` at `0x036d8c98` - indirect, `0x20`

```
0x036d8c88: str      x19, [sp, #0x48]
0x036d8c8c: mov      x8, xzr
0x036d8c90: tbnz     w21, #0x1f, #0x36d8eac
0x036d8c94: and      w9, w9, #0xff
0x036d8c98: mov      x18, #0x5541           <- site: hash seed, in x18 not x1
...
0x036d8ca4: movk     x18, #0x7cd, lsl #16
```

Producer for this site's first call is `ldr x8, [x8, #0x20]` at `0x36d8cac`,
itself from `ldr x8, [x0]` at `0x36d8ca8`; `x0` was **not** loaded by
displacement `0x50` within 12 instructions, so this site is outside the chain
count. The hash is built in `x18`, not in an argument register.

### 8.4 `air_accel_y` at `0x006c3d64` - `blr` whose producer is not a displacement `ldr`

```
0x006c3d40: ldr      w8, [x22, #0x98]      <- producer, 32-bit load
0x006c3d44: ldr      x26, [sp, #0x18]
0x006c3d48: cbz      w8, #0x6c395c
0x006c3d4c: str      w8, [sp, #0xa0]
...
0x006c3d64: mov      x1, #0x57d9            <- site: hash seed
0x006c3d68: movk     x1, #0xba18, lsl #16
0x006c3d6c: movk     x1, #0x0, lsl #32      <- completes 0x0ba18057d9
0x006c3d70: mov      x2, xzr
0x006c3d78: blr      x8
```

Classified `indirect_other_producer`: the register the `blr` uses was last
written by `ldr w8, [x22, #0x98]`, a 32-bit load, so there is no 64-bit slot
displacement to report. Recorded, not interpreted.

### 8.5 `scale` at `0x0131c014` - indirect, `0x50`

```
0x0131c004: add      x0, x8, #8
0x0131c008: bl       #0x7a4740
0x0131c00c: stp      x0, x1, [sp, #0xb0]
0x0131c010: ldr      x8, [x0, #0x50]        <- producer of the call register
0x0131c014: mov      x1, #0x2584            <- site: hash seed
0x0131c018: movk     x1, #0x888f, lsl #16
0x0131c01c: movk     x1, #0x13, lsl #32     <- completes 0x05ec462584
0x0131c020: ...
0x0131c024: blr      x8                    <- first call in the span
```

The `0x50` here is the base register's displacement in `ldr x8, [x0, #0x50]`,
not a vtable slot offset: the base is `x0`, not a vtable pointer reached through
`ldr xN,[xM]`. This is why the `+0x50` chain test in section 5 requires
`ldr xM,[x0]` with the *slot* displacement taken from a *further* base, and why
this site is not counted as a chain site. The `0x50` value appearing here is
recorded as a displacement only.

## 9. Limitations

1. **No runtime claim.** Nothing here says when any site executes, how often,
   whether the result is cached, or whether the same call site serves every
   fighter. The tier-A console log in `evidence/2026-10-04_gate1/RESULT.md`
   covers `weight` and `walk_speed_max` only, and only for the sites the log
   recorded; this survey adds no runtime evidence.
2. **`movz`/`movk` builds only.** A hash reached by `orr`/`add` of two
   immediates, or loaded from one of the eight data qwords, would not appear as
   a code site. For the four candidates with no data occurrence (`weight`,
   `scale`, `jump_y`, `jump_count_max`) a non-`movz`/`movk` code path cannot be
   excluded by this method.
3. **Window limits.** "First call" searches from the instruction after the
   completing `movk` through a fixed 0x400-byte span. Class `none` means no
   `bl`/`blr` was found in that span, not that none exists later. The x2
   lookback is 8 instructions and the `[x0]`/`#0x50` lookback is 12; a chain
   that crosses a longer distance is not seen.
4. **Displacements are numbers.** `0x270`, `0x250` and `0x260` are compared with
   numbers in P2-STAT-HOOKPOINT (C) and with nothing in the image. No vtable
   was resolved and no slot was dereferenced, so "via +0x270" means "the
   feeding instruction's displacement operand is 0x270", nothing more.
5. **Two scanners, one rule.** The primary and strict scanners agree on all 12
   hashes and `check_stat_sites.py` adds a third, independently shaped
   dataflow scanner that agrees on the two controls. All three encode the same
   gap rule, so they cannot jointly disprove the rule itself.
6. **The 306 `scale` sites dominate the totals** and most of them are class
   `direct_bl` or `none`. That is a count of shapes, not a measure of
   importance, and no importance is claimed.
7. **Nothing is named.** No function purpose, no fighter kind, no Mii
   connection, no value range, and no statement about what any of these
   parameters means is made anywhere in this report.
8. **`scale` has 6 `0x270` sites with the same feeding displacement but 11
   `ldr xM,[x0]` bases among 19 indirect sites**, i.e. the chain test does not
   partition its indirect sites cleanly. The three tests (class, displacement,
   chain) are reported independently and should not be multiplied together.

## 10. Next experiment

Offline, and the smallest one that says something the classification cannot:

> Take the one `0x250` site, `jump_count_max` at `0x622960`, and the one `0x270`
> site of the same candidate if any appears with a wider span, and re-run the
> first-call search for both with the span raised from 0x400 to 0x4000 bytes.
> If the counts of `direct_bl` / `none` sites drop materially, then the "none"
> column in section 3 is an artefact of P2's 0x400 window rather than a shape,
> and the survey's class table should be restated with the wider span. If they
> do not, the classes are stable under a ten-times wider window. Either answer
> is offline: it reads the image, it does not run it.

A second offline option, if a reader wants the direct-`bl` targets resolved
rather than counted: the most frequent `bl` targets across the twelve candidates
are `0x39c0d80` (249 sites' worth, dominated by `scale`), `0x75d8f0` and
`0x392dce0`/`0x392e590`. Disassembling those three targets and recording their
first 8 instructions would say what shape of code consumes the hash, still
without naming a purpose.

## Evidence index

| file | what |
|---|---|
| `evidence/P4-STAT-SITES/check_stat_sites.py` | re-derives every count, address, class, displacement, chain flag and x2 value from the image and compares them with `sites.json` and with the report tables; nonzero on mismatch |
| `evidence/P4-STAT-SITES/sites.json` | full machine-readable per-site list for all 12 candidates |
| `evidence/P4-STAT-SITES/examples.json` | index of the example window files |
| `evidence/P4-STAT-SITES/win_*.txt` | 12 raw 12-before / 20-after windows, one per distinct (class, displacement) pair |
| `evidence/P4-STAT-SITES/scan_raw.txt` | raw scan output (counts, per-hash displacement histogram, timings) |
| `scratch/2026-10-04_P4-STAT-SITES/scan_all.py` | the survey; imports the copied scanner |
| `scratch/2026-10-04_P4-STAT-SITES/stat_reads.py` | byte-identical copy of the P2 scanner |
| `scratch/2026-10-04_P4-STAT-SITES/report.py` | byte-identical copy of the P2 report generator (unused by this task) |
| `scratch/2026-10-04_P4-STAT-SITES/d.py` | byte-identical copy of the P1-ID-REVIEW disassembler |
| `scratch/2026-10-04_P4-STAT-SITES/patch_examples.py` | one-off patcher that inserted the window-writing block into `scan_all.py` |

## Summary

Task `P4-STAT-SITES` - **DONE**.

Changed files, all inside `mods/mii_customizer/`; no other worker's file, no
commit, no branch, no emulator, no SD access, no framework change:

* `research/P4-STAT-SITES.md` (this file, new)
* `evidence/P4-STAT-SITES/` (new: `check_stat_sites.py`, `sites.json`,
  `examples.json`, 12 `win_*.txt`, `scan_raw.txt`)
* `scratch/2026-10-04_P4-STAT-SITES/` (new: `scan_all.py`,
  `patch_examples.py`, and the three copies)

Inputs stayed read-only; `gamedata/ssbu-13.0.4/main.bin` was rehashed and
matched.

Observed checks:

* `scan_all.py validate` - **33/33 pass, exit 0**.
* `scan_all.py scan` - primary and strict scanners agree on **all 12** hashes
  (counts and address sets); 621 code sites in total. Image load 0.0 s, primary
  scan 17.6 s, strict scan 6.9 s, exit 0. Three failures were found and fixed
  during this task, all by the check script rather than by reading the code:
  the first run's dataflow cross-check reported completing `movk` addresses
  instead of seed addresses; the section 5 chain counts for `air_accel_y` and
  `jump_y` were wrong in the report draft (6 and 1, not 5 and 0); and the
  section 4 totals counted 154 indirect sites instead of 137. All three are
  corrected above and the check now fails if any of them reappears.
* `evidence/P4-STAT-SITES/check_stat_sites.py` - **3327 passed, 0 failed,
  exit 0, 93 s wall clock** (log: `evidence/P4-STAT-SITES/check_raw.txt`).
  It rehashes the input, re-derives every site with a third scanner written in
  a different shape (a forward per-register dataflow instead of a per-seed
  extension), re-derives every classification and data-site count, checks that
  each producer instruction really carries the reported displacement and each
  `direct_bl` really branches to the reported target, and compares the report's
  overall, section-5 and section-6 tables against the derivation so the prose
  cannot drift. It also asserts that the report contains no ranking or
  recommendation wording outside an explicit disclaimer.
* **Negative test of the check itself (B).** One count in this report's overall
  table was deliberately changed (`jump_count_max`, none 3 -> 4), the check was
  rerun, and it reported `FAIL overall row jump_count_max counts [5, 0, 1, 0,
  1, 4]`, 3326 passed / 1 failed, **exit 1**; the report was then restored to
  sha256 `167a53a5cd7daf0f3ddd2a9293e337b74ef3169aa674a97c4046107986349598`
  and the passing run above re-confirmed. The nonzero exit required by the
  prompt is therefore observed, not assumed.

Unresolved questions left for the next reader: whether the class `none` column
survives a wider first-call span; what the eight data qwords between `0x453d0e0`
and `0x453d2e8` are; whether the eight displacement values other than `0x270`
that occur anywhere in the survey (`0x250`, `0x130`, `0x110`, `0x108`, `0x98`,
`0xb0`, `0x50`, `0x20`, ten sites in total) correspond to anything the project
has already named; and why `scale` has 306
code sites when no other candidate exceeds 102. Nothing here indicates which
candidates should be made editable, and no such ranking is offered.