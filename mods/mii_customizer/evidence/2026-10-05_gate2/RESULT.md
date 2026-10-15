# Gate 2 - plugin 0.2.0-override on the console - 2026-10-05

Tier A (console). Written by the coordinator from the log and the user report; not rewritten.

## Installed

`libmii_customizer.nro` 0.2.0-override, sha256 `4477dc9acdbef341638a89174df5f2b8946125e0cfa24f10358cc8ad4abf59c9`;
`ultimate/mii_customizer/loadouts.txt`, sha256 `4c2ae058267e...` (ID 0000f589: weight 130.0,
walk_speed_max 1.6; no line for 0000f58b). Gate-1 probes removed. Existing mod and plugins active.

## User report (chat)

"yes, I can confirm, Gunner A is heavier and walks faster than Gunner B". No crash reported; no
crash report newer than 2026-10-03 on the card.

## Log

`log_boot1.txt`, sha256 `96d899909af6229e98373a7e94aee0ccf13d198b214d9e3ffbe4c85409e80f28`,
139 lines, one boot. L0 8, L3 46, L4 8, L5 11, L6 64, OV 2. Every L5: `dropped=0`, `orig_null=0`,
only the outcomes `ok` and `noent` (no `reent`, `gfull`, `rt`, `kindx`, `entx`, `vt`).

What was played, read from the L4 lines (the plan's Mario/Kirby control, the port swap and the
Mario + Gunner B match do not appear in the log; the user played four Gunner-only matches):

| match | player 0 | player 1 |
|---|---|---|
| 1 | 0000f589 (A) | 0000f58b (B) |
| 2 | 0000f58b (B) | 0000f58b (B) |
| 3 | 0000f58b (B) | 0000f58b (B) |
| 4 | 0000f589 (A) | 0000f589 (A) |

## Findings

1. Load: `0.2.0-override loaded`, loadout `state=ok`, `accepted=2`, `rejected=0`, `ids=1`; both
   hook sites `match=1`, `installed=1`. The six imported game functions resolved (the plugin ran).
2. Identity: every fighter line has `vt=1` (vtable 0x4f89490), `kind=74`, and `p` equal to the
   slot whose ID the L4 line shows for that player. So fighters' work objects have that vtable,
   `FIGHTER_KIND_MIIGUNNER` is 74 (0x4A) on 13.0.4, and the game's entry id is the index of the
   saved-Mii slot table, for two local players.
3. Override: all lines with `id=0000f589` show `ov=1`, weight `orig=104.0000 -> v=130.0000`, walk
   speed `orig=1.0000 -> v=1.6000`, `st=ok`; all lines with `id=0000f58b` show `ov=0`, `st=noent`,
   values 104 / 1.0. In match 4 Gunner A is overridden on player 1 as well as player 0, so the
   override follows the saved-Mii ID, not the port. Two OV lines, both for 0000f589.
4. Effect: the user saw A walk faster and be heavier than B. So the values returned by
   0x4e53e0 drive walking speed and knockback weight (the throw comparison was the planned probe;
   the user did not describe which observation showed "heavier").
5. Special-move application (L6, log-only hook at 0x4e53f0): for every fighter, calls with
   `w2` = 0, 1, 2, 3 from return addresses `0x60e9f4`, `0x60ea04`, `0x60ea14`, `0x60ea24`, and
   `w1` = 0 for Gunner A (all first options) and 2 for Gunner B (all third options); each set of
   four appears four times per fighter in the first 64 events. So the engine tells a fighter
   its special variant per slot through this function, with (w1 = option 0..2, w2 = slot 0..3),
   from one code location around `0x60e9d0..0x60ea24`.

## Not shown by this run

No non-Mii fighter was played with 0.2.0 (the `st=kind` path and vanilla values for other
characters were not exercised on the console; gate 1 showed their values with 0.1.0). The
stale-slot question (non-Mii player after a Mii match) is still open. CPU players, more than two
players and other modes untested. The no-file control boot was not needed and not run.

## Verdict

The persistence + retrieval + apply half of the vertical slice works on the console for weight
and walk speed, keyed by saved-Mii ID.
