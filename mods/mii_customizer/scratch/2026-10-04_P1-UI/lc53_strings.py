"""Scratch: dump the string constant table of a Lua 5.3 .lc chunk (SSBU ui/script).

Verified target: the .lc files under ui/script/menu/chara_make/ start with the
standard Lua 5.3 header 1b 4c 75 61 53 00 19 93 0d 0a 1a 0a.
Read-only; prints the constants and upvalue/local names it can walk.

Usage: python lc53_strings.py <file.lc> [max_chars_per_string]
"""
import struct
import sys

TYPES = {
    0: "nil", 1: "boolean", 3: "number", 4: "string", 6: "function",
    7: "userdata", 8: "thread",
}


class R:
    def __init__(self, d):
        self.d = d
        self.p = 0

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def raw(self, n):
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def uint(self, n):
        v = 0
        for i in range(n):
            v = (v << 8) | self.d[self.p + i]
        self.p += n
        return v

    def uleb128(self):
        v = 0
        while True:
            b = self.u8()
            v = (v << 7) | (b & 0x7F)
            if not (b & 0x80):
                return v


def read_string(r):
    # Lua 5.3 dumps: dumpsize is a varint too (LEB128 without continuation past
    # 7 bits is wrong; the format uses a full varint for both size and data).
    size = 0
    while True:
        b = r.u8()
        size = (size << 7) | (b & 0x7F)
        if not (b & 0x80):
            break
    return r.raw(size - 1).decode("utf-8", "replace")


def read_int(r):
    return int.from_bytes(r.raw(r.u8()), "little", signed=True)


def read_const(r):
    t = r.u8()
    if t == 0:
        return None
    if t == 1:
        return r.u8() != 0
    if t == 3:
        return read_int(r)
    if t == 4:
        return read_string(r)
    if t == 7:  # userdata: len + ptr-ish
        return "<userdata %d>" % r.uleb128()
    return "<type %d>" % t


def dump(path, limit=200):
    d = open(path, "rb").read()
    assert d[:4] == b"\x1bLua", "not a Lua chunk"
    ver = d[4]
    fmt = d[6]
    print("== %s" % path)
    print("   lua version byte %d, format %d, size %d bytes" % (ver, fmt, len(d)))
    # Lua 5.3 header: sig(4) ver(1) fmt(1) LUAC_DATA(6) cint(1) sizet(1)
    # instr(1) IntegerSize(1) LUAC_INT(IntegerSize) LUAC_NUM(8)
    cint, sizet, instr, isize = d[12], d[13], d[14], d[15]
    r = R(d)
    r.p = 16 + isize + 8
    print("   cint=%d sizet=%d instr_size=%d IntegerSize=%d" % (cint, sizet, instr, isize))
    print("   header ends at 0x%02x" % r.p)
    func = r.u8()                   # LUAC_TSOURCE
    nup = r.uleb128()
    print("   LUAC_TSOURCE=%d, nupvalues=%d" % (func, nup))

    linedefined = r.uleb128()
    lastlinedefined = r.uleb128()
    print("   lines %d..%d" % (linedefined, lastlinedefined))
    nun = r.u8()     # numparams
    is_vararg = r.u8()
    maxstack = r.u8()
    print("   numparams=%d is_vararg=%d maxstacksize=%d" % (nun, is_vararg, maxstack))

    code = [r.uint(instr) for _ in range(r.uleb128())]
    print("   %d instructions" % len(code))

    for _ in range(r.uleb128()):     # constants
        c = read_const(r)
        if isinstance(c, str) and len(c) > limit:
            c = c[:limit] + "...[%d chars]" % len(c)
        print("   const: %s" % (repr(c),))

    for _ in range(r.uleb128()):     # upvalues
        r.raw(1)
    for kind in (3, 1, 2):           # upvalue names, then nested protos
        for _ in range(r.uleb128()):
            print("   name[%d]: %s" % (kind, read_string(r)))
        if kind == 1:
            break
    for i in range(r.uleb128()):    # line info
        r.uleb128()
    for _ in range(r.uleb128()):     # locvars
        read_string(r)
        r.uleb128()
        r.uleb128()
    for _ in range(r.uleb128()):     # upvalue line info
        r.uleb128()


if __name__ == "__main__":
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    for p in sys.argv[1:] if len(sys.argv) > 2 else sys.argv[1:2]:
        dump(p, lim)