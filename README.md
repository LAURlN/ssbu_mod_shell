# Building Smash Ultimate mods with AI coding agents

This is a working copy of my Super Smash Bros. Ultimate (Switch, game version 13.0.4) modding workspace.
It contains two mods: Skyline plugins in Rust, with Python asset and audit pipelines. AI coding agents
wrote nearly all of the code and documents: Claude Opus 5.5, GPT 6.1 Sol and GPT 6 Luna, Codex, and
Freebuff "Space Bunny Alpha" workers. My part was directing the work. I wrote the rules the agents follow,
split the work into bounded tasks with prompts, picked which model got which task, reviewed the results,
and ran every test on my own console. The interesting part is the process: rules that each cite the
failure that produced them, a coordinator/worker setup, evidence tiers, and a graveyard of retracted
claims.

What it achieved, split by evidence. Tier A means confirmed on my console:
- **Mii Customizer**: a mod menu inside the game's own Mii maker. It gives each saved Mii Gunner the stats of
  any of 94 fighters, plus borrowed moves. Confirmed on console: per-Mii stat presets, the menu drawn on the
  native list screen, saving and reloading, and Mii Brawler's forward tilt on one Gunner while a second Gunner
  in the same match stays vanilla. More moves are integrated and pass the offline checks, but have never run.
- **Pyra/Mythra → Mr. Game & Watch reskin with borrowed moves** (`pgwr`). Several moves are confirmed on
  console (Monkey Flip grab, G&W up-B, Chrom jab, Cloud forward air sword). Many later ports are built and
  audited only. Each status file below says which is which.

## Start with these five files (about 5 minutes)

1. [`AGENTS.md`](AGENTS.md): workspace rules that every agent reads first. Scope, where knowledge goes,
   hard rules (no publishing, never touch the dump, the user installs).
2. [`mods/ssbu_mod_new/AGENTS.md`](mods/ssbu_mod_new/AGENTS.md): the stricter mod rules. Evidence tiers
   A-D, "control before claim", "a worse result is a revert", one change per hardware test. Each rule names
   the failure it came from.
3. [`mods/ssbu_mod_new/handbook/graveyard.md`](mods/ssbu_mod_new/handbook/graveyard.md): confident
   agent claims that turned out wrong, each with who claimed it and the evidence that refuted it.
4. [`mods/mii_customizer/HANDOFF.md`](mods/mii_customizer/HANDOFF.md): how the coordinator/worker setup
   runs in practice. Who does what, observed strengths and weaknesses of each model, review routine.
5. [`mods/mii_customizer/evidence/2026-10-07_session4/RESULT_boot1.md`](mods/mii_customizer/evidence/2026-10-07_session4/RESULT_boot1.md):
   one console test report. A startup crash is traced to a 324 KiB stack frame with an offline tool,
   fixed, and turned into a standing check.

If you have more time: the task table in [`mods/mii_customizer/STATUS.md`](mods/mii_customizer/STATUS.md);
a worker prompt, [`mods/mii_customizer/prompts/MOVE-TEMPLATE.md`](mods/mii_customizer/prompts/MOVE-TEMPLATE.md);
the coordinator's review log, [`mods/mii_customizer/research/COORDINATOR-2026-10-04.md`](mods/mii_customizer/research/COORDINATOR-2026-10-04.md);
and the post-mortem that produced the rules, [`mods/ssbu_mod_new/projects/_workspace_migration/PLAN.md`](mods/ssbu_mod_new/projects/_workspace_migration/PLAN.md).

## How the agent workflow works

- **Rules first.** The first workspace was about 20 GB of agent output: competing "read this first"
  documents, append-only narratives that contradicted themselves, and at least eight confident claims
  that were later retracted. The migration plan diagnoses why. The rule files target those causes: one place
  per fact, dated scratch, no absolute paths, retractions edited in place, short status files instead of
  handoff essays.
- **Coordinator and workers.** One chat (the coordinator) scopes bounded tasks and writes a prompt for each,
  with allowed write paths, deliverables and a self-check. I start the workers by hand. At most three
  Freebuff "Space Bunny Alpha" workers run in parallel, on exclusive paths. Every worker writes a report to
  `research/<task>.md` and a check script to `evidence/<task>/`. The coordinator reruns each check, re-reads
  the key evidence, puts corrections in a banner at the top of the report, and only then integrates the
  result and updates `STATUS.md`. Every prompt is kept in `prompts/`.
- **Premium models used sparingly.** Claude Opus 5.5 and GPT 6.1 Sol get only native reverse engineering,
  plugin architecture and hard debugging, through a focused escalation brief. Long offline fact-finding goes
  to the cheaper workers. The handoff records where that worked and where it did not (workers that stopped
  without a report, partial native RE).
- **Evidence tiers.** A = my console (a log or crash report, tested against a vanilla control);
  B = measured offline by a script in the repo; C = read from a pinned third-party source (URL + commit);
  D = hypothesis, written as one together with the experiment that would settle it. "Compiles", "byte-equal"
  and "is installed" are never phrased as "works". Emulator runs count as B, never A.
- **Graveyard.** When a claim turns out wrong, it is corrected where it stands and logged in
  `graveyard.md` with the refuting evidence, so later agents do not re-derive it.
- **Hardware gates.** Agents never install to the SD card on their own initiative. A designated installer
  assembles READY packages listed in `CURRENT_INSTALL.md` (hashes, test steps, expected log lines, rollback).
  I run the numbered test and report back, and the result is filed as an immutable `RESULT.md`.

## Layout

| path | what |
|---|---|
| `AGENTS.md`, `kb/`, `tools/` | workspace rules, environment knowledge base (playbooks, findings), shared tools (data.arc extraction, Freebuff dispatch) |
| `mods/ssbu_mod_new/` | the first mod: `AGENTS.md`, `handbook/` (+ `graveyard.md`, `facts/facts.yaml`), `projects/*/STATUS.md`, `evidence/` (console reports, install records), `tools/` (105 audit/build scripts), `src/` (plugin and pipeline source; see the limitations below) |
| `mods/mii_customizer/` | the second mod: `AGENTS.md`, `STATUS.md`, `HANDOFF.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md`, `prompts/` (66), `research/` (70 reports), `evidence/`, `plugin/src/`, `moves/`, `tools/`, referenced check scripts under `scratch/` |
| `dump/`, `gamedata/` | empty placeholders for your own game dump and its extractions |
| [`MANIFEST.md`](MANIFEST.md), [`NEEDS_DECISION.md`](NEEDS_DECISION.md) | what was copied, left out or edited, and the borderline cases |

## Resuming work with a fresh dump

The layout matches the original workspace, so the relative paths in every document still resolve. To work
again you need your own legally made dump and keys. Nothing from the game is included.

1. Put the nxdumptool dump (base and update NSP) under `dump/`. Read
   [`kb/playbooks/extracting-data-arc-offline.md`](kb/playbooks/extracting-data-arc-offline.md).
   `tools/data-arc-extract` needs `LibHac.dll` 0.19.0 at `Ryujinx/build/`. The `Ryujinx/` tree is not
   included; `tools/data-arc-extract/backend.lock.json` names the official NuGet package and the hashes to
   check it against.
2. Build `tools/arc-extract` (`cargo build --release`) and pull single files into `gamedata/`
   ([playbook](kb/playbooks/extracting-single-files-from-data-arc.md)).
3. In `mods/ssbu_mod_new/`, copy `paths.example.toml` to `paths.toml` and recreate `dumps/` as described in
   [`mods/ssbu_mod_new/dumps/INDEX.md`](mods/ssbu_mod_new/dumps/INDEX.md).
4. Restore what was left out, before building plugins:
   generated code (rerun the generators listed in [`MANIFEST.md`](MANIFEST.md#game-derived-source-files-left-out)),
   pinned donor material in `refs/` (each folder keeps its `SOURCE.json` with URL, commit and sha256), and the
   vendored crates (Smashline fork, Clone Engine). The cargo git dependencies are fetched by cargo.
5. The toolchain is listed in [`kb/reference/local-machine.md`](kb/reference/local-machine.md) and
   [`kb/reference/cargo-skyline.md`](kb/reference/cargo-skyline.md).

## Honest limitations

- **This copy does not build as it stands.** The move code that was ported or generated from the game's own
  scripts and code is left out on purpose: about 100 Rust and assembly files across the two mods (all
  listed in the manifest). About a third have a generator in the repo. The hand ports would have to be re-ported by agents.
  The Mii Customizer plugin also lacks `moves.rs`, which mixes my dispatcher with ported ACMD.
- **Most features are tier B or D.** Only the items named above as console-confirmed are tier A. Many later
  `pgwr` moves and Mii Customizer 0.9.0+ were built and checked offline but never run.
- **The documents are agent-written and long.** Some files break their own rules (for example
  `mods/mii_customizer/STATUS.md` far exceeds the ~150-line status limit), and some reports are partial
  or unreviewed. The status tables say so instead of hiding it.
- **Review is not complete.** The coordinator reruns check scripts and re-reads key evidence, but does not
  re-derive every claim. The tables mark where a check was not rerun.
- No history: the Mii Customizer was never a git repo, and the mod repo's history is not part of this
  export. No CI, and no automated runtime tests. Runtime behaviour is only ever confirmed on one console by
  one person.
- Raw console logs and crash reports are left out. The `RESULT.md` files quote the relevant lines.
