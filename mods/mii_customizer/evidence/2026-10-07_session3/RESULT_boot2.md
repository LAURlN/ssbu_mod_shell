# Session 3, boot 2 - plugin 0.5.1-menu - 2026-10-07 (tier A)

User report: "everything seemed to work as intended"; no extra Kirby jumps (expected: jump
count is an integer parameter, not in the 41-float presets).

Log: `log_boot2.txt` (491 lines, sha256 `3076370e...`; boot A lines 1-388, reboot from 389).
`loadouts_after_boot2.txt`: `0000f58b preset kirby`, `0000f589 preset dedede`. The edited Mii
was Gunner B (`0000f58b`), not A as the plan said; nothing depends on which.

| claim | evidence in the log |
|---|---|
| foreign hook accepted, hooks in | `L0|ui_probe_entry_hooked=0x37a22f0|accepted=1`; `sites|ui=on|sites_ok=6/6|probes_ok=48/48|installed=6` |
| main page on a list shorter than the native one | `open|page=main|native_count=52|rows=24`, `list|count=24|available=24|cursor=0|tick=-1` (5 visits) |
| literal row text set, never missed | `text_set` 40..582 per main page, `text_missed=0` on every page; through the foreign hook without a crash |
| page change by in-place restart of state 5 | 24 `page` lines over 4 visits (longest: 10 changes, 11 pages); every one `depth=1|equal=1|record_equal=1` |
| stack depth constant | every `exit`: `depth_open=1|depth_now=0` |
| slot page: only the default available, greyed rows drawn | `list|page=entry:special_up|count=87|available=1|cursor=0|tick=0`; `greyed_fills=1662`, `1608`, `28`, `28` |
| greyed rows not decidable | no `refused_unavailable` line; the only slot decisions are `row=0 ... action=slot_nothing_stored` (how often A was pressed on a greyed row is not in the log) |
| B on an entry page returns to its row | `page|from=entry:special_up|to=main|...|cursor=22`, `list|page=main|...|cursor=22`; same for rows 11, 1, 0 |
| stats: set, tick follows, clear | `decide row=38 dedede set` -> next `list cursor=38|tick=38`; `row=6 kirby set` -> `cursor=6|tick=6`; `row=0 ... action=clear` -> `cursor=0|tick=0`; then kirby again |
| saved each time | four `SV|result=ok` (60, 59, 37, 59 bytes) |
| Mii unchanged | 4 `exit` lines, all `hat_before == hat_after`, `equal=1|restored=0|record_equal=1` |
| sort button harmless | `sort_ignored=3` |
| applied in a match | 22 `OV` lines `id=0000f58b ... preset=kirby` |
| survives a reboot | second boot: `L0|loadout|...|bytes=59|accepted=2`, `LO|id=0000f58b|preset=kirby`, `LO|id=0000f589|preset=dedede` (first time a plugin-written file is read back) |
| no fallback path taken | no `open_refused`, `visit_lost`, `stale`, `reentry`, `close_unexpected`, `log_cap` |

Not exercised or not visible in the log: way in B (ZL/ZR); the normal headgear / outfit
screens leave no line by design (user reported nothing wrong); how the greyed rows and the
text looked, and cursor movement over greyed rows (user: as intended); `text_off`, `ui_off`.
Observation: `greyed_fills` grows by about 1600 on a slot page that stayed open a while, so
the row filler runs far more often than once per scroll step (per frame for visible rows,
D). Literal text is set on each of those fills on the main page (`text_set` up to 582):
two game allocations per row fill. No problem seen; worth a look if the menu ever stutters.
Still unknown: which plugin hooks `0x37a22f0`.
