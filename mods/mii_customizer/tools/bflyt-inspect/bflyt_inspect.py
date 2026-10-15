"""bflyt-inspect: a bounded, read-only BFLYT inspector for Smash UI layout files.

This tool parses the container and the block, group and part layers of the
``.bflyt`` files that live inside the Mii editor ``layout.arc`` archives, and
reports them as a machine-readable inventory. It exists to describe the editor
rows and selector groups that are already in the game.

It is **strictly read-only**. It never writes a ``.bflyt`` and never rewrites an
archive. Understanding the structure is a prerequisite for changing it, not a
licence to change it. Nothing here establishes that the game would accept a
modified file.

Every field this tool prints is either (a) a measured value with a byte offset,
or (b) explicitly marked unknown with its raw bytes preserved. Fields whose
meaning has not been established are labelled rather than guessed.

Format notes (all measured, tier B; see README.md for provenance):

* Header. ``"FLYT"`` magic, byte-order mark ``ff fe`` at +4, little-endian
  ``u16 header_size`` at +6 (0x14 in every file measured), a 4-byte word at +8
  whose meaning is **unverified**, ``u32 file_size`` at +0x0C and
  ``u16 block_count`` at +0x10.
* Blocks. A block is a 4-byte ASCII tag followed by a little-endian ``u32``
  size at +4. **The size covers the tag and the size field themselves**, so the
  next block begins at ``offset + size``, not ``offset + 8 + size``. Walking
  ``block_count`` blocks from ``header_size`` lands exactly on the end of the
  file for every file measured here.
* Groups (``grp1``). A 36-byte preamble followed by ``count`` fixed-size name
  slots. ``count`` is the ``u16`` at payload offset +34. Each slot is 24 bytes
  holding a NUL-padded name. Verified to consume every ``grp1`` payload exactly
  in both target files.
* Parts (``prt1``). A fixed 78-byte header (node type, a repeated 0xffff
  sentinel, a 32-byte NUL-padded name, position, scale and extent floats, and a
  child count) followed by ``child_count`` 40-byte child records, each carrying
  its own inline name. The region after those records contains a padding gap,
  an owner layout name, and further embedded blocks; that tail is reported by
  offset and by the names found in it, and is **not** claimed to be decoded.
* ``pas1``/``pae1``/``grs1``/``gre1`` are empty marker blocks of size 8 in every
  file measured. They are listed, and their emptiness is reported as a
  measurement, not as a claim about the loader's intent.

See ``README.md`` in this directory for usage, provenance and limitations.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

MAGIC = b"FLYT"

HEADER_MIN = 0x14
FILE_SIZE_OFF = 0x0C
BLOCK_COUNT_OFF = 0x10
UNKNOWN_WORD_OFF = 0x08

# grp1 layout (verified against every grp1 in both target files)
GRP1_COUNT_OFF = 34
GRP1_ENTRY_SIZE = 24
GRP1_ENTRY_STRIDE = 24

# prt1 layout (header verified; child records verified by name/position checks)
PRT1_TYPE_OFF = 0
PRT1_SENTINEL_OFF = 2
PRT1_NAME_OFF = 4
PRT1_NAME_LEN = 32
PRT1_X_OFF = 36
PRT1_Y_OFF = 40
PRT1_SCALE_OFF = 60
PRT1_W_OFF = 68
PRT1_H_OFF = 72
PRT1_CHILD_COUNT_OFF = 76
PRT1_HEADER_LEN = 78
PRT1_CHILD_SIZE = 40
PRT1_CHILD_NAME_OFF = 10
PRT1_CHILD_NAME_LEN = 24

# The u16 at payload offset +2 of a name-bearing node block. It is NOT a
# constant, so it must never be used to decide whether a block has a name.
# Measured across 123 node blocks in four files: 0x0000, 0x00ff, 0x0200, 0x02ff
# and 0x06ff all occur, and every one of those blocks has a valid name. Two
# earlier drafts of this tool gated name detection on a guessed marker (first
# 0xffff, then <= 0x03ff) and both produced FALSE 'unresolved group member'
# reports by silently skipping real nodes. Name detection now relies only on the
# name itself; the marker is recorded but never enforced. Its meaning is
# unverified.
SENTINEL = 0x00FF

# Recorded for reporting only. Not a gate. See the note above.
MARKERS_SEEN = (0x0000, 0x00FF, 0x0200, 0x02FF, 0x06FF)

# Block tags whose payload begins with an inline node name, which is what the
# grp1 cross-check resolves against.
NODE_TAGS = ("prt1", "pan1", "bnd1", "txt1", "wnd1", "pic1")


class BflytError(Exception):
    """Raised when a file does not parse as the structure this tool models."""


def _cstr(buf: bytes, off: int, limit: int) -> str:
    """Read a NUL-terminated ASCII name from ``buf`` at ``off``, at most ``limit`` bytes."""
    if off < 0 or off > len(buf):
        return ""
    end = off
    stop = min(len(buf), off + limit)
    while end < stop and buf[end] != 0:
        end += 1
    return buf[off:end].decode("ascii", "replace")


def _u16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _f32(buf: bytes, off: int) -> float:
    return struct.unpack_from("<f", buf, off)[0]


@dataclass
class Block:
    """One BFLYT block. ``size`` covers the tag and size fields."""

    index: int
    tag: str
    offset: int
    size: int
    payload_offset: int
    payload_size: int

    @property
    def end(self) -> int:
        return self.offset + self.size


@dataclass
class GroupEntry:
    """One 24-byte name slot inside a ``grp1`` block."""

    index: int
    name: str
    offset: int


@dataclass
class Group:
    """A ``grp1`` block: a named container of name slots."""

    name: str
    name_offset: int
    offset: int
    size: int
    count_offset: int
    entry_count: int
    entries: list[GroupEntry] = field(default_factory=list)
    exact: bool = False


@dataclass
class PartChild:
    """One 40-byte child record inside a ``prt1`` block."""

    index: int
    name: str
    name_offset: int
    offset: int


@dataclass
class TailName:
    """A name found in a prt1 tail. Location only; no field semantics claimed."""

    name: str
    offset: int


@dataclass
class Part:
    """A ``prt1`` block: a named node with child records and an opaque tail."""

    name: str
    name_offset: int
    offset: int
    size: int
    node_type: int
    sentinel: int
    position: tuple[float, float]
    scale: tuple[float, float]
    extent: tuple[float, float]
    child_count_offset: int
    child_count: int
    children: list[PartChild] = field(default_factory=list)
    records_end: int = 0
    tail_names: list[TailName] = field(default_factory=list)
    tail_first_nonzero: int | None = None
    exact: bool = False


@dataclass
class Bflyt:
    """A parsed ``.bflyt`` file."""

    path: str
    sha256: str
    size: int
    header: dict
    blocks: list[Block]
    groups: list[Group]
    parts: list[Part]
    node_names: dict[str, list[dict]]
    walked_end: int
    exact_walk: bool

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size": self.size,
            "header": self.header,
            "walked_end": self.walked_end,
            "exact_walk": self.exact_walk,
            "blocks": [asdict(b) for b in self.blocks],
            "groups": [asdict(g) for g in self.groups],
            "parts": [asdict(p) for p in self.parts],
            "node_names": self.node_names,
        }


def parse_header(data: bytes) -> dict:
    """Parse the fixed BFLYT header. Unverified fields are labelled, not guessed."""
    if len(data) < HEADER_MIN:
        raise BflytError(f"file shorter than the {HEADER_MIN}-byte header: {len(data)}")
    if data[:4] != MAGIC:
        raise BflytError(f"bad magic {data[:4]!r}, expected {MAGIC!r}")
    header_size = _u16(data, 6)
    file_size = _u32(data, FILE_SIZE_OFF)
    block_count = _u16(data, BLOCK_COUNT_OFF)
    return {
        "magic": data[:4].decode("ascii"),
        "byte_order_mark": data[4:6].hex(),
        "header_size": header_size,
        "header_size_offset": 6,
        "word_at_0x08": data[UNKNOWN_WORD_OFF:UNKNOWN_WORD_OFF + 4].hex(),
        "word_at_0x08_note": (
            "unverified: not the block count; meaning not established"
        ),
        "file_size_field": file_size,
        "file_size_offset": FILE_SIZE_OFF,
        "block_count": block_count,
        "block_count_offset": BLOCK_COUNT_OFF,
    }


def parse_blocks(data: bytes, block_count: int, header_size: int) -> tuple[list[Block], int]:
    """Walk blocks sequentially. Each block's size includes its own 8-byte header."""
    blocks: list[Block] = []
    off = header_size
    for i in range(block_count):
        if off + 8 > len(data):
            raise BflytError(
                f"block {i} header at {off:#x} runs past end of file ({len(data)})"
            )
        tag = data[off:off + 4]
        if not all(32 <= c < 127 for c in tag):
            raise BflytError(f"block {i} at {off:#x} has non-ASCII tag {tag!r}")
        size = _u32(data, off + 4)
        if size < 8:
            raise BflytError(f"block {i} at {off:#x} has size {size}, less than its header")
        if off + size > len(data):
            raise BflytError(
                f"block {i} at {off:#x} size {size} runs past end of file ({len(data)})"
            )
        blocks.append(
            Block(
                index=i,
                tag=tag.decode("ascii"),
                offset=off,
                size=size,
                payload_offset=off + 8,
                payload_size=size - 8,
            )
        )
        off += size
    return blocks, off


def parse_group(data: bytes, block: Block) -> Group:
    """Parse a ``grp1`` block: 36-byte preamble then ``count`` 24-byte name slots."""
    p = block.payload_offset
    end = block.end
    payload = data[p:end]
    if len(payload) < GRP1_COUNT_OFF + 2:
        raise BflytError(f"grp1 at {block.offset:#x} payload too small ({len(payload)})")
    count = _u16(payload, GRP1_COUNT_OFF)
    entries: list[GroupEntry] = []
    for k in range(count):
        rel = GRP1_COUNT_OFF + 2 + k * GRP1_ENTRY_SIZE
        if p + rel + GRP1_ENTRY_SIZE > end:
            raise BflytError(
                f"grp1 at {block.offset:#x} entry {k} runs past block end"
            )
        entries.append(
            GroupEntry(
                index=k,
                name=_cstr(payload, rel, GRP1_ENTRY_SIZE),
                offset=p + rel,
            )
        )
    expected = GRP1_COUNT_OFF + 2 + count * GRP1_ENTRY_SIZE
    return Group(
        name=_cstr(payload, 0, 32),
        name_offset=p,
        offset=block.offset,
        size=block.size,
        count_offset=p + GRP1_COUNT_OFF,
        entry_count=count,
        entries=entries,
        exact=(expected == len(payload)),
    )


def _scan_names(payload: bytes, base: int) -> list[TailName]:
    """Collect NUL-terminated printable runs of length >= 2 with absolute offsets."""
    out: list[TailName] = []
    i = 0
    n = len(payload)
    while i < n:
        if 32 <= payload[i] < 127:
            j = i
            while j < n and 32 <= payload[j] < 127:
                j += 1
            if j - i >= 2:
                out.append(
                    TailName(
                        name=payload[i:j].decode("ascii", "replace"),
                        offset=base + i,
                    )
                )
            i = j
        else:
            i += 1
    return out


def parse_part(data: bytes, block: Block) -> Part:
    """Parse a ``prt1`` block: fixed header, child records, and a reported tail."""
    p = block.payload_offset
    end = block.end
    payload = data[p:end]
    if len(payload) < PRT1_HEADER_LEN:
        raise BflytError(f"prt1 at {block.offset:#x} payload too small ({len(payload)})")
    child_count = _u16(payload, PRT1_CHILD_COUNT_OFF)
    children: list[PartChild] = []
    for k in range(child_count):
        rel = PRT1_HEADER_LEN + k * PRT1_CHILD_SIZE
        if rel + PRT1_CHILD_SIZE > len(payload):
            raise BflytError(
                f"prt1 at {block.offset:#x} child {k} runs past block end"
            )
        children.append(
            PartChild(
                index=k,
                name=_cstr(payload, rel + PRT1_CHILD_NAME_OFF, PRT1_CHILD_NAME_LEN),
                name_offset=p + rel + PRT1_CHILD_NAME_OFF,
                offset=p + rel,
            )
        )
    records_end = PRT1_HEADER_LEN + child_count * PRT1_CHILD_SIZE
    tail = payload[records_end:]
    first_nz = None
    for k, b in enumerate(tail):
        if b != 0:
            first_nz = records_end + k
            break
    return Part(
        name=_cstr(payload, PRT1_NAME_OFF, PRT1_NAME_LEN),
        name_offset=p + PRT1_NAME_OFF,
        offset=block.offset,
        size=block.size,
        node_type=_u16(payload, PRT1_TYPE_OFF),
        sentinel=_u16(payload, PRT1_SENTINEL_OFF),
        position=(_f32(payload, PRT1_X_OFF), _f32(payload, PRT1_Y_OFF)),
        scale=(_f32(payload, PRT1_SCALE_OFF), _f32(payload, PRT1_SCALE_OFF + 4)),
        extent=(_f32(payload, PRT1_W_OFF), _f32(payload, PRT1_H_OFF)),
        child_count_offset=p + PRT1_CHILD_COUNT_OFF,
        child_count=child_count,
        children=children,
        records_end=p + records_end,
        tail_names=_scan_names(tail, p + records_end),
        tail_first_nonzero=(p + first_nz) if first_nz is not None else None,
        exact=(records_end <= len(payload)),
    )


def collect_node_names(data: bytes, blocks: Iterable[Block]) -> dict[str, list[dict]]:
    """Map each inline node name to the blocks that define it.

    A block is treated as name-bearing when it is one of ``NODE_TAGS`` and payload+4
    holds a printable, NUL-terminated, identifier-shaped name. The u16 marker at
    +2 is recorded but never used as a gate; see the note on :data:`SENTINEL`.
    """
    out: dict[str, list[dict]] = {}
    for b in blocks:
        if b.tag not in NODE_TAGS:
            continue
        payload = data[b.payload_offset:b.end]
        if len(payload) < PRT1_NAME_OFF + 2:
            continue
        node_type = _u16(payload, 0)
        marker = _u16(payload, 2)
        name = _cstr(payload, PRT1_NAME_OFF, PRT1_NAME_LEN)
        if not name or not all(c.isalnum() or c == "_" for c in name):
            continue
        out.setdefault(name, []).append(
            {
                "tag": b.tag,
                "offset": b.offset,
                "node_type": node_type,
                "marker_u16": marker,
                "name_offset": b.payload_offset + PRT1_NAME_OFF,
            }
        )
    return out


def load(path: str | Path) -> Bflyt:
    """Parse one ``.bflyt`` file into a :class:`Bflyt`."""
    p = Path(path)
    data = p.read_bytes()
    header = parse_header(data)
    blocks, end = parse_blocks(data, header["block_count"], header["header_size"])
    groups = [parse_group(data, b) for b in blocks if b.tag == "grp1"]
    parts = [parse_part(data, b) for b in blocks if b.tag == "prt1"]
    return Bflyt(
        path=p.as_posix(),
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        header=header,
        blocks=blocks,
        groups=groups,
        parts=parts,
        node_names=collect_node_names(data, blocks),
        walked_end=end,
        exact_walk=(end == len(data)),
    )


def crosscheck_groups(bf: Bflyt) -> dict:
    """Resolve every grp1 member name against the node names defined in the file.

    An unresolved member is reported as unresolved. It is **not** treated as
    corruption: a member may legitimately name a node defined in a child
    layout archive rather than in this file.
    """
    rows = []
    for g in bf.groups:
        for e in g.entries:
            refs = bf.node_names.get(e.name, [])
            rows.append(
                {
                    "group": g.name,
                    "group_offset": g.offset,
                    "member": e.name,
                    "member_offset": e.offset,
                    "resolved": bool(refs),
                    "definitions": refs,
                }
            )
    unresolved = [r for r in rows if not r["resolved"]]
    return {
        "total_members": len(rows),
        "resolved": len(rows) - len(unresolved),
        "unresolved": len(unresolved),
        "unresolved_members": unresolved,
        "members": rows,
    }


def row_parts(bf: Bflyt, prefix: str) -> list[dict]:
    """Return the parts whose names start with ``prefix``, in file order."""
    return [
        {
            "name": p.name,
            "offset": p.offset,
            "size": p.size,
            "name_offset": p.name_offset,
            "position": list(p.position),
            "extent": list(p.extent),
            "child_count": p.child_count,
            "child_names": [c.name for c in p.children],
            "tail_names": [t.name for t in p.tail_names],
        }
        for p in bf.parts
        if p.name.startswith(prefix)
    ]


def cmd_header(bf: Bflyt) -> int:
    print(f"{bf.path}")
    print(f"  size            {bf.size}")
    print(f"  sha256          {bf.sha256}")
    for k, v in bf.header.items():
        print(f"  {k:18s} {v}")
    print(f"  {'blocks_walked':18s} {len(bf.blocks)}")
    print(f"  {'walked_end':18s} {bf.walked_end}")
    print(f"  {'exact_walk':18s} {bf.exact_walk}")
    return 0 if bf.exact_walk else 1


def cmd_blocks(bf: Bflyt) -> int:
    print(f"{bf.path}  ({len(bf.blocks)} blocks)")
    print(f"{'idx':>4} {'offset':>10} {'size':>7} {'tag':>6} {'payload':>10} {'plen':>7}")
    for b in bf.blocks:
        print(
            f"{b.index:>4} {b.offset:>10} {b.size:>7} {b.tag:>6} "
            f"{b.payload_offset:>10} {b.payload_size:>7}"
        )
    return 0


def cmd_groups(bf: Bflyt) -> int:
    print(f"{bf.path}  ({len(bf.groups)} groups)")
    for g in bf.groups:
        flag = "" if g.exact else "  [PAYLOAD NOT FULLY EXPLAINED]"
        print(
            f"\ngrp1 @{g.offset:#08x} size={g.size} name={g.name!r} "
            f"entries={g.entry_count} count_field@{g.count_offset:#08x}{flag}"
        )
        for e in g.entries:
            print(f"    [{e.index}] @{e.offset:#08x} {e.name!r}")
    return 0


def cmd_parts(bf: Bflyt, prefix: str | None = None) -> int:
    sel = [p for p in bf.parts if prefix is None or p.name.startswith(prefix)]
    print(f"{bf.path}  ({len(sel)} parts)")
    for p in sel:
        print(
            f"\nprt1 @{p.offset:#08x} size={p.size} name={p.name!r} type={p.node_type} "
            f"sentinel={p.sentinel:#06x} pos={p.position} extent={p.extent}"
        )
        print(f"    children={p.child_count} count_field@{p.child_count_offset:#08x} "
              f"records_end=@{p.records_end:#08x}")
        for c in p.children:
            print(f"      [{c.index}] @{c.offset:#08x} {c.name!r}")
        if p.tail_names:
            print(f"    tail names ({len(p.tail_names)}), offsets only, semantics unverified:")
            for t in p.tail_names:
                print(f"      @{t.offset:#08x} {t.name!r}")
    return 0


def cmd_crosscheck(bf: Bflyt) -> int:
    cc = crosscheck_groups(bf)
    print(f"{bf.path}")
    print(f"  group members      {cc['total_members']}")
    print(f"  resolved in file   {cc['resolved']}")
    print(f"  unresolved         {cc['unresolved']}")
    for r in cc["unresolved_members"]:
        print(f"    UNRESOLVED {r['group']!r} -> {r['member']!r} @{r['member_offset']:#08x}")
    if not cc["unresolved"]:
        print("    (none)")
    return 0


def cmd_rows(bf: Bflyt, prefix: str) -> int:
    rows = row_parts(bf, prefix)
    print(f"{bf.path}  parts matching {prefix!r}: {len(rows)}")
    for r in rows:
        print(
            f"  {r['name']:16s} @{r['offset']:#08x} size={r['size']:5d} "
            f"pos={tuple(r['position'])} extent={tuple(r['extent'])} "
            f"children={r['child_count']}"
        )
        print(f"      child_names={r['child_names']}")
    return 0


def cmd_inventory(bf: Bflyt, out: str | None = None) -> int:
    inv = bf.to_dict()
    inv["group_crosscheck"] = crosscheck_groups(bf)
    inv["rows"] = {
        "set_item": row_parts(bf, "set_item"),
        "set_special_item": row_parts(bf, "set_special_item"),
    }
    text = json.dumps(inv, indent=2)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {out} ({len(text)} bytes)")
    else:
        print(text)
    return 0


def cmd_verify(bf: Bflyt) -> int:
    """Structural self-checks. Exit 0 only when every check passes."""
    checks: list[tuple[bool, str]] = []
    checks.append((bf.exact_walk,
                   f"sequential block walk consumes file exactly "
                   f"(walked={bf.walked_end}, size={bf.size})"))
    checks.append((bf.header["file_size_field"] == bf.size,
                   f"file_size field matches actual size "
                   f"({bf.header['file_size_field']} == {bf.size})"))
    checks.append((bf.header["header_size"] >= HEADER_MIN,
                   f"header_size sane ({bf.header['header_size']})"))
    checks.append((len(bf.blocks) == bf.header["block_count"],
                   f"walked {len(bf.blocks)} blocks, header says {bf.header['block_count']}"))
    for b in bf.blocks:
        checks.append((b.size >= 8 and b.end <= bf.size,
                       f"block {b.index} ({b.tag}@{b.offset:#x}) within file"))
    for g in bf.groups:
        checks.append((g.exact,
                       f"grp1 {g.name!r} payload exactly consumed by {g.entry_count} entries"))
        checks.append((bool(g.name), f"grp1 @{g.offset:#x} has a name"))
    for p in bf.parts:
        checks.append((p.exact,
                       f"prt1 {p.name!r} child records within payload ({p.child_count} children)"))
        checks.append((p.sentinel in MARKERS_SEEN,
                       f"prt1 {p.name!r} marker field 0x{p.sentinel:04x} is one of "
                       f"the measured values {tuple(hex(m) for m in MARKERS_SEEN)}"))
        checks.append((bool(p.name), f"prt1 @{p.offset:#x} has a name"))
    cc = crosscheck_groups(bf)
    checks.append((True,
                   f"group members resolved {cc['resolved']}/{cc['total_members']} "
                   f"(unresolved reported, not assumed corrupt)"))

    failed = [msg for ok, msg in checks if not ok]
    for ok, msg in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {msg}")
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


USAGE = """usage: bflyt_inspect.py <command> <file.bflyt> [args]

commands:
  header FILE...              header fields and exact-walk result
  blocks FILE...              every block with tag, offset and size
  groups FILE...              grp1 blocks, member names and counts
  crosscheck FILE...          resolve every group member against node names
  verify FILE...              structural self-checks; exit 0 only if ALL pass
  parts FILE [PREFIX]         prt1 blocks with children and tail names
  rows FILE PREFIX            parts whose name starts with PREFIX
  inventory FILE [--out J]    machine-readable JSON inventory

Commands marked FILE... check every file given; a failure in any one of them
makes the exit status nonzero. A parse error in any file is reported and exits
nonzero rather than being skipped.

This tool is read-only. It never writes a .bflyt or an archive.
"""


# Commands that accept one or more FILE arguments and nothing else.
MULTI_FILE = ("header", "blocks", "groups", "crosscheck", "verify")
# Commands that take exactly one FILE, optionally followed by one non-FILE
# argument (a PREFIX or the --out PATH pair).
SINGLE_FILE = ("parts", "rows", "inventory")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(USAGE, file=sys.stderr)
        return 2
    cmd, path = argv[1], argv[2]
    rest = argv[3:]

    # Multi-file commands must check every file given. An earlier version
    # silently processed only argv[2] and discarded the rest, so
    # `verify good.bflyt corrupt.bflyt` exited 0. That is a false pass, so all
    # positional arguments after the command are now treated as files to check.
    if cmd in MULTI_FILE:
        paths = [path, *rest]
    elif cmd in SINGLE_FILE:
        # 'rest' is this command's own optional argument (PREFIX or --out PATH),
        # not an extra file, so it is left for the per-command handler.
        paths = [path]
    else:
        print(USAGE, file=sys.stderr)
        return 2

    try:
        loaded = [load(p) for p in paths]
    except (OSError, BflytError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if cmd == "header":
        return max(cmd_header(bf) for bf in loaded)
    if cmd == "blocks":
        return max(cmd_blocks(bf) for bf in loaded)
    if cmd == "groups":
        return max(cmd_groups(bf) for bf in loaded)
    if cmd == "crosscheck":
        return max(cmd_crosscheck(bf) for bf in loaded)
    if cmd == "verify":
        return max(cmd_verify(bf) for bf in loaded)
    if cmd == "parts":
        if len(loaded) != 1 or len(rest) > 1:
            print("error: parts takes one FILE and an optional PREFIX",
                  file=sys.stderr)
            return 2
        return cmd_parts(loaded[0], rest[0] if rest else None)
    if cmd == "rows":
        if len(rest) != 1:
            print("error: rows takes exactly one PREFIX", file=sys.stderr)
            print(USAGE, file=sys.stderr)
            return 2
        return cmd_rows(loaded[0], rest[0])
    if cmd == "inventory":
        out = None
        if rest:
            if rest[0] != "--out" or len(rest) != 2:
                print("error: inventory takes --out PATH", file=sys.stderr)
                return 2
            out = rest[1]
        return cmd_inventory(loaded[0], out)
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))