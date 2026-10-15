# P3-DIAG-PLUGIN - premium: log-only diagnostic plugin for the first console gate

For Claude Opus 5.5 or GPT 6.1 Sol. Follow workspace AGENTS.md, this mod's
AGENTS.md and STATUS.md. No agents, commits, branches, emulator, SD access,
framework-plugin changes or edits to other workers' files. Do not install anything
and do not mark anything READY; the coordinator packages and writes the test plan.
All paths are relative to mods/mii_customizer/ unless marked workspace-relative;
create every folder inside mods/mii_customizer/. Use `python`, not `python3`.
Save the report and end with task ID, DONE/PARTIAL/BLOCKED, changed files and what
you could not verify.

Goal: extend the mod's own plugin crate (plugin/, built by build-plugin.sh, see
research/P2-PLUGIN-SCAFFOLD.md) into version 0.1.0, a LOG-ONLY diagnostic that one
console session can use to settle three runtime questions. It must not change game
behaviour. A crash or hang costs the user a console session, so prefer logging
less over reading more.

Read first: research/P2-MATCH-READER.md, research/P2-STAT-HOOKPOINT.md section 2.6,
research/P2-STAT-READS.md section 3, research/COORDINATOR-2026-10-04.md (last two
sections). Then mods/ssbu_mod_new/AGENTS.md, its projects/pgwr/STATUS.md,
handbook/00_INDEX.md and handbook/11_smashline_skyline.md (read-only reference; copy
no source files, change nothing there).

Image: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613, flat, address ==
file offset. Disassembler scripts: copy from scratch/2026-10-04_P2-MATCH-READER/.

Offline facts the hooks rest on (B, instructions re-read by the coordinator):
- 0x4e53e0 is slot +0x270 of vtable 0x4f89490: `ldr x0,[x0,#0x38]; ldr x8,[x0];
  ldr x3,[x8,#0x30]; br x3`. It passes x1/x2 through untouched. The object with that
  vtable is 0x98 bytes, built at 0x688508-0x68852c with `stp vtable, x19, [obj]`
  (so [obj+8] = the parent), and stored at [parent+0x50] (0x688584). Engine sites
  call `[[parent+0x50]]+0x270` with the param hash in x1 and x2 = 0
  (0x2db55b8-0x2db55d8). 0x4e53d0 (slot +0x268, the one the exported lua_bind
  wrapper 0x208de50 uses) just re-dispatches slot +0x270. A second vtable 0x4f73738
  shares these slot functions. D: parent is the fighter's module accessor and this
  is the float-param getter.
- 0x179e440(x0 = T, w1 = player, x2 = local struct) stores record content into the
  per-player entry; T = 0x5307760. Saved-fighter u32 ID per player at
  T + 0xe58 + p*0x240 (player 0: 0x53085b8), special bytes at T + 0xa2 + p*0x1c8
  (player 0: 0x5307802), p in 0..7. Both lie beyond the end of the file (bss).
- 0x17c8210(x0 = manager, w1 = id, x2 = out) loads a saved-fighter record.
- Hashes: weight 0x0607cd5541, walk_speed_max 0x0ee2ec2860.

Step 0 - prerequisites, offline, before writing code.
a) Offset convention: show that a file offset in this image equals the offset
   `#[skyline::hook(offset = ...)]` expects, by taking one raw-offset hook or patch
   that the old mod's handbook or evidence records as working on the console
   (tier A there) and checking the instruction bytes at that file offset match what
   that hook assumes. Cite the handbook line. If no tier-A raw offset exists, say so;
   then the first log lines of this plugin must make the convention checkable (see
   L0 below).
b) For each hook address confirm it is a function entry and record the first four
   instruction words; the plugin must compare those words at load time and skip the
   hook (logging why) when they differ.
c) Decide inline hook versus replace hook per site from what the pinned skyline
   revision supports safely for a 4-instruction tail-call thunk (0x4e53e0 has no
   prologue and ends in `br x3`). If hooking the thunk itself is unsafe, say why and
   pick the nearest safe point with the same arguments, with addresses.

Step 1 - the plugin (version 0.1.0). Log lines go to
sd:/ultimate/mii_customizer_log.txt (append, errors ignored, as in the scaffold)
and are flushed per line. Every line starts with `mc|`. Required events:
L0  load: version, and for each hook `site, expected words, found words, installed
    yes/no`. Also the module base and the runtime addresses the statics resolve to.
L1  entry of 0x179e440: player, return address (module-relative), then AFTER the
    original returns: the u32 at T+0xe58+p*0x240 and the four bytes at
    T+0xa2+p*0x1c8 for that player. First 64 events, then count only.
L2  entry of 0x17c8210: id, module-relative return address. First 64 events whose
    return address is outside 0x19d0950..0x19dc304, then count only.
L3  0x4e53e0 (or the point chosen in Step 0c), only when x1 is one of the two
    hashes: x0, [x0+8] (the parent), x2, module-relative return address, and the
    returned f32. Per distinct parent pointer log the first 4 events per hash; keep
    at most 32 distinct parents; keep total counters per hash. No heap allocation,
    locks or file IO on calls for other hashes: one compare and out.
L4  snapshot: when L3 sees a parent pointer it has not seen before, log all eight
    (ID, four special bytes) pairs from the two static tables, once per new parent.
L5  a totals line (calls per hash, distinct parents, L1/L2 counts) whenever L4
    fires and at most once per ~600 L3 hits otherwise.
Use only fixed-size static storage and atomics. No threads. Never unwrap, never
panic, never hold a lock across the original call. The only pointer reads allowed
are the ones listed above; do not walk any other structure. If you want the
player/entry id of a parent, you may get it only through an exported game function
resolved by symbol that the pinned bindings already declare (state which); if that
needs a new dependency or any guess, leave it out and say so.

Optional variant, only if the entry id is obtained by such a proven call: a second
NRO `0.1.0-override` identical to the first except that L3 returns the original
value multiplied by 1.5 for walk_speed_max when the parent's entry id is 0, logged
on each of the first 4 uses. Separate build output, separate manifest, off unless
the user installs that file. If the condition is not met, do not build it.

Step 2 - build and offline checks. Build with build-plugin.sh (adapt it for the
version/variant; target dir stays builds/.cache/plugin-target/). Outputs to
builds/0.1.0-diag/ (and builds/0.1.0-override/ if built) with MANIFEST.json: NRO
sha256, size, crate version, dependency revisions, build command, hook table,
"not installed, not tested on hardware". Report: build exit codes, that the hook
offsets and expected words appear in the binary, and a host-side unit test or
script for any pure logic you wrote (counters, dedupe table, line formatting).

Step 3 - for the coordinator's test plan, write in the report: what the user should
do in the game in at most 10 steps to exercise L1-L4 (vanilla fighters control, then
two differently configured saved Mii Gunners as P1 and P2, one match, then the same
after reopening the Mii editor once), which log lines decide which question, what
each possible outcome means, and what a hang or crash at each stage would implicate.
Questions to decide: (1) are the per-player ID slots correct for P1/P2 when a match
starts, and which writer filled them; (2) do weight / walk_speed_max requests reach
0x4e53e0, how often per fighter, and does the parent pointer separate the two
Gunners; (3) is the offset convention right (L0).

Not in scope: any override beyond the optional variant, UI or asset changes, config
or save files, install scripts, touching framework plugins, emulator runs.

Exclusive writes: plugin/, build-plugin.sh, builds/0.1.0-diag/,
builds/0.1.0-override/, builds/.cache/, research/P3-DIAG-PLUGIN.md,
evidence/P3-DIAG-PLUGIN/, scratch/2026-10-04_P3-DIAG-PLUGIN/.
