# P5-MSG-PROBE - can the mod add its own menu text labels? Source facts and one staged probe

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Report exact inputs/hashes, commands, observed
checks, failures and limits. B is offline observation, C pinned source, D
hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create every
folder INSIDE mods/mii_customizer/ and make scripts write there, never into the
current directory. Use `python`, not `python3`.

Background (console, tier A, evidence/2026-10-04_gate1/RESULT_test2.md): the Mii
special-move screen's sub-title is set from Lua with a message key
(`set_sub_title("mnu_mmiif_setup_sp_move_title")`), and swapping that key for
another existing key changed the text on screen. The mod will need its own texts
(stat names, option names). The keys live in ui/message/msg_menu.msbt.

One goal: establish from pinned sources how a mod can add or override message
labels with the file loader that is on the user's card, and stage ONE probe that a
later console session can use to see a brand-new label on screen. Nothing is
installed and nothing is marked READY.

Part 1 - source facts (C). The loader on the card is ARCropolis (plugin file
`libarcropolis.nro`, 2347008 bytes, sha256 starting 49b6f634039f; kb note
workspace-relative kb/reference/ssbu-modding-stack.md names v4.1.1 as the release
checked on 2026-09-25, unverified for this card). From the official ARCropolis
repository (github.com/Raytwo/ARCropolis), pin the tag or commit you read and
answer with file and line citations:
 a) Does it support message patch files (commonly `.xmsbt`) placed in a mod
    folder? Which path and file name does it expect for msg_menu? Which text
    encoding and XML shape (element and attribute names) does its parser accept?
 b) Does a patch add labels that do not exist in the base file, or only replace
    existing ones? What happens with duplicate labels across mods?
 c) Is there any region/language handling in the file name or path?
 d) Since which version does this exist, and is it enabled by default?
 If the repository's releases let you match the card's NRO size or hash to a
 version, say so; otherwise state that the card's version is not established.
 Read source and docs only; download no binaries.
 Before reading inside mods/ssbu_mod_new/ read its AGENTS.md,
 projects/pgwr/STATUS.md and handbook/00_INDEX.md; then check whether the handbook
 or that mod's shipped tree already uses a message patch (search for `xmsbt` and
 `msbt`), and quote what you find with its tier.

Part 2 - local facts (B). Extract workspace-relative ui/message/msg_menu.msbt from
gamedata/ssbu-13.0.4/data.arc with tools/arc-extract into
gamedata/mii_customizer/P5-MSG-PROBE/ (the coordinator's copy has sha256 starting
4b4f3d236400, 268096 bytes; confirm). Write a small reader (LBL1 + TXT2) and
report: label count, that `mnu_mmiif_setup_sp_move_title` and
`mnu_mmiif_setup_sp_move_width` exist with their texts, the control-code bytes
that occur inside texts of labels starting with `mnu_mmiif_` (list distinct
sequences, do not interpret), and whether any label starting with `mnu_mc_` exists
(expected: none). Check the archive index for per-language variants of this file
and list them.

Part 3 - staged probe, only if Part 1 gives a documented format. Build
  builds/0.2.1-msg-probe/mii_customizer_probe_msg/
containing: the message patch file at the path Part 1 establishes, defining ONE new
label `mnu_mc_probe_title` with the text `MC probe 0.2.1`; a copy of the special
actor chunk in which main.p14 K[2] is that new key; and an info.toml that parses
as TOML (check it with Python's tomllib). The new key is 18 characters and the
original 29, so this is a different-LENGTH chunk: build it with
`lua53_inspect.py setconst --allow-used`, and report size before/after, `verify`,
`compare` (exactly one structural difference) and `roundtrip`. Write
MANIFEST.json (paths, sizes, sha256, original hashes, "not installed, not tested
on hardware") and a check script with negative controls, like
builds/0.1.0-arc-probes/check_probes.py (read it; do not edit it). This folder
would replace the earlier Lua probe; say so in the manifest.
State what the probe can show: new label visible = added labels work AND a chunk
of different length loads; raw key or empty title = the chunk loaded but the label
did not resolve; unchanged title = chunk not loaded. Say which of these the probe
cannot tell apart.

If Part 1 finds no documented mechanism, do not stage anything; report what the
source shows and stop PARTIAL.

Exclusive writes: builds/0.2.1-msg-probe/, research/P5-MSG-PROBE.md,
evidence/P5-MSG-PROBE/, scratch/2026-10-05_P5-MSG-PROBE/, workspace-relative
gamedata/mii_customizer/P5-MSG-PROBE/.
