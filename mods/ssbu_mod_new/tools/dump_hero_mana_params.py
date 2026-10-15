#!/usr/bin/env python
"""Decode Hero's mana (SP) parameters from a pinned `vl.prc`.

Purpose: print the exact Hash40 keys and numeric values of Hero's SP
parameters (`sp_max`, `sp_recover_frame`, `recover_sp`, `sp_recover_damage_mul`,
`sp_recover_shield_mul`, `sp_special_n1..3`, `sp_special_s1..3`,
`sp_special_hi1..3`) from a `paracobn` PRC file, so owned recipient code can be
given the donor's real numbers instead of invented ones. Labels come from
`dumps/scripts/ParamLabels.csv` when present; the Hash40 key is read from the
file itself, so the result does not depend on the label list being complete.

Usage:
  python tools/dump_hero_mana_params.py <path/to/vl.prc> [--json out.json]

Read-only. Tier B: it measures a pinned file and proves nothing about runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

# Parameter names this tool reports, in report order. The Hash40 key of each is
# read from the file, never asserted here.
WANTED = (
    "sp_max",
    "recover_sp",
    "sp_recover_frame",
    "sp_recover_damage_mul",
    "sp_recover_shield_mul",
    "sp_special_n1",
    "sp_special_n2",
    "sp_special_n3",
    "sp_special_s1",
    "sp_special_s2",
    "sp_special_s3",
    "sp_special_hi1",
    "sp_special_hi2",
    "sp_special_hi3",
)

# Paths inside the PRC that may carry a value for a name. `param_private` holds
# the flat SP block; `param_special_n` is a per-level list that repeats the
# neutral prices in its first entry.
SEARCH_PATHS = ("param_private", "param_special_n[0]", "param_special_s[0]")


def load_labels(root: Path) -> dict:
    """Hash40 -> name, from the label CSV if it is present. Optional."""
    csv = root / "dumps" / "scripts" / "ParamLabels.csv"
    labels = {}
    if csv.is_file():
        with csv.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                key, _, name = line.strip().partition(",")
                try:
                    labels[int(key, 16)] = name
                except ValueError:
                    continue
    return labels


def read_prc(path: Path):
    """Return (hashes, root_value) for a paracobn PRC file.

    Mirrors the reader in `tools/prcdump.py` (tier B, same format), but keeps
    the raw hash table so a name can be reported with the key that carries it.
    """
    data = path.read_bytes()
    if data[:8] != b"paracobn":
        raise ValueError("not a paracobn PRC: %s" % path)
    hash_size, ref_size = struct.unpack_from("<II", data, 8)
    hashes = struct.unpack_from("<" + "Q" * (hash_size // 8), data, 16)
    ref_base = 16 + hash_size
    base = ref_base + ref_size

    def read(off: int):
        kind = data[off]
        if kind == 1:
            return bool(data[off + 1]), off + 2
        if kind == 2:
            return struct.unpack_from("<b", data, off + 1)[0], off + 2
        if kind == 3:
            return data[off + 1], off + 2
        if kind == 4:
            return struct.unpack_from("<h", data, off + 1)[0], off + 3
        if kind == 5:
            return struct.unpack_from("<H", data, off + 1)[0], off + 3
        if kind == 6:
            return struct.unpack_from("<i", data, off + 1)[0], off + 5
        if kind == 7:
            return struct.unpack_from("<I", data, off + 1)[0], off + 5
        if kind == 8:
            # Keep full f32 precision: the generated Rust table copies the
            # exact f32 bits of the donor value.
            return struct.unpack_from("<f", data, off + 1)[0], off + 5
        if kind == 9:
            idx = struct.unpack_from("<I", data, off + 1)[0]
            return ("H", hashes[idx]), off + 5
        if kind == 10:
            rel = struct.unpack_from("<I", data, off + 1)[0]
            end = data.index(b"\0", ref_base + rel)
            return data[ref_base + rel:end].decode(), off + 5
        if kind == 11:
            count = struct.unpack_from("<I", data, off + 1)[0]
            offsets = struct.unpack_from("<" + "I" * count, data, off + 5)
            return [read(off + o)[0] for o in offsets], off + 5 + 4 * count
        if kind == 12:
            count, rel = struct.unpack_from("<II", data, off + 1)
            out = {}
            for i in range(count):
                hi, po = struct.unpack_from("<II", data, ref_base + rel + 8 * i)
                out[hashes[hi]] = read(off + po)[0]
            return out, off + 9
        raise ValueError("unknown PRC type %d at %d" % (kind, off))

    return hashes, read(base)[0]


def name_keys(node, labels, keymap):
    """Return a copy of a decoded PRC value with Hash40 keys resolved to names.

    `keymap` is filled with name -> Hash40 for every key resolved, so a value
    can be reported by the name and by the key the donor looks it up with.
    """
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if isinstance(key, int):
                name = labels.get(key, "0x%09x" % key)
                keymap.setdefault(name, key)
                out[name] = name_keys(value, labels, keymap)
            else:
                out[key] = name_keys(value, labels, keymap)
        return out
    if isinstance(node, list):
        return [name_keys(v, labels, keymap) for v in node]
    return node


def collect(node, name, hits, where=""):
    """Walk a decoded PRC value and record (name -> (hash, value, path))."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == name:
                hits.append((key, value, where))
            collect(value, name, hits, "%s%s/" % (where, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            collect(value, name, hits, "%s[%d]/" % (where, index))


def synthetic_prc() -> bytes:
    """A tiny in-memory `paracobn` with two float keys, for the smoke test.

    Built by hand rather than shipped as a fixture, so the smoke test cannot rot
    against a copy of the reader it is meant to check.
    """
    keys = (0x0634FFDA6C, 0x0D3FD79C7D)  # sp_max, sp_special_n1
    hashes = b"".join(struct.pack("<Q", k) for k in keys)
    hash_size = len(hashes)
    count = len(keys)
    # Value block: two type-8 (f32) cells of five bytes each.
    values = b"".join(bytes([8]) + struct.pack("<f", v) for v in (100.0, 6.0))
    ref_base = 16 + hash_size
    ref_size = 8 * count
    dict_head = bytes([12]) + struct.pack("<II", count, 0)
    out = bytearray()
    out += b"paracobn" + struct.pack("<II", hash_size, ref_size) + hashes
    ref_base_abs = len(out)
    assert ref_base_abs == ref_base
    for i in range(count):
        out += struct.pack("<II", i, 9 + 5 * i)  # hash index, offset from the dict head
    assert len(out) - ref_base_abs == ref_size
    out += dict_head + values
    return bytes(out)


def smoke() -> int:
    """Self-test: the reader must decode the synthetic file it is handed."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "synthetic.prc"
        path.write_bytes(synthetic_prc())
        labels = {0x0634FFDA6C: "sp_max", 0x0D3FD79C7D: "sp_special_n1"}
        _hashes, root = read_prc(path)
        keymap = {}
        root = name_keys(root, labels, keymap)
    failures = []
    if not isinstance(root, dict):
        failures.append("root is %s, not a dict" % type(root).__name__)
    else:
        for name, want in (("sp_max", 100.0), ("sp_special_n1", 6.0)):
            got = root.get(name)
            if got != want:
                failures.append("%s: got %r, want %r" % (name, got, want))
            if name not in keymap:
                failures.append("%s: no Hash40 recovered" % name)
    if failures:
        for line in failures:
            print("FAIL\t%s" % line, file=sys.stderr)
        return 1
    print("PASS\tsynthetic paracobn decoded: sp_max=100.0 sp_special_n1=6.0 with keys")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prc", nargs="?")
    ap.add_argument("--json", help="write the report to this path")
    ap.add_argument("--mod-root", default=".", help="mod repo root for labels")
    ap.add_argument("--smoke", action="store_true",
                    help="self-test the reader on a synthetic PRC and exit")
    args = ap.parse_args()

    if args.smoke:
        return smoke()
    if not args.prc:
        ap.error("a .prc path is required unless --smoke is given")

    prc = Path(args.prc)
    if not prc.is_file():
        print("MISSING\t%s" % prc, file=sys.stderr)
        return 1
    labels = load_labels(Path(args.mod_root))
    hashes, root = read_prc(prc)
    # The PRC stores Hash40 keys, not names. Resolve them so a value can be
    # reported by name and by the key the donor looks it up with.
    keymap = {}
    root = name_keys(root, labels, keymap)

    digest = hashlib.sha256(prc.read_bytes()).hexdigest()
    report = {
        "tool": "tools/dump_hero_mana_params.py v1.0.0",
        "tier": "B",
        "source_file": str(prc),
        "source_sha256": digest,
        "params": {},
        "notes": (
            "Values are read from the pinned donor PRC. A hash40 is the key the "
            "donor looks the value up by at runtime; nothing here proves the "
            "donor reads it on any particular path."
        ),
    }

    print("# source %s" % prc)
    print("# sha256 %s" % digest)
    for name in WANTED:
        hits = []
        collect(root, name, hits)
        # `param_special_n[0]` repeats the neutral prices; prefer the flat
        # `param_private` block and record the duplicate as a cross-check.
        primary = None
        for key, value, where in hits:
            if where == "param_private/":
                primary = (key, value, where)
                break
        if primary is None and hits:
            primary = hits[0]
        if primary is None:
            print("%-24s NOT FOUND" % name)
            report["params"][name] = None
            continue
        key, value, where = primary
        hash_hex = keymap.get(name)
        if hash_hex is None:
            print("%-24s found at %s but no Hash40 in the file" % (name, where))
            report["params"][name] = None
            continue
        entry = {
            "name": name,
            "hash40": "0x%09x" % hash_hex,
            "value": value,
            "path": where.rstrip("/"),
        }
        report["params"][name] = entry
        print("%-24s %s  %-8s  %s" % (name, entry["hash40"], value, entry["path"]))
        for _k, v, w in [h for h in hits if h[2] != where]:
            agree = "agrees" if v == value else "DIFFERS"
            print(
                "%-24s   cross-check %-8s %s (%s)"
                % (name, v, w.rstrip("/"), agree)
            )

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("# wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
