# chrom-jab-sword 1.0.0 — the Chrom jab's sword, eflame c06/c07 — 2026-10-03

Offline record. **Not installed. No console, emulator, game or card access. Every
runtime claim below is tier D.** The user-reported symptom it addresses is
"Chrom jab sword is not visible on G&W", from
`evidence/2026-10-03_pgwr_user_verdict/RESULT.md`.

Baseline: `builds/pgwr/dk_cargo-0.1.1-test` (the current card state per
`CURRENT_INSTALL.md`), mod tree `dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e`
over 5098 files. Package: `builds/pgwr/chrom-jab-sword-1.0.0/`.

## Root cause — tier B, measured on the shipped bytes

The esword article's `motion_list.bin` gained two appended entries for the jab in
0.20.0, `jab_open` and `jab_to_open`. `build_esword_pose._build_jab_mlist` wrote
each entry's animation-name hash as `hash40('<stem>')`.

An animation-name hash in a motion list covers the **file name including its
extension**. Measured against the vanilla c06 list, all five named states:

| entry | anim hash in the file | equals `hash40('<stem>.nuanmb')` | equals `hash40('<stem>')` |
|---|---|---|---|
| `close` | `0xf40969975` | yes | - |
| `open` | `0xe32317ab0` | yes | - |
| `to_close` | `0x112231a323` | yes | - |
| `to_open` | `0x104816f3ec` | yes | - |
| `d01specials1` | `0x139fa92724` | yes | - |
| **`jab_open`** (shipped) | `0x717c468bf` | **no** (`0xe50df6cbb`) | yes |
| **`jab_to_open`** (shipped) | `0x921c9118e` | **no** (`0x105f36fd98`) | yes |

So both jab entries named a file that does not exist. This is a silent miss: no
error, no log line. The article keeps playing the clip it already had, and between
moves that is `z00close`, whose `flamesword` **mesh visibility track is False**
(`build_esword_pose.STATES`). That mesh track overrides the
`set_visibility_whole(true)` that `chrom_jab.rs::game_attack11` issues at frame 3,
which is why an article-level visibility call alone did not put a blade on screen.
The Cloud fair was never affected: it drives the vanilla `to_open` kind, whose name
was always right.

This also explains why the search had to be this specific. `add_motion_partial`'s
anim argument (`Hash40::new("to_open")`) matches the entry's **motion kind**, not
its clip name — the fair's calls work against vanilla data whose clip is
`z00toopen.nuanmb`, so the name the caller passes is never the clip name. Only the
clones this module appends had to get the clip name right, and only they got it
wrong.

## Changes

Source, two files:

- `src/pgwr/tools/build_esword_pose.py` 1.1.0 — write `hash40('<stem>.nuanmb')`;
  assert the vanilla entry being cloned names its own file, extension and all;
  assert each new animation hash resolves to a real file in the output folder,
  once before writing and once on the bytes read back off disk. Also resolves the
  ArcExplorer export through `paths.toml` when `dumps/arc` is absent (this module
  could not run in this workspace before), falling back rather than raising so
  `build.py`'s module-level import is unaffected.
- `tools/audit_chrom_jab_sword.py` (new) — the offline audit below.

Assets, two files, both `motion_list.bin` (884 bytes before and after; differing
byte offsets per slot **804–808** and **856–860**, inside the two appended entries,
5 bytes each because 3 of the 8 hash bytes coincide):

| file | baseline | candidate |
|---|---|---|
| `fighter/eflame/motion/esword/c06/motion_list.bin` | `8b7be43a2435c97121904c6b6bfaf6f79e80c9fb1bd4b8f8c57afe0cad81cde4` | `1816a2913b77843312f7d8c19a2497677736721e68fa778b8106341f51f62b2f` |
| `fighter/eflame/motion/esword/c07/motion_list.bin` | `8b7be43a2435c97121904c6b6bfaf6f79e80c9fb1bd4b8f8c57afe0cad81cde4` | `1816a2913b77843312f7d8c19a2497677736721e68fa778b8106341f51f62b2f` |

`src/pgwr/plugin/src/acmd/chrom_jab.rs`: **documentation only**, no code changed. It
recorded the fact that `set_visibility_whole` is necessary and not sufficient, and
why nothing in it should compensate for a motion-list defect.

## Measured offline (tier B)

- **Regeneration is reproducible against the installed baseline.** Running the
  generator into a scratch tree produced **22 of the 24** esword files
  byte-identical to `dk_cargo-0.1.1-test` and the two `motion_list.bin` files above.
  No other file of the 5098-file tree differs, and nothing was added or removed.
- **`tools/audit_chrom_jab_sword.py --check`**: **96 checks, 0 failures**, with all
  four negative controls caught — a bare-stem animation name, `flamesword=False` on
  `jabtoopen.nuanmb`, an `attack_11` cancel frame moved by one, and a deleted jab
  clip. The controls matter because three of the four failure modes this move has
  had (R-20, R-21, R-22) were invisible to every other check that passed.
- **The audit detects the shipped defect.** Run against the baseline with no
  candidate it reports **92 checks, 10 failures** — the four extension failures per
  slot, twice each because of the scope check. So a `PASS` on the fixed tree is a
  statement about the fix, not a statement that the audit ran.
- **Preserved by measurement:** the body's `attack_11`, `attack_12` and `attack_13`
  still name `c00attack11.nuanmb` at cancel frame **23** (Chrom's), `attack_air_f`
  still names `c05attackairf.nuanmb`, both jab clips are still declared in
  `config.json`, and per-state visibility/scale is unchanged (`flamesword` False in
  `z00close`/`z00toclose`/the four `d01specials*`, True in `z00open`/`z00toopen` at
  `Sword1` 1.4 and in `jabopen`/`jabtoopen` at 0.9).
- **Expected merged mod tree** (only if every other file equals this baseline):
  `1091b63be89a26bb319eeb38879e2d166cc66a0946e940ccea6a9e04d4f080cf`, 5098 files.
  The rule used is sha256 over sorted `"<relpath>\t<sha256>\n"` rows; it reproduces
  the baseline's own `dae0bff0…` exactly, so it is the installer's scheme and not
  one invented here.

## What is deliberately not changed

- **No Rust source, so no NRO.** The installer must not rebuild or copy a plugin
  binary for this section; the installed NRO stays valid.
- **No second visibility guard.** `attack_air_f::esword_visibility_guard` remains
  the single owner of the article's visibility for the whole fighter, and it
  already lists `attack_11`/`_12`/`_13`. Adding a jab-local guard would be two
  guards writing the same flag on the same transitions, with registration order as
  the tie-break.
- **No "always show the sword" fallback.** The lever that would mask this bug is
  the one the module docstring already rules out, and it would break the fair's
  put-away and every other Pyra move along with it.
- **No body-side clip change.** The jab's animation and hitboxes were confirmed on
  hardware in 0.16.0 and are not in question. Measured, for the record: `HandR`
  moves through 42 distinct rotations in `c00attack11.nuanmb` and `HaveR` (the
  grafted `HandR -> HaveR -> Sword1 -> Sword2` chain the article and the trail hang
  off) carries a single constant local transform, so the blade and the trail both
  ride the hand through the whole jab. `Sword1` is likewise constant-local, so the
  `AFTER_IMAGE4_ON_arg29` ribbon on `sword1` follows too.

## Open items, in order, if the blade still does not appear

1. **`game_toopen` is not readable in this workspace.** The `jab_to_open` entry
   inherits `to_open`'s `game_script` (`hash40('game_toopen')`), and the article's
   own `game_open`/`game_close`/`game_toopen`/`game_toclose` scripts are not in
   `dumps/decoded/acmd_snapshot_pmclone/lua2cpp_eflame/eflame_esword/`. If that
   script chains the article to the `open` kind, the blade appears at the fair's
   1.4 rather than the jab's 0.9 — visible but the wrong size. That is the expected
   next failure, and it is a size problem, not a visibility one.
2. **The `ADD_PARTIAL_MTION_SWORD_WHEN_CHANGEING` flag.** Every vanilla eflame
   sword-drawing script sets it when `MotionModule::is_changing` — including the
   recipient's own `OpenSword1F`, `AttackAirF` and the Corrin up-air this repo
   ports — and `chrom_jab.rs` does not. Measured counter-evidence to it being the
   cause: it is **never cleared** anywhere in the dumped scripts, so it latches on
   during almost any move and would already be set by the time most players jab. It
   is recorded as a fidelity deviation, not as the fix, and it is deliberately not
   shipped so that the hardware result can attribute cleanly.
3. **Blade angle and size remain taste values** (`graveyard` R-21: three offline
   geometry tools disagreed with each other and with the console). Nothing offline
   can settle them.

## Not run

No plugin build (no Rust change), no game, no emulator, no Ryujinx, no console, no
SD access, no install, no commit, no branch, no push, no subagent.

## Blockers

- **None for the port itself.** Source complete, delta packaged and audited, hashes
  checked. The installer needs nothing from me beyond copying two files.
- **Blocked only by the user** for every behavioural claim. The console test sheet
  is in `CURRENT_INSTALL.md`; it is the only thing that can move this from tier D.
- One genuine gap, stated rather than guessed around: the article's own
  `game_toopen` script is not available in this workspace, so whether the jab ends
  up in its own `jab_open` state or the fair's `open` state cannot be settled
  offline. See open item 1.