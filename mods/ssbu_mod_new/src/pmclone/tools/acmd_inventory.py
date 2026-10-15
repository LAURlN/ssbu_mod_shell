"""ACMD inventory tool for Pyra, Mythra, and Element dumped scripts.
"""

import json
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Set


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
SMASHLINE_ROOT = WORKSPACE_ROOT / "SSBU-Dumped-Scripts-main" / "smashline"
OUTPUT_JSON = PROJECT_ROOT / "reports" / "acmd-inventory.json"

TARGET_DIRS = ["lua2cpp_eflame", "lua2cpp_elight", "lua2cpp_element"]

FN_HEADER_RE = re.compile(
    r'unsafe\s+extern\s+"C"\s+fn\s+((game|effect|sound|expression)_([a-zA-Z0-9_]+))\s*\('
)

KEYWORDS = {
    "if", "while", "for", "match", "return", "let", "unsafe", "extern", "fn",
    "mut", "ref", "else", "loop", "in", "as", "break", "continue", "where",
    "type", "impl", "trait", "struct", "enum", "const", "static", "pub"
}

CALL_RE = re.compile(r'\b([a-zA-Z0-9_:]+)(?:!|\s*\()')
FN_DEF_RE = re.compile(r'fn\s+([a-zA-Z0-9_]+)\s*\(')


def strip_strings_and_comments(text: str) -> str:
    s = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    s = re.sub(r'//.*', '', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
    return s


def extract_calls(text: str) -> Set[str]:
    calls = set()
    s = strip_strings_and_comments(text)
    defined_fns = set(FN_DEF_RE.findall(s))
    for m in CALL_RE.finditer(s):
        name = m.group(1).strip()
        if name in KEYWORDS or name in defined_fns:
            continue
        calls.add(name)
    return calls


def parse_file_functions(filepath: Path) -> List[Dict[str, Any]]:
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
        line_count = end_idx - start_idx + 1
        fns.append({
            "name": full_name,
            "category": cat,
            "line_count": line_count,
            "text": fn_text,
            "start_line": start_idx + 1,
            "end_line": end_idx + 1,
            "calls": extract_calls(fn_text),
        })
    return fns


def find_unique_calls(all_target_calls: Set[str], other_files: List[Path]) -> Set[str]:
    call_bytes = {c: c.encode("utf-8") for c in all_target_calls}
    found_in_others: Set[str] = set()

    def scan_file(path: Path) -> Set[str]:
        try:
            with open(path, "rb") as f:
                data = f.read()
            return {c for c, cb in call_bytes.items() if cb in data}
        except Exception:
            return set()

    with ThreadPoolExecutor(max_workers=16) as pool:
        for res in pool.map(scan_file, other_files, chunksize=100):
            found_in_others.update(res)

    return all_target_calls - found_in_others


def main() -> int:
    if not SMASHLINE_ROOT.exists():
        sys.stderr.write(f"Smashline root does not exist: {SMASHLINE_ROOT}\n")
        return 1

    # 1. Collect other fighter files for cross-check
    other_dirs = [
        d for d in sorted(os.listdir(SMASHLINE_ROOT))
        if (SMASHLINE_ROOT / d).is_dir() and d not in TARGET_DIRS
    ]
    other_files: List[Path] = []
    for d in other_dirs:
        dp = SMASHLINE_ROOT / d
        for r, _, fs in os.walk(dp):
            for f in fs:
                if f.endswith(".txt"):
                    other_files.append(Path(r) / f)

    # 2. Parse all target agents
    disk_counts: Dict[str, int] = {}
    agent_data: Dict[str, Dict[str, Any]] = {}
    all_target_calls: Set[str] = set()

    for td in TARGET_DIRS:
        tdp = SMASHLINE_ROOT / td
        for agent in sorted(os.listdir(tdp)):
            ap = tdp / agent
            if not ap.is_dir():
                continue
            txt_files = sorted([f for f in os.listdir(ap) if f.endswith(".txt")])
            disk_counts[agent] = len(txt_files)
            agent_data[agent] = {}
            for f in txt_files:
                parsed_fns = parse_file_functions(ap / f)
                agent_data[agent][f] = parsed_fns
                for fn in parsed_fns:
                    all_target_calls.update(fn["calls"])

    # 3. Find unique calls not present in any other fighter
    unique_calls = find_unique_calls(all_target_calls, other_files)

    # 4. Inventory data collection
    total_files = 0
    total_fns = 0
    overall_flag_counts = defaultdict(int)
    overall_flagged_fns = 0

    json_agents: Dict[str, Any] = {}

    for agent in sorted(agent_data.keys()):
        files_dict = agent_data[agent]
        agent_file_count = len(files_dict)
        total_files += agent_file_count

        # Check duplicates within agent
        name_to_files = defaultdict(list)
        for fname in sorted(files_dict.keys()):
            for fn in files_dict[fname]:
                name_to_files[fn["name"]].append(fname)

        agent_fn_count = 0
        agent_flagged_fn_count = 0
        agent_flag_counts = defaultdict(int)
        json_files: Dict[str, Any] = {}

        for fname in sorted(files_dict.keys()):
            fns = files_dict[fname]
            file_fns_json = []
            for fn in fns:
                agent_fn_count += 1
                total_fns += 1
                flags = []

                # Flag 1: Hash40::new_raw(
                if "Hash40::new_raw(" in fn["text"]:
                    flags.append("unresolved_hash")
                    agent_flag_counts["unresolved_hash"] += 1
                    overall_flag_counts["unresolved_hash"] += 1

                # Flag 2: Unique call not in other fighters
                bad_calls = fn["calls"] & unique_calls
                if bad_calls:
                    flags.append(f"call_not_in_other_fighters: {', '.join(sorted(bad_calls))}")
                    agent_flag_counts["call_not_in_other_fighters"] += 1
                    overall_flag_counts["call_not_in_other_fighters"] += 1

                # Flag 3: Unbalanced braces/parentheses
                stripped = strip_strings_and_comments(fn["text"])
                if stripped.count('{') != stripped.count('}') or stripped.count('(') != stripped.count(')'):
                    flags.append("unbalanced_delimiters")
                    agent_flag_counts["unbalanced_delimiters"] += 1
                    overall_flag_counts["unbalanced_delimiters"] += 1

                # Flag 4: Comments containing TODO, unknown, error
                has_suspicious_comment = False
                for line in fn["text"].splitlines():
                    if "//" in line:
                        cpart = line.split("//", 1)[1].lower()
                        if any(w in cpart for w in ("todo", "unknown", "error")):
                            has_suspicious_comment = True
                            break
                if has_suspicious_comment:
                    flags.append("suspicious_comment")
                    agent_flag_counts["suspicious_comment"] += 1
                    overall_flag_counts["suspicious_comment"] += 1

                # Flag 5: Duplicate function name across files of the same agent
                if len(name_to_files[fn["name"]]) > 1:
                    other_fnames = [x for x in name_to_files[fn["name"]] if x != fname]
                    flags.append(f"duplicate_function_name: also in {', '.join(other_fnames)}")
                    agent_flag_counts["duplicate_function_name"] += 1
                    overall_flag_counts["duplicate_function_name"] += 1

                if flags:
                    agent_flagged_fn_count += 1
                    overall_flagged_fns += 1

                file_fns_json.append({
                    "name": fn["name"],
                    "category": fn["category"],
                    "line_count": fn["line_count"],
                    "flags": sorted(flags),
                })

            json_files[fname] = {
                "functions": file_fns_json,
            }

        json_agents[agent] = {
            "file_count": agent_file_count,
            "function_count": agent_fn_count,
            "flagged_function_count": agent_flagged_fn_count,
            "flags_by_type": {k: agent_flag_counts[k] for k in sorted(agent_flag_counts.keys())},
            "files": json_files,
        }

    # Ensure all 5 flag types are in overall_flag_counts
    for ftype in [
        "call_not_in_other_fighters",
        "duplicate_function_name",
        "suspicious_comment",
        "unbalanced_delimiters",
        "unresolved_hash",
    ]:
        if ftype not in overall_flag_counts:
            overall_flag_counts[ftype] = 0

    json_inventory = {
        "totals": {
            "file_count": total_files,
            "function_count": total_fns,
            "flagged_function_count": overall_flagged_fns,
            "flags_by_type": {k: overall_flag_counts[k] for k in sorted(overall_flag_counts.keys())},
        },
        "agents": json_agents,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(json_inventory, f, indent=2, sort_keys=True)

    # Done when check: print both disk and JSON file counts
    print("=== File Totals Check ===")
    all_match = True
    for agent in sorted(disk_counts.keys()):
        d_cnt = disk_counts[agent]
        j_cnt = json_inventory["agents"][agent]["file_count"]
        match = (d_cnt == j_cnt)
        if not match:
            all_match = False
        print(f"Agent '{agent}': disk={d_cnt}, json={j_cnt}, match={match}")

    total_disk = sum(disk_counts.values())
    total_json = json_inventory["totals"]["file_count"]
    total_match = (total_disk == total_json)
    print(f"OVERALL FILE TOTALS: disk={total_disk}, json={total_json}, match={total_match}")

    print("\n=== Flagged Functions by Type ===")
    for k in sorted(overall_flag_counts.keys()):
        print(f"  {k}: {overall_flag_counts[k]}")
    print(f"Total flagged functions: {overall_flagged_fns} / {total_fns}")
    print(f"Output written to: {OUTPUT_JSON}")

    return 0 if (all_match and total_match) else 1


if __name__ == "__main__":
    sys.exit(main())
