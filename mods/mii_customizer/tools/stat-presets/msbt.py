"""Minimal read-only MSBT reader, enough to read label -> text.

Layout cross-checked against pinned source (tier C):
`RoccoDev/msbt-rs` commit 9837597fe8e8349b6b079a0d17b9ac224df3984d, cloned
read-only into `scratch/2026-10-05_P5-MSG-PROBE/msbt-rs` by task P5-MSG-PROBE.
Files read there: `src/lib.rs` (header, `MsbtReader::read_lbl1`, `read_txt2`,
`skip_padding`, `PADDING_CHAR`), `src/section.rs`, `src/section/lbl1.rs`,
`src/section/txt2.rs`. Everything below is a stdlib-only Python transcription of
those readers; the file itself was measured by running this module.

Container:

    header 32 bytes: 'MsgStdBn' | BOM(2) | u16 | u8 encoding | u8 | u16 | u16 |
                     u32 file_size | 10 bytes padding
    then sections, each 4-byte magic + u32 size + 8 bytes padding + body,
    padded to a 16-byte boundary with 0xAB after each one.

    LBL1: u32 group_count, then group_count x (u32 label_count, u32 offset), then
          per group label_count x (u8 name_len, name bytes, u32 string index).
          Labels are stored grouped, but the group a label came from is a hash
          bucket and carries no meaning here, so labels are read flat.

    TXT2: u32 string_count, then string_count u32 offsets, then the raw string
          bytes. The offsets are relative to the start of the section *body*
          (the `string_count` field), not to the first offset entry. Encoding
          byte 1 means UTF-16 in the header's byte order.

Only what this tool needs is implemented: LBL1 label names plus TXT2 strings.
Other sections (NLI1, ATO1, ATR1, TSY1) are skipped by their declared size.
Strings keep their trailing NUL and control codes; nothing is stripped, because
the caller records what the file actually holds.
"""
from __future__ import annotations

import struct

HEADER_MAGIC = b"MsgStdBn"
PADDING_CHAR = 0xAB
HEADER_SIZE = 32
SECTION_HEADER_SIZE = 16


def _u16(data, off, little):
    return struct.unpack_from("<H" if little else ">H", data, off)[0]


def _u32(data, off, little):
    return struct.unpack_from("<I" if little else ">I", data, off)[0]


def read_header(data):
    """Return (little_endian, encoding, section_count, declared_file_size)."""
    if data[:8] != HEADER_MAGIC:
        raise ValueError("not an MSBT file: bad magic %r" % (data[:8],))
    bom = data[8:10]
    if bom == b"\xfe\xff":
        little = False
    elif bom == b"\xff\xfe":
        little = True
    else:
        raise ValueError("bad byte order mark %r" % (bom,))
    encoding = data[12]
    if encoding not in (0, 1):
        raise ValueError("unknown text encoding byte %d" % encoding)
    return {
        "little_endian": little,
        "encoding": "utf-8" if encoding == 0 else "utf-16-le",
        "section_count": _u16(data, 14, little),
        "declared_file_size": _u32(data, 18, little),
        "actual_file_size": len(data),
    }


def read_labels(path):
    """Return {label: raw_text} for every label whose string decodes.

    Labels whose bytes do not decode are skipped and counted in
    `read_labels_counted`, so a caller can report them instead of silently
    losing them.
    """
    return read_labels_counted(path)[0]


def read_labels_counted(path):
    """Return ({label: text}, header_dict, undecodable_label_list)."""
    with open(path, "rb") as handle:
        data = handle.read()
    head = read_header(data)
    little = head["little_endian"]

    labels = {}
    strings = []

    off = HEADER_SIZE
    while off + 4 <= len(data):
        magic = data[off:off + 4]
        size = _u32(data, off + 4, little)
        body = off + SECTION_HEADER_SIZE
        if magic == b"LBL1":
            group_count = _u32(data, body, little)
            pos = body + 4
            counts = [_u32(data, pos + 8 * i, little) for i in range(group_count)]
            pos += 8 * group_count
            for count in counts:
                for _ in range(count):
                    name_len = data[pos]
                    pos += 1
                    name = data[pos:pos + name_len].decode("utf-8")
                    pos += name_len
                    labels[name] = _u32(data, pos, little)
                    pos += 4
            off = body + size
        elif magic == b"TXT2":
            count = _u32(data, body, little)
            offsets = [_u32(data, body + 4 + 4 * i, little) for i in range(count)]
            end = body + size
            strings = [
                data[body + offsets[i]:(body + offsets[i + 1]) if i + 1 < count else end]
                for i in range(count)
            ]
            off = end
        else:
            off = body + size
        while off < len(data) and data[off] == PADDING_CHAR:
            off += 1

    out = {}
    undecodable = []
    for name, index in sorted(labels.items()):
        if index >= len(strings):
            undecodable.append((name, "string index %d out of range" % index))
            continue
        raw = strings[index]
        try:
            out[name] = raw.decode(head["encoding"])
        except UnicodeDecodeError as exc:
            undecodable.append((name, str(exc)))
    return out, head, undecodable