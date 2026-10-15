# Prerequisite 0.6.0 — new motion kinds + a custom status

Written 2026-09-29. This is the NO SHORTCUTS prerequisite, not a finished move.
Judge is one number out of nine and has no hitbox yet.

## Installed on the card

```
sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/
  libpyra_gamewatch_reskin.nro
  cbeacca69da00e70166dab9027a9c7e5a039ba4d539f308b380dc5193b901288
sd:/ultimate/mods/pyra_gamewatch_reskin/    assets 0.6.0
```

The asset tree was re-copied wholesale, not patched: 0.5.0 on the card predated
the visibility-completion pass, so every clip differed. `diff -rq` against
`mod_output/` is clean. The four framework plugins were re-hashed after the copy
and are byte-identical to their pre-install values. Rollback is
`sd_backups/2026-09-29_before_pgwr_0.6.0/`.

## What was added

Motion list, `eflame/motion/body/c06` and `c07` — two new entries, copied whole
from G&W's own list:

| kind | clip | file status |
| ---- | ---- | ----------- |
| `special_s_1` | `d01specials.nuanmb` | overwrites Pyra's side-special clip (eflame already had that name) |
| `special_s_1_l` | `d01specialsl.nuanmb` | **new file** — a name eflame has never had |

729 stock entries → 731, all 729 byte-identical, and the build asserts that every
clip the finished list references resolves to a real file.

Plugin, one custom status:

| id | name | entered by |
| -- | ---- | ---------- |
| `0x1EE` | `JUDGE` | ground side-B, via the `Pre` of Pyra's `SPECIAL_S` (`0x1DD`) |

`Pre` plays `special_s_1`; at frame 16 it releases the `panel` visibility group
and plays `special_s_1_l`; at frame 46 it hands the character back to idle.

## The test

Boot into a match as **Pyra c06**. Log filtered on `[PGWR]`.

**Expected at boot**

```
[PGWR] Pyra G&W reskin plugin v0.6.0 (prerequisite: G&W motion kinds + custom Judge status) loaded
[PGWR] gated fighter=eflame costumes=[6, 7]
[PGWR] NOT registered: elight (Mythra), gamewatch (real G&W)
[PGWR] GATE ACTIVE: entry 0 running c06/c07 overrides, reported colour 6
```

**Press side-B once.** Expect, in order:

```
[PGWR] JUDGE redirect: entry 0 -> status 0x1ee
[PGWR] JUDGE enter: status 0x1ee entry 0 colour 6 motion special_s_1
[PGWR] JUDGE hold: entry 0 at frame 16 motion special_s_1_l
[PGWR] JUDGE end: entry 0 at frame 46
```

**What you should see:** G&W pulls out the Judge and holds up a number card,
then drops back to idle about ¾ of a second later. No sword, no Pyra side-B
animation at any point.

### Numbered checks

1. **Pyra c06, side-B.** The four log lines above, and G&W's Judge pose. This is
   the one that matters.
2. **Pyra c07, side-B.** Same four lines with `colour 7`. Same pose.
3. **Vanilla Pyra c00–c05, side-B, each one.** Pyra's Rethunder Toss, her
   animation, her sword. **No `JUDGE` line in the log for any of them** — that
   absence is the control, and it is the thing that has been skipped twice now.
4. **Mythra, any colour.** Vanilla. Down-B to Pyra lands on c06 only if Mythra
   was c06/c07; then side-B is Judge, and down-B back to Mythra is normal.
5. **Real Mr. Game & Watch, side-B.** Completely vanilla, no `[PGWR]` lines.
6. **c06, side-B, three times in a row.** Each press gives one clean Judge, no
   double pose, no stuck state.
7. **c06 while airborne, press side-B.** Nothing should crash. The air Judge is
   *not* built yet, so this may do nothing or may do the ground pose — record
   which, that is the input for the next build.
8. **c06, side-B, then get hit mid-pose.** He must recover to idle normally.

### Report back

For each of 1–8: what you saw, and the `[PGWR]` lines. If anything crashes, the
Atmosphere report plus the full Skyline log.

## What this test can and cannot tell us

**It proves**, if it passes: a motion-list entry can be added to `eflame`; a clip
file name that never existed for `eflame` can be added and loads; a status id
above Pyra's table can be registered through the costume gate and entered; a
G&W motion kind played from it animates.

**It does not prove** the rest of Judge. Specifically still missing, and listed
in the handoff so nothing is quietly dropped: the other eight numbers and
G&W's odds-without-repeat rule, the `SpecialS1Sub` hitbox (so no damage, no
launcher, and the number card is currently decorative), `SpecialSCommonA/B`, the
air Judge and the `special_air_s_N` kinds, the panel and number-card effects,
and G&W's sounds.

## Two things I got wrong along the way, both now in the guide

The old "never add a new file name" rule was too broad, and the reason recorded
for it was wrong. The real invariant is that a motion entry may not name a clip
present in neither the game data nor the mod. A new clip *name* in an existing
motion directory is fine — the earlier console-verified Monkey Flip build
already shipped donor clip names that way.

And `special_s_1`, the obvious candidate, turned out **not** to need a new file:
`d01specials.nuanmb` already exists under `eflame` because it is Pyra's side
special. Measuring first is what surfaced `special_s_1_l` as the entry that
genuinely tests file addition.

## One unknown worth watching

The motion entries carry a 28-byte tail of undocumented per-kind data — three
hashes and three frame values. They are not mesh names and they do not decode
from `model.numshb`. I copied G&W's bytes rather than guess at them. If those
hashes are fighter-specific triggers, the corresponding effect or sound simply
will not resolve on `eflame` and nothing else is affected. The log cannot show
this; only the console can.
