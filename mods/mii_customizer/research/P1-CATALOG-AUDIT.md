# P1-CATALOG-AUDIT - slot grouping and timing fields

Task: P1-CATALOG-AUDIT. Worker: Space Bunny Alpha. Date: 2026-10-04.
Prompt: `prompts/P1-CATALOG-AUDIT.md`. Phase: `phases/01_discovery.md`.

Goal: make the Gunner slot inventory dependable enough for a UI to consume, by
(a) settling `attack_s3_s` vs `attack_s4_s`, (b) adjudicating the suspicious timing
fields, and (c) producing one corrected user-facing slot table.

Evidence tiers: **B** = measured offline by scripts that still exist; **D** =
hypothesis. **No A** - nothing was run on hardware or in an emulator.

Paths are workspace-relative. Inputs, hashes, controls and commands:
`evidence/P1-CATALOG-AUDIT/EXTRACTION.md`. Scripts:
`scratch/2026-10-04_P1-CATALOG-AUDIT/`. `research/P1-CATALOG.md` was corrected in
place; the corrections are marked in that file and listed in §5 here.

P1-ID was left untouched: nothing here reads identity, saved-Mii, save-format or
native UI-binding material.

---

## 1. Method: what made this decidable

The previous report could not settle the side-tilt question because it only ever
looked at the Gunner file, where nothing is named beyond the motion kind. The
missing control was already in this workspace:

- `mods/ssbu_mod_new/dumps/scripts/gamewatch_motion_list.yml` is a **decoded field
  listing** for GameWatch body c00 - `game_script`, `blend_frames`, `xlu_start`,
  `xlu_end`, `cancel_frame`, `no_stop_intp` per kind, 746 kinds.
- `gamedata/ssbu-13.0.4/files/fighter/gamewatch/motion/body/c00/motion_list.bin`
  is that fighter's actual binary (sha256 `306be009edb4...`).

So the raw reader can be checked against *named* fields for a real fighter instead of
against its own round trip. That control answers both open questions at once, and it
is the reason the timing values could be interpreted rather than merely re-reported.

One caution carried from `handbook/04`: motion names hash **with** the file extension
and the `size` tail is not fully decoded, so nothing here assumes a field's meaning
from its position. Each field below is identified by agreeing with a labelled value.

---

## 2. Forward tilt: `attack_s3_s` is the side/forward tilt

**Verdict: the coordinator's objection is answered. The Gunner has a forward/side
tilt. It is `attack_s3_s`. The forward smash is `attack_s4_s`.** `B`.

The strongest single piece of evidence is that Gunner's two entries carry exactly
GameWatch's two entries, down to the game-script hash and the clip hash, so the
names GameWatch's decoder produced apply verbatim:

| field | Gunner `attack_s3_s` | GameWatch `attack_s3_s` | Gunner `attack_s4_s` | GameWatch `attack_s4_s` |
|---|---|---|---|---|
| kind hash | `0xb7dd72b57` | `0xb7dd72b57` | `0xb78983dd2` | `0xb78983dd2` |
| game script | `0xd28325277` = `game_attacks3` | `0xd28325277` | `0xdb656c7d4` = `game_attacks4` | `0xdb656c7d4` |
| clip | `c01attacks3s.nuanmb` | `c01attacks3s.nuanmb` | `c03attacks4s.nuanmb` | `c03attacks4s.nuanmb` |
| flags | `0x0080`, `move = false` | `0x0080`, `move = false` | `0x0084`, `move = true` | `0x0084`, `move = true` |
| decoded cancel | 37 | 38 | 78 (raw 334) | 43 (raw 43) |

Three independent readings agree:

1. **Script naming.** `hash40("game_attacks3") == 0xd28325277` is the game script of
   Gunner's `attack_s3_s`, and `hash40("game_attacks4") == 0xdb656c7d4` is that of
   `attack_s4_s`. The `_s` in the kind name is a naming form; the script name drops it.
   `attack_100` in GameWatch makes the same point (script `game_attack1`).
2. **The `move` flag.** GameWatch's decoder names flag `0x0004` `move`. It is false
   for `attack_s3_s` and true for `attack_s4_s`. Smashes move the fighter; tilts do
   not. This is a labelled boolean, not an inference.
3. **The charge partner.** `attack_s4_s` has a `attack_s4_hold` partner
   (`c03attacks4charge.nuanmb`, script `game_attacks4charge`), and `attack_s3_s` has
   none. A smash is a chargeable two-entry slot; a tilt is one clip. Same pattern
   holds for `hi4`/`lw4` versus `hi3`/`lw3`.

**Provenance, exactly.** Kind names come from the entry hashes via
`ParamLabels.csv`. Script names come from `hash40` of the kind-name form and are
**confirmed** by equality with the GameWatch decoder's output. Clip names come from
P1-CATALOG's closed-set hash join over `arc_files.tsv`. No script *body* was read -
`dumps/scripts/SSBU-Dumped-Scripts-main` is absent from this workspace - so this is
naming and structure evidence, not behaviour evidence.

**Directional variants: measured absent, not assumed.** The prompt asked about
directional variants, and a missing local script body is not proof a move is absent -
so this was checked as a presence question against both binaries:

| variant kind | GameWatch | Gunner |
|---|---|---|
| `attack_hi3_l` | present | **absent** |
| `attack_hi4_r` | present | **absent** |
| `attack_s3_l` / `_r` / `_f` / `_b` | absent | absent |
| `attack_hi3_f` / `_b` / `_r` | absent | absent |

Gunner's tilt and smash families are **single-entry per direction**: one forward
tilt clip, one forward smash clip, one up tilt, one down tilt. GameWatch's
`attack_hi3_l` and `attack_hi4_r` show the *form* exists in the engine, so Gunner's
absence is a real per-fighter authoring difference rather than a naming artefact.
`B`, for presence in these two files only.

**Caveat that is not resolved.** Whether the *engine* falls back to `attack_s3_s` for
both forward and back tilt input, or whether the back tilt is driven by a kind with
no separate clip, is not settled by a motion list. That needs script or ACMD bodies.

---

## 3. The timing fields: 334 and 318 are not frame counts

**Verdict: the `cancel` column in `P1-CATALOG.md` was wrong. The field packs two
values in one `u16`.** `B`, 746/746.

The reader reports the last two bytes of the entry tail. Comparing it to GameWatch's
decoded fields over all 746 shared kinds:

| check | result |
|---|---|
| `game_script` hash agrees with the decoded name | **746/746** |
| `blend_frames` agrees | **746/746** |
| `cancel_frame` agrees with the raw reader | 728/746 |
| `cancel_frame` agrees with the reader **masked by `~0x100`** | **746/746** |

Every one of the 18 disagreements is exactly `+256`. That is not a coincidence of
rounding: bit `0x100` of the field is the `no_stop_intp` boolean, and it lines up with
the decoder's own boolean in **746/746** cases (728 false/false, 18 true/true).

So the trailing field is a `u16` whose low byte is `cancel_frame` and whose bit
`0x100` is `no_stop_intp`. In the 28-byte tail the last four bytes are four separate
bytes, confirmed byte-wise against the decoded field names:

| tail offset | field | agreement with GameWatch decoder |
|---|---|---|
| `+24` | `xlu_start` | 746/746 |
| `+25` | `xlu_end` | 746/746 |
| `+26` | `cancel_frame` | 746/746 |
| `+27` | `no_stop_intp` | 746/746 |

and the first 24 bytes are three `u64` **script-name hashes** - verified by name, not
by position: for GameWatch `attack_s3_s` the tail's three `u64` are
`expression_attacks3` `0x137f8a3d23`, `sound_attacks3` `0xe43cef37d`,
`effect_attacks3` `0xfb1b90bcf`, in that order. (`_l` forms do not match, which is the
expected discriminator.)

### The two suspicious values, resolved

| kind | raw `u16` | `cancel_frame` | `no_stop_intp` | GameWatch same kind |
|---|---|---|---|---|
| `attack_s4_s` (forward smash) | 334 | **78** | 1 | 43 |
| `attack_air_hi` (up air) | 318 | **62** | 1 | 42 |

Under the corrected reading they sit inside the file's normal range, and the masked
distribution collapses from a strange 256/264/271/297/306/318/334 cluster to
**0-81**, with no value above 81 anywhere in the list. 19 Gunner entries were affected
in total; the rest of the file was already correct, which is exactly why the original
table looked anomalous in only two places.

**Round-trip equality proved nothing here.** `encode(parse(x)) == x` held for both
files and would have held under either reading - it shows byte preservation, not
field identity. The coordinator's point that "round-trip equality alone is not
semantic validation" is confirmed and was the reason for building the GameWatch
control.

**What is still not established.** These are the *authored* values in the file. They
are not a measurement of the fighter's actual cancel window in a match: `handbook/04`
already records a clip outlasting its own cancel frame (Snake up tilt), and a clip
that fails to load leaves the previous clip playing. So `cancel_frame` here is a
per-fighter parameter to copy, not frame data to promise a player.

---

## 4. Candidate user-facing slot table

Corrected, compact, with dependencies grouped. All rows `B`, from Gunner body c00
(sha256 `2b7ed9b6b17a...`). `xlu_s`/`xlu_e` are `xlu_start`/`xlu_end`.

**This is a candidate for a UI, not a claim the game routes these slots that way.**
`P1-ID` and native binding remain untouched.

### Group A - normals (one slot each)

| slot id | kind | game script | cancel_frame | notes |
|---|---|---|---|---|
| `jab_1` | `attack_11` | `game_attack11` | 26 | |
| `jab_2` | `attack_12` | `game_attack12` | 26 | |
| `jab_3` | `attack_13` | `game_attack13` | 38 | |
| `dash` | `attack_dash` | `game_attackdash` | 46 | |
| `tilt_up` | `attack_hi3` | `game_attackhi3` | 38 | no directional variant in Gunner |
| `tilt_side` | **`attack_s3_s`** | `game_attacks3` | 37 | **forward tilt**, no variant |
| `tilt_down` | `attack_lw3` | `game_attacklw3` | 41 | |

### Group B - smashes (a smash is a **state pair**, not one slot)

| slot id | release kind | hold kind | release cancel | dependency |
|---|---|---|---|---|
| `smash_f` | `attack_s4_s` | `attack_s4_hold` | 78 (`nsi`=1) | hold + release must ship together |
| `smash_up` | `attack_hi4` | `attack_hi4_hold` | 56 | same |
| `smash_down` | `attack_lw4` | `attack_lw4_hold` | 53 | same |

All three holds carry `cancel_frame = 0`. A UI that offers "forward smash" must treat
the charge as part of the same slot; offering one without the other is an incomplete
slot.

### Group C - aerials (**five separate selectable slots**, one per direction)

| slot id | kind | game script | cancel_frame | matching landing kind |
|---|---|---|---|---|
| `air_neutral` | `attack_air_n` | `game_attackairn` | 42 | `landing_air_n` |
| `air_forward` | `attack_air_f` | `game_attackairf` | 42 | `landing_air_f` |
| `air_back` | `attack_air_b` | `game_attackairb` | 48 | `landing_air_b` |
| `air_up` | `attack_air_hi` | `game_attackairhi` | 62 (`nsi`=1) | `landing_air_hi` |
| `air_down` | `attack_air_lw` | `game_attackairlw` | 55 | `landing_air_lw` |

Each direction has its own kind **and** its own `landing_air_*` entry, all five
landings at `cancel_frame` 20. Replacing an aerial therefore implies reviewing its
paired landing entry - that pairing is a real dependency, not a naming coincidence,
since the five landing kinds are distinct.

### Group D - grab, pummel, throws

| slot id | kind | game script | cancel_frame | dependency |
|---|---|---|---|---|
| `grab` | `catch` | `game_catch` | 35 | start of the grab chain |
| `grab_dash` | `catch_dash` | `game_catchdash` | 43 | |
| `grab_turn` | `catch_turn` | `game_catchturn` | 38 | flags `0x0081` |
| `grab_pull` | `catch_pull` | `game_catchpull` | 2 | victim-side `capture_*` is separate |
| `grab_wait` | `catch_wait` | `game_catchwait` | 0 | flags `0x0002`, **blend 6** |
| `pummel` | `catch_attack` | `game_catchattack` | 7 | |
| `grab_cut` | `catch_cut` | `game_catchcut` | 30 | the escape; pairs with Group D victim kinds |
| `throw_forward` | `throw_f` | `game_throwf` | 34 | needs victim `thrown_f*` |
| `throw_back` | `throw_b` | `game_throwb` | 50 | needs victim `thrown_b*` |
| `throw_up` | `throw_hi` | `game_throwhi` | 52 | needs victim `thrown_hi*` |
| `throw_down` | `throw_lw` | `game_throwlw` | 41 | needs victim `thrown_lw*` |

Dependency, per `handbook/04` fact 4: attacker throw entries and victim `thrown_*`
reactions are **separate entries** in the same file. A throw slot is not shippable
without its victim side. `catch_wait` is the only entry in this whole table with a
non-zero `blend` (6) - worth remembering if blending is ever read.

### Group E - specials (three alternatives per direction, each with its own states)

| direction | alternative | kinds | state count | variant |
|---|---|---|---|---|
| neutral | 1 | `special_n1_start/hold/cancel/fire/fire_max` | 5 | `fire` and `fire_max` name the **same clip** - one charge level, two kinds |
| neutral | 2 | `special_n2_start/loop/end` | 3 | air mirror present |
| neutral | 3 | `special_n3_start/end` | 2 | air mirror present |
| side | 1 | `special_s1` | 1 | single clip |
| side | 2 | `special_s2_start/loop/end` | 3 | air mirror present |
| side | 3 | `special_s3_1`, `special_s3_2` | 2 | air mirror present |
| up | 1 | `special_hi1` | 1 | |
| up | 2 | `special_hi2` + `special_hi2_squat` | 2 | air mirror; squat has `xlu_s`=7 `xlu_e`=13 |
| up | 3 | `special_hi3_start`, `special_hi3`, + `...3f` / `...3b` | 3 clips | **has directional clips**; `...3f`/`...3b` kinds still unnamed |
| down | 1 | `special_lw1_start/loop/hit/end` **+ `_l` forms** | 8 | left-side sub-variant, ground **and** air |
| down | 2 | `special_lw2` | 1 | single clip |
| down | 3 | `special_lw3_start/hold/hit/end` | 4 | air mirror present |

Measured this task, and it matters for slot design: every `special_lw1_*` `_l` kind
shares its base kind's `game_script` hash **exactly** (`start`/`start_l` both
`0x148e2088ad`, `loop`/`loop_l` both `0x13f9896335`, `hit`/`hit_l` both
`0x12e4e0ec7c`, `end`/`end_l` both `0x12becef98c`) and differs only in clip. So the
down-special-1 `_l` variant is a real per-direction state, not an alias of the base.

The up-special `special_hi3` is the only player-facing family with directional
**clips** (`d02specialhi3`, `...3f`, `...3b`). Two of the three kind names are still
unresolved; they are recorded by clip and hash (`0x0d3aaf0366` on `d02specialhi3f`,
`0x0d3dc2c77f` on `d02specialhi3b`) and must not be guessed into a UI label.

### Group F - explicitly **pending a scope decision**, not dropped

Not offered in the table above, listed so the coordinator decides rather than the
table deciding silently.

| item | kinds | what is measured | what is missing |
|---|---|---|---|
| Final Smash | `final_start/final/final_end`, `final_air_*`, `final_u/final_d`, `final_air_u/d` (10) | all present and named, indices 159-168 | **naming trap**: `motion/fullthrottle/c00/` owns clips with the *same* `d04final*` names; those are Full Throttle's, not Final Smash's dependency |
| Get-up attacks | `down_attack_u` (301), `down_attack_d` (310), plus `down_forward_u/d`, `down_back_u/d` | present, named, `xlu_s`=1, `xlu_e`=23 (`_u`) / 24 (`_d`), cancel 46 | **one slot or several is a coordinator decision**; the four directional kinds make a single get-up entry lossy |
| Ledge / cliff | `cliff_catch` (339), `cliff_wait` (340), `cliff_attack_quick` (342), `slip_attack` (350), `slip_escape_f/b` (351/352) | these six named | four kinds on `g02cliffclimb`, `g02cliffescape`, `g02cliffjump1/2` unresolved |
| Taunts | six `appeal_*` kinds, 260-265, cancel 50 | named, clips `j01appeal*` | also `win_*`, `lose`, `menu_pose*`, `entry_*`, `share_*`; scope undecided |

### AI attack list - a cross-check that does **not** work

Checked, as instructed, and reported as a negative result rather than quietly dropped.

`fighter/miigunner/ai/param/attack_list_param.prc` (2,530 scalars, 0 unlabelled keys)
contains **zero** occurrences of any Gunner `attack_*` motion-kind hash - checked
`attack_s3_s`, `attack_s4_s`, `attack_hi3`, `attack_11`, `attack_air_hi`, `attack_lw3`
explicitly. Its 34 attack keys are AI **input/action** fields
(`attack_quick_s`, `attack_power_s`, `attack_air_f_e`, `attack_ground_feint`,
...), a different vocabulary from motion kinds. `attack_quick_s` and `attack_power_s`
are not tilts and smashes; they are AI decision weights.

So the AI list **cannot** be used to classify player-facing slots, and
`research/P1-CATALOG.md` §9's suggestion that it was "the obvious next input" for this
question is wrong. The motion list plus the decoded GameWatch control above is what
settled the slot table. Corrected in place.

---

## 5. Corrections made to `research/P1-CATALOG.md`

All in place, uncertainty preserved:

1. **§2 table rewritten** with `cancel(raw u16)`, `cancel_frame` and `no_stop_intp`
   columns. `attack_s4_s` 334 -> 78, `attack_air_hi` 318 -> 62.
2. **§2 side tilt resolved**: `attack_s3_s` is the forward tilt, with its game script
   `game_attacks3` and the evidence chain; the "classification pending audit" label is
   replaced by the verdict. `attack_hi4f`/`attack_hi4b` remain the wrong search names,
   as originally noted.
3. **§2 game scripts filled in**: the `-` cells for `attack_s3_s`, `attack_s4_s`,
   `attack_s4_hold`, `attack_lw4`, `attack_hi4`, `attack_air_hi`, `attack_air_lw` and
   the holds are now named.
4. **§2 anomalous-value note removed** and replaced by the packing explanation, with
   the per-fighter-authored caveat.
5. **§3 side specials**: `special_s3_1` 297 -> 41 frames, `special_s3_2` 306 -> 50.
6. **§3 down-special-1**: added the measured `_l` game-script equality.
7. **§7 stat table**: adopted the coordinator's correction explicitly - weight is not
   gravity or fall speed; `air_speed_y_stable` is a terminal cap, not floatiness;
   assess weight by controlled knockback.
8. **§9 gap 5 reversed**: the AI attack list cannot classify slots; the earlier
   "obvious next input" claim is marked wrong rather than left standing.
9. **§10 summary**: "whether a side tilt exists at runtime despite having no motion
   kind" is moved from unresolved to resolved.

Nothing was deleted for being inconvenient. The unresolved kind names for the two
up-special directional clips stay unresolved and are still recorded by clip and hash.

---

## 6. Limitations

1. **No A evidence.** No console, no emulator, no build. Nothing here shows the game
   *reads* these values in a match. Everything is file-level.
2. **The `cancel_frame` / `no_stop_intp` / `xlu_*` semantics are validated for
   GameWatch body c00 and applied to Gunner on the strength of identical layout.**
   `B`, but it is an inference across fighters, not a separate Gunner decode. A second
   decoded reference would make it airtight.
3. **`c06`/`c07` were not decoded.** Only `body/c00` was read. P1-CATALOG's gap 3
   stands: check the other costume sets before assuming one script per slot.
4. **Script bodies are unavailable** (`dumps/scripts/SSBU-Dumped-Scripts-main` absent).
   So: which helper motion list belongs to which special alternative, what each
   special actually does, hitboxes, damage, and whether back tilt reuses
   `attack_s3_s` all remain open. No claim above depends on a script body.
5. **Directional-variant absence is scoped to these two files.** Gunner lacks
   `attack_hi3_l`/`attack_hi4_r` that GameWatch has. That is a measured difference in
   the motion lists, not proof about runtime input handling.
6. **`no_stop_intp`'s runtime meaning is unknown.** The bit is identified by
   correlation with the decoder's boolean label. What it does to interpolation at
   runtime is not established.
7. **Which helper belongs to which special alternative is still unlinked**, so the
   Group E rows describe motion states, not move behaviour.
8. **Untouched by design:** saved-Mii identity, save format, native UI binding
   (P1-ID's lane). Also not done: `vl.prc` per-move `hit_data` mining, `c06`/`c07`,
   Final Smash / get-up / ledge / taunt scope decisions.

---

## 7. Suggested next step

One cheap, high-value input remains before Phase 2 chooses a slot schema: **decode
`fighter/miigunner/motion/body/c06/motion_list.bin`** (already indexed, not read) and
diff it against `c00`. That settles limitation 3 with one existing file, and would
confirm or break the "one script per slot per costume set" assumption the slot table
quietly relies on. It does not require P1-ID and does not overlap it.

Escalation to a premium model is **not** requested. Nothing found here needs native
RE; the open questions need script bodies or a measurement, not a disassembly.

---

## Summary

- **P1-CATALOG-AUDIT: DONE.**
- **Changed files** (all inside this task's exclusive write paths):
  - `mods/mii_customizer/research/P1-CATALOG-AUDIT.md` (this report)
  - `mods/mii_customizer/research/P1-CATALOG.md` (corrections only, §5 lists all nine)
  - `mods/mii_customizer/evidence/P1-CATALOG-AUDIT/EXTRACTION.md`
  - `mods/mii_customizer/evidence/P1-CATALOG-AUDIT/reader_vs_gamewatch_decoded_yaml.txt`
  - `mods/mii_customizer/evidence/P1-CATALOG-AUDIT/cancel_field_adjudication.txt`
  - `mods/mii_customizer/evidence/P1-CATALOG-AUDIT/tail_layout_and_variants.txt`
  - `mods/mii_customizer/evidence/P1-CATALOG-AUDIT/representative_entries_raw.txt`
  - `mods/mii_customizer/evidence/P1-CATALOG-AUDIT/report_claims_verification.txt`
  - `mods/mii_customizer/evidence/P1-CATALOG-AUDIT/catalog_script_name_verification.txt`
  - `mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/` (7 scratch scripts,
    disposable)
- **No new extraction.** The optional `gamedata/mii_customizer/P1-CATALOG-AUDIT/`
  path was not needed and was not created. No shared tool, dump or production file was
  modified; the shared reader was imported read-only.
- **Observed checks:** GameWatch decoder agreement 746/746 for `game_script`,
  746/746 for `blend_frames`, 728/746 raw for cancel and **746/746 masked**;
  `no_stop_intp` correlation 746/746; tail byte layout 746/746 at each of the four
  offsets; `expression`/`sound`/`effect` hashes matched by name; round trip equal for
  both motion lists; both input hashes re-verified and matching the coordinator's.
  Every quantitative claim marked **B** in this report is re-derived and asserted by
  `scratch/2026-10-04_P1-CATALOG-AUDIT/check_report_claims.py`
  (evidence `report_claims_verification.txt`). It caught one wrong claim in an earlier
  draft of this report - `down_attack_d` `xlu_end` is 24, not 23 - which was fixed
  before publication; that script now passes with 0 failures.
- **All 29 `game_*` names written into the corrected tables verified by hash**
  (evidence `catalog_script_name_verification.txt`):
  `hash40(name)` equals the entry's own `game_script` field for all 18 normal-attack
  scripts and all 11 grab/pummel/throw scripts. A negative control confirms the
  plausible-but-wrong forms (`game_attack_s3_s`, `game_attacks3_s`, `game_attack_s3`,
  `game_attacks4_s`, `game_attack_s4_s`) match neither `attack_s3_s` nor
  `attack_s4_s`, which pins the naming rule: drop the `_s` suffix and the underscore
  before the digit, then prefix `game_` (`attack_s3_s` -> `attacks3` -> `game_attacks3`).
  Result: **0 failing script-name claims**.
- **Verified (B):** `attack_s3_s` is the forward/side tilt and `attack_s4_s` the
  forward smash; the trailing `u16` packs `cancel_frame` with `no_stop_intp` at bit
  `0x100`; `attack_s4_s` = 78 frames, `attack_air_hi` = 62; Gunner has no
  `attack_hi3_l`/`attack_hi4_r`; the `special_lw1_*` `_l` kinds share their base
  game-script hash; the AI attack list contains no motion-kind hashes; all 29
  `game_*` script names in the corrected tables hash to their own entries.
- **Unverified (D / unestablished):** any runtime behaviour of these values; which
  helper belongs to which special alternative; back-tilt routing; `no_stop_intp`'s
  runtime meaning; `c06`/`c07` layout; scope of Final Smash, get-up, ledge, taunts;
  the two unnamed up-special directional kinds.
- **Blockers:** none.
- **Next question for the coordinator:** should the slot table treat **get-up attacks**
  as one slot or as five (`down_attack_u/d` plus `down_forward_*` and `down_back_*`)?
  The motion list has five distinct kinds, so a single get-up entry would drop four
  of them. This needs a scope decision, not more analysis.