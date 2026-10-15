# Cleanup plan for modpack_test_1 -> modpack_test_2

Written 2026-09-29 after a read-only survey of `modpack_test_1`. Nothing in
`modpack_test_1` was edited (agents are working there); everything written is in this folder.
`APPENDIX_doc_listing.txt` is the raw listing of every note/log/json found (393 entries), kept as an appendix.

Companion documents in this folder:

- `KNOWLEDGE_TRIAGE.md`  what the agents claimed, sorted into confirmed / open / refuted, with sources
- `AGENT_RULES.md`       draft rules file for every future agent (goes in `AGENTS.md` / `CLAUDE.md`)
- `SOURCE_MAP.md`        every folder in modpack_test_1 and where it goes

---

## 1. What is actually in there (the short version)

~20 GB, ~170k files, no git commits (28 untracked entries, `main` has zero commits).
About 95% of the file count is not yours or not work: 77k files of dumped scripts,
25k files of game export, Ghidra (unpacked), cargo `target/` dirs, and copies.

| Kind | Where | Note |
| --- | --- | --- |
| The live project | `mod_files/pyra_gamewatch_reskin` | 0.14.0, Pyra c06/c07 = G&W. Keep, is the base of the new workspace |
| Finished-ish project A | `mod_files/mythra_gamewatch_swap` | hook-based Mythra<->G&W swap. Moves work, Monkey Flip grab never did |
| Finished-ish project B | `mod_files/mgw_standalone` | Clone Engine. G&W clone works, Mythra clone never stopped crashing (p1-p16) |
| Parked project C | `pyra_mythra_clone` (3 GB) | full-copy clone attempt + trace recorder. Loader passed, no playable clone |
| Game dumps | `export/` (4.2 GB, partial, 98 fighters), ExeFS `main` (x5 copies), `SSBU-Dumped-Scripts-main/` | the valuable inputs |
| Research | `references/`, `scratch/`, `reports/` | mixed: some gold (decoded tables, ghidra scripts), lots of one-off probes |
| Shipping trees / backups | `mod_output*`, `mod_backup_2`, `sd_backups`, `sd-backup-*` (x9 inside pgwr), `mod_files/*/backups` | 8+ overlapping copies of the same SD tree |
| Other mods used as reference | `George v3.0…`, `ssbuGeorgeMoveset-main`, `chrom_c07_ftilt`, `skins_to_use`, `skyline-rs-template…` | not yours to maintain |
| Agent litter | 3 rule files, 6+ HANDOFF/REPORT/DIAGNOSIS docs per project, `01a0a728-…` (a Gemini/Antigravity task dump), `.freebuff` | contradict each other, see triage |

Disk: **C: has 15.4 GB free of 475 GB**, and it already hit 0 once (2026-09-28).
Consequence for the plan: *move within the volume, do not copy*. A same-volume move
costs no space and is instant; copying the 4.2 GB export plus everything else
would nearly fill the drive. Dedupe before/while moving.

## 2. Why it became a mess (so the rules can target the causes)

1. **Every agent started a new top-level folder** (`pyra_mythra_clone`, `mythra_gamewatch_swap`
   at root *and* in mod_files, `mod_output_pair`, `mod_backup_2`…) instead of extending one.
2. **Knowledge lives in append-only narratives** (a 110 KB "guide" whose lessons log
   contradicts itself, DIAGNOSIS.md at 65 KB, HANDOFFs that say "read this first" in 4 places).
   Nothing is ever marked wrong in place, only "corrected" further down.
3. **Claims were never separated from evidence.** Offline compile + byte compare got written as
   "does work"; later a console log disagreed. At least 8 confident claims were retracted (see triage).
4. **Hand-installed / hand-copied deliverables and self-made backups** at every step, all kept forever.
5. **Paths are absolute and per machine** (`user-specific paths`, `ArcExplorer export directory`, `<user>`).
6. **Scratch is the real workspace.** ~150 one-off `.py` probes in `scratch/`; a few (hash search,
   xref, maindesc, constmap) are genuinely useful tools that live nowhere else.
7. **Hazards left armed:** `install-to-card.sh` still installs the *patched global smashline* by
   default although that whole approach was retracted (see triage R-1). The next agent that runs the
   documented command will overwrite the good plugin on the card.

## 3. Target layout of modpack_test_2

Principle: one thing, one place; knowledge is organized by *topic* (how to do X), history by *project*
and by *date*, and raw data is read-only and separate from anything an agent edits.

```
modpack_test_2/
  AGENTS.md              rules (from AGENT_RULES.md); CLAUDE.md is a 1-line pointer to it
  README.md              30-line map: where things are, how to start
  paths.toml             the only place with machine paths (SD drive, dump root, toolchains)

  handbook/              THE GOAL: everything needed to copy/edit moves and characters
    00_INDEX.md          decision tree: "I want to ... -> read ..."
    01_pipeline_overview.md      tiers (ACMD-only / new motions / new statuses / new geometry / new articles)
    02_toolchain_build_deploy.md msys2, cargo-skyline 3.5.0, py312, deploy verification, SD install
    03_dumps_and_sources.md      what is dumped, how to dump more (arc-network), which repo for what
    04_motion_lists_and_animation.md  motion_list.bin format, retargeting, aliasing, timing tails
    05_acmd_porting.md           dump->Rust conversion rules (R1-R26), known dump artifacts
    06_statuses_and_kinetics.md  custom statuses, id allocation, Pre/Main, TERM+ids, pitfalls
    07_articles_and_projectiles.md  clone_weapon, registry, config.json, per-slot files, breath/normal_weapon
    08_models_visibility_skeleton.md  visibility tables (lowercase hashes!), bone injection, meshes
    09_params_prc.md             vl.prc, expression_vl.prc, param objects, extraction with provenance
    10_arcropolis_config_json.md new-dir-files vs new-dir-infos, costume groups, failure signatures
    11_smashline_skyline_api.md  LookupSymbol, gating with set_costume, what does not exist in the bindings
    12_native_main_13.0.4.md     offsets, tables, ExeFS/main.bin facts, how to xref, Ghidra sizing
    13_swap_and_pairs.md         Element pair table, handoff offsets, hook list, Mythra/Pyra/G&W ids
    14_clone_engine.md           standalone clone lessons p1-p16, smashline 1.6.8 offset errors
    15_grabs_catch.md            Monkey Flip investigation, what is eliminated, next experiment
    16_crash_and_log_reading.md  Atmosphere report reading, how to map PCs, log prefixes
    17_hardware_test_protocol.md how a console test is specified and its result recorded
    facts/               one small file per fact family: facts.yaml (id, claim, tier, evidence, date, status)
    graveyard.md         retracted/refuted claims with why (so nobody re-derives them)

  projects/              per-project state, short, current only
    pgwr/                STATUS.md (feature matrix), CHANGELOG.md, TODO.md, tests/ (dated console results)
    mgw_swap/            same shape, status FROZEN
    mgw_standalone/      same shape, status FROZEN (Mythra clone unsolved)
    pmclone/             status PARKED

  src/                   code that builds: pgwr/ (plugin/, build.py, tools/), mgw_swap/, mgw_standalone/, pmclone/
  tools/                 shared, curated, documented scripts (see section 6)
  dumps/                 READ-ONLY game data, mirrors ARC paths (see section 5)
  refs/                  pinned donor material per move (diddy_monkey_flip/, mii_hero_spin/, …) + third-party repos
  builds/                per project, per version: NRO + mod tree hash manifest. Keep last 3 + last-known-good
  evidence/              crash reports and logs, dated, one folder per console run, each with a RESULT.md
  archive/               cold storage (old backups, staging, Space-Bunny-era snapshots), nothing here is read by agents
  scratch/               gitignored, per agent per date: scratch/2026-09-30_agentname/; deleted after 30 days
```

Rules that fall out of this layout: agents never create top-level folders; `handbook/` is the
only place for durable knowledge; `projects/*/STATUS.md` is the only place for "what works now".

## 4. Execution phases (nothing before phase 0 completes)

**Phase 0 - freeze and snapshot (you + agents).** Wait until pgwr agents stop; `git init` is *already*
there with no commits. Make one commit of `mod_files/pyra_gamewatch_reskin` source only (with a
strict `.gitignore`: `target*`, `export`, `*.nro`, `sd-backup*`, `__pycache__`, `scratch`). This gives
history without disk cost. Record hashes of the NRO on the card as last-known-good.

**Phase 1 - dumps (biggest win, safest).** Create `dumps/` (section 5), *move* `export/`, the
ExeFS, `SSBU-Dumped-Scripts-main`, motion-list/param label files, prebuilt NROs, decoded tables
(`main_symbols.json`, article table, etc.). Write `dumps/INDEX.md` + `manifest.sha256` (hash-once).
Leave a `paths.toml` that both trees can read so old agents keep working via env var
`MGW_EXPORT` (already honoured by the swap tools). Delete the 4 duplicate ExeFS images after
hash-verifying (two copies of the `main` NSO: UPD dump + `pyra_mythra_clone/reference/dumps/exefs`; two copies of the
86 MB flat image: `pyra_mythra_clone/reference/dumps/images/main.bin` and `references/mythra_gamewatch_feasibility/main_memory.bin`).

**Phase 2 - handbook (the actual goal).** Write the 17 topic files from `KNOWLEDGE_TRIAGE.md`.
Each fact enters `facts.yaml` only with tier + evidence pointer. Anything below tier B goes into the
file under "Unverified" or is dropped. This is the real work (~1-2 agent sessions); the triage
already lists what to carry over and what to drop.

**Phase 3 - tools.** Promote useful scripts from `scratch/`, `references/*/`, `mod_files/*/tools`
into `tools/` with a one-line docstring and a smoke test; leave the rest in `archive/scratch_old/`.
Candidate list in section 6.

**Phase 4 - projects.** Move pgwr in as `src/pgwr` (drop `target*`, `__pycache__`, 9 sd-backup dirs,
crash-reports -> `evidence/`). Move swap and standalone as frozen (drop `target`, `staging` p1-p15,
keep `evidence/`+`latest_logs` -> `evidence/`, keep `smashline_1304` overlay + `engine-local-changes.patch`).
`pyra_mythra_clone`: keep `README/HANDOFF/ASSESSMENT`, `tools/`, `trace/` and `runtime/` source; archive
`editable/` (2.9 GB of copies of dumps), `build/`, `native/`, the 60+ crash logs.

**Phase 5 - retire modpack_test_1.** Only after you spot-check. Keep it read-only for a month or zip
`archive/` to an external drive. Move `George`, `ssbuGeorgeMoveset-main`, `chrom_c07_ftilt` to a
sibling `other_mods/` (or delete: George/Chrom aren't yours).

Order of value/risk: Phase 1 and 2 first; phases 3-5 can wait without any harm.

## 5. dumps/ layout ("all relevant dumps, sorted")

Mirror the ARC path scheme, because every tool and doc already uses those paths; sort by *origin*
first so an agent knows what is authoritative.

```
dumps/
  INDEX.md                   coverage table (which fighters / which subfolders are present) + how to dump more
  manifest.sha256            one hash per top-level artifact (not per file)
  arc/                       from ArcExplorer / arc-network, 13.0.4, EXACTLY as exported
    fighter/<id>/{model,motion,param,sound?}   98 fighters (partial); pgwr-relevant: gamewatch eflame elight element diddy kamui luigi shulk miiswordsman snake younglink chrom
    effect/ camera/ common/ finalsmash/ item/ sound/ standard/ ui/
    prebuilt/nro/release/    lua2cpp_*.nro (98)   <- fighter status/ACMD code
  exefs/
    13.0.4/main (NSO), main.npdm, rtld, sdk, subsdk0     original, read-only
    13.0.4/main.bin          decompressed flat image (VA==file offset; 86,672,752 B) - ONE copy
    13.0.4/README.md         hashes: NSO 77936fe2…, image f70c97d2…, build id 3eae0063…
  decoded/                   things derived from the above, each with the script + version that made it
    main_symbols.json  transformation_symbols.json  article_registry.json  visibility_tables.json
    ghidra_scripts__*.c (Mythra SpecialLw*, etc.)  main_functions/*.asm.txt
  scripts/                   third-party text dumps (git clones, pinned commit noted in README)
    SSBU-Dumped-Scripts/    (WuBoytH) ACMD per fighter  <- can be re-cloned; keep only lua2cpp_* folders you use? keep all, 107 MB
    SSBU-Dumped-Motion-Lists/ (motion_list.yml)  + gamewatch_motion_list.yml already present
    ParamLabels.csv
    SSBU-Dumped-Status-Scripts (tree listing only) 
```

Also: the `export/` folder lacks many files agents later dumped into `pyra_mythra_clone/export additions`
(“network extraction added missing files to ../export”). Confirm before moving that `export/` is the
superset; the 36 files from 2026-09-28 should already be inside it.

What is NOT a dump and must not go here: anything under `references/*/donor_acmd` are *pinned excerpts
with provenance*; they go to `refs/<move>/`.

## 6. Tools worth keeping (found in scratch/ and elsewhere)

Keep and document (each solved a real problem):

| Tool | Now | Purpose |
| --- | --- | --- |
| hash40 / findhash / hashscan | scratch | resolve hashes; brute force short names |
| motion_list parse/patch | `inject_monkey_flip.py`, `build.py:parse_mlist_entries` | byte-exact entry copy, round-trip assert |
| prc read/write | `pgwr/tools/prc.py` | typed .prc edit (pyprc can't add keys) |
| visibility_table / untracked_meshes | pgwr/tools | decode `param_visibility_data_body` (lowercase hashes) |
| article_table / find_rodata_xref / maindesc / constmap / xref*.py | pgwr/tools, scratch | static analysis of flat `main.bin` |
| nro_syms | pgwr/tools | list `create_agent_fighter_*` symbols |
| gen_acmd / gen_common | pgwr/tools | dump -> Rust (rules R1-R26) - the core "copy a move" engine |
| build_hero_spin / retarget helpers | swap/tools | bone-intersection retarget of nuanmb |
| extract params | swap+pgwr | donor .prc -> Rust table w/ SHA |
| summarise_mflip_log (+fixture) | scratch | shows how to guard log parsers |
| decode_log_names.py | scratch | status ids -> names |
| verify_nro / deploy hash check | scratch | catches "deploy shipped the old binary" |
| install-to-card.sh | pgwr | card autodetect + backup + verify + rollback (fix smashline default!) |
| build_plugin.cmd | scratch | cmd wrapper so exit codes are real |
| atmosphere crash-report decoder | (ad hoc) | should be created: PC -> module+offset -> symbol |

Drop: `test_*.py`, `x24*.py`, `w690`, `e61`… one-offs (archive).

## 7. Decisions I need from you

1. **Move vs copy** for phase 1 (recommend move; same drive). OK to *move* `export/` etc. once agents are idle?
2. **George / Chrom / skins / skyline template**: delete, or shelve in `other_mods/`?
3. Keep `pyra_mythra_clone/editable` (2.9 GB of duplicate asset copies)? Recommend archive/delete; it is regenerable by its own `prepare.py`.
4. Is `Space Bunny Alpha`'s smashline experiment fully dead? (assumed yes; I would archive `smashline_1304/src/pgwr_article.rs`.)
5. Which repo hosting? Recommend a private git repo for `src/`, `handbook/`, `projects/`, `tools/` only.
6. The other machine (`<user>`) - do you still use it? If yes `paths.toml` must support two profiles.

## 8. Open risks / things to verify before moving

- `install-to-card.sh` default installs `target-smashline/…/libsmashline_plugin.nro` - verify the card
  currently has `5f4091ee…` (good) and change the script default to `--no-smashline` first.
- Several docs claim different last-known-good states; the authoritative one is `mod_files/pyra_gamewatch_reskin/install-record-0.14.0.json` + hashes on the card.
- An agent may still be writing `mod_output/pyra_gamewatch_reskin`; only touch it in phase 4.
- `scratch/ghidra` (1.1 GB unpacked Ghidra 11.1.2 + a project) is a *tool install*, not data. Record the version and download URL, keep only `ghidra_scripts/` and the project if wanted.
