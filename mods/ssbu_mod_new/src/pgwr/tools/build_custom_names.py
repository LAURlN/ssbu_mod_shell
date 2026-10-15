"""Build and validate costume slot name overrides for Pyra/G&W and Mythra (c06 & c07).

Configures:
- c06: 'Ursula' (uppercase 'URSULA' for nam_chr1 banner)
- c07: 'Wilhelmine' (uppercase 'WILHELMINE' for nam_chr1 banner)

Applies to both Mythra and G&W (Pyra) across:
- eflame_first (Pyra CSS starter)
- eflame_only (Pyra solo / in-game)
- elight_first (Mythra CSS starter)
- elight_only (Mythra solo / in-game)
- element (transformation pair)

Routes n06_index -> 6 and n07_index -> 7 in ui_chara_db.prc, preserving all
other rows, fields, and vanilla slots c00-c05 unmodified.
Generates ui/message/msg_name.xmsbt with 40 entries across categories 0..3.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

# Ensure src/pgwr/tools is on path for prc module
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import prc

ROOT = HERE.parents[2]
EXPORT = ROOT / "dumps/arc"

COSTUMES = {'c06': 'c06', 'c07': 'c07'}
COSTUME_NAMES = {'c06': 'Ursula', 'c07': 'Wilhelmine'}
TARGET_NAME_IDS = ('eflame_first', 'eflame_only', 'elight_first', 'elight_only', 'element')


def sha256(data_or_path: bytes | Path) -> str:
    if isinstance(data_or_path, Path):
        return hashlib.sha256(data_or_path.read_bytes()).hexdigest()
    return hashlib.sha256(data_or_path).hexdigest()


def generate_xmsbt_tree() -> ET.Element:
    root = ET.Element('xmsbt')
    for slot in sorted(COSTUMES):
        name = COSTUME_NAMES[slot]
        name_upper = name.upper()
        for name_id in TARGET_NAME_IDS:
            for category in range(4):
                entry = ET.SubElement(root, 'entry', label=f'nam_chr{category}_{slot[1:]}_{name_id}')
                text = ET.SubElement(entry, 'text')
                text.text = name_upper if category == 1 else name
    return root


def write_xmsbt(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    root = generate_xmsbt_tree()
    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ', level=0)
    tree.write(path, encoding='utf-8', xml_declaration=True)
    # Ensure newline at end of file
    text = path.read_text(encoding='utf-8')
    if not text.endswith('\n'):
        path.write_text(text + '\n', encoding='utf-8')
    return sha256(path)


def generate_name_database(export_dir: Path | None = None) -> tuple[bytes, list[str]]:
    base_export = export_dir or EXPORT
    rel = 'ui/param/database/ui_chara_db.prc'
    src_file = base_export / rel
    if not src_file.exists():
        raise FileNotFoundError(f"Source database not found: {src_file}")

    tree = prc.read(src_file)
    original = prc.read(src_file)
    changes = []
    target_set = {('str', x) for x in TARGET_NAME_IDS}

    for _, rows in tree[1]:
        if rows[0] != 'list':
            continue
        for row in rows[1]:
            fields = dict(row[1])
            if fields.get(prc.hash40('name_id')) not in target_set:
                continue
            for slot in COSTUMES:
                key = prc.hash40(f'n{slot[1:]}_index')
                if key not in fields:
                    raise KeyError(f"Missing name index {slot} in {fields.get(prc.hash40('name_id'))}")
                row[1][:] = [(k, ('u8', int(slot[1:]))) if k == key else (k, v)
                             for k, v in row[1]]
                changes.append(f"{fields[prc.hash40('name_id')][1]}/{slot}")

    expected_change_count = len(TARGET_NAME_IDS) * len(COSTUMES)
    if len(changes) != expected_change_count:
        raise ValueError(f"Expected {expected_change_count} changes, got {len(changes)}: {changes}")

    # Isolation check: only n06_index and n07_index changed on target entries
    for (_, old_rows), (_, new_rows) in zip(original[1], tree[1]):
        for old, new in zip(old_rows[1], new_rows[1]):
            name = dict(old[1]).get(prc.hash40('name_id'))
            allowed = {prc.hash40('n06_index'), prc.hash40('n07_index')} if name in target_set else set()
            diff_old = [(k, v) for k, v in old[1] if k not in allowed]
            diff_new = [(k, v) for k, v in new[1] if k not in allowed]
            if diff_old != diff_new:
                raise ValueError(f"Unrelated field changed in {name}")

    encoded = prc.write(tree)
    return encoded, changes


def write_name_database(out_path: Path, export_dir: Path | None = None) -> tuple[str, list[str]]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data, changes = generate_name_database(export_dir)
    out_path.write_bytes(data)
    # Verify round-trip readability
    re_read = prc.read(out_path)
    if prc.write(re_read) != data:
        raise ValueError("PRC round-trip verification failed after write")
    return sha256(data), changes


def check(xmsbt_path: Path, prc_path: Path) -> bool:
    """Smoke test: verify XMSBT and PRC overrides."""
    if not xmsbt_path.exists():
        print(f"FAIL: {xmsbt_path} does not exist", file=sys.stderr)
        return False
    if not prc_path.exists():
        print(f"FAIL: {prc_path} does not exist", file=sys.stderr)
        return False

    # Check XMSBT
    root = ET.parse(xmsbt_path).getroot()
    if root.tag != 'xmsbt':
        print(f"FAIL: {xmsbt_path} root tag is not 'xmsbt'", file=sys.stderr)
        return False

    expected_xmsbt = {
        f'nam_chr{category}_{slot[1:]}_{name_id}':
        COSTUME_NAMES[slot].upper() if category == 1 else COSTUME_NAMES[slot]
        for slot in COSTUMES for category in range(4)
        for name_id in TARGET_NAME_IDS
    }
    entries = root.findall('entry')
    actual_xmsbt = {e.get('label'): e.findtext('text') for e in entries}

    if len(entries) != len(expected_xmsbt):
        print(f"FAIL: XMSBT entry count mismatch: expected {len(expected_xmsbt)}, got {len(entries)}", file=sys.stderr)
        return False
    if actual_xmsbt != expected_xmsbt:
        print("FAIL: XMSBT entries content mismatch", file=sys.stderr)
        return False

    # Check PRC
    tree = prc.read(prc_path)
    target_set = {('str', x) for x in TARGET_NAME_IDS}
    found = {}
    for _, rows in tree[1]:
        if rows[0] != 'list':
            continue
        for row in rows[1]:
            fields = dict(row[1])
            nid = fields.get(prc.hash40('name_id'))
            if nid in target_set:
                nid_str = nid[1]
                n06 = fields.get(prc.hash40('n06_index'))
                n07 = fields.get(prc.hash40('n07_index'))
                found[nid_str] = (n06, n07)

    for nid in TARGET_NAME_IDS:
        if nid not in found:
            print(f"FAIL: Missing entry {nid} in {prc_path}", file=sys.stderr)
            return False
        n06, n07 = found[nid]
        if n06 != ('u8', 6) or n07 != ('u8', 7):
            print(f"FAIL: Unexpected indices for {nid}: n06={n06}, n07={n07}", file=sys.stderr)
            return False

    print(f"PASS: {xmsbt_path} (40 entries) and {prc_path} (10 index routes) verified successfully.")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate existing files')
    parser.add_argument('--xmsbt', type=Path, default=HERE.parent / 'ui/message/msg_name.xmsbt',
                        help='Output or check path for msg_name.xmsbt')
    parser.add_argument('--prc', type=Path, default=ROOT / 'builds/pgwr/staged_names/ui/param/database/ui_chara_db.prc',
                        help='Output or check path for ui_chara_db.prc')
    args = parser.parse_args()

    if args.check:
        ok = check(args.xmsbt, args.prc)
        sys.exit(0 if ok else 1)

    print("Generating custom name overrides...")
    xmsbt_hash = write_xmsbt(args.xmsbt)
    print(f"Wrote XMSBT to {args.xmsbt} (sha256: {xmsbt_hash})")

    staged_xmsbt = ROOT / 'builds/pgwr/staged_names/ui/message/msg_name.xmsbt'
    staged_xmsbt.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(args.xmsbt, staged_xmsbt)
    print(f"Staged XMSBT to {staged_xmsbt} (sha256: {sha256(staged_xmsbt)})")

    prc_hash, changes = write_name_database(args.prc)
    print(f"Wrote PRC to {args.prc} (sha256: {prc_hash}) with {len(changes)} routes: {changes}")

    ok = check(args.xmsbt, args.prc)
    ok_staged = check(staged_xmsbt, args.prc)
    print(f"Verification: {'SUCCESS' if (ok and ok_staged) else 'FAILED'}")
    sys.exit(0 if (ok and ok_staged) else 1)


if __name__ == '__main__':
    main()
