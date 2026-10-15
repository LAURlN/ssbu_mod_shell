# Monkey Flip - 2026-09-30

## Current evidence

0.20.6 captures on hardware, but victims T-pose (user). Ten EVENT/ACCEPT/SETUP/CLING entries and 447 captured CLUNG_DIDDY samples. Both release exits still need explicit confirmation.
Evidence: `evidence/2026-09-30_pgwr_0.20.6/RESULT.md`; owned receiver provenance: `refs/diddy_monkey_flip/capture_{native,owned_data}.json`.
The user permits deferring the victim-pose issue if difficult. Do not substitute a stand-in pose.

## Aerial availability: two controlled changes

Tier B: `tools/audit_diddy_special_lockout.py` 1.0.0 / `refs/diddy_monkey_flip/special_lockout.json` pin the shipped Diddy NRO, end-handler instructions and availability callback.
1. **0.20.7 (INSTALLED, hardware-confirmed by the user 2026-09-30):** JUMP end -> FALL sets an owned side-only input lock; the shared Fire availability callback disables CONT_SPECIAL_S. Native ground/cliff/hit/reset events refresh it; owned phase state never clears it.
2. **T-0053 (2026-10-02): source complete, NOT packaged and NOT installed.** KICK and STICK_ATTACK2 end -> FLIP_FALL now set the donor's general special-input lock, and the availability callback disables HI/S/LW for it (neutral-B and the aerials untouched, as in the donor). Both locks are per-entry state **owned by the battle object that set them**, so Mythra landing can no longer re-own the slot and unlock Pyra mid-air - that second defect was found while diagnosing why a repeated airborne flip was still possible. Both flags are refreshed only by the native landing/ledge (+0x168), hit (+0x220), class-reset (+0x210) and rebirth/dead/entry events. Installer section, bounded log lines and the ten-step manual test (with stock-Diddy and c00 controls): `CURRENT_INSTALL.md`, section "Monkey Flip aerial locks: kick + swap". Finding: `kb/findings/monkey-flip-aerial-locks-need-an-object-owned-record.md`. Compile-checked only; no runtime evidence of any kind yet.
   Confirm on hardware: kick -> up-B/down-B/side-B denied, no-kick leap -> only side-B denied, landing/hit/ledge/stock restoration, swap does not unlock, capture and both release exits preserved, Fire unchanged.

AGENTS rule 11 requires one state-changing change per hardware test. Preserve the now-capturing receiver and assets during these tests. Rule 10 requires restoring 0.20.6 on a new crash/freeze rather than stacking a variant.

## Remaining capture scope

Owned receiver handles Pyra c06/c07 custom JUMP + capture/CLUNG_DIDDY with copied victim offsets and native setup order; other events forward to original Pyra. No framework rebuild. Item attachment branches remain unported.
Victim pose: measure requested/playing motion and native CLUNG_DIDDY initialization before deciding the correct owned asset/selection fix. Motion-kind/frame telemetry does not prove a rendered pose. Existing donor sound/effect and spare animation-carrier gaps remain.

# Snake neutral-B (grenade) on Pyra c06/c07 - plan, 2026-09-30 (0.20.11 packaged offline; not installed)

## What the earlier attempt actually did (tier B, `tools/maindesc.py 0x22`, main sha256 `f70c97d2…7613`)

Snake is `FIGHTER_KIND` 0x22. His article table (index = local `FIGHTER_SNAKE_GENERATE_ARTICLE_*`) has **two** grenade entries:

| local | const | weapon kind | init / fini | what it is |
| --- | --- | --- | --- | --- |
| 12 (0xC) | `GRENADE_PIN` | `0x199` `WEAPON_KIND_SNAKE_GRENADE` | `0x11b71c0` / none | ordinary weapon, model `fighter/snake/model/grenade`, clip `special_n_start` (pin pull). No `lua2cpp_snake` weapon agent exists for it, so it has no status code. |
| 13 (0xD) | `GRENADE` | `0x96` = `ITEM_KIND_SNAKEGRENADE` | `0x11b6c60` / `0x11b6da0`, extra=1 | an **item-backed article**: Snake's script `generate_article(GRENADE)` makes the real item in his hand and `ArticleModule::shoot` throws it. |

The 2026-09-26 attempt (`refs/snake_grenade/PROGRESS.md`) created `ITEM_KIND_SNAKEGRENADE` through the item manager, i.e. the
same object Snake's article wraps. So "spawn Snake's grenade" and "Snake's native article" are one path, and that path is
Snake-coupled in three places:

1. `snakegrenade::life()` (`main+0x1674e90`) = `*(*(*(main+0x52bb3b0)+0x7e0)+0xf0)`: Snake's decoded `param_snakegrenade.life` (150).
   Potentially null without Snake in the match (B pointer-chain dependency; prior crash R-11 cause remains unisolated). Same class of fault as G&W breath (`+0x690`) and Hero fireball (`+0x1298`).
2. The article's fini `0x11b6da0` compares the owner's status kind with `0x1ef` and `0x30e`. `0x1ef` is Snake's `SPECIAL_N_THROW`;
   on eflame `0x1EF` is a Monkey Flip phase. Cloning it would make the native code act on the wrong status (rule 19).
3. Init `0x11b6c60` reads `param_special_n` / `param_snakegrenade` through the owner's WorkModule.

Consequence: cloning or spawning the item article cannot be made "owned"; a `life()` hook only moves the fault (R-11: .p3 died in a
stack overflow 14 MB away, and the .p4 build with the grenade compiled out was the bisect).

## Proposed route (own everything, rule 17): a self-contained grenade weapon

Everything the item does is small and already recoverable offline:

* **Hitboxes/effects/sounds**: `dumps/scripts/SSBU-Dumped-Scripts-main/luas/item/snakegrenade/script/animcmd/body/{game,effect,sound}.lua`
  (C, WuBoytH decompile of the item `.lc`): `Throw` = one 1-damage ball, size 1.6, angle 361, bone `top`; `Born` = explosion, hit 1
  damage 9 angle 80 kbg 69 bkb 60 size 12, next frame size 20, `collision_attr_fire`, quake S, effect `sys_bomb_a`/`sys_bomb_b` (`EFFECT_BRANCH_SITUATION`, scale 1.2),
  sound `se_snake_special_n04`, vanish sound `se_item_item_vanish`.
* **Numbers**: `fighter/snake/param/vl.prc` (in `dumps/`): `param_special_n[0]` throw_m 1.1/1.0, hi 2.5/0.3 (threshold 0.4), lw 0.2/1.8 (threshold -0.4),
  `ear_close_distance` 45.0; `param_snakegrenade[0].life` = 150.
* **Assets** (extracted 2026-09-30 into `refs/snake_grenade/arc/`): `fighter/snake/model/grenade/c00` is the **pin** (bones Root/Ring/Trigger; its 3 clips + list are in `dumps/`), `item/snakegrenade/model/body/c00` is the **grenade body** (Have/Rot; 7 clip-less states `appear have fall throw born lost wait_ground`). The owned copy needs both: pin article + grenade weapon.
* **Fighter side**: Snake's SPECIAL_N statuses are pinned in `refs/snake_grenade/status/` (C, Coolsonickirby dump `b6bb1fec…`): START, HOLD_WAIT/WALK/DASH/JUMP(_SQUAT/_AERIAL)/LANDING/AIR, EAR_CLOSE, THROW.
  Body clips exist in `dumps/arc/fighter/snake/motion/body/c00/` (13 `d00specialn*`); Snake's body `motion_list.bin` (extracted, 764 entries) has 14 `special_(air_)n_*` entries naming them; the `legs_dash` clips are not referenced by those 14 entries (find their entries before porting HOLD_DASH).
* Clone `WEAPON_KIND_SNAKE_GRENADE` (0x199, no native fini, init `0x11b71c0` contains no param-manager read: verify with `tools/scan_param_manager_reads.py`) as the container for
  both the in-hand model and the thrown body; own weapon statuses (FLY/bounce, FUSE, BORN) with gravity/bounce from the item's `lua2cpp_item.nro` statuses (Ghidra) and the
  explosion from `game.lua` above; own fighter statuses from `0x1FB` (next free block) for START/HOLD/THROW, Snake's clips retargeted to the G&W body (Cloud-fair/Monkey Flip pipeline).
  Fuse = 150 frames from the throw, tier D until measured on hardware (the item might start it at `Appear`/`Born`; `lua2cpp_item.nro` decides).

## Still unknown (do not present as done)

* Item bounce/gravity/friction and the fuse start are in `lua2cpp_item.nro` + `main`; decompile before writing the FLY status (tier B once done).
* Whether a cloned weapon with `use_original_code=false` renders (R-22 risk) and whether 0x199's default kinetics fit; console only.
* Sounds: `se_snake_special_n01..n04` are in `se_snake_c00` (extracted to `refs/snake_grenade/arc/sound/`; merging them into the eflame bank is still to do).

## Dumps: all extracted 2026-09-30 (`dumps/MISSING.md`, `refs/snake_grenade/extraction.json`)

## Snake grenade item, offline map (2026-09-30, B unless marked)

Source: `dumps/arc/prebuilt/nro/release/lua2cpp_item.nro` flattened with `tools/nro_decomp/nro_flatten.py`; scratch annotator
`scratch/2026-09-30_claude_snakegren/annot.py` (hash40 + lua-const names per call).

* Factory `create_agent_item_status_script` branches on `hash40("snakegrenade")` = `0xca537ca72` at `item+0x2da80` to a
  0x468-byte agent, vtable `item+0xcae8b0`, base ctor `item+0x87f400`; its code is `item+0x7c8000..0x7caa00` (shared with `snakecbox`).
* Statuses (by `init_status_data` + motion names): `appear` (init: `set_life_type`, **`life()`**, `set_bomb_countdown`, two mesh toggles
  `0x8f4c1b42e`/`0xf793b9c2c`), `have` (HIT_STATUS_XLU), `fall`, `wait_ground`, `throw`, `born` (explosion; rot speed x0.5, `disable_area`),
  `lost` (hide + `request_remove`). `send_bomb_link_event` (main `0x1674eb0`) only messages the linked owner, no param read.
* The fuse is started in `appear`, i.e. at creation, not at the throw (corrects the tier-D note above).
* All motion/bounce/landing/catch is in shared item-framework helpers (`item+0x8f8db0, 0x8f90e0, 0x8d9d20, 0x8d0820, 0x8a0370`) used by every item.
* The only Snake-param read in the whole item path is `life()` (main `0x1674e90`): `tools/scan_param_manager_reads.py 0x7e0`.

### The route decision this forces (user's call)

* **A. Real item, own everything else.** Pyra's own statuses create `ITEM_KIND_SNAKEGRENADE` through the item manager (not Snake's
  article 13, whose init/fini are Snake-bound), plus one byte-verified plugin-local hook on `life()` that returns our pinned `param_snakegrenade.life`
  (150) only while Snake's slot is null. Keeps pickup/catch/throw-back and the exact native physics. Needs rule-17 approval for the hook.
  Risk: the 09-26 crash is unexplained (R-11), and whether the item's resources load without Snake is tier D.
* **B. Owned weapon copy.** Clone Snake's pin weapon `0x199` as the container and re-implement `appear..lost` plus the shared item helpers in the plugin.
  No hook, but opponents cannot pick up or catch it (weapons are not items), and the item-framework physics must be decompiled from `main`
  and rewritten. Much larger and less faithful.

**Decision 2026-09-30 (user): route A.** The user authorized the plugin-local, byte-verified `life()` hook (rule 17) for the Snake grenade on Pyra c06/c07.
Framework plugins untouched. No install until the user asks.

---

# Hero side-B status id allocation - 2026-09-30 (Buffy)

Allocation settled; gameplay implementation blocked by native dependencies (2026-09-30).
Nothing implemented, built or installed for side-B. Mana/Special-Move-gauge system
excluded by the user's instruction. Source of record: `refs/brave_special_s/status_table.txt`
(247 rows, tier B) and `refs/brave_special_s/SOURCE_STATUS.md`.
Research fan-out briefs: `projects/pgwr/AGENT_BRIEFS.md` (A-E dispatched, F answered 2026-09-30).

## The binding constraint: `eflame` and `elight` have separate tables

They do not share an id space, so "the next free id" means *which fighter*. Two blocks are live
at once and both must be respected:

| table | ends at | held by pgwr | next free |
| --- | --- | --- | --- |
| `eflame` (Pyra) | `FIGHTER_EFLAME_STATUS_KIND_NUM` `0x1EE` | Monkey Flip `0x1EE`-`0x1F8`, up-B `0x1F9`/`0x1FA` | **`0x1FB`** |
| `elight` (Mythra) | `FIGHTER_ELIGHT_STATUS_KIND_NUM` `0x1F1` | Hero Spin `0x1F1`-`0x1F4`, Hero neutral-B `0x1F5`-`0x1F9` | **`0x1FA`** |

Side-B is a **Mythra** move, so it allocates from the `elight` block at **`0x1FA`**. The G&W
neutral-B Chef already queued for `0x1FB` is on the *Pyra* table and does not collide - the two
"next free" numbers are unrelated and both stay valid.

Per `handbook/06_statuses.md`: allocate a block from the end of the used block, never from the
lowest free id, and never reuse a retired number (`0x1EE` on Pyra was Judge's).

## Proposed block: `0x1FA`-`0x1FE` on `elight`

| id | name | donor status | entered by |
| --- | ---- | ------------ | ---------- |
| `0x1FA` | `SPECIAL_S_ATTACK1` | `FIGHTER_BRAVE_STATUS_KIND_SPECIAL_S_ATTACK1` | `SPECIAL_S` startup clip ending, side-B pressed |
| `0x1FB` | `SPECIAL_S_ATTACK2` | `..._ATTACK2` | ATTACK1 clip ending, still in chain |
| `0x1FC` | `SPECIAL_S_ATTACK3` | `..._ATTACK3` | ATTACK2 clip ending, still in chain |
| `0x1FD` | `SPECIAL_S_ATTACK3_APPEND` | `..._ATTACK3_APPEND` | ATTACK3 clip ending with the append window |
| `0x1FE` | `SPECIAL_S_HOLD` | `..._SPECIAL_S_HOLD` | holding side-B; release fires the SP slash with no gauge check (see decision) |

No id for the entry itself: `FIGHTER_STATUS_KIND_SPECIAL_S` (`0x1DD`) is a *common* status and is
replaced on the gated agent exactly as up-B's `SPECIAL_HI` is, rather than given a new id. Same
shape as the existing up-B precedent.

`0x1FE` is allocated: the user decided the charge hold stays and its SP outcome is released
unconditionally. All five ids are in use.

## What the measurement settled (and what it did not)

Settled, tier B, from `refs/brave_special_s/status_table.txt`:

- Hero's side-B is **six** statuses, not more, and **there is no air-specific side-B status**.
  `lua_const.rs` has no `FIGHTER_BRAVE_STATUS_KIND_AIR_S*`; the `d01specialairs*` clips are
  reached from the same six states. Air is a situation branch inside them, so the block does not
  double for air.
- Conditions are **not** uniform across the chain. `EXEC_STATUS` is registered on HOLD, ATTACK1,
  ATTACK2 and ATTACK3_APPEND but not ATTACK3; `CHECK_ATTACK` on ATTACK1, ATTACK2 and
  ATTACK3_APPEND but not ATTACK3. A port that assumes PRE/MAIN/END everywhere will mis-handle the
  third hit.
- The toolchain is the pinned one: `skyline-smash 315e4e8`
  (`src/pgwr/plugin/Cargo.toml` line 36). `FIGHTER_BRAVE_STATUS_KIND_NUM` = `0x1FE`,
  `FIGHTER_ELIGHT_STATUS_KIND_NUM` = `0x1F1`.

Not settled - the table gives addresses, not behaviour (updated after the read; see
`refs/brave_special_s/SOURCE_STATUS.md` addendum):

- **Charge thresholds: now read.** `param_special_s` entry 0: `hold_frame_m` **9**, `hold_frame_l`
  **26**, `hold_frame_max` **26**, `activate_wait_frame_{s,m,l}` 3/3/3,
  `hit_stop_mul_{s,m,l}` 0.2/0.0/0.5, `speed_lightning` -10.0, `offset_y_lightning` 85.0,
  `hit_speed_y_air` 0.6, `start_speed_x_mul` 0.5 ground / 0.8 air. Pinned as
  `refs/brave_special_s/param_special_s.json` via `tools/dump_param_special_s.py --check`.
- **The hold trigger: now decoded.** HOLD `EXEC_STATUS` `0x58f0` increments
  `WORK_INT_HOLD_FRAME`, compares it to `hold_frame_m` with **`==` (not `>=`)**, and on that single
  frame calls `FIGHTER_ANIMCMD_EFFECT`. `>=` would re-fire the charge effect every frame past 9.
  Listing: `refs/brave_special_s/special_s_hold_exec.asm.txt`.
- **SP decision recovered:** canonical corrected measurement in
  `refs/brave_special_s/SOURCE_STATUS.md` sections 4-5. The owned port replaces its
  decision with unconditional success and performs no recipient SP reads.
- **Helpers recovered:** canonical mapping and corrected spark guard in the same file.
  The three brief addresses are readers/hold handling, not the setter.
- Cancel windows, and whether ATTACK3_APPEND is reachable without the gauge.

## Decision 2026-09-30 (user): hold kept, SP slash released unconditionally

The user chose option 3 of the three readings put to them. Holding B charges, and release always
produces the SP slash - the gauge check is **removed**, not merely its price.

**This is "without the mana system" in the sense the user means it, and the wording in the docs
should say so precisely:** there is no Special-Move gauge, no mana read, no mana price and no
failure branch. The *outcome* the gauge used to unlock is now unconditional. Anything that says
"the charged version is absent" is wrong and must not be written.

Consequences:

- `0x1FE` is **allocated and live**, not reserved. The block is `0x1FA`-`0x1FE`, five ids, no
  retired number inside it.
- `SPECIAL_S_HOLD` keeps its donor charge timing and hold clip (`d01specialshold.nuanmb`), and its
  `EXEC_STATUS` row (`0x58f0`) is the one that has to be understood first - it is the only
  side-B exec function that is not shared with ATTACK1/2/APPEND at `0x5b00`.
- The SP slash is the `d01specials32.nuanmb` clip. Evidence: `SpecialS32.txt` is 8 `ATTACK` lines
  at 120 base knockback / 50 growth with `ATTACK_SOUND_LEVEL_L` - far too large for the third
  link of a three-hit chain, and the same shape as a charged finisher. `SpecialS1.txt` shows the
  branch key is `FIGHTER_BRAVE_STATUS_SPECIAL_S_FLAG_SUCCESS_SP`. The port sets that flag on
  release unconditionally instead of gating it on the gauge.
  Tier **C** (pinned WuBoytH ACMD text), and only a shape argument - which status owns the check
  is still unread, so the clip-to-status mapping is an expectation, not a result.
- Tier **B**, native recheck 2026-09-30: ground/air S3 resolve to `0x115590`,
  whose complete body activates the lightning article at frame 10 and has zero
  direct ATTACK calls. Its hitboxes must come from the owned article translation.
  The earlier claim that this count was necessarily a dump artifact is retracted;
  see `refs/brave_special_s/SOURCE_STATUS.md` section 6 and R-HERO-S-5.
- **Do not read the gauge at all.** No `WorkModule` read of the special-move gauge, no
  `param_special_s` mana field, no `vc_brave_mp_lost` voice
  > **Superseded 2026-10-02 (T-0057):** the mana system now exists - see the T-0057 section at
  > the end of this file. The bullet above records the port as it stood then and is kept
  > as the history of the decision, not as current behaviour. (that line is the mana-lost call and is
  expected to be *absent*, which is worth a log assertion so its absence is a reading rather than
  an omission).
- Charge thresholds come from `param_special_s` in the pinned
  `dumps/arc/fighter/brave/param/vl.prc`; 9/26/26 rechecked with
  `tools/dump_param_special_s.py --check` on 2026-09-30.

Rule 9 applies to removing the gate: the control is vanilla Hero on the same build. Vanilla must
compare sufficient/insufficient SP for the requested charge level; the recovered helper
tests the requested amount against SP, not necessarily a full meter. Ours must show
the successful outcome unconditionally. Without that pair the
"gate removed" claim is a reading of our own code, not a result.

## Consequences to record when this is implemented

- Mythra's own side-B statuses `FIGHTER_ELIGHT_STATUS_KIND_SPECIAL_S_FORWARD` (`0x1E9`) and
  `..._SPECIAL_S_END` (`0x1EA`) become unreachable **on c06/c07 only**. They stay in her table and
  stay live for c00-c05 - that is the vanilla negative control for this move.
- Donor ids `0x1E6`-`0x1EA` above are Hero's. They are recorded for traceability and must never be
  written into Mythra code (rule 19, no equating ids across fighters); Mythra's block is
  `0x1FA`-`0x1FE` and the translation is per-entry state, as neutral-B already does.
- The blade length is Mythra's, not Hero's. Hero's side-B trail numbers (`tex_brave_sword*`, tip,
  `1.4` width, `-90` roll) are donor values against her textures and must be re-derived per blade
  the way `chrom_jab.rs` derives `JAB_TRAIL_TIP` from Mythra's 14.5. Per-state blade length, same
  shape as the jab's `jab_open` clip plus a size constant, guarded against drift between the Rust
  and Python copies.
- Guard at load: `assert_eq!` the first id against `FIGHTER_ELIGHT_STATUS_KIND_NUM`, as
  `mythra::status_id_for` and `status::judge` already do, so a toolchain bump fails at boot rather
  than overwriting a real Mythra status.

## Native prerequisite / hand-back (2026-09-30)

User authorized the three proposed side-B native sites on 2026-09-30.
Concrete evidence: `refs/brave_special_s/native_dependency_audit.{json,asm.txt}`,
reproduced by `tools/audit_hero_side_b.py --check`. See canonical findings in
`refs/brave_special_s/SOURCE_STATUS.md` section 5. Proposed scope: signature-checked,
plugin-local replacements for spark/lightning descriptor initializers
`main+0x85d580` / `main+0x85dad0`, using copied donor algorithms with owned
recipient status/work/parameter callbacks; forward all real Hero calls.
Spark class callback `main+0x33cbb20` needs a separately audited owned parameter
route for its `+0x1298` dependency. Full class/collision coverage is still required;
these three sites are not claimed to be the complete hook set. Additional sites
still require hand-back under rule 17. Registration source is now present but
disconnected until owned handlers and all dependencies are complete. Six exact
spark/lightning motion lists are missing; see `dumps/MISSING.md` (rule 2).
No framework rebuild, donor-fighter cast, recipient SP read or stand-in article.
Resource inventory E and standalone F report were absent at review. The brief F
gauge-reachability conclusion is unverified; mana remained excluded by design at this point
(see the T-0057 section at the end of this file for what changed).
Before a future diagnostic package, require file logging enabled: current recorded
0.20.10 is the silent build. Build/package/install still need separate user authorization.
# Hero side-B reserved interception review (2026-10-01)

Approve or reject a fourth native site: Mythra fighter receiver class +0x170,
slot `main+0x4fb2110`, original `main+0xa2a000`. Required scope is a costume-gated
owned lightning event translator with original forwarding, signature checks and
file logging. Evidence: `refs/brave_special_s/SOURCE_STATUS.md` section 7 and
`tools/audit_hero_side_b_link_events.py --check`. No framework rebuild or Hero
fighter cast is proposed. 2026-10-01: implemented in `receiver.rs` (header says user-approved) and
shipped in package 0.20.15; the user must confirm the approval before installation.

# Snake up tilt (AttackHi3) on Pyra c06/c07 - IMPLEMENTED 2026-10-02 (Freebuff slot 2), not installed

**Status: implemented, audited, READY for the collective build; not packaged and not
installed by me (AGENTS.md rule 23).** Installer section, hashes and the 12-step console
test: `CURRENT_INSTALL.md`, "Snake up tilt (AttackHi3) on G&W c06/c07". Delta audit:
`evidence/2026-10-02_pgwr_snake_uptilt/SNAKE_UPTILT_DELTA.json`. Plugin NRO
`75deff8de447f8f4d171539d8791f046e5c190a60901b05b5ec9ddef809dc313` (compiles, no errors).

What the "next steps" below asked for, and what actually happened:

1. `plugin/src/acmd/snake_attack_hi3.rs` - done. **The `AttackHi3.txt` it needed was no
   longer in this workspace**: `dumps/scripts/SSBU-Dumped-Scripts-main/` is gone (only
   `ParamLabels.csv` and `gamewatch_motion_list.yml` are left) and the external export
   `paths.toml` points at holds almost no files. Rather than approximate the script
   (rule 17), the donor text was re-pinned from the commit this project already pins
   (`refs/snake_attack_hi3/donor_acmd/`, manifest with per-file sha256), and R.O.B.'s
   `AttackLw3.txt` was pulled at the same commit as a control - the shipped
   `acmd::robot_attack_lw3` was written from exactly that file, which is how the dump's
   conversion errors were judged before any line was ported. Snake's AttackHi3 has no
   branch, no lost braces, no article call and no work-id write, so nothing was dropped.
2. `src/pgwr/tools/build_snake_uptilt.py` - done, and it additionally **measures that the
   leg chain moves** (see the "check the legs" note below) and refuses to write a clip
   whose `LegL/R`, `KneeL/R`, `FootL/R` or `ToeL/R` is static.
3. `tools/merge_snake_uptilt_sound.py` - done, chained after the R.O.B. down-tilt merge,
   with the sequence append idempotent and tone preservation asserted against a
   deliberately damaged bank.
4. `tools/audit_snake_uptilt_delta.py` - done, passes against the installed 0.20.17.

One thing measured that this section did not anticipate: **the clip's 48 frames, against a
cancel frame of 38.** The donor's expression script ends at frame 32 and the motion entry
cancels at 38, so the last six frames of the clip are never played. That is Snake's own
arrangement, taken whole, and it is *not* changed here.

Original section follows, kept as the record of what was pinned on 2026-10-01.

---

User request: give G&W (replacing Pyra on c06/c07) Snake's up tilt. The console was
powered on, so everything the port needs was pulled live over arc-network instead of
waiting for the next dump. **Nothing is implemented and nothing was installed** - this
is the pinned donor set only (AGENTS.md rule 23: development agents do not install).

## Pinned (tier B, `refs/snake_attack_hi3/`)

Extracted 2026-10-01 via `tools/fetch_arc_files.py --set snake_attack_hi3`, 8/8 files,
0 failures, re-verified with `--check`: `c02attackhi3.nuanmb` (45,760 B), Snake body
`motion_list.bin` (764 entries), `model.nusktb` (97 bones), the two AI attack params,
and `vc_snake_c00` (audio/bank/label). Provenance: `refs/snake_attack_hi3/SOURCE.json`,
per-file sha256 in `extraction.json`.

Already in the workspace, deliberately not re-copied (rule 29): the ACMD text at
`dumps/scripts/SSBU-Dumped-Scripts-main/smashline/lua2cpp_snake/snake/AttackHi3.txt`;
`se_snake_c00.*` and `snake.sqb` in `refs/snake_grenade/`; `dumps/arc/fighter/snake/param/*.prc`.

## Measured (`tools/audit_snake_hi3_donor.py`, report `refs/snake_attack_hi3/inventory.json`)

* Snake's raw `attack_hi3` entry: **cancel frame 38, flags 0x84, blend 0**, game_script
  `0xef3bca119`, one animation `0x138caf3e29` = `c02attackhi3.nuanmb`. The dtilt took its
  cancel frame 15 from R.O.B. the same way; 38 is the number to use here.
* Clip groups: Transform 87, Visibility 26, Material 2. Every transform node exists on
  Snake's own skeleton, so clip and skeleton are the same revision.
* Against the built recipient (eflame c06/c07, 165 bones): **77 of 87** transform nodes
  kept, no case-only matches, 10 dropped (`FaceN` and the nine `S_Bandanna*` nodes) -
  same shape as the R.O.B. dtilt retarget.
* Sounds: `se_snake_attackhard_h01` and `seq_snake_rnd_attack` both resolve in pinned
  material (read by CRC through `tools/merge_hero_neutral_b_sound.py`, not grepped), and
  **neither is in `se_eflame_c06`/`c07` or `eflame.sqb` in `builds/pgwr/0.20.15`** - the
  neutral-B merge added nine other Snake tones. The merge step is still owed.
* No `attack_hi3` entry in Snake's `vl.prc`: the move is inline hitboxes plus the motion
  list, so there is no param to port.

## Deliberate non-issues (do not "fix" these)

* The script writes hitbox bones `top`, `kneel`, `legl`; eflame's built skeleton names
  `LegL`/`KneeL` and has no `top` bone. G&W's own up tilt - what runs on c06/c07 today -
  also writes `top`, so this is the working convention, not a defect. Remapping would
  diverge from what already ships. **Re-measured 2026-10-02 on the built c06/c07 skeleton:
  all three names are absent** (`refs/snake_attack_hi3/inventory.json`). That was left
  alone deliberately and is now step 9 of the manual console test, i.e. the one open item
  on this move: if the boxes land at the fighter's origin, remapping `kneel`/`legl` to
  `KneeL`/`LegL` is the single next change.
* Only `sys_attack_arc_b` and `sys_turn_smoke` are spawned, both common-bank, so
  `ef_snake.eff` was not pulled.
* `AttackHi3` is a vanilla status kind: **no new status id**, unlike neutral-B's
  `0x1FB..0x207`. Next free Pyra id stays `0x208`.

## Next steps (implementation, not done)

1. `plugin/src/acmd/snake_attack_hi3.rs` from `AttackHi3.txt`, following
   `acmd/robot_attack_lw3.rs`; no G&W article or work-id lines exist to drop.
2. `src/pgwr/tools/build_snake_uptilt.py` modelled on `build_robot_dtilt.py`: pin the
   clip hashes, retarget 87 -> 77 nodes, G&W idle visibility, drop the Material group,
   write over eflame's own `c02attackhi3.nuanmb` for c06/c07, and replace the
   `attack_hi3` motion entry with Snake's raw one (cancel 38, flags 0x84).
3. `tools/merge_snake_uptilt_sound.py` chained after the Snake neutral-B merge to append
   `se_snake_attackhard_h01` to both Pyra banks and the `seq_snake_rnd_attack` record.
4. Offline checks mirroring the dtilt: `tools/audit_snake_uptilt_delta.py`, existing 457
   tones per bank preserved, built vs packaged NRO equality, baseline delta audit.
5. Only then does this become a READY section in `CURRENT_INSTALL.md`. Rule 11: ship the
   up tilt on its own, not stacked with another state-changing change.

# Hero mana on the c06/c07 pair - T-0057 (2026-10-02, Freebuff slot 3)

**Done, compiles, not packaged, not installed, no console run.** The playable meter is
in `src/pgwr/plugin/src/mythra/hero_mana/`; the numbers came out of the donor `vl.prc`
(sha256 `dafa43c6...`) rather than out of anyone's memory. Evidence
`refs/brave_special_n/T-0057/SOURCE.md`; readiness, hashes and a twelve-step console test
in that task's own section of `CURRENT_INSTALL.md`.

**What was actually wrong:** nothing. The Hero moves shipped with the donor's
affordability gate hard-wired to "yes" and no MP value, so there was no mana system to
break. T-0046/T-0049 stopped at BLOCKED waiting for the six prices, and the only reason
they were hard to get is the dead end in `handbook/graveyard.md` R-HERO-MANA-2.

**Left, and why:**

1. **The HUD gauge.** Reserved. The useful new fact: the vanilla fighter HUD *already*
   has the MP gauge - `blyt/info_melee_lct_player_sp.bflyt`, panes `sp_00..sp_03`, the
   `info_melee_lct_player_*_sp` animations, `MELEE_GAUGE_SP_GET/USE` - so an approved
   build authors no assets. What is still missing is the interception and its ABI.
   `src/pgwr/plugin/src/mythra/hero_mana/hud.rs` is the hand-back, behind
   `hero-mana-reserved` (off).
2. **Recovery on being hit or blocking.** Reserved, same feature. The recipient owns no
   path that sees this fighter being hit. `.../hero_mana/damage.rs` is the hand-back.
3. **A real frame clock.** No in-bindings one exists. The per-frame advance uses the
   crate's usual `on_line(Main)` and says so in the module docstring; the log's `TICK`
   rate line is the measurement that would catch it firing twice per frame.
4. **The out-of-MP failure effect and sound.** The pinned status dumps carry no effect
   names, so nothing was invented in their place. The move visibly fails, which is the
   donor's own shape, but the cosmetic is not the donor's yet.

**If the next agent picks this up:** do not re-derive the prices, they are pinned with the
key each one is read by, and `tools/dump_hero_mana_params.py` regenerates the report. Do
not add a second meter for the Pyra half - the entry-keyed table is what makes the swap
free. Do not re-derive the gate either; `refs/brave_special_s/flag_success_sp.c` is the
pin, and the two rules that matter are "debit only on success" and "the finisher does not
debit".
