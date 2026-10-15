#!/usr/bin/env python3
"""Write MANIFEST.md of an export from export-report.json (run after export.py).

Usage (from the workspace root):
    python <dst>/tools/showcase-export/make_manifest.py --src . --dst <dst>
The generator column is read from the header comment of each left-out file in --src.
"""
import argparse
import collections
import json
import os
import re

GEN = re.compile(r"(?i)(?:generated (?:by|from|there by)|generated in the donor project by|from pinned .*? by)\s+`?([\w./-]+\.py)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    a = ap.parse_args()
    dst = a.dst
    r = json.load(open(os.path.join(dst, "tools/showcase-export/export-report.json"), encoding="utf-8"))

    def find_gen(name):
        b = os.path.basename(name)
        for dp, _, fn in os.walk(os.path.join(dst, "mods")):
            if b in fn:
                return os.path.relpath(os.path.join(dp, b), dst).replace(os.sep, "/")
        return None

    folder = {}
    for k in r["excluded_by_folder"]:
        p, why = k.split("  -- ", 1)
        folder[p] = why
    rows = []
    for p in r["excluded_source_files"]:
        why = folder.get(p) or folder.get(p.rsplit("/", 1)[0] + "/*", "")
        g = "-"
        full = os.path.join(a.src, p)
        if os.path.isfile(full):
            m = GEN.search(open(full, encoding="utf-8", errors="replace").read(4000))
            if m:
                f = find_gen(m.group(1))
                g = f"`{f}`" if f else f"`{m.group(1)}` (not in this copy)"
        rows.append((p, why, g))

    cat = collections.Counter()
    for why, n in r["excluded_by_reason"].items():
        if why.startswith("binary or game-format"):
            why = "game-format or binary file (model, texture, animation, sound, effect, param, NRO, executable, compiled Lua)"
        cat[why] += n

    L = []
    A = L.append
    A("# MANIFEST\n")
    A("What this folder contains, what was left out and why, and every change made to copied files. "
      "The copy was produced by [`tools/showcase-export/export.py`](tools/showcase-export/export.py) on 2026-10-15; "
      "its machine-readable report is [`tools/showcase-export/export-report.json`](tools/showcase-export/export-report.json).\n")
    A("## Included\n")
    A("Same relative layout as the original workspace, so paths inside the documents resolve.\n")
    A("| area | what |\n|---|---|")
    A("| workspace root | `AGENTS.md` (+ `CLAUDE.md` / `GEMINI.md` pointers), `kb/` (index, playbooks, findings, reference, journal, templates), "
      "`tools/` (README, REGISTRY, `arc-extract` and `data-arc-extract` source, `freebuff-dispatch`), "
      "`evidence/freebuff-dispatch/` (prompts and run records of the dispatch experiment) |")
    A("| `mods/ssbu_mod_new/` | `AGENTS.md`, `README.md`, `CURRENT_INSTALL.md`, `.gitignore`, `paths.example.toml`, `handbook/` "
      "(all pages, `graveyard.md`, `facts/facts.yaml`), `projects/` (every `STATUS.md`, plans, changelogs, history), `evidence/` "
      "(every `RESULT.md` / `INSTALL.md` / `REVIEW.md`, install records, audit and verification JSON), `tools/` (all audit, build "
      "and check scripts), `kb/findings/`, `dumps/INDEX.md` + `MISSING.md`, `refs/*` provenance only (`SOURCE.json`, "
      "`*manifest.json`, notes), `src/` (plugin and pipeline source except the game-derived files below; build scripts, "
      "manifests, validation records) |")
    A("| `mods/mii_customizer/` | `AGENTS.md`, `README.md`, `STATUS.md`, `HANDOFF.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md`, "
      "`build-plugin.sh`, `phases/`, `prompts/` (all), `research/` (all reports incl. per-move reports), `evidence/` (check "
      "scripts, `RESULT*.md`, check outputs), `plugin/` (`Cargo.toml`, `Cargo.lock`, README, own source modules), `moves/*/` "
      "(`unit.json`, asset build and retarget scripts), `tools/` (own tools), `scratch/` (only check scripts and host tests "
      "that copied documents reference by path; see `NEEDS_DECISION.md`) |")
    A("| new files | `README.md`, `MANIFEST.md`, `NEEDS_DECISION.md`, `dump/README.md`, `gamedata/README.md`, "
      "`tools/showcase-export/` (scripts, README, report), one row added to `tools/REGISTRY.md` |\n")

    A("## Left out, by category\n")
    A("| category | entries |\n|---|---:|")
    for why, n in sorted(cat.items(), key=lambda x: -x[1]):
        A(f"| {why} | {n} |")
    A("\nEntries count files, except whole folders (`target/`, `builds/`, vendored crates, `assets/`, the `scratch/` roots), "
      "which count once. Per-folder detail: `excluded_by_folder` in the report.\n")
    A("Never walked (outside the copied roots): `dump/`, `gamedata/`, `Ryujinx/`, `testenv/`, workspace `builds/` and "
      "`scratch/`, and the stray root `moves/` folder (a duplicate of `mods/mii_customizer/moves/aerial_back__mario` "
      "that a worker wrote to the wrong place).\n")
    A("In short: nothing taken from the game (dumps, extractions, models, textures, animations, sounds, effects, params, "
      "Lua and ACMD scripts, decoded tables, disassembly, relocated machine code, built NROs); no third-party code "
      "(vendored crates, Smashline fork, Clone Engine, Lua 5.3.6, Python wheels and DLLs, `*_reference.rs` copies); "
      "no logs, crash reports, agent transcripts, SD-card backups, build outputs or caches; no machine-local config "
      "(`paths.toml`).\n")

    A("## Game-derived source files left out\n")
    A("Files a build needs that were ported or generated from the game's own scripts, parameters or code, or copied from "
      "third-party sources. Where the file header names a generator, it is listed: rerun it against your own dump. "
      "Files without a generator were ported by hand and must be ported again (for example with "
      "`mods/ssbu_mod_new/tools/fetch_donor_acmd.py` and `mods/ssbu_mod_new/handbook/05_acmd_porting.md`). "
      "`mods/ssbu_mod_new/src/pmclone/moveset/src/acmd/` (15 files of ported ACMD) is left out as a whole; "
      "`.s`/`.S` relocated machine code appears below only where it sat in the plugin source.\n")
    A("| file | reason | generator |\n|---|---|---|")
    for p, why, g in rows:
        A(f"| `{p}` | {why} | {g} |")

    A("\n## Redactions and edits in copied files\n")
    A("Automatic replacements (rules in `export.py`): workspace absolute paths to relative paths (bare root to "
      "`<workspace>`, old root to `<old workspace path>`); user-profile paths to `%USERPROFILE%`; the ArcExplorer "
      "install path to `<ArcExplorer dir>`; SD-card drive letters to `sd:/`; other drive-letter paths to `<drive>:/`; "
      "the machine account name to `<user>`; e-mail addresses to `<email>` (none were found).\n")
    A("| file | replacements |\n|---|---|")
    for p in sorted(r["redactions"]):
        A(f"| `{p}` | " + ", ".join(f"{k} x{v}" for k, v in r["redactions"][p].items()) + " |")
    A("\nManual edits (the `manual edit` entries above; exact rules in `TEXT_EDITS` in `export.py`):\n")
    A("- `kb/INDEX.md`: removed the row that linked the left-out Google-account finding.")
    A("- `kb/findings/claude-and-codex-clis-report-real-subscription-limits.md`: \"this Pro account\" became "
      "\"the account used\" (subscription tier).")
    A("- `kb/reference/local-machine.md`: the CLI login-state values replaced by \"(removed for publication)\".\n")
    A("Disassembly removed from reports (runs of 12 or more instruction lines replaced by a one-line note):\n")
    for p, n in sorted(r["disassembly_lines_removed"].items()):
        A(f"- `{p}`: {n} lines")
    A("\nRedactions that touch code (check before running these scripts):\n")
    A("- `mods/ssbu_mod_new/tools/verify_installed_card.py`: the default card path became `sd:/ultimate/mods/...`; "
      "pass your card's real path.")
    A("- `mods/mii_customizer/tools/gunner-catalog/validate_catalog.py`: a guard that asserts no absolute drive path "
      "appears in its output now tests for the placeholder `<drive>:/`; restore the drive letter if you rely on it.")
    A("- Workspace-path replacements in JSON records (`checks.json`, `install-record-*.json`, ...) only change "
      "recorded strings, not behaviour.")
    A("\nLeft out for personal-data reasons: `kb/findings/gemini-cli-rejects-this-google-account.md` (describes the "
      "user's Google account tier).\n")
    A("Left out as third-party leftovers whose code was already excluded: "
      "`mods/ssbu_mod_new/src/pgwr/tools/one_slot_effects/UPSTREAM_README.md`, "
      "`mods/ssbu_mod_new/src/pgwr/tools/texture_cli/LICENSE`.\n")
    A("Written by hand after the export run (a rerun of `export.py` does not reproduce them): `README.md`, "
      "`MANIFEST.md` (by `make_manifest.py`), `NEEDS_DECISION.md`, `dump/README.md`, `gamedata/README.md`, and the "
      "`tools/showcase-export/` scripts and README. The `showcase-export` row in `tools/REGISTRY.md` is added by "
      "`export.py` (`TEXT_EDITS`).\n")
    A("## Final checks (2026-10-15, `tools/showcase-export/check_export.py`)\n")
    A("| check | result |\n|---|---|")
    A("| e-mail addresses | 0 |")
    A("| account / personal names (machine account, real name) | 0 |")
    A("| user-profile paths (`C:\\Users\\...`) | 0 |")
    A("| drive-letter paths | 10 in 7 files (not counting this table), all justified: standard install locations (`C:/msys64`, `C:\\Program Files\\dotnet`, "
      "`c:\\devkitPro`), an elided `C:\\...` in a note, and string literals in path-guard checks "
      "(`validate_catalog.py`, `check_presets.py`, `patch_examples.py` escape sequence `f:\\n`) |")
    A("| phone-number pattern | 23 in 9 files (not counting this table), all hex dumps or byte counts in research reports (`0001 0005 0002`, `86 672 752`) |")
    A("| key / token / secret / password / Bearer | about 1,900 occurrences of the words (dictionary keys, param-hash "
      "keys, `prod.keys` file names, tokenizer variables); a targeted scan for assigned secret values, `Bearer` headers "
      "and known token formats (`sk-`, `ghp_`, `AKIA`, `AIza`, `xox*`) found none (one hit: a Rust variable "
      "`let token = s.cast_token...`) |")
    A("| hex longer than 64 | 2, the same sha256 written with one extra digit in two snake-grenade notes |")
    A("| base64-like strings | 21 in 19 files, all file paths (`atmosphere/contents/01006A800016E000/...`) or a mixed-case sha256 |")
    A("| files over 200 KB | 1: `mods/ssbu_mod_new/CURRENT_INSTALL.md` (209 KB, agent-written install records; plain text) |")
    A("| non-text files | 0 |")
    A("| relative links in README.md, MANIFEST.md, NEEDS_DECISION.md | all resolve |\n")
    with open(os.path.join(dst, "MANIFEST.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"{len(rows)} source rows, {len(r['redactions'])} redacted files")


if __name__ == "__main__":
    main()
