---
title: Hero mana research recovered local main; the ARC inputs turned out to be readable after all
summary: T-0049 decoded the local 13.0.4 main; T-0057 then refuted this note's input-boundary claim by reading the donor vl.prc and the HUD layout out of the local data.arc with tools/arc-extract.
status: verified
tags: [mod-workspace, pgwr, research, nso, input-boundary]
updated: 2026-10-02
source: T-0049; corrected 2026-10-02 by T-0057
---

## What

The ExeFS main configured in the mod paths.toml is inside this lab. T-0049 decoded
it into `gamedata/ssbu-13.0.4/main.bin`; embedded section hashes and the known flat
image hash matched. Game findings stay in the mod repo's
[contract](../../mods/ssbu_mod_new/refs/brave_special_n/T-0033/MANA_HUD_CONTRACT.md)
and [provenance](../../mods/ssbu_mod_new/refs/brave_special_n/T-0046/main_provenance.json).

## Evidence

One-off captures in `state/scratch/T-0049/` reused the NSO segment algorithm from
mod `tools/inspect_main.py` and `tools/main_image.py`. The existing project-local
`src/mgw_swap/tools/analysis_lib/capstone` supplied disassembly without installation.
Pure standard-library LZ4 decoding was checked against each NSO section hash; this
was evidence extraction, not an automated test. Main flat SHA256:
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.
A pip dependency request stalled without output and was cancelled; no successful
installation is claimed. Existing in-repo lz4 binaries target CPython 3.8, while this
session uses 3.12; they were not used.

## Input boundary (CORRECTED 2026-10-02 by T-0057 - this is the retraction)

The three sentences below were true about *this workspace's tools at the time* and were
read as a claim about the data. They are not. `tools/arc-extract` reads individual
entries out of `gamedata/ssbu-13.0.4/data.arc`, and both of the "absent" files came out
of it: `fighter/brave/param/vl.prc` (sha256 `dafa43c6...`, which is the same file the mod's
`donor_params.rs` was generated from) and
`ui/layout/info/info_melee/info_melee/layout.arc` (sha256 `c382a6e5...`, whose MP gauge is
`info_melee_lct_player_sp`). Hero's six spell prices, the 100 ceiling and the recovery
period are now measured. The general lesson is recorded in the mod repo as
`handbook/graveyard.md` R-HERO-MANA-2 and R-ARC-1: **an empty folder in the user's
ArcExplorer export, or a null result from grepping a hash-indexed container, is not
evidence that a base-game file is missing.**

Original text, kept for the record:

## Input boundary (as written 2026-10-02 by T-0049)

Workspace inventory found no original Hero/common NRO or Hero vl.prc. The configured
ARC export is outside the lab and was not read under the stay-inside instruction.
This does not establish whether those files exist in that export. The local patched
ARC container is present; the current extraction tool does not expose individual
ARC entries. The precise small export/read-authorization request is in the contract.
No console, emulator, tests, build, card access or production edit occurred.
