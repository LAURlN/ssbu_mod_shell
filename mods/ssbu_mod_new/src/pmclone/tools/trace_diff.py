"""Trace diff tool for comparing vanilla and clone Smash Ultimate .trace.csv files.
"""

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


EXPECTED_COLUMNS = [
    "frame",
    "slot",
    "object",
    "kind",
    "status",
    "situation",
    "motion",
    "motion_frame",
    "motion_rate",
    "pos_x",
    "pos_y",
    "lr",
    "speed",
    "damage",
    "hitstop",
    "hitboxes",
    "work",
]

FLOAT_COLUMNS = {
    "motion_frame",
    "motion_rate",
    "pos_x",
    "pos_y",
    "lr",
    "damage",
}

INT_COLUMNS = {
    "frame",
    "slot",
    "kind",
    "status",
    "situation",
    "hitstop",
}

STRING_COLUMNS = {
    "object",
    "motion",
}


class ParseError(Exception):
    def __init__(self, filename: str, line_num: int, message: str):
        super().__init__(f"Malformed input in {filename} at line {line_num}: {message}")
        self.filename = filename
        self.line_num = line_num
        self.message = message


def values_equal(left, right, tolerance):
    """Preserve the recorder's representation; numerical tolerance is opt-in."""
    if left == right:
        return True
    if tolerance <= 0:
        return False
    try:
        a, b = float(left), float(right)
        return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance
    except (ValueError, TypeError):
        return False


def parse_speed(speed_str: str, filename: str, line_num: int) -> Dict[str, Tuple[float, float]]:
    speed_dict = {}
    cleaned = speed_str.strip().rstrip(";")
    if not cleaned:
        return speed_dict
    entries = cleaned.split(";")
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("=")
        if len(parts) != 2:
            raise ParseError(filename, line_num, f"Invalid speed format: '{entry}'")
        name = parts[0].strip()
        coords = parts[1].strip().split(":")
        if len(coords) != 2:
            raise ParseError(filename, line_num, f"Invalid speed coordinates: '{parts[1]}'")
        try:
            vx = float(coords[0])
            vy = float(coords[1])
        except ValueError:
            raise ParseError(filename, line_num, f"Non-numeric speed coordinates in '{entry}'")
        if not name or name in speed_dict:
            raise ParseError(filename, line_num, 'Empty or duplicate speed name')
        speed_dict[name] = (coords[0], coords[1])
    return speed_dict


def parse_hitboxes(hb_str: str, filename: str, line_num: int) -> Dict[Tuple[int, int], Dict[str, float]]:
    hb_dict = {}
    cleaned = hb_str.strip().rstrip(";")
    if not cleaned:
        return hb_dict
    entries = cleaned.split(";")
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("/")
        if len(parts) != 14:
            raise ParseError(filename, line_num, f"Hitbox entry must have 14 fields, found {len(parts)} in '{entry}'")
        try:
            hid = int(parts[0])
            hpart = int(parts[1])
            fields = {
                "damage": float(parts[2]),
                "angle": float(parts[3]),
                "kbg": float(parts[4]),
                "fkb": float(parts[5]),
                "bkb": float(parts[6]),
                "size": float(parts[7]),
                "x": float(parts[8]),
                "y": float(parts[9]),
                "z": float(parts[10]),
                "x2": float(parts[11]),
                "y2": float(parts[12]),
                "z2": float(parts[13]),
            }
        except ValueError as err:
            raise ParseError(filename, line_num, f"Invalid hitbox field value: {err}")
        if (hid, hpart) in hb_dict:
            raise ParseError(filename, line_num, 'Duplicate hitbox id/part')
        hb_dict[(hid, hpart)] = dict(zip(fields, parts[2:]))
    return hb_dict


def parse_work(work_str: str, filename: str, line_num: int) -> Dict[str, str]:
    work_dict = {}
    cleaned = work_str.strip().rstrip(";")
    if not cleaned:
        return work_dict
    entries = cleaned.split(";")
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("=", 1)
        if len(parts) != 2:
            raise ParseError(filename, line_num, f"Invalid work format: '{entry}'")
        key = parts[0].strip()
        val = parts[1].strip()
        if not key or key in work_dict:
            raise ParseError(filename, line_num, 'Empty or duplicate work key')
        work_dict[key] = val
    return work_dict


def parse_trace_file(filepath: str) -> Dict[Tuple[int, int, str], Dict[str, Any]]:
    rows: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    try:
        f = open(filepath, "r", encoding="utf-8")
    except Exception as err:
        raise ParseError(filepath, 0, f"Cannot open file: {err}")

    with f:
        header_found = False
        recorder_file = False
        complete = False
        completed_counts = None
        col_indices: Dict[str, int] = {}
        for line_num, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                recorder_file |= line.startswith('# pmclone_trace v')
                if line.startswith('# complete '):
                    if complete:
                        raise ParseError(filepath, line_num, 'Duplicate completion footer')
                    try:
                        fields = dict(item.split('=') for item in line.split()[2:])
                        completed_counts = (int(fields['frames']), int(fields['rows']))
                    except (ValueError, KeyError):
                        raise ParseError(filepath, line_num, 'Malformed completion footer')
                    complete = True
                if line.startswith('# invalid '):
                    raise ParseError(filepath, line_num, line)
                continue

            if complete:
                raise ParseError(filepath, line_num, 'State row after completion footer')

            # Parse row with csv reader
            reader = csv.reader([raw_line])
            try:
                row = next(reader)
            except Exception as err:
                raise ParseError(filepath, line_num, f"CSV parsing error: {err}")

            if not header_found:
                col_indices = {col.strip(): idx for idx, col in enumerate(row)}
                missing_cols = [c for c in EXPECTED_COLUMNS if c not in col_indices]
                if missing_cols:
                    raise ParseError(filepath, line_num, f"Header missing required columns: {missing_cols}")
                header_found = True
                continue

            if len(row) != len(col_indices):
                raise ParseError(filepath, line_num, f"Expected {len(col_indices)} fields, found {len(row)}")

            parsed_row: Dict[str, Any] = {}
            for col in EXPECTED_COLUMNS:
                raw_val = row[col_indices[col]].strip()
                if col in INT_COLUMNS:
                    try:
                        parsed_row[col] = int(raw_val)
                    except ValueError:
                        raise ParseError(filepath, line_num, f"Column '{col}' must be int, got '{raw_val}'")
                elif col in FLOAT_COLUMNS:
                    try:
                        float(raw_val)  # Validate without discarding signed zero/NaN text.
                        parsed_row[col] = raw_val
                    except ValueError:
                        raise ParseError(filepath, line_num, f"Column '{col}' must be float, got '{raw_val}'")
                elif col == "speed":
                    parsed_row[col] = parse_speed(raw_val, filepath, line_num)
                elif col == "hitboxes":
                    parsed_row[col] = parse_hitboxes(raw_val, filepath, line_num)
                elif col == "work":
                    parsed_row[col] = parse_work(raw_val, filepath, line_num)
                else:
                    parsed_row[col] = raw_val

            key = (parsed_row["frame"], parsed_row["slot"], parsed_row["object"])
            if key in rows:
                raise ParseError(filepath, line_num, f"Duplicate row for (frame={key[0]}, slot={key[1]}, object='{key[2]}')")
            rows[key] = parsed_row

    if not header_found:
        raise ParseError(filepath, 0, "No header row found")
    if not rows:
        raise ParseError(filepath, 0, 'No state rows found')
    if recorder_file and not complete:
        raise ParseError(filepath, 0, 'Recorder trace lacks completion footer (interrupted or old build)')
    if completed_counts is not None:
        frames, count = completed_counts
        observed_frames = {key[0] for key in rows}
        if count != len(rows) or frames != len(observed_frames) or min(observed_frames) != 0 or max(observed_frames) != frames - 1:
            raise ParseError(filepath, 0, 'Completion counts disagree with rows or frames are missing')

    return rows


def diff_traces(
    vanilla_rows: Dict[Tuple[int, int, str], Dict[str, Any]],
    clone_rows: Dict[Tuple[int, int, str], Dict[str, Any]],
    ignore_columns: Set[str],
    float_tol: float = 0.0,
) -> List[Dict[str, Any]]:
    differences: List[Dict[str, Any]] = []
    all_keys = sorted(set(vanilla_rows.keys()) | set(clone_rows.keys()))

    for key in all_keys:
        frame, slot, obj = key
        if key not in vanilla_rows:
            differences.append({
                "frame": frame,
                "slot": slot,
                "object": obj,
                "field": "row",
                "message": f"frame {frame} slot {slot} {obj}: extra in clone",
            })
            continue
        if key not in clone_rows:
            differences.append({
                "frame": frame,
                "slot": slot,
                "object": obj,
                "field": "row",
                "message": f"frame {frame} slot {slot} {obj}: missing in clone",
            })
            continue

        v_row = vanilla_rows[key]
        c_row = clone_rows[key]

        for col in EXPECTED_COLUMNS:
            if col in ignore_columns:
                continue

            v_val = v_row[col]
            c_val = c_row[col]

            if col in INT_COLUMNS or col in STRING_COLUMNS:
                if v_val != c_val:
                    differences.append({
                        "frame": frame,
                        "slot": slot,
                        "object": obj,
                        "field": col,
                        "message": f"frame {frame} slot {slot} {obj}: {col} {v_val} != {c_val}",
                    })
            elif col in FLOAT_COLUMNS:
                if not values_equal(v_val, c_val, float_tol):
                    differences.append({
                        "frame": frame,
                        "slot": slot,
                        "object": obj,
                        "field": col,
                        "message": f"frame {frame} slot {slot} {obj}: {col} {v_val} != {c_val}",
                    })
            elif col == "speed":
                # Compare speed dicts
                all_energies = sorted(set(v_val.keys()) | set(c_val.keys()))
                for e in all_energies:
                    if e not in v_val:
                        differences.append({
                            "frame": frame,
                            "slot": slot,
                            "object": obj,
                            "field": "speed",
                            "message": f"frame {frame} slot {slot} {obj}: speed energy '{e}' present in clone only",
                        })
                    elif e not in c_val:
                        differences.append({
                            "frame": frame,
                            "slot": slot,
                            "object": obj,
                            "field": "speed",
                            "message": f"frame {frame} slot {slot} {obj}: speed energy '{e}' present in vanilla only",
                        })
                    else:
                        vx1, vy1 = v_val[e]
                        vx2, vy2 = c_val[e]
                        if not values_equal(vx1, vx2, float_tol):
                            differences.append({
                                "frame": frame,
                                "slot": slot,
                                "object": obj,
                                "field": "speed",
                                "message": f"frame {frame} slot {slot} {obj}: speed '{e}' x {vx1} != {vx2}",
                            })
                        if not values_equal(vy1, vy2, float_tol):
                            differences.append({
                                "frame": frame,
                                "slot": slot,
                                "object": obj,
                                "field": "speed",
                                "message": f"frame {frame} slot {slot} {obj}: speed '{e}' y {vy1} != {vy2}",
                            })
            elif col == "hitboxes":
                # Compare hitboxes dicts
                all_hb = sorted(set(v_val.keys()) | set(c_val.keys()))
                for hb_key in all_hb:
                    hid, hpart = hb_key
                    if hb_key not in v_val:
                        differences.append({
                            "frame": frame,
                            "slot": slot,
                            "object": obj,
                            "field": "hitboxes",
                            "message": f"frame {frame} slot {slot} {obj}: hitboxes id={hid} part={hpart} present in clone only",
                        })
                    elif hb_key not in c_val:
                        differences.append({
                            "frame": frame,
                            "slot": slot,
                            "object": obj,
                            "field": "hitboxes",
                            "message": f"frame {frame} slot {slot} {obj}: hitboxes id={hid} part={hpart} present in vanilla only",
                        })
                    else:
                        hb_v = v_val[hb_key]
                        hb_c = c_val[hb_key]
                        for fld in ["damage", "angle", "kbg", "fkb", "bkb", "size", "x", "y", "z", "x2", "y2", "z2"]:
                            val_v = hb_v[fld]
                            val_c = hb_c[fld]
                            if not values_equal(val_v, val_c, float_tol):
                                differences.append({
                                    "frame": frame,
                                    "slot": slot,
                                    "object": obj,
                                    "field": "hitboxes",
                                    "message": f"frame {frame} slot {slot} {obj}: hitboxes id={hid} {fld} {val_v} != {val_c}",
                                })
            elif col == "work":
                all_work = sorted(set(v_val.keys()) | set(c_val.keys()))
                for w_key in all_work:
                    if w_key not in v_val:
                        differences.append({
                            "frame": frame,
                            "slot": slot,
                            "object": obj,
                            "field": "work",
                            "message": f"frame {frame} slot {slot} {obj}: work '{w_key}' present in clone only",
                        })
                    elif w_key not in c_val:
                        differences.append({
                            "frame": frame,
                            "slot": slot,
                            "object": obj,
                            "field": "work",
                            "message": f"frame {frame} slot {slot} {obj}: work '{w_key}' present in vanilla only",
                        })
                    else:
                        val_v = v_val[w_key]
                        val_c = c_val[w_key]
                        is_diff = not values_equal(val_v, val_c, float_tol)
                        if is_diff:
                            differences.append({
                                "frame": frame,
                                "slot": slot,
                                "object": obj,
                                "field": "work",
                                "message": f"frame {frame} slot {slot} {obj}: work '{w_key}' {val_v} != {val_c}",
                            })

    return differences


def parse_ignore_arg(ignore_args: Optional[List[str]]) -> Set[str]:
    if ignore_args is None:
        return {"kind"}
    res = set()
    for arg in ignore_args:
        if not arg or arg.strip().lower() in ("", "none"):
            continue
        for item in arg.split(","):
            cleaned = item.strip()
            if cleaned:
                res.add(cleaned)
    return res


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Diff vanilla vs clone Smash Ultimate trace files.")
    parser.add_argument("vanilla", help="Path to vanilla .trace.csv")
    parser.add_argument("clone", help="Path to clone .trace.csv")
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=None,
        help="Columns to ignore (default: kind). Pass empty string or none to check all columns.",
    )
    parser.add_argument("--float-tol", type=float, default=0.0, help="Absolute tolerance for float comparisons (default: 0.0)")
    parser.add_argument("--max-report", type=int, default=50, help="Maximum number of differences to display (default: 50)")
    parser.add_argument("--json", dest="json_out", default=None, help="Path to write JSON diff report")

    args = parser.parse_args(argv)
    if not math.isfinite(args.float_tol) or args.float_tol < 0:
        parser.error('--float-tol must be finite and non-negative')

    try:
        vanilla_rows = parse_trace_file(args.vanilla)
        clone_rows = parse_trace_file(args.clone)
    except ParseError as err:
        sys.stderr.write(f"{err}\n")
        return 2

    ignore_set = parse_ignore_arg(args.ignore)
    diffs = diff_traces(vanilla_rows, clone_rows, ignore_set, float_tol=args.float_tol)

    identical = len(diffs) == 0
    first_diverging_frame = None if identical else min(d["frame"] for d in diffs)

    if args.json_out:
        json_data = {
            "identical": identical,
            "first_diverging_frame": first_diverging_frame,
            "difference_count": len(diffs),
            "differences": diffs,
        }
        try:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)
        except Exception as err:
            sys.stderr.write(f"Error writing JSON report: {err}\n")
            return 2

    if identical:
        print("IDENTICAL")
        return 0
    else:
        print(f"FIRST DIVERGING FRAME: {first_diverging_frame}")
        shown = diffs[: args.max_report]
        print(f"Differences ({len(shown)} of {len(diffs)}):")
        for d in shown:
            print(f"  {d['message']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
