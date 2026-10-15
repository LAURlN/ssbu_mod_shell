# Hardware test protocol

Tiers: **A** hardware-confirmed (console or decoded crash report) - **B** measured offline by a script that still exists - **C** read from pinned third-party source - **D** hypothesis. Anything without a tier below is A/B unless marked otherwise. Paths in the source column refer to the *old* workspace (`modpack_test_1`); the same material now lives under `projects/*/history/`, `dumps/` and `evidence/`.

- Development agents queue their changes in `CURRENT_INSTALL.md`; only the user-designated collective installer installs. Canonical workflow: `AGENTS.md` rule 23 (user instruction, 2026-09-30).
- Installer hands over: exact file + SHA-256, exact SD destination, numbered short test, which log lines prove what, a vanilla negative control. Log prefixes `[MGW-*]`, `[PGWR*]`; file log `sd:/ultimate/pgwr_log.txt` reset per run.
- One change per build for anything that mutates state (two changes at once turned a diagnosis into a revert). A change that moves a crash *earlier* is a regression: revert, do not stack a third variant on the same premise.
- An invalid test is not a code failure: verify the card really holds the build before interpreting (`grep -c` a marker in the NRO). The "none of the moves are visible" report was a 0.8.x card.
- Compilation, offline byte-compare and lint are never validation.

---
