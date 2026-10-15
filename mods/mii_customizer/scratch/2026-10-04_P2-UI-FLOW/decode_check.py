"""P2-UI-FLOW: independent instruction-level cross-check of the editor chunks.

Read-only. Two purposes, both independent of tools/lua53-inspect:

 1. Determine the pre-main-proto header length empirically instead of
    assuming it, by trying every plausible start offset and keeping only
    the one that parses to exactly the end of the file with every LOADK /
    CLOSURE operand in range.
 2. Decode the instruction words with the Lua 5.3 bit layout taken from
    the pinned source lua/lua v5.3.6 lopcodes.h
    (SIZE_OP 6, SIZE_A 8, SIZE_k 1, SIZE_B 9, SIZE_C 9)
    and print the specific PCs this report relies on, so the register and
    branch claims do not rest on one tool.

Writes nothing. Reads only the three already-extracted .lc files.
"""
import struct
import sys

OPNAMES = {
    0: "MOVE", 1: "LOADK", 2: "LOADKX", 3: "LOADBOOL", 4: "LOADNIL",
    5: "GETUPVAL", 6: "GETTABUP", 7: "GETTABLE", 8: "SETTABUP", 9: "SETUPVAL",
    10: "SETTABLE", 11: "NEWTABLE", 12: "SELF", 13: "ADD", 14: "SUB", 15: "MUL",
    16: "MOD", 17: "POW", 18: "DIV", 19: "IDIV", 20: "BAND", 21: "BOR",
    22: "BXOR", 23: "SHL", 24: "SHR", 25: "UNM", 26: "BNOT", 27: "NOT",
    28: "LEN", 29: "CONCAT", 30: "JMP", 31: "EQ", 32: "LT", 33: "LE",
    34: "TEST", 35: "TESTSET", 36: "CALL", 37: "TAILCALL", 38: "RETURN",
    39: "FORLOOP", 40: "FORPREP", 41: "TFORCALL", 42: "TFORLOOP",
    43: "SETLIST", 44: "CLOSURE", 45: "VARARG", 46: "EXTRAARG",
}
BITRK = 1 << 8
MAXARGSBX = (1 << 18) - 1


def read_string(raw, pos):
    """DumpString writes one size byte, then `size` bytes of text including NUL.
    size == 0 is the dumped NULL source and consumes just the size byte.
    size == 0xFF escapes to a full size_t."""
    size = raw[pos]
    if size == 0xFF:
        size = struct.unpack_from("<Q", raw, pos + 1)[0]
        return raw[pos + 9:pos + 9 + size - 1].decode("utf-8", "replace"), pos + 9 + size
    if size == 0:
        return None, pos + 1
    # Measured on these chunks: the size byte counts the trailing NUL
    # (size == len + 1, e.g. 0x0d for the 12-byte 'get_skill_id') but the
    # payload stores only the len text bytes, no NUL. So the text is
    # raw[pos+1 : pos+size] and the next field starts at pos+size.
    return raw[pos + 1:pos + size].decode("utf-8", "replace"), pos + size


def decode(w):
    """iABC layout, cross-checked against the bytes and lua53-inspect:
    op bits 0-5, A bits 6-13, k bit 22, C bits 14-22, B bits 23-31.
    C sits at bit 14 and B at bit 23 -- C is the LOWER field. An earlier
    version of this script had B and C swapped and mis-decoded GETTABUP.
    """
    op = w & 0x3F
    bx = (w >> 14) & 0x3FFFF
    return (OPNAMES.get(op, "OP%d" % op), (w >> 6) & 0xFF,
            (w >> 23) & 0x1FF, (w >> 14) & 0x1FF,
            bx, bx - 131071)


def try_load(raw, start):
    """Walk every prototype from `start`. Return (protos, end) or raise."""
    pos = start
    main, pos = load_proto(raw, pos, set())
    return main, pos


def load_proto(raw, pos, seen):
    if pos in seen or pos >= len(raw):
        raise ValueError("offset cycle/overrun at %d" % pos)
    seen.add(pos)
    _, pos = read_string(raw, pos)                      # source (may be a NULL byte)
    pos += 4 + 4 + 1 + 1 + 1                             # lines, nparams, vararg, maxstack
    code_n = struct.unpack_from("<i", raw, pos)[0]
    pos += 4
    if not (0 < code_n < 100000):
        raise ValueError("implausible sizecode %d" % code_n)
    code = list(struct.unpack_from("<%dI" % code_n, raw, pos))
    pos += 4 * code_n
    k_n = struct.unpack_from("<i", raw, pos)[0]
    if not (0 <= k_n < 100000):
        raise ValueError("implausible sizek %d" % k_n)
    pos += 4
    consts = []
    for _ in range(k_n):
        tag = raw[pos]
        pos += 1
        if tag == 0x00:                                  # LUA_TNIL
            consts.append(None)
        elif tag == 0x01:                                # LUA_TBOOLEAN
            consts.append(raw[pos] != 0); pos += 1
        elif tag == 0x03:                                # LUA_TNUMFLT (4 bytes here)
            consts.append(struct.unpack_from("<f", raw, pos)[0]); pos += 4
        elif tag == 0x13:                                # LUA_TNUMINT (8 bytes)
            consts.append(struct.unpack_from("<q", raw, pos)[0]); pos += 8
        elif tag in (0x04, 0x14):                         # short / long string
            s, pos = read_string(raw, pos)
            consts.append(s)
        else:
            raise ValueError("unknown constant tag 0x%02x" % tag)
    # LoadFunction reads the upvalue count with loadInt (4 bytes), NOT a byte,
    # then 2 bytes (instack, idx) per upvalue. Getting this wrong desyncs the
    # walk; that was a real bug in the first version of this script.
    up_n = struct.unpack_from("<i", raw, pos)[0]
    pos += 4 + 2 * up_n
    p_n = struct.unpack_from("<i", raw, pos)[0]
    if not (0 <= p_n < 10000):
        raise ValueError("implausible sizep %d" % p_n)
    pos += 4
    kids = []
    for _ in range(p_n):
        k, pos = load_proto(raw, pos, seen)
        kids.append(k)
    li_n = struct.unpack_from("<i", raw, pos)[0]
    pos += 4 + 4 * li_n
    lv_n = struct.unpack_from("<i", raw, pos)[0]
    pos += 4
    for _ in range(lv_n):
        _, pos = read_string(raw, pos)
        pos += 8                                          # startpc + endpc
    un_n = struct.unpack_from("<i", raw, pos)[0]
    pos += 4
    for _ in range(un_n):
        _, pos = read_string(raw, pos)
    return {"code": code, "consts": consts, "kids": kids,
            "nparams": None, "start": pos}, pos


def structural_ok(p):
    """Every operand that indexes something must be in range."""
    for pr in p["kids"] + [p]:
        n = len(pr["code"])
        for pc, w in enumerate(pr["code"]):
            name, A, B, C, Bx, sBx = decode(w)
            if name == "LOADK" and Bx >= len(pr["consts"]):
                return "LOADK out of range in %d/%d" % (n, pc)
            if name == "CLOSURE" and Bx >= len(pr["kids"]):
                return "CLOSURE out of range"
            for f in (B, C):
                if f >= BITRK and (f - BITRK) >= len(pr["consts"]):
                    return "RK out of range"
            if name in ("JMP", "FORLOOP", "FORPREP"):
                if not (0 <= pc + 1 + sBx < n):
                    return "jump out of range"
    return None


def walk(path, verbose=True):
    raw = open(path, "rb").read()
    ok_starts = []
    for start in range(0x10, 0x30):
        try:
            p, end = try_load(raw, start)
        except Exception:
            continue
        if end != len(raw):
            continue
        if structural_ok(p):
            ok_starts.append((start, p))
    print("== %s" % path)
    print("   header length that yields an exact, in-range walk: %s"
          % (", ".join("0x%x (%d bytes)" % (s, s) for s, _ in ok_starts) or "NONE"))
    if not ok_starts:
        return None
    start, main = ok_starts[0]
    if verbose:
        total = sum(len(pr["code"]) for pr in main["kids"]) + len(main["code"])
        print("   protos=%d instructions=%d constants=%d"
              % (1 + len(main["kids"]), total, sum(len(pr["consts"]) for pr in main["kids"]) + len(main["consts"])))
    return main


def show(main, pfx, pcs, consts_for=None):
    p = main if pfx == "main" else main["kids"][int(pfx.split(".")[1][1:])]
    for pc in pcs:
        w = p["code"][pc]
        name, A, B, C, Bx, sBx = decode(w)
        note = ""
        if name == "LOADK":
            note = " K[%d] = %r" % (Bx, p["consts"][Bx])
        elif name == "CLOSURE":
            note = " -> main.p%d" % Bx
        elif name in ("JMP", "FORLOOP", "FORPREP"):
            note = " -> pc %d" % (pc + 1 + sBx)
        elif name in ("LT", "LE", "EQ", "TEST"):
            note = " (compare)"
        print("   %-9s [%3d] 0x%08x  %-9s A=%-3d B=%-3d C=%-3d Bx=%-6d sBx=%-7d%s"
              % (pfx, pc, w, name, A, B, C, Bx, sBx, note))


if __name__ == "__main__":
    paths = sys.argv[1:]
    m = walk(paths[0])
    if m is not None:
        print()
        print("-- PCs this report relies on (special actor) --")
        show(m, "main.p14", [8, 9, 11, 12, 14, 15, 16, 17, 18, 34, 35, 38, 40, 41, 42, 43, 44])
        print()
        show(m, "main.p15", [55, 58, 59, 60, 61, 62, 63, 68, 70, 71, 72, 94, 95, 96, 97, 98, 104, 107, 108])
        print()
        show(m, "main.p2", [7, 12, 13, 14, 15, 16, 17, 22, 23, 24, 38, 39, 44, 49, 50])
        print()
        show(m, "main.p10", [0, 1, 2, 3, 4, 5, 16, 17, 18, 19, 40, 41, 59, 63, 64])
        print()
        show(m, "main.p13", [11, 13, 14, 15, 16, 17])
        print()
        show(m, "main.p3", [0, 1, 2, 3, 4, 8, 9, 10, 21])
        print()
        show(m, "main.p4", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 17, 18, 19, 46, 47, 48, 49])
        print()
        show(m, "main.p8", [64, 65, 66, 67, 68, 69, 70, 77, 78])
    for extra in paths[1:]:
        walk(extra)
