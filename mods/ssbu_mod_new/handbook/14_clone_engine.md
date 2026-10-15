# Clone engine

Tiers: **A** hardware-confirmed (console or decoded crash report) - **B** measured offline by a script that still exists - **C** read from pinned third-party source - **D** hypothesis. Anything without a tier below is A/B unless marked otherwise. Paths in the source column refer to the *old* workspace (`modpack_test_1`); the same material now lives under `projects/*/history/`, `dumps/` and `evidence/`.

- Clone Engine keys identity by **entry**, one custom kind per entry; a two-base pair fails `clone_kind_of_object`, `param_override_kind`, `ENTRY_FIGHTER_BOMA`. Needs a maintained fork for pairs. (C)
- Mythra clone crash chain (each a hardware crash, decoded): Smashline factory hook at `+0x5b0` (1) -> input-hook float-as-pointer (2) -> costume table null (3) -> `FilesystemInfo` (4) -> wrong global addresses / model lookup `have` null (5) -> motion-bind state 5 skips holder allocation at `0x49748c` (`main+0x497350` routine) (6) -> holder+0x10 vtable+0x38 returns 0 at `0x4984d4` (7) -> `bunshin` body model file `0x34e65` not resident (`0x35c23a8`) (8). p16 (route body lookup with stride 0x18 via `0x35c2040`) untested. (A)
- Mythra's esword/winsword lists reference **Pyra's** esword dir; Mythra owns `esword` + `bunshin` articles with no separate bunshin model (uses the body model). (B)
- BNTX portrait rename in-place works only for the verified single-leaf layout; do not generalize. (B)
- Need the extra dump list: `mgw_standalone/MISSING_DUMPS.md` (18 sound banks). (B)


## What the failed / parked projects still teach

- pmclone: Clone Engine gives exactness only if the clone runs the *original* vtable/lua2cpp and every "is this Pyra/Mythra"
  site accepts the clone; ~150 raw immediates against kinds 90/91 are noise. Relocating machine code gives independence but not editability.
  Fidelity test idea (differential traces vs vanilla) is sound, but the reset gaps (attack serial, article animation phase, CPU AI) were never solved;
  zeroing `INT_ATTACK_SERIAL` or `MotionModule::set_frame` on a weapon crashes (`status_Attack_Main_button` assert).
- The whole route was parked by the user on 2026-09-29 in favour of the reskin ("no shortcuts" rules in `AGENT_RULES.md`).
