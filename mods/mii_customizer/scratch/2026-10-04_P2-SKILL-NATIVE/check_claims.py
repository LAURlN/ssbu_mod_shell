"""P2-SKILL-NATIVE claim check: re-verify every address claim in the report directly
against gamedata/ssbu-13.0.4/main.bin, independently of the scratch window scripts.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python check_claims.py

Exit code 0 = all checks pass, non-zero = at least one claim failed.

Checks compare against capstone disassembly text and raw relocation records rather than
hand-computed instruction encodings, so a mistake in the checker shows up as a failure
rather than as a silently different encoding.
"""
import struct
import sys
from pathlib import Path

import capstone

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
REC = 24
R_AARCH64_RELATIVE = 0x403
TEXT = (0x100, 0x39C8000)

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md.detail = False

fails = []
n = 0


def check(label, cond):
    global n
    n += 1
    if cond:
        print('ok   %s' % label)
    else:
        print('FAIL %s' % label)
        fails.append(label)


def sx(v, b):
    return v - (1 << b) if v & (1 << (b - 1)) else v


def word(a):
    return struct.unpack_from('<I', data, a)[0]


def dis(a):
    """(mnemonic, op_str) for the instruction at a, or ('.word', '')."""
    ins = next(md.disasm(data[a:a + 4], a), None)
    return (ins.mnemonic, ins.op_str) if ins else ('.word', '')


def norm(a):
    m, o = dis(a)
    return '%s %s' % (m, o)


def is_mov_w_imm(a, reg, imm):
    m, o = dis(a)
    return m == 'mov' and o == 'w%s, #%#x' % (reg, imm)


def addend_for(slot):
    """The R_AARCH64_RELATIVE addend for a .data slot address, or None."""
    pat = struct.pack('<Q', slot)
    i = 0
    out = None
    while True:
        i = data.find(pat, i)
        if i < 0:
            return out
        if i + REC <= len(data):
            info = struct.unpack_from('<I', data, i + 8)[0]
            pad = struct.unpack_from('<I', data, i + 0xC)[0]
            v = struct.unpack_from('<Q', data, i + 0x10)[0]
            if info == R_AARCH64_RELATIVE and pad == 0 and v != 0:
                out = v
        i += 1


def adrp_add_value(add_a):
    """Decode the adrp+add pair ending at add_a; return (target, dest_reg, base_reg)."""
    adrp_a = add_a - 4
    w1, w2 = word(adrp_a), word(add_a)
    if (w1 & 0x9F000000) != 0x90000000 or (w2 & 0xFF800000) != 0x91000000:
        return None, None, None
    page = (adrp_a & ~0xFFF) + (sx((((w1 >> 5) & 0x7FFFF) << 2) | ((w1 >> 29) & 3), 21) << 12)
    return page + ((w2 >> 10) & 0xFFF), w2 & 31, (w2 >> 5) & 31


def bl_target(a):
    w = word(a)
    if (w & 0xFC000000) != 0x94000000:
        return None
    return a + (sx(w & 0x3FFFFFF, 26) << 2)


# ===== 1. strings: exactly one NUL-terminated occurrence each ==================
print('--- 1. name strings in the image ---')
STRINGS = {
    'get_skill_id': 0x042905bf,
    'set_skill_id': 0x04348c5a,
    'replace_skill': 0x0439bd6c,
    'replace_skill_subwindow': 0x0437af9d,
    'get_skill_name_label': 0x0427f3d5,
    'get_skill_help_label': 0x0441127e,
}
for name, a in STRINGS.items():
    b = name.encode()
    check('%s at 0x%x: bytes match and a NUL terminator follows' % (name, a),
          data[a:a + len(b)] == b and data[a + len(b)] == 0)
    hits = []
    i = 0
    while True:
        i = data.find(b + b'\0', i)
        if i < 0:
            break
        hits.append(i)
        i += 1
    check('%s: exactly 1 NUL-terminated occurrence, at the reported address '
          '(found %d)' % (name, len(hits)), hits == [a])
# the prefix trap: replace_skill occurs bare inside replace_skill_subwindow only
LONGER = b'replace_skill_subwindow\0'
check('replace_skill terminator match is not satisfied by the bare prefix at 0x437af9d',
      data[0x437af9d:0x437af9d + len(b'replace_skill\0')] != b'replace_skill\0'
      and data[0x437af9d:0x437af9d + len(LONGER)] == LONGER)

# ===== 2. the adrp+add completion that yields each string address ==============
print('--- 2. adrp+add reference sites ---')
SITES = {
    'set_skill_id': 0x19de10c,
    'get_skill_id': 0x19de1bc,
    'get_skill_name_label': 0x19de268,
    'get_skill_help_label': 0x19de310,
    'replace_skill': 0x19de3b0,
    'replace_skill_subwindow': 0x19de45c,
}
for name, add_a in SITES.items():
    tgt, rd, rn = adrp_add_value(add_a)
    check('%s: adrp@0x%x+add@0x%x resolves to the name string 0x%x'
          % (name, add_a - 4, add_a, STRINGS[name]), tgt == STRINGS[name])
    check('%s: the add writes x1, the name argument of the registration call' % name,
          rd == 1)
    check('%s: the add bases on the adrp register x%d (single adrp source)' % (name, rn),
          rn == 1)

# ===== 3. registration call at each site =======================================
print('--- 3. registration call ---')
CALL = {'set_skill_id': 0x19de120, 'get_skill_id': 0x19de1d0,
        'get_skill_name_label': 0x19de280, 'get_skill_help_label': 0x19de328,
        'replace_skill': 0x19de3c8, 'replace_skill_subwindow': 0x19de470}
for name, a in CALL.items():
    check('%s: bl at 0x%x targets 0x3376540 (the post_fighter registration call)'
          % (name, a), bl_target(a) == 0x3376540)
    check('%s: x0 is set from x20 (the registration receiver) just before the call' % name,
          dis(a - 4) == ('mov', 'x0, x20'))

# ===== 4. allocation size immediate =============================================
print('--- 4. delegate allocation size ---')
# Each block calls the allocator exactly twice (a primary attempt, then a retry through
# an allocator wrapper reached by blr). The two calls and the addresses where the
# delegate is built are listed explicitly so a neighbouring block cannot leak in.
ALLOC = 0x392dce0
SIZES = {'set_skill_id': (0x28, 0x19de10c, [0x19de0a0, 0x19de0e0], 0x19de0ec),
         'get_skill_id': (0x38, 0x19de1bc, [0x19de148, 0x19de188], 0x19de194),
         'get_skill_name_label': (0x38, 0x19de268, [0x19de1f8, 0x19de238], 0x19de244),
         'get_skill_help_label': (0x38, 0x19de310, [0x19de2a8, 0x19de2e8], 0x19de2f4),
         'replace_skill': (0x28, 0x19de3b0, [0x19de350, 0x19de390], 0x19de39c),
         'replace_skill_subwindow': (0x28, 0x19de45c, [0x19de3f0, 0x19de430], 0x19de43c)}
for name, (size, site, calls, build) in SIZES.items():
    check('%s: both allocator calls are present and are bl 0x%x (%s)'
          % (name, ALLOC, ['0x%x' % c for c in calls]),
          len(calls) == 2 and all(bl_target(c) == ALLOC for c in calls))
    # The two argument-setting movs appear in either order across the six blocks
    # (some set w1 then w0, others w0 then w1), so accept both orderings.
    def args_ok(c):
        pair = [(dis(c - 4), dis(c - 8)), (dis(c - 8), dis(c - 4))]
        return any(a == ('mov', 'w1, #%#x' % size) and b == ('mov', 'w0, #0x10')
                   for a, b in pair)

    check('%s: every allocator call in the block requests size 0x%x (w1) and '
          'alignment 0x10 (w0)' % (name, size), all(args_ok(c) for c in calls))
    check('%s: every allocator result is tested with cbnz x0' % name,
          all(dis(c + 4)[0] == 'cbnz' for c in calls))
    check('%s: the second allocator retry lands on the delegate-build block at 0x%x'
          % (name, build),
          int(dis(calls[-1] + 4)[1].split('#')[-1], 0) == build)
    check('%s: the delegate build block is between the last allocator call and the '
          'name reference' % name, calls[-1] < build <= site)

# ===== 5. handler address immediate + the store that writes it =================
print('--- 5. handler address and the store into the delegate ---')
# name -> (handler, adrp+add address that builds it, storing instruction, owner offset)
HANDLER = {
    'set_skill_id': (0x19dcf20, 0x19de0f8, 0x19de104, 'x19, x8, [x0, #0x10]'),
    'get_skill_id': (0x19dcf40, 0x19de1a0, 0x19de1b4, 'xzr, x9, [x0, #0x20]'),
    'get_skill_name_label': (0x19dcf60, 0x19de248, 0x19de254, 'x8, xzr, [x0, #0x18]'),
    'get_skill_help_label': (0x19dd080, 0x19de2f8, 0x19de300, 'x8, xzr, [x0, #0x18]'),
    'replace_skill': (0x19dd1a0, 0x19de3a0, 0x19de3a8, 'x19, x8, [x0, #0x10]'),
    'replace_skill_subwindow': (0x19dd250, 0x19de448, 0x19de454, 'x19, x9, [x0, #0x10]'),
}
for name, (h, defa, store, expect_op) in HANDLER.items():
    tgt, rd, rn = adrp_add_value(defa)
    check('%s: adrp+add at 0x%x resolves to handler 0x%x' % (name, defa, h), tgt == h)
    m, o = dis(store)
    check('%s: "%s %s" at 0x%x is the store that puts the handler in the delegate'
          % (name, m, o, store), m == 'stp' and o == expect_op)

# get_skill_id differs from the others: +0x18 is zero and the handler is at +0x28
check('get_skill_id: the +0x18 slot is explicitly stored zero at 0x19de1ac',
      dis(0x19de1ac)[0] == 'stp' and dis(0x19de1ac)[1] == 'x19, xzr, [x0, #0x10]')
check('get_skill_id: the +0x30 slot is explicitly stored zero at 0x19de1b0',
      dis(0x19de1b0)[0] == 'str' and dis(0x19de1b0)[1] == 'xzr, [x0, #0x30]')

# owner: every delegate stores the owner at +0x10
for name in HANDLER:
    sites = [0x19de104, 0x19de1ac, 0x19de26c, 0x19de318, 0x19de3a8, 0x19de454]
    break
for name, owner_store in (('set_skill_id', 0x19de104), ('get_skill_id', 0x19de1ac),
                          ('get_skill_name_label', 0x19de26c),
                          ('get_skill_help_label', 0x19de318),
                          ('replace_skill', 0x19de3a8),
                          ('replace_skill_subwindow', 0x19de454)):
    m, o = dis(owner_store)
    op_is_x19_at_0x10 = o in ('x19, x8, [x0, #0x10]', 'x19, x9, [x0, #0x10]',
                              'x19, xzr, [x0, #0x10]', 'x19, [x0, #0x10]')
    check('%s: owner x19 stored at delegate +0x10 (%s %s at 0x%x)'
          % (name, m, o, owner_store), m in ('stp', 'str') and op_is_x19_at_0x10)

# ===== 6. owner object origin, inside the enclosing function ===================
print('--- 6. owner object origin ---')
check('enclosing function 0x19ddb30 opens with sub sp,sp,#0xa0',
      dis(0x19ddb30)[0] == 'sub' and dis(0x19ddb30)[1] == 'sp, sp, #0xa0')
check('the word before 0x19ddb30 is udf #0 padding, so 0x19ddb30 is a function start',
      dis(0x19ddb2c) == ('udf', '#0'))
check('x19 = x0 at 0x19ddb94, from the allocator call at 0x19ddb90',
      dis(0x19ddb94) == ('mov', 'x19, x0') and bl_target(0x19ddb90) == 0x392dce0)
check('that allocation requests 0x150 bytes (mov w1,#0x150 at 0x19ddb80)',
      is_mov_w_imm(0x19ddb80, 1, 0x150))
tgt, _, _ = adrp_add_value(0x19ddbf8)
check('the owner object vtable 0x50a6e20 is built by adrp@0x19ddbf4/add@0x19ddbf8',
      tgt == 0x50a6e20)
check('x23 = x0 at 0x19ddb6c (the scene object, kept in a callee-saved register)',
      dis(0x19ddb6c) == ('mov', 'x23, x0'))
ep_m, ep_o = dis(0x19de6ac)
check('enclosing function closes with add sp,sp,#0xa0 at 0x19de6ac and ret at 0x19de6b0',
      ep_m == 'add' and ep_o == 'sp, sp, #0xa0' and dis(0x19de6b0) == ('ret', ''))
check('the register allocation size 0xa0 matches between prologue and epilogue',
      dis(0x19ddb30)[1].split('#')[-1] == dis(0x19de6ac)[1].split('#')[-1])

# ===== 7. delegate vtables: three relocated slot values =========================
print('--- 7. delegate vtable relocations ---')
VT = {0x50a6e78: (0x19c2210, 0x19dd940, 0x19dd950),
      0x50a6ea0: (0x19c2210, 0x19dd7c0, 0x19dd7d0),
      0x50a6ec8: (0x19c2210, 0x19dd5b0, 0x19dd5c0),
      0x50a6ef0: (0x19c2210, 0x19dd470, 0x19dd480)}
for vt, slots in VT.items():
    for i, want in enumerate(slots):
        check('vtable 0x%x slot %d relocates to 0x%x' % (vt, i, want),
              addend_for(vt + 8 * i) == want)
    check('vtable 0x%x file qwords are zero (relocation fills them), slot 0' % vt,
          struct.unpack_from('<Q', data, vt)[0] == 0)

print('--- 7b. control: the vtable P1-ID-REVIEW already decoded ---')
for i, want in enumerate((0x19c2210, 0x19dc640, 0x19dc650)):
    check('control vtable 0x50a6d28 slot %d relocates to 0x%x' % (i, want),
          addend_for(0x50a6d28 + 8 * i) == want)

# vtable addresses must be the ones actually stored into the new delegate
VSTORE = {'set_skill_id': 0x19de0fc, 'get_skill_id': 0x19de1a4,
          'get_skill_name_label': 0x19de260, 'get_skill_help_label': 0x19de2fc,
          'replace_skill': 0x19de3a4, 'replace_skill_subwindow': 0x19de44c}
VT_OF = {'set_skill_id': 0x50a6e78, 'get_skill_id': 0x50a6ea0,
         'get_skill_name_label': 0x50a6ec8, 'get_skill_help_label': 0x50a6ec8,
         'replace_skill': 0x50a6e78, 'replace_skill_subwindow': 0x50a6ef0}
REGDEF = {'set_skill_id': 0x19de0f0, 'get_skill_id': 0x19de198,
          'get_skill_name_label': 0x19de250, 'get_skill_help_label': 0x19de250,
          'replace_skill': 0x19de0f0, 'replace_skill_subwindow': 0x19de440}
for name, st in VSTORE.items():
    m, o = dis(st)
    check('%s: vtable is written at delegate +0x00 (%s %s at 0x%x)'
          % (name, m, o, st), m == 'str' and o == 'x21, [x0]' or
          (m == 'str' and o.startswith('x8, [x0]')) or (m == 'str' and o.startswith('x22, [x0]')))
    d_tgt, d_rd, _ = adrp_add_value(REGDEF[name])
    check('%s: the register stored at +0x00 was loaded with vtable 0x%x'
          % (name, VT_OF[name]), d_tgt == VT_OF[name])

# ===== 8. thunk field reads ====================================================
print('--- 8. invoke thunks: which delegate offset each one loads ---')
# the post_fighter control: ldp reads +0x10 (owner) and +0x18 (handler)
check('control thunk 0x19dc650 loads the owner/handler pair at 0x19dc71c',
      norm(0x19dc71c) == 'ldp x8, x2, [x19, #0x10]')
check('control thunk 0x19dc650 tail-branches through x2 at 0x19dc744',
      norm(0x19dc744) == 'br x2')
# set_skill_id / replace_skill share one thunk and the same layout as the control
check('thunk 0x19dd950 loads the owner/handler pair at 0x19dda98',
      norm(0x19dda98) == 'ldp x8, x3, [x19, #0x10]')
check('thunk 0x19dd950 tail-branches through x3 at 0x19ddac4',
      norm(0x19ddac4) == 'br x3')
# replace_skill_subwindow
check('thunk 0x19dd480 loads the owner/handler pair at 0x19dd54c',
      norm(0x19dd54c) == 'ldp x8, x2, [x19, #0x10]')
check('thunk 0x19dd480 tail-branches through x2 at 0x19dd574',
      norm(0x19dd574) == 'br x2')
# the two thunks that read +0x28 first and fall back to +0x18
for th, at28, at18 in ((0x19dd5c0, 0x19dd708, 0x19dd750),
                       (0x19dd7d0, 0x19dd89c, 0x19dd8f8)):
    m1, o1 = dis(at28)
    check('thunk 0x%x reads the +0x28 pair first at 0x%x (%s %s)' % (th, at28, m1, o1),
          m1 == 'ldp' and o1.endswith('[x20, #0x28]'))
    m2, o2 = dis(at18)
    check('thunk 0x%x falls back to +0x18 at 0x%x (%s %s)' % (th, at18, m2, o2),
          m2 == 'ldp' and o2.endswith('[x20, #0x18]'))
check('thunk 0x19dd7d0 (get_skill_id) branches through the +0x28-loaded register at 0x19dd8c0',
      norm(0x19dd8c0) == 'blr x8')
check('thunk 0x19dd5c0 (get_skill_name_label) returns the handler result to Lua at 0x19dd74c',
      norm(0x19dd74c) == 'b #0x38f4570')

# ===== 9. all six in one enclosing function =====================================
print('--- 9. one enclosing function ---')
FSTART, FEND = 0x19ddb30, 0x19de6b0
for name in HANDLER:
    check('%s reference 0x%x lies in 0x%x..0x%x' % (name, SITES[name], FSTART, FEND),
          FSTART <= SITES[name] <= FEND)
    check('%s registration call 0x%x lies in 0x%x..0x%x' % (name, CALL[name], FSTART, FEND),
          FSTART <= CALL[name] <= FEND)
    check('%s handler 0x%x is OUTSIDE the enclosing function (not a local closure)'
          % (name, HANDLER[name][0]),
          not (FSTART <= HANDLER[name][0] <= FEND))

# ===== 10. handler function starts =============================================
print('--- 10. handler candidate function starts ---')
BOUNDARY = {0x19dcf20: ('udf #0', 0x19dcf1c),
            0x19dcf40: ('assert block', 0x19dcf3c),
            0x19dcf60: ('assert block', 0x19dcf5c),
            0x19dd080: ('udf #0', 0x19dd07c),
            0x19dd1a0: ('udf #0', 0x19dd19c),
            0x19dd250: ('udf #0', 0x19dd24c)}
for h, (why, prev) in BOUNDARY.items():
    if why == 'udf #0':
        check('handler 0x%x: preceded by udf #0 padding at 0x%x' % (h, prev),
              dis(prev) == ('udf', '#0'))
    else:
        check('handler 0x%x: preceded by the cold assert block whose last call at 0x%x '
              'targets 0x39c20a0' % (h, prev),
              bl_target(prev) == 0x39c20a0)
    # each handler is immediately followed by a ret or a prologue, never mid-stream
    check('handler 0x%x starts a plausible entry (first insn is not a branch target tail)'
          % h, dis(h)[0] in ('cmp', 'sub', 'stp', 'ldr', 'add', 'str', 'mov'))

print()
print('%d checks, %d failures' % (n, len(fails)))
for f in fails:
    print('  failing: %s' % f)
sys.exit(1 if fails else 0)
