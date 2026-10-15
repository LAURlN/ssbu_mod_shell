# P4-OVERRIDE-SLICE - premium: plugin 0.2.0, per-saved-Mii stat override from a mod-owned file

For Claude Opus 5.5 or GPT 6.1 Sol. Follow workspace AGENTS.md, this mod's AGENTS.md
and STATUS.md. No agents, commits, branches, emulator, SD access, framework-plugin
changes or edits to other workers' files. Do not install anything; the coordinator
packages and installs. All paths are relative to mods/mii_customizer/ unless marked
workspace-relative; create every folder inside mods/mii_customizer/. Use `python`.
Save the report and end with task ID, DONE/PARTIAL/BLOCKED, changed files and what
you could not verify.

Goal: the first behaviour-changing build. One saved Mii Gunner gets different
weight and walk speed from another in the same match, taken from a file the mod
owns, keyed by the saved-fighter ID. Everything else stays vanilla. This is the
"persistence + retrieval + apply" half of the vertical slice; the in-game editor UI
comes later and is not part of this task.

Read first: evidence/2026-10-04_gate1/RESULT.md and RESULT_test2.md (console, tier
A), research/P3-DIAG-PLUGIN.md, plugin/src/lib.rs and logic.rs, plugin/README.md,
research/P2-STAT-HOOKPOINT.md section 2.6, research/COORDINATOR-2026-10-04.md (last
three sections). For bindings: mods/ssbu_mod_new/AGENTS.md, projects/pgwr/STATUS.md,
handbook/00_INDEX.md, handbook/11_smashline_skyline.md and
src/pgwr/plugin/Cargo.toml + Cargo.lock (read-only reference; copy no source).

Console facts (A): the three hook sites and the 4-word far hook work; 0x4e53e0 is
called with x1 = weight (0x0607cd5541) or walk_speed_max (0x0ee2ec2860), x2 = 0,
repeatedly per fighter, from the main module and from another module; [x0+8]
(parent) differs per fighter; saved-Mii ID and special bytes are in
T+0xe58+p*0x240 and T+0xa2+p*0x1c8 (T = 0x5307760) for local players 0 and 1 when
the fighters are created; a non-Mii match shows zero slots.
Offline facts (B): objects with vtable 0x4f89490 are built with [obj+8] = parent
and stored at [parent+0x50] (0x688508-0x688584); the exported wrappers of the form
`ldr x0,[x0,#0x50]` take a `BattleObjectModuleAccessor*` (mangled names). A second
vtable 0x4f73738 shares the slot functions; for it [x0+8] is not shown to be a
parent.
Open: which parent is which player. This task must close it.

Loadout file, version 1 (coordinator contract; implement exactly, do not extend):
  path  sd:/ultimate/mii_customizer/loadouts.txt   (read only, never written)
  line 1 must be exactly `mc_loadouts 1`
  other lines: `<id: 8 hex digits> <key> <decimal value>`; `#` starts a comment;
  blank lines allowed; fields separated by spaces or tabs.
  keys: `weight` (absolute value replacing the original) and `walk_speed_max`
  (absolute value). Accepted ranges, as PROPOSALS for this test, not declared safe:
  weight 60.0..140.0, walk_speed_max 0.5..2.0. Finite numbers only.
  ID 00000000 is invalid. At most 32 distinct IDs. A later line for the same
  id+key replaces an earlier one.
  Any violation (missing/other version line, bad id, unknown key, out of range,
  too many ids, non-UTF-8, file larger than 16 KiB): that LINE is ignored and
  logged with its line number; a bad first line or unreadable file disables all
  overrides. No file = no overrides, logged once. The file is read once at plugin
  load. No unwrap/panic anywhere; fixed-size storage.

Deciding whether to override a request (all conditions required, otherwise return
the original value untouched):
 1. hash is one of the two; x0 != 0; `[x0] == base + 0x4f89490`;
    parent = [x0+8] != 0 and `[parent+0x50] == x0`.
 2. the parent is a fighter of kind Mii Gunner, and its player/entry index p is
    0..7. Obtain kind, category and entry id ONLY through exported game functions
    declared by a pinned binding crate, called with `parent` as the module
    accessor. The old plugin's dependency `skyline_smash` (rev 315e4e8...) is the
    intended source; add it the way that crate's Cargo.toml documents so the build
    has a single `skyline` (read its comments about the bare-URL collision). State
    exactly which functions and constants you use and where they are declared. If
    the entry id cannot be obtained that way, stop PARTIAL; do not guess offsets.
 3. the slot ID at T+0xe58+p*0x240 is non-zero and has a loadout entry for this key.
Unknown identity, missing entry, bad file: vanilla value. Recompute per request or
cache per parent, but a cache must not survive the parent being destroyed and its
address reused by another fighter; say how you guarantee that, or do not cache.
Never call back into 0x4e53e0's own path from inside the decision in a way that
can recurse without bound; if the binding functions you call can re-enter the
hook, add a per-thread or atomic re-entry guard that falls through to vanilla.

Logging (same file and style as 0.1.0, `mc|` lines, bounded): L0 as before plus
the file load result (version line ok, entries accepted, each rejected line with
reason). L3 lines gain `p=<player>|kind=<kind>|id=<slot id>|ov=<0/1>|orig=<orig>`;
keep the first 4 per hash per parent. One `mc|OV|` line the first time an override
is applied for each (id, key). Keep L4/L5; drop L1 and L2 hooks entirely (their
questions are answered) unless you need them.
Add one log-only hook: 0x4e53f0 (slot +0x278, D: set_customize_no; four words
`ldr x0,[x0,#0x38]; ldr x8,[x0]; ldr x3,[x8,#0x38]; br x3`, verify them and apply
the same word check). Log `mc|L6|` with x0, [x0+8] under the same vtable guard,
w1, w2 and module-relative return address, first 64 events. Purpose: learn when
and with what values the engine applies special choices. It must not change
anything.

Build: version 0.2.0, output builds/0.2.0-override/ with MANIFEST.json (hashes,
dependency revisions, hook table, "not installed, not tested on hardware"), same
build script and target dir. Host unit tests for the parser (every rejection
rule, ranges, replacement, limits) and the decision logic as far as it is pure.
Binary/source checks as in 0.1.0. Also deliver
builds/0.2.0-override/example/loadouts.txt for the two IDs seen on the console:
0000f589 with weight 130.0 and walk_speed_max 1.6; 0000f58b absent (vanilla
control inside the same match).

For the coordinator's test plan, write: at most 10 user steps (control match with
non-Mii fighters; match A=P1 vs B=P2; same match with ports swapped; one match
with the file removed or renamed as the no-override control if you judge it needed)
and what the user should see and feel (walk speed is visible; weight needs a
knockback comparison - propose one simple, repeatable way). List which log lines
prove: correct player mapping, override applied only to ID f589 regardless of
port, vanilla for the other Gunner and for non-Mii fighters, and what each failure
pattern would mean.

Not in scope: UI, Lua or layout changes, writing files, more stats, move changes,
install scripts, the framework plugins.

Exclusive writes: plugin/, build-plugin.sh, builds/0.2.0-override/, builds/.cache/,
research/P4-OVERRIDE-SLICE.md, evidence/P4-OVERRIDE-SLICE/,
scratch/2026-10-04_P4-OVERRIDE-SLICE/.
