# P7-PRESET-ENGINE - premium: plugin 0.3.0, character stat presets per saved Mii

For Claude Opus 5.5 or GPT 6.1 Sol. Follow workspace AGENTS.md, this mod's AGENTS.md
and STATUS.md. No agents, commits, branches, emulator, SD access, framework-plugin
changes or edits to other workers' files. Do not install anything; the coordinator
packages and installs. All paths are relative to mods/mii_customizer/ unless marked
workspace-relative; create every folder inside mods/mii_customizer/. Use `python`.
Save the report and end with task ID, DONE/PARTIAL/BLOCKED, changed files and what
you could not verify.

Where we are (console, tier A): plugin 0.2.0 gives a saved Mii Gunner the weight
and walk speed listed for its saved-fighter ID in
sd:/ultimate/mii_customizer/loadouts.txt; identity (vtable 0x4f89490, kind 74,
entry id = slot index) and the hook at 0x4e53e0 work
(evidence/2026-10-05_gate2/RESULT.md). The user now wants a saved Mii to use "the
stats of character X". The in-game list UI is being researched separately and is
NOT part of this task. This task builds the engine the UI will later drive, and it
must be testable on the console now by editing the loadout file by hand.

Read first: evidence/2026-10-05_gate2/RESULT.md, research/P4-OVERRIDE-SLICE.md,
plugin/src/*.rs, plugin/README.md, prompts/P6-PRESET-DATA.md (the preset file
contract; that task runs in parallel and may not be finished),
research/P4-STAT-SITES.md section 3, research/COORDINATOR-2026-10-04.md (last
three sections).

Contracts (coordinator-owned; implement exactly, report any gap instead of
extending them).

A. Preset file `sd:/ultimate/mii_customizer/presets.txt`, read once at load, never
   written. Format `mc_presets 1`:
     line 1 exactly `mc_presets 1`
     `fighter <name> <kind_hash>`   starts a preset; name is [a-z0-9_]{1,31};
                                    kind_hash is `0x` + 10 hex digits
     `<field_hash> <decimal value>` field of the current preset; field_hash is
                                    `0x` + 10 hex digits; value finite f32
     `#` comments, blank lines, spaces or tabs between fields, `\n` or `\r\n`.
   Limits: file at most 512 KiB, at most 128 presets, at most 48 fields per preset,
   at most 48 DISTINCT field hashes over the whole file. Duplicate preset name or a
   field line before any `fighter` line: that line (or that whole preset, for a
   duplicate name) is rejected and logged. A bad first line, an unreadable or
   oversized file: no presets at all. Values are not range-limited (they are other
   fighters' real values) but must be finite. Fixed-size static storage; no heap
   beyond what std::fs needs to read the file.

B. Loadout file `sd:/ultimate/mii_customizer/loadouts.txt`. Accept first line
   `mc_loadouts 1` or `mc_loadouts 2`. Keys:
     `<id> preset <name>`            the Mii uses that preset (version 2 only)
     `<id> weight <v>` / `<id> walk_speed_max <v>`  as in 0.2.0, same ranges
   Resolution for a request with field hash h for the Mii with saved ID i:
   an explicit line for (i, h) wins; otherwise, if i has a preset and the preset
   has h, the preset value; otherwise the game's value. A `preset` line naming an
   unknown preset is rejected and logged, and that Mii has no preset. In a version
   1 file a `preset` line is an unknown key (rejected, logged). All other rules of
   0.2.0's parser stay (section 2.1 of research/P4-OVERRIDE-SLICE.md), except the
   size limit, which stays 16 KiB for this file.

C. Who gets it: unchanged from 0.2.0. Only a fighter that passes the pointer guard
   and `resolve` and whose kind is Mii Gunner, for a non-zero slot ID. Keep the
   list of accepted kinds as one constant array so more kinds can be added later.

D. Which requests: 0x4e53e0 with x2 == 0 and x1 equal to one of the field hashes
   that occur in the loaded preset file or in the two named keys. The hot path for
   every other hash must stay cheap and lock-free: no game call, no allocation, no
   file IO; a bounded search in a table built at load (state its cost in
   instructions or compares). Requests with x2 != 0 are passed through untouched
   and counted.

Also in this build:
- Remove the log-only hook on 0x4e53f0 (its question is answered). One hook site.
- Serialisation for later use by the UI: a pure function that turns the in-memory
  loadout state into file text (`mc_loadouts 2`, one `preset` line and any
  explicit lines per ID, stable order), with a host test that parse(serialise(x))
  == x, and a function `save_loadouts()` that writes that text to the loadout path
  (write a temporary file in the same folder, then replace; if this target cannot
  rename over an existing file, say what you did instead and why it is safe on
  power loss or why not). `save_loadouts()` must compile into the NRO but is NOT
  called from anywhere in 0.3.0. State that plainly; it is untested at runtime by
  design.
- Logging, bounded, same file and `mc|` style: L0 with both files' load results
  (counts of presets, distinct field hashes, rejected lines with line number and
  reason, first 32 each); one `mc|LO|` line per saved ID with its preset name and
  explicit keys; L3 reduced to the first line per (parent, field hash) for at most
  16 hashes per parent, with `p`, `kind`, `id`, `ov`, `orig`, `v`, `st`, and
  `src=explicit|preset|-`; `mc|OV|` once per (id, field hash); L4 and L5 as before,
  L5 with per-outcome counters plus `x2nz=` (requests with x2 != 0 for a known
  hash). No per-request logging beyond these bounds.

Checks and build: version 0.3.0, output builds/0.3.0-presets/ with MANIFEST.json.
Host unit tests for both parsers (every rule and limit above), the resolution
order, the hash table, serialise/parse round trip; a mutation control like
0.2.0's. If workspace-relative gamedata/mii_customizer/P6-PRESET-DATA/presets.txt
exists when you finish, run your host parser over it and report presets, fields,
rejects and size; if it does not exist, say so. Do not copy that file into the mod
tree. Write your own small synthetic preset file for tests (invented numbers,
clearly not game data) under scratch.
Deliver builds/0.3.0-presets/example/loadouts.txt: version 2, `0000f589 preset
<name>` with a placeholder name the coordinator replaces at install, and a comment
block explaining the format for a human editing it by hand.

Test plan for the coordinator (write it in the report, at most 10 user steps): the
user has two saved Gunners, A = 0000f589 and B = 0000f58b, two controllers. Propose
which two real fighters make good presets for a clearly visible and feelable
difference using only the ten fields weight, walk_speed_max, run_speed_max,
dash_speed, air_speed_x_stable, air_speed_y_stable, air_accel_y, air_accel_x_mul,
jump_y, jump_speed_x (for example one very fast light fighter and one slow heavy
one), what the user should try with each (run, jump height, fall speed, air
drift), one non-Mii control match, and which log lines prove that each field was
requested through the hook, overridden from the preset, and left alone for B and
for non-Mii fighters. Include how to tell from the log which of the ten fields
were NEVER requested through 0x4e53e0 with x2 == 0 during play, because that
decides which stats this mechanism can cover at all.

Not in scope: any UI, Lua, layout or message file; hooks other than 0x4e53e0;
integer parameters; other Mii classes; writing files at runtime; install scripts.

Exclusive writes: plugin/, build-plugin.sh, builds/0.3.0-presets/, builds/.cache/,
research/P7-PRESET-ENGINE.md, evidence/P7-PRESET-ENGINE/,
scratch/2026-10-05_P7-PRESET-ENGINE/.
