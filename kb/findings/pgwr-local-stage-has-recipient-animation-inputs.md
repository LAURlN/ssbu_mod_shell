---
title: The local pgwr 0.20.16 stage contains recipient animation inputs
summary: Ignored release files are present even when rg --files omits them; T-0036 used the complete local stage without external exports.
status: verified
tags: [mod-workspace, pgwr, assets, staging]
updated: 2026-10-02
source: T-0036
---

## What

The local `mods/ssbu_mod_new/builds/pgwr/0.20.16/` contains a complete 1983-file mod
tree and the recorded plugin NRO. `rg --files` without `--no-ignore` did not show
its ignored skeleton/animation files. Native PowerShell enumeration found them.
`mods/ssbu_mod_new/dumps/arc` is absent; no outside-workspace export was accessed.

## Evidence

`Get-ChildItem -LiteralPath builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin -Recurse -File`
from the mod root found 50 `.nusktb` and 1009 `.nuanmb` files, among other assets.
T-0036's existing move generator read the actual local built recipient skeleton
and idle clips and staged an animation-only variant retaining the baseline NRO.
This is generation/source inspection evidence, not an automated test or game run.

## Why

The mod's `.gitignore` excludes builds, and rg honors ignores by default.
Read-only asset discovery should use `rg --files --no-ignore builds/pgwr/<version>`
or native enumeration before declaring an input missing.

## Next

Mod-specific recipe, commands, hashes and unverified visual checks live only in
[the motion handbook](../../mods/ssbu_mod_new/handbook/04_motion_lists_animation.md)
and [the down-tilt installer section](../../mods/ssbu_mod_new/CURRENT_INSTALL.md).

## Overlapping assignment inspection — 2026-10-02, T-0051

Read-only native enumeration and `Get-FileHash` again found the actual local
recipient inputs and existing candidate. Missing dump exports are not the blocker.
T-0048's queue record remained `in_progress` with explicit ownership of the same
recipe and generator assigned to T-0051; no T-0048 result was present when inspected.
T-0051 therefore did not switch the shared branch, edit mod files, take a build
reservation, or generate a competing stage. The existing package was preserved.

Newer user intent is recorded in `tasks/queue/T-0045-*`, including feedback on the
already custom animation. Do not treat T-0036's historical review as acceptance of
that newer request. Mod-specific measurements and proposed changes remain solely in
[T-0047's design record](../../mods/ssbu_mod_new/evidence/2026-10-02_pgwr_T-0045/T-0047_design_record.md).
The overlap and manual review questions are recorded in
[T-0051's result](../../state/results/T-0051.json). No automated tests, emulator,
card access or new animation generation occurred.

## Collective build-only verification — 2026-10-02

The requested T-0036/T-0042 batch already shares one complete versioned package.
The designated worker reused it and measured local files with the existing mod
verification tool; no device access or fresh Rust compilation occurred. Batch
coverage, hashes, source normalization and limitations are recorded only in
[the mod verification record](../../mods/ssbu_mod_new/evidence/2026-10-02_pgwr_console-89c7baa998178f244493-build/VERIFY.json).
