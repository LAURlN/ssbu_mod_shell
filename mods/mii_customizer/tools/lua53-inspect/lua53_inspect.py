#!/usr/bin/env python3
"""Bounded inspector for Lua 5.3 precompiled chunks (``.lc``).

This tool parses a dumped Lua 5.3 chunk the same way the reference loader
``lundump.c`` does, records the exact byte offset of every field it reads, and
can decode the subset of opcodes needed to answer counting / table-field /
branch / call questions. Anything it cannot decode stays ``unknown`` -- it is
never turned into invented Lua source.

It can also *write*: :func:`encode_chunk` re-serialises a parsed chunk in the
exact field order the reference dumper ``ldump.c`` uses, and ``roundtrip``
proves the result is byte-identical. Since P2-LUA-EDIT it also performs three
guarded edits -- :func:`append_constant`, :func:`patch_instruction` and
:func:`insert_instructions` -- each of which validates the request against the
pinned format, raises :class:`EncodeError` without writing anything when it
cannot prove the result safe, and refuses insertion, deletion or reordering of
prototypes, upvalue edits and any kind of compiler. Round-tripping real chunks
and mutating them is evidence about the **bytes only**. It says nothing about
whether the game would load a modified chunk.

Format authority (pinned, tier C):
  lua/lua, tag v5.3.6
  - lundump.c   https://github.com/lua/lua/blob/v5.3.6/lundump.c
  - lopcodes.h  https://github.com/lua/lua/blob/v5.3.6/lopcodes.h
  - lopcodes.c  https://github.com/lua/lua/blob/v5.3.6/lopcodes.c
  - lobject.h   https://github.com/lua/lua/blob/v5.3.6/lobject.h
This is Lua 5.3, *not* LuaU (which uses a different, extended chunk format).

Deliberate differences from ``lundump.c``, all of them parse-time safety:
  * every read is bounds-checked and raises :class:`ParseError` naming the
    byte offset instead of the C loader's ``error(S, "truncated")``;
  * an unknown constant type tag raises instead of ``lua_assert(0)``;
  * structure sizes are read from the header (as the C loader does) but are
    sanity-checked, so a garbage size byte cannot cause a huge allocation;
  * the interpreter is *not* executed and there is deliberately no decompiler.

Usage examples (all paths relative to the workspace root)::

    python3 lua53_inspect.py header    some.lc
    python3 lua53_inspect.py summary   some.lc
    python3 lua53_inspect.py protos    some.lc
    python3 lua53_inspect.py dis       some.lc [max_string_len]
    python3 lua53_inspect.py constants some.lc
    python3 lua53_inspect.py xref      some.lc SKILL_COMMAND_NUM
    python3 lua53_inspect.py verify    some.lc other.lc ...
    python3 lua53_inspect.py roundtrip some.lc other.lc ...
    python3 lua53_inspect.py encode    some.lc out.lc
    python3 lua53_inspect.py setconst  some.lc out.lc main 1 "new text"
    python3 lua53_inspect.py appendconst some.lc out.lc main integer 7
    python3 lua53_inspect.py patchins  some.lc out.lc main 12 MOVE A=3 B=3
    python3 lua53_inspect.py insertins some.lc out.lc main 5 1 LOADK A=0 Bx=3
    python3 lua53_inspect.py compare   a.lc b.lc
    python3 lua53_inspect.py synth     out.lc

``verify`` prints one line per file and exits non-zero if any file fails.
"""

from __future__ import annotations

import struct
import sys
from typing import Any

__all__ = [
    "const_uses",
    "EncodeError",
    "ParseError",
    "Header",
    "Proto",
    "Constant",
    "Instruction",
    "check_header",
    "load_chunk",
    "walk",
    "encode_chunk",
    "set_string_constant",
    "append_constant",
    "constant_reachability",
    "patch_instruction",
    "insert_instructions",
    "protected_pair",
    "find_proto",
    "build_instruction",
    "rk_operands",
    "b_arg_mode",
    "c_arg_mode",
    "build_synthetic_chunk",
    "diff_chunks",
]

# ---------------------------------------------------------------------------
# pinned constants from lua/lua v5.3.6
# ---------------------------------------------------------------------------

LUAC_VERSION = 0x53          # lundump.c: LUAC_VERSION (5.3)
LUAC_FORMAT = 0              # lundump.c: LUAC_FORMAT
LUA_SIGNATURE = b"\x1bLua"   # lundump.c: LUA_SIGNATURE
LUAC_DATA = b"\x19\x93\r\n\x1a\n"
LUAC_INT = 0x5678            # lundump.c: LUAC_INT
LUAC_NUM = 370.5             # lundump.c: LUAC_NUM
MAX_SHORT_STRING = 40        # LUAI_MAXSHORTLEN, llimits.h

# lobject.h: base type tags actually written by LoadConstants.
T_NIL = 0                    # LUA_TNIL
T_BOOLEAN = 1                # LUA_TBOOLEAN
T_NUMFLT = 3                 # LUA_TNUMBER | (0 << 4)
T_NUMINT = 3 | (1 << 4)      # LUA_TNUMINT   = 19
T_SHRSTR = 4                 # LUA_TSTRING | (0 << 4)
T_LNGSTR = 4 | (1 << 4)      # LUA_TLNGSTR   = 20

_TAG_NAMES = {
    T_NIL: "nil",
    T_BOOLEAN: "boolean",
    T_NUMFLT: "float",
    T_NUMINT: "integer",
    T_SHRSTR: "string",
    T_LNGSTR: "string",
}

# lopcodes.h: argument sizes / positions.
SIZE_OP, SIZE_A, SIZE_B, SIZE_C = 6, 8, 9, 9
SIZE_Bx = SIZE_C + SIZE_B     # 18
SIZE_Ax = SIZE_Bx + SIZE_A    # 26
POS_OP, POS_A, POS_C, POS_B = 0, 6, 14, 23
POS_Bx, POS_Ax = POS_C, POS_A
MAXARG_Bx = (1 << SIZE_Bx) - 1
MAXARG_sBx = MAXARG_Bx >> 1   # 131071
# lopcodes.h:74-76, the per-field maxima. Not used by the decoder (which only
# masks) but the mutators need them to refuse an out-of-range field instead of
# silently truncating it into the word.
MAXARG_A = (1 << SIZE_A) - 1   # 255
MAXARG_B = (1 << SIZE_B) - 1   # 511
MAXARG_C = (1 << SIZE_C) - 1   # 511
MAXARG_Ax = (1 << SIZE_Ax) - 1  # 67108863
BITRK = 1 << (SIZE_B - 1)     # 256
NUM_OPCODES = 47              # OP_MOVE .. OP_EXTRAARG inclusive

# lopcodes.c: luaP_opnames, index == opcode number.
OPNAMES = [
    "MOVE", "LOADK", "LOADKX", "LOADBOOL", "LOADNIL", "GETUPVAL",
    "GETTABUP", "GETTABLE", "SETTABUP", "SETUPVAL", "SETTABLE",
    "NEWTABLE", "SELF", "ADD", "SUB", "MUL", "MOD", "POW", "DIV", "IDIV",
    "BAND", "BOR", "BXOR", "SHL", "SHR", "UNM", "BNOT", "NOT", "LEN",
    "CONCAT", "JMP", "EQ", "LT", "LE", "TEST", "TESTSET", "CALL",
    "TAILCALL", "RETURN", "FORLOOP", "FORPREP", "TFORCALL", "TFORLOOP",
    "SETLIST", "CLOSURE", "VARARG", "EXTRAARG",
]
assert len(OPNAMES) == NUM_OPCODES

# lopcodes.c: luaP_opmodes, packed as opmode(T, A, B, C, mode) values.
_OPARG_N, _OPARG_U, _OPARG_R, _OPARG_K = 0, 1, 2, 3
_IABC, _IABX, _IASBX, _IAX = 0, 1, 2, 3


def _opmode(t, a, b, c, m):
    return (t << 7) | (a << 6) | (b << 4) | (c << 2) | m


OPMODES = [
    _opmode(0, 1, _OPARG_R, _OPARG_N, _IABC),    # MOVE
    _opmode(0, 1, _OPARG_K, _OPARG_N, _IABX),    # LOADK
    _opmode(0, 1, _OPARG_N, _OPARG_N, _IABX),    # LOADKX
    _opmode(0, 1, _OPARG_U, _OPARG_U, _IABC),    # LOADBOOL
    _opmode(0, 1, _OPARG_U, _OPARG_N, _IABC),    # LOADNIL
    _opmode(0, 1, _OPARG_U, _OPARG_N, _IABC),    # GETUPVAL
    _opmode(0, 1, _OPARG_U, _OPARG_K, _IABC),    # GETTABUP
    _opmode(0, 0, _OPARG_R, _OPARG_K, _IABC),    # GETTABLE
    _opmode(0, 0, _OPARG_K, _OPARG_K, _IABC),    # SETTABUP
    _opmode(0, 0, _OPARG_U, _OPARG_N, _IABC),    # SETUPVAL
    _opmode(0, 0, _OPARG_K, _OPARG_K, _IABC),    # SETTABLE
    _opmode(0, 1, _OPARG_U, _OPARG_U, _IABC),    # NEWTABLE
    _opmode(0, 1, _OPARG_R, _OPARG_K, _IABC),    # SELF
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # ADD
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # SUB
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # MUL
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # MOD
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # POW
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # DIV
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # IDIV
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # BAND
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # BOR
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # BXOR
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # SHL
    _opmode(0, 1, _OPARG_K, _OPARG_K, _IABC),    # SHR
    _opmode(0, 0, _OPARG_R, _OPARG_N, _IABC),    # UNM
    _opmode(0, 0, _OPARG_R, _OPARG_N, _IABC),    # BNOT
    _opmode(0, 0, _OPARG_R, _OPARG_N, _IABC),    # NOT
    _opmode(0, 0, _OPARG_R, _OPARG_N, _IABC),    # LEN
    _opmode(0, 0, _OPARG_R, _OPARG_R, _IABC),    # CONCAT
    _opmode(0, 0, _OPARG_R, _OPARG_N, _IASBX),   # JMP
    _opmode(1, 0, _OPARG_K, _OPARG_K, _IABC),    # EQ
    _opmode(1, 0, _OPARG_K, _OPARG_K, _IABC),    # LT
    _opmode(1, 0, _OPARG_K, _OPARG_K, _IABC),    # LE
    _opmode(1, 0, _OPARG_N, _OPARG_U, _IABC),    # TEST
    _opmode(1, 1, _OPARG_R, _OPARG_U, _IABC),    # TESTSET
    _opmode(0, 1, _OPARG_U, _OPARG_U, _IABC),    # CALL
    _opmode(0, 1, _OPARG_U, _OPARG_U, _IABC),    # TAILCALL
    _opmode(0, 0, _OPARG_U, _OPARG_N, _IABC),    # RETURN
    _opmode(0, 1, _OPARG_R, _OPARG_N, _IASBX),   # FORLOOP
    _opmode(0, 1, _OPARG_R, _OPARG_N, _IASBX),   # FORPREP
    _opmode(0, 0, _OPARG_N, _OPARG_U, _IABC),    # TFORCALL
    _opmode(0, 1, _OPARG_R, _OPARG_N, _IASBX),   # TFORLOOP
    _opmode(0, 0, _OPARG_U, _OPARG_U, _IABC),    # SETLIST
    _opmode(0, 1, _OPARG_U, _OPARG_N, _IABX),    # CLOSURE
    _opmode(0, 1, _OPARG_U, _OPARG_N, _IABC),    # VARARG
    _opmode(0, 0, _OPARG_U, _OPARG_U, _IAX),     # EXTRAARG
]
assert len(OPMODES) == NUM_OPCODES

MODE_NAMES = {_IABC: "iABC", _IABX: "iABx", _IASBX: "iAsBx", _IAX: "iAx"}

# lopcodes.h:274-278, enum OpArgMask.
ARG_NAMES = {_OPARG_N: "OpArgN", _OPARG_U: "OpArgU", _OPARG_R: "OpArgR",
             _OPARG_K: "OpArgK"}
# lopcodes.h:143, ``#define MAXINDEXRK (BITRK - 1)`` == 255. A constant at a
# higher index can still be reached by LOADK's Bx (lopcodes.h:172) but not by
# any RK operand, so appendconst reports which of the two applies.
MAXINDEXRK = BITRK - 1


def b_arg_mode(op: int) -> int:
    """B operand mode of ``op``: ``getBMode`` (lopcodes.h:284)."""
    return (OPMODES[op] >> 4) & 3


def c_arg_mode(op: int) -> int:
    """C operand mode of ``op``: ``getCMode`` (lopcodes.h:285)."""
    return (OPMODES[op] >> 2) & 3


def rk_operands(inst: "Instruction") -> "list[tuple[str, int]]":
    """``(field, constant index)`` for each RK operand of ``inst``.

    An operand is an RK operand only when ``luaP_opmodes`` says its argument
    mode is ``OpArgK`` *and* the instruction is iABC. Both halves matter:

    * ``OpArgK`` (lopcodes.h:278) is "argument is a constant or
      register/constant". ``OpArgU`` fields are plain values and ``OpArgR``
      fields are registers or jump offsets, so neither can name a constant even
      when bit 256 happens to be set in the word. ``GETTABUP`` B is
      ``OpArgU`` (lopcodes.c:82, an upvalue index) and ``TEST`` C is
      ``OpArgU`` (lopcodes.c:110), so neither is an RK operand.
    * Only iABC has independent B and C fields. In iAsBx (lopcodes.h:32, 50)
      B and C are simply the two halves of Bx, so their bit 8 is part of the
      jump offset and means nothing about constants. iABx has a single Bx.
    """
    if inst.op >= NUM_OPCODES or inst.mode != _IABC:
        return []
    out = []
    if b_arg_mode(inst.op) == _OPARG_K and inst.b & BITRK:
        out.append(("B", inst.b & ~BITRK))
    if c_arg_mode(inst.op) == _OPARG_K and inst.c & BITRK:
        out.append(("C", inst.c & ~BITRK))
    return out


class ParseError(Exception):
    """Raised for any malformed or unsupported chunk input.

    The message always carries the byte offset at which parsing stopped, so a
    failure can be reproduced by hand from the raw file.
    """


# ---------------------------------------------------------------------------
# byte reader
# ---------------------------------------------------------------------------


class _Reader:
    """Bounds-checked little-endian reader over a chunk's bytes.

    Endianness is not assumed from the host: the chunk header carries the
    reference ``LUAC_INT`` and ``LUAC_NUM`` values, so a chunk that does not
    match them is rejected in :func:`check_header` before anything else is
    decoded.
    """

    def __init__(self, data: bytes, sizes: "Header"):
        self.data = data
        self.sizes = sizes
        self.pos = 0

    def fail(self, msg: str, off: "int | None" = None) -> "ParseError":
        return ParseError(
            "%s at offset 0x%x (%d), chunk length %d"
            % (msg, self.pos if off is None else off,
               self.pos if off is None else off, len(self.data))
        )

    def _need(self, n: int) -> int:
        if self.pos + n > len(self.data):
            raise self.fail("truncated: need %d byte(s)" % n)
        at = self.pos
        self.pos += n
        return at

    def byte(self) -> int:
        self._need(1)
        return self.data[self.pos - 1]

    def raw(self, n: int) -> bytes:
        at = self._need(n)
        return self.data[at:at + n]

    def block(self, n: int) -> None:
        """Skip ``n`` bytes, recording nothing (used for vectors)."""
        self._need(n)

    def int_(self) -> int:
        n = self.sizes.int_size
        raw = self.raw(n)
        return int.from_bytes(raw, "little", signed=True)

    def number(self) -> float:
        raw = self.raw(self.sizes.num_size)
        if self.sizes.num_size == 4:
            return struct.unpack("<f", raw)[0]
        return struct.unpack("<d", raw)[0]

    def integer(self) -> int:
        raw = self.raw(self.sizes.integer_size)
        return int.from_bytes(raw, "little", signed=True)


# ---------------------------------------------------------------------------
# header
# ---------------------------------------------------------------------------


class Header:
    """The parsed ``checkHeader()`` state of a chunk."""

    __slots__ = (
        "version", "format", "int_size", "size_t_size", "instr_size",
        "integer_size", "num_size", "luac_int", "luac_num", "size",
        "main_nupvalues", "nupvalues_offset", "body_offset",
    )

    def __init__(self, **kw: Any) -> None:
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    @property
    def float_kind(self) -> str:
        if self.num_size == 4:
            return "float32"
        if self.num_size == 8:
            return "float64"
        return "float%d" % self.num_size

    def as_dict(self) -> "dict[str, Any]":
        return {k: getattr(self, k) for k in self.__slots__}


def check_header(data: bytes) -> "tuple[Header, _Reader]":
    """Validate a chunk header and return ``(header, positioned reader)``.

    Mirrors ``checkHeader()`` in lundump.c, including the exact expected
    values, so a LuaU chunk or a different Lua version is rejected up front
    with a specific message rather than decoding into nonsense.
    """
    if len(data) < 4 or data[:4] != LUA_SIGNATURE:
        raise ParseError(
            "not a Lua chunk: signature %r != %r (need at least 4 bytes, got %d)"
            % (data[:4], LUA_SIGNATURE, len(data))
        )

    class _Sizer:
        int_size = 4
        size_t_size = 8
        instr_size = 4
        integer_size = 8
        num_size = 8

    sizes = _Sizer()
    r = _Reader(data, sizes)          # type: ignore[arg-type]
    r.pos = 4                         # first signature byte already consumed

    version = r.byte()
    if version != LUAC_VERSION:
        raise ParseError(
            "version mismatch at offset 0x4: 0x%02x != 0x%02x "
            "(this tool reads Lua 5.3 chunks, not Lua %s)"
            % (version, LUAC_VERSION, _version_name(version))
        )
    fmt = r.byte()
    if fmt != LUAC_FORMAT:
        raise ParseError("format mismatch at offset 0x5: 0x%02x != 0x%02x"
                         % (fmt, LUAC_FORMAT))
    if r.raw(len(LUAC_DATA)) != LUAC_DATA:
        raise ParseError("corrupted: LUAC_DATA mismatch at offset 0x6")

    for name, attr, off in (
        ("int", "int_size", 0x0c),
        ("size_t", "size_t_size", 0x0d),
        ("Instruction", "instr_size", 0x0e),
        ("lua_Integer", "integer_size", 0x0f),
        ("lua_Number", "num_size", 0x10),
    ):
        v = r.byte()
        if not 1 <= v <= 16:
            raise ParseError(
                "implausible %s size %d at offset 0x%x (header not a 5.3 chunk?)"
                % (name, v, off)
            )
        setattr(sizes, attr, v)

    # LUAC_INT / LUAC_NUM double as endianness and float-format checks.
    luac_int = r.integer()
    if luac_int != LUAC_INT:
        raise ParseError(
            "endianness mismatch: LUAC_INT 0x%x at offset 0x11 != 0x%x "
            "(chunk is big-endian or a non-standard build)" % (luac_int, LUAC_INT)
        )
    luac_num = r.number()
    if luac_num != LUAC_NUM:
        raise ParseError(
            "float format mismatch: LUAC_NUM %r at offset 0x11 != %r"
            % (luac_num, LUAC_NUM)
        )

    body_offset = r.pos
    # luaU_undump reads one byte for the main closure's upvalue count.
    nup_off = r.pos
    nup = r.byte()

    hdr = Header(
        version=version, format=fmt,
        int_size=sizes.int_size, size_t_size=sizes.size_t_size,
        instr_size=sizes.instr_size, integer_size=sizes.integer_size,
        num_size=sizes.num_size, luac_int=luac_int, luac_num=luac_num,
        size=len(data), main_nupvalues=nup, nupvalues_offset=nup_off,
        body_offset=body_offset,
    )
    return hdr, r


def _version_name(v: int) -> str:
    if 0x50 <= v <= 0x5F:
        return "5.%d" % (v - 0x50)
    if v == 0x54:
        return "5.4"
    return "0x%02x" % v


# ---------------------------------------------------------------------------
# data model
# ---------------------------------------------------------------------------


class Constant:
    """One entry of a prototype's constant table (``LoadConstants``)."""

    __slots__ = ("index", "offset", "tag", "tag_offset", "kind", "value",
                 "long_form")

    def __init__(self, index: int, offset: int, tag: int, tag_offset: int,
                 kind: str, value: Any, long_form: bool = False):
        self.index = index
        self.offset = offset          # offset of the payload
        self.tag = tag
        self.tag_offset = tag_offset  # offset of the type tag byte
        self.kind = kind
        self.value = value
        # ``LoadString`` reaches a full size_t only through a leading 0xFF
        # size byte. That byte is part of the file, so an encoder that always
        # chose the short form would not be byte-identical. Remembered here.
        self.long_form = long_form

    @property
    def is_string(self) -> bool:
        return self.kind == "string"

    @property
    def is_number(self) -> bool:
        return self.kind in ("float", "integer")

    def text(self, limit: int = 0) -> str:
        if self.kind == "string":
            s = self.value if isinstance(self.value, str) else repr(self.value)
            if limit and len(s) > limit:
                return "%s...[%d chars]" % (s[:limit], len(s))
            return s
        return repr(self.value)

    def __repr__(self) -> str:
        return "K[%d]@0x%x %s %s" % (self.index, self.tag_offset,
                                     self.kind, self.text(60))


class Instruction:
    """One decoded instruction word plus its file offset."""

    __slots__ = ("pc", "offset", "word", "op", "a", "b", "c", "bx", "sbx", "ax")

    def __init__(self, pc: int, offset: int, word: int):
        self.pc = pc
        self.offset = offset
        self.word = word
        self.op = word & ((1 << SIZE_OP) - 1)
        self.a = (word >> POS_A) & ((1 << SIZE_A) - 1)
        self.b = (word >> POS_B) & ((1 << SIZE_B) - 1)
        self.c = (word >> POS_C) & ((1 << SIZE_C) - 1)
        self.bx = (word >> POS_Bx) & MAXARG_Bx
        self.sbx = self.bx - MAXARG_sBx
        self.ax = (word >> POS_Ax) & ((1 << SIZE_Ax) - 1)

    # -- field accessors ---------------------------------------------------
    @property
    def name(self) -> str:
        return OPNAMES[self.op] if self.op < NUM_OPCODES else "OP_?"

    @property
    def mode(self) -> int:
        return OPMODES[self.op] & 3

    @property
    def mode_name(self) -> str:
        return MODE_NAMES[self.mode]

    @property
    def is_test(self) -> bool:
        """True when the next instruction must be a jump (``testTMode``)."""
        return bool(OPMODES[self.op] & (1 << 7))

    @property
    def sets_a(self) -> bool:
        return bool(OPMODES[self.op] & (1 << 6))

    def b_arg(self) -> int:
        """B as a signed jump offset for iAsBx, unsigned otherwise."""
        return self.sbx if self.mode == _IASBX else self.b

    def rk(self, proto: "Proto", which: str) -> str:
        """Resolve an RK operand (``lopcodes.h``: bit 256 selects a constant)."""
        raw = self.b if which == "B" else self.c
        if raw & BITRK:
            idx = raw & ~BITRK
            if idx < len(proto.constants):
                return "K[%d] %s" % (idx, proto.constants[idx].text(40))
            return "K[%d] <out of range>" % idx
        return "R[%d]" % raw

    def branch_target(self) -> "int | None":
        """Absolute pc target of a jump/test instruction, else ``None``."""
        if self.name in ("JMP", "FORLOOP", "FORPREP", "TFORLOOP"):
            return self.pc + 1 + self.sbx
        if self.is_test:
            return self.pc + 1
        return None

    def args_text(self) -> str:
        m = self.mode
        if m == _IABX:
            extra = ""
            if self.name == "CLOSURE":
                extra = ""
            return "A=%d Bx=%d%s" % (self.a, self.bx, extra)
        if m == _IASBX:
            return "A=%d sBx=%d -> pc %d" % (self.a, self.sbx,
                                             self.pc + 1 + self.sbx)
        if m == _IAX:
            return "Ax=%d" % self.ax
        return "A=%d B=%d C=%d" % (self.a, self.b, self.c)


class LocVar:
    __slots__ = ("name", "name_offset", "startpc", "endpc", "name_long")

    def __init__(self, name, name_offset, startpc, endpc, name_long=False):
        self.name = name
        self.name_offset = name_offset
        self.startpc = startpc
        self.endpc = endpc
        self.name_long = name_long


class Proto:
    """A parsed ``Proto``: code, constants, upvalues, nested protos, debug."""

    def __init__(self, path: str, offset: int):
        self.path = path              # e.g. "main" or "main.p0.p2"
        self.offset = offset          # offset of the first byte of this proto
        self.source: "str | None" = None
        self.source_offset = 0
        # ``LoadFunction`` substitutes the parent's source when the dumped
        # string is NULL, so ``source`` alone cannot say what was on disk.
        self.source_is_null = False
        self.source_long = False
        self.linedefined = 0
        self.lastlinedefined = 0
        self.numparams = 0
        self.is_vararg = 0
        self.maxstacksize = 0
        self.code_offset = 0
        self.code: "list[Instruction]" = []
        self.consts_offset = 0
        self.constants: "list[Constant]" = []
        self.upvals_offset = 0
        self.upvalues: "list[tuple[int, int]]" = []      # (instack, idx)
        self.protos_offset = 0
        self.protos: "list[Proto]" = []
        self.lineinfo_offset = 0
        self.lineinfo: "list[int]" = []
        self.locvars: "list[LocVar]" = []
        self.upvalue_names: "list[str | None]" = []
        # parallel to upvalue_names: per-name 0xFF-escape flags
        self.upvalue_names_long: "list[bool]" = []
        self.upvalue_names_offset = 0
        self.end_offset = 0            # first byte after this proto

    # -- convenience -------------------------------------------------------
    def iter_protos(self):
        yield self
        for p in self.protos:
            yield from p.iter_protos()

    @property
    def is_stripped(self) -> bool:
        """``lundump.c`` omits debug data when the chunk was stripped."""
        return self.source is None and not self.lineinfo and not self.locvars

    def const_by_text(self, needle: str) -> "list[Constant]":
        out = []
        for k in self.constants:
            if k.is_string and needle in (k.value or ""):
                out.append(k)
        return out

    def __repr__(self) -> str:
        return "<Proto %s code=%d consts=%d protos=%d @0x%x>" % (
            self.path, len(self.code), len(self.constants),
            len(self.protos), self.offset)


# ---------------------------------------------------------------------------
# loader
# ---------------------------------------------------------------------------


def _load_string(r: _Reader) -> "tuple[str | None, int, bool]":
    """``LoadString``: one size byte, 0xFF escaping to a full size_t.

    Note this is *not* a variable-length integer. The dumped size includes the
    trailing NUL, so the stored text is ``size - 1`` bytes. Size 0 means NULL.

    Returns ``(text_or_None, offset_of_size_byte, used_0xFF_escape)``. The
    escape flag is reported because the reference dumper only writes 0xFF when
    ``size >= 0xFF`` (ldump.c ``DumpString``), so re-deriving the width from the
    string length alone would be a guess. Recording it keeps the encoder exact.
    """
    size = r.byte()
    size_off = r.pos - 1
    long_form = False
    if size == 0xFF:
        long_form = True
        size = int.from_bytes(r.raw(r.sizes.size_t_size), "little")
    if size == 0:
        return None, size_off, long_form
    n = size - 1
    if n > len(r.data):
        raise r.fail("string length %d exceeds remaining chunk" % n, size_off)
    raw = r.raw(n)
    return raw.decode("utf-8", "surrogateescape"), size_off, long_form


def _load_const(r: _Reader, index: int) -> Constant:
    tag_off = r.pos
    tag = r.byte()
    payload_off = r.pos
    if tag == T_NIL:
        return Constant(index, payload_off, tag, tag_off, "nil", None)
    if tag == T_BOOLEAN:
        return Constant(index, payload_off, tag, tag_off, "boolean",
                        bool(r.byte()))
    if tag == T_NUMFLT:
        return Constant(index, payload_off, tag, tag_off, "float", r.number())
    if tag == T_NUMINT:
        return Constant(index, payload_off, tag, tag_off, "integer",
                        r.integer())
    if tag in (T_SHRSTR, T_LNGSTR):
        text, soff, long_form = _load_string(r)
        return Constant(index, soff, tag, tag_off, "string", text, long_form)
    raise r.fail(
        "unknown constant type tag %d (expected nil/boolean/float/integer/"
        "string)" % tag, tag_off
    )


def _load_function(r: _Reader, path: str, psource: "str | None") -> Proto:
    """``LoadFunction``, recursing through ``LoadProtos``."""
    f = Proto(path, r.pos)

    f.source, f.source_offset, f.source_long = _load_string(r)
    f.source_is_null = f.source is None
    if f.source is None:
        f.source = psource          # reuse parent's source, as lundump.c does
    f.linedefined = r.int_()
    f.lastlinedefined = r.int_()
    f.numparams = r.byte()
    f.is_vararg = r.byte()
    f.maxstacksize = r.byte()

    n = r.int_()
    if n < 0:
        raise r.fail("negative instruction count %d" % n)
    need = n * r.sizes.instr_size
    if need > len(r.data) - r.pos:
        raise r.fail("instruction count %d needs %d bytes, %d remain"
                     % (n, need, len(r.data) - r.pos))
    f.code_offset = r.pos
    fmt = {1: "<B", 2: "<H", 4: "<I", 8: "<Q"}.get(r.sizes.instr_size)
    if fmt is None:
        raise r.fail("unsupported Instruction size %d" % r.sizes.instr_size)
    for pc in range(n):
        off = r.pos
        word = struct.unpack(fmt, r.raw(r.sizes.instr_size))[0]
        f.code.append(Instruction(pc, off, word))

    n = r.int_()
    if n < 0:
        raise r.fail("negative constant count %d" % n)
    f.consts_offset = r.pos
    for i in range(n):
        f.constants.append(_load_const(r, i))

    n = r.int_()
    if n < 0:
        raise r.fail("negative upvalue count %d" % n)
    f.upvals_offset = r.pos
    for _ in range(n):
        instack = r.byte()
        idx = r.byte()
        f.upvalues.append((instack, idx))

    n = r.int_()
    if n < 0:
        raise r.fail("negative child proto count %d" % n)
    f.protos_offset = r.pos
    for i in range(n):
        f.protos.append(_load_function(r, "%s.p%d" % (path, i), f.source))

    n = r.int_()                                # lineinfo
    f.lineinfo_offset = r.pos
    if n < 0:
        raise r.fail("negative lineinfo count %d" % n)
    if n * r.sizes.int_size > len(r.data) - r.pos:
        raise r.fail("lineinfo count %d does not fit" % n)
    for _ in range(n):
        f.lineinfo.append(r.int_())

    n = r.int_()                                # locvars
    for _ in range(n):
        name, noff, name_long = _load_string(r)
        startpc = r.int_()
        endpc = r.int_()
        f.locvars.append(LocVar(name, noff, startpc, endpc, name_long))

    n = r.int_()                                # upvalue names
    f.upvalue_names_offset = r.pos
    # ldump.c DumpDebug() dumps the upvalue *name* count as 0 when the chunk
    # was stripped, while DumpUpvalues() keeps the real descriptor count. So
    # 0 names with N upvalues is the normal stripped shape, not a parse error.
    for _ in range(n):
        name, _off, name_long = _load_string(r)
        f.upvalue_names.append(name)
        f.upvalue_names_long.append(name_long)

    f.end_offset = r.pos
    return f


def load_chunk(data: bytes) -> "tuple[Header, Proto]":
    """Parse a full chunk; returns ``(header, main proto)``.

    The caller is responsible for the end-of-file consumption check; use
    :func:`verify` for the full set of checks.
    """
    hdr, r = check_header(data)
    main = _load_function(r, "main", None)
    return hdr, main


def walk(main: Proto):
    """Yield every proto in the chunk, parents before children."""
    return main.iter_protos()


# ---------------------------------------------------------------------------
# encoder (ldump.c field order, tier C)
# ---------------------------------------------------------------------------


class EncodeError(Exception):
    """Raised when a :class:`Proto` cannot be written back out.

    Every check here is about *this file's* consistency. Passing means the
    bytes were produced; it says nothing about whether any game would accept
    the result.
    """


class _Writer:
    """Little-endian writer using the widths recorded in the chunk header.

    Widths come from the parsed :class:`Header`, never from the host, so a
    chunk with 4-byte floats stays 4-byte floats.
    """

    def __init__(self, hdr: "Header"):
        self.hdr = hdr
        self.buf = bytearray()

    # -- primitives -----------------------------------------------------
    def byte(self, v: int, what: str = "byte") -> None:
        if not 0 <= v <= 0xFF:
            raise EncodeError("%s value %d does not fit in one byte"
                              % (what, v))
        self.buf.append(v)

    def raw(self, b: bytes) -> None:
        self.buf += b

    def int_(self, v: int, what: str = "int") -> None:
        n = self.hdr.int_size
        try:
            self.buf += int(v).to_bytes(n, "little", signed=True)
        except OverflowError:
            raise EncodeError("%s value %d does not fit in %d signed byte(s)"
                              % (what, v, n))

    def number(self, v: float, what: str = "lua_Number") -> None:
        n = self.hdr.num_size
        try:
            if n == 4:
                self.buf += struct.pack("<f", v)
            elif n == 8:
                self.buf += struct.pack("<d", v)
            else:
                raise EncodeError("unsupported lua_Number width %d" % n)
        except (OverflowError, struct.error) as exc:
            raise EncodeError("%s value %r does not fit in %d byte(s): %s"
                              % (what, v, n, exc))

    def integer(self, v: int, what: str = "lua_Integer") -> None:
        n = self.hdr.integer_size
        try:
            self.buf += int(v).to_bytes(n, "little", signed=True)
        except OverflowError:
            raise EncodeError("%s value %d does not fit in %d signed byte(s)"
                              % (what, v, n))

    def instruction(self, word: int) -> None:
        n = self.hdr.instr_size
        try:
            self.buf += int(word).to_bytes(n, "little", signed=False)
        except OverflowError:
            raise EncodeError("instruction 0x%x does not fit in %d byte(s)"
                              % (word, n))

    # -- strings --------------------------------------------------------
    def string(self, text: "str | None", long_form: bool = False,
               what: str = "string") -> None:
        """``DumpString``: NULL is one 0 byte; else size = len + 1.

        ``ldump.c`` writes a single size byte while ``size < 0xFF`` and the
        ``0xFF`` + full ``size_t`` escape otherwise. ``long_form`` forces the
        escape so a chunk that used it re-encodes identically.
        """
        if text is None:
            self.byte(0, what)
            return
        data = text.encode("utf-8", "surrogateescape")
        size = len(data) + 1            # dumped size includes the trailing NUL
        if long_form or size >= 0xFF:
            self.byte(0xFF, what)
            self.buf += size.to_bytes(self.hdr.size_t_size, "little")
        else:
            self.byte(size, what)
        self.buf += data


def _encode_const(w: _Writer, k: Constant) -> None:
    w.byte(k.tag, "constant tag")
    if k.kind == "nil":
        return
    if k.kind == "boolean":
        w.byte(1 if k.value else 0, "boolean")
        return
    if k.kind == "float":
        w.number(k.value, "float constant K[%d]" % k.index)
        return
    if k.kind == "integer":
        w.integer(k.value, "integer constant K[%d]" % k.index)
        return
    if k.kind == "string":
        w.string(k.value, k.long_form, "string constant K[%d]" % k.index)
        return
    raise EncodeError("cannot encode constant kind %r (K[%d])" % (k.kind,
                                                                  k.index))


def _encode_proto(w: _Writer, p: Proto) -> None:
    """``DumpFunction``: field order copied from ldump.c, not guessed."""
    # source: ldump.c writes NULL when stripped or identical to the parent's.
    w.string(None if p.source_is_null else p.source, p.source_long,
             "source of %s" % p.path)
    w.int_(p.linedefined, "linedefined")
    w.int_(p.lastlinedefined, "lastlinedefined")
    w.byte(p.numparams, "numparams of %s" % p.path)
    w.byte(p.is_vararg, "is_vararg of %s" % p.path)
    w.byte(p.maxstacksize, "maxstacksize of %s" % p.path)

    w.int_(len(p.code), "code count of %s" % p.path)
    for i in p.code:
        w.instruction(i.word)

    w.int_(len(p.constants), "constant count of %s" % p.path)
    for k in p.constants:
        _encode_const(w, k)

    w.int_(len(p.upvalues), "upvalue count of %s" % p.path)
    for n, (instack, idx) in enumerate(p.upvalues):
        w.byte(instack, "upvalue %d instack of %s" % (n, p.path))
        w.byte(idx, "upvalue %d idx of %s" % (n, p.path))

    w.int_(len(p.protos), "child proto count of %s" % p.path)
    for child in p.protos:
        _encode_proto(w, child)

    w.int_(len(p.lineinfo), "lineinfo count of %s" % p.path)
    for v in p.lineinfo:
        w.int_(v, "lineinfo entry of %s" % p.path)

    w.int_(len(p.locvars), "locvar count of %s" % p.path)
    for lv in p.locvars:
        w.string(lv.name, lv.name_long, "locvar name of %s" % p.path)
        w.int_(lv.startpc, "locvar startpc of %s" % p.path)
        w.int_(lv.endpc, "locvar endpc of %s" % p.path)

    w.int_(len(p.upvalue_names), "upvalue name count of %s" % p.path)
    for n, name in enumerate(p.upvalue_names):
        long_form = (n < len(p.upvalue_names_long)
                     and p.upvalue_names_long[n])
        w.string(name, long_form, "upvalue %d name of %s" % (n, p.path))


def encode_chunk(hdr: "Header", main: Proto) -> bytes:
    """Re-serialise a parsed chunk. Returns the complete file bytes.

    Mirrors ``luaU_dump``: ``DumpHeader``, the main closure's upvalue count,
    then ``DumpFunction`` over the whole prototype tree. The result is
    re-parsable by :func:`load_chunk`; use ``roundtrip`` to confirm it is also
    byte-identical to the input.
    """
    w = _Writer(hdr)
    w.raw(LUA_SIGNATURE)
    w.byte(hdr.version, "version")
    w.byte(hdr.format, "format")
    w.raw(LUAC_DATA)
    w.byte(hdr.int_size, "sizeof int")
    w.byte(hdr.size_t_size, "sizeof size_t")
    w.byte(hdr.instr_size, "sizeof Instruction")
    w.byte(hdr.integer_size, "sizeof lua_Integer")
    w.byte(hdr.num_size, "sizeof lua_Number")
    w.integer(LUAC_INT, "LUAC_INT")
    w.number(LUAC_NUM, "LUAC_NUM")
    w.byte(hdr.main_nupvalues, "main closure upvalue count")
    _encode_proto(w, main)
    return bytes(w.buf)


# ---------------------------------------------------------------------------
# mutation (bounded: one constant, nothing else)
# ---------------------------------------------------------------------------


def set_string_constant(main: Proto, proto_path: str, index: int,
                        text: str) -> Constant:
    """Replace one string constant's text; every other field is untouched.

    Refuses anything that is not a string constant. The type tag is recomputed
    the way ``ldump.c`` would (``LUA_TLNGSTR`` past ``LUAI_MAXSHORTLEN``),
    because the loader picks short/long storage from the size while the tag is
    what the dumper wrote.
    """
    target = None
    for p in walk(main):
        if p.path == proto_path:
            target = p
            break
    if target is None:
        raise EncodeError("no such prototype %r (known: %s)"
                          % (proto_path, ", ".join(q.path for q in walk(main))))
    if not 0 <= index < len(target.constants):
        raise EncodeError("proto %s has %d constant(s), so K[%d] does not exist"
                          % (proto_path, len(target.constants), index))
    k = target.constants[index]
    if k.kind != "string":
        raise EncodeError("K[%d] of %s is a %s constant, not a string; "
                          "this tool only rewrites string constants"
                          % (index, proto_path, k.kind))
    k.value = text
    k.long_form = False
    k.tag = T_SHRSTR if len(text) <= MAX_SHORT_STRING else T_LNGSTR
    return k


# ---------------------------------------------------------------------------
# guarded mutators: constants, one instruction, and code insertion
# ---------------------------------------------------------------------------
#
# Three rules govern every function in this section:
#
#  1. Refuse rather than guess. Anything that cannot be checked against the
#     pinned format is an error, never a default.
#  2. Decide from ``luaP_opmodes`` (lopcodes.c:74-123) and the opcode comments
#     in lopcodes.h (171-233), never from a hand-written opcode list.
#  3. Raise :class:`EncodeError` *before* touching the tree, so a refused
#     request leaves the in-memory chunk exactly as it was. The CLI turns that
#     into a non-zero exit and writes no file.
#
# Not implemented, deliberately: deleting instructions or constants, inserting
# or reordering prototypes, editing upvalue descriptors, and any kind of
# compiler. Those need a real reachability analysis this tool does not have.

EXIT_OK = 0
EXIT_REFUSED = 1        # the request was unsafe or unsupported; nothing written
EXIT_USAGE = 2          # the command line itself was wrong

# Which field names an instruction format actually has (lopcodes.h:32, and the
# CREATE_* macros at 117-124). Asking for a field the format does not have is a
# refusal, not something to silently drop.
_FIELD_ALLOWED = {
    _IABC: ("A", "B", "C"),
    _IABX: ("A", "Bx"),
    _IASBX: ("A", "sBx"),
    _IAX: ("Ax",),
}
_FIELD_RANGE = {
    "A": (0, MAXARG_A),                 # lopcodes.h:74
    "B": (0, MAXARG_B),                 # lopcodes.h:75
    "C": (0, MAXARG_C),                 # lopcodes.h:76
    "Bx": (0, MAXARG_Bx),               # lopcodes.h:60
    "sBx": (-MAXARG_sBx, MAXARG_sBx),   # lopcodes.h:112, SETARG_sBx at 115
    "Ax": (0, MAXARG_Ax),               # lopcodes.h:68
}


def find_proto(main: Proto, proto_path: str) -> Proto:
    """The prototype at ``proto_path``, or :class:`EncodeError` listing all."""
    for p in walk(main):
        if p.path == proto_path:
            return p
    raise EncodeError("no such prototype %r (known: %s)"
                      % (proto_path, ", ".join(q.path for q in walk(main))))


def _signed_range(width: int) -> "tuple[int, int]":
    return (-(1 << (width * 8 - 1)), (1 << (width * 8 - 1)) - 1)


# ---------------------------------------------------------------------------
# appendconst
# ---------------------------------------------------------------------------

APPENDABLE_KINDS = ("string", "integer", "float")


def constant_reachability(proto: Proto, index: int) -> str:
    """How a constant at ``index`` can be reached, from ``lopcodes.h``.

    ``MAXINDEXRK`` is ``BITRK - 1`` == 255 (lopcodes.h:143): the largest index
    that fits the low 8 bits of an RK operand once ``BITRK`` is set. At or
    below it a constant can be used *directly* by an iABC RK operand; above it
    only ``LOADK``'s 18-bit ``Bx`` (lopcodes.h:172) can name it.
    """
    if index < 0 or index >= len(proto.constants):
        return "index %d does not exist" % index
    if index <= MAXINDEXRK:
        return ("RK operand still possible: index %d <= MAXINDEXRK %d "
                "(BITRK leaves 8 bits, lopcodes.h:134/143); LOADK also works"
                % (index, MAXINDEXRK))
    if index <= MAXARG_Bx:
        return ("LOADK only: index %d > MAXINDEXRK %d, so no RK operand can "
                "name it; LOADK Bx reaches up to %d"
                % (index, MAXINDEXRK, MAXARG_Bx))
    return ("unreachable: index %d exceeds LOADK's Bx limit of %d"
            % (index, MAXARG_Bx))


def append_constant(main: Proto, hdr: Header, proto_path: str, kind: str,
                    value, at: "int | None" = None) -> Constant:
    """Append one constant to the END of one prototype's table.

    Appending is the only insertion this tool performs, and it is safe for a
    structural reason rather than a lucky one: ``LOADK``/``LOADKX`` and RK
    operands index the table *positionally* (lopcodes.h:172-173), so inserting
    or deleting anywhere but the end would silently re-point every later
    reference. ``at`` exists only so a caller can be told, explicitly, that a
    non-end position is refused.

    Numbers use the *chunk's* widths from the parsed header, not the host's:
    an integer is written at ``sizeof lua_Integer`` (``LoadInteger`` reads that
    many bytes, lundump.c:78-83) and a float at ``sizeof lua_Number``
    (``LoadNumber``, lundump.c:73-77). The three SSBU chunks are 4-byte floats,
    so a Python double that is not exactly a float32 is refused rather than
    silently rounded.
    """
    p = find_proto(main, proto_path)
    kind = (kind or "").lower()
    if kind not in APPENDABLE_KINDS:
        raise EncodeError("cannot append a %r constant; this tool appends "
                          "%s only (nil and boolean are refused because "
                          "nothing changes by adding them)"
                          % (kind, " / ".join(APPENDABLE_KINDS)))
    index = len(p.constants)
    if at is not None and at != index:
        raise EncodeError(
            "refusing to insert at K[%d]: constants can only be APPENDED, and "
            "%s already has %d (K[0..%d]); inserting at K[%d] would move every "
            "later index and silently re-point the LOADK Bx / RK operands that "
            "name them" % (at, proto_path, index, index - 1, at))
    if index > MAXARG_Bx:
        raise EncodeError(
            "refusing to append: the new index %d exceeds LOADK's Bx limit of "
            "%d (MAXARG_Bx, lopcodes.h:60), so no instruction could reach it"
            % (index, MAXARG_Bx))

    long_form = False
    if kind == "string":
        if not isinstance(value, str):
            raise EncodeError("a string constant needs a string, not %r"
                              % (value,))
        raw = value.encode("utf-8", "surrogateescape")
        # lundump.c:94 picks short/long storage from the *text* length, and
        # ldump.c writes the matching tag; MAX_SHORT_STRING is LUAI_MAXSHORTLEN.
        tag = T_SHRSTR if len(raw) <= MAX_SHORT_STRING else T_LNGSTR
        stored = value
    elif kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise EncodeError("an integer constant needs a Python int, not %r"
                              % (value,))
        lo, hi = _signed_range(hdr.integer_size)
        if not lo <= value <= hi:
            raise EncodeError("%d does not fit this chunk's %d-byte "
                              "lua_Integer (%d..%d, LoadInteger/lundump.c:78)"
                              % (value, hdr.integer_size, lo, hi))
        tag, stored = T_NUMINT, value
    else:                                     # float
        try:
            v = float(value)
        except (TypeError, ValueError):
            raise EncodeError("a float constant needs a number, not %r"
                              % (value,))
        if hdr.num_size == 4:
            back = struct.unpack("<f", struct.pack("<f", v))[0]
            if back != v:
                raise EncodeError(
                    "refusing %r: this chunk uses 4-byte lua_Number, and %r is "
                    "not exactly representable in float32 (it would be stored "
                    "as %r)" % (v, v, back))
        elif hdr.num_size == 8:
            struct.pack("<d", v)
        else:
            raise EncodeError("unsupported lua_Number width %d"
                              % hdr.num_size)
        tag, stored = T_NUMFLT, v

    k = Constant(index, 0, tag, 0, kind, stored)
    k.long_form = long_form
    p.constants.append(k)
    return k


# ---------------------------------------------------------------------------
# instruction field validation, shared by patchins and insertins
# ---------------------------------------------------------------------------

# Opcodes whose A is a register although testAMode (lopcodes.h:286, bit 6) is
# clear, because they write through it rather than assign to it. From the
# opcode comments: OP_SETTABLE "R(A)[RK(B)] := RK(C)" (lopcodes.h:183) and
# OP_SETUPVAL "UpValue[B] := R(A)" (lopcodes.h:182).
_A_REGISTER_EXTRA = ("SETTABLE", "SETUPVAL")


def _check_instruction(proto: Proto, pc: int, inst: Instruction,
                       next_name: "str | None", code_len: int,
                       what: str) -> None:
    """Raise :class:`EncodeError` unless ``inst`` is safe at ``pc``.

    ``next_name`` is the opcode that will follow ``inst`` (``None`` when
    nothing will), used only for the three adjacencies the VM asserts on.
    Every bound below comes from the pinned source, quoted in the message.
    """
    name = inst.name
    ms = proto.maxstacksize
    nk = len(proto.constants)
    nu = len(proto.upvalues)
    np_ = len(proto.protos)

    def bad(msg):
        raise EncodeError("%s pc%d %s: %s" % (what, pc, name, msg))

    # -- A: register, upvalue index, or a 0/1 test flag ------------------
    if name in ("EQ", "LT", "LE"):
        if inst.a not in (0, 1):
            bad("A=%d; %s uses A as the condition to accept (lopcodes.h:%d), "
                "so only 0 or 1 is meaningful" % (inst.a, name,
                                                  209 + ("EQ", "LT", "LE").index(name)))
    elif name == "SETTABUP":
        if inst.a >= nu:
            bad("A=%d is an upvalue index but the proto has %d upvalue(s) "
                "(lopcodes.h:181)" % (inst.a, nu))
    elif (inst.sets_a or name in _A_REGISTER_EXTRA) and inst.a >= ms:
        bad("A=%d is a register but maxstacksize is %d" % (inst.a, ms))

    # -- B / C: what their argument mode says they are -------------------
    # Only iABC has independent B and C fields. In iAsBx (lopcodes.h:32, 50)
    # they are the two halves of Bx, so a JMP's B is part of its jump offset
    # and is not a register -- reading it as one would be the same mistake
    # const_uses used to make.
    if inst.mode == _IABC:
        for which, raw in (("B", inst.b), ("C", inst.c)):
            mode = b_arg_mode(inst.op) if which == "B" \
                else c_arg_mode(inst.op)
            if mode == _OPARG_N:
                continue
            if mode == _OPARG_K and raw & BITRK:
                idx = raw & ~BITRK
                if idx >= nk:
                    bad("RK.%s names K[%d] but the proto has %d constant(s)"
                        % (which, idx, nk))
            elif mode == _OPARG_R and raw >= ms:
                bad("%s=%d is a register but maxstacksize is %d (%s, OpArgR)"
                    % (which, raw, ms, which))
            elif mode == _OPARG_U and name in ("GETUPVAL", "SETUPVAL") \
                    and raw >= nu:
                bad("%s=%d is an upvalue index but the proto has %d upvalue(s) "
                    "(%s, lopcodes.h:176/182)" % (which, raw, nu, which))
            elif mode == _OPARG_U and name == "GETTABUP" and which == "B" \
                    and raw >= nu:
                bad("B=%d is an upvalue index but the proto has %d upvalue(s) "
                    "(lopcodes.h:178)" % (raw, nu))

    # -- LOADK / CLOSURE index against the real table sizes --------------
    if name == "LOADK" and inst.bx >= nk:
        bad("Bx=%d but the proto has %d constant(s) (lopcodes.h:172)"
            % (inst.bx, nk))
    if name == "CLOSURE" and inst.bx >= np_:
        bad("Bx=%d but the proto has %d nested proto(s) (lopcodes.h:229)"
            % (inst.bx, np_))

    # -- multi-register spans, quoted from the opcode comments -----------
    # B == 0 or C == 0 means "up to top" (lopcodes.h:250-253), which is not a
    # value this tool can resolve, so those are left alone rather than guessed.
    spans = []
    if name == "LOADNIL":
        spans.append((inst.a + inst.b, "R(%d)..R(%d) := nil (lopcodes.h:175)"
                      % (inst.a, inst.a + inst.b)))
    elif name == "SELF":
        spans.append((inst.a + 1, "R(%d) and R(%d) (lopcodes.h:187)"
                      % (inst.a, inst.a + 1)))
    elif name == "CONCAT" and inst.mode == _IABC:
        spans.append((inst.c, "R(%d)..R(%d) (lopcodes.h:206)"
                      % (inst.b, inst.c)))
    elif name == "CALL" or name == "TAILCALL":
        top = max(inst.b, inst.c) - 1
        if top > 0:
            spans.append((inst.a + top, "R(%d)..R(%d) (lopcodes.h:216/217)"
                          % (inst.a, inst.a + top)))
    elif name == "RETURN" and inst.b >= 2:
        spans.append((inst.a + inst.b - 2, "R(%d)..R(%d) (lopcodes.h:218)"
                      % (inst.a, inst.a + inst.b - 2)))
    elif name == "VARARG" and inst.b >= 2:
        spans.append((inst.a + inst.b - 2, "R(%d)..R(%d) (lopcodes.h:231)"
                      % (inst.a, inst.a + inst.b - 2)))
    elif name == "SETLIST" and inst.b > 0:
        spans.append((inst.a + inst.b, "R(%d)..R(%d) (lopcodes.h:227)"
                      % (inst.a, inst.a + inst.b)))
    elif name == "TFORCALL":
        spans.append((inst.a + 2 + inst.c, "R(%d)..R(%d) (lopcodes.h:224)"
                      % (inst.a, inst.a + 2 + inst.c)))
    elif name == "FORPREP":
        spans.append((inst.a + 2, "R(%d), R(%d), R(%d) (lopcodes.h:222)"
                      % (inst.a, inst.a + 1, inst.a + 2)))
    elif name == "FORLOOP":
        spans.append((inst.a + 3, "R(%d)..R(%d), R(%d) written "
                      "(lopcodes.h:220-221)" % (inst.a, inst.a + 2, inst.a + 3)))
    elif name == "TFORLOOP":
        spans.append((inst.a + 3, "R(%d)..R(%d) (lopcodes.h:225)"
                      % (inst.a, inst.a + 3)))
    elif name == "JMP" and inst.a != 0:
        # lopcodes.h:208 -- a non-zero A closes upvalues from R(A-1) up
        spans.append((inst.a - 1, "R(%d) (lopcodes.h:208)" % (inst.a - 1,)))
    for hi, label in spans:
        if hi >= ms:
            bad("%s needs R[%d] but maxstacksize is %d" % (label, hi, ms))

    # -- flags that are booleans, not counts -----------------------------
    for which, raw in (("B", inst.b), ("C", inst.c)):
        if name in ("LOADBOOL",) and which == "B" and raw not in (0, 1):
            bad("B=%d; LOADBOOL stores a boolean (lopcodes.h:174)" % raw)
        if name in ("LOADBOOL", "TEST") and which == "C" and raw not in (0, 1):
            bad("C=%d; %s uses C as a boolean (lopcodes.h:174/213)"
                % (raw, name))

    # -- jump targets against the code length ---------------------------
    if inst.mode == _IASBX:
        target = pc + 1 + inst.sbx
        if not 0 <= target <= code_len:
            bad("sBx=%d targets pc %d, outside 0..%d"
                % (inst.sbx, target, code_len))

    # -- the three adjacencies the VM asserts on ------------------------
    if name == "LOADKX" and next_name != "EXTRAARG":
        bad("must be followed by EXTRAARG (lopcodes.h:255, lvm.c:814), but "
            "pc%d would be followed by %s"
            % (pc, next_name if next_name else "nothing (it is the last "
                                                  "instruction)"))
    if name == "SETLIST" and inst.c == 0 and next_name != "EXTRAARG":
        bad("SETLIST with C=0 must be followed by EXTRAARG (lopcodes.h:252, "
            "lvm.c:1270), but pc%d would be followed by %s"
            % (pc, next_name if next_name else "nothing"))
    if name == "TFORCALL" and next_name != "TFORLOOP":
        bad("must be followed by TFORLOOP (lvm.c:1250-1253), but pc%d would "
            "be followed by %s"
            % (pc, next_name if next_name else "nothing"))


def build_instruction(proto: Proto, pc: int, opname: str,
                      fields: "dict[str, int]", code_len: int,
                      next_name: "str | None" = None,
                      what: str = "instruction") -> Instruction:
    """Assemble one validated instruction from an opcode name and fields."""
    name = opname.upper()
    if name not in OPNAMES:
        raise EncodeError("unknown opcode %r (5.3 has: %s)"
                          % (opname, " ".join(OPNAMES)))
    op = OPNAMES.index(name)
    mode = OPMODES[op] & 3
    allowed = _FIELD_ALLOWED[mode]
    extra = sorted(set(fields) - set(allowed))
    if extra:
        raise EncodeError(
            "%s %s is %s (lopcodes.c:74-123), which has no %s field; it takes "
            "%s. Asking for a field the format does not have is refused rather "
            "than dropped, because dropping it would silently change the word."
            % (what, name, MODE_NAMES[mode], "/".join(extra),
               ", ".join(allowed)))
    for key in sorted(fields):
        lo, hi = _FIELD_RANGE[key]
        val = fields[key]
        if isinstance(val, bool) or not isinstance(val, int):
            raise EncodeError("%s %s field %s=%r is not an integer"
                              % (what, name, key, val))
        if not lo <= val <= hi:
            raise EncodeError("%s %s field %s=%d does not fit %d..%d "
                              "(lopcodes.h:74-76/60/112/68)"
                              % (what, name, key, val, lo, hi))

    a = fields.get("A", 0)
    b = fields.get("B", 0)
    c = fields.get("C", 0)
    bx = fields.get("Bx", 0)
    sbx = fields.get("sBx", 0)
    ax = fields.get("Ax", 0)
    if mode == _IASBX:
        word = _i(op, a=a, bx=sbx + MAXARG_sBx)      # SETARG_sBx, lopcodes.h:115
    elif mode == _IABX:
        word = _i(op, a=a, bx=bx)
    elif mode == _IAX:
        word = (op & 0x3F) | (ax << POS_Ax)           # CREATE_Ax, lopcodes.h:124
    else:
        word = _i(op, a=a, b=b, c=c)

    inst = Instruction(pc, 0, word)
    _check_instruction(proto, pc, inst, next_name, code_len, what)
    return inst


def _parse_spec(tokens: "list[str]") -> "tuple[str, dict[str, int]]":
    """'OPNAME A=1 B=2' -> ('OPNAME', {'A': 1, 'B': 2}); other fields allowed."""
    if not tokens:
        raise EncodeError("expected an opcode name, e.g. MOVE A=1 B=1")
    opname = tokens[0].upper()
    fields: "dict[str, int]" = {}
    for tok in tokens[1:]:
        if "=" not in tok:
            raise EncodeError("field %r is not NAME=VALUE (expected A=, B=, "
                              "C=, Bx=, sBx= or Ax=)" % tok)
        key, _, val = tok.partition("=")
        key = key.strip()
        if key not in _FIELD_RANGE:
            raise EncodeError("unknown instruction field %r (known: A, B, C, "
                              "Bx, sBx, Ax)" % key)
        try:
            fields[key] = int(val.strip(), 0)
        except ValueError:
            raise EncodeError("field %s=%r is not an integer" % (key, val))
    return opname, fields


# ---------------------------------------------------------------------------
# patchins
# ---------------------------------------------------------------------------

def patch_instruction(main: Proto, proto_path: str, pc: int, opname: str,
                      fields: "dict[str, int]") -> "tuple[int, int]":
    """Replace ONE instruction word, given as opcode + fields.

    Never accepts a raw 32-bit word: a raw word can set fields the opcode's
    mode does not have, and there is then nothing left to check it against.
    Returns ``(old_word, new_word)``.
    """
    p = find_proto(main, proto_path)
    if not 0 <= pc < len(p.code):
        raise EncodeError("%s has %d instruction(s), so pc %d does not exist"
                          % (proto_path, len(p.code), pc))
    new = build_instruction(
        p, pc, opname, fields, len(p.code),
        next_name=(p.code[pc + 1].name if pc + 1 < len(p.code) else None),
        what="patched instruction")
    old = p.code[pc].word
    p.code[pc] = Instruction(pc, p.code[pc].offset, new.word)
    return old, new.word


# ---------------------------------------------------------------------------
# insertins
# ---------------------------------------------------------------------------

#: The iAsBx opcodes whose target is ``pc + 1 + sBx``. All four are handled.
IASA_BC_JUMPS = ("JMP", "FORPREP", "FORLOOP", "TFORLOOP")

#: Adjacencies the VM relies on. Inserting *between* the two halves would
#: change what the instruction at ``pc-1`` skips, so those pcs are refused.
#: Each entry cites where the requirement comes from.
PAIR_REQUIREMENTS = (
    # a test opcode: bit 7 of luaP_opmodes is set (testTMode, lopcodes.h:287),
    # meaning "next instruction must be a jump" (lopcodes.c:107-111)
    ("is_test", "is a test (testTMode, lopcodes.h:287), so the VM executes the "
                "next instruction as its jump (lvm.c:744 donextjump)"),
    ("LOADBOOL/C!=0", "has C=%d != 0, so the VM skips the next instruction "
                      "(lvm.c:821)"),
    ("LOADKX", "must be followed by its EXTRAARG (lopcodes.h:255, lvm.c:814)"),
    ("SETLIST/C=0", "has C=0, so its EXTRAARG follows (lopcodes.h:252, "
                    "lvm.c:1270)"),
    ("TFORCALL", "must be followed by TFORLOOP (lvm.c:1250-1253)"),
)


def protected_pair(p: Proto, pc: int) -> "str | None":
    """Why ``pc`` may not start an inserted run, or ``None`` if it may."""
    if pc <= 0 or pc > len(p.code):
        return None
    prev = p.code[pc - 1]
    if prev.op >= NUM_OPCODES:
        return None
    name = prev.name
    if prev.is_test:
        return ("pc%d is %s, which %s" % (pc - 1, name, PAIR_REQUIREMENTS[0][1]))
    if name == "LOADBOOL" and prev.c != 0:
        return ("pc%d is LOADBOOL, which %s"
                % (pc - 1, PAIR_REQUIREMENTS[1][1] % prev.c))
    if name == "LOADKX":
        return ("pc%d is LOADKX, which %s" % (pc - 1, PAIR_REQUIREMENTS[2][1]))
    if name == "SETLIST" and prev.c == 0:
        return ("pc%d is SETLIST, which %s" % (pc - 1, PAIR_REQUIREMENTS[3][1]))
    if name == "TFORCALL":
        return ("pc%d is TFORCALL, which %s" % (pc - 1, PAIR_REQUIREMENTS[4][1]))
    return None


def insert_instructions(main: Proto, proto_path: str, pc: int,
                        specs: "list[tuple[str, dict[str, int]]]",
                        ) -> dict:
    """Insert N instructions at one pc, relocating every affected jump.

    Jump kinds **handled**: the four iAsBx opcodes ``JMP``, ``FORPREP``,
    ``FORLOOP`` and ``TFORLOOP``. They all compute their destination as
    ``pc + 1 + sBx`` (lvm.c:741 ``dojump``; 1208 FORLOOP, 1238 FORPREP,
    1259 TFORLOOP), so one rule covers them: a destination at or after the
    insertion point moves by N, as does the jump itself when it sits at or
    after that point.

    Jump kinds **not** handled, and therefore refused rather than guessed:

    * the implicit ``pc++`` skips (``EQ``/``LT``/``LE``/``TEST``/``TESTSET``,
      ``LOADBOOL`` with C != 0) and the two EXTRAARG adjacencies
      (``LOADKX``, ``SETLIST`` with C == 0) -- :func:`protected_pair` refuses
      any insertion that would split one;
    * ``TFORCALL``, which always falls into the ``TFORLOOP`` at the next pc
      (lvm.c:1250-1253), likewise refused as a split;
    * ``OP_CALL``/``OP_TAILCALL``/``OP_RETURN``/``OP_VARARG``/``OP_SETLIST``,
      which take their extent from ``L->top`` at run time rather than from a
      pc, so inserting anywhere is as safe as inserting nowhere -- but this
      tool will not reason about them and offers no guarantee.

    Refuses when a relocated offset no longer fits ``sBx``, when the insertion
    point splits a protected pair, or when ``lineinfo`` is present but is not
    one-per-instruction (it would then be meaningless after the shift).

    Returns a report dict: the pc mapping, the relocated jumps and the
    ``lineinfo``/``locvar`` adjustments made.
    """
    p = find_proto(main, proto_path)
    n = len(specs)
    if n == 0:
        raise EncodeError("nothing to insert: 0 instructions given")
    if not 0 <= pc <= len(p.code):
        raise EncodeError("%s has %d instruction(s), so an insertion point of "
                          "pc %d is outside 0..%d"
                          % (proto_path, len(p.code), pc, len(p.code)))
    split = protected_pair(p, pc)
    if split is not None:
        raise EncodeError(
            "refusing to insert at pc %d: %s. Inserting here would put an "
            "instruction between the two halves of a pair whose adjacency the "
            "VM depends on." % (pc, split))
    old = list(p.code)
    code_len = len(old)
    new_len = code_len + n

    # lineinfo is one entry per instruction (lundump.c:187-192 loads an
    # independent count, so a wrong length still loads but means nothing).
    if p.lineinfo and len(p.lineinfo) != code_len:
        raise EncodeError(
            "%s has %d lineinfo entries for %d instructions; refusing to insert "
            "because the line table could not be kept aligned"
            % (proto_path, len(p.lineinfo), code_len))
    line = p.lineinfo[pc] if p.lineinfo and pc < len(p.lineinfo) else (
        p.lineinfo[-1] if p.lineinfo else 0)

    # --- validate the incoming instructions against the NEW layout -----
    def follower_name(at: int) -> "str | None":
        """Opcode that will follow position ``at`` after the insertion."""
        nxt = at + 1
        if nxt >= pc + n:                       # past the inserted run
            j = nxt - n
            return old[j].name if 0 <= j < len(old) else None
        return specs[nxt - pc][0].upper()      # another instruction we insert

    new_words = []
    for j, (opname, fields) in enumerate(specs):
        at = pc + j
        new_words.append(
            build_instruction(p, at, opname, fields, new_len,
                              next_name=follower_name(at),
                              what="inserted instruction %d" % (j + 1)))

    # --- relocate the pre-existing jumps -------------------------------
    rebuilt: "list[tuple[int, int]]" = []
    relocated = []
    for inst in old:
        new_pc = inst.pc + n if inst.pc >= pc else inst.pc
        word = inst.word
        if inst.mode == _IASBX:
            old_tgt = inst.pc + 1 + inst.sbx
            new_tgt = old_tgt + n if old_tgt >= pc else old_tgt
            new_sbx = new_tgt - new_pc - 1
            if not -MAXARG_sBx <= new_sbx <= MAXARG_sBx:
                raise EncodeError(
                    "refusing to insert %d instruction(s) at pc %d: %s at pc "
                    "%d would need sBx=%d, outside -%d..%d (MAXARG_sBx, "
                    "lopcodes.h:60/112)"
                    % (n, pc, inst.name, inst.pc, new_sbx, MAXARG_sBx,
                       MAXARG_sBx))
            if new_sbx != inst.sbx:
                word = _i(inst.op, a=inst.a, bx=new_sbx + MAXARG_sBx)
            relocated.append({"pc": inst.pc, "name": inst.name,
                              "old_target": old_tgt, "new_pc": new_pc,
                              "new_target": new_tgt, "old_sbx": inst.sbx,
                              "new_sbx": new_sbx})
        rebuilt.append((new_pc, word))

    # --- everything checkable has passed; only now mutate ---------------
    code = [Instruction(p_, 0, w) for p_, w in rebuilt]
    ins = [Instruction(pc + j, 0, w.word) for j, w in enumerate(new_words)]
    p.code = code[:pc] + ins + code[pc:]

    line_adjusted = False
    if p.lineinfo:
        # the inserted instructions inherit the line of the instruction they
        # are inserted before, so the table stays one entry per instruction
        p.lineinfo = p.lineinfo[:pc] + [line] * n + p.lineinfo[pc:]
        line_adjusted = True
    moved = []
    for lv in p.locvars:
        before = (lv.startpc, lv.endpc)
        if lv.startpc >= pc:
            lv.startpc += n
        if lv.endpc >= pc:
            lv.endpc += n
        if before != (lv.startpc, lv.endpc):
            moved.append((lv.name, before, (lv.startpc, lv.endpc)))

    return {
        "proto": proto_path,
        "pc": pc,
        "inserted": n,
        "old_len": code_len,
        "new_len": new_len,
        "relocated": relocated,
        "lineinfo_adjusted": line_adjusted,
        "line_of_inserted": line,
        "locvars_moved": moved,
        "pc_map": {i: (i + n if i >= pc else i) for i in range(code_len)},
        "words": [i.word for i in new_words],
    }


# ---------------------------------------------------------------------------
# structural comparison (used to prove a mutation changed only one field)
# ---------------------------------------------------------------------------


def diff_chunks(a: bytes, b: bytes) -> "list[str]":
    """Every structural difference between two chunks, one line each.

    Compares header widths, then each prototype's scalar fields, instruction
    words, constants, upvalues, child count, ``lineinfo``, ``locvars`` and
    upvalue names. Deliberately compares *values*, not byte offsets: offsets
    necessarily move when a string changes length, and saying so is the point.
    """
    hdr_a, main_a = load_chunk(a)
    hdr_b, main_b = load_chunk(b)
    out: "list[str]" = []

    for field in Header.__slots__:
        va, vb = getattr(hdr_a, field), getattr(hdr_b, field)
        if field == "size":
            continue
        if va != vb:
            out.append("header %s: %r != %r" % (field, va, vb))

    pa = {p.path: p for p in walk(main_a)}
    pb = {p.path: p for p in walk(main_b)}
    for path in sorted(set(pa) | set(pb)):
        if path not in pa:
            out.append("%s: only in B" % path)
            continue
        if path not in pb:
            out.append("%s: only in A" % path)
            continue
        out.extend(_diff_proto(pa[path], pb[path]))
    return out


def _diff_proto(a: Proto, b: Proto) -> "list[str]":
    out: "list[str]" = []
    tag = a.path
    for field in ("linedefined", "lastlinedefined", "numparams",
                  "is_vararg", "maxstacksize", "source_is_null",
                  "source_long"):
        va, vb = getattr(a, field), getattr(b, field)
        if va != vb:
            out.append("%s.%s: %r != %r" % (tag, field, va, vb))

    aw = [i.word for i in a.code]
    bw = [i.word for i in b.code]
    if aw != bw:
        if len(aw) != len(bw):
            out.append("%s.code: %d instruction(s) != %d"
                       % (tag, len(aw), len(bw)))
        else:
            diff = [i for i, (x, y) in enumerate(zip(aw, bw)) if x != y]
            out.append("%s.code: word(s) differ at pc %s"
                       % (tag, diff[:8]))

    ka = [(k.tag, k.kind, k.value, k.long_form) for k in a.constants]
    kb = [(k.tag, k.kind, k.value, k.long_form) for k in b.constants]
    if ka != kb:
        if len(ka) != len(kb):
            out.append("%s.constants: %d != %d"
                       % (tag, len(ka), len(kb)))
        for i, (x, y) in enumerate(zip(ka, kb)):
            if x != y:
                out.append("%s.K[%d]: tag=%s kind=%s value=%r long=%s != "
                           "tag=%s kind=%s value=%r long=%s"
                           % (tag, i, x[0], x[1], x[2], x[3],
                              y[0], y[1], y[2], y[3]))

    if a.upvalues != b.upvalues:
        out.append("%s.upvalues: %r != %r" % (tag, a.upvalues, b.upvalues))
    if a.upvalue_names != b.upvalue_names:
        out.append("%s.upvalue_names: %r != %r"
                   % (tag, a.upvalue_names, b.upvalue_names))
    if a.upvalue_names_long != b.upvalue_names_long:
        out.append("%s.upvalue_names_long: %r != %r"
                   % (tag, a.upvalue_names_long, b.upvalue_names_long))
    if a.lineinfo != b.lineinfo:
        out.append("%s.lineinfo: %d entr(ies) differ"
                   % (tag, max(len(a.lineinfo), len(b.lineinfo))))
    la = [(lv.name, lv.name_long, lv.startpc, lv.endpc) for lv in a.locvars]
    lb = [(lv.name, lv.name_long, lv.startpc, lv.endpc) for lv in b.locvars]
    if la != lb:
        out.append("%s.locvars: %r != %r" % (tag, la, lb))
    return out


# ---------------------------------------------------------------------------
# a synthetic valid chunk, for tests that need a length change the real
# chunks do not contain
# ---------------------------------------------------------------------------


def _op(name: str) -> int:
    """Opcode number by name, taken from the pinned luaP_opnames table."""
    return OPNAMES.index(name)


def _i(op: int, a: int = 0, b: int = 0, c: int = 0, bx: int = 0) -> int:
    """Assemble an instruction word from its fields (lopcodes.h layout)."""
    return ((op & 0x3F)
            | ((a & 0xFF) << POS_A)
            | ((c & 0x1FF) << POS_C)
            | ((b & 0x1FF) << POS_B)
            | ((bx & MAXARG_Bx) << POS_Bx))


def _isbx(op: int, a: int, pc: int, target: int) -> int:
    """Assemble an iAsBx word from its *destination pc*, not its offset.

    ``SETARG_sBx`` (lopcodes.h:115) stores ``sBx + MAXARG_sBx`` in ``Bx``, and
    the VM computes the destination as ``pc + 1 + sBx`` (lvm.c:741
    ``dojump``, lvm.c:1208/1238/1259 for FORLOOP/FORPREP/TFORLOOP). Taking the
    destination and deriving the offset keeps hand-written jump tables in this
    file off-by-one-proof.
    """
    return _i(op, a=a, bx=(target - pc - 1) + MAXARG_sBx)


def build_synthetic_chunk() -> "tuple[Header, Proto]":
    """Build a small valid Lua 5.3 chunk with the *same widths as SSBU*.

    29-byte header, 4-byte float ``lua_Number``, 8-byte ``size_t``, one nested
    prototype, one local variable and one upvalue name -- so it exercises every
    section the three real chunks leave empty (``locvars`` and upvalue names),
    plus a marker string long enough to force the ``0xFF`` size escape when it
    is replaced.

    Extended in P2-LUA-EDIT to carry every control-flow shape the three real
    editor chunks contain, because ``insertins`` has to relocate them:
    a numeric ``for`` loop (``FORPREP``/``FORLOOP``), a backward ``JMP``, a
    forward ``JMP``, and both implicit-skip pairs the VM asserts on --
    ``EQ``+``JMP`` (``testTMode``, lopcodes.c:107) and
    ``LOADBOOL C!=0``+next (lvm.c:821). Every jump offset is derived from its
    destination pc by :func:`_isbx`, never hand-computed. The layout is::

        0   MOVE    1, 0            R1 := R0
        1   LOADK   2, Bx=0         R2 := K[0]
        2   LOADK   3, Bx=1         R3 := K[1]
        3   LOADK   4, Bx=2         R4 := 42      (for-loop limit)
        4   LOADK   5, Bx=3         R5 := 1.0     (for-loop step)
        5   EQ      0, 2, 3         test, pairs with pc6
        6   JMP     -> 9            forward
        7   LOADK   6, Bx=2         R6 := 42
        8   JMP     -> 3            BACKWARD
        9   FORPREP 3, -> 12        pc6+... lands on the FORLOOP
        10  ADD     0, 0, 1         loop head
        11  LOADK   6, Bx=2         loop body
        12  FORLOOP 3, -> 10        jumps back to the loop head
        13  LOADBOOL 0, 1, 1        R0 := true; C != 0 so pc14 is skipped
        14  RETURN  0, 2            return R0, R1

    ``maxstacksize`` is 8 because the loop uses R3..R6 (FORPREP/FORLOOP read
    R(A), R(A+1), R(A+2) and FORLOOP writes R(A+3), lopcodes.h:220-222).
    """
    hdr = Header(
        version=LUAC_VERSION, format=LUAC_FORMAT,
        int_size=4, size_t_size=8, instr_size=4, integer_size=8, num_size=4,
        luac_int=LUAC_INT, luac_num=LUAC_NUM, size=0, main_nupvalues=1,
        nupvalues_offset=0x1D, body_offset=29,
    )

    main = Proto("main", 0)
    main.source = None
    main.source_is_null = True
    main.linedefined = 0
    main.lastlinedefined = 0
    main.numparams = 0
    main.is_vararg = 1
    main.maxstacksize = 8
    # (opcode name, A, B, C) for iABC, (name, A, destination pc) for iAsBx
    layout = [
        ("MOVE", 1, 0, 0),        # 0
        ("LOADK", 2, None, 0),    # 1  Bx = K[0]
        ("LOADK", 3, None, 1),    # 2  Bx = K[1]
        ("LOADK", 4, None, 2),    # 3  Bx = K[2] = 42
        ("LOADK", 5, None, 3),    # 4  Bx = K[3] = 1.0
        ("EQ", 0, 2, 3),          # 5  test: pairs with pc6
        ("JMP", 0, 9, None),      # 6  forward to pc9
        ("LOADK", 6, None, 2),    # 7  Bx = K[2]
        ("JMP", 0, 3, None),      # 8  BACKWARD to pc3
        ("FORPREP", 3, 12, None),  # 9  lands on the FORLOOP at pc12
        ("ADD", 0, 0, 1),         # 10 loop head
        ("LOADK", 6, None, 2),    # 11 loop body
        ("FORLOOP", 3, 10, None),  # 12 jumps back to the loop head
        ("LOADBOOL", 0, 1, 1),    # 13 C != 0, so pc14 is skipped
        ("RETURN", 0, 2, 0),      # 14
    ]
    words = []
    for pc, (name, a, b, c) in enumerate(layout):
        op = _op(name)
        mode = OPMODES[op] & 3
        if mode == _IASBX:
            words.append(_isbx(op, a, pc, b))
        elif mode == _IABX:
            words.append(_i(op, a=a, bx=c))
        else:
            words.append(_i(op, a=a, b=b, c=c))
    main.code = [Instruction(pc, pc * 4, words[pc])
                 for pc in range(len(layout))]
    main.constants = [
        Constant(0, 0, T_SHRSTR, 0, "string",
                 "synthetic_p1_lua_write_marker_0123456789"),
        Constant(1, 0, T_SHRSTR, 0, "string", "short_marker"),
        Constant(2, 0, T_NUMINT, 0, "integer", 42),
        Constant(3, 0, T_NUMFLT, 0, "float", 1.0),
        Constant(4, 0, T_BOOLEAN, 0, "boolean", True),
        Constant(5, 0, T_NIL, 0, "nil", None),
        # Deliberately unreferenced: nothing in this synthetic chunk loads or
        # reads it, so rewriting it cannot change any executed behaviour. This
        # is the mutation target for the length-changing round-trip test.
        Constant(6, 0, T_SHRSTR, 0, "string",
                 "p1_lua_write_inert_literal_replace_me"),
    ]
    main.upvalues = [(1, 0)]
    # one entry per instruction (lundump.c:187-192 loads an independent count)
    main.lineinfo = list(range(100, 100 + len(layout)))

    child = Proto("main.p0", 0)
    child.source = None
    child.source_is_null = True
    child.linedefined = 5
    child.lastlinedefined = 6
    child.numparams = 1
    child.is_vararg = 0
    child.maxstacksize = 2
    child.code = [
        Instruction(0, 0, _i(_op("GETTABUP"), a=0, b=0, c=BITRK | 0)),
        Instruction(1, 4, _i(_op("RETURN"), a=0, b=1)),
    ]
    child.constants = [Constant(0, 0, T_SHRSTR, 0, "string",
                                "synthetic_child_env_lookup")]
    child.upvalues = [(1, 0)]
    child.upvalue_names = ["_ENV"]
    child.upvalue_names_long = [False]
    child.lineinfo = [5, 6]
    child.locvars = [LocVar("synthetic_local", 0, 0, 2, False)]
    main.protos = [child]
    return hdr, main


# ---------------------------------------------------------------------------
# semantic helpers (bounded; never a decompiler)
# ---------------------------------------------------------------------------


def rk_text(proto: Proto, raw: int, limit: int = 40) -> str:
    """Resolve an RK operand to text, or ``R[n]`` for a register."""
    if raw & BITRK:
        idx = raw & ~BITRK
        if idx < len(proto.constants):
            return "K[%d]=%s" % (idx, proto.constants[idx].text(limit))
        return "K[%d] <out of range>" % idx
    return "R[%d]" % raw


def explain(inst: Instruction, proto: Proto, limit: int = 40) -> str:
    """Decode the opcodes this task cares about.

    Covers counts (LOADK / numeric constants), table fields and globals
    (GETTABUP / GETTABLE / SETTABUP / SETTABLE / SELF), branches (JMP, the
    comparison and test ops, FORPREP / FORLOOP) and calls (CALL / TAILCALL).
    Every other opcode yields ``''`` so callers can leave it un-annotated
    rather than inventing a source-level meaning for it.
    """
    n = inst.name
    try:
        if n == "LOADK":
            k = proto.constants[inst.bx]
            return "R[%d] := K[%d] %s" % (inst.a, inst.bx, k.text(limit))
        if n == "GETTABUP":
            up = _upname(proto, inst.b)
            return "R[%d] := %s[%s]" % (inst.a, up, rk_text(proto, inst.c, limit))
        if n == "SETTABUP":
            up = _upname(proto, inst.a)
            return "%s[%s] := %s" % (up, rk_text(proto, inst.b, limit),
                                     rk_text(proto, inst.c, limit))
        if n == "GETTABLE":
            return "R[%d] := R[%d][%s]" % (inst.a, inst.b,
                                           rk_text(proto, inst.c, limit))
        if n == "SETTABLE":
            return "R[%d][%s] := %s" % (inst.a, rk_text(proto, inst.b, limit),
                                        rk_text(proto, inst.c, limit))
        if n == "SELF":
            return "R[%d] := R[%d][%s] ; R[%d+1] := R[%d]" % (
                inst.a, inst.b, rk_text(proto, inst.c, limit), inst.a, inst.b)
        if n in ("CALL", "TAILCALL"):
            nargs = inst.b - 1 if inst.b else -1
            return "R[%d](%d args%s)" % (inst.a, nargs,
                                         ", multret" if inst.c == 0 else "")
        if n == "CLOSURE":
            return "R[%d] := closure(%s.p%d)" % (inst.a, proto.path, inst.bx)
        if n == "JMP":
            return "pc -> %d" % (inst.pc + 1 + inst.sbx)
        if n in ("EQ", "LT", "LE"):
            return "if (%s %s %s) ~= %d then pc++" % (
                rk_text(proto, inst.b, limit),
                {"EQ": "==", "LT": "<", "LE": "<="}[n],
                rk_text(proto, inst.c, limit), inst.a)
        if n == "TEST":
            return "if not (R[%d] <=> %d) then pc++" % (inst.a, inst.c)
        if n == "TESTSET":
            return "if (R[%d] <=> %d) then R[%d] := R[%d] else pc++" % (
                inst.b, inst.c, inst.a, inst.b)
        if n in ("FORPREP", "FORLOOP"):
            return "loop over R[%d]..R[%d] with R[%d+2] step; target pc %d" % (
                inst.a, inst.a + 1, inst.a, inst.pc + 1 + inst.sbx)
    except IndexError:
        return "<unresolved>"
    return ""


def _upname(proto: Proto, idx: int) -> str:
    if 0 <= idx < len(proto.upvalue_names) and proto.upvalue_names[idx]:
        return "up[%d] %s" % (idx, proto.upvalue_names[idx])
    if 0 <= idx < len(proto.upvalues):
        instack, k = proto.upvalues[idx]
        return "up[%d] (instack=%d idx=%d)" % (idx, instack, k)
    return "up[%d]" % idx


def find_xref(main: Proto, needle: str) -> "list[tuple[Proto, int, Constant]]":
    """Every constant equal to ``needle``, with its proto and offset."""
    hits = []
    for p in walk(main):
        for k in p.constants:
            if k.is_string and k.value == needle:
                hits.append((p, k.index, k))
    return hits


def const_uses(p: Proto, index: int) -> "list[tuple[Instruction, str]]":
    """Instructions that read constant ``index`` of proto ``p``.

    A constant can be reached three ways and all must be reported:

      * ``LOADK A Bx`` -- loaded into a register (lopcodes.h:172). ``Bx`` is a
        plain constant index, so it is always a use.
      * ``LOADKX A`` -- also loads from the constant table, but the index is
        not in this instruction: it is the ``Ax`` of the *following* EXTRAARG
        (lopcodes.h:255 "the next 'instruction' is always EXTRAARG", read at
        lvm.c:812-817). Reported against the LOADKX instruction itself.
      * directly as an RK operand (``BITRK`` set, lopcodes.h:134) of an iABC
        instruction -- this is how ``GETTABUP`` consumes a global name.

    Which of B/C is an RK operand is decided by :func:`rk_operands`, i.e. from
    the pinned ``luaP_opmodes`` table, never from a hand-written list. Two
    classes of false positive used to be reported here and are gone:

      * **iAsBx instructions.** ``JMP``/``FORPREP``/``FORLOOP``/``TFORLOOP``
        are iAsBx (lopcodes.c:106,115,116,118), and in that format B and C
        are the two halves of ``Bx`` (lopcodes.h:50, ``POS_Bx == POS_C``).
        Their bit 8 is part of a jump offset, so a forward jump (``Bx`` above
        ``MAXARG_sBx``) had bit 256 set in B and was reported as an RK use of
        a constant it never reads.
      * **iABC fields whose arg mode is not OpArgK.** ``GETTABUP`` B is
        ``OpArgU`` (an upvalue index, lopcodes.c:82), ``TEST`` C is
        ``OpArgU`` (lopcodes.c:110) and ``TESTSET`` C likewise
        (lopcodes.c:111). These are plain values whose bit 256 says nothing
        about constants.

    Only checking LOADK would still be wrong: it would report a name consumed
    solely by ``GETTABUP`` as unused.
    """
    out: "list[tuple[Instruction, str]]" = []
    for n, i in enumerate(p.code):
        if i.op >= NUM_OPCODES:
            continue
        if i.name == "LOADK":
            if i.bx == index:
                out.append((i, "LOADK"))
            continue
        if i.name == "LOADKX":
            # the index lives in the next EXTRAARG; without that follower the
            # chunk is malformed and no index can be attributed to this word
            if (n + 1 < len(p.code) and p.code[n + 1].name == "EXTRAARG"
                    and p.code[n + 1].ax == index):
                out.append((i, "LOADKX"))
            continue
        for which, idx in rk_operands(i):
            if idx == index:
                out.append((i, "RK.%s" % which))
    return out


# ---------------------------------------------------------------------------
# semantic validation
# ---------------------------------------------------------------------------


def verify(main: Proto, data: bytes, header: Header) -> "list[str]":
    """Return a list of check results; empty list means everything passed."""
    results: "list[str]" = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append("%s %s%s" % ("PASS" if ok else "FAIL", name,
                                    (": " + detail) if detail else ""))

    # 1. complete consumption: lundump.c reads nothing after the main proto.
    consumed = main.end_offset == len(data)
    check("full-consumption", consumed,
          "proto ends at 0x%x, file is 0x%x bytes" % (main.end_offset,
                                                     len(data)))
    check("no-trailing-bytes", main.end_offset <= len(data),
          "over-read by %d byte(s)" % (main.end_offset - len(data)))

    # 2. every opcode is real
    bad_ops = sorted({i.pc for p in walk(main) for i in p.code
                      if i.op >= NUM_OPCODES})
    check("opcodes-in-range", not bad_ops,
          "bad opcode number(s) %s" % bad_ops if bad_ops else
          "all %d opcodes in 0..%d" % (
              sum(len(p.code) for p in walk(main)), NUM_OPCODES - 1))

    # 3. LOADK / CLOSURE constant and proto index bounds
    # Guard on the raw opcode number first: an out-of-range opcode would make
    # OPMODES[self.op] raise, so verify() must never crash on damaged input.
    kbad = []
    pbad = []
    rkbad = []
    for p in walk(main):
        for i in p.code:
            if i.op >= NUM_OPCODES:
                continue
            if i.name == "LOADK" and i.bx >= len(p.constants):
                kbad.append("%s pc%d Bx=%d >= %d" % (p.path, i.pc, i.bx,
                                                    len(p.constants)))
            if i.name == "CLOSURE" and i.bx >= len(p.protos):
                pbad.append("%s pc%d Bx=%d >= %d" % (p.path, i.pc, i.bx,
                                                     len(p.protos)))
            # rk_operands applies luaP_opmodes' OpArgK per field and skips the
            # non-iABC formats, so a JMP's jump offset can no longer be read as
            # a constant index. Same discipline as const_uses.
            for which, idx in rk_operands(i):
                if idx >= len(p.constants):
                    rkbad.append("%s pc%d RK.%s=%d out of range"
                                 % (p.path, i.pc, which, idx))
    check("loadk-in-range", not kbad, "; ".join(kbad[:5]))
    check("closure-in-range", not pbad, "; ".join(pbad[:5]))
    check("rk-constant-in-range", not rkbad, "; ".join(rkbad[:5]))

    # 4. jump targets land inside the proto
    jbad = []
    for p in walk(main):
        for i in p.code:
            if i.op >= NUM_OPCODES:
                continue
            tgt = i.branch_target()
            if tgt is not None and not 0 <= tgt <= len(p.code):
                jbad.append("%s pc%d -> %d (code len %d)"
                            % (p.path, i.pc, tgt, len(p.code)))
    check("jumps-in-range", not jbad, "; ".join(jbad[:5]))

    # 5. upvalue name count vs descriptor count. A stripped chunk legitimately
    # has zero names (ldump.c DumpDebug), so only an over- or partial count is
    # an error.
    ubad = ["%s names=%d upvalues=%d" % (p.path, len(p.upvalue_names),
                                          len(p.upvalues))
            for p in walk(main)
            if len(p.upvalue_names) != len(p.upvalues)
            and len(p.upvalue_names) != 0]
    names = sum(len(p.upvalue_names) for p in walk(main))
    check("upvalue-name-count", not ubad,
          "; ".join(ubad[:5]) if ubad
          else "%d upvalue name(s) total (stripped chunks carry none)" % names)

    # 6. debug/local table sanity where present
    lbad = ["%s pc%d" % (p.path, lv.startpc) for p in walk(main)
            for lv in p.locvars if not 0 <= lv.startpc <= len(p.code)]
    check("locvar-pc-in-range", not lbad, "; ".join(lbad[:5]))

    # 7. the main closure's upvalue count in the header must agree with the
    # prototype's descriptor count: luaU_undump asserts exactly this
    # (``lua_assert(cl->nupvalues == cl->p->sizeupvalues)``).
    check("main-upvalue-count", header.main_nupvalues == len(main.upvalues),
          "header says %d, main proto has %d descriptor(s)"
          % (header.main_nupvalues, len(main.upvalues)))

    check("header-accepted", header.version == LUAC_VERSION,
          "version 0x%02x, %d-byte %s, Instruction=%d, size_t=%d, int=%d"
          % (header.version, header.num_size, header.float_kind,
             header.instr_size, header.size_t_size, header.int_size))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _read(path: str) -> bytes:
    """Read a chunk, turning I/O problems into a clear message.

    The caller-facing commands are meant to be run by hand against a list of
    ARC paths, so a mistyped or missing path should say so rather than dump a
    traceback.
    """
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        raise SystemExit("error: no such file: %s" % path)
    except IsADirectoryError:
        raise SystemExit("error: %s is a directory, expected a .lc file" % path)
    except PermissionError:
        raise SystemExit("error: cannot read %s (permission denied)" % path)
    except OSError as exc:
        raise SystemExit("error: cannot read %s: %s" % (path, exc))


def _cmd_header(args: "list[str]") -> int:
    for path in args:
        data = _read(path)
        try:
            hdr, r = check_header(data)
        except ParseError as exc:
            print("%s: HEADER ERROR: %s" % (path, exc))
            continue
        print("== %s" % path)
        print("   size                %d bytes (0x%x)" % (hdr.size, hdr.size))
        print("   version             0x%02x (Lua 5.3)" % hdr.version)
        print("   format              %d" % hdr.format)
        print("   sizeof int          %d" % hdr.int_size)
        print("   sizeof size_t       %d" % hdr.size_t_size)
        print("   sizeof Instruction  %d" % hdr.instr_size)
        print("   sizeof lua_Integer  %d" % hdr.integer_size)
        print("   sizeof lua_Number   %d  (%s)" % (hdr.num_size,
                                                   hdr.float_kind))
        print("   LUAC_INT            0x%x (little-endian confirmed)" % hdr.luac_int)
        print("   LUAC_NUM            %r" % hdr.luac_num)
        print("   header size         %d bytes" % hdr.body_offset)
        print("   main nupvalues      %d (at 0x%x)"
              % (hdr.main_nupvalues, hdr.nupvalues_offset))
        print("   first proto byte    0x%x" % r.pos)
    return 0


def _cmd_prototype_rows(main: Proto) -> "list[str]":
    rows = []
    for p in walk(main):
        rows.append(
            "%-10s @0x%-6x code=%-4d consts=%-3d upvals=%-2d protos=%-3d "
            "lines=%d..%d params=%d vararg=%d maxstack=%d stripped=%s"
            % (p.path, p.offset, len(p.code), len(p.constants),
               len(p.upvalues), len(p.protos), p.linedefined,
               p.lastlinedefined, p.numparams, p.is_vararg, p.maxstacksize,
               p.is_stripped))
    return rows


def _cmd_summary(args: "list[str]") -> int:
    for path in args:
        data = _read(path)
        hdr, main = load_chunk(data)
        protos = list(walk(main))
        print("== %s" % path)
        print("   size            %d bytes" % hdr.size)
        print("   float           %s" % hdr.float_kind)
        print("   protos          %d" % len(protos))
        print("   instructions    %d" % sum(len(p.code) for p in protos))
        print("   constants       %d" % sum(len(p.constants) for p in protos))
        print("   strings         %d"
              % sum(1 for p in protos for k in p.constants if k.is_string))
        print("   upvalues        %d" % sum(len(p.upvalues) for p in protos))
        print("   debug stripped  %s"
              % ("yes" if all(p.is_stripped for p in protos) else "no"))
        print("   consumed        %d / %d bytes"
              % (main.end_offset, len(data)))
        print("   per-proto:")
        for row in _cmd_prototype_rows(main):
            print("     " + row)
    return 0


def _cmd_protos(args: "list[str]") -> int:
    for path in args:
        data = _read(path)
        _hdr, main = load_chunk(data)
        print("== %s" % path)
        for p in walk(main):
            print("proto %s @0x%x .. 0x%x" % (p.path, p.offset, p.end_offset))
            print("  source        %r" % p.source)
            print("  code          %d instrs @0x%x" % (len(p.code), p.code_offset))
            print("  constants     %d @0x%x" % (len(p.constants), p.consts_offset))
            print("  upvalues      %d @0x%x %s"
                  % (len(p.upvalues), p.upvals_offset, p.upvalues))
            print("  upval names   %s" % (p.upvalue_names,))
            print("  children      %d @0x%x" % (len(p.protos), p.protos_offset))
            print("  lineinfo      %d @0x%x" % (len(p.lineinfo), p.lineinfo_offset))
            print("  locvars       %d %s" % (
                len(p.locvars),
                [(lv.name, lv.startpc, lv.endpc) for lv in p.locvars][:8]))
    return 0


def _cmd_dis(args: "list[str]") -> int:
    """Disassemble every prototype of each chunk.

    An optional leading all-digit argument sets the constant-text length limit;
    everything after it is a chunk path. There is no per-prototype filter --
    use ``protos`` to see the list first. (The module docstring used to claim
    ``dis <file> <proto_path>``; corrected in P2-LUA-EDIT, where passing a proto
    name made the file be opened as a path.)
    """
    limit = 60
    if args and args[0].isdigit():
        limit = int(args[0])
        args = args[1:]
    for path in args:
        data = _read(path)
        _hdr, main = load_chunk(data)
        print("== %s" % path)
        for p in walk(main):
            print("--- proto %s @0x%x  maxstack=%d params=%d vararg=%d"
                  % (p.path, p.offset, p.maxstacksize, p.numparams,
                     p.is_vararg))
            for i in p.code:
                extra = explain(i, p, limit)
                flag = "T" if i.is_test else " "
                print("  %s[%3d] 0x%08x @0x%-6x %-10s %-22s %s"
                      % (flag, i.pc, i.word, i.offset, i.name, i.args_text(),
                         extra))
    return 0


def _cmd_constants(args: "list[str]") -> int:
    limit = 80
    for path in args:
        data = _read(path)
        _hdr, main = load_chunk(data)
        print("== %s" % path)
        for p in walk(main):
            if not p.constants:
                continue
            print("--- proto %s: %d constants @0x%x"
                  % (p.path, len(p.constants), p.consts_offset))
            for k in p.constants:
                print("  %-22s tag=0x%02x @0x%-6x %s"
                      % ("K[%d]" % k.index, k.tag, k.tag_offset,
                         k.text(limit)))
    return 0


def _cmd_xref(args: "list[str]") -> int:
    if len(args) < 2:
        print("usage: xref <file.lc> <string> [string ...]", file=sys.stderr)
        return 2
    path, needles = args[0], args[1:]
    data = _read(path)
    _hdr, main = load_chunk(data)
    print("== %s" % path)
    rc = 0
    for needle in needles:
        hits = find_xref(main, needle)
        print("constant %r: %d exact occurrence(s)" % (needle, len(hits)))
        if not hits:
            # fall back to substring so a near-miss is still visible
            for p in walk(main):
                for k in p.constants:
                    if k.is_string and needle.lower() in (k.value or "").lower():
                        print("  ~ substring in %s K[%d] @0x%x: %r"
                              % (p.path, k.index, k.tag_offset, k.value))
            rc = 1 if not hits else rc
            continue
        for p, idx, k in hits:
            print("  %s K[%d] tag=0x%02x @0x%x = %r"
                  % (p.path, idx, k.tag, k.tag_offset, k.value))
            uses = const_uses(p, idx)
            if not uses:
                print("      (no instruction consumes it)")
            for i, how in uses:
                note = explain(i, p, limit=80)
                print("      used via %-5s by [%d] 0x%08x @0x%-6x %-10s %s"
                      % (how, i.pc, i.word, i.offset, i.name,
                         note or i.args_text()))
    return rc


def _cmd_verify(args: "list[str]") -> int:
    rc = 0
    for path in args:
        data = _read(path)
        try:
            hdr, main = load_chunk(data)
        except ParseError as exc:
            print("== %s" % path)
            print("  PARSE ERROR: %s" % exc)
            rc = 1
            continue
        results = verify(main, data, hdr)
        failed = [r for r in results if r.startswith("FAIL")]
        print("== %s  (%s)" % (path, "OK" if not failed else "PROBLEMS"))
        for r in results:
            print("  " + r)
        if failed:
            rc = 1
    return rc


def _cmd_roundtrip(args: "list[str]") -> int:
    """parse -> encode, compared byte-for-byte and by SHA256."""
    import hashlib

    rc = 0
    for path in args:
        data = _read(path)
        try:
            hdr, main = load_chunk(data)
        except ParseError as exc:
            print("== %s" % path)
            print("  PARSE ERROR: %s" % exc)
            rc = 1
            continue
        try:
            out = encode_chunk(hdr, main)
        except EncodeError as exc:
            print("== %s" % path)
            print("  ENCODE ERROR: %s" % exc)
            rc = 1
            continue
        identical = out == data
        h_in = hashlib.sha256(data).hexdigest()
        h_out = hashlib.sha256(out).hexdigest()
        print("== %s" % path)
        print("  input   %d bytes  sha256 %s" % (len(data), h_in))
        print("  encoded %d bytes  sha256 %s" % (len(out), h_out))
        print("  %s round-trip"
              % ("BYTE-IDENTICAL" if identical else "MISMATCH"))
        if not identical:
            rc = 1
            first = next((i for i, (a, b) in enumerate(zip(data, out))
                          if a != b), min(len(data), len(out)))
            print("  first difference at offset 0x%x" % first)
        # a second, independent comparison: reparse the encoded bytes and diff
        # the structure. This catches an encoder that is self-consistent but
        # loses a field, which a hash comparison of identical input would not.
        diffs = diff_chunks(data, out)
        print("  reparse structural diff: %s"
              % ("none" if not diffs else "; ".join(diffs[:6])))
        if diffs:
            rc = 1
    return rc


def _cmd_encode(args: "list[str]") -> int:
    if len(args) != 2:
        print("usage: encode <in.lc> <out.lc>", file=sys.stderr)
        return 2
    data = _read(args[0])
    hdr, main = load_chunk(data)
    out = encode_chunk(hdr, main)
    try:
        with open(args[1], "wb") as fh:
            fh.write(out)
    except OSError as exc:
        raise SystemExit("error: cannot write %s: %s" % (args[1], exc))
    print("wrote %s (%d bytes, identical to input: %s)"
          % (args[1], len(out), out == data))
    return 0


def _cmd_setconst(args: "list[str]") -> int:
    """Replace one string constant. Refuses referenced constants by default."""
    argv = list(args)
    allow_used = False
    if "--allow-used" in argv:
        argv.remove("--allow-used")
        allow_used = True
    if len(argv) != 5:
        print('usage: setconst <in.lc> <out.lc> <proto> <K-index> <text> '
              '[--allow-used]', file=sys.stderr)
        return 2
    path, out_path, proto_path, idx_text, text = argv
    try:
        index = int(idx_text)
    except ValueError:
        print("error: constant index %r is not an integer" % idx_text,
              file=sys.stderr)
        return 2
    data = _read(path)
    hdr, main = load_chunk(data)
    target = next((p for p in walk(main) if p.path == proto_path), None)
    if target is None or not 0 <= index < len(target.constants):
        raise SystemExit("error: %s has no K[%s]" % (proto_path, idx_text))
    uses = const_uses(target, index)
    print("== %s" % path)
    print("  target      %s K[%d] = %r"
          % (proto_path, index, target.constants[index].value))
    print("  new text    %r (%d chars, was %d)"
          % (text, len(text), len(target.constants[index].value or "")))
    if uses and not allow_used:
        print("  REFUSING: this constant is read by %d instruction(s):"
              % len(uses))
        for i, how in uses:
            print("    %-5s [%d] %s %s" % (how, i.pc, i.name,
                                            explain(i, target, 60)))
        print("  A referenced literal may be a bridge name, a selector, a")
        print("  flag, a loop bound or a native argument. Pass --allow-used")
        print("  only if you have established that it is inert.")
        return 1
    if uses:
        print("  WARNING: --allow-used given; %d instruction(s) consume it:"
              % len(uses))
        for i, how in uses:
            print("    %-5s [%d] %s %s" % (how, i.pc, i.name,
                                            explain(i, target, 60)))
    k = set_string_constant(main, proto_path, index, text)
    out = encode_chunk(hdr, main)
    try:
        with open(out_path, "wb") as fh:
            fh.write(out)
    except OSError as exc:
        raise SystemExit("error: cannot write %s: %s" % (out_path, exc))
    print("  wrote       %s (%d bytes, was %d)"
          % (out_path, len(out), len(data)))
    print("  new tag     0x%02x (%s)" % (k.tag,
                                         _TAG_NAMES.get(k.tag, "?")))
    return 0


def _finish(hdr: Header, main: Proto, data: bytes, out_path: str):
    """Encode, re-parse, verify, then write. Refuses to write a failing chunk.

    Re-parsing before reporting matters: byte offsets recorded during the
    initial parse are meaningless once the chunk has grown, so every offset the
    mutators print is read off the re-parsed output.
    """
    out = encode_chunk(hdr, main)
    hdr2, main2 = load_chunk(out)
    res = verify(main2, out, hdr2)
    failed = [r for r in res if r.startswith("FAIL")]
    if failed:
        raise EncodeError("the mutated chunk does not pass verify(), so it was "
                          "NOT written: %s" % "; ".join(failed))
    try:
        with open(out_path, "wb") as fh:
            fh.write(out)
    except OSError as exc:
        raise SystemExit("error: cannot write %s: %s" % (out_path, exc))
    return out, main2


def _refuse(msg: str) -> int:
    """Print a refusal on stderr and return the refusal exit code."""
    print("REFUSING: %s" % msg, file=sys.stderr)
    print("nothing was written", file=sys.stderr)
    return EXIT_REFUSED


def _cmd_appendconst(args: "list[str]") -> int:
    argv = list(args)
    at = None
    if "--at" in argv:
        i = argv.index("--at")
        if i + 1 >= len(argv):
            print("usage: appendconst ... --at <index>", file=sys.stderr)
            return EXIT_USAGE
        at = int(argv[i + 1])
        del argv[i:i + 2]
    if len(argv) != 5:
        print("usage: appendconst <in.lc> <out.lc> <proto> <string|integer|"
              "float> <value> [--at <index>]", file=sys.stderr)
        return EXIT_USAGE
    path, out_path, proto_path, kind, raw = argv
    if kind == "integer":
        try:
            value = int(raw, 0)
        except ValueError:
            return _refuse("integer value %r is not an integer" % raw)
    elif kind == "float":
        try:
            value = float(raw)
        except ValueError:
            return _refuse("float value %r is not a number" % raw)
    else:
        value = raw
    data = _read(path)
    hdr, main = load_chunk(data)
    print("== %s" % path)
    target = next((p for p in walk(main) if p.path == proto_path), None)
    if target is None:
        return _refuse("no such prototype %r (known: %s)"
                       % (proto_path, ", ".join(p.path for p in walk(main))))
    before = len(target.constants)
    print("  target     %s: %d constant(s), new index K[%d]"
          % (proto_path, before, before))
    try:
        k = append_constant(main, hdr, proto_path, kind, value, at=at)
    except EncodeError as exc:
        return _refuse(str(exc))
    try:
        out, main2 = _finish(hdr, main, data, out_path)
    except EncodeError as exc:
        return _refuse(str(exc))
    after = next(p for p in walk(main2) if p.path == proto_path)
    print("  appended   %s K[%d] tag=0x%02x %s"
          % (proto_path, k.index, k.tag, k.text(80)))
    print("  K[0..%d]   unchanged: %d constant(s) before, %d after"
          % (before - 1, before, len(after.constants)))
    print("  reachable  %s" % constant_reachability(after, k.index))
    print("  wrote      %s (%d bytes, was %d, %+d)"
          % (out_path, len(out), len(data), len(out) - len(data)))
    return EXIT_OK


def _cmd_patchins(args: "list[str]") -> int:
    if len(args) < 6:
        print("usage: patchins <in.lc> <out.lc> <proto> <pc> <OP> [A=..] [B=..] "
              "[C=..] | Bx=.. | sBx=.. | Ax=..", file=sys.stderr)
        return EXIT_USAGE
    path, out_path, proto_path, pc_text = args[0], args[1], args[2], args[3]
    try:
        pc = int(pc_text, 0)
    except ValueError:
        print("usage: pc %r is not an integer" % pc_text, file=sys.stderr)
        return EXIT_USAGE
    try:
        opname, fields = _parse_spec(args[4:])
    except EncodeError as exc:
        return _refuse(str(exc))
    data = _read(path)
    hdr, main = load_chunk(data)
    print("== %s" % path)
    target = next((p for p in walk(main) if p.path == proto_path), None)
    if target is None:
        return _refuse("no such prototype %r (known: %s)"
                       % (proto_path, ", ".join(p.path for p in walk(main))))
    if not 0 <= pc < len(target.code):
        return _refuse("%s has %d instruction(s), so pc %d does not exist"
                       % (proto_path, len(target.code), pc))
    was = target.code[pc]
    print("  old        pc%-4d 0x%08x %-10s %s"
          % (pc, was.word, was.name,
             explain(was, target, 80) or was.args_text()))
    print("  new        pc%-4d %s %s" % (pc, opname,
                                         " ".join("%s=%d" % kv
                                                  for kv in sorted(fields.items()))))
    try:
        old_word, new_word = patch_instruction(main, proto_path, pc,
                                               opname, fields)
    except EncodeError as exc:
        return _refuse(str(exc))
    try:
        out, main2 = _finish(hdr, main, data, out_path)
    except EncodeError as exc:
        return _refuse(str(exc))
    now = next(p for p in walk(main2) if p.path == proto_path).code[pc]
    print("  result     old 0x%08x %-10s -> new 0x%08x %-10s %s"
          % (old_word, was.name, new_word, now.name,
             explain(now, target, 80) or now.args_text()))
    print("  wrote      %s (%d bytes, was %d, %+d)"
          % (out_path, len(out), len(data), len(out) - len(data)))
    return EXIT_OK


def _cmd_insertins(args: "list[str]") -> int:
    if len(args) < 6:
        print("usage: insertins <in.lc> <out.lc> <proto> <pc> <N> "
              "<OP> [fields...] x N", file=sys.stderr)
        return EXIT_USAGE
    path, out_path, proto_path, pc_text, count_text = args[:5]
    rest = args[5:]
    try:
        pc = int(pc_text, 0)
        count = int(count_text, 0)
    except ValueError:
        print("usage: pc/count must be integers", file=sys.stderr)
        return EXIT_USAGE
    if count < 1:
        return _refuse("N=%d; nothing to insert" % count)
    if len(rest) < count:
        print("usage: N=%d but only %d instruction spec(s) given"
              % (count, len(rest)), file=sys.stderr)
        return EXIT_USAGE
    specs = []
    # group the tokens: an opcode is a token with no '='; everything up to the
    # next such token belongs to it
    groups: "list[list[str]]" = []
    for tok in rest:
        if "=" in tok or groups:
            groups[-1].append(tok) if groups else groups.append([tok])
        else:
            groups.append([tok])
    if len(groups) != count:
        print("usage: N=%d but the arguments describe %d instruction(s)"
              % (count, len(groups)), file=sys.stderr)
        return EXIT_USAGE
    try:
        specs = [_parse_spec(g) for g in groups]
    except EncodeError as exc:
        return _refuse(str(exc))

    data = _read(path)
    hdr, main = load_chunk(data)
    print("== %s" % path)
    target = next((p for p in walk(main) if p.path == proto_path), None)
    if target is None:
        return _refuse("no such prototype %r (known: %s)"
                       % (proto_path, ", ".join(p.path for p in walk(main))))
    print("  target     %s: %d instruction(s), inserting %d at pc %d"
          % (proto_path, len(target.code), count, pc))
    for opname, fields in specs:
        print("  insert     %s %s" % (opname,
                                       " ".join("%s=%d" % kv
                                                for kv in sorted(fields.items()))))
    try:
        rep = insert_instructions(main, proto_path, pc, specs)
    except EncodeError as exc:
        return _refuse(str(exc))
    try:
        out, main2 = _finish(hdr, main, data, out_path)
    except EncodeError as exc:
        return _refuse(str(exc))
    after = next(p for p in walk(main2) if p.path == proto_path)
    print("  length     %d -> %d instruction(s)"
          % (rep["old_len"], rep["new_len"]))
    if rep["relocated"]:
        print("  relocated  %d iAsBx jump(s):" % len(rep["relocated"]))
        for r in rep["relocated"]:
            tag = "  (unchanged)" if r["old_sbx"] == r["new_sbx"] else ""
            print("    pc%-4d %-9s sBx %+d -> %+d   target pc %d -> pc %d%s"
                  % (r["pc"], r["name"], r["old_sbx"], r["new_sbx"],
                     r["old_target"], r["new_target"], tag))
    else:
        print("  relocated  no iAsBx jump needed moving")
    if rep["lineinfo_adjusted"]:
        print("  lineinfo   %d entr(ies) -> %d, inserted instructions inherit "
              "line %d" % (rep["old_len"], rep["new_len"],
                           rep["line_of_inserted"]))
    for name, before, after_pc in rep["locvars_moved"]:
        print("  locvar     %s pc %s -> %s" % (name, before, after_pc))
    print("  code       %d instruction(s) after pc %d shifted by %+d"
          % (rep["new_len"] - rep["pc"], rep["pc"], rep["inserted"]))
    print("  wrote      %s (%d bytes, was %d, %+d)"
          % (out_path, len(out), len(data), len(out) - len(data)))
    return EXIT_OK


def _cmd_compare(args: "list[str]") -> int:
    if len(args) != 2:
        print("usage: compare <a.lc> <b.lc>", file=sys.stderr)
        return 2
    diffs = diff_chunks(_read(args[0]), _read(args[1]))
    print("== %s vs %s" % (args[0], args[1]))
    if not diffs:
        print("  no structural differences")
        return 0
    print("  %d structural difference(s):" % len(diffs))
    for d in diffs:
        print("    " + d)
    return 0


def _cmd_synth(args: "list[str]") -> int:
    if len(args) != 1:
        print("usage: synth <out.lc>", file=sys.stderr)
        return 2
    hdr, main = build_synthetic_chunk()
    data = encode_chunk(hdr, main)
    try:
        with open(args[0], "wb") as fh:
            fh.write(data)
    except OSError as exc:
        raise SystemExit("error: cannot write %s: %s" % (args[0], exc))
    print("wrote %s (%d bytes, synthetic test chunk)" % (args[0], len(data)))
    return 0


_COMMANDS = {
    "header": _cmd_header,
    "summary": _cmd_summary,
    "protos": _cmd_protos,
    "dis": _cmd_dis,
    "constants": _cmd_constants,
    "xref": _cmd_xref,
    "verify": _cmd_verify,
    "roundtrip": _cmd_roundtrip,
    "encode": _cmd_encode,
    "setconst": _cmd_setconst,
    "appendconst": _cmd_appendconst,
    "patchins": _cmd_patchins,
    "insertins": _cmd_insertins,
    "compare": _cmd_compare,
    "synth": _cmd_synth,
}


def main(argv: "list[str]") -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0 if len(argv) >= 2 else 2
    cmd = argv[1]
    if cmd not in _COMMANDS:
        print("unknown command %r; expected one of: %s"
              % (cmd, ", ".join(sorted(_COMMANDS))), file=sys.stderr)
        return 2
    return _COMMANDS[cmd](argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
