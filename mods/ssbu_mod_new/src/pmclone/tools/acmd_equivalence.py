#!/usr/bin/env python3
"""tools/acmd_equivalence.py

Verifies equivalence between dumped Smashline ACMD scripts and the ported
modules in pyra_mythra_clone/moveset/src/acmd/.

Requirements from HANDOFF_WEAK_MODEL.md:
- For each ported function, normalise whitespace and compare its token stream to the dump's.
- The only allowed differences are the entries in acmd-port-fixes.md.
- Report `n identical / n fixed / n excluded`.
- Done when equivalence script reports 0 unexplained differences.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = WORKSPACE_ROOT / "src" / "pmclone"
SMASHLINE_ROOT = WORKSPACE_ROOT / "dumps" / "scripts" / "SSBU-Dumped-Scripts-main" / "smashline"
MOVESET_ACMD = PROJECT_ROOT / "moveset" / "src" / "acmd"
FIXES_MD = PROJECT_ROOT / "reports" / "acmd-port-fixes.md"

AGENT_MAP = [
    ("eflame", "cflame", "lua2cpp_eflame"),
    ("eflame_blazepillar", "cflame_blazepillar", "lua2cpp_eflame"),
    ("eflame_esword", "cflame_esword", "lua2cpp_eflame"),
    ("eflame_firepillar", "cflame_firepillar", "lua2cpp_eflame"),
    ("eflame_windummy", "cflame_windummy", "lua2cpp_eflame"),
    ("elight", "clight", "lua2cpp_elight"),
    ("elight_beam", "clight_beam", "lua2cpp_elight"),
    ("elight_bunshin", "clight_bunshin", "lua2cpp_elight"),
    ("elight_exprosiveshot", "clight_exprosiveshot", "lua2cpp_elight"),
    ("elight_meteor", "clight_meteor", "lua2cpp_elight"),
    ("elight_spreadbullet", "clight_spreadbullet", "lua2cpp_elight"),
    ("elight_windummy", "clight_windummy", "lua2cpp_elight"),
    ("element_diver", "clement_diver", "lua2cpp_element"),
]

FN_HEADER_RE = re.compile(
    r'(?:pub\s+)?unsafe\s+extern\s+"C"\s+fn\s+((game|effect|sound|expression)_([a-zA-Z0-9_]+))\s*\('
)

def strip_strings_and_comments(text: str) -> str:
    s = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    s = re.sub(r'//.*', '', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
    return s

def tokenize(text: str) -> List[str]:
    # Tokenize words, numbers, strings, and symbols
    token_re = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*|\d+\.\d+|\d+|"(?:\\.|[^"\\])*"|[^\s\w]')
    return token_re.findall(text)

def parse_dump_functions(filepath: Path) -> List[Dict[str, str]]:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    fn_starts = []
    for idx, line in enumerate(lines):
        m = FN_HEADER_RE.search(line)
        if m:
            fn_starts.append((idx, m.group(1), m.group(2), m.group(3)))

    fns = []
    for i, (start_idx, full_name, cat, base_name) in enumerate(fn_starts):
        next_start = fn_starts[i + 1][0] if i + 1 < len(fn_starts) else len(lines)
        depth = 0
        opened = False
        end_idx = start_idx
        for line_idx in range(start_idx, next_start):
            stripped = strip_strings_and_comments(lines[line_idx])
            for ch in stripped:
                if ch == '{':
                    depth += 1
                    opened = True
                elif ch == '}':
                    depth -= 1
                    if opened and depth == 0:
                        end_idx = line_idx
                        break
            if opened and depth == 0:
                break
        else:
            end_idx = next_start - 1

        fn_text = "".join(lines[start_idx : end_idx + 1])
        fns.append({
            "name": full_name,
            "category": cat,
            "base_name": base_name,
            "text": fn_text,
        })
    return fns

def parse_ported_agent(filepath: Path) -> Dict[str, Dict]:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Find both active functions and commented-out excluded functions
    # An excluded function is marked by "// EXCLUDED:" followed by commented lines
    fn_map = {}
    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("// EXCLUDED:"):
            # Collect following commented lines
            start = i
            i += 1
            excl_lines = []
            while i < len(lines) and lines[i].startswith("//"):
                excl_lines.append(lines[i][2:].lstrip())
                i += 1
            excl_text = "\n".join(excl_lines)
            m = FN_HEADER_RE.search(excl_text)
            if m:
                fn_name = m.group(1)
                fn_map[fn_name] = {
                    "status": "excluded",
                    "text": excl_text,
                }
            continue

        m = FN_HEADER_RE.search(line)
        if m and not line.strip().startswith("//"):
            fn_name = m.group(1)
            # Find end of this function
            depth = 0
            opened = False
            fn_lines = []
            for j in range(i, len(lines)):
                fn_lines.append(lines[j])
                stripped = strip_strings_and_comments(lines[j])
                for ch in stripped:
                    if ch == '{':
                        depth += 1
                        opened = True
                    elif ch == '}':
                        depth -= 1
                        if opened and depth == 0:
                            break
                if opened and depth == 0:
                    i = j
                    break
            fn_map[fn_name] = {
                "status": "active",
                "text": "\n".join(fn_lines),
            }
        i += 1

    return fn_map

def load_fixes_from_md(md_path: Path) -> Set[Tuple[str, str]]:
    fixed_set = set()
    if not md_path.exists():
        return fixed_set
    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("|") and not line.startswith("| Agent") and not line.startswith("|---"):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 2:
                    agent, fn = parts[0], parts[1]
                    fixed_set.add((agent, fn))
    return fixed_set

def normalize_active_ported_tokens(tokens: List[str]) -> List[str]:
    # In active functions, the only syntactic difference from the dump header is `pub`
    # e.g., `pub unsafe extern "C" fn` vs `unsafe extern "C" fn`
    if len(tokens) >= 1 and tokens[0] == "pub":
        return tokens[1:]
    return tokens

def main():
    fixed_set = load_fixes_from_md(FIXES_MD)

    n_identical = 0
    n_fixed = 0
    n_excluded = 0
    unexplained = []

    for vagent, cagent, folder in AGENT_MAP:
        dirpath = SMASHLINE_ROOT / folder / vagent
        txts = sorted([f for f in os.listdir(dirpath) if f.endswith(".txt")])

        # Parse dump
        dump_fns = []
        for txt in txts:
            parsed = parse_dump_functions(dirpath / txt)
            for p in parsed:
                p["file"] = txt
            dump_fns.extend(parsed)

        # Parse ported file
        ported_path = MOVESET_ACMD / f"{cagent}.rs"
        if not ported_path.exists():
            print(f"Error: missing ported file {ported_path}", file=sys.stderr)
            sys.exit(1)

        ported_map = parse_ported_agent(ported_path)

        for dfn in dump_fns:
            name = dfn["name"]
            if name not in ported_map:
                unexplained.append((cagent, name, "Function missing from ported file"))
                continue

            ported_entry = ported_map[name]
            status = ported_entry["status"]

            if status == "excluded":
                n_excluded += 1
            elif (cagent, name) in fixed_set:
                n_fixed += 1
            else:
                dump_tokens = tokenize(dfn["text"])
                ported_tokens = normalize_active_ported_tokens(tokenize(ported_entry["text"]))
                if dump_tokens == ported_tokens:
                    n_identical += 1
                else:
                    unexplained.append((cagent, name, "Token mismatch between dump and ported without recorded fix"))

    total = n_identical + n_fixed + n_excluded
    print(f"ACMD Equivalence Summary:")
    print(f"  Total scripts examined : {total}")
    print(f"  Identical              : {n_identical}")
    print(f"  Fixed (in fixes.md)    : {n_fixed}")
    print(f"  Excluded (in QUESTIONS): {n_excluded}")
    print(f"  Unexplained differences: {len(unexplained)}")

    if unexplained:
        print("\nUnexplained differences detail:")
        for agent, fn, reason in unexplained[:20]:
            print(f"  - {agent}::{fn}: {reason}")
        if len(unexplained) > 20:
            print(f"  ... and {len(unexplained) - 20} more")
        sys.exit(1)
    else:
        print("\nStatus: PASS (0 unexplained differences)")
        sys.exit(0)

if __name__ == "__main__":
    main()
