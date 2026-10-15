# ness-throw-b — vanilla Ness's back throw on Mythra c06/c07 — 2026-10-02

**Status: READY as source + a checked delta. NOT packaged as a release, NOT
installed, NO console run.** Runtime behaviour is entirely unverified.

Author: Freebuff (buffy). Mod-relative paths are relative to
`mods/ssbu_mod_new/`.

## What was built

Ported Ness's `throw_b` onto Mythra (`elight`) c06/c07: the donor's four ACMD
scripts verbatim, his attacker animation retargeted onto Mythra's skeleton, his
absolute throw numbers, release, camera, rumble, effect and sounds, with every
donor-owned resource merged into recipient-owned assets and gated by costume.

**No custom status id is requested.** `throw_b` is a vanilla kind already in
Mythra's own list and status table, and the donor touches no fighter work id.

## Evidence tiers

| claim | tier | how |
|---|---|---|
| donor ACMD text is what is ported | **C** | `WuBoytH/SSBU-Dumped-Scripts` @ `5900468523…`, per-file sha256 in `refs/ness_throw_b/donor_acmd/manifest.json` |
| donor binaries are 13.0.4 bytes | **B** | read out of the local `data.arc` with `tools/arc-extract`, hashes pinned and re-checked |
| motion delta is exactly one byte per slot | **B** | `tools/audit_ness_throw_b.py`, which diffs both lists entry by entry |
| other throws untouched | **B** | same audit: `throw_f`/`throw_hi`/`throw_lw`/`thrown_*` byte-identical |
| clip retarget keeps the bones that matter | **B** | `src/pgwr/tools/build_ness_throw_b.py`, which refuses to ship a static limb |
| donor-owned resources are reachable | **B** | effect/sound merge tools + the audit |
| the move behaves like Ness's on hardware | **D** | nothing observed — **no console, no emulator, no automated test** |

## What the offline checks establish, and what they do not

`audit_ness_throw_b.py --check` passes. It proves the delta is one clip and one
byte per slot; that no other motion entry moved; that 66 of the donor's 68 nodes
exist on the recipient with the two drops accounted for (`Bat`/`BatL`); that the
donor-owned emitter, tones and sequence record are present in the *recipient's*
banks; and that nothing outside Mythra c06/c07 is touched.

It proves **nothing** about what the throw looks like, how hard it hits, whether
the release timing reads correctly, or whether the PSI draws. The effect merge
proves bytes, not playback. The sound merge proves tone records, not sound. The
build proves the code compiles, not that it runs. Console steps 1-12 in
`CURRENT_INSTALL.md` are the only thing that settles behaviour.

Three negative controls fire, so "PASS" is not the audit agreeing with itself: a
motion list with `throw_hi` altered is rejected; a candidate shipping
`effect/fighter/ness/` is rejected; a bank missing `se_ness_throw_pk01` is
rejected.

## Dead ends and corrections found on the way (all fixed)

- **Wrong donor clip hash pinned.** The first pin used
  `e01throwngirlb.nuanmb`'s hash (34624 B) for `e01throwb.nuanmb` (50488 B). The
  tool refused to run rather than retargeting the wrong file. Corrected; the pin
  now carries the path next to the digest so the two cannot be confused again.
- **`merge_ness_throw_sound.py` had an inverted assertion.** It asserted the
  requested donor tones were *absent* from the donor bank, which can never hold.
  Corrected to assert the **common** sounds are absent from it, which is the
  claim that actually matters.
- **`scratch/` pruned mid-session.** Both tools imported `mlist` from scratch, and
  the directory was removed by concurrent activity, breaking the audit with a
  `ModuleNotFoundError` for reasons unrelated to the move. `mlist.py` was promoted
  to `src/pgwr/tools/mlist.py` (rule 3: promote useful code out of scratch) and
  every scratch-dependent path is now created on demand.
- **The audit's first costume check was wrong twice** — it tested path segments
  for `c06`, which misses slots embedded in file names like
  `se_elight_c06.nus3audio`. Replaced with an explicit `_slot_of()` that reads
  both forms, so "the delta touches a vanilla costume" is a real check.
- **A `singletons` compile error blocked the tree.** The Snake down throw agent
  recorded this against my in-flight file; it is resolved and their section says
  so.

## Known limitations, stated rather than papered over

1. **The throw-finish cut-in is not the donor's.** Ness sets zoom rate `2.0` and
   offset `(0,5,0)` through `FighterCutInManager`. The pinned `skyline-smash`
   315e4e8 exposes the methods but no accessor for the instance, and the crate has
   no `singletons` module, so the calls cannot be written at all. Verified three
   ways: the E0433 build failure; `acmd/monkey_flip.rs`, which dropped the same
   two calls for Diddy's cling attack; and `src/pmclone/moveset/…/cflame.rs`,
   which excluded Mythra's *own* vanilla `throw_b` over them. No hand-built
   pointer, no raw-offset hook (rule 17). `CHECK_FINISH_CAMERA(-5, 18)` — the
   camera the move actually uses — **is** the donor's.
2. **No `REVERSE_LR`,** because Ness's script has none. Established as the
   donor's own arrangement by a ten-fighter sweep at the pinned commit (six
   fighters omit it). Console step 3 judges how it reads; adding one would be
   inventing donor behaviour.
3. **The NRO built here is not shippable.** The tree carries other agents'
   uncommitted work, and two builds of identical source produced two different
   hashes at the same size. It is a verification build only.
4. **Effect banks conflict with the concurrent Lucas down smash**, which merges
   two different emitters into the same two files from the same baseline. They
   must be merged in sequence, not applied by copying files. Recorded in
   `CURRENT_INSTALL.md` with the command.

## Files created or changed by this task

Plugin:
- `src/pgwr/plugin/src/mythra/ness_throw_b.rs` (new — the four ACMD scripts)
- `src/pgwr/plugin/src/mythra/mod.rs` (additive: `pub mod`, log prefix, install
  call, banner text; other agents' concurrent edits preserved)

Tools:
- `src/pgwr/tools/mlist.py` (new — byte-faithful motion-list reader)
- `src/pgwr/tools/build_ness_throw_b.py` (new — retarget + one-byte patch)
- `tools/merge_ness_throw_effects.py` (new — `NESS_PSI_RUSH` into Mythra's banks)
- `tools/merge_ness_throw_sound.py` (new — tones, voice and sequence)
- `tools/audit_ness_throw_b.py` (new — the delta audit and its negative controls)

Provenance and evidence:
- `refs/ness_throw_b/donor_acmd/` + `manifest.json` (new)
- `refs/ness_throw_b/SOURCE.json` (new)
- `evidence/2026-10-02_pgwr_T-0060_ness_throw_b/DELTA.json` (new)
- this file (new)
- `CURRENT_INSTALL.md`, `projects/pgwr/STATUS.md` (own entries only)

Build output (not source):
- `builds/pgwr/ness-throw-b-candidate/ult_mod/` — the 19-file delta
- `builds/.cache/pgwr-fb-4-ness-throw-b-target/` — the isolated cargo cache

No branch, commit, push, install, SD access, emulator run or framework-plugin
change was made.