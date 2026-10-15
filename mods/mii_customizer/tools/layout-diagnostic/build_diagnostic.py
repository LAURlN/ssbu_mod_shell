#!/usr/bin/env python3
"""layout-diagnostic: build ONE reproducible layout-only diagnostic archive.

Purpose
-------
Produce a single offline diagnostic that a later coordinator package can use to
ask one question: *does the game's Mii special editor load a layout asset we
changed?* The only change is that the two scale floats of the ``prt1`` node
named ``set_special_item_00`` in the Mii special editor layout are set to 75% of
their original values, so the first special-selection row should render smaller.

What this tool does, in order:

1. Parses the SARC archive with its own reader and extracts exactly one member.
2. Refuses unless the archive and the member match their pinned sha256 values,
   so a changed game file can never be silently patched.
3. Cross-checks the extracted member against the separately extracted `.bflyt`
   input, and against `tools/bflyt-inspect`, then re-reads the located bytes
   locally before touching anything.
4. Locates the `prt1` node by name and refuses unless there is exactly one
   match, the scale is finite and positive, and the structure is the one this
   tool models.
5. Writes the same-length payload, feeds it through the existing
   `tools/sarc-layout` same-length replacement, and also writes an unchanged
   control archive through `tools/sarc-layout`'s byte-exact rebuild.
6. Verifies the result independently: member count, header metadata, every
   member offset, exactly one changed member, and that every differing byte of
   the archive lies inside one of the two scale fields. It then reparses both
   layouts and compares every other parsed field.

Everything it cannot establish it refuses. It never guesses an offset.

Scope limits, stated because they matter:
  * This is a diagnostic, not a customization feature. It changes no row name,
    count, position, selector membership, child reference, animation, text key,
    Lua or native behaviour.
  * Whether the row scale is even visible is UNVERIFIED: an animation may
    overwrite scale at runtime. That is exactly what the diagnostic is for.
  * Nothing here was run on hardware or in an emulator. Tier B, offline only.

Usage (from the workspace root; `python` works, `python3` does not on Windows):

    python mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py
    python mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import struct
import subprocess
import sys

# ---------------------------------------------------------------------------
# Pinned inputs. A different hash means a different game file, and this tool
# refuses rather than patching an unrecognised layout.
# ---------------------------------------------------------------------------

DEFAULT_ARCHIVE = "gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc"
DEFAULT_MEMBER = "blyt/make_mii_special.bflyt"
DEFAULT_ARCHIVE_SHA256 = "5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945"
DEFAULT_MEMBER_SHA256 = "a63cbacc09a9264ff07ac83c1b765dd0caeeaa1afd92bdb58297f774a3c0b3e8"
DEFAULT_EXTRACTED = "gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_special/blyt/make_mii_special.bflyt"
DEFAULT_PART = "set_special_item_00"
DEFAULT_FACTOR = 0.75
DEFAULT_OUT_DIR = "gamedata/mii_customizer/P2-LAYOUT-PATCH"

# The two fields this tool is allowed to touch, as offsets inside a prt1 payload.
# Measured in P2-LAYOUT-STRUCTURE; re-derived and re-checked locally below.
SCALE_OFFSETS = (60, 64)
SCALE_COMPONENTS = ("scale_x", "scale_y")

# prt1 payload structure this tool models (P2-LAYOUT-STRUCTURE, tier B).
PRT1_NAME_OFFSET = 4
PRT1_NAME_LEN = 32
PRT1_NODE_TYPE_OFFSET = 0
PRT1_NODE_TYPE = 3
PRT1_XY_OFFSET = 36
PRT1_EXTENT_OFFSET = 68
PRT1_CHILD_COUNT_OFFSET = 76
PRT1_HEADER_LEN = 78
PRT1_CHILD_SIZE = 40

FLYT_MAGIC = b"FLYT"
FLYT_HEADER_MIN = 0x14
FLYT_FILE_SIZE_OFF = 0x0C
FLYT_BLOCK_COUNT_OFF = 0x10

SARC_MAGIC = b"SARC"
SARC_HEADER_SIZE = 0x14
SARC_SFAT_HEADER_SIZE = 0x0C
SARC_ENTRY_SIZE = 0x10
SARC_NAME_TABLE_HEADER_SIZE = 0x08
SARC_NAME_ATTRIBUTE_BIT = 0x01000000
SARC_NAME_OFFSET_MASK = 0x00FFFFFF
SARC_BYTE_ORDER_LE_BE = 0xFFFE

COMPRESSED_MAGICS = (
    (b"Yaz0", "Yaz0 compressed SARC"),
    (b"\x28\xb5\x2f\xfd", "Zstd compressed SARC"),
    (b"YAZR", "YazR compressed SARC"),
)

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")
)
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
SARC_TOOL = os.path.join(os.path.dirname(TOOLS_DIR), "sarc-layout", "sarc_layout.py")
BFLYT_TOOL = os.path.join(os.path.dirname(TOOLS_DIR), "bflyt-inspect", "bflyt_inspect.py")


class Refusal(Exception):
    """A refusal. The message states what was rejected and why."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(path: str, label: str) -> bytes:
    if not os.path.isabs(path):
        path = os.path.join(REPO_ROOT, path)
    if not path.startswith(REPO_ROOT + os.sep):
        raise Refusal("refusing to read outside the workspace: %s" % path)
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError as exc:
        raise Refusal("cannot read %s %s: %s" % (label, path, exc))


# ---------------------------------------------------------------------------
# Independent SARC reader (written here so the extraction does not validate the
# archive against the tool that will later write it).
# ---------------------------------------------------------------------------


def sarc_name_hash(name: str, key: int) -> int:
    h = 0
    for ch in name:
        h = (h * key + ord(ch)) & 0xFFFFFFFF
    return h


def parse_sarc(raw: bytes, label: str) -> dict:
    """Parse an uncompressed little-endian SARC, or refuse."""
    if len(raw) < SARC_HEADER_SIZE:
        raise Refusal("%s is %d bytes, too short for a SARC header" % (label, len(raw)))
    for magic, name in COMPRESSED_MAGICS:
        if raw[:4] == magic:
            raise Refusal("%s is a %s; only uncompressed SARC is supported" % (label, name))
    if raw[:4] != SARC_MAGIC:
        raise Refusal("%s does not start with SARC (found %r)" % (label, raw[:4]))

    header_size = struct.unpack_from("<H", raw, 0x04)[0]
    if header_size != SARC_HEADER_SIZE:
        raise Refusal("%s header_size is 0x%x, expected 0x%x" % (label, header_size, SARC_HEADER_SIZE))
    bom_raw = struct.unpack_from("<H", raw, 0x06)[0]
    if struct.unpack_from(">H", raw, 0x06)[0] != SARC_BYTE_ORDER_LE_BE:
        raise Refusal(
            "%s is not the supported little-endian SARC (byte-order field 0x%04x)"
            % (label, bom_raw)
        )
    size_field, data_offset, word_0x10 = struct.unpack_from("<III", raw, 0x08)
    if size_field != len(raw):
        raise Refusal("%s header size field is %d but the file is %d bytes" % (label, size_field, len(raw)))
    if data_offset % 4 or data_offset < SARC_HEADER_SIZE or data_offset > len(raw):
        raise Refusal("%s data_offset 0x%x is not a usable in-file offset" % (label, data_offset))

    if raw[0x14:0x18] != b"SFAT":
        raise Refusal("%s has no SFAT at 0x14 (found %r)" % (label, raw[0x14:0x18]))
    sfat_header_size = struct.unpack_from("<H", raw, 0x18)[0]
    if sfat_header_size != SARC_SFAT_HEADER_SIZE:
        raise Refusal("%s sfat_header_size is 0x%x, expected 0x%x" % (label, sfat_header_size, SARC_SFAT_HEADER_SIZE))
    member_count = struct.unpack_from("<H", raw, 0x1A)[0]
    hash_key = struct.unpack_from("<I", raw, 0x1C)[0]

    table_off = 0x20
    table_end = table_off + member_count * SARC_ENTRY_SIZE
    if table_end > len(raw):
        raise Refusal("%s SFAT table of %d entries runs past the end of the file" % (label, member_count))
    if raw[table_end:table_end + 4] != b"SFNT":
        raise Refusal("%s has no SFNT at 0x%x (found %r)" % (label, table_end, raw[table_end:table_end + 4]))
    name_table = raw[table_end + SARC_NAME_TABLE_HEADER_SIZE:data_offset]

    data_len = len(raw) - data_offset
    members = []
    seen = set()
    for i in range(member_count):
        f0, f1, start, end = struct.unpack_from("<IIII", raw, table_off + i * SARC_ENTRY_SIZE)
        if not f1 & SARC_NAME_ATTRIBUTE_BIT:
            raise Refusal("%s member %d has no name; this tool only patches named members" % (label, i))
        name_rel = (f1 & SARC_NAME_OFFSET_MASK) * 4
        if name_rel >= len(name_table):
            raise Refusal("%s member %d name offset %d is outside the name table" % (label, i, name_rel))
        nul = name_table.find(b"\x00", name_rel)
        if nul < 0:
            raise Refusal("%s member %d name is not NUL-terminated" % (label, i))
        try:
            name = name_table[name_rel:nul].decode("ascii")
        except UnicodeDecodeError:
            raise Refusal("%s member %d name is not ASCII" % (label, i))
        if any(part in ("", ".", "..") for part in name.split("/")) or name.startswith("/"):
            raise Refusal("%s member %r is not a normalised relative name" % (label, name))
        if name in seen:
            raise Refusal("%s has duplicate member name %r" % (label, name))
        seen.add(name)
        if end < start or end > data_len:
            raise Refusal(
                "%s member %r range [%d, %d) is not inside the %d-byte data section"
                % (label, name, start, end, data_len)
            )
        members.append(
            {
                "index": i,
                "name": name,
                "name_hash_field": f0,
                "name_hash_matches": f0 == sarc_name_hash(name, hash_key),
                "name_off_field": f1,
                "data_start": start,
                "data_end": end,
                "size": end - start,
            }
        )

    return {
        "size": len(raw),
        "sha256": sha256(raw),
        "header_size": header_size,
        "byte_order_raw": bom_raw,
        "size_field": size_field,
        "data_offset": data_offset,
        "word_0x10": word_0x10,
        "sfat_header_size": sfat_header_size,
        "member_count": member_count,
        "hash_key": hash_key,
        "name_table_offset": table_end,
        "members": members,
    }


def member_bytes(archive: dict, raw: bytes, name: str) -> tuple[bytes, dict]:
    matches = [m for m in archive["members"] if m["name"] == name]
    if not matches:
        raise Refusal("no member named %r in the archive (%d members)" % (name, len(archive["members"])))
    if len(matches) > 1:
        raise Refusal("member name %r is ambiguous: %d matches" % (name, len(matches)))
    m = matches[0]
    return raw[archive["data_offset"] + m["data_start"]:archive["data_offset"] + m["data_end"]], m


# ---------------------------------------------------------------------------
# Independent BFLYT block walk and node locator.
# ---------------------------------------------------------------------------


def _cstr(buf: bytes, off: int, limit: int) -> str:
    stop = min(len(buf), off + limit)
    end = off
    while end < stop and buf[end] != 0:
        end += 1
    return buf[off:end].decode("ascii", "replace")


def walk_bflyt(data: bytes, label: str) -> list[dict]:
    """Walk the sequential block chain. Refuse if the model does not hold."""
    if len(data) < FLYT_HEADER_MIN:
        raise Refusal("%s is %d bytes, shorter than a FLYT header" % (label, len(data)))
    if data[:4] != FLYT_MAGIC:
        raise Refusal("%s does not start with FLYT (found %r)" % (label, data[:4]))
    header_size = struct.unpack_from("<H", data, 0x06)[0]
    if header_size != FLYT_HEADER_MIN:
        raise Refusal("%s header_size is 0x%x, expected 0x%x" % (label, header_size, FLYT_HEADER_MIN))
    file_size_field = struct.unpack_from("<I", data, FLYT_FILE_SIZE_OFF)[0]
    if file_size_field != len(data):
        raise Refusal(
            "%s header file_size field is %d but the member is %d bytes"
            % (label, file_size_field, len(data))
        )
    block_count = struct.unpack_from("<H", data, FLYT_BLOCK_COUNT_OFF)[0]

    blocks = []
    off = header_size
    for i in range(block_count):
        if off + 8 > len(data):
            raise Refusal("%s block %d header at 0x%x runs past the end" % (label, i, off))
        tag = data[off:off + 4]
        if not all(32 <= c < 127 for c in tag):
            raise Refusal("%s block %d at 0x%x has a non-ASCII tag %r" % (label, i, off, tag))
        size = struct.unpack_from("<I", data, off + 4)[0]
        if size < 8 or off + size > len(data):
            raise Refusal(
                "%s block %d (%s) at 0x%x has size %d, which does not fit in the file"
                % (label, i, tag, off, size)
            )
        blocks.append(
            {
                "index": i,
                "tag": tag.decode("ascii"),
                "offset": off,
                "size": size,
                "payload_offset": off + 8,
                "payload_size": size - 8,
            }
        )
        off += size
    if off != len(data):
        raise Refusal(
            "%s sequential block walk ends at %d, not at the member size %d"
            % (label, off, len(data))
        )
    return blocks


def find_part(data: bytes, blocks: list[dict], name_query: str, label: str) -> dict:
    """Locate exactly one prt1 part whose name starts with `name_query`."""
    matches = []
    for b in blocks:
        if b["tag"] != "prt1":
            continue
        if b["payload_size"] < PRT1_HEADER_LEN:
            continue
        name = _cstr(data, b["payload_offset"] + PRT1_NAME_OFFSET, PRT1_NAME_LEN)
        if name and name.startswith(name_query):
            matches.append((b, name))

    if not matches:
        raise Refusal(
            "no prt1 part whose name starts with %r in %s; refusing to guess an offset"
            % (name_query, label)
        )
    if len(matches) > 1:
        raise Refusal(
            "part name %r is ambiguous in %s: %d prt1 blocks match (%s); refusing to guess an offset"
            % (name_query, label, len(matches), ", ".join("%s@0x%x" % (n, b["offset"]) for b, n in matches))
        )

    block, name = matches[0]
    payload = block["payload_offset"]
    node_type = struct.unpack_from("<H", data, payload + PRT1_NODE_TYPE_OFFSET)[0]
    if node_type != PRT1_NODE_TYPE:
        raise Refusal(
            "%s %r at 0x%x has node type %d, not the %d this tool models; unsupported structure"
            % (label, name, block["offset"], node_type, PRT1_NODE_TYPE)
        )
    child_count = struct.unpack_from("<H", data, payload + PRT1_CHILD_COUNT_OFFSET)[0]
    if PRT1_HEADER_LEN + child_count * PRT1_CHILD_SIZE > block["payload_size"]:
        raise Refusal(
            "%s %r at 0x%x declares %d child records, which do not fit in %d payload bytes"
            % (label, name, block["offset"], child_count, block["payload_size"])
        )

    return {
        "name": name,
        "block_offset": block["offset"],
        "block_size": block["size"],
        "payload_offset": payload,
        "payload_size": block["payload_size"],
        "node_type": node_type,
        "child_count": child_count,
        "matches": len(matches),
    }


def read_scale(data: bytes, part: dict, label: str) -> list[dict]:
    """Re-read the two scale floats from the located bytes and validate them."""
    values = []
    for rel, component in zip(SCALE_OFFSETS, SCALE_COMPONENTS):
        off = part["payload_offset"] + rel
        if off + 4 > len(data):
            raise Refusal("%s scale field %s at 0x%x runs past the end" % (label, component, off))
        raw4 = data[off:off + 4]
        value = struct.unpack("<f", raw4)[0]
        values.append(
            {
                "component": component,
                "payload_relative_offset": rel,
                "member_offset": off,
                "bytes": raw4.hex(),
                "value": value,
            }
        )
    for entry in values:
        if not math.isfinite(entry["value"]):
            raise Refusal(
                "%s %s at 0x%x is %r, not a finite number; refusing to scale it"
                % (label, entry["component"], entry["member_offset"], entry["value"])
            )
        if entry["value"] <= 0.0:
            raise Refusal(
                "%s %s at 0x%x is %r, not positive; refusing to scale it"
                % (label, entry["component"], entry["member_offset"], entry["value"])
            )
    return values


def pack_scale(values: list[float], label: str) -> list[dict]:
    """Validate and pack the replacement scale floats."""
    out = []
    for component, value in zip(SCALE_COMPONENTS, values):
        if not math.isfinite(value):
            raise Refusal("requested %s %r is not finite" % (component, value))
        if value <= 0.0:
            raise Refusal("requested %s %r is not positive" % (component, value))
        try:
            packed = struct.pack("<f", value)
        except (OverflowError, struct.error) as exc:
            raise Refusal("requested %s %r does not fit in an f32: %s" % (component, value, exc))
        if not math.isfinite(struct.unpack("<f", packed)[0]):
            raise Refusal("requested %s %r overflows f32 to a non-finite value" % (component, value))
        out.append({"component": component, "value": value, "bytes": packed.hex()})
    return out


def apply_scale(member: bytes, part: dict, new_scale: list[dict]) -> tuple[bytes, list[int]]:
    """Write the two floats in place. Returns the bytes and the touched offsets."""
    touched = []
    out = bytearray(member)
    for entry, rel in zip(new_scale, SCALE_OFFSETS):
        off = part["payload_offset"] + rel
        out[off:off + 4] = bytes.fromhex(entry["bytes"])
        touched.append(off)
    out = bytes(out)
    if len(out) != len(member):
        raise Refusal("internal error: payload length changed")
    return out, touched


# ---------------------------------------------------------------------------
# Independent comparison of the parsed layout, ignoring the two target floats.
# ---------------------------------------------------------------------------


def parsed_fields(data: bytes, part: dict, label: str) -> dict:
    """Every parsed field of the located part plus its surrounding blocks."""
    blocks = walk_bflyt(data, label)
    target = part["block_offset"]
    for b in blocks:
        if b["offset"] == target:
            payload = b["payload_offset"]
            child_count = struct.unpack_from("<H", data, payload + PRT1_CHILD_COUNT_OFFSET)[0]
            return {
                "block_count": len(blocks),
                "block_chain": [(x["tag"], x["offset"], x["size"]) for x in blocks],
                "target": {
                    "offset": target,
                    "size": b["size"],
                    "tag": b["tag"],
                    "node_type": struct.unpack_from("<H", data, payload + PRT1_NODE_TYPE_OFFSET)[0],
                    "name": _cstr(data, payload + PRT1_NAME_OFFSET, PRT1_NAME_LEN),
                    "marker_u16": struct.unpack_from("<H", data, payload + 2)[0],
                    "position": list(struct.unpack_from("<2f", data, payload + PRT1_XY_OFFSET)),
                    "extent": list(struct.unpack_from("<2f", data, payload + PRT1_EXTENT_OFFSET)),
                    "child_count": child_count,
                    "children": [
                        _cstr(data, payload + PRT1_HEADER_LEN + k * PRT1_CHILD_SIZE + 10, 24)
                        for k in range(child_count)
                    ],
                    "scale": list(
                        struct.unpack_from("<2f", data, payload + SCALE_OFFSETS[0])
                    ),
                },
            }
    raise Refusal("%s no longer contains the located block at 0x%x" % (label, target))


def diff_offsets(a: bytes, b: bytes) -> list[int]:
    if len(a) != len(b):
        raise Refusal("refusing to compare archives of different sizes (%d vs %d)" % (len(a), len(b)))
    return [i for i in range(len(a)) if a[i] != b[i]]


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal("cannot load %s" % path)
    module = importlib.util.module_from_spec(spec)
    # Register before executing: @dataclass resolves annotations through
    # sys.modules[cls.__module__], so an unregistered module fails.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def guard_output(path: str, protected: list[str]) -> str:
    """Refuse to write outside the workspace, over an input, or into an input tree."""
    abs_path = os.path.abspath(path if os.path.isabs(path) else os.path.join(REPO_ROOT, path))
    if not abs_path.startswith(REPO_ROOT + os.sep):
        raise Refusal("refusing to write outside the workspace: %s" % abs_path)
    for prot in protected:
        prot_abs = os.path.abspath(prot if os.path.isabs(prot) else os.path.join(REPO_ROOT, prot))
        if abs_path == prot_abs:
            raise Refusal("refusing to write %s: it is a supplied input" % abs_path)
        if abs_path.startswith(prot_abs + os.sep):
            raise Refusal(
                "refusing to write %s: supplied inputs live under %s and are read-only"
                % (abs_path, prot_abs)
            )
    parent = os.path.dirname(abs_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    return abs_path


def run_sarc_tool(argv: list[str], what: str) -> subprocess.CompletedProcess:
    if not os.path.isfile(SARC_TOOL):
        raise Refusal("cannot find the archive tool at %s" % SARC_TOOL)
    proc = subprocess.run(
        [sys.executable, SARC_TOOL] + argv,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        raise Refusal(
            "%s failed (exit %d): %s%s" % (what, proc.returncode, proc.stdout.strip(), proc.stderr.strip())
        )
    return proc


# ---------------------------------------------------------------------------


def build(args) -> dict:
    dry_run = args.dry_run
    archive_path = args.archive
    extracted_path = args.extracted

    protected = [archive_path, extracted_path, os.path.dirname(archive_path),
                 os.path.dirname(extracted_path), "gamedata/mii_customizer/P1-UI",
                 "gamedata/mii_customizer/P1-LAYOUT"]

    out_dir = args.out_dir
    control_arc = os.path.join(out_dir, "control", "layout_original.arc")
    patched_arc = os.path.join(out_dir, "patched", "layout_row00_scale075.arc")
    payload_bf = os.path.join(out_dir, "member", "make_mii_special.scale075.bflyt")

    if not dry_run:
        control_abs = guard_output(control_arc, protected)
        patched_abs = guard_output(patched_arc, protected)
        payload_abs = guard_output(payload_bf, protected)
        report_abs = guard_output(args.report, protected)
    else:
        control_abs = patched_abs = payload_abs = report_abs = None

    # 1. archive, independently parsed
    arc_raw = read_bytes(archive_path, "archive")
    archive = parse_sarc(arc_raw, os.path.basename(archive_path))
    if archive["sha256"] != args.expect_archive_sha256:
        raise Refusal(
            "unexpected archive hash: %s has sha256 %s, pinned %s; refusing to patch an unrecognised input"
            % (archive_path, archive["sha256"], args.expect_archive_sha256)
        )
    if not all(m["name_hash_matches"] for m in archive["members"]):
        raise Refusal("%s has a member whose stored name hash disagrees with its name" % archive_path)

    # 2. member, extracted here, then pinned
    payload_original, member = member_bytes(archive, arc_raw, args.member)
    if sha256(payload_original) != args.expect_member_sha256:
        raise Refusal(
            "unexpected member hash: %s!%s has sha256 %s, pinned %s"
            % (args.member, os.path.basename(archive_path), sha256(payload_original), args.expect_member_sha256)
        )
    if payload_original[:4] != FLYT_MAGIC:
        raise Refusal(
            "member %s payload starts with %r, not FLYT; unsupported structure for this diagnostic"
            % (args.member, payload_original[:4])
        )

    # 3. cross-check against the separately extracted file and against the inspector
    extracted_raw = read_bytes(extracted_path, "extracted layout")
    if extracted_raw != payload_original:
        raise Refusal(
            "member %s extracted from the archive is not byte-identical to the pinned extracted file %s"
            % (args.member, extracted_path)
        )
    if sha256(extracted_raw) != args.expect_member_sha256:
        raise Refusal(
            "extracted file %s has sha256 %s, pinned %s"
            % (extracted_path, sha256(extracted_raw), args.expect_member_sha256)
        )

    inspector = load_module(BFLYT_TOOL, "bflyt_inspect_ref")
    try:
        inv = inspector.load(extracted_path)
        matches = [p for p in inv.parts if p.name.startswith(args.part)]
    except Exception as exc:  # noqa: BLE001 - any inspector failure is a refusal
        raise Refusal("bflyt-inspect could not read %s: %s" % (extracted_path, exc))
    if len(matches) != 1:
        raise Refusal(
            "bflyt-inspect finds %d prt1 parts matching %r in %s; refusing to guess an offset"
            % (len(matches), args.part, extracted_path)
        )
    inspector_part = matches[0]

    # 4. locate locally and verify the inspector's offsets against the real bytes
    blocks = walk_bflyt(payload_original, args.member)
    part = find_part(payload_original, blocks, args.part, args.member)
    if inspector_part.offset != part["block_offset"] or inspector_part.name != part["name"]:
        raise Refusal(
            "inspector and local walk disagree: inspector says %r@0x%x, local walk says %r@0x%x"
            % (inspector_part.name, inspector_part.offset, part["name"], part["block_offset"])
        )
    original_scale = read_scale(payload_original, part, args.member)
    for entry, observed in zip(original_scale, inspector_part.scale):
        if entry["value"] != observed:
            raise Refusal(
                "inspector scale %s %r disagrees with the bytes at 0x%x (%r)"
                % (entry["component"], observed, entry["member_offset"], entry["value"])
            )

    # 5. the only change: the two scale floats
    requested = [entry["value"] * args.factor for entry in original_scale]
    new_scale = pack_scale(requested, args.member)
    payload_changed, touched = apply_scale(payload_original, part, new_scale)
    if payload_changed[:4] != FLYT_MAGIC or len(payload_changed) != len(payload_original):
        raise Refusal("internal error: the payload is no longer a same-length FLYT member")
    allowed_member_offsets = set(touched)

    # 6. predicted outputs, computed with the existing archive tool, before writing
    sarc = load_module(SARC_TOOL, "sarc_layout_ref")
    pred_arc = sarc.parse(archive_path)
    if sha256(pred_arc.raw) != archive["sha256"]:
        raise Refusal("archive tool and local reader disagree on the archive bytes")
    predicted_control = sha256(pred_arc.serialise())
    predicted_patched = sha256(
        pred_arc.serialise({args.member: payload_changed})
    )
    if predicted_control != archive["sha256"]:
        raise Refusal(
            "unchanged rebuild of %s is not byte-identical (%s); refusing to publish a control"
            % (archive_path, predicted_control)
        )

    written = {"control": False, "patched": False, "payload": False}
    if not dry_run:
        with open(payload_abs, "wb") as fh:
            fh.write(payload_changed)
        written["payload"] = True
        run_sarc_tool(
            ["rebuild", archive_path, "-o", control_arc, "--json",
             os.path.join(out_dir, "control", "rebuild.json"), "--quiet"],
            "sarc-layout rebuild (control)",
        )
        written["control"] = True
        run_sarc_tool(
            ["replace", archive_path, args.member, "--payload", payload_bf,
             "-o", patched_arc, "--json", os.path.join(out_dir, "patched", "replace.json"), "--quiet"],
            "sarc-layout replace (same length)",
        )
        written["patched"] = True

    # 7. verify what was written, independently of the archive tool
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})
        if not ok:
            raise Refusal("verification failed: %s (%s)" % (name, detail))

    if not dry_run:
        control_raw = read_bytes(control_arc, "control archive")
        patched_raw = read_bytes(patched_arc, "patched archive")
        check("control-byte-identical", control_raw == arc_raw,
              "sha256 %s" % sha256(control_raw))
        check("written-control-matches-prediction", sha256(control_raw) == predicted_control,
              "predicted %s, written %s" % (predicted_control, sha256(control_raw)))
        check("written-patched-matches-prediction", sha256(patched_raw) == predicted_patched,
              "predicted %s, written %s" % (predicted_patched, sha256(patched_raw)))
        check("size-unchanged", len(patched_raw) == len(arc_raw),
              "%d vs %d bytes" % (len(patched_raw), len(arc_raw)))
    else:
        control_raw, patched_raw = None, None

    out_arc = parse_sarc(patched_raw, "patched archive") if patched_raw else None
    out_member = member_bytes(out_arc, patched_raw, args.member)[0] if patched_raw else None

    if patched_raw:
        in_members = {m["name"]: m for m in archive["members"]}
        out_members = {m["name"]: m for m in out_arc["members"]}
        check("member-count-unchanged", len(in_members) == len(out_members),
              "%d members" % len(out_members))
        check("membership-unchanged", set(in_members) == set(out_members), "identical name sets")
        # 'sha256' and 'size' are compared separately: the size must be equal and
        # the hash must differ, so neither belongs in the metadata comparison.
        skip = ("members", "sha256", "size")
        check("header-metadata-unchanged",
              {k: v for k, v in archive.items() if k not in skip}
              == {k: v for k, v in out_arc.items() if k not in skip},
              "all header fields except the archive's own size and hash")
        check(
            "member-offsets-unchanged",
            all(
                (in_members[n]["data_start"], in_members[n]["data_end"], in_members[n]["name_off_field"])
                == (out_members[n]["data_start"], out_members[n]["data_end"], out_members[n]["name_off_field"])
                for n in in_members
            ),
            "%d members compared" % len(in_members),
        )

        changed = [
            n for n in in_members
            if arc_raw[archive["data_offset"] + in_members[n]["data_start"]:
                       archive["data_offset"] + in_members[n]["data_end"]]
            != patched_raw[out_arc["data_offset"] + out_members[n]["data_start"]:
                           out_arc["data_offset"] + out_members[n]["data_end"]]
        ]
        check("exactly-one-member-changed", changed == [args.member], "changed: %s" % (changed or "none"))

        # every differing byte of the archive must sit in one of the two fields
        diffs = set(diff_offsets(arc_raw, patched_raw))
        base = archive["data_offset"] + member["data_start"]
        allowed_archive = {base + off + k for off in allowed_member_offsets for k in range(4)}
        # Not every byte of an f32 has to differ (1.0 and 0.75 share their
        # low-order bytes), so the expected difference set is computed from the
        # payload, not assumed to be the full 4-byte spans.
        expected_member_diffs = {
            off + k for off in allowed_member_offsets for k in range(4)
            if payload_original[off + k] != payload_changed[off + k]
        }
        expected_diffs = {base + off for off in expected_member_diffs}
        check("diffs-inside-the-two-scale-fields", diffs <= allowed_archive,
              "%d differing bytes at %s; allowed spans at %s"
              % (len(diffs), sorted(hex(d) for d in diffs),
                 sorted(hex(d) for d in allowed_archive)))
        check("diffs-are-exactly-the-changed-scale-bytes", diffs == expected_diffs,
              "archive differs at %s; the two floats account for %s"
              % (sorted(hex(d) for d in diffs), sorted(hex(d) for d in expected_diffs)))

        # the member payload itself must differ only in those eight bytes
        member_diffs = set(diff_offsets(payload_original, out_member))
        check("member-diffs-inside-scale-fields", member_diffs == expected_member_diffs,
              "%d differing bytes, all inside the two floats" % len(member_diffs))

        # reparsing: every other parsed field must be identical
        out_blocks = walk_bflyt(out_member, "patched member")
        out_part = find_part(out_member, out_blocks, args.part, "patched member")
        check("part-located-again", out_part["block_offset"] == part["block_offset"],
              "0x%x" % out_part["block_offset"])
        before = parsed_fields(payload_original, part, "original member")
        after = parsed_fields(out_member, out_part, "patched member")
        before["target"].pop("scale")
        after["target"].pop("scale")
        check("all-other-parsed-fields-identical", before == after,
              "%d blocks, name/position/extent/children/marker unchanged" % len(before["block_chain"]))

        out_scale = read_scale(out_member, out_part, "patched member")
        for old, new, want in zip(original_scale, out_scale, new_scale):
            check(
                "field-%s-scaled" % old["component"],
                new["value"] == want["value"] and new["member_offset"] == old["member_offset"],
                "0x%x: %r -> %r (x%s)" % (old["member_offset"], old["value"], new["value"], args.factor),
            )

        

    # 8. inputs must be unchanged
    check("input-archive-unchanged", read_bytes(archive_path, "archive") == arc_raw,
          "sha256 %s" % archive["sha256"])
    check("input-extracted-layout-unchanged", read_bytes(extracted_path, "extracted layout") == extracted_raw,
          "sha256 %s" % sha256(extracted_raw))

    result = {
        "task": "P2-LAYOUT-PATCH",
        "tier": "B (offline measurement; no console, emulator or runtime observation)",
        "dry_run": dry_run,
        "inputs": {
            "archive": {
                "path": archive_path,
                "sha256": archive["sha256"],
                "size": archive["size"],
                "member_count": archive["member_count"],
                "data_offset": archive["data_offset"],
            },
            "member": {
                "name": args.member,
                "sha256": sha256(payload_original),
                "size": member["size"],
                "data_start": member["data_start"],
                "data_end": member["data_end"],
            },
            "extracted_layout": {
                "path": extracted_path,
                "sha256": sha256(extracted_raw),
                "size": len(extracted_raw),
            },
        },
        "located_part": part,
        "scale_fields": [
            {
                "component": entry["component"],
                "payload_relative_offset": entry["payload_relative_offset"],
                "member_offset": entry["member_offset"],
                "archive_offset": archive["data_offset"] + member["data_start"] + entry["member_offset"],
                "original_bytes": original_scale[i]["bytes"],
                "original_value": original_scale[i]["value"],
                "new_bytes": new_scale[i]["bytes"],
                "new_value": new_scale[i]["value"],
            }
            for i, entry in enumerate(original_scale)
        ],
        "factor": args.factor,
        "outputs": {
            "control_archive": control_arc,
            "control_sha256": predicted_control,
            "patched_archive": patched_arc,
            "patched_sha256": predicted_patched,
            "changed_member_payload": payload_bf,
            "changed_member_payload_sha256": sha256(payload_changed),
            "written": written,
        },
        "verification": checks,
        "all_checks_pass": all(c["pass"] for c in checks),
        "not_established": [
            "Whether the game, the emulator or the console accepts a modified layout.arc.",
            "Whether the smaller row is visible at all: an animation may overwrite the scale at runtime.",
            "That the two floats are the row's rendered scale rather than some other transform; "
            "the offsets are measured, the meaning is inferred.",
        ],
        "not_changed": [
            "row names and counts", "positions", "selector group membership",
            "child references", "animations", "text keys", "Lua", "native behaviour",
        ],
    }

    if not dry_run:
        with open(report_abs, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(result, fh, indent=1, sort_keys=True)
            fh.write("\n")
        result["report"] = report_abs
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_diagnostic.py",
        description="Build the one-row layout-only diagnostic archive (offline, same length).",
    )
    p.add_argument("--archive", default=DEFAULT_ARCHIVE, help="layout.arc input (read-only)")
    p.add_argument("--member", default=DEFAULT_MEMBER, help="archive member to patch")
    p.add_argument("--expect-archive-sha256", default=DEFAULT_ARCHIVE_SHA256,
                   help="pinned sha256 of the archive; anything else is refused")
    p.add_argument("--expect-member-sha256", default=DEFAULT_MEMBER_SHA256,
                   help="pinned sha256 of the member payload")
    p.add_argument("--extracted", default=DEFAULT_EXTRACTED,
                   help="separately extracted .bflyt, cross-checked against the archive member")
    p.add_argument("--part", default=DEFAULT_PART,
                   help="prt1 part name prefix; must match exactly one part")
    p.add_argument("--factor", type=float, default=DEFAULT_FACTOR,
                   help="multiplier applied to both scale floats (default 0.75)")
    p.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                   help="output folder for the control, patched archive and payload")
    p.add_argument("--report", default="mods/mii_customizer/evidence/P2-LAYOUT-PATCH/diagnostic.json",
                   help="where to write the JSON report")
    p.add_argument("--dry-run", action="store_true",
                   help="verify and report without writing any file")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build(args)
    except Refusal as exc:
        sys.stderr.write("refused: %s\n" % exc)
        return 2
    for entry in result["verification"]:
        sys.stdout.write("  %-4s %-38s %s\n" % ("ok" if entry["pass"] else "FAIL", entry["check"], entry["detail"]))
    sys.stdout.write("\n%s: %d checks passed\n" % ("DRY RUN" if result["dry_run"] else "build",
                                                   len(result["verification"])))
    sys.stdout.write("  part        %s @0x%x in %s\n" % (result["located_part"]["name"],
                                                        result["located_part"]["block_offset"],
                                                        result["inputs"]["member"]["name"]))
    for field in result["scale_fields"]:
        sys.stdout.write("  %-9s 0x%-6x %r -> %r\n" % (field["component"], field["member_offset"],
                                                       field["original_value"], field["new_value"]))
    sys.stdout.write("  control     %s\n" % result["outputs"]["control_sha256"])
    sys.stdout.write("  patched     %s\n" % result["outputs"]["patched_sha256"])
    if not result["dry_run"]:
        sys.stdout.write("  written     %s\n" % result["report"])
    return 0


if __name__ == "__main__":
    sys.exit(main())