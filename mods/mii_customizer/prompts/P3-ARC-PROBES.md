# P3-ARC-PROBES - stage two file-override probes as separate mod folders

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Report exact inputs/hashes, commands, observed
checks, failures and limits. B is offline observation, C pinned source, D
hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create every
folder INSIDE mods/mii_customizer/ (game-derived work files go in workspace-relative
gamedata/mii_customizer/P3-ARC-PROBES/). Use `python`, not `python3`.

One goal: produce two small, separately toggleable ARCropolis mod folders that a
later console test can use to see whether the game loads (1) a changed editor
layout and (2) a changed editor Lua chunk. Staging only: nothing is installed,
nothing is marked READY, and you do not ask the user to test.

Read first: research/P2-LAYOUT-PATCH.md, research/P2-UI-FLOW.md sections 4 (rows
10, 16, 17) and 9, research/P2-LUA-EDIT.md section 3, tools/lua53-inspect/README.md,
workspace-relative kb/reference/ssbu-modding-stack.md. Then, after reading
mods/ssbu_mod_new/AGENTS.md, projects/pgwr/STATUS.md and handbook/00_INDEX.md, read
the handbook page(s) the index names for ARCropolis mod folders / file overrides,
to learn the folder layout, any required metadata file (for example info.toml) and
anything recorded about file-size or hash requirements. Quote what you rely on
with its tier. Read-only there; copy no files from that repo.

Probe A - layout. Use the already built and reviewed archive, workspace-relative
gamedata/mii_customizer/P2-LAYOUT-PATCH/patched/layout_row00_scale075.arc, sha256
86044f63d4bb4456d906c8d896a4c53ed80c20a298f97bb528fffc3708f55877 (verify; if it
differs, regenerate with tools/layout-diagnostic/build_diagnostic.py and report).
ARC path: ui/layout/menu/make_mii_special/make_mii_special/layout.arc.

Probe B - Lua. Do NOT use the existing `MCUZ_DIAGNOSTIC_TITLE_XXXXXXX` probe: an
unknown message key has unknown behaviour. Build a new same-length probe from the
original workspace-relative
gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc
(sha256 ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d):
replace the string constant `mnu_mmiif_setup_sp_move_title` (main.p14 K[2], the
argument of ComFrameActor.set_sub_title) with `mnu_mmiif_setup_sp_move_width`, a key
of the same length that this same chunk already uses as a text label (main.p2
K[7]). Use `lua53_inspect.py setconst --allow-used`. Verify: file size unchanged
(7799), `verify` exit 0, `compare` shows exactly one structural difference
(main.p14.K[2]), `roundtrip` byte-identical, the differing bytes are contiguous and
inside that one string, and every other constant and instruction is unchanged.
Check with the tool that both keys are 29 characters; do not trust this prompt.
Confirm from the local archive index that no `ui/script_patch/...` version of
make_mii_special_actor.lc exists (research/P2-UI-FLOW.md section 6 says none
does; re-check with tools/arc-extract or the existing extraction listing and report
how you checked). ARC path: ui/script/menu/chara_make/make_mii_special_actor.lc.
The intended visible sign, unverified: the special-move screen's sub-title shows
the side-special label text instead of its normal title.

Staging. Create
  builds/0.1.0-arc-probes/mii_customizer_probe_layout/<ARC path of probe A>
  builds/0.1.0-arc-probes/mii_customizer_probe_lua/<ARC path of probe B>
each with whatever metadata file the handbook says a mod folder needs (minimal,
with a display name and version 0.1.0) and nothing else. One
builds/0.1.0-arc-probes/MANIFEST.json listing for every file: relative path, size,
sha256, the original file's sha256 and size, and the exact byte offsets that differ
from the original. Add a check script that re-derives the manifest from the staged
files and the originals and exits nonzero on any mismatch, including an unexpected
extra file. State in the manifest: "not installed, not tested on hardware".

Do not: build an install script, write outside the paths below, touch the plugin
crate, combine both probes in one folder, change any other game file, or claim that
either probe is visible or loads. If the handbook gives no usable description of
the mod folder layout, stop PARTIAL with what you found instead of guessing.

Deliver research/P3-ARC-PROBES.md: hashes, commands with exit codes, the handbook
lines relied on, limits, and for each probe one sentence on what the user would
look at and what "no visible change" would and would not mean.

Exclusive writes: builds/0.1.0-arc-probes/, research/P3-ARC-PROBES.md,
evidence/P3-ARC-PROBES/, scratch/2026-10-04_P3-ARC-PROBES/, workspace-relative
gamedata/mii_customizer/P3-ARC-PROBES/.
