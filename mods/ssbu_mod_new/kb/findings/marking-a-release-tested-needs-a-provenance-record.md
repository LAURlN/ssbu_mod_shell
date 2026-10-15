---
title: Marking an installed release "tested" needs a provenance record, and a verdict is not a result
summary: The user declared everything on the card tested; recording that honestly means writing "exercised" where no verdict was reported, anchoring it to on-card logs and crash-report timestamps, and never promoting it to "passing".
status: verified
tags: [pgwr, testing, evidence, process, installer, mod-workspace]
updated: 2026-10-02
source: T-0056
---

## What

T-0056 asked for two things: "mark everything that is installed on the SD card right now as
tested" and "install the new changes". The first is a declaration with no attached evidence -
no log, no verdict per item - and it lands in a queue file where several sections carried
open questions. Recording it as "passed" would have been a lie in a document other agents read
before touching the card.

## How it was recorded

Each installed section in `CURRENT_INSTALL.md` gained one line:

> TESTED 2026-10-02 (T-0056): exercised on hardware by the user.

plus, where it mattered, the reason the item is *exercised* rather than *passing*:

- **Little Mac angled forward smashes** - the routing question (does the engine ask for
  `attack_s4_hi` / `attack_s4_lw` on eflame at all?) stays open, because nobody reported
  whether the animation differed. Written as "exercised too, but no verdict was reported".
- **T-0036 down tilt recipe 2.0.0** - exercised, then superseded on the card an hour later by
  recipe 3.0.0, so its verdict describes an animation that is no longer installed. Stated, so
  nobody re-tests a clip that is gone.
- **Hero side-B 0.20.15** - its existing per-level verdicts (level 1 pass, level 2 bolt points
  down, level 3 fails) are kept as they were; a new declaration does not improve them.

Independent anchors that were on the card and cost nothing to read, used as corroboration
rather than as the claim itself:

- `sd:/ultimate/pgwr_snake_log.txt` - 5198 lines, several `BOOT v0.20.16` sessions, **0**
  `FAIL`/`REFUSED`. Archived with its sha256 (`d146f7ae...`).
- `sd:/atmosphere/crash_reports/` - newest file 2026-09-30 04:09, i.e. **no crash** from any
  0.20.13 / 0.20.14 / 0.20.15 / 0.20.16 run, which is the strongest thing a boot-only build can
  say for itself.

## What this buys

- `CURRENT_INSTALL.md` installer procedure step 6 now requires a provenance line for any future
  "mark as tested" instruction, and forbids promoting an item to *passing* without a reported
  verdict. The next agent cannot read the file as a claim that the Little Mac angled variants
  were proved to route, or that the stretched-arm down tilt looks right.
- It also stops the opposite error: a "tested" mark that silently expires. Both the 0.20.7
  Monkey Flip section and the T-0036 section now say in one line what superseded them.

## Not verified

That the user in fact exercised each individual item. A blanket declaration is evidence about
the *card state*, not about the 0.20.16+robot-dtilt.4 release as a whole, and the two differ:
the declaration arrived while the card held recipe 2.0.0 and it was replaced within the hour.
The open questions that were never answered stay open; only the record of "asked, not answered"
is new. See also `kb/findings/pgwr-card-autodetect-and-asset-only-installs.md` for the install
side of the same day.