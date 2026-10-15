# pgwr - subagent briefs, Hero side-B (2026-09-30)

Dispatch sheet for the parallel **research** phase of the Hero side-B port. Written by Buffy.

The design phase is done. See `projects/pgwr/TODO.md` (section "Hero side-B status id allocation")
and `refs/brave_special_s/SOURCE_STATUS.md` for what is already established. Briefs **A-E** are for
subagents; **F was done by Buffy on 2026-09-30** and is summarised at the end.

These are task briefs, not a handoff. The handoff stays `projects/pgwr/STATUS.md`.

## Rules that bind every subagent below

Read `AGENTS.md` first, in full. It is short and every rule in it has a recorded failure behind it.

* **Read-only research.** No brief here authorises editing source, building, installing, or touching
  the SD card. If a brief seems to need a code change, stop and report that instead.
* **`dumps/` is read-only** (rule 2). Derived data goes to `refs/brave_special_s/` with the tool and
  version that produced it, or to your own `scratch/2026-09-30_<yourname>/` (rule 3).
* **Do not edit shared state.** Off limits for every subagent: `src/pgwr/plugin/**`,
  `src/pgwr/build.py`, `src/pgwr/Cargo.toml`, any `config.json`, `projects/pgwr/STATUS.md`,
  `projects/pgwr/TODO.md`, `handbook/**`, `dumps/**`. Write **only** the one output file named.
  Reason: `projects/pgwr/STATUS.md` records that on 0.20.2 a concurrent session had already claimed
  version 0.20.1, and one shared binary ended up carrying two unrelated changes - which breaks the
  one-change-per-hardware-test rule and makes both install records ambiguous.
* **No absolute paths** (rule 4). Use `paths.toml`; scripts derive the root themselves.
* **Every finding carries a tier** (rule 8): A hardware, B measured offline by a named script, C pinned
  third-party source, D hypothesis. A tier-D or offline-only statement may not be phrased as "works",
  "does", "cannot" or "proven".
* **Dumped text is evidence, not code** (section F). WuBoytH ACMD dumps have conversion errors and
  drop arguments - `SpecialS3.txt` contains zero `ATTACK` lines, which is a dump artefact and not a
  design fact. Never conclude "this hitbox does not exist" from a text dump.
* **Python**: `toolchains/py312/python.exe`, never system Python. `ssbh_data_py` is cp312-only.
* **Report back** with: what you established and at what tier, what you could not establish, and the
  exact sha256 of every file you produced. Do not restate the brief back to me.

---

## Brief A - identify the three unknown functions that touch `FLAG_SUCCESS_SP`

**Why:** `FIGHTER_BRAVE_STATUS_SPECIAL_S_FLAG_SUCCESS_SP` decides whether a side-B hit is the SP
variant. It is *read* in the ATTACK1/2/3 MAIN bodies but is **never touched by `SPECIAL_S_HOLD`** in
PRE/MAIN/END/EXEC. Three anonymous functions reference it and are the likely setter. This is the last
unknown standing between the port and a faithful SP release.

**Inputs**
* `dumps/arc/prebuilt/nro/release/lua2cpp_brave.nro` (13.0.4, region 2)
* Const offsets already recovered: `FLAG_SUCCESS_SP` `0xc914`, `WORK_INT_HOLD_FRAME` `0xc958`,
  `FLAG_ACTIVATE_LIGHTNING` `0xc98c`
* `refs/brave_special_s/status_table.txt` (247 rows) - the function-start map
* `refs/brave_special_s/SOURCE_STATUS.md` - the addendum explaining the above

**Addresses to name:** references sit at `0x28d00`, `0x29820` and near `0x2ad40`. No exported symbol
covers `0x20000`-`0x30000` and no status-table row starts there, so these are helpers, not directly
registered status functions.

**Method**
```
GHIDRA_HOME=<from paths.toml> tools/nro_decomp/run_ghidra.sh \
  dumps/arc/prebuilt/nro/release/lua2cpp_brave.nro \
  scratch/2026-09-30_<yourname>/ \
  refs/brave_special_s/flag_success_sp.c 0x28d00 0x29820 0x2ad40
```
First run imports and analyses (~3 min); later runs reuse the project in your scratch dir. Ghidra
11.1.2 lives in the **old** workspace per `paths.toml` - do **not** unpack a copy into this one
(rule 30, disk is scarce). `c++filt` must be on PATH (`paths.toml` `msys2_mingw`).

**Critical:** Ghidra drops `global_table` indices and register-mediated constant loads. The const
offsets reach the code as `mov w8, #0xNNNN` + `ldr w1, [x22, x8]`, **not** as an `ldr` immediate.
Searching for the immediate returns zero references and looks like a clean null result; that trap has
already been hit once here. Confirm const identities from disassembly. See
`tools/nro_decomp/annotate_c.py` and the precedent `refs/brave_special_n/neutral_b_status.c`.

**Output:** `refs/brave_special_s/flag_success_sp.c` (annotated C) **plus**
`refs/brave_special_s/FLAG_SUCCESS_SP.md` stating, per function: entry point, caller if determinable,
whether it sets or clears `FLAG_SUCCESS_SP`, and what else it touches.

**Done when:** each of the three addresses is either named with a caller and a verdict, or explicitly
recorded as unidentifiable with the evidence for that. "I could not decompile it" is a useful result.
A guess is not.

---

## Brief B - bone-by-bone skeleton diff, Hero c06/c07 vs c00

**Why:** clip retargeting matches donor tracks to Mythra's skeleton **by bone name**. The extraction
reported Hero's c06/c07 `model.nusktb` differ from c00 in bytes but never compared the bone *sets*.
If a costume has a bone c00 lacks, or a different name, tracks silently fail to retarget and the move
plays against a stale pose - exactly the R-21 failure in `handbook/graveyard.md`, where a `Sword1`
track in the body clip changed nothing on hardware.

**Inputs**
* `refs/brave_special_s/arc/fighter/brave/model/body/c00|c06|c07/model.nusktb`
* `dumps/arc/fighter/elight/model/body/c06|c07/model.nusktb` (recipients)
* Helper: `tools/probe_bone_names.py` (donor vs recipient naming; run with
  `toolchains/py312/python.exe`). `tools/findhash.py` / `tools/hashscan.py` if hash forms compare
  more easily than strings.

**Output:** `refs/brave_special_s/skeleton_bones.md` - per costume: sorted bone list, diff against c00,
parent map, and a three-way table marking every bone present-in-all / missing-from-recipient /
renamed. Include the sha256 of each `.nusktb` read.

**Done when:** every bone name the side-B clips reference is accounted for, and `sword1` is confirmed
present and compatible in **both** Hero and Mythra - both fighters name the trail bone `sword1`, which
is why the donor's `AFTER_IMAGE4_ON_arg29` calls can retarget by name.

---

## Brief C - is the air side-B just the ground side-B plus a situation check?

**Why:** this sets the real size of the translation job. `SpecialS1.txt` is 534 lines and
`SpecialAirS1.txt` is 532, which *suggests* near-duplication - but that is an eyeball inference, not
a measurement. If air is ground plus situation, the job is roughly half what the line count implies.

**Inputs**
* `dumps/scripts/SSBU-Dumped-Scripts-main/smashline/lua2cpp_brave/brave/` : `SpecialS1` vs
  `SpecialAirS1`, `SpecialS2` vs `SpecialAirS2`, `SpecialS32` vs `SpecialAirS32`
* `refs/brave_special_s/status_table.txt` - confirms there is **no** air-specific side-B status
  (`lua_const.rs` has no `FIGHTER_BRAVE_STATUS_KIND_AIR_S*`), so air is reached from the same six states

**Method:** normalise both files (strip whitespace, rename the function symbol) and diff. Classify
every differing line: situation mask, gravity/kinetic, effect placement, clip name, or genuinely
different hitbox. Watch for conversion artefacts - a line present in one dump and absent in the other
may be a dropped call, not a real difference.

**Output:** `refs/brave_special_s/air_vs_ground_side_b.md` - per-pair diff summary, a verdict per pair
(`identical modulo situation` / `differs, and here is how`), and a final estimate of unique lines to
translate.

**Done when:** someone else could scope the translation from your document without opening the dumps.

---

## Brief D - Mythra's blade length, for the trail tip

**Why (the user asked for this explicitly):** the user decided Mythra keeps her **own** sword. Hero's
side-B trail numbers (`tex_brave_sword*`, trail tip, `1.4` width, `-90` roll) were tuned for *his*
blade. Hers is a different length, so a copied tip detaches the ribbon from the hilt.
`chrom_jab.rs` already solves this by deriving `JAB_TRAIL_TIP` from Mythra's 14.5; side-B needs the
same treatment.

**Measured context**
* Hero stores the blade in his **body** model (`brave_sword_VIS_O_OBJShape`) on a body `Sword1` bone.
* Mythra stores hers in a **separate article**: `FIGHTER_ELIGHT_GENERATE_ARTICLE_ESWORD`, skeleton
  `Root -> HaveR -> Sword1`. Her body model has **zero** sword-named shapes. Her blade length is
  therefore a property of the esword article, not the body.
* The user also decided the trail becomes **hers** (`tex_elight_sword1/2/3`), not Hero's.

**Inputs**
* `dumps/arc/fighter/elight/model/esword/c06/` and `.../c07/` (`model.nusktb`, `model.numdlb`,
  `model.numshb`, `model.numatb`)
* `refs/brave_special_s/arc/fighter/brave/motion/body/c00/swing.prc` and `c06/swing.prc` - the
  extraction found `swing.prc` **differs per costume**; establish whether that matters now that the
  trail is hers rather than Hero's.
* Her existing call sites for comparison: `dumps/scripts/.../lua2cpp_elight/elight/AttackS3.txt` uses
  `tex_elight_sword1` + `sword2` on bone `sword1` with trail tip **15.5**; `Attack12.txt` uses **14.5**.

**CRITICAL - read before modelling.** `src/pgwr/tools/fair_sword_geometry.py` documents a **refuted**
model. Do not treat the blade as rigidly attached to the body bone `Sword1` and rigid along +z: that
was refuted on hardware 2026-09-30 (`handbook/graveyard.md` R-21 - a `Sword1` track in the body clip
changed nothing). The chain that survives both refutations is:

```
owner HaveR (animated by the body clip)
  x article HaveR  (from the article's own clip - constant in every sword state)
  x article Sword1 (from the article's own clip - also constant)
```

Measure with forward kinematics over that chain; extend `fair_sword_geometry.py` rather than writing a
new estimator.

**Output:** `refs/brave_special_s/blade_length.md` - measured tip offset per costume (c06, c07), the
method, the script, and a recommended `TRAIL_TIP` expressed the way `chrom_jab.rs` expresses
`JAB_TRAIL_TIP` (a derived multiple, not a magic number). State the tier: this is **tier B offline**,
and per R-21 an offline geometry result is **not** a hardware result - the console has disagreed with
this tool's predecessors three times.

**Done when:** there is a number, a script, and a stated uncertainty, in a form the Rust and Python
sides can share and cross-check the way `JAB_SIZE_FACTOR` is guarded today.

---

## Brief E - exact effect and sound resource inventory for the side-B merge

**Why:** rule 17 (the user's "no shortcuts" standard) - the mod owns what it uses: copied clips,
effects and sounds, not another fighter's code at runtime, and no stand-in sounds. The neutral-B port
merged 16 Hero effect resources into Mythra's one-slot banks and had to relocate the gold c07 texture
collision. Side-B is a new set and the same machinery applies.

**Already collected - verify and extend, do not re-derive:**
Effects named by the side-B scripts, from `ef_brave.eff`: `brave_chant`, `brave_chant_finish`,
`brave_lightning1_discharge`, `brave_lightning1_hold`, `brave_lightning2_swordspark`,
`brave_lightning3_hit`, `brave_lightning3_hit2`, `brave_lightning3_lightning2`,
`brave_lightning3_rolllightning`, `brave_lightning3_sword`, `brave_lightning3_swordspark`,
`tex_brave_lightningsword1`, `tex_brave_sword1`, `tex_brave_sword2`.
Sounds: `se_brave_miss`, `se_brave_special_s01/03/04/05/06/07/08`, `vc_brave_special_s01`,
`vc_brave_mp_lost`, `seq_brave_rnd_special_s1_en`, `_s1_jp`, `_s2_en`, `_s2_jp`, `_s3_en`, `_s3_jp`.

**Hero's sword trails are deliberately NOT in that list.** The user decided Mythra keeps her own
sword, so trails become `tex_elight_sword1/2/3` from `dumps/arc/effect/fighter/elight/trail/` (5
textures, all present). Say so explicitly in your output so nobody re-adds Hero's.

**Inputs**
* `dumps/arc/effect/fighter/brave/ef_brave.eff` and `.../trail/`
* `dumps/arc/effect/fighter/elight/ef_elight.eff` and `.../trail/`
* `dumps/arc/sound/bank/fighter/se_brave.{nus3bank,nus3audio,tonelabel}`
* `refs/brave_special_n/sound/arc/sound/sequence/fighter/brave.sqb` (already pinned, 1392 B)
* Recipient themed banks: `src/pgwr/tools/build_color_themes.py`; see `src/pgwr/COLOR_THEMES.md` for
  the `one_slot_effects` routing and the c06/c07 bank layout.

**Output:** `refs/brave_special_s/resources_side_b.md` - per resource: kind, source path, exact byte
size, sha256, whether it already exists in Mythra's banks, and the merge route the existing tooling
provides. Call out any name collision with an existing Mythra resource, and any texture that will need
the c07 relocation treatment.

**Done when:** the list is complete against all twelve side-B scripts (`SpecialS1/2/3/32`,
`SpecialSStart`, `SpecialSHold`, their air variants) plus the six voice/sound scripts, and a merge can
be planned without re-reading the dumps.

---

## Brief F - DONE BY BUFFY on 2026-09-30, not dispatched

Result recorded here so the reasoning survives. Full artifact to be written as
`refs/brave_special_s/mana_feasibility.md`.

**Question:** can Hero's on-screen mana (SP) gauge be reproduced for Mythra?

**Reviewed verdict (2026-09-30): visible-gauge reachability is unestablished.**
No standalone `mana_feasibility.md` was present at integration. The original
impossibility argument from binding absences was not sufficient evidence and is
retracted (handbook graveyard R-HERO-S-1). Mana remains excluded by the settled
user decision; no gauge implementation or associated hook is requested.

Hero's mana is `SP`, engine-side C++ in `app::FighterSpecializer_Brave`. Present in the shipped 13.0.4
image (`dumps/decoded/main_symbols.json`, `main.bin` sha256 `f70c97d2...`, VA == file offset for
`.text`):

| symbol | address | size |
| --- | --- | --- |
| `FighterSpecializer_Brave::set_sp(Fighter&, f32, bool)` | `0x8529f0` | `0x1f8` |
| `FighterSpecializer_Brave::add_sp(Fighter&, f32)` | `0x853890` | `0x1d0` |
| `FighterSpecializer_Brave::get_special_lw_command_sp_cost(...)` | (exports) | returns `f32` |

The original search found `get_fighter_information` returning metadata, and no
direct gauge-drawing binding. Those search results do not establish that a Fighter
pointer or a UI route is unreachable. No complete native HUD trace is recorded.

Hero's `FLOAT_SP` and `FLOAT_MAX_SP` are recovered in the donor NRO's helper;
canonical tier-B measurement: `refs/brave_special_s/SOURCE_STATUS.md` section 4.
The earlier inference that Hero lacked lua-visible SP state is retracted.

**Cost of each route:**

* Reading/writing Hero's work/specializer state on Mythra violates the owned-state
  design and rule 19. No such route is proposed. An owned gauge would need its own
  state, UI and an independently audited recharge signal.
* *Visible bar* - the whole binding surface has exactly one HUD function, `change_hud_kind`. No
  gauge-drawing binding exists, so this is new UI work, and `handbook/00_INDEX.md` lists CSS/UI as a
  known gap with no precedent here. **Not verified:** how Hero's bar is drawn internally. Only the
  absence of a binding was measured, so the cost is an estimate.
* *On-hit recharge* - the original search for a smashline `on_hit` hook was not a
  complete audit of attack/collision signals. Feasibility and any native-hook
  requirement remain unestablished; Monkey Flip's receiver has since been implemented.

**The cheap alternative, and why it is still not recommended.** Storing the gauge in plugin-side
state uses the existing per-entry atomic pattern. A visible bar and recharge signal
have not been audited, and are outside the side-B scope.
The closest proxies - polling `AttackModule` hitstop, or the victim's status - are heuristics, and
`AGENTS.md` section F is explicit that a live hitbox does not mean the engine acted on it, so the
consequence would have to be logged rather than the setup.

**Recommendation: do not build it now.** Ship side-B with the SP releasing unconditionally - the
decision already recorded in `projects/pgwr/TODO.md`. If mana is wanted later it is a separate project
requiring a separate design/audit before requesting any reserved native hook.

---

# Integration prompt - give this to a stronger model once briefs A-E have reported

```
You are continuing the Hero side-B port in the Smash Ultimate 13.0.4 modding workspace at the repo
root. Five read-only research subagents have just reported; brief F was already answered by Buffy.
Their job was done - yours is to read their output critically and then IMPLEMENT.

READ FIRST, IN FULL:
  AGENTS.md, CLAUDE.md
  projects/pgwr/STATUS.md            (what works, what is pending, the next queued test)
  projects/pgwr/AGENT_BRIEFS.md      (the briefs A-E the agents worked from, and F's result)
  projects/pgwr/TODO.md              (status-id allocation + all settled decisions)
  refs/brave_special_s/SOURCE_STATUS.md, status_table.txt, param_special_s.json,
      special_s_hold_exec.asm.txt, extraction.json, SOURCE.json
  handbook/06_statuses.md, 07_articles.md, 09_params_prc.md
  handbook/graveyard.md              (READ THIS - R-21 and R-22 are directly relevant)

SETTLED - do not re-litigate:
  * Status ids 0x1FA-0x1FE on the `elight` (Mythra) table: SPECIAL_S_ATTACK1/2/3,
    SPECIAL_S_ATTACK3_APPEND, SPECIAL_S_HOLD. The entry is the COMMON FIGHTER_STATUS_KIND_SPECIAL_S
    (0x1DD), replaced on the gated agent exactly as up-B's SPECIAL_HI is.
    `eflame` (Pyra) and `elight` (Mythra) have SEPARATE tables - 0x1FB on Pyra is the G&W Chef and
    does not collide.
  * Mana is deliberately OUT of the ported code. Three measured absences: no gauge constant in
    lua_const.rs, no cost field in param_special_s, no gauge read in the HOLD exec body. The user's
    decision: the hold stays and the SP slash releases UNCONDITIONALLY. Do not add a gauge, do not
    read SP, and never write that the charged version is "absent" - the gate is removed, the outcome
    is unconditional. Brief F did not establish visible-gauge impossibility.
  * Mythra keeps her OWN sword. Hero's sword article (fighter/brave/{model,motion}/blue, 136 files)
    is pinned as evidence but is NOT a dependency. Trails are tex_elight_sword1/2/3.
  * Charge thresholds: hold_frame_m 9, hold_frame_l 26, hold_frame_max 26. The donor's hold trigger
    compares with == (NOT >=) so the charge effect fires on exactly one frame.
  * The costume gate is install-time (TARGET_COSTUMES / set_costume [6,7]) and already works.

THE FIVE BRIEFS - verify before trusting any of them:
  A name the three anonymous functions near 0x28d00/0x29820/0x2ad40 that touch FLAG_SUCCESS_SP, and
    say which one SETS it
  B bone-by-bone skeleton diff, Hero c00/c06/c07 vs Mythra c06/c07
  C whether the air side-B is ground plus a situation branch
  D Mythra's measured blade length for the trail tip (forward kinematics over
    owner HaveR x article HaveR x article Sword1 - the rigid-body model was REFUTED, R-21)
  E the exact effect and sound resource inventory for the merge
Treat every claim as tier-B-or-lower until you re-run their script or re-read their file. If a brief
contradicts something measured in refs/brave_special_s/, the measurement wins and you say so.

HARD RULES - each has been violated before in this project:
  * Rule 17: if the proper route needs a reserved raw-offset hook or a rebuilt global framework
    plugin, STOP and hand back with the evidence. Do not choose a cheaper route.
  * Rule 11: one state-changing change per hardware test.
  * Rule 19: never equate numeric status/work ids across fighters; never cast objects to another
    fighter kind.
  * Rule 22: libsmashline_plugin.nro, libarcropolis.nro, libarc_network.nro, libnro_hook.nro and
    Skyline itself are OFF LIMITS. (0.10.0 rebuilt smashline and crashed at match start.)
  * Rule 26: do not edit files while a build or console test is in progress.
  * Anything that can crash needs file logging - Skyline's TCP log loses its tail.
  * Dumped ACMD text is evidence, not code. SpecialS3.txt has zero ATTACK lines; that is a dump
    artefact. Read real values from the NRO before writing them into an ACMD.

FIRST ACTIONS, IN ORDER:
  1. Read everything above. Write a short implementation plan carrying the status-id table, the
     per-status condition list (note EXEC_STATUS is on HOLD, ATTACK1, ATTACK2, ATTACK3_APPEND but NOT
     ATTACK3; CHECK_ATTACK on 1/2/APPEND but NOT 3), and the list of files you will create. Confirm
     it with me before writing code.
  2. Confirm whether the card's PENDING changes (0.20.4: up-B landing/ledge refresh via slot +0x168,
     and the 0.9 jab size) have been tested. Rule 11 requires that before a third state-changing
     change is added, or a side-B failure cannot be attributed to side-B.
  3. Implement in this order: status registration + load-time assert against
     FIGHTER_ELIGHT_STATUS_KIND_NUM; then motion registrations and bone-track retargeting (brief B);
     then ACMD translation (brief C's scoping); then the esword open/close plus the per-state blade
     length and derived trail tip (brief D); then the effect and sound merge (brief E); then logging.
  4. Do NOT build, package or install until I authorise it. When authorised, use
     src/pgwr/install-to-card.sh (smashline install OFF by default) and hand me: what is on the card
     with hashes, a numbered test of at most ~12 steps INCLUDING the vanilla negative control and
     real Hero as the donor control, the exact log lines that mean pass and fail, and where the log
     and crash report will be. Ask for the log FROM BOOT.

REPORTING
Update projects/pgwr/STATUS.md (<=150 lines) and CHANGELOG.md, add handbook/facts entries at the
right tier, and list every file you created outside scratch/ in your final message. Leave no *.log,
*.bak or build2/3/4 leftovers in source dirs.
```
