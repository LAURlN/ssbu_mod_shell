"""Minimal MSBT reader for SSBU ui/message files (header + LBL1 + TXT2).

What is implemented, as observed on 13.0.4 `ui/message/msg_menu.msbt`
(cross-checked against the `msbt-rs` crate ARCropolis itself uses, commit
9837597fe8e8349b6b079a0d17b9ac224df3984d, RoccoDev/msbt-rs):

  file header, 32 bytes
    0x00  8  magic "MsgStdBn"
    0x08  2  byte-order mark (ff fe = little endian)
    0x0A  2  unknown
    0x0C  1  encoding (00 = Utf8, 01 = Utf16)
    0x0D  1  unknown
    0x0E  2  section count
    0x10  2  unknown
    0x12  4  file size (equals len(file) on the file read here)
    0x16 10  padding (zeros)

  section, repeated: 4-byte magic, u32 payload size, 8 filler bytes, payload.
  Between sections there is 0xAB padding, which the walk skips.

  LBL1 payload: u32 group count, then per group (u32 label count, u32 offset),
  then per group `label count` labels of: u8 name length, name bytes, u32 index
  into the TXT2 string table. The name length byte does not include a
  terminator; the stored names here carry none, so names are read verbatim.

  TXT2 payload: u32 string count, u32 offset[count] relative to the payload
  start, then the strings back to back; string i spans offset[i]..offset[i+1]
  and the last one runs to the end of the payload.

The reader only reports what is in the file. It never writes a file back and
says nothing about whether the game accepts one.

Usage:  python read_msbt.py <path to .msbt> [label-prefix ...]
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

HEADER_MAGIC = b"MsgStdBn"
SECTION_FILLER = 8
PADDING_CHAR = 0xAB


class MsbtError(Exception):
    pass


def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def parse(path: Path) -> dict:
    raw = path.read_bytes()
    if raw[:8] != HEADER_MAGIC:
        raise MsbtError("not an MSBT file: magic %r" % raw[:8])
    bom = raw[8:10]
    if bom != b"\xff\xfe":
        raise MsbtError("byte-order mark %r is not little endian" % bom)
    encoding = raw[12]
    if encoding != 0x01:
        raise MsbtError("encoding byte 0x%02x is not Utf16" % encoding)
    section_count = struct.unpack_from("<H", raw, 14)[0]
    file_size = _u32(raw, 0x12)

    sections: dict[str, bytes] = {}
    order: list[str] = []
    off = 32
    while off + 16 <= len(raw):
        while off < len(raw) and raw[off] == PADDING_CHAR:
            off += 1
        if off + 16 > len(raw):
            break
        tag = raw[off:off + 4].decode("ascii", "replace")
        size = _u32(raw, off + 4)
        payload_at = off + 4 + 4 + SECTION_FILLER
        if payload_at + size > len(raw):
            raise MsbtError("section %s at 0x%x claims %d bytes, only %d left"
                            % (tag, off, size, len(raw) - payload_at))
        sections[tag] = raw[payload_at:payload_at + size]
        order.append(tag)
        off = payload_at + size

    for required in ("LBL1", "TXT2"):
        if required not in sections:
            raise MsbtError("no %s section; sections: %s" % (required, order))

    lbl1 = sections["LBL1"]
    group_count = _u32(lbl1, 0)
    groups = []
    for i in range(group_count):
        base = 4 + i * 8
        groups.append({"label_count": _u32(lbl1, base),
                       "offset": _u32(lbl1, base + 4)})
    labels_at = 4 + group_count * 8

    txt2 = sections["TXT2"]
    string_count = _u32(txt2, 0)
    offsets = [_u32(txt2, 4 + i * 4) for i in range(string_count)]
    texts = []
    for i, start in enumerate(offsets):
        end = offsets[i + 1] if i + 1 < string_count else len(txt2)
        texts.append(txt2[start:end])

    labels = []
    pos = labels_at
    expected = sum(g["label_count"] for g in groups)
    for group in groups:
        for _ in range(group["label_count"]):
            name_len = lbl1[pos]
            pos += 1
            name = lbl1[pos:pos + name_len].decode("utf-8")
            pos += name_len
            index = _u32(lbl1, pos)
            pos += 4
            labels.append({"name": name, "index": index})
    if len(labels) != expected:
        raise MsbtError("group table counts %d labels, read %d"
                        % (expected, len(labels)))
    if pos > len(lbl1):
        raise MsbtError("label block ran %d bytes past the LBL1 payload"
                        % (pos - len(lbl1)))

    undecodable = 0
    for lbl in labels:
        if lbl["index"] >= len(texts):
            raise MsbtError("label %r points at TXT2 string %d of %d"
                            % (lbl["name"], lbl["index"], len(texts)))
        lbl["text_bytes"] = texts[lbl["index"]]
        # Some texts contain unit values that are not valid UTF-16 (the game's
        # inline escapes). Those units are kept as-is in text_bytes and are
        # replaced in the printable string; the hex runs below are the record.
        lbl["text"] = lbl["text_bytes"].decode("utf-16-le", "replace")
        if "�" in lbl["text"]:
            undecodable += 1

    return {
        "path": str(path),
        "bytes": len(raw),
        "file_size_field": file_size,
        "file_size_matches": file_size == len(raw),
        "section_count_field": section_count,
        "section_order": order,
        "group_count": group_count,
        "label_count": len(labels),
        "string_count": string_count,
        "labels": labels,
        "labels_with_undecodable_units": undecodable,
    }


def control_runs(text_bytes: bytes) -> list[bytes]:
    """Maximal runs of UTF-16LE units that are outside printable ASCII.

    A unit is outside 0x20..0x7E, which covers both the inline escape codes and
    the icon glyphs the editor texts use. A trailing 0x0000 unit (the string
    terminator) is dropped from the run that ends the text. The runs are
    reported as raw bytes; nothing here is interpreted or named.
    """
    units = [text_bytes[i] | (text_bytes[i + 1] << 8)
             for i in range(0, len(text_bytes) - 1, 2)]
    runs: list[bytes] = []
    current: list[int] = []
    for unit in units:
        printable = 0x20 <= unit <= 0x7E
        if printable:
            if current:
                runs.append(current)
                current = []
        else:
            current.append(unit)
    if current:
        while current and current[-1] == 0:
            current.pop()
        if current:
            runs.append(current)
    out = []
    for run in runs:
        data = b"".join(u.to_bytes(2, "little") for u in run)
        out.append(data)
    return out


def main(argv: list[str]) -> int:
    # The texts contain units that cp1252 cannot print; keep the transcript
    # readable by escaping what the console cannot encode.
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if not argv:
        print(__doc__)
        return 2
    info = parse(Path(argv[0]))
    prefixes = argv[1:]

    print("file            %s" % info["path"])
    print("bytes           %d (header size field %d, equal: %s)"
          % (info["bytes"], info["file_size_field"], info["file_size_matches"]))
    print("sections        %d declared, found %s"
          % (info["section_count_field"], " ".join(info["section_order"])))
    print("LBL1 groups     %d" % info["group_count"])
    print("LBL1 labels     %d" % info["label_count"])
    print("TXT2 strings    %d" % info["string_count"])
    print("labels with undecodable UTF-16 units: %d"
          % info["labels_with_undecodable_units"])

    wanted = [l for l in info["labels"]
              if not prefixes or any(l["name"].startswith(p) for p in prefixes)]
    print("matched         %d label(s) for prefixes %s" % (len(wanted), prefixes))
    for lbl in wanted:
        print("  %-40s = %r" % (lbl["name"], lbl["text"]))

    runs: dict[bytes, list[str]] = {}
    for lbl in wanted:
        for run in control_runs(lbl["text_bytes"]):
            runs.setdefault(run, []).append(lbl["name"])
    print("distinct raw non-ASCII runs in matched labels: %d" % len(runs))
    for run, names in sorted(runs.items()):
        print("  units %-26s bytes %-24s %d label(s), e.g. %s"
              % (" ".join("%04x" % (run[i] | (run[i + 1] << 8))
                          for i in range(0, len(run), 2)),
                 " ".join("%02x" % b for b in run), len(names), names[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))