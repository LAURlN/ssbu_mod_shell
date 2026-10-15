# dk_cargo — 2026-10-02 — INCOMPLETE / NOT READY

**The requested runtime mechanic is not implemented.** This is an offline
research report, not a console-run report. The complete semantic graph required
before implementation remains incomplete. No additional authorization is being
requested; the two authorized native extensions remain unapplied.

Manifest SHA-256 `27332a68e1884fc3f744e7ffc15ad05f7bd4068c24d3a0301b1d4efb3d14a161`.
Package tree SHA-256 `95a7039c40373f34db8d3de805551144785311166755ac657e7282b63879776a`.

Review package `builds/pgwr/dk_cargo-research.1/` pins baseline 0.20.19:
28 attacker clips, four append-only sound banks, SQB/effect merges, 30 victim
pose templates and separate raw motion/config additions; 94 victim motion lists
and symbol-keyed offsets are pinned. Templates are not blanket victim overrides.
No runtime Rust, integration NRO or registration patch exists.

ID requirement: 15 attacker states plus three victim roles per eligible fighter
table (18 roles on eflame c06/c07). No production numbers selected. The 94-list
review universe includes non-playable controls, not 94 proven catchable kinds.

The user authorized cargo extensions at existing +0x170/+0x210 interception
points; these remain unimplemented. No further hook requirement is established.
Remaining work: native victim shared-pose lookup/owned aliases, complete state
and cleanup semantics, callback identity/lifetime, registration coverage and
runtime implementation/build. These are unfinished engineering work, not a
request for more user authorization or missing game inputs.

Shared dependencies: forward grab-dispatch slot global_table[0x45], existing
Monkey Flip/G&W native wrappers, victim status registrations, params, motion
lists, config, SE/VC/SQB/effect banks. Preserve Snake down throw, ordinary grabs
and other directions. Rebase bank merges on collective inputs; do not overwrite
them with 0.20.19 snapshots. No shared build/version/framework change or install.

Offline B: extractor GNU build, input hashes, graph captures, retarget readback,
entry/script hashes, bank preservation, effect round trip and package checks.
No cargo plugin build was run because no runtime Rust was added. Compilation
would not verify capture/release. No game/emulator or console result.

Reproduction: `src/pgwr/tools/dk_cargo/README.md`.
Evidence/failures: `evidence/2026-10-02_pgwr_dk_cargo/RESULT.md`.
Changed/generated files: its `FILES.json`.

## Captured semantics and limits

Tier B: `semantic.py`, `native.py`, `victims.py`, `pose_route.py` measure the
pinned 13.0.4 main/DK/common images. Full hashes and exact instruction addresses
are in `refs/donkey_cargo/{SOURCE,local_inputs,DEPENDENCIES}.json`.
DK initializer assigns global_table[0x45]; common CatchCont reads it, and grab
cleanup classifies it as a throw. Pickup sends `shoulder` through the existing
capture link. `shoulder_throw` carries the victim directional motion and generic
target work IDs. Generic native consumers queue common START/THROWN phases.
Common CARRY sends mash-expiry event 0x21ba53a92c. No hand-built capture/link
sequence was added. Candidate DK callbacks still lack independent constructor
identity and exact +0x210 trigger proof (D).

The lift helper's inspected branch toggles COMMON LIGHT_WEIGHT then a callback
also defaulted on recipient Pyra. Calling the DK helper on eflame is prohibited.
Owned kinetic/parameter initialization is still unimplemented.

Native body-hash suffixes and enum families were independently measured; body
motion IDs are not interchangeable with motion-share IDs. Pose resource lookup
passes through native resource callbacks and a MotionModule +0x190 delegate.
The delegate setter is pinned at main+0x49f9e0, but its capture-specific callback
and empty-entry sharing resolver remain unidentified. The 883 store matches are
unclassified candidates, not a complete native dependency graph.

Correction B: main exports Singleton<FighterCutInManager>::instance_E, eight
bytes at 0x52b8850. Missing Rust bindings alone do not require a raw-offset hook.
Extern-symbol pointer/ABI and runtime validation remain unperformed.

Public ACMD/bindings pins are tier C. Asset appearance, attachment and gameplay
remain unverified. No reachable cargo function was found referencing the empty
`shoulder_damage` entry; requiring it is unconfirmed.

## Failures and corrections

1. Extractor request `*shoulder*` matched no ARC path; batch aborted before
   extraction. Corrected to DK's actual `e01throwf*` clips. No game conclusion
   was drawn from the file-name mismatch.
2. NRO path without colon returned MISSING. Correct `prebuilt:/` read succeeded
   but write failed with Windows error 123. Task-local extractor sanitizes
   `:/` to `;/`; shared source untouched. Environment note in workspace kb.
3. Initial task extractor build used the host MSVC default and failed:
   `linker link.exe not found`. Explicit GNU toolchain offline build passed.
4. Base Python lacked capstone. A sandbox pip attempt failed with WinError
   10013; the permitted retry installed cached capstone 5.0.9 and
   ssbh_data_py 0.9.1 into the task cache. No system-wide dependency installed.
5. Article-locality lookup raised `ValueError: min() iterable argument is
   empty` for DK (no descriptors). Corrected to retain candidate class identity
   as tier D pending constructor proof; no false identity assertion.
6. Initial retarget staging raised `TypeError: cannot pickle
   'anim_data.GroupData' object` on deepcopy. Read-only visibility reuse fixed
   staging. Stage and readback checks passed.
7. c06 effect conversion/re-export passed; repeating c07's equivalent baseline
   dump raised RuntimeError whose retained tail was `Saving data....` repeatedly.
   Cause unverified. Final staging asserts identical baseline hashes and reuses
   c06's verified bank for c07. It does not claim the failed converter run passed.
8. Found and corrected the initial review delta's donor sound/effect/expression
   hashes: final deltas rename **all four** categories, preserving unrelated
   throws. No initial delta was installed.

9. A guessed capture-event hash assertion failed; explicit rehash identified
   `0x5ecd55cc6` as `final`, excluded from cargo. No runtime branch was guessed.
10. Fighter-kind parser initially omitted uppercase hexadecimal values (34
    missing labels); case-aware parsing passed all 94 unique symbol mappings.
11. The earlier 16 donor/22 victim unresolved calls were imported PLT tails.
    Stopping at named imports yielded zero in those Lua graphs; native virtual
    sharing callbacks remain unresolved. Zero does not mean semantic completeness.
12. Default-sandbox evidence writes failed WinError 5; reviewed workspace-only
    generator runs succeeded. No writes outside task roots were needed.
13. ADRP scans found no independent constructor reference to candidate DK vtable
    0x4fa8c80, even with 256-byte windows. Identity remains D, not disproved.
14. All-module +0x190 store scan yielded 883 candidates. Matching an offset is
    insufficient ownership evidence. Retained the address inventory; narrowed
    assembly files to the recovered MotionModule std::function setter.


No emulator/game, SD access, plugin/framework change, branch, commit, push,
shared regeneration or release-version bump. No console behavior is claimed.
