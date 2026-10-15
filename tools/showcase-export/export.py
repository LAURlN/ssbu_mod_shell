#!/usr/bin/env python3
"""Export a publishable working copy of the SSBU agent workspace.

Copies the workspace's own text material (rules, kb, handbook, status, prompts, reports,
tools, mod source code) into a destination folder, keeping the original layout so relative
paths in the docs still resolve. Leaves out game data, game-derived code, third-party code,
binaries, logs and caches, and redacts machine paths and account names in copied text.

Usage (from the workspace root):
    python showcase/smash-agent-workflow/tools/showcase-export/export.py \
        --src . --dst showcase/smash-agent-workflow --redact <account-name> [--redact <other>]

Writes `tools/showcase-export/export-report.json` in the destination (counts per exclusion
reason, every excluded source file with its reason, every redaction per file).
The script never deletes anything; run it into an empty destination (its own folder excepted).
Status: experimental, written 2026-10-15 for the showcase export.
"""
import argparse
import fnmatch
import json
import os
import re
import sys

ROOTS = ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "kb", "tools", "evidence", "mods"]

# Directory names never entered (any depth). Reason in the value.
EXCLUDED_DIRS = {
    "target": "build cache", ".cache": "build cache", "__pycache__": "cache", "state": "runtime state",
    ".git": "git metadata", ".freebuff": "agent tool state", "builds": "build outputs (NRO, packages)",
    "gamedata": "game files extracted from the dump", "references": "third-party / donor material",
    "archive": "old snapshots incl. game files", "vendor": "vendored third-party code",
    ".deps": "vendored Python packages", "analysis_lib": "vendored Python packages + DLLs",
    "runtime_lib": "vendored Python packages", "python_deps": "vendored Python packages",
    "upstream": "vendored third-party code", "smashline_1304": "vendored third-party code (Smashline fork)",
    "assets": "game models/textures/effects", "theme_preview": "renders of game models",
    "vs_previews": "renders of game models", "sd-backups": "SD card backups", "build-archives": "build archives",
    "generated": "code generated from game scripts", "node_modules": "third-party packages",
    "logging_backup_0.20.9": "old copy of plugin source incl. ported game code",
    "dl": "downloaded third-party archives", "bin": "built binaries",
}
# Workspace-relative directory paths never entered.
EXCLUDED_PATHS = {
    "mods/ssbu_mod_new/dumps/decoded": "decompiled / decoded game data",
    "mods/ssbu_mod_new/dumps/scripts": "dumped game scripts",
    "mods/ssbu_mod_new/src/pmclone/native": "game disassembly",
    "mods/ssbu_mod_new/src/pmclone/reference": "game ACMD text and .prc params",
    "mods/ssbu_mod_new/src/pmclone/moveset/src/acmd": "ACMD ported from game scripts",
    "mods/mii_customizer/tools/luac53-game/src": "third-party Lua 5.3.6 source",
    "mods/mii_customizer/gamedata": "game files extracted from the dump",
    "evidence/moves": "stray copy written to the wrong place by a worker (canonical copy is in mods/mii_customizer)",
}
SCRATCH_DIR = "scratch"  # handled separately: only referenced code files are copied

EXCLUDED_EXT = set(
    ".nro .exe .dll .pyd .pyi .o .gz .bin .prc .stprm .stdat .nus3audio .nus3bank .nutexb .bntx .eff "
    ".nuanmb .numdlb .numshb .nusktb .numatb .nuhlpb .lua .lc .out .xmsbt .msbt .bfres .tar .zip .7z "
    ".log .png .jpg .jpeg .gif .webp .s .asm .motdiff .arc .sarc .bflyt .tsv .csv .jsonl .calls .inputs "
    ".html .css .1 .pyc .bak .nca .nsp .xci .keys".split()
)
EXT_REASON = {
    ".log": "log", ".jsonl": "agent transcript / log", ".s": "relocated game machine code",
    ".asm": "game disassembly", ".tsv": "decoded game table", ".csv": "decoded game table",
    ".png": "image (game renders / previews)", ".jpg": "image", ".lua": "game Lua script",
}
# Single files left out for personal-data reasons, and exact text edits in copied files.
EXCLUDED_FILES = {
    "kb/findings/gemini-cli-rejects-this-google-account.md": "describes the user's Google account tier (login details)",
    "mods/ssbu_mod_new/src/pgwr/tools/one_slot_effects/UPSTREAM_README.md": "third-party README (code not included)",
    "mods/ssbu_mod_new/src/pgwr/tools/texture_cli/LICENSE": "third-party license (code not included)",
}
TEXT_EDITS = {
    "tools/REGISTRY.md": [
        (re.compile(r"(?s)\A(.*?)\s*\Z"), r"\1" "\n| [showcase-export](showcase-export/README.md) | experimental | Export a publishable working "
         "copy of the workspace without game data, game-derived code, third-party code or personal data | "
         "`python <dst>/tools/showcase-export/export.py --src . --dst <dst> --redact <account-name>` |\n"),
    ],
    "kb/INDEX.md": [
        (re.compile(r"^\| \[Gemini CLI refuses.*\n", re.M), ""),
    ],
    "kb/findings/claude-and-codex-clis-report-real-subscription-limits.md": [
        (re.compile(r"it was empty on this Pro account"), "it was empty on the account used"),
    ],
    "kb/reference/local-machine.md": [
        (re.compile(r"\| login state on 2026-10-01 \|"), "| login state |"),
        (re.compile(r"\| (logged in with ChatGPT|logged in|not logged in yet) \|"), "| (removed for publication) |"),
    ],
}

EXCLUDED_NAMES = {"paths.toml": "machine-local config", "scratch_inv.txt": "scratch listing",
                  ".last-sd-backup": "machine-local marker", "luac.out": "compiled Lua output"}

# Rust files that are ported/generated from game scripts, decompiled game code or third-party
# code (reviewed by hand on 2026-10-15). Workspace-relative glob patterns.
GAME_DERIVED_RS = {
    "mods/mii_customizer/moves/*/unit.rs": "move unit: ACMD / status code ported from the donor fighter",
    "mods/mii_customizer/plugin/src/unit_*.rs": "move unit: ACMD / status code ported from the donor fighter",
    "mods/mii_customizer/plugin/src/moves.rs": "own dispatcher mixed with ported Mii Brawler ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/attack_air_f.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/gaogaen_throw_b.rs": "generated ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/littlemac_attack_s4.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/monkey_flip.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/pikachu_attack_air_b.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/robot_attack_lw3.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/snake_attack_hi3.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/snake_throw_lw.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/attack_air_hi.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_spin_acmd.rs": "generated ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_spin_params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/lucas_attack_lw4.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/ness_throw_b.rs": "ported decompiled game code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/throw_lw.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_mana/hud_signatures.rs": "game instruction signatures",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_mana/params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/acmd.rs": "generated ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/donor_params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/signatures.rs": "game instruction signatures",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/fighter.rs": "translated from game NRO code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/game_acmd.rs": "generated ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/script_acmd.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/native_params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/native_signatures.rs": "game instruction signatures",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/receiver.rs": "generated translation of game code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/fighter.rs": "translated from game NRO code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/fighter_loops.rs": "translated from game NRO code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/gaogaen_throw_b_data.rs": "generated from game data",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip.rs": "ported decompiled game status code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip_capture.rs": "translated from game native code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip_capture_data.rs": "generated from game data",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip_params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/special_hi.rs": "ported decompiled game status code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/dk_cargo/acmd.rs": "generated ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/dk_cargo/data.rs": "generated from game params",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/acmd.rs": "generated ACMD",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/lower.rs": "translated from game native code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/mod.rs": "ported decompiled game status code",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/native_signatures.rs": "game instruction signatures",
    "mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/pgwr/tools/*_reference.rs": "third-party source copy",
    "mods/ssbu_mod_new/src/pgwr/tools/texture_cli/*_reference.rs": "third-party source copy",
    "mods/ssbu_mod_new/src/mgw_swap/src/attack_air_f.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/mgw_swap/src/attack_air_hi.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/mgw_swap/src/hero_spin3_acmd.rs": "generated ACMD",
    "mods/ssbu_mod_new/src/mgw_swap/src/hero_spin3_vanilla_acmd.rs": "generated ACMD",
    "mods/ssbu_mod_new/src/mgw_swap/src/hero_spin3_params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/mgw_swap/src/hero_spin_params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/mgw_swap/src/monkey_flip.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/mgw_swap/src/monkey_flip_params.rs": "generated from game params",
    "mods/ssbu_mod_new/src/mgw_swap/src/monkey_flip_status.rs": "ported decompiled game status code",
    "mods/ssbu_mod_new/src/mgw_swap/src/throw_lw.rs": "ported ACMD",
    "mods/ssbu_mod_new/src/pmclone/runtime/src/modules.rs": "generated from third-party bindings",
    "mods/ssbu_mod_new/src/pmclone/trace/src/work_ids.rs": "generated from third-party bindings",
}

# JSON outputs whose name says they hold decoded game data (tables, sites, signatures).
DATA_JSON = re.compile(
    r"(?i)(decoded|status_table|param|motion_entries|motion_list|motion_lib|instruction_graph|signature|xrefs|"
    r"strings|sites|sweep|rowfill|derived|ui_api|focus_lists|input_scan|inventory_make|catalog|special_variants|"
    r"symbols|constants|cargo|translation|callback|^native|_native|capture_owned|event_slots|receivers|"
    r"registration|vl_|life_native|examples|COLLISION|ENGINE|ROUTES)"
)
REFS_KEEP = re.compile(r"(?i)^(SOURCE\.json|INDEX\.md|.*manifest\.json|public_sources\.json|.*\.md)$")

TEXT_LIMIT_JSON = 150_000
TEXT_LIMIT_OTHER = 300_000

SEP = r"(?:\\{1,4}|/)"
ASM_LINE = re.compile(
    r"^\s*(?:[-*>|`]\s*)?(?:0x)?[0-9a-fA-F]{5,}[:\s|]+.*\b(ldr|ldur|str|stur|stp|ldp|bl|blr|br|mov|movk|movz|add|sub|"
    r"cmp|b\.\w+|b|adrp|ret|cbz|cbnz|tbz|tbnz|fmov|orr|and|lsl|lsr|csel|cset|udf|nop|madd|ldrb|strb|ldrh|strh|fcmp)\b",
    re.I,
)
ASM_RUN = 12
ACMD_LINE = re.compile(r"\b(frame|wait|wait_loop_clear|FT_MOTION_RATE)\s*\(|macros::|is_excute|ATTACK\(|sv_animcmd")


def rel(path):
    return path.replace(os.sep, "/")


def build_redactions(words):
    subs = []
    root = r"(?:[A-Za-z]:|/[a-zA-Z])" + SEP + r"(?:modpack_smash_3|Smash_modding_space)"
    subs.append(("workspace path", re.compile(root + SEP), ""))
    subs.append(("workspace path", re.compile(r"(?:[A-Za-z]:|/[a-zA-Z])" + SEP + r"Smash_modding_space\b"),
                 "<old workspace path>"))
    subs.append(("workspace path", re.compile(root + r"\b"), "<workspace>"))
    subs.append(("user home path", re.compile(r"(?:[A-Za-z]:|/[a-zA-Z])" + SEP + r"Users" + SEP + r"[^\\/\s\"'<>:]+"),
                 "%USERPROFILE%"))
    subs.append(("tool install path", re.compile(r"[A-Za-z]:" + SEP + r"ArcExplorer_win_x64"), "<ArcExplorer dir>"))
    subs.append(("SD card path", re.compile(r"\b[D-Z]:" + SEP + r"(?=ultimate|atmosphere|\.\.\.|switch)", re.I), "sd:/"))
    subs.append(("drive path", re.compile(r"\b[D-Z]:" + SEP), "<drive>:/"))
    for w in words:
        subs.append(("account name", re.compile(re.escape(w) + r"\w*", re.I), "<user>"))
    subs.append(("e-mail", re.compile(r"\b(?!noreply@|git@)[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"),
                 "<email>"))
    return subs


def strip_asm(text):
    lines = text.split("\n")
    out, i, removed = [], 0, 0
    while i < len(lines):
        j = i
        while j < len(lines) and (ASM_LINE.search(lines[j]) or (j > i and not lines[j].strip())):
            j += 1
        while j > i and not lines[j - 1].strip():
            j -= 1
        if j - i >= ASM_RUN:
            n = j - i
            out.append(f"[{n} lines of game disassembly removed for publication; regenerate them from your own "
                       f"13.0.4 main with this report's check script]")
            removed += n
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out), removed


class Exporter:
    def __init__(self, src, dst, words):
        self.src, self.dst = os.path.abspath(src), os.path.abspath(dst)
        self.subs = build_redactions(words)
        self.included, self.excluded, self.redactions, self.asm_removed = [], [], {}, {}
        self.scratch_dirs = {}

    def exclude(self, path, reason):
        self.excluded.append((path, reason))

    def file_reason(self, p):
        """Return an exclusion reason for workspace-relative file path p, or None to include."""
        b = os.path.basename(p)
        e = os.path.splitext(b)[1].lower()
        full = os.path.join(self.src, p)
        size = os.path.getsize(full)
        if p in EXCLUDED_FILES:
            return EXCLUDED_FILES[p]
        if b in EXCLUDED_NAMES:
            return EXCLUDED_NAMES[b]
        if e in EXCLUDED_EXT:
            return EXT_REASON.get(e, f"binary or game-format file ({e})")
        if "/refs/" in "/" + p and not REFS_KEEP.match(b):
            return "pinned donor material / decoded game data (refs)"
        for pat, why in GAME_DERIVED_RS.items():
            if fnmatch.fnmatch(p, pat):
                return why
        if e == ".rs":
            with open(full, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines() or [""]
            hits = sum(1 for line in lines if ACMD_LINE.search(line))
            if hits >= 25 and hits / len(lines) >= 0.1:
                return "ACMD ported from game scripts (heuristic)"
        if e == ".txt" and ("/evidence/" in "/" + p or "log" in b.lower()):
            return "raw log / disassembly / card listing (evidence text)"
        if e == ".json":
            if size > TEXT_LIMIT_JSON:
                return "large measured output (regenerate with its check script)"
            if DATA_JSON.search(b) and not p.endswith("unit.json"):
                return "decoded game data output (regenerate with its check script)"
        elif size > TEXT_LIMIT_OTHER:
            return "file over size limit"
        try:
            with open(full, "rb") as fh:
                fh.read().decode("utf-8")
        except UnicodeDecodeError:
            return "non-text file"
        return None

    def walk(self, root):
        full = os.path.join(self.src, root)
        if os.path.isfile(full):
            yield root
            return
        for dp, dn, fn in os.walk(full):
            rp = rel(os.path.relpath(dp, self.src))
            keep = []
            for d in sorted(dn):
                sub = f"{rp}/{d}"
                if sub.startswith("showcase"):
                    continue
                if d == SCRATCH_DIR:
                    self.scratch_dirs[sub] = True
                    continue
                if d in EXCLUDED_DIRS or d.startswith("target"):
                    self.exclude(sub + "/", EXCLUDED_DIRS.get(d, "build cache"))
                    continue
                if sub in EXCLUDED_PATHS:
                    self.exclude(sub + "/", EXCLUDED_PATHS[sub])
                    continue
                keep.append(d)
            dn[:] = keep
            for f in sorted(fn):
                yield f"{rp}/{f}"

    def copy(self, p):
        reason = self.file_reason(p)
        if reason:
            self.exclude(p, reason)
            return False
        with open(os.path.join(self.src, p), "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
        counts = {}
        for label, rx, repl in self.subs:
            text, n = rx.subn(repl, text)
            if n:
                counts[label] = counts.get(label, 0) + n
        for rx, repl in TEXT_EDITS.get(p, []):
            text, n = rx.subn(repl, text)
            if n:
                counts["manual edit"] = counts.get("manual edit", 0) + n
        if p.endswith(".md"):
            text, n = strip_asm(text)
            if n:
                self.asm_removed[p] = n
        if counts:
            self.redactions[p] = counts
        out = os.path.join(self.dst, p)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        self.included.append(p)
        return True

    def scratch_refs(self):
        """Code files in scratch dirs that copied text references by exact path (check scripts,
        host tests), plus sibling files those scripts name. Repeats until nothing new is found."""
        rx = re.compile(r"scratch/(\d{4}-\d{2}-\d{2}_[A-Za-z0-9_.+-]+/[A-Za-z0-9_./+-]+\.(?:py|rs|sh|toml))")
        sib = re.compile(r"[A-Za-z0-9_.+-]+\.(?:py|rs|sh|toml)")
        roots = sorted(self.scratch_dirs)
        seen, queue = set(), list(self.included)
        while queue:
            p = queue.pop()
            try:
                with open(os.path.join(self.dst, p), encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                continue
            cands = [f"{r}/{m}" for m in rx.findall(text) for r in roots]
            if "/scratch/" in p:
                d = p.rsplit("/", 1)[0]
                cands += [f"{d}/{m}" for m in sib.findall(text)]
            for q in cands:
                if q in seen or not os.path.isfile(os.path.join(self.src, q)):
                    continue
                seen.add(q)
                if self.copy(q):
                    queue.append(q)
        for r in roots:
            self.exclude(r + "/", "scratch (only files referenced by exact path are copied)")

    def by_folder(self):
        agg = {}
        for p, why in self.excluded:
            key = (p if p.endswith("/") else p.rsplit("/", 1)[0] + "/*") + "  -- " + why
            agg[key] = agg.get(key, 0) + 1
        return dict(sorted(agg.items()))

    def run(self):
        for r in ROOTS:
            for p in self.walk(r):
                if p.startswith("tools/showcase-export/"):
                    continue
                self.copy(p)
        self.scratch_refs()
        reasons = {}
        for _, why in self.excluded:
            reasons[why] = reasons.get(why, 0) + 1
        report = {
            "included_files": len(self.included),
            "excluded_by_reason": dict(sorted(reasons.items(), key=lambda x: -x[1])),
            "excluded_source_files": sorted(p for p, why in self.excluded
                                            if p.endswith(".rs") or why.startswith("relocated")),
            "excluded_by_folder": self.by_folder(),
            "redactions": self.redactions,
            "disassembly_lines_removed": self.asm_removed,
            "scratch_files_copied": sorted(p for p in self.included if "/scratch/" in p),
        }
        out = os.path.join(self.dst, "tools/showcase-export/export-report.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
        print(f"included {len(self.included)} files; excluded {len(self.excluded)} entries")
        for why, n in report["excluded_by_reason"].items():
            print(f"  {n:6}  {why}")
        print(f"redacted files: {len(self.redactions)}; md files with disassembly removed: {len(self.asm_removed)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--redact", action="append", default=[], help="account name to replace (repeatable)")
    a = ap.parse_args()
    if not os.path.isfile(os.path.join(a.src, "AGENTS.md")):
        sys.exit("--src must be the workspace root (AGENTS.md not found)")
    Exporter(a.src, a.dst, a.redact).run()


if __name__ == "__main__":
    main()
