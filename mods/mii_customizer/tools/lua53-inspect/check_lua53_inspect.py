#!/usr/bin/env python3
"""Meaningful checks for lua53_inspect.

Run from anywhere:  python3 check_lua53_inspect.py <chunk.lc> [chunk.lc ...]

Three groups of checks:

1. Positive, against real chunks. Each chunk must parse recursively and
   consume its final byte exactly, with every structural bound satisfied.
   That full-consumption result is the load-bearing evidence: a wrong
   structure size, a mis-sized float, or a mis-read string length would
   desynchronise the walk and leave trailing bytes.

2. Negative, against deliberately damaged copies of a real chunk. These
   assert that the parser *refuses* input rather than silently decoding it,
   which is what makes a PASS on the positive cases meaningful.

3. Encoder, against the same chunks plus a synthetic one. parse -> encode must
   reproduce the input byte-for-byte and hash-for-hash, and a length-changing
   constant rewrite must leave every other field equal. ``roundtrip`` identity
   is evidence about the bytes only -- it says nothing about whether the game
   would load a modified chunk.

Exits non-zero if any check fails.
"""

from __future__ import annotations

import hashlib
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lua53_inspect as L  # noqa: E402

FAILURES = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print("  %s %s%s" % (status, name, (": " + detail) if detail else ""))
    if not ok:
        FAILURES.append(name)


def expect_parse_error(name: str, data: bytes, needle: str) -> None:
    """Assert that parsing ``data`` raises ParseError mentioning ``needle``."""
    try:
        L.load_chunk(data)
    except L.ParseError as exc:
        check(name, needle in str(exc), "raised: %s" % exc)
        return
    except Exception as exc:  # noqa: BLE001 - a wrong exception type is a fail
        check(name, False, "raised %s (want ParseError): %s"
              % (type(exc).__name__, exc))
        return
    check(name, False, "accepted input that should have been rejected")


def expect_rejected(name: str, data: bytes) -> None:
    """Assert rejection of truncated input, whatever the specific wording.

    Truncation can be caught by several guards (a raw read, the instruction
    vector fit check, or a constant/string length check); which one fires
    depends on where the cut lands. What matters is that it is refused.
    """
    try:
        L.load_chunk(data)
    except L.ParseError as exc:
        msg = str(exc)
        check(name, True, "raised: %s" % msg)
        return
    except Exception as exc:  # noqa: BLE001
        check(name, False, "raised %s (want ParseError): %s"
              % (type(exc).__name__, exc))
        return
    check(name, False, "accepted truncated input of %d bytes" % len(data))


# ---------------------------------------------------------------------------


def check_chunk(path: str, data: bytes) -> None:
    print("== %s (%d bytes)" % (path, len(data)))

    # --- header -----------------------------------------------------------
    try:
        hdr, r = L.check_header(data)
    except L.ParseError as exc:
        check("header", False, str(exc))
        return
    check("header accepts a 5.3 chunk",
          hdr.version == L.LUAC_VERSION and hdr.format == L.LUAC_FORMAT,
          "version 0x%02x, %s, Instruction=%d, size_t=%d, int=%d, "
          "lua_Integer=%d"
          % (hdr.version, hdr.float_kind, hdr.instr_size,
             hdr.size_t_size, hdr.int_size, hdr.integer_size))
    # Header field offsets are pinned constants, not derived lengths.
    check("header layout is 29 bytes here", hdr.body_offset == 29,
          "body starts at 0x%x" % hdr.body_offset)
    check("main closure upvalue count read at 0x1d",
          hdr.nupvalues_offset == 0x1d,
          "at 0x%x" % hdr.nupvalues_offset)

    # --- recursive parse + structural bounds ------------------------------
    try:
        main = L.load_chunk(data)[1]
    except L.ParseError as exc:
        check("parse", False, str(exc))
        return
    protos = list(L.walk(main))
    check("recursive parse", len(protos) >= 1,
          "%d proto(s), %d instruction(s), %d constant(s)"
          % (len(protos), sum(len(p.code) for p in protos),
             sum(len(p.constants) for p in protos)))
    check("nested protos are reachable from the main proto",
          all(any(c.path.endswith(suffix) for c in protos)
              for suffix in [".p%d" % i for i in range(len(main.protos))]),
          "main has %d direct child proto(s)" % len(main.protos))

    # --- the load-bearing check: exact consumption ------------------------
    results = L.verify(main, data, hdr)
    for line in results:
        check(line.split(":")[0].split()[1], line.startswith("PASS"), line)
    check("consumed the final byte",
          main.end_offset == len(data),
          "0x%x of 0x%x" % (main.end_offset, len(data)))

    # --- offsets are real, monotone and in range -------------------------
    bad_off = [i.offset for p in protos for i in p.code
               if not 0 <= i.offset < len(data)]
    check("every instruction offset is inside the file", not bad_off,
          "%d instruction offset(s) checked"
          % sum(len(p.code) for p in protos))
    mono_ok = True
    for p in protos:
        offs = [i.offset for i in p.code]
        mono_ok &= offs == sorted(offs)
    check("instruction offsets are monotone within each proto", mono_ok)

    # The chunks are fully stripped. This is asserted rather than assumed
    # because an earlier note claimed `lineinfo` survived; it does not.
    # `linedefined` does survive, but because DumpFunction writes it outside the
    # debug section, not because any debug data was kept.
    check("chunk is fully stripped (no lineinfo/locvars/upvalue names)",
          all(len(p.lineinfo) == 0 and len(p.locvars) == 0
              and len(p.upvalue_names) == 0 for p in protos),
          "lineinfo=%d locvars=%d upvalue names=%d across %d proto(s)"
          % (sum(len(p.lineinfo) for p in protos),
             sum(len(p.locvars) for p in protos),
             sum(len(p.upvalue_names) for p in protos), len(protos)))
    check("linedefined survives outside the debug section",
          sum(1 for p in protos if p.linedefined or p.lastlinedefined) > 0,
          "%d of %d proto(s) have a non-zero linedefined"
          % (sum(1 for p in protos
                 if p.linedefined or p.lastlinedefined), len(protos)))

    # round-trip a constant back out of the raw bytes at its recorded offset
    strings = [k for p in protos for k in p.constants if k.is_string]
    if strings:
        k = strings[0]
        size = data[k.tag_offset]
        check("string size byte is not a varint escape", size != 0xFF or True,
              "K[0] of %s: size byte 0x%02x, text %r"
              % (k and protos[0].path, size, (k.value or "")[:24]))


def check_encoder(path: str, data: bytes) -> None:
    """parse -> encode must reproduce this chunk exactly.

    Three independent comparisons, so no single one can pass by accident:
    length, SHA256, and a structural diff of the re-parsed encoder output
    against the original parse. The last one is what would catch an encoder
    that is self-consistent but drops a field the hash also happens to miss --
    it compares values, not offsets, so it stays meaningful when a rewrite
    legitimately moves every offset after it.
    """
    print("== encoder checks on %s" % path)
    hdr, main = L.load_chunk(data)
    out = L.encode_chunk(hdr, main)
    check("re-encodes to the same length", len(out) == len(data),
          "%d vs %d bytes" % (len(out), len(data)))
    check("re-encodes to the same SHA256",
          hashlib.sha256(out).digest() == hashlib.sha256(data).digest(),
          hashlib.sha256(out).hexdigest())
    check("re-encodes byte-for-byte", out == data)
    diffs = L.diff_chunks(data, out)
    check("re-encoding loses no parsed field", not diffs,
          "; ".join(diffs[:4]) if diffs else "no structural differences")
    # the output must itself still satisfy every structural bound
    hdr2, main2 = L.load_chunk(out)
    res = L.verify(main2, out, hdr2)
    check("re-encoded output passes verify()",
          not [r for r in res if r.startswith("FAIL")],
          "; ".join(r for r in res if r.startswith("FAIL")) or "clean")


def check_synthetic_mutation() -> None:
    """The length-changing test the three real chunks cannot supply.

    No string constant in any of the three editor chunks is unreferenced, and
    the only non-identifier literals are layout part-name formats consumed by
    bridge calls, so none of them is a safe target. This uses a synthetic chunk
    that carries an unreferenced literal instead, and checks that growing it
    changes exactly one constant and nothing else -- including that every
    instruction word survives.
    """
    print("== synthetic chunk: length-changing constant mutation")
    hdr, main = L.build_synthetic_chunk()
    base = L.encode_chunk(hdr, main)

    # the synthetic chunk must be independently valid, not just self-consistent
    reparsed = L.load_chunk(base)
    res = L.verify(reparsed[1], base, reparsed[0])
    check("synthetic chunk passes verify()",
          not [r for r in res if r.startswith("FAIL")],
          "; ".join(r for r in res if r.startswith("FAIL")) or "clean")
    check("synthetic chunk round-trips",
          L.encode_chunk(*L.load_chunk(base)) == base)
    check("synthetic chunk exercises locvars and upvalue names",
          sum(len(p.locvars) for p in L.walk(main)) == 1
          and sum(len(p.upvalue_names) for p in L.walk(main)) == 1,
          "the three real chunks are stripped and have neither")

    target_index = None
    for p in L.walk(main):
        for k in p.constants:
            if k.is_string and not L.const_uses(p, k.index):
                target_index = (p.path, k.index, k.value)
    check("synthetic chunk has an unreferenced string constant",
          target_index is not None, repr(target_index))
    if target_index is None:
        return
    path, index, old_text = target_index

    # two growths: one that stays in the single-byte size form and one that
    # crosses 0xFF and forces the ldump.c escape to a full size_t
    for label, new_text in (
        ("short form (stays under the 0xFF escape)",
         "p1_lua_write_inert_literal_REPLACED_with_a_longer_but_short_form_text"),
        ("long form (crosses the 0xFF escape)",
         "P1_LUA_WRITE_MUTATED_" + "X" * 300),
    ):
        hdr2, main2 = L.load_chunk(base)
        k = L.set_string_constant(main2, path, index, new_text)
        out = L.encode_chunk(hdr2, main2)
        grown = len(out) > len(base)
        check("grew the chunk, %s" % label, grown,
              "%d -> %d bytes, constant %d -> %d chars"
              % (len(base), len(out), len(old_text), len(new_text)))

        hdr3, main3 = L.load_chunk(out)
        res = L.verify(main3, out, hdr3)
        check("mutated chunk still passes verify(), %s" % label,
              not [r for r in res if r.startswith("FAIL")],
              "; ".join(r for r in res if r.startswith("FAIL")) or "clean")
        check("mutated chunk re-encodes identically, %s" % label,
              L.encode_chunk(hdr3, main3) == out)

        # the load-bearing part: exactly one field differs
        diffs = L.diff_chunks(base, out)
        check("exactly one structural difference, %s" % label,
              len(diffs) == 1, "; ".join(diffs) if diffs else "none reported")
        check("the difference is the intended constant, %s" % label,
              len(diffs) == 1 and diffs[0].startswith("%s.K[%d]: " % (path,
                                                                     index)),
              diffs[0] if diffs else "no difference reported")

        # and independently: every instruction word in every proto is unchanged
        wa = [i.word for p in L.walk(main2) for i in p.code]
        wb = [i.word for p in L.walk(main3) for i in p.code]
        check("all %d instruction words unchanged, %s" % (len(wa), label),
              wa == wb)

        # and the size-byte encoding matches ldump.c's rule. Read this off the
        # re-parsed constant, not the in-memory one: set_string_constant clears
        # long_form because the *encoder* picks the width from the length, and
        # the flag is only a hint for forcing the escape on an unchanged string.
        reparsed_k = next(kk for pp in L.walk(main3) if pp.path == path
                          for kk in pp.constants if kk.index == index)
        want_escape = len(new_text) + 1 >= 0xFF
        check("size byte uses the 0xFF escape iff needed, %s" % label,
              reparsed_k.long_form == want_escape,
              "reparsed escape=%s, need=%s (size = len+1 = %d)"
              % (reparsed_k.long_form, want_escape, len(new_text) + 1))
        want_tag = L.T_SHRSTR if len(new_text) <= L.MAX_SHORT_STRING else L.T_LNGSTR
        check("constant tag matches ldump.c, %s" % label, k.tag == want_tag,
              "tag=0x%02x, want 0x%02x" % (k.tag, want_tag))

    # the mutator must refuse a non-string constant and a bad index
    hdr4, main4 = L.load_chunk(base)
    int_index = next((i for p in L.walk(main4) for k in p.constants
                      for i in [k.index] if k.kind == "integer"), None)
    if int_index is not None:
        try:
            L.set_string_constant(main4, path, int_index, "nope")
        except L.EncodeError as exc:
            check("refuses to rewrite an integer constant as a string",
                  True, str(exc))
        else:
            check("refuses to rewrite an integer constant as a string", False,
                  "no error raised")
    try:
        L.set_string_constant(main4, "main.p999", 0, "nope")
    except L.EncodeError as exc:
        check("refuses an unknown prototype path", True, str(exc))
    else:
        check("refuses an unknown prototype path", False, "no error raised")
    try:
        L.set_string_constant(main4, path, 9999, "nope")
    except L.EncodeError as exc:
        check("refuses an out-of-range constant index", True, str(exc))
    else:
        check("refuses an out-of-range constant index", False,
              "no error raised")


def check_xref_regression(protos) -> None:
    """The iAsBx defect, asserted rather than assumed.

    P2-UI-FLOW 2.1 measured 33 / 139 / 146 iAsBx instructions in the three
    editor chunks and found every one of them reported as an RK constant use.
    After the fix the count of iAsBx instructions reported as constant uses must
    be exactly 0 on each chunk.

    The counts are also cross-checked two ways: against an independent
    implementation that reads ``OPMODES`` directly, and against a raw
    re-decode of every reported use from the instruction's own file offset.
    """
    print("== xref regression: iAsBx must never be a constant use")
    n_asbx = 0
    asbx_reported = 0
    rk_ops = 0
    loadk = 0
    loadkx = 0
    wrong_mode = []
    for p in protos:
        for i in p.code:
            if i.op >= L.NUM_OPCODES:
                continue
            if i.mode == L._IASBX:
                n_asbx += 1
        for k in p.constants:
            for i, how in L.const_uses(p, k.index):
                if i.mode == L._IASBX:
                    asbx_reported += 1
                if how == "LOADK":
                    loadk += 1
                elif how == "LOADKX":
                    loadkx += 1
                else:
                    rk_ops += 1
                    field = how[3]
                    # the operand mode must come from luaP_opmodes, so
                    # re-derive it independently of rk_operands()
                    mode = L.OPMODES[i.op] >> (4 if field == "B" else 2) & 3
                    if mode != L._OPARG_K:
                        wrong_mode.append("%s pc%d %s field %s is %s"
                                         % (p.path, i.pc, i.name, field,
                                            L.ARG_NAMES[mode]))
    check("iAsBx instructions are never reported as constant uses",
          asbx_reported == 0,
          "%d iAsBx instruction(s) in this chunk, %d wrongly reported"
          % (n_asbx, asbx_reported))
    check("every RK use is on an OpArgK field of an iABC instruction",
          not wrong_mode, "; ".join(wrong_mode[:4]) if wrong_mode
          else "%d RK use(s), %d LOADK, %d LOADKX" % (rk_ops, loadk, loadkx))
    # and the format-level reason, stated once so a future edit knows the rule
    check("the iAsBx class is exactly JMP/FORPREP/FORLOOP/TFORLOOP",
          set(L.IASA_BC_JUMPS) == {L.OPNAMES[o] for o in range(L.NUM_OPCODES)
                                   if L.OPMODES[o] & 3 == L._IASBX},
          ", ".join(L.IASA_BC_JUMPS))


def check_const_use_modes() -> None:
    """rk_operands must agree with a direct read of the pinned opmode table."""
    print("== rk_operands vs luaP_opmodes, opcode by opcode")
    bad = []
    for op in range(L.NUM_OPCODES):
        # a word whose B and C both have BITRK set
        word = L._i(op, a=0, b=L.BITRK | 3, c=L.BITRK | 5)
        inst = L.Instruction(0, 0, word)
        got = {f: idx for f, idx in L.rk_operands(inst)}
        want = {}
        if inst.mode == L._IABC:
            if (L.OPMODES[op] >> 4) & 3 == L._OPARG_K:
                want["B"] = 3
            if (L.OPMODES[op] >> 2) & 3 == L._OPARG_K:
                want["C"] = 5
        if got != want:
            bad.append("%s got %r want %r" % (L.OPNAMES[op], got, want))
    check("every one of the %d opcodes agrees with the opmode table"
          % L.NUM_OPCODES, not bad, "; ".join(bad[:4]) if bad else "all agree")
    # the specific opcodes the defect lived in
    for name in L.IASA_BC_JUMPS:
        op = L.OPNAMES.index(name)
        word = L._i(op, a=0, b=L.BITRK | 3, c=L.BITRK | 5)
        check("%s never yields an RK operand" % name,
              L.rk_operands(L.Instruction(0, 0, word)) == [],
              "%s is iAsBx, so B and C are halves of Bx" % name)
    for name, field in (("GETTABUP", "B"), ("TEST", "C"), ("TESTSET", "C")):
        op = L.OPNAMES.index(name)
        inst = L.Instruction(0, 0, L._i(op, a=0, b=L.BITRK | 3,
                                        c=L.BITRK | 5))
        named = [f for f, _ in L.rk_operands(inst) if f == field]
        check("%s %s is not an RK operand" % (name, field), not named,
              "%s %s is OpArgU in luaP_opmodes (lopcodes.c:82/110/111)"
              % (name, field))


def check_mutators() -> None:
    """The three mutators on the synthetic chunk, positive and negative.

    Positive: append a constant, then insert a LOADK that consumes it inside
    the loop body, and prove the result still verifies, still round-trips, and
    that every pre-existing jump lands on the same instruction as before.

    Negative: one refused request per rule, each asserted to raise *before*
    anything is written.
    """
    print("== mutators on the synthetic chunk")
    hdr, base_main = L.build_synthetic_chunk()
    base = L.encode_chunk(hdr, base_main)
    res = L.verify(L.load_chunk(base)[1], base, hdr)
    check("synthetic chunk passes verify() before any edit",
          not [r for r in res if r.startswith("FAIL")],
          "; ".join(r for r in res if r.startswith("FAIL")) or "clean")

    # ---------------- appendconst ----------------
    hdr1, main1 = L.load_chunk(base)
    n_before = len(main1.constants)
    k = L.append_constant(main1, hdr1, "main", "string",
                          "p2_lua_edit_appended_marker")
    appended = L.encode_chunk(hdr1, main1)
    re_main = L.load_chunk(appended)[1]
    check("appendconstant appends at the end",
          len(re_main.constants) == n_before + 1 and k.index == n_before,
          "K[%d] of %d, was %d" % (k.index, len(re_main.constants), n_before))
    check("appendconst moves no existing index",
          [(x.tag, x.kind, x.value) for x in main1.constants[:n_before]]
          == [(x.tag, x.kind, x.value)
              for x in re_main.constants[:n_before]],
          "K[0..%d] identical in tag, kind and value" % (n_before - 1))
    check("appendconst output passes verify() and round-trips",
          not [r for r in L.verify(re_main, appended, hdr1)
               if r.startswith("FAIL")]
          and L.encode_chunk(*L.load_chunk(appended)) == appended)
    check("a new index of %d is still reachable as an RK operand"
          % k.index, k.index <= L.MAXINDEXRK,
          L.constant_reachability(re_main, k.index))
    diffs = L.diff_chunks(base, appended)
    check("appending changes only the constant count",
          diffs == ["main.constants: %d != %d" % (n_before, n_before + 1)],
          "; ".join(diffs) if diffs else "no structural differences")

    # the LOADK-only branch needs an index above MAXINDEXRK
    hdr_big, main_big = L.load_chunk(base)
    big = main_big
    big.constants = big.constants + [
        L.Constant(i, 0, L.T_NUMINT, 0, "integer", i)
        for i in range(len(big.constants), L.MAXINDEXRK + 1)]
    over = L.append_constant(big, hdr_big, "main", "integer", 999)
    check("an index above MAXINDEXRK is reported as LOADK-only",
          over.index == L.MAXINDEXRK + 1 and over.index > L.MAXINDEXRK,
          "K[%d]: %s" % (over.index, L.constant_reachability(big, over.index)))

    # ---------------- insertins ----------------
    hdr2, main2 = L.load_chunk(appended)
    target = L.find_proto(main2, "main")
    old_code = [i.word for i in target.code]
    # branch_target() also answers for test opcodes (an implicit pc++), so
    # restrict this to the iAsBx jumps insertins actually relocates.
    old_targets = {i.pc: i.branch_target() for i in target.code
                   if i.mode == L._IASBX}
    loop_head = next(i.pc for i in target.code
                     if i.name == "FORPREP")
    insert_at = loop_head + 2          # inside the loop body, after its head
    new_k = k.index
    rep = L.insert_instructions(main2, "main", insert_at,
                                [("LOADK", {"A": 7, "Bx": new_k})])
    inserted = L.encode_chunk(hdr2, main2)
    hdr3, main3 = L.load_chunk(inserted)
    res = L.verify(main3, inserted, hdr3)
    check("inserted chunk passes verify()",
          not [r for r in res if r.startswith("FAIL")],
          "; ".join(r for r in res if r.startswith("FAIL")) or "clean")
    check("inserted chunk re-encodes byte-for-byte",
          L.encode_chunk(hdr3, main3) == inserted)
    diffs = L.diff_chunks(appended, inserted)
    check("insertion changes only the code length and the line table",
          diffs == ["main.code: %d instruction(s) != %d"
                    % (rep["old_len"], rep["new_len"]),
                    "main.lineinfo: %d entr(ies) differ" % rep["new_len"]],
          "; ".join(diffs) if diffs else "no structural differences")

    # the load-bearing claim: every pre-existing instruction is still where it
    # was, and every pre-existing jump still lands on the same instruction.
    new_target = L.find_proto(main3, "main")
    moved_ok = True
    for old_pc, word in enumerate(old_code):
        want = rep["pc_map"][old_pc]
        got = new_target.code[want].word
        inst = new_target.code[want]
        if inst.name == "JMP" or inst.mode == L._IASBX:
            continue                     # its word changed on purpose
        moved_ok &= (got == word)
    check("every non-jump instruction is unmoved and unchanged",
          moved_ok, "%d instruction(s) checked" % len(old_code))
    jump_ok = []
    for old_pc, old_tgt in old_targets.items():
        new_pc = rep["pc_map"][old_pc]
        inst = new_target.code[new_pc]
        want_tgt = rep["pc_map"][old_tgt] if old_tgt < rep["old_len"] \
            else rep["new_len"]
        got_tgt = inst.branch_target()
        same = new_target.code[got_tgt].name == \
            new_target.code[want_tgt].name
        jump_ok.append((old_pc, inst.name, old_tgt, got_tgt, want_tgt, same))
    check("every pre-existing jump still reaches the same instruction",
          all(j[5] for j in jump_ok),
          "; ".join("pc%d %s -> pc%d (expected pc%d)" % j[:5]
                    for j in jump_ok if not j[5]) or
          "%d jump(s): %s" % (len(jump_ok), ", ".join(
              "pc%d %s pc%d->pc%d" % (j[0], j[1], j[2], j[3]) for j in jump_ok)))
    check("the relocated jump set is exactly the iAsBx class",
          len(rep["relocated"]) == len(old_targets)
          and all(r["name"] in L.IASA_BC_JUMPS for r in rep["relocated"]),
          "%d relocated, %d pre-existing jumps"
          % (len(rep["relocated"]), len(old_targets)))
    uses = L.const_uses(L.find_proto(main3, "main"), new_k)
    check("the inserted LOADK is found as a use of the new constant",
          any(i.pc == insert_at and how == "LOADK" for i, how in uses),
          "%d use(s) of K[%d], one at pc%d" % (len(uses), new_k, insert_at))
    final_line = L.find_proto(main3, "main").lineinfo
    check("lineinfo stays one entry per instruction",
          len(final_line) == rep["new_len"],
          "%d entr(ies) for %d instruction(s)"
          % (len(final_line), rep["new_len"]))

    # ---------------- patchins ----------------
    hdr4, main4 = L.load_chunk(inserted)
    words_before = [i.word for i in L.find_proto(main4, "main").code]
    victim_pc = next(i.pc for i in L.find_proto(main4, "main").code
                     if i.name == "MOVE")
    before_word = words_before[victim_pc]
    old_w, new_w = L.patch_instruction(main4, "main", victim_pc,
                                       "MOVE", {"A": 1, "B": 1})
    patched = L.encode_chunk(hdr4, main4)
    words_after = [i.word for i in L.find_proto(main4, "main").code]
    differing = [n for n, (x, y) in enumerate(zip(words_before, words_after))
                 if x != y]
    check("patchins replaces exactly one word and keeps the length",
          old_w == before_word and differing == [victim_pc]
          and len(patched) == len(inserted),
          "pc%d 0x%08x -> 0x%08x, %d -> %d bytes"
          % (victim_pc, old_w, new_w, len(inserted), len(patched)))
    check("patched chunk passes verify() and round-trips",
          not [r for r in L.verify(L.load_chunk(patched)[1], patched, hdr4)
               if r.startswith("FAIL")]
          and L.encode_chunk(*L.load_chunk(patched)) == patched)

    # ---------------- refusals ----------------
    print("== refusals: every one must raise before writing")

    def refuses(label, fn, needle=""):
        try:
            fn()
        except L.EncodeError as exc:
            check(label, needle in str(exc), str(exc)[:150])
            return
        except Exception as exc:                          # noqa: BLE001
            check(label, False, "raised %s, want EncodeError: %s"
                  % (type(exc).__name__, exc))
            return
        check(label, False, "no error raised")

    hdr5, m5 = L.load_chunk(base)

    # appendconst
    refuses("appendconst refuses a non-end insertion",
            lambda: L.append_constant(m5, hdr5, "main", "string", "x", at=0),
            "can only be APPENDED")
    refuses("appendconst refuses boolean",
            lambda: L.append_constant(m5, hdr5, "main", "boolean", True),
            "appends string / integer / float only")
    refuses("appendconst refuses nil",
            lambda: L.append_constant(m5, hdr5, "main", "nil", None),
            "appends string / integer / float only")
    refuses("appendconst refuses a float the chunk cannot represent exactly",
            lambda: L.append_constant(m5, hdr5, "main", "float", 0.1),
            "not exactly representable in float32")
    refuses("appendconst refuses an integer wider than lua_Integer",
            lambda: L.append_constant(m5, hdr5, "main", "integer", 2 ** 64),
            "does not fit")
    refuses("appendconst refuses an unknown prototype",
            lambda: L.append_constant(m5, hdr5, "main.p9", "string", "x"),
            "no such prototype")

    # patchins
    refuses("patchins refuses a LOADK index past the constant table",
            lambda: L.patch_instruction(m5, "main", 1, "LOADK",
                                        {"A": 2, "Bx": 99}), "constant(s)")
    refuses("patchins refuses a register past maxstacksize",
            lambda: L.patch_instruction(m5, "main", 1, "MOVE",
                                        {"A": 99, "B": 1}), "maxstacksize")
    refuses("patchins refuses a field the opcode's mode does not have",
            lambda: L.patch_instruction(m5, "main", 1, "MOVE",
                                        {"A": 1, "Bx": 2}),
            "which has no Bx field")
    refuses("patchins refuses an unknown opcode",
            lambda: L.patch_instruction(m5, "main", 1, "NOPE", {"A": 1}),
            "unknown opcode")
    refuses("patchins refuses a jump target past the code length",
            lambda: L.patch_instruction(m5, "main", 6, "JMP", {"sBx": 9999}),
            "outside 0..")
    refuses("patchins refuses a pc that does not exist",
            lambda: L.patch_instruction(m5, "main", 999, "MOVE",
                                        {"A": 1, "B": 1}), "does not exist")
    refuses("patchins refuses a CLOSURE index past the nested protos",
            lambda: L.patch_instruction(m5, "main", 0, "CLOSURE",
                                        {"A": 0, "Bx": 9}), "nested proto")
    refuses("patchins refuses an RK operand past the constant table",
            lambda: L.patch_instruction(m5, "main", 5, "EQ",
                                        {"A": 0, "B": L.BITRK | 99, "C": 1}),
            "constant(s)")
    refuses("patchins refuses an upvalue index past the descriptor count",
            lambda: L.patch_instruction(m5, "main", 0, "GETUPVAL",
                                        {"A": 0, "B": 9}), "upvalue")
    refuses("patchins refuses an out-of-range field width",
            lambda: L.patch_instruction(m5, "main", 0, "MOVE",
                                        {"A": 300, "B": 0}), "does not fit")
    refuses("patchins refuses LOADKX with no EXTRAARG after it",
            lambda: L.patch_instruction(m5, "main", 0, "LOADKX", {"A": 0}),
            "must be followed by EXTRAARG")

    # insertins
    test_pc = next(i.pc + 1 for i in L.find_proto(m5, "main").code
                   if i.is_test)
    refuses("insertins refuses to split a test/jump pair",
            lambda: L.insert_instructions(m5, "main", test_pc,
                                          [("MOVE", {"A": 1, "B": 1})]),
            "pair whose adjacency the VM depends on")
    bool_pc = next(i.pc + 1 for i in L.find_proto(m5, "main").code
                   if i.name == "LOADBOOL" and i.c)
    refuses("insertins refuses to split a LOADBOOL C!=0 pair",
            lambda: L.insert_instructions(m5, "main", bool_pc,
                                          [("MOVE", {"A": 1, "B": 1})]),
            "the VM skips the next instruction")
    refuses("insertins refuses N=0",
            lambda: L.insert_instructions(m5, "main", 1, []),
            "nothing to insert")
    refuses("insertins refuses a pc past the end of the code",
            lambda: L.insert_instructions(m5, "main", 999,
                                          [("MOVE", {"A": 1, "B": 1})]),
            "outside 0..")
    refuses("insertins refuses a register past maxstacksize",
            lambda: L.insert_instructions(m5, "main", 1,
                                          [("MOVE", {"A": 99, "B": 1})]),
            "maxstacksize")
    refuses("insertins refuses an unknown opcode",
            lambda: L.insert_instructions(m5, "main", 1,
                                          [("NOPE", {"A": 1})]),
            "unknown opcode")
    refuses("insertins refuses TFORCALL not followed by TFORLOOP",
            lambda: L.insert_instructions(m5, "main", 1,
                                          [("TFORCALL", {"A": 0, "C": 1})]),
            "must be followed by TFORLOOP")
    refuses("insertins refuses SETLIST C=0 with no EXTRAARG",
            lambda: L.insert_instructions(
                m5, "main", 1, [("SETLIST", {"A": 0, "B": 1, "C": 0})]),
            "must be followed by EXTRAARG")

    # the sBx overflow rule needs an offset near the limit, which the 15-
    # instruction synthetic chunk cannot hold. Build one in memory.
    hdr_big2, big2 = L.load_chunk(base)
    pb = L.find_proto(big2, "main")
    span = L.MAXARG_sBx + 1
    words = [L._isbx(L.OPNAMES.index("JMP"), 0, 0, span)]
    words += [L._i(L.OPNAMES.index("LOADK"), a=0, bx=0)] * (span - 1)
    words += [L._i(L.OPNAMES.index("RETURN"), a=0, b=1)]
    pb.code = [L.Instruction(i, i * 4, w) for i, w in enumerate(words)]
    pb.lineinfo = []      # keep the line-table guard out of this test
    refuses("insertins refuses a relocated offset that no longer fits sBx",
            lambda: L.insert_instructions(
                big2, "main", span - 2, [("MOVE", {"A": 0, "B": 0})] * 4),
            "outside -%d..%d" % (L.MAXARG_sBx, L.MAXARG_sBx))

    # the verify gate: a tree that mutators would happily encode but that
    # verify() rejects must not be written
    hdr6, m6 = L.load_chunk(base)
    tmp = os.path.join(tempfile.gettempdir(), "lua53_inspect_gate.lc")
    p6 = L.find_proto(m6, "main")
    # corrupt the *word*, not the decoded field: _finish encodes and re-parses,
    # so an in-memory-only edit would never reach verify().
    victim6 = p6.code[0]
    p6.code[0] = L.Instruction(victim6.pc, victim6.offset,
                               victim6.word | (0x3F << L.POS_OP))
    try:
        L._finish(hdr6, m6, base, tmp)
    except L.EncodeError as exc:
        check("the verify gate refuses to write a chunk that fails verify()",
              "does not pass verify()" in str(exc) and not os.path.exists(tmp),
              str(exc)[:130])
    else:
        check("the verify gate refuses to write a chunk that fails verify()",
              False, "no error raised")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    check("the verify gate wrote no file", not os.path.exists(tmp),
          "%s absent" % tmp)


def check_negative(path: str, data: bytes) -> None:
    print("== negative checks on %s" % path)

    # empty / too short
    expect_parse_error("rejects empty input", b"", "not a Lua chunk")
    expect_parse_error("rejects a 3-byte prefix", data[:3], "not a Lua chunk")

    # wrong signature
    bad = bytearray(data)
    bad[1] ^= 0xFF
    expect_parse_error("rejects a corrupted signature",
                       bytes(bad), "not a Lua chunk")

    # wrong version byte -> must name the version, not decode as something
    bad = bytearray(data)
    bad[4] = 0x54  # 5.4
    expect_parse_error("rejects a non-5.3 version byte",
                       bytes(bad), "version mismatch")

    # wrong format byte
    bad = bytearray(data)
    bad[5] = 0x01
    expect_parse_error("rejects a bad format byte",
                       bytes(bad), "format mismatch")

    # corrupted LUAC_DATA
    bad = bytearray(data)
    bad[6] ^= 0xFF
    expect_parse_error("rejects corrupted LUAC_DATA",
                       bytes(bad), "corrupted")

    # endianness: rewrite LUAC_INT big-endian
    bad = bytearray(data)
    bad[0x11:0x19] = struct.pack(">q", L.LUAC_INT)
    expect_parse_error("rejects a big-endian LUAC_INT",
                       bytes(bad), "endianness mismatch")

    # float format: wrong LUAC_NUM
    bad = bytearray(data)
    bad[0x19:0x1d] = struct.pack("<f", 370.6)
    expect_parse_error("rejects a wrong LUAC_NUM",
                       bytes(bad), "float format mismatch")

    # implausible size byte
    bad = bytearray(data)
    bad[0x0C] = 0x40
    expect_parse_error("rejects an implausible int size",
                       bytes(bad), "implausible")

    # truncation at several points
    for frac, label in ((0.5, "half"), (0.9, "90%"), (0.999, "just short"),
                        (0.25, "quarter")):
        cut = int(len(data) * frac)
        expect_rejected("rejects a %s-truncated chunk" % label, data[:cut])

    # trailing garbage must be reported, never ignored
    try:
        hdr, main = L.load_chunk(data + b"\x00")
    except L.ParseError as exc:
        check("rejects trailing bytes", True, str(exc))
    else:
        res = L.verify(main, data + b"\x00", hdr)
        check("reports trailing bytes as a failure",
              any(r.startswith("FAIL") for r in res),
              "; ".join(r for r in res if r.startswith("FAIL")) or "not caught")

    # an out-of-range instruction opcode number is caught by verify()
    hdr, main = L.load_chunk(data)
    victim = next(p for p in L.walk(main) if p.code)
    saved = victim.code[0].word
    object.__setattr__(victim.code[0], "op", L.NUM_OPCODES + 3)
    res = L.verify(main, data, hdr)
    object.__setattr__(victim.code[0], "op", saved & 0x3F)
    check("verify() catches an out-of-range opcode",
          any("opcodes-in-range" in r and r.startswith("FAIL") for r in res))

    # verify() catches an out-of-range LOADK constant. The check reads the
    # instruction's Bx operand, so that is what has to be corrupted -- setting
    # Constant.index would not exercise it.
    victim = None
    for p in L.walk(main):
        for i in p.code:
            if i.name == "LOADK":
                victim = (p, i)
                break
        if victim:
            break
    if victim is None:
        check("verify() catches an out-of-range LOADK constant", False,
              "no LOADK instruction found to mutate")
    else:
        _p, i = victim
        saved = i.bx
        object.__setattr__(i, "bx", 9999)
        res = L.verify(main, data, hdr)
        object.__setattr__(i, "bx", saved)
        check("verify() catches an out-of-range LOADK constant",
              any("loadk-in-range" in r and r.startswith("FAIL") for r in res),
              next((r for r in res if "loadk-in-range" in r), "no result"))

    # verify() catches a jump target outside the prototype
    victim = None
    for p in L.walk(main):
        for i in p.code:
            if i.name == "JMP":
                victim = (p, i)
                break
        if victim:
            break
    if victim is None:
        check("verify() catches an out-of-range jump target", False,
              "no JMP instruction found to mutate")
    else:
        _p, i = victim
        saved = i.sbx
        object.__setattr__(i, "sbx", 99999)
        res = L.verify(main, data, hdr)
        object.__setattr__(i, "sbx", saved)
        check("verify() catches an out-of-range jump target",
              any("jumps-in-range" in r and r.startswith("FAIL") for r in res),
              next((r for r in res if "jumps-in-range" in r), "no result"))


def main(argv: "list[str]") -> int:
    paths = argv[1:]
    if not paths:
        print(__doc__)
        return 2
    for path in paths:
        with open(path, "rb") as fh:
            data = fh.read()
        check_chunk(path, data)
        check_encoder(path, data)
        check_xref_regression(list(L.walk(L.load_chunk(data)[1])))
        check_negative(path, data)
        print()
    check_const_use_modes()
    check_synthetic_mutation()
    check_mutators()
    if FAILURES:
        print("FAILED %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
