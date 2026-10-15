# Snake up tilt (AttackHi3) on G&W c06/c07 - Freebuff slot 2, 2026-10-02

**Result: implemented, compiled, audited, READY for the collective build. NOT packaged by
this session and NOT installed (AGENTS.md rule 23).** Nothing here is evidence that the move
behaves any particular way in game: there was no console, no emulator and no automated test.

## What was asked

Give G&W (Pyra c06/c07) Snake's up tilt instead of G&W's own, on those two costumes only:
his animation retargeted onto the recipient, his hitboxes and timing, his own effects,
sounds and rumble.

## What was done

| part | file | notes |
| --- | --- | --- |
| scripts | `src/pgwr/plugin/src/acmd/snake_attack_hi3.rs` (new) | Snake's own `game_/effect_/sound_/expression_attackhi3`, registered at `Priority::High` over the generated G&W `AttackHi3`, gated `set_costume([6,7])` |
| registration | `src/pgwr/plugin/src/acmd/mod.rs` | three additive edits: `pub mod`, table row for `ATTACK_HI3`, one `install()` call |
| assets | `src/pgwr/tools/build_snake_uptilt.py` (new), `src/pgwr/build.py` | four additive edits: import, motion entry, G&W-verbatim skip, `require`, `deploy_for_slot`, record |
| sound | `tools/merge_snake_uptilt_sound.py` (new), `src/pgwr/build.py` | import + one `build()` call after the R.O.B. merge |
| audit | `tools/audit_snake_uptilt_delta.py` (new) | offline delta audit, passes against the installed 0.20.17 |
| reproduction | `tools/stage_snake_uptilt_candidate.py` (new) | stages a candidate without the ArcExplorer export |
| donor | `refs/snake_attack_hi3/donor_acmd/` (new) | the ACMD text, re-pinned - see below |

## The one real obstacle, and what was done about it

`projects/pgwr/TODO.md` and `refs/snake_attack_hi3/SOURCE.json` both say the donor script
text was "already in the workspace, deliberately not re-copied", at
`dumps/scripts/SSBU-Dumped-Scripts-main/smashline/lua2cpp_snake/snake/AttackHi3.txt`.
**It is not there.** `dumps/scripts/` holds only `ParamLabels.csv` and
`gamewatch_motion_list.yml`; the export `paths.toml [dumps] arc` names
(`<ArcExplorer dir>/export`) contains almost no files; `gamedata/` has `data.arc` but
no ARC reader in this workspace. Approximating a donor script is forbidden by rule 17.

Route taken: re-pin the text from the commit this project **already** pins for exactly this
purpose - `WuBoytH/SSBU-Dumped-Scripts` at
`59004685238a3f6f93bae905d3a4e079701c40b4`, the commit behind
`refs/brave_special_n/acmd_pin.json` and `tools/fetch_donor_acmd.py` - into
`refs/snake_attack_hi3/donor_acmd/` with per-file sha256 in `manifest.json`
(`snake__AttackHi3.txt` `99cc3499cfa39bfc...`, 7,070 B).

R.O.B.'s `AttackLw3.txt` was pinned at the same commit as a **control**
(`65b13e7c00a04a1d...`, 6,629 B): the shipped `acmd::robot_attack_lw3` was written from
exactly that file, so reading the two side by side is what establishes how much the dump
loses before a line is ported. R.O.B.'s loses braces around its region-JP branch and prints
an `is_excute` inside an `else`; Snake's `AttackHi3` has no branch, no lost braces, no
article call and no work-id write, so **nothing was dropped**.

Dead end worth not repeating: a raw YARP reader over `gamedata/ssbu-13.0.4/data.arc` would
have produced `.lc` bytecode, not readable script text, and no decompiler exists in this
workspace. Recorded in `handbook/graveyard.md` as R-SNAKE-UPTILT-1.

## What was measured (tier B, offline)

* **Motion entry:** cancel frame **38**, flags **0x84**, blend 0, `game_script`
  `0xef3bca119` = `hash40("game_attackhi3")`, animation `0x138caf3e29` =
  `hash40("c02attackhi3.nuanmb")`, raw sha256 `3c1cd8b9e4094a1e2a9569bfb5371522b5a98b6d1534dfbcf52200c698bede21`.
* **Clip:** 87 transform nodes -> **77 kept** on the built recipient, 10 dropped
  (`FaceN` + the nine `S_Bandanna*` nodes), **0 case-only matches**, Visibility replaced by
  the recipient idle's 98 nodes, Material group dropped, 48 frames, sha256
  `47133f4fb017c0fdc0416e9f169cdf7d3e710c10a724b14489041c13d52d4839` (identical in c06 and
  c07, which is expected - the same skeleton and the same idle drive both).
* **The leg chain carries the kick.** Measured against the recipient idle:
  `LegL` 92.62 deg / `LegR` 78.01, `KneeL` 97.79 / `KneeR` 80.55,
  `FootL` 102.57 / `FootR` 54.40, `ToeL` 0.00 deg but 0.5895 units of translation,
  `ToeR` 7.06 deg / 0.5885 units. `deploy_for_slot` raises if any of the eight is static.
  This is the failure the user rejected on the R.O.B. down tilt (T-0036/T-0048), and node
  coverage alone cannot detect it - "87 -> 77" would print the same for a clip whose legs sat
  in rest pose.
* **Sound:** `se_eflame_c06/c07` retain **543** tones byte-for-byte and gain exactly
  `se_snake_attackhard_H01`; `vc_eflame_c06/c07` retain **240** and gain exactly
  `vc_snake_attack01..04`; `eflame.sqb` retains **13** records and gains the
  `seq_snake_rnd_attack` record (14 total), appended exactly once. The four voice tones were
  **measured** out of the donor sequence record by CRC32, not listed by hand.
* **Compilation:** `cargo skyline build --release --features snake-neutral-b,hero-side-b`
  in cache `builds/.cache/pgwr-fb-2-snake-up-tilt-target`, no errors. NRO
  `75deff8de447f8f4d171539d8791f046e5c190a60901b05b5ec9ddef809dc313`, 466,944 B, carrying
  `game_attackhi3`, `effect_attackhi3`, `sound_attackhi3`, `expression_attackhi3`,
  `se_snake_attackhard_h01`, `seq_snake_rnd_attack`, `sys_attack_arc_b`, `sys_turn_smoke`
  and `rbkind_attackm`.
* **Delta audit vs the installed 0.20.17** (`SNAKE_UPTILT_DELTA.json`): 18 changed files,
  0 added, 0 removed, 0 outside the up-tilt set, `attack_hi3` the only motion-list entry
  that differs in either slot, banks and sqb append-only, no c00-c05 Pyra file in the delta.

## Negative controls (so "PASS" is not the tool agreeing with itself)

* `merge_snake_uptilt_sound.py --check`: the merge runs against the **real 0.20.17 banks**
  staged out of the package, asserts the retained counts (543 / 240), then deletes one
  appended tone from a copy of a written bank and requires `verify_preserved()` to reject
  it. It does.
* `audit_snake_uptilt_delta.py`: (a) against an unchanged baseline it fails listing all 18
  required files; (b) `--combined` on an exact delta fails, so the flag cannot silently
  excuse a wrong build; (c) reverting one of the two clips fails naming that clip.
* `--combined` was also exercised positively: with one unrelated effect-bank byte changed,
  the audit passes and reports `changed_outside_up_tilt` instead of demanding an exact
  match. That is the mode the combined install build needs.

## Deliberately unchanged, and why

The donor parents its hitboxes on `top`, `kneel` and `legl`. The built c06/c07 skeleton has
**none** of those three names (it has `LegL`/`KneeL`). This was left exactly as the donor
wrote it: G&W's own up tilt - the handler this replaces - also writes `top`, so remapping
two of the three would make this handler differ from the one it supersedes on a question no
offline measurement can settle. The measurement is recorded
(`refs/snake_attack_hi3/inventory.json`, re-measured 2026-10-02) and carried into the
manual test as **step 9**, which decides it. If that step fails, remapping
`kneel` -> `KneeL` and `legl` -> `LegL` is the single next change.

No new status id: `AttackHi3` is a vanilla status kind. The next free Pyra id stays
`0x208`. No article, no work-id write, no stand-in sound, no framework change.

## Unverified (tier D until a console run)

How the kick looks on G&W's body; whether the legs read as a leg kick; hitbox placement;
facing and slope behaviour; whether the 38-frame cancel feels right; that Snake's tone and
grunt play; that the rumble is right; any regression in the other moves; and that the engine
asks for `attack_hi3` at all on this recipient in a way the `High`-priority handler wins.

## Reproduce

```bash
cd mods/ssbu_mod_new
python src/pgwr/build.py                      # needs the ArcExplorer export - not available here
python tools/stage_snake_uptilt_candidate.py  # fallback when it is not
python tools/audit_snake_uptilt_delta.py --baseline 0.20.17 --version <the staged version>
python tools/merge_snake_uptilt_sound.py --check
```