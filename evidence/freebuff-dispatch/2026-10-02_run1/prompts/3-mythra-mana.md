# Task: find out why the mana system on Mythra (c06/c07) is not working, and fix it

"Mythra" here always means **Mythra (elight) costumes c06 and c07** of the Pyra/Mythra pair whose
Pyra half is reskinned to Mr. Game & Watch, in the mod `mods/ssbu_mod_new` (project `pgwr`).
Vanilla costumes c00-c05 must stay untouched.

## What the user wants

Mythra c06/c07 uses Hero's neutral-B (Frizz line) and side-B (Zap line). The user expects a working
mana (MP) system for them and reports that it is not working. Find the actual reason and fix it so
the mana system works on the console.

## What is already known (verify, do not trust blindly)

- In the current working tree the Hero moves are built with mana **off**: see the `mana=off` log
  lines and "mana excluded" comments in `src/pgwr/plugin/src/mythra/hero_neutral_b/` and
  `hero_side_b/` (`SUCCESS_SP` is always true, no price is charged, no gauge exists). So the most
  likely answer to "why is it not working" is that it was specified and researched but never
  implemented. Confirm or refute that first, including on the other local branches
  (`git branch -a`, `git log`, `git show <branch>:<path>` only; `lab/T-0049` holds the mana work).
- The specification the user agreed to is `mods/ssbu_mod_new/refs/brave_special_n/T-0033/MANA_HUD_CONTRACT.md`
  (revised by T-0046): one shared meter for the c06/c07 pair, only neutral-B and side-B spend,
  the value persists through the Pyra<->Mythra swap, and a real fighter HUD shows it. Evidence
  gathered so far is in `refs/brave_special_n/T-0046/`; see also `projects/pgwr/STATUS.md`
  (T-0049 paragraph), `projects/pgwr/TODO.md` and `kb/findings/hero-mana-audit-local-main-and-arc-boundary.md`.
- T-0049 was blocked on inputs: Hero's numeric PRC values (prices, max, recovery), the lifecycle /
  failure mapping, and the HUD pane/hook ABI. What has changed: the ARC export that
  `mods/ssbu_mod_new/paths.toml` -> `[dumps] arc` points to is available (it contains
  `fighter/brave/param`, `ui`, etc.). **You may read that export (read-only) for this task**; never
  write into it and pin what you take into `refs/brave_special_n/` with its sha256. The 13.0.4
  game binary is at `gamedata/ssbu-13.0.4/main.bin` and the full `data.arc` beside it.

## How to scope it so that something real ships

Work in this order and finish each layer before starting the next:
1. **Gameplay mana**: an owned MP value for the pair with Hero's real max, prices, natural recovery
   and recovery on hit taken from his params; neutral-B and side-B check and spend it, with Hero's
   real out-of-MP failure behaviour (not a silent no-op); persistence through the swap; reset on
   death/match start as Hero does. Owned state only - no Hero work ids, no casting to Hero.
2. **A visible readout**: the real fighter HUD gauge if it can be reached with what rule 17 allows.
3. Bounded file logging of every spend / refuse / recover / reset (one line per event, never per
   frame) so the user can send a log.

If a layer needs something rule 17 reserves (a raw-offset native hook, anything touching a framework
plugin), do not drop the task: implement everything that does not need it, put the reserved part
behind its own cargo feature that is **off by default**, byte-verify its target on the 13.0.4 image
as the existing hooks do, and say in your handoff that this feature needs the user's approval before
it is built in. Framework plugins on the card stay off limits without exception.

## Done means

- A written answer to "why was it not working", with evidence.
- The fix compiled into the plugin behind the existing `hero-side-b` feature set (plus your own
  feature only for reserved parts), with the mana numbers traceable to the pinned donor params.
- Your section in `CURRENT_INSTALL.md` says READY (or exactly what blocks it) with build steps and
  the manual console checks (including vanilla Mythra c00 and vanilla Hero as controls).

{{COMMON}}
