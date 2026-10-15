---
title: Offline data.arc extraction runs end to end, but readability and 13.0.4 correctness still need the user's viewer
summary: The LibHac tool extracted both base-only and patched 13.0.4 data.arc with matching hashes, yet no ARC viewer exists in the workspace so archive readability and version correctness remain unconfirmed by the user
status: verified
tags: [dump, extraction, data-arc, libhac, gamedata, unverified-limits]
updated: 2026-10-02
source: T-0032 (observed runs on this machine)
---

## What

`tools/data-arc-extract` performed a real offline extraction on this workspace: base-only and
base+update both completed, and the patched 13.0.4 result was written to
`gamedata/ssbu-13.0.4/data.arc`. **Nobody has opened that archive.** There is no ARC viewer inside
the workspace, so "the archive works" and "the archive is really 13.0.4" are **not** established -
a matching length and SHA-256 only prove the bytes were streamed faithfully from the mounted
RomFS, not that they form a valid, correct-version ARC.

## Evidence

Run 2026-10-02 from `<workspace>` (setup `-Build`: 0 warnings, 0 errors).

- Patched 13.0.4: `COMPLETE: 17600869448 bytes; SHA-256
  ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995`. Independently recomputed
  with Python `hashlib` over the written file - identical. Provenance recorded
  `selection: patched`, `selectedVersion: 13.0.4 / CNMT 1966080`, `complete: true`,
  `originalMetadataUnchanged: true`. Base Program NCA `144389b9a6d0eb19c21cad297fa7dde4`
  (content index 0, key generation 8); patch Program NCA `c641433fd07f4a934b25aeec19c4d020`
  (CNMT title `01006A800016E800`, version 1966080, type Patch,
  `ApplicationTitleId 01006A800016E000`).
- Base-only, same session: 14,460,050,172 bytes, SHA-256
  `f15156141f065283385e5efee77256f1ea72d5970f17a70292a153388a2253a8`. Deleted afterwards to
  reclaim 14 GiB; its provenance was kept at `state/scratch/T-0032/base-only-provenance.json`.
- The 13.0.4 archive is 3.14 GB larger than base-only, consistent with real patch composition
  rather than a base copy.
- Dump split parts, `prod.keys` and `title.keys` retained their original sizes and timestamps after
  both runs; all inputs were opened read-only.
- A deliberately killed run left only `data.arc.partial` plus an `in-progress` journal with
  `complete: false` and **no final archive**, which is the intended interruption behaviour.
- Rejections exercised: DLC package (`Mismatched/DLC content: ... found AddOnContent
  01006A800016F001`), split gap, empty part, non-PFS0 content, `--base-only` with `--update`,
  neither flag, `..` traversal, output outside `gamedata/`, output outside the workspace, and
  output equal to an input file.
- No ARC viewer exists under the workspace: `testenv/` holds only `ryujinx/` and `scenarios/`.
  The known viewer is the user's ArcExplorer install outside the workspace, which this task did
  not access.

## Why

The bench on automated testing means agents cannot settle "is this archive valid" without a
viewer, and the only compatible viewer is outside the workspace boundary. Recording this prevents
the next agent from reading a green `COMPLETE:` line as proof the archive is usable.

## What to do instead / next

The user should open `gamedata/ssbu-13.0.4/data.arc` in their existing ArcExplorer, browse a few
entries and extract exactly one known entry into `gamedata/` only. Alternatively install a
compatible ARC viewer inside the workspace as an explicit prerequisite. Until then, treat any
downstream work that needs ARC contents as blocked on that check, and keep the tool's registry
status `experimental`. Full command list and pass/fail signals:
[the tool README](../../tools/data-arc-extract/README.md).

## Update 2026-10-02: the archive is readable (verified offline)

`tools/arc-extract` (smash-arc 0.6.0) opens `gamedata/ssbu-13.0.4/data.arc` and extracts files
from it. Two extracted files were compared with independent copies: `effect/fighter/eflame/ef_eflame.eff`
is byte-identical to the user's ArcExplorer export, and `fighter/snake/motion/body/c00/c02attackhi3.nuanmb`
has the sha256 of the copy pulled from the running 13.0.4 console over arc-network. So "no ARC
viewer exists in the workspace" and "readability unconfirmed" above no longer hold. Still
unverified: that every file matches 13.0.4 (two files were compared, not the whole archive).
See [the playbook](../playbooks/extracting-single-files-from-data-arc.md).
