# P11-INT-PARAMS - integer fighter parameters through the +0x250 getter (facts only)

Task `P11-INT-PARAMS` (continued by `P12-INT-PARAMS`). Worker: Space Bunny Alpha.
Prompt: `prompts/P11-INT-PARAMS.md`, continued per `prompts/P12-INT-PARAMS.md`.
Dates: 2026-10-06 (previous worker, stopped), 2026-10-07 (this worker).

> **Coordinator note, 2026-10-07: this task STOPPED WITHOUT A REPORT.** Nothing below was
> filled in and `evidence/P11-INT-PARAMS/` is empty (no check script). Left behind and
> **unreviewed**: scripts in `scratch/2026-10-06_P11-INT-PARAMS/` and tables under workspace
> `gamedata/mii_customizer/P11-INT-PARAMS/` (`int_table.md`, `sites250.md`,
> `others_table.md` + JSON). Those tables say, unverified: of the i32 fields only a handful
> have a +0x250 call site (`jump_count_max` at `0x622960` with x2 = 0 among them). No
> answer exists for Q1 and Q3. The work is continued by `prompts/P12-INT-PARAMS.md`, which
> writes its result into this file.
>
> **Coordinator review, 2026-10-07 (later):** P12-INT-PARAMS finished this report. Check
> rerun with the disassembler path set: 558 checks, 0 failures, exit 0 (without
> `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python` it stops on `import capstone`).
> Result used by the coordinator: slot +0x250 is the 4-instruction thunk `0x4e53a0`
> (`f9401c00 f9400008 f9401103 d61f0060`, no PC-relative word), the integer twin of the
> hooked `0x4e53e0`; six integer fields qualify, of which `jump_count_max` is the one a
> player would notice (2 for 85 fighters; 3 buddy, plizardon, ridley; 4 pit, pitb; 5 dedede;
> 6 kirby, metaknight, purin) and it depends on jump motions a Gunner may not have.
>
> **Coordinator note, 2026-10-07 (P12-INT-PARAMS):** continued by the P12-INT-PARAMS
> worker as instructed; the banner above is the coordinator's and is kept as written.

**Offline static analysis only.** Nothing is executed or patched. No hook code.
Evidence tiers: **B** = offline measurement of the local image (and of what the
check script re-reads); **D** = hypothesis/runtime behaviour, marked as such.
No tier A is produced here; the console facts quoted in the background come
from earlier gates and are cited to their reports.

## Short answers

> **Status of this section:** Q2 and Q4 were first written here from the previous
> worker's left-over tables (marked unverified), then **reproduced by this worker on
> 2026-10-07**: the scanners were copied into `scratch/2026-10-07_P12-INT-PARAMS/`,
> validated against P4's controls, rerun, and the regenerated tables are byte-identical
> to the left-over ones (see "Verification record" V2-V3 below).
> **Q2 and Q4 are VERIFIED (B).** Q1 was answered fresh by this worker; Q3 was not
> answered by the previous worker at all.

### Q1 - slot +0x250 of vtable 0x4f89490

**Verified (B)** - reproduced by `scratch/2026-10-07_P12-INT-PARAMS/q1_slot.py`
(image `gamedata/ssbu-13.0.4/main.bin`, sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`,
86 672 752 bytes; 306 167 RELA records parsed).

**The slot.** `[0x4f89490 + 0x250]` is a relocated pointer (RELA record at file
address `0x4f896e0`) whose addend is **`0x4e53a0`**. Neighbouring slots:

| slot | fn | slot | fn |
|---|---|---|---|
| +0x240 | `0x4e5380` (body: `ret`) | +0x260 | `0x4e53c0` |
| +0x248 | `0x4e5390` | +0x268 | `0x4e53d0` |
| +0x250 | **`0x4e53a0`** | +0x270 | `0x4e53e0` |
| +0x258 | `0x4e53b0` | +0x278 | `0x4e53f0` |

**Full disassembly of `0x4e53a0`** (the whole function - four instructions,
next function `0x4e53b0`, previous word `0x4e539c` is `udf #0`, 16-byte aligned):

```
0x004e53a0: f9401c00  ldr  x0, [x0, #0x38]
0x004e53a4: f9400008  ldr  x8, [x0]
0x004e53a8: f9401103  ldr  x3, [x8, #0x20]
0x004e53ac: d61f0060  br   x3
```

First four words: **`f9401c00 f9400008 f9401103 d61f0060`**. **No
PC-relative instruction among them** (checked: adrp, b/bl, b.cond, ldr
literal - none match; the only control transfer is `br x3`, a register branch).

**What it forwards to.** Compare `0x4e53e0` (slot +0x270), body
`ldr x0,[x0,#0x38]; ldr x8,[x0]; ldr x3,[x8,#0x30]; br x3` (words
`f9401c00 f9400008 f9401903 d61f0060`). The two thunks are identical except
for the inner slot: **`0x4e53a0` dispatches slot `+0x20` of the object at
`[x0 + 0x38]`, where `0x4e53e0` dispatches slot `+0x30` of the object at the
same `[x0 + 0x38]`.** (P4-OVERRIDE-SLICE confirmed the same pattern for
`0x4e53f0` -> `+0x38`.)

**Argument and return registers.** The thunk writes only `x0`, `x8`, `x3`:
x1 (field hash) and x2 (selector) are forwarded unchanged; `x0` on entry is
the accessor object and is *replaced* by `[x0 + 0x38]` before the tail
branch, so the inner function sees `x0` = that member object. The thunk
itself returns whatever the inner function returns. The consumers at the
+0x250 call sites read **`w0`** as a 32-bit integer after the call
(`mov w1, w0` @`0x622980`, `cmp w20, w0` @`0x6ca678`, `cmp w0, #1`
@`0x34e5690`, `str w0, [sp, #0x34]` @`0x62bff8`, `mov w25, w0`
@`0xf07954`) - that is the usage (B); the inner `+0x20` implementation and
its own return-register discipline are not disassembled here (unverified).

**Which other slots re-dispatch into it.** In the thunk block `0x4e5380..0x4e53fc`
only one slot reaches +0x250: **slot +0x248** (`0x4e5390`):

```
0x004e5390: ldr  x8, [x0]
0x004e5394: ldr  x3, [x8, #0x250]
0x004e5398: br   x3
```

i.e. `+0x248` re-dispatches into the object's own slot `+0x250` - the exact
analogue of `+0x268` (`0x4e53d0`) re-dispatching into `+0x270` (`0x4e53e0`).
None of `+0x258`, `+0x260`, `+0x268`, `+0x270`, `+0x278` branches into
`0x4e53a0`: `+0x258` (`0x4e53b0`) re-dispatches the object's own `+0x260`,
`+0x260` (`0x4e53c0`) forwards `[x0+0x38]` -> inner `+0x28`, `+0x268` ->
object `+0x270`, `+0x270` -> inner `+0x30`, `+0x278` (`0x4e53f0`) -> inner
`+0x38`; `+0x240` is a bare `ret`. Across all of `.text` there are **24**
`ldr xN,[xM,#0x250]` sites with a `br xN` within 2 instructions (listed by
`q1_slot.py`); the only one inside this vtable's thunk block is `0x4e5394`,
the rest are other dispatchers that reach whichever object's `+0x250` it
holds - none is a direct branch into `0x4e53a0` (no `b`/`bl` targets it;
verified with `d.py calls 0x4e53a0` - no output - and re-read by the check
as `q1.direct_branches_4e53a0 == 0`).

**Same function in other classes' vtables.** Exactly **two** relocated
qwords in the whole image hold `0x4e53a0`: `0x4f896e0` = vtable
`0x4f89490 + 0x250` and `0x4f73988` = vtable `0x4f73738 + 0x250`. Both sit at
`+0x250` of qualifying vtable runs (>= 0x288 bytes of contiguous stride-8
code pointers; 928 such runs in the image). The same two vtables are the
two that hold `0x4e53e0` at `+0x270`. P2-STAT-HOOKPOINT section 2.6 had
already shown these two vtables share their **entire** `+0x248..+0x278`
block (its table at line 441/442 lists identical functions for both).
So a hook on `0x4e53a0` is seen by both classes, exactly like the existing
`0x4e53e0` hook: Mii-fighter relevance comes from the tier-A gate-2 fact
(vtable `0x4f89490` confirmed for Mii fighters) plus the one engine call
site `jump_count_max` uses (`0x622960`); whether any object of class
`0x4f73738` is a fighter is **not established** (D - identity of that class
remains open, see P4-OVERRIDE-SLICE failure pattern `st=vt`).

### Q2 - integer (i32) fighter_param fields with +0x250 sites

**Unverified at first draft, left by the previous worker; VERIFIED (B) by this worker
2026-10-07.** Source: `gamedata/mii_customizer/P11-INT-PARAMS/int_table.md` /
`int_table.json`, `sites250.md`, `sites_int.json` (all six files regenerated and
diffed - see the verification record below).

Of the 25 i32 fields in the table, seven have at least one +0x250 call site
(the eight sites listed in `sites250.md`), and six of those qualify for a
preset by the float rule (integer, at least one +0x250 site with x2 == 0,
value differs between fighters):

| field | hash | sites | +0x250 sites | x2 at the +0x250 site(s) | Mii Gunner | min | max | distinct | qualifies |
|---|---|---|---|---|---|---|---|---|---|
| jump_count_max | `0x0e35ca3d82` | 5 | 1 | `0x622960`: imm 0 | 2 | 2 | 6 | 5 | yes |
| attack_lw3_rebound_count | `0x1800b91901` | 4 | 1 | `0x6ca664`: imm 0 | 3 | 0 | 6 | 4 | yes |
| attack_100_rebound_count | `0x189aea226c` | 3 | 1 | `0x34e567c`: imm 0 | 5 | 2 | 10 | 5 | yes |
| scroll_rate_change_frame | `0x18cde09792` | 3 | 1 | `0x62bfb4`: imm 0 | 30 | 1 | 30 | 2 | yes |
| pickel_capture_fence_type | `0x19327d6d0a` | 5 | 2 | `0xf0792c`, `0xf15620`: imm 0 | 0 | 0 | 1 | 2 | yes |
| (unlabelled) | `0x19f190006a` | 2 | 1 | `0x33f084c`: imm 0 | 5 | 0 | 5 | 2 | yes |

One more i32 field has a +0x250 site but does not qualify (x2 is not an immediate 0):
`final_start_turn_frame` (`0x163fab98bf`, site `0x62e9fc`, x2 written by
`movk x2, #0x17, lsl #32`). The remaining 18 i32 fields have no +0x250 site
(`s4_combo_max`, `s3_combo_max`, `lw4_combo_max`, `jump_squat_frame`, `attack_combo_max`,
`star_attack_power`, `dead_rare_se_rate`, `landing_heavy_frame`, `attack_s4_hold_frame`,
`attack_100_enable_cnt`, `attack_lw4_hold_frame`, `attack_hi4_hold_frame`,
`escape_air_landing_frame`, `tread_fall_recovery_frame`, `attack_s4_hold_keep_frame`,
`damage_model_no_hit_frame`, `attack_lw4_hold_keep_frame`,
`attack_hi4_hold_keep_frame`). Full per-field site counts, displacement histograms and
value statistics: `gamedata/mii_customizer/P11-INT-PARAMS/int_table.md`.
Per-site detail (site, producer `ldr`, call, x2, return use): `sites250.md`.

#### Cited instruction words for the eight +0x250 sites (pinned by the check)

Every word below is quoted from the image and asserted by
`evidence/P11-INT-PARAMS/check_p11_int_params.py`; the three hash-composition
words at each site recompose to the field's hash40.

| field | producer: addr = word | seed: addr = word (text) | x2 writer | call: addr = word | return use: addr = word (text) |
|---|---|---|---|---|---|
| jump_count_max | `0x62295c` `f9412908` | `0x622960` `d287b041` (`mov x1, #0x3d82`) + `f2a6b941` @`0x622964` + `f2c001c1` @`0x622968` | `0x622970` `aa1f03e2` `mov x2, xzr` (imm 0) | `0x622974` `d63f0100` | `0x622980` `2a0003e1` (`mov w1, w0`) |
| final_start_turn_frame | `0x62ea20` `f9412908` | `0x62e9fc` `d29317e1` (`mov x1, #0x98bf`) + `f2a7f561` @`0x62ea00` + `f2c002c1` @`0x62ea04` | `0x62ea34` `f2c002e2` `movk x2, #0x17, lsl #32` (**not** imm 0; x2 = `0x17a2eae8f6`, a hash) | `0x62ea40` `d63f0100` | `0x62ea44` `2a0003f7` (`mov w23, w0`) |
| attack_lw3_rebound_count | `0x6ca660` `f9412908` | `0x6ca664` `d2832021` (`mov x1, #0x1901`) + `f2c00301` @`0x6ca66c` | `mov x2, xzr` (imm 0) | `0x6ca674` `d63f0100` | `0x6ca678` `6b00029f` (`cmp w20, w0`) |
| attack_100_rebound_count | `0x34e5678` `f9412908` | `0x34e567c` `d2844d81` (`mov x1, #0x226c`) + `f2c00301` @`0x34e5684` | `mov x2, xzr` (imm 0) | `0x34e568c` `d63f0100` | `0x34e5690` `7100041f` (`cmp w0, #1`) |
| scroll_rate_change_frame | `0x62bfb0` `f9412908` | `0x62bfb4` `d292f241` (`mov x1, #0x9792`) + `f2c00301` @`0x62bfbc` | `mov x2, xzr` (imm 0) | `0x62bfcc` `d63f0100` | `0x62bff8` `b90037e0` (`str w0, [sp, #0x34]`) |
| pickel_capture_fence_type (site 1) | `0xf07928` `f9412908` | `0xf0792c` `d28da141` (`mov x1, #0x6d0a`) + `f2c00321` @`0xf07934` | `mov x2, xzr` (imm 0) | `0xf07940` `d63f0100` | `0xf07954` `2a0003f9` (`mov w25, w0`) |
| pickel_capture_fence_type (site 2) | `0xf1561c` `f9412908` | `0xf15620` `d28da141` (`mov x1, #0x6d0a`) + `f2c00321` @`0xf15628` | `mov x2, xzr` (imm 0) | `0xf15634` `d63f0100` | `0xf15648` `2a0003f7` (`mov w23, w0`) |
| (unlabelled) `0x19f190006a` | `0x33f0848` `f9412908` | `0x33f084c` `d2800d41` (`mov x1, #0x6a`) + `f2c00321` @`0x33f0854` | `mov x2, xzr` (imm 0) | `0x33f0864` `d63f0100` | `0x33f0870` `2a0003f7` (`mov w23, w0`) |

All eight producers are the same word `f9412908` = `ldr x8, [x8, #0x250]`;
all eight calls are `d63f0100` = `blr x8`. The thunk-block words cited in Q1
(`0x4e5380..0x4e53fc`) are pinned in the check script as well.

### Q3 - qualifying-field analysis

**Verified (B) 2026-10-07** - `scratch/2026-10-07_P12-INT-PARAMS/q3_qualify.py`
(`ALL PASS, 0 failures`) plus the return-use dumps of the copied `q3_data.py`
and `q3_extra.py`. Six i32 fields qualify (integer, at least one +0x250 site
with x2 == 0, value differs between fighters):

| field | Mii Gunner | min | max | distinct | value distribution | plausibly controls (D) | flag |
|---|---|---|---|---|---|---|---|
| `jump_count_max` | 2 | 2 | 6 | 5 | 2: 85 fighters; 3: buddy, plizardon, ridley; 4: pit, pitb; 5: dedede; 6: kirby, metaknight, purin | number of mid-air jumps (the read is compared/consumed as an int, `mov w1, w0` @`0x622980`) | **REVIEW - count that resources depend on** (see below) |
| `attack_lw3_rebound_count` | 3 | 0 | 6 | 4 | 3: 91 fighters; 0: koopag; 5: lucas; 6: pzenigame | how often the down-tilt (`attack_lw3`) rebound re-hits; the site loops on it (`cmp w20, w0` @`0x6ca678`, `b.ge` follows) | no (a hit count on one animation) |
| `attack_100_rebound_count` | 5 | 2 | 10 | 5 | 5: 61; 10: 23; 8: bayonetta, fox, gekkouga, metaknight, miienemyf, miifighter, sheik; 4: pichu, pikachu; 2: shizue | rapid-jab (`attack_100`) rebound chain length; `cmp w0, #1` @`0x34e5690` then the value is passed on in `w19` | no (same animation repeats) |
| `scroll_rate_change_frame` | 30 | 1 | 30 | 2 | 30: 87; 1: donkey, eflame, elight, ganon, gekkouga, kirby, robot | a frame delay/threshold before a rate change; what "scroll" is here is not established | no, but meaning unresolved (D) |
| `pickel_capture_fence_type` | 0 | 0 | 1 | 2 | 0: 74; 1: 20 | named *type* - a 0/1 selector for a capture-fence variant (both sites read it into a register and pass it on, `mov w25, w0` @`0xf07954`) | **REVIEW - selector / type flag** (name is also pickel-specific) |
| `0x19f190006a` (unlabelled) | 5 | 0 | 5 | 2 | 5: 93; 0: koopag | unknown - no verified label | **REVIEW - unknown identity** (cannot be classified) |

No field is *recommended* for shipping here (the prompt forbids it); the three
REVIEW rows are the ones a coordinator should look at first.

**`jump_count_max` in detail (the prompt's example).** Fighters with more
than 2 (all nine, `q3_qualify.py` B):

| kind (internal) | value | display label (from `fighters.json`) |
|---|---|---|
| `buddy` | 3 | `nam_chr0_00_buddy` |
| `plizardon` | 3 | (none - exception list) |
| `ridley` | 3 | `nam_chr0_00_ridley` |
| `pit` | 4 | `nam_chr0_00_pit` |
| `pitb` | 4 | `nam_chr0_00_pitb` |
| `dedede` | 5 | `nam_chr0_00_dedede` |
| `kirby` | 6 | (none - exception list) |
| `metaknight` | 6 | `nam_chr0_00_metaknight` |
| `purin` | 6 | `nam_chr0_00_purin` |

Mii Gunner = 2. **Does Mii Gunner's body motion list have the motions those
fighters use for extra jumps? NO (B for presence, D for the semantic link).**
Decoding the c00 `motion_list.bin` of each of the nine (from
`gamedata/ssbu-13.0.4/dk_cargo/fighter/<kind>/motion/body/c00/motion_list.bin`
(full stdout incl. per-file sha256 saved as
`evidence/P11-INT-PARAMS/run_q3_qualify.txt`) plus two controls:

| motion kind | in the 9 fighters with >2 | in `mario` (2) | in Mii Gunner (2) |
|---|---|---|---|
| `jump_squat`, `jump_f`, `jump_b` | 9/9 | yes | yes |
| `jump_aerial_f2` (+ anim `a03jumpaerialf2.nuanmb`) | **9/9** | no | **no** |
| `jump_aerial_f3` (+ anim `a03jumpaerialf3.nuanmb`) | 6/9 - exactly the fighters with value >= 4 (pit, pitb, dedede, kirby, metaknight, purin) | no | **no** |
| `jump_aerial_b2`, `jump_aerial_b3` | 0/9 | no | no |
| `jump_aerial_f`, `jump_aerial_b` kinds | 0/9 (their *anims* `a03jumpaerialf` exist in 8/9; buddy lacks even that) | yes | yes |

So the sample shows a perfect correlation: every fighter with 3+ mid-air
jumps carries motion kind `jump_aerial_f2` and its animation, and every
fighter with 4+ also carries `jump_aerial_f3`; the two 2-jump controls and
Mii Gunner carry neither. **Mii Gunner's motion list (the exact file
P1-DATASET used, `.../P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin`,
sha256 `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba`,
774 entries, decoded independently by the copied `probe_mlist.py`) does NOT
contain `jump_aerial_f2/_f3/_b2/_b3` kinds nor `a03jumpaerialf2/f3/b2/b3`
animations.** It has only `jump_aerial_f` / `jump_aerial_b` (entries 26/27).
What the engine does when `jump_count_max` asks for a jump whose motion kind
is missing is runtime behaviour (D, untested): hence the REVIEW flag.

### Q4 - bool and other non-float, non-int fields: which getter slot

**Unverified at first draft, left by the previous worker; VERIFIED (B) by this worker
2026-10-07.** Source: `gamedata/mii_customizer/P11-INT-PARAMS/others_table.md` /
`others_table.json` (regenerated and diffed - see the verification record below).
52 fields listed; displacement = the feeding `ldr` at the first call
after the hash composition (P4 method). Short summary:

- Fields with +0x250 displacements (14 of 52): `size` (584 sites, 0x250 x13), `skin_kind`
  (0x250 x2), `aerial_type` (0x250 x1), `dead_end_final` (0x250 x4), `wall_jump_type`
  (0x250 x1), `metal_sound_level` (0x250 x3), and eight unlabelled bool fields
  (`0x12326f1f2a`, `0x13042acb2d`, `0x13cf982a55`, `0x13e3bcfb18`, `0x1408832504`,
  `0x145620fd97`, `0x187608007b`, `0x18f0607a99` - each 0x250 x1).
- Fields with 0x260 displacements (4): `ice_node` (0x260 x4), `fire_hit_size` (0x260 x1),
  `edge_flare_node` (0x260 x2), `trail_special_s_joint_id` (0x260 x5).
- `size` also shows 0x50 x4; all other displacements in the table are "none".
- All 25 bool fields shown use no other slot; `fighter_kind` (48 sites) shows none.

Full table with per-field site counts and displacement histograms:
`gamedata/mii_customizer/P11-INT-PARAMS/others_table.md`.

## Input

| item | value |
|---|---|
| file | `gamedata/ssbu-13.0.4/main.bin` (workspace-relative) |
| expected sha256 | `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` |
| layout | flat, address == file offset |

**Verified (B) 2026-10-07:** sha256 =
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`
(matches the pinned value), size 86 672 752 bytes.

## Answers

All four questions are answered in "Short answers" above: Q1 (fresh, B),
Q2 and Q4 (verified by reproduction, B), Q3 (fresh, B with D markings).

## Verification record (what was rerun, in order)

### V1 - Q1 measurement (2026-10-07)

Command (workspace root):

```
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python \
  mods/mii_customizer/scratch/2026-10-07_P12-INT-PARAMS/q1_slot.py
```

Result: `ALL PASS (0 failures)` - image sha256 matches the pinned value; slot
+0x250 of `0x4f89490` = `0x4e53a0`; slot +0x270 = `0x4e53e0` as stated in the
background; first four words of `0x4e53a0` are not PC-relative; exactly two
relocated qwords hold `0x4e53a0` (both at +0x250 of qualifying vtable runs,
bases `0x4f89490` and `0x4f73738`). Full stdout saved as
`evidence/P11-INT-PARAMS/run_q1_slot.txt`; the same assertions are re-read by
`evidence/P11-INT-PARAMS/check_p11_int_params.py`.

Supporting disassembly via the shared disassembler (`d.py win 0x4e5370 44`)
showed the whole thunk block; the Q1 section quotes it.

### V2 - scanner validation against P4 (2026-10-07)

Command (workspace root):

```
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python \
  mods/mii_customizer/scratch/2026-10-07_P12-INT-PARAMS/scan_int.py validate
```

Result, exit 0 (saved as `evidence/P11-INT-PARAMS/run_validate.txt`):

- planted-sequence self-test of the scanner: `VALIDATE OK` (34 PASS lines),
- P4's ten float controls reproduced exactly: `VALIDATE_P4 OK`
  (e.g. `weight sites=37 via270=23`, `walk_speed_max 18/6`, ... ),
- **P4 section 6 / example 8.2 control: `jump_count_max` - 5 sites, 1 via
  +0x250, 0 via +0x270, 1 direct_bl, 3 none, +0x250 site at `0x622960`:**
  `VALIDATE_INT OK`, all six sub-checks `ok`.

The byte patterns of the copied scanners match the reviewed originals:
`stat_reads.py` sha256 `28126c1bb703ecc7f79b7cc71b32d24db6b711c00bbb5f781b4dc01d44fd9a6d`
(identical in P2-STAT-READS, P4-STAT-SITES, P10-PRESET-WIDE scratches) and
`scan_wide.py` sha256 `773c90b410601760e0a82c11474b02a7d942301843b8494e32b7132681f44069`
(identical in P10-PRESET-WIDE scratch).

Independent disassembly of P4 example 8.2's window (`d.py win 0x622950 17`)
reproduced the published window instruction-for-instruction, including
`ldr x8,[x8,#0x250]` @`0x62295c`, hash composition `0x0e35ca3d82`,
`mov x2,xzr` @`0x622970`, `blr x8` @`0x622974`, return use
`mov w1, w0` @`0x622980`.

### V3 - full rerun and diff against the left-over tables (2026-10-07)

Left-over tables were first copied read-only to
`scratch/2026-10-07_P12-INT-PARAMS/leftover_tables/`. Then:

```
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python \
  mods/mii_customizer/scratch/2026-10-07_P12-INT-PARAMS/scan_int.py scan
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python \
  mods/mii_customizer/scratch/2026-10-07_P12-INT-PARAMS/make_tables.py
diff (six files) against leftover_tables/
```

Scan stdout, exit 0: `primary scan 15.8s; sites 3169 over 369 fields`,
`scanners disagree on 0 fields`, `i32 fields 25, bool+hash 52`,
`qualifying i32 fields: 6 -> jump_count_max, attack_lw3_rebound_count,
attack_100_rebound_count, scroll_rate_change_frame, pickel_capture_fence_type,
0x19f190006a`.

Diff result:

| file | result |
|---|---|
| `int_table.md` | byte-identical |
| `int_table.json` | byte-identical |
| `others_table.md` | byte-identical |
| `others_table.json` | byte-identical |
| `sites250.md` | byte-identical |
| `sites_int.json` | differs **only** in `timing_seconds.scan_primary` (left-over 17.5, rerun 15.8) - no factual difference |

**Conclusion: Q2 and Q4 are VERIFIED (B); no correction needed.** The left-over
tables' numbers are reproduced from the same image by byte-identical copies of
the reviewed P2/P4/P10 scanners, after the P4 controls passed. The regenerated
files in `gamedata/mii_customizer/P11-INT-PARAMS/` supersede nothing: they are
the same content.

### V4 - the check script (2026-10-07)

```
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python \
  mods/mii_customizer/evidence/P11-INT-PARAMS/check_p11_int_params.py
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python \
  mods/mii_customizer/evidence/P11-INT-PARAMS/check_p11_int_params.py --neg
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python \
  mods/mii_customizer/evidence/P11-INT-PARAMS/check_p11_int_params.py --selftest
```

During development the check caught three bugs in ITSELF (a missing dot in a
key derivation, a mistyped return-use address `0xf1648` for `0xf15648`, and a
string/int key mismatch in the `qualifies` recomputation) and one real input
fact (the P6 vs P10 `fighter_param_full.json` hash question - see Method).
The final runs are pasted verbatim under "Final check outputs" below; they
were executed after the last content edit of this file (the paste itself is
the only later change, and it does not alter any checked input).

## Method

**Inputs pinned.** Image `gamedata/ssbu-13.0.4/main.bin`: sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`,
86 672 752 bytes. `fighter_param_full.json`: the prompt names the
`gamedata/mii_customizer/P10-PRESET-WIDE/` copy (sha256 `c46dcd3e...415c3`),
but the copied scanner resolves its `FULL_REL` to the
`gamedata/mii_customizer/P6-PRESET-DATA/` copy (sha256 `9188c768...6d70df`,
the pin recorded in `sites_int.json`). Both were compared field-by-field:
**the `rows` arrays are identical (0 differing fields over 94 x 369 cells)**;
only metadata/formatting differs, so no Q2/Q4 number depends on the choice.
The check pins both hashes. Mii Gunner's motion list is P1-DATASET's file
`gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin`,
sha256 `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba`,
774 entries.

**Q1.** `scratch/2026-10-07_P12-INT-PARAMS/q1_slot.py`: parses the RELA
table (306 167 relocated records), prints slots `+0x240..+0x288` of vtables
`0x4f89490`, disassembles the target with raw words and a PC-relative flag,
scans all of `.text` for `ldr xN,[xM,#0x250]` + `br xN` pairs, and searches
every relocated qword for the thunk addresses. Supporting disassembly with
the shared `d.py win` (thunk block `0x4e5370..0x4e53fc`; example 8.2 window
`0x622950..0x62298c`). See V1.

**Q2/Q4.** The previous worker's scripts were copied into
`scratch/2026-10-07_P12-INT-PARAMS/` (its own folder not touched); the
copied `stat_reads.py` / `scan_wide.py` are byte-identical to the reviewed
P2/P4/P10 originals (sha256 verified, V2). Order: `scan_int.py validate`
(scanner self-test, P4's ten float controls, the `jump_count_max` control)
-> `scan_int.py scan` -> `make_tables.py` -> `diff` of all six outputs
against read-only copies of the left-over tables. See V2/V3.

**Q3.** `scratch/2026-10-07_P12-INT-PARAMS/q3_qualify.py` (written for this
task) recomputes the qualifying set, the value distributions of the six
qualifying fields, the nine fighters with `jump_count_max > 2`, and decodes
every relevant `motion_list.bin` (magic checked against `hash40("motion")`)
for kinds and animations; plus reruns of the copied `q3_data.py`,
`q3_extra.py`, `probe_mlist.py`, `probe_anims.py`. The nine >2 fighters'
motion lists come from the existing game-derived extraction
`gamedata/ssbu-13.0.4/dk_cargo/fighter/<kind>/motion/body/c00/motion_list.bin`
(sha256 per file recorded in the run output).

**Check script.** `evidence/P11-INT-PARAMS/check_p11_int_params.py`
re-implements the movz/movk site rule and the first-call / producer / x2
classifier independently (it does NOT import the scratch scanners, so a
shared bug cannot hide) and compares against the artifact tables; it also
verifies the image identity, the Q1 relocation facts, every instruction word
cited in this report, the value statistics, and the motion facts. 558
comparisons in 19 groups. Seven negative controls behind `--neg`
(hash, slot, word, reloc, site, disp, mlist), each must fail; `--selftest`
runs the clean suite plus all controls in one process.

## Limitations

- **Offline B only.** Nothing here is runtime evidence; no emulator, no
  console, no hook code. Tier A remains the earlier gates.
- The *inner* implementations behind slot `+0x20` (reached by `0x4e53a0`)
  and slot `+0x30` (reached by `0x4e53e0`) are not disassembled here; that
  the +0x250 getter returns an int in `w0` is inferred from call-site usage
  (B), not read from the callee.
- The class identity of vtable `0x4f73738` is unestablished; whether any of
  its objects are fighters is D (same open question as P4-OVERRIDE-SLICE's
  `st=vt` failure pattern).
- The extra-jump motion link is a perfect correlation over 11 decoded motion
  lists (9 fighters with >2, 2 controls), not a code path: which motion the
  engine plays for the n-th mid-air jump is D; what happens when the motion
  kind is missing is untested.
- Site rule = P2/P4 movz/movk composition (gap <= 4, no register overwrite);
  a hash materialised any other way (loaded, computed) is invisible, exactly
  as in P4/P10. `x2` rule = closest writer within 8 instructions, not a full
  dataflow proof; `final_start_turn_frame`'s x2 is a composed 40-bit hash,
  and only its last movk is within the window.
- Value statistics come from the decoded `fighter_param_full.json` (P6/P10),
  not re-decoded from `fighter_param.prc` in this task.
- The check script does not parse this report file; it pins the cited
  constants in its own source. A typo introduced into the report after the
  constants were transcribed would not be caught by re-running it.
- The `dk_cargo` motion-list extraction is read as given game-derived data;
  it was not re-verified against `dump/` in this task.
- `scroll_rate_change_frame`'s meaning and the label for `0x19f190006a` are
  unresolved; both are marked in Q3 instead of guessed.

## Summary

- **Q1:** slot `+0x250` of `0x4f89490` is `0x4e53a0`, a 4-instruction
  forwarder (`ldr x0,[x0,#0x38]; ldr x8,[x0]; ldr x3,[x8,#0x20]; br x3`),
  words `f9401c00 f9400008 f9401103 d61f0060`, none PC-relative; identical
  in shape to `0x4e53e0` (+0x270, inner slot `+0x30`) except the inner slot;
  x1/x2 pass through, x0 becomes `[x0+0x38]`; slot `+0x248` re-dispatches
  into it exactly as `+0x268` does into `+0x270`; it sits in exactly two
  vtables (`0x4f89490`, `0x4f73738`) - the two that share the whole
  `+0x248..+0x278` block (B).
- **Q2:** verified by byte-identical reproduction; 25 i32 fields, 7 with
  +0x250 sites, 6 qualifying (B).
- **Q3:** three of the six are flagged for coordinator review -
  `jump_count_max` (count with resource dependency: Mii Gunner's motion
  list lacks `jump_aerial_f2/_f3` kinds and `a03jumpaerialf2/f3` anims that
  all 9 fighters with >2 jumps carry; Mii Gunner value 2),
  `pickel_capture_fence_type` (0/1 type selector), `0x19f190006a`
  (unlabelled). The other three are plain counts/frame thresholds, with
  `scroll_rate_change_frame`'s meaning marked unresolved. No field is
  recommended for shipping (D for all "plausibly controls" readings).
- **Q4:** verified; 52 bool/hash fields, 14 with `0x250` displacements,
  4 with `0x260`, `size` also `0x50 x4`, everything else `none` (B).
- Check: 558 checks, 0 failures; seven negative controls detected; outputs
  pasted below.

## Final check outputs

Run 1 (clean), after the last content edit of this file:

```
PASS compose        8 checks
PASS dist           6 checks
PASS full           1 checks
PASS full6          1 checks
PASS i32            1 checks
PASS image          2 checks
PASS jump           7 checks
PASS motion         14 checks
PASS others         1 checks
PASS q1             15 checks
PASS q3             2 checks
PASS q4             2 checks
PASS qualifying     1 checks
PASS sites250       48 checks
PASS table          231 checks
PASS table250       32 checks
PASS tablevalues    125 checks
PASS total          2 checks
PASS word           59 checks
558 checks, 0 failures
ALL PASS
EXIT=0
```

Run 2 (negative controls):

```
neg hash   detected (suite failed, 1 mismatches) (control: image.sha256 = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7614')
neg slot   detected (suite failed, 1 mismatches) (control: q1.slot+0x250 = 0x4e53e0)
neg word   detected (suite failed, 1 mismatches) (control: word[0x004e53a8] = 0xf9401903)
neg reloc  detected (suite failed, 1 mismatches) (control: q1.reloc_4e53a0 = {0x4f896e0: 0x4e53a0, 0x4f73988: 0x4e53a0, 0x4f89708: 0x4e53a0})
neg site   detected (suite failed, 1 mismatches) (control: field.0x0e35ca3d82.code_sites = 6)
neg disp   detected (suite failed, 1 mismatches) (control: field.0x0e35ca3d82.via250 = 0)
neg mlist  detected (suite failed, 1 mismatches) (control: motion.gunner.kinds = ['jump_aerial_b', 'jump_aerial_f', 'jump_b', 'jump_f', 'jump_squat', 'jump_aerial_f2'])
ALL 7 CONTROLS DETECTED - CHECKER OK
EXIT=1
```

(A `--selftest` run in the same session reported `SELFTEST OK`, exit 0:
clean suite 0 failures plus all seven controls detected; stdout also saved
for the clean and `--neg` runs as `evidence/P11-INT-PARAMS/check_run.txt`
and `check_neg.txt`.)

## End of task

- **Task ID:** `P12-INT-PARAMS` (finishing `P11-INT-PARAMS`)
- **Status:** DONE
- **Changed files:**
  - `research/P11-INT-PARAMS.md` (this report; coordinator banner kept)
  - `evidence/P11-INT-PARAMS/check_p11_int_params.py`
  - `evidence/P11-INT-PARAMS/run_q1_slot.txt`, `run_validate.txt`,
    `run_q3_qualify.txt` (stdout of V1/V2/Q3 runs)
  - `scratch/2026-10-07_P12-INT-PARAMS/` (copies of the previous worker's
    scripts, `leftover_tables/` backups, `q1_slot.py`, `q3_qualify.py`,
    `dump_cited.py`)
  - workspace `gamedata/mii_customizer/P11-INT-PARAMS/` (regenerated;
    five files byte-identical, `sites_int.json` differs only in the timing field)
- **Checks run:** see "Verification record" V1-V4 and "Final check outputs"
  (all exit codes listed there).
- **Open questions:**
  1. What sits in inner slots `+0x20`/`+0x30` (needed before any second
     hook is designed; premium/native RE candidate).
  2. Which fields the coordinator wants in a preset, and what happens in
     game if `jump_count_max > 2` for a Mii whose motion list has no extra
     jump motions (console question, deliberately not run here).
  3. Class identity of vtable `0x4f73738` (does a hook on `0x4e53a0` see
     fighters of both classes?).
  4. Label/meaning for `0x19f190006a`, `scroll_rate_change_frame`, and the
     exact domain of `pickel_capture_fence_type`.
