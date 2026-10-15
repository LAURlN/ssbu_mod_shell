# Swap / pairs

Tiers: **A** hardware-confirmed (console or decoded crash report) - **B** measured offline by a script that still exists - **C** read from pinned third-party source - **D** hypothesis. Anything without a tier below is A/B unless marked otherwise. Paths in the source column refer to the *old* workspace (`modpack_test_1`); the same material now lives under `projects/*/history/`, `dumps/` and `evidence/`.

- Pair = one fighter entry with sub-fighter table redirected `[90,91,-1]` -> `[28,91,-1]`; Element changer machinery is native. (A)
- Pose repair must run **after** the native restore returns (an early nested WAIT callback got overwritten by the original departure pose). (A, 2026-09-15)
- Drop any held live item before the owning body goes dormant. Per-entry state in fixed arrays tagged with owner id, cleared at boundaries. (A/B)
