# Mythra c06/c07 move replacements — 0.13.0 (not built, not installed)

Adds three moves to **Mythra** (`elight`) in costumes c06 and c07, ported from
`mod_files/mythra_gamewatch_swap`, which ships the same three on the same two
costumes:

| input | now | donor |
| ----- | --- | ----- |
| up air | Corrin's up air (`d02`) | `src/attack_air_hi.rs` |
| up B | Hero's Spin, Mii Swordfighter `Hi3` | `src/hero_spin3.rs` (build `2026-09-26.g`) |
| down throw | Luigi's down throw (`d02`) | `src/throw_lw.rs` |

The Pyra/G&W side is **not** touched. G&W's up air still shoots the breath
projectile, G&W's down throw is still G&W's, and no G&W script, asset or status
is changed by anything in this change.

## State: written and typechecked, deliberately not built

Nothing has been compiled into an NRO and nothing has gone near the SD card.
`build.py` and `build-plugin.sh` have not been run.

What *has* been run:

- `cargo skyline check` on the Switch target: **0 errors, 0 new warnings**. The
  one remaining warning is the pre-existing dead `IS_HAVE_ITEM_KIND` in
  `acmd/compat.rs`. The check ran into a throwaway `target-check/` which was then
  deleted, so no build artefact exists.
- The asset retarget, into a throwaway `scratch/hi3-verify/` which was also
  deleted: all four phases x both slots, round-trip verified. Results below.

That is a compile and a data check. Neither is a console test, and neither
establishes anything about how the moves feel or look on hardware. The donor's
own numbers are the best available prediction and they come from a *different*
project: see "What is untested" at the end.

## The gate, and the one thing that had to be checked

This is the part worth reading. In the donor, Mythra *is* the starting character.
Here, Pyra c06/c07 is, and Mythra is what down-B hands you.

smashline's costume filter reads the costume from
`get_costume_from_entry_id` (`src/utils.rs:40` in the locked `be3ef308`), which
reads a field at offset `100` on the **entry** — the character-select slot — not
on the active body. So an entry created as Pyra c06 reports `6` for the whole
match, including the frames where Mythra is standing there. The gate therefore
fires on Mythra after the down-B, which is what was asked for.

Both install paths are filtered, not just ACMD: `install_script`
(`create_agent.rs:246`) and `install_status_scripts`
(`create_agent.rs:738`). Hero's Spin needs the second one, because it registers
status callbacks and ids.

- Pyra c06/c07 selected -> entry reports 6/7 -> Mythra gets the three moves,
  in both halves of the transformation.
- Mythra c06/c07 selected directly -> same.
- Mythra c00-c05 -> gate fails -> every stock pointer untouched.

The third is the negative control, and `mythra::gate_trace` exists to make the
first two a reading rather than a judgement: a `Main` callback on a costumed
`elight` agent, which smashline therefore only installs for c06/c07, printing
once per entry.

```
[PGWR] MYTHRA GATE ACTIVE: entry 0 is Mythra, running c06/c07 move replacements, reported colour 6
```

## What was *not* ported, deliberately

The donor registers `elight` globally and branches at runtime on
`is_target_costume`, keeping a hand-copied copy of vanilla Mythra in each
`else`. That copy is roughly half of both script files, and for Hero's Spin it
drags in a third, `hero_spin3_vanilla_acmd.rs`.

None of it is ported. With an install-time gate those arms are unreachable, and
carrying them would mean shipping a second copy of vanilla that can silently
drift from the game. The trade is explicit and it is a real reduction in code:
~400 fewer lines than a literal port.

The one place this changes behaviour rather than just deleting dead code is
`hi3_ground_hold`, which exists in the donor purely as a guard and becomes an
empty body. It still has to be registered, because its purpose is to *suppress*
the stock `game_specialairhi1`; without it, Mythra's own up-B hold script would
run on top of the retargeted hold clip.

## Status ids

`FIGHTER_ELIGHT_STATUS_KIND_NUM` is `0x1F1` in the locked `skyline-smash`, so the
four Hero's Spin phases take exactly the first four free ids:

| id | name | entered by |
| - | ---- | ---------- |
| `0x1F1` | `STATUS_START` | up B on the ground, via `SPECIAL_HI` `Pre` |
| `0x1F2` | `STATUS_HOLD` | startup clip ending while SPECIAL_B held |
| `0x1F3` | `STATUS_GROUND_SPIN` | SPECIAL_B released |
| `0x1F4` | `STATUS_AIR_SPIN` | up B in the air, or leaving the ground |

`mythra::status_id_for` asserts this at load, so a toolchain bump that moves
Mythra's table panics before any fighter is built. Same guard as
`status::judge`'s `0x1EE` on `eflame`; different fighter, separate table, no
collision.

## Assets

`tools/build_hero_spin.py`, called from `build.py`'s `main()`, retargets the
four Mii `Hi3` clips onto Mythra c06 and c07. Verified output:

| motion kind | donor clip | frames | transform tracks |
| ----------- | ---------- | ------ | ---------------- |
| `special_hi_start` | `d02specialhi3start.nuanmb` | 8 | 64 |
| `special_air_hi1` | `d02specialhi3hold.nuanmb` | 61 | 64 |
| `special_air_hi_jump` | `d02specialhi3.nuanmb` | 83 | 64 |
| `special_air_hi_end` | `d02specialairhi3.nuanmb` | 86 | 64 |

169 bones in Mythra's skeleton; 11 Mii-only tracks dropped (`Miihead` and
`Finger*L/R*4_eff`); c06 and c07 produce byte-identical clips, which is expected
because their skeletons are.

**No motion-list surgery and no `config.json` change are needed.** The donor adds
four Mii motion kinds and patches Mythra's list. This does not, because
`hero_spin.rs` asks for Mythra's own four motion names
(`special_hi_start`, `special_air_hi1`, `special_air_hi_jump`,
`special_air_hi_end`), which already point at four existing files. The retarget
overwrites the clip *behind* a stock motion kind. Consequences:

- nothing written is a new file, so `build_config_json`'s "every new file must
  be declared" check stays satisfied with no edit to it;
- the motion list cannot desync from the clips, because it is never touched;
- `c00`-`c05` are untouched by construction — no path outside the two named slots
  is ever opened for writing.

The package file count goes 793 -> 801. `install-to-card.sh` compares staged
against built count at run time rather than against a constant, so it adapts.

The tool imports its low-level helpers (transform round-trip comparison, the
visibility/material layout check, the skeleton-intersection check) from
`mod_files/mythra_gamewatch_swap/tools/build_hero_spin_assets.py` rather than
reimplementing them. Those helpers are the parts the donor actually debugged on
hardware. This is a real cross-project dependency and is called out in the
module docstring; if the donor folder goes away, so does this tool.

## What is untested, and what to watch

The donor's air spin was tuned across four Switch builds against Mii Swordfighter
on Mythra's own body. Here it runs on Mythra reached through a down-B, whose
kinetic and status context is not the same. Two specific carries-over risks:

1. **The air kinetic.** `hero_spin_params.rs` keeps the donor's Mii-derived
   gravity (0.106) and terminal speed (1.55), scaled 85% / 90%. Mythra's own are
   0.137 / 1.87. The donor's `.d` build scaled these because its own trace showed
   the spin leaving the air status before the frame 47-48 finisher. That trace
   was Mythra-selected, not Mythra-after-down-B. If the finisher is being cut
   short, this is the first number to look at, and the log line to read is
   `[PGWR-HI3] air spin y <start> -> <end> over the phase`.
2. **Startup turnaround.** The ground START phase requests
   `FIGHTER_STATUS_ATTR_START_TURN` because both the native Elight and Mii's own
   `SpecialHi` `Pre` set it and the donor's interrupt bypassed it. That fix was
   made for Mythra-selected and has not been re-checked here.

Also unchanged from the donor and still true: the sword trail borrows Mythra's
`tex_elight_sword*` on `sword1` because Mii's own trail is not in her effect
bank, and the air phase's dedicated Mii `Hi3` kinetic cannot be installed on
`elight` at all.

### Bounded console test, when this is built

1. **The gate.** In one match, run Pyra c06, then down-B to Mythra. Expect
   `[PGWR] MYTHRA GATE ACTIVE: entry 0 ... reported colour 6`, and
   `[PGWR-HI3] entry id=0 ... -> status 0x1f1` on ground up-B. If the
   `MYTHRA GATE ACTIVE` line is absent for an entry that is visibly Mythra, stop
   and report — the gate is the whole basis of this change.
2. **The negative control.** Mythra c00-c05 in the same match must produce no
   `[PGWR]` line of any kind, and her up air, up B and down throw must be
   vanilla.
3. **Up B.** Ground tap, hold-and-release, and a use in the air. Read the
   `[PGWR-HI3] transition` lines; they should read start -> hold -> ground spin
   -> wait, and the air attempt should reach `0x1f4` and not land at frame 0.
4. **Up air and down throw.** Corrin's hitboxes on Mythra's sword; Luigi's
   throw picks up, spins and releases.
5. **No regression.** Pyra c06/c07 as G&W: breath still shoots on up air, the
   down throw is still G&W's, G&W's props and Judge are unchanged, and the
   down-B transformation still works in both directions.
