# Pipeline overview: copying a move from a donor to a recipient

Lifted from the old `move_replacement_guide.md` sections 5-9 and 12 (tiers and checklist were console-proven on the swap project) and
adjusted for the 2026-09-29 "no shortcuts" direction. Tier legend: see `AGENTS.md` rule 8.

## Two architectures used so far

| | Hook swap (`src/mgw_swap`) | Reskin (`src/pgwr`, current) |
| --- | --- | --- |
| Idea | Mythra c06/c07 and real G&W c06/c07 share one entry via redirected pair table; G&W is actually G&W | Pyra c06/c07 *is* a G&W skin+moveset; Mythra stays vanilla; vanilla Element swap is the transformation |
| Needs | native hooks on `main` (11 sites) | no hooks, smashline scripts gated with `set_costume([6,7])` |
| Risk | swap position/camera/pose bugs, engine crashes | port completeness (statuses/articles/sounds), visibility |
| Status | frozen, works with known bugs | active |
| Third route | Clone Engine standalone clone (`src/mgw_standalone`): G&W ok, Mythra crashes | parked |

## Tiers (cost of a move)

1. **ACMD only** - recipient already has the status and motion slot. Copy donor ACMD, keep recipient vanilla branch, fix cancel frames.
   Example: Corrin uair / Luigi dthrow on Mythra (worked with raw animation copy).
2. **Motion registration** - donor motions must exist in the recipient's `motion_list.bin`. Copy entries whole; map onto *existing* clip file names and overwrite the clips
   (see `04`, and graveyard R-5 for why not to add new file names blindly).
3. **State machine** - the move is several statuses (Monkey Flip, Hero's Spin): allocate new status ids above the recipient's native count (`06`), own kinetics, params extracted from donor `.prc` with hash provenance.
4. **Geometry** - donor bones/meshes/textures are missing (Shulk fair `SwordR` bone, G&W props): all four model files must agree (`08`).
5. **Articles** - projectiles/props: `clone_weapon` + files for all 8 slots + config.json (`07`, `10`).
6. **Native-owned behaviour** - anything whose logic is in the game binary (breath constructor, prop lifetime): find it in `main.bin` (`12`), then bridge, replicate, or hand back.

## Steps (short form of the checklist)

1. Name the target move, carrier, donor; classify the tier with reasons.
2. Pin donor sources into `refs/<donor>_<move>/` with `SOURCE.json`: URL, commit, date, sha256. Read **all** functions in the script file (game/effect/sound/expression) and follow helpers.
3. Record donor and recipient motion-list entries independently (`tools/inject_monkey_flip.py` and `src/pgwr/build.py:parse_mlist_entries` are the templates).
4. Dependency list: bones, meshes, article constants, work ids, motion kinds, kinetics, effects, textures, sounds, params, statuses. Missing dump files -> `dumps/MISSING.md`.
5. Ask "does the donor's own clip already do this?" before writing code (visibility tracks, `tools/untracked_meshes.py`).
6. Generate, do not hand-write, ported scripts (`src/pgwr/tools/gen_acmd.py`, rules R1-R26 in `05`). Never hand-edit `generated/*.rs`.
7. Gate by costume; build; verify hashes; install with `install-to-card.sh`; give the user a numbered test with a vanilla control (`17`).
8. Record the result in `evidence/`, update `projects/<p>/STATUS.md` and the handbook.

## Source procedure summary (from movemakerguide)

- Damage/angles/hitboxes/effects: WuBoytH `SSBU-Dumped-Scripts` (`dumps/scripts`). Motion names/anims/cancel: motion-list dumps. State machines: status-script dumps (coverage not guaranteed - G&W has none) or `tools/nro_decomp` (Ghidra on `dumps/arc/prebuilt/nro/release/lua2cpp_<fighter>.nro`, see `06`).
- HewDraw-Remix is a *balance mod*: implementation examples only, never the source of vanilla values.
- Videos are not a way to measure hitbox radii, BKB, KBG.
- Resolve internal fighter ids from the archive folders (Mythra `elight`, Pyra `eflame`, G&W `gamewatch`, Joker `jack`, Byleth `master`, Greninja `gekkouga`, Incineroar `gaogaen`, Corrin `kamui`, ZSS `szerosuit`, Min Min `tantan`, Mii swordfighter `miiswordsman`). Never guess numeric kinds (Mythra 91, Pyra 90, G&W 28 verified).
- If a source is missing: report exactly what, continue independent work, never invent values.
