**dk_cargo (2026-10-03, Codex): READY for private hardware test; NOT INSTALLED, gameplay unverified.**

Package `builds/pgwr/dk_cargo-0.1.0-test/`; task version 0.1.0-test, shared
plugin/info version 0.20.20. Includes the checked Gaogaen 0.3.0 baseline and
Snake/Lucas/Ness changes. NRO `270bc6723393767b7ae0dd639faae821fe0ffde6357938a552bed41a7faa7795` (581632 bytes).
Mod tree `dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e` (5098 files; SHA256 sorted path/TAB/hash/LF).
Manifest `ad10838399da61f99b63f52b36ab58e0f1ed2980c9af4ffa957b3de24c9f339e`. Asset delta: 3126 declared paths; 725 list append operations;
2359 victim clips including 36 full shared templates; 28 attacker clips;
append-only SE/VC/SQB and checked effect merges. Baseline entries preserved.

Offline B: isolated release build passed; source/baseline, callback, ID,
motion/config/bank/hash and linked SIMD-return checks passed. No game/emulator
or console result; compilation does not verify capture or release.
Implementation owns 15 attacker states, three victim roles, native translated
callback closure, clatter/offset parameters, motion aliases, four ACMD families,
escape/release/cleanup. Host G&W baseline physics and geometry require review.

Full collective ID requirement: 15 attacker + 3 victim states per eligible
table, 18 on eflame. Production IDs unallocated. Private test uses audited
0x400..0x411, above native NUM maximum 0x37d, disjoint from shared IDs.
No production shared ID edits. Additional pending moves must be conflict-checked.

Shared integration: UNAPPLIED four-file `src/pgwr/tools/dk_cargo/integration.patch`;
Patch check: `git apply --ignore-whitespace --check` passed against the exact
recorded live baseline. Plain apply check rejects mixed LF/CRLF context.
status registration, existing Monkey Flip +0x170 receiver, G&W +0x210 callback
(only explicitly authorized cargo extensions), existing exported Gaogaen throw
classifier. Forward slot global_table[0x45] changes only eflame c06/c07.
Victim bridges are gated by an owned captor; actual victim native pickup scripts
and generic engine link/shared-motion interfaces remain dependencies. No DK
specializer on eflame, manual capture/link construction or per-frame forcing.
Framework plugins untouched; no further reserved hook requirement established.

Mergeable deltas: package `ASSET_DELTA.json`, config/motion-list additions,
sound/effect/animation audits and `integration.patch`; regenerate semantic banks
against a different collective baseline. Runtime sources under
`src/pgwr/plugin/src/status/dk_cargo/`; private compile snapshot/cache under
`builds/.cache/dk_cargo/`. Reproduction: task tools `README.md`.
Checks/evidence/failures/files and twelve hardware checks:
`evidence/2026-10-03_pgwr_dk_cargo/RESULT.md`, `FILES.json`, `LINKED_ABI.json`.

Evidence tiers: B = measured local bytes/build, C = pinned public source,
D = predicted recipient behavior. No tier A result. Native inputs: main
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613;
DK NRO 14030b3cfb605cddf114ba5f140dbd554515b7834209e15067a6dd632c9b555b;
common NRO 43876f961a80e413370629d32c23af9de6e4cc26b448bab88d5433714a566097.
Public ACMD commit 59004685238a3f6f93bae905d3a4e079701c40b4 (C).
Reviewed contract pins 71 attacker + 48 common/helper functions, 10911
translated instructions and 152 classified relocations; no unresolved indirect
calls in that owned closure. Generic engine interface internals are dependencies,
not a claim of complete engine decompilation. Donor class-factory identity remains
a D hypothesis; no donor class callback is invoked by this port.

Verified failures/corrections (B): private getter missing-key path returns zero,
not neighboring value 13; long-lived const-bank registers defeated older semantic
annotations, fixed with independently decoded bank; ABI signature extra parent-ID
argument caused E0061, corrected to SDK; own-ID ADR_PREL/LDST PIC linker errors
fixed with hidden symbols; ABS64 text callback pointers replaced with owned
ADRP/ADD. Cached BUILD-linker-failure.txt and BUILD-pointer-relocation-failure.txt
record exact errors. Victimlocal pickup filenames collided with eflame captor
templates, corrected before final stage. Prepackage retry appended aliases twice,
corrected to native ARC baseline for newly introduced lists. Native callback
registration measured 18, replacing guessed 24 (no Exec/MapCorrection).
Framework source supports wildcard statuses but concrete-kind ACMD only;
per-kind scripts now registered without a framework change. Final checker first
compared an intermediate append hash to the final twice-appended list, then
incorrectly assumed 96 victim-template nodes; corrected to exact native 26/67
track lists. Final package and linked SIMD checks passed after corrections.

Record tool initially used Windows default cp1252 for the changelog and failed
UnicodeDecodeError on byte 0x9d; corrected to explicit UTF-8 before recording.
Integration patch normalizes text line endings while the shared baseline is
mixed LF/CRLF. Plain git apply --check failed at status/mod.rs:61 and
gaogaen_throw_b.rs:71; all four baseline hashes still matched. The explicit
git apply --ignore-whitespace --check passed. No source patch was applied.

Build retains SDK SIMD Vector3 FFI warning; LINKED_ABI.json checks supported
returns load x/y/z into v0 and reach the epilogue without mutation. This verifies
only this compiled artifact. Generic capture check_damage_thrown virtual
implementation is not fully decompiled; console routing/cleanup must be tested.
Host baseline physics, retarget alignment, runtime clipping, playback and all
capture/release behavior remain D/unverified. There is no established additional
reserved-hook/framework blocker. Production allocation is pending as above.

Installer: complete package over its exact baseline using CURRENT_INSTALL.md
workflow, protected framework plugins OFF. No files have been installed here.
Reproduction: src/pgwr/tools/dk_cargo/README.md; CHECKS.json and BUILD.txt in
package. Manifest source_tool_pins are packaging-time provenance; task docs and
the secondary verifier were updated afterward without modifying payload.

Hardware checks (maximum twelve). Send log from boot and any crash report:

1. Save hashes and log from boot. Expect `REGISTERED task=dk_cargo-0.1.0-test private_ids=0x400..0x411 costumes=[6, 7] production=unallocated`. Compare vanilla DK and Pyra c00/c01; normal grabs and other throw directions must remain ordinary.
2. c06 and c07 standing/dash/pivot grabs, forward direction: one `PICKUP`, attacker 0x400, `VICTIM_ROUTE` to 0x40f. Confirm actual published capture and advancing attacker/victim frame/end values, rather than status requests alone.
3. Ground carry: pickup completion, idle, slow/fast walk, turn, forward/backward jump squat and platform pass. Compare vanilla DK priorities and attachment.
4. Jump, drift, walk off a platform and land. Confirm ground/air transitions and recovery; host G&W baseline physics remain.
5. Four ground cargo throws, both facings: states 0x40b..0x40e, victim 0x411, donor damage/angle/timing and one release.
6. Repeat all four throws airborne: donor kinetics/recovery/landing; victim gains normal control after release.
7. Low/high-damage mash escape: decreasing clatter, `ESCAPE event=0x21ba53a92c`, catch-cut and victim control restored.
8. Victim poses: several sizes, body suffix variants, G&W, another c06/c07 pair and Pickel overlay. Confirm advancing clips/end frames and aligned carry/throw anchors.
9. Slopes, platforms, ledges and blast zones: compare donor restrictions; no orphaned capture constraints.
10. Third-party hits, attacker/victim death, rebirth and match reset: interruption/end/cleanup, no stale link, invincibility or hidden items.
11. Swap requests/departures while carrying or throwing: compare restrictions; no victim attached to the dormant body and no stale state on return.
12. Regression: Snake down throw, Incineroar back throw, Ness back throw, Lucas down smash, normal grabs and unrelated moves. Repeat vanilla DK/Pyra controls; return log from boot and any crash report.
