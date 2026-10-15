#!/usr/bin/env python3
"""tools/scenario_coverage.py

Verifies scenario test coverage of all `game_` ACMD scripts in
pyra_mythra_clone/reports/acmd-inventory.json against pyra_mythra_clone/tests/scenarios.md.

Requirements from HANDOFF_WEAK_MODEL.md:
- Parses `tests/scenarios.md` and extracts every covered `game_` script.
- Compares against `reports/acmd-inventory.json`.
- Prints: total scenarios, total `game_` scripts covered, missing scripts (if any).
- Exits with 0 if coverage is 100%, non-zero otherwise.
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = WORKSPACE_ROOT / "src" / "pmclone"
INV_PATH = PROJECT_ROOT / "reports" / "acmd-inventory.json"
SCENARIOS_MD = PROJECT_ROOT / "tests" / "scenarios.md"

def load_inventory_game_scripts(inv_path: Path) -> Set[Tuple[str, str]]:
    with open(inv_path, "r", encoding="utf-8") as f:
        inv = json.load(f)

    game_scripts = set()
    for agent, data in inv["agents"].items():
        for fname, fdata in data["files"].items():
            for fn in fdata["functions"]:
                if fn["category"] == "game":
                    game_scripts.add((agent, fn["name"]))
    return game_scripts

def parse_covered_scripts(scenarios_path: Path) -> Tuple[int, Set[Tuple[str, str]]]:
    with open(scenarios_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match scenarios by ### SCEN-XXX
    scenario_matches = re.findall(r"^###\s+(SCEN-\d+):", content, flags=re.MULTILINE)
    total_scenarios = len(scenario_matches)

    # Extract all `- `agent::game_...``
    covered_items = set()
    item_re = re.compile(r"-\s+`([a-zA-Z0-9_]+)::(game_[a-zA-Z0-9_]+)`")
    for m in item_re.finditer(content):
        agent = m.group(1)
        fn = m.group(2)
        covered_items.add((agent, fn))

    return total_scenarios, covered_items

def main():
    if not INV_PATH.exists():
        print(f"Error: Inventory file {INV_PATH} not found.", file=sys.stderr)
        sys.exit(1)
    if not SCENARIOS_MD.exists():
        print(f"Error: Scenarios file {SCENARIOS_MD} not found.", file=sys.stderr)
        sys.exit(1)

    inv_scripts = load_inventory_game_scripts(INV_PATH)
    total_scenarios, covered_scripts = parse_covered_scripts(SCENARIOS_MD)

    missing = sorted(inv_scripts - covered_scripts)

    print("=== Scenario Coverage Report ===")
    print(f"Total scenarios defined: {total_scenarios}")
    print(f"Total inventory game scripts: {len(inv_scripts)}")
    print(f"Total game scripts covered  : {len(covered_scripts)}")
    print(f"Uncovered game scripts      : {len(missing)}")

    if missing:
        print("\nMissing scripts detail:")
        for agent, fn in missing[:20]:
            print(f"  - {agent}::{fn}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
        print("\nResult: FAIL (incomplete coverage)")
        sys.exit(1)
    else:
        print("\nResult: PASS (100% coverage, 0 uncovered)")
        sys.exit(0)

if __name__ == "__main__":
    main()
