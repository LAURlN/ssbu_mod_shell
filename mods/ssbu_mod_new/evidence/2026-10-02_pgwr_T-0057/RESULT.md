# T-0057 - Hero mana on the c06/c07 pair: what was done and what was measured

Freebuff dispatch slot `3-mythra-mana`, 2026-10-02. Mod `mods/ssbu_mod_new`,
project `pgwr`. **No console, no emulator, no tests, no card access, no install,
no Ryujinx.** Every line below is either a file measurement (tier B) or an
explicit statement that a thing is unverified.

## The question, and the answer

"Why is the mana system not working on Mythra c06/c07?"

Because there was no mana system. The Hero neutral-B and side-B shipped with the
donor's affordability gate hard-wired to "always yes" and no MP value anywhere, so
there was nothing that could fail. It was specified (T-0046) and researched
(T-0049) and then not written, because T-0049 was blocked waiting for the donor's
numeric parameter values.

The blocking reason turned out to be a dead end, not a real boundary: the user's
ArcExplorer export has an **empty** `fighter/brave/param/` directory, and the
workspace tool `tools/arc-extract` reads the file straight out of the local
`data.arc` in seconds. Full detail and hashes: `refs/brave_special_n/T-0057/SOURCE.md`.

## What ships (source only; the installer builds and installs)

* `src/pgwr/plugin/src/mythra/hero_mana/` - the owned meter: per-entry value,
  donor gate, donor debit sites, passive recovery, per-stock reset, bounded log.
* neutral-B spends in its SHOOT MAIN, side-B in ATTACK1/2/3, the Kazap finisher
  does not. Out of MP: nothing spent, motion plays, no projectile / no sparks /
  no lightning, one `REFUSE` line.
* One meter per player, keyed by entry, both halves of the pair accepted, so the
  down-B swap costs nothing to support.
* New Cargo feature `hero-mana-reserved`, **off by default**, holding the two
  reserved parts (HUD gauge, hit recovery) as hand-back documents with their
  byte-verified targets.

## Measurements actually taken

| claim | how | result |
| --- | --- | --- |
| the six prices, the ceiling, the recovery period | `tools/dump_hero_mana_params.py` on the pinned donor `vl.prc` sha256 `dafa43c6...` | N 6/16/36, S 8/18/42, max 100, +1 per 60 frames, hit/shield 0.8 |
| the label table agrees with the file | the tool prints the Hash40 read out of the file | 11/11 keys identical to the contract's table |
| the gate's shape and debit sites | re-read of the pinned `flag_success_sp.c` and `neutral_b_status.c` | `<=`, debit only on success, neutral SHOOT MAIN + side ATTACK1/2/3, finisher exempt |
| the reserved hook targets have not moved | `tools/audit_hero_mana_native.py` on `main.bin` sha256 `f70c97d2...` and the donor NRO sha256 `dc5edcde...` | 9/9 MATCH |
| the vanilla fighter HUD already has an MP gauge | `tools/arc-extract` on `ui/layout/info/info_melee/info_melee/layout.arc` sha256 `c382a6e5...` | `info_melee_lct_player_sp` pane tree, `sp_00..sp_03`, `MELEE_GAUGE_SP_GET/USE` |
| the code compiles | three feature sets, own cargo caches | all three build; NRO 471,040 B sha256 `1189bd1c...` |

## Deliberately not done

* **No framework plugin, no raw-offset hook, no donor call.** The two reserved
  parts are the only things that would have needed one, and they are off.
* **No invented failure effect.** The donor's out-of-MP cosmetic was not
  recoverable offline, so none was substituted; the move visibly fails, which is
  the donor's own control flow.
* **No hit/shield recovery shortcut.** Awarding from our own projectile hit, or
  every frame from a "was hit" flag, would both be wrong.
* **No second meter for the Pyra half**, no version bump, no packaging, no card.

## Unverified (rule 8)

Everything about behaviour: that the meter shows the right number, that the swap
really preserves it, that the refusal feels like Hero's, the recovery rate, the
per-frame rate of the recovery callback, and the whole reserved HUD story. The
console test that would settle them is the twelve-step list in this task's section
of `CURRENT_INSTALL.md`, with Mythra c00 and real Hero as controls.

## Files created outside `refs/` and `evidence/`

`src/pgwr/plugin/src/mythra/hero_mana/{mod.rs,params.rs,logging.rs,damage.rs,hud.rs}`,
`tools/dump_hero_mana_params.py`, `tools/audit_hero_mana_native.py`.
Edited: `mythra/mod.rs`, `mythra/hero_neutral_b/{mod.rs,fighter.rs}`,
`mythra/hero_side_b/{mod.rs,fighter.rs}`, `plugin/Cargo.toml`, `plugin/src/lib.rs`,
`CURRENT_INSTALL.md`, `projects/pgwr/{STATUS.md,CHANGELOG.md,TODO.md}`,
`handbook/{09_params_prc.md,graveyard.md}`, `tools/README.md`,
`refs/brave_special_n/{T-0033/MANA_HUD_CONTRACT.md,T-0057/*}`.
