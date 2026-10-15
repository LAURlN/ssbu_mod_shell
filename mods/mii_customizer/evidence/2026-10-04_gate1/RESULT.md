# Gate 1, test 1 - plugin 0.1.0-diag on the console - 2026-10-04

Tier A (console). Written by the coordinator from the log; not rewritten afterwards.

## What was installed

`atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro`, sha256
`ae49c1c84da39cf454f41811c75ed5e22cde21cfd63a9b530b592b15ee8c96af` (package
`builds/0.1.0-gate1/step1_plugin/`). Other plugins on the card unchanged, including the existing
`libpyra_gamewatch_reskin.nro` and smashline; `ultimate/mods/pyra_gamewatch_reskin` active.
No file probes installed for this test.

## What the user did and reported

Ran test 1 from `CURRENT_INSTALL.md` (control match with two non-Mii fighters, match with two saved
Mii Gunners, Mii editor visit, second Gunner match). Report in chat: "nothing crashed or seemed
weird in any way ingame". Which two control fighters were used and which Gunner was P1 were not
stated; the plan asked for Gunner A (first option in all four special slots) as P1 and Gunner B
(third option in all four) as P2.

## Log

`test1_log.txt` in this folder, copied from `sd:/ultimate/mii_customizer_log.txt`, sha256
`2ad80c8ab6bf80477003ab35f313b98c6ec40f4a6f2534b7c3568103742fe253`, 137 lines, `seq` 0..136
without gaps. Lines by event: L0 8, L1 64, L2 7, L3 45, L4 6, L5 7. Every L5 has `dropped=0` and
`orig_null=0`. No crash report newer than 2026-10-03 exists in `atmosphere/crash_reports/`.

## Findings

1. **Offset convention confirmed.** L0 seq 1-6: at `base+0x179e440`, `base+0x17c8210` and
   `base+0x4e53e0` the four instruction words equal the words of the offline 13.0.4 image
   (`match=1`), all three hooks `installed=1`, patch form `58000051,d61f0220,<addr>` (far form,
   four words). File offset of the flat image == Text-region offset on the console.

2. **0x4e53e0 is a per-fighter float-param getter, read repeatedly.**
   - Control match (seq 44-60): two parents. `0x2472a31580`: walk_speed_max 1.1550, weight 98.0.
     `0x2472a40ec0`: walk_speed_max 1.5230, weight 77.0. Two different fighters, two different
     parent pointers, values differ per parent.
   - Gunner matches: parents `0x24730e8d80` / `0x24730f86c0` (match 1) and `0x242f1248c0` /
     `0x242f114f80` (match 2), all walk_speed_max 1.0000 and weight 104.0, which are the Gunner
     row values of `fighter_param.prc` (B, P2-STAT-API). New parent pointers in every match.
   - Counters grow during play: walk_speed_max 62 -> 379 -> 537, weight 7 -> 48 -> 63. The values
     are requested again and again, not once at set-up.
   - `x2` is 0 in all 45 L3 lines. Return addresses inside the module: `0x6d42d8`, `0x6d86f0`,
     `0x6c65b0`, each directly after a call site listed in P2-STAT-READS (`0x6d42c0`, `0x6d86d4`,
     `0x6c6590`). Return addresses printed as `0xffffffcc97a5....` lie outside the main module
     (below its base): callers in another loaded module also arrive at this function.
   - Not shown by this log: which parent belongs to which player.

3. **Per-player saved-Mii slots are filled at fighter creation, by player index.**
   - Control match L4 (seq 45, 51): all eight slots `00000000:00000000`.
   - Gunner match 1 L4 (seq 62, 66) and match 2 L4 (seq 115, 118), each at the first param request
     of a new fighter: `p0=0000f589:00000000`, `p1=0000f58b:02020202`, p2..p7 zero.
     Two different non-zero IDs; special bytes all-first on player 0 and all-third on player 1,
     which is the assignment the plan asked for (A = P1, B = P2).
   - Editor visit (seq 83-85): the record loader was called with id `0x0000f589` from return
     addresses `0x1810074`, `0x18102d4`, `0x180fcb8`, the editor functions of P2-SKILL-STORE /
     P2-MATCH-READER. The user opened Gunner A there, so `0xf589` is Gunner A, and it is the ID in
     player slot 0. This also ties scene `0x1808980` to the Mii editor.
   - The IDs were identical in both matches, before and after the editor visit.

4. **Who fills the slots is not the hooked store function.** `l1` is 36 in every L5 of the control
   match and of Gunner match 1: `0x179e440` was not called between the two, yet the slots changed
   from zero to the two IDs. All 64 logged L1 calls (return addresses `0x235b6ec`, `0x178d168` ..
   `0x178d9f0`, `0x17b0040`) left their slot at `00000000:00000000` (they look like resets of all
   eight players; meaning D). The loader call with return address `0x230f2a8` (function
   `0x230d4c0`, which reads the ID back from the slot) appears after each Gunner match (seq 81-82,
   135-136), not before it. 823 loader calls from the address range P1-ID-REVIEW called "editor"
   happened before the first Gunner match, i.e. that range is also active outside the Mii editor
   (D: Mii lists on the character select screen).

## Verdict

Questions 1-3 of the gate are answered:
- offset convention: confirmed;
- weight / walk_speed_max requests reach `0x4e53e0` per fighter object and repeatedly: confirmed;
- saved-Mii ID per player readable from `T+0xe58+p*0x240` when the fighter is created: confirmed
  for two local players in a normal Smash match, in two matches.

Open after this test: the mapping from a param request's parent object to the player index; slot
contents for CPU players, more than two players, other modes, and for a non-Mii player selected
after a Mii match in the same session (stale-slot question); question 4 of the gate (file probes,
test 2).

Control used: the non-Mii match in the same boot (slots zero, different weights per parent).
