---
title: Little Mac effect merge is prepared but lacks local recipient and converter inputs
summary: T-0050 found no recipient bank or repaired converter inside the lab and prepared a source-only merge with no installable package.
status: verified
tags: [mod-workspace, assets, effects, input-boundary]
updated: 2026-10-02
source: T-0050
---

## What

Workspace filename inspection including ignored builds, refs and gamedata found no
original ef_eflame.eff or EffectConverter/EffectLibrary. Pinned converter source is
also absent. The configured export is outside the authorized workspace and was not
accessed. Local data.arc exists; the existing extraction tool produces the archive,
not individual effect files. No in-workspace ARC reader was found.

## Evidence

PowerShell Get-ChildItem recursive file searches and rg --files --hidden --no-ignore
with ef_eflame/EffectConverter/EffectLibrary filename filters; paths.toml and existing
converter build tool inspected. No automated tests, converter, emulator or installation.
Mod-specific evidence, source hashes, planned delta and manual checks are recorded only
in `mods/ssbu_mod_new/evidence/2026-10-02_pgwr_T-0050/`.

## What to do instead / next

Export the exact recipient ARC file into gamedata using the user's viewer and provide
the repaired pinned converter companions. Source preparation is not READY; no output
hashes or claims of dependency preservation/runtime appearance exist yet. Tool changes
and their unverified limits live in the mod evidence and its CURRENT_INSTALL.md section.
