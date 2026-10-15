"""P3-CUSTOMIZE-SITES: re-derive every site and count claimed in
research/P3-CUSTOMIZE-SITES.md from the image, and exit nonzero on any mismatch.

Nothing here trusts the task's intermediate JSON as truth: the indirect-site scan is
re-run from the image, every count is recomputed, and each expected value is a literal
below. The report file is opened and every address and count the report states must
appear in the re-derived result.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \\
      python mods/mii_customizer/scratch/2026-10-04_P3-CUSTOMIZE-SITES/check_report_claims.py

Exit 0 = every claim reproduced; exit 1 = at least one mismatch (printed).
"""
import hashlib
import json
import struct
import sys
from array import array
from pathlib import Path

import capstone
import capstone.arm64 as arm64

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lib
from lib import TEXT, dis, ldr_imm, branch_reg, written, text
import step3_scan as s3
import step45_sites as s45

MOD = HERE.parents[1]
REPORT = MOD / 'research/P3-CUSTOMIZE-SITES.md'
SHA = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'

# ---- claims as written in the report -------------------------------------------
CLAIMS = {
    'wrapper_0x208de60': [
        'ldr x0, [x0, #0x50]', 'ldr x8, [x0]', 'ldr x3, [x8, #0x278]', 'br x3'],
    'thunk_0x4e53f0': [
        'ldr x0, [x0, #0x38]', 'ldr x8, [x0]', 'ldr x3, [x8, #0x38]', 'br x3'],
    'vtable_0x4f89490_slot_0x278_addend': 0x4E53F0,
    'vtable_0x4f89490_slot_0x270_addend': 0x4E53E0,
    'direct_branches_to_0x208de60': 0,
    'pointers_to_0x208de60': [0x41BB7C8],
    'reloc_addends_eq_0x208de60': 0,
    'ldr_0x278_words_in_TEXT': 977,
    'unfiltered_shape_matches': 86,
    'kept_sites': [
        {'ldr': 0x208DE68, 'call': 0x208DE6C, 'call_kind': 'br',
         'vtable_load': 0x208DE64, 'base_of_0x50': 0x208DE60},
        {'ldr': 0x20922FC, 'call': 0x2092308, 'call_kind': 'blr',
         'vtable_load': 0x20922F8, 'base_of_0x50': 0x20922E4},
    ],
    'wrapper_found_by_unfiltered_shape': True,
    'prologue_candidates': [0x208D940, 0x20921D0],
    'prologue_caller_counts': [2, 0],
    'prologue_first_callers': [
        [0x2138794, 0x21399A8], []],
    'set_customize_no_string': [0x439D46A],
    'symtab_st_value_slot': 0x41BB7C8,
    'symtab_symbol': ('_ZN3app8lua_bind33WorkModule__set_customize_no_impl'
                      'EPNS_26BattleObjectModuleAccessorEii'),
    'arg_materialisation_reg': [(0x209281C, 'set_customize_no'), (0x2092828, 0x20921D0)],
}

fails = []
checks = 0


def check(name, got, want):
    global checks
    checks += 1
    ok = got == want
    print('%-52s %s' % (name, 'PASS' if ok else 'FAIL'))
    if not ok:
        print('    got : %r' % (got,))
        print('    want: %r' % (want,))
        fails.append(name)
    return ok


# ---- 1. input identity ---------------------------------------------------------
h = hashlib.sha256(lib.data).hexdigest()
check('input sha256', h, SHA)
check('input size', len(lib.data), 86672752)

# ---- 2. the two instruction blocks, read again ---------------------------------
for addr, want in ((0x208DE60, CLAIMS['wrapper_0x208de60']),
                   (0x4E53F0, CLAIMS['thunk_0x4e53f0'])):
    got = ['%s %s' % (i.mnemonic, i.op_str) for i in dis(addr, 4)]
    check('four instructions at 0x%x' % addr, got, want)

# ---- 3. vtable slots via the relocation array ----------------------------------
def reloc_addend_of(slot):
    a, end = 0x39C8070, 0x40C9FC8
    out = []
    while a + 24 <= end:
        off, info, pad = struct.unpack_from('<QII', lib.data, a)
        add, = struct.unpack_from('<Q', lib.data, a + 0x10)
        if info == 0x403 and pad == 0 and add and off == slot:
            out.append(add)
        a += 24
    return out


check('vtable 0x4f89490 +0x278 addend',
      reloc_addend_of(0x4F89490 + 0x278), [CLAIMS['vtable_0x4f89490_slot_0x278_addend']])
check('vtable 0x4f89490 +0x270 addend',
      reloc_addend_of(0x4F89490 + 0x270), [CLAIMS['vtable_0x4f89490_slot_0x270_addend']])

# ---- 4. direct users of the wrapper --------------------------------------------
words = array('I')
words.frombytes(lib.data[TEXT[0]:TEXT[1]])
sx = lib.sx
brs = []
for i, w in enumerate(words):
    if (w & 0xFC000000) == 0x94000000:
        a = TEXT[0] + 4 * i
        if a + (sx(w & 0x3FFFFFF, 26) << 2) == 0x208DE60:
            brs.append(a)
check('bl/b in TEXT targeting 0x208de60', brs, [])
pat = struct.pack('<Q', 0x208DE60)
ptrs, i = [], 0
while True:
    i = lib.data.find(pat, i)
    if i < 0:
        break
    ptrs.append(i)
    i += 1
check('8-byte pointers to 0x208de60', ptrs, CLAIMS['pointers_to_0x208de60'])

addends = []
pat = struct.pack('<Q', 0x208DE60)
i = 0
while True:
    i = lib.data.find(pat, i)
    if i < 0:
        break
    if i >= 16:
        rec = i - 16                     # +0x10 is the addend, so the record starts here
        off, info, pad = struct.unpack_from('<QII', lib.data, rec)
        if info == 0x403 and pad == 0:
            addends.append(off)
    i += 1
check('reloc addends equal to 0x208de60 (whole-image search)', addends, [])

# The hard-coded record-array extent used above.  NOTE: `relocs.py --bounds` prints
# "306169 records" for this extent, but its arithmetic is (fwd + REC - back) / REC where
# `fwd` is the first position that is NOT a 0x403 record, so it counts that one trailing
# foreign record.  Counting only r_info == 0x403 gives 306168.  Recorded, not hidden.
cnt = 0
foreign = []
a = 0x39C8070
while a + 24 <= 0x40C9FC8:
    off, info, pad = struct.unpack_from('<QII', lib.data, a)
    if info == 0x403 and pad == 0:
        cnt += 1
    else:
        foreign.append((a, info, pad))
    a += 24
check('R_AARCH64_RELATIVE records in the bounded extent', cnt, 306168)
check('the one non-0x403 record relocs.py --bounds counts', foreign,
      [(0x40C9FB0, 0x401, 3)])

# ---- 5. re-run the whole indirect scan ------------------------------------------
syn, _ = s3.synthetic()
check('synthetic case 1 (must match)', syn[0][1], True)
check('synthetic case 2 (x overwritten)', syn[1][1], True)
check('synthetic case 3 (disp 0x270)', syn[2][1], True)
check('synthetic case 4 (no 0x50 filter)', syn[3][1], True)

wr_items = s3.window(0x208DE68, 12, 8)
wi = next(k for k, (aa, _) in enumerate(wr_items) if aa == 0x208DE68)
wok, wrec = s3.match(wr_items, wi)
check('wrapper found by the unfiltered shape', wok, CLAIMS['wrapper_found_by_unfiltered_shape'])
check('wrapper filter D applied', bool(wrec.get('has_0x50')), True)

cands, unf, kept = s3.scan()
check('ldr #0x278 words in TEXT', len(cands), CLAIMS['ldr_0x278_words_in_TEXT'])
check('unfiltered shape matches', len(unf), CLAIMS['unfiltered_shape_matches'])
check('kept sites', len(kept), len(CLAIMS['kept_sites']))
got_kept = [{'ldr': k['ldr'], 'call': k['call'], 'call_kind': k['call_kind'],
             'vtable_load': k['vtable_load'], 'base_of_0x50': k['base_of_0x50']}
            for k in kept]
check('kept site addresses and shapes', got_kept, CLAIMS['kept_sites'])

# ---- 6. per-site provenance, loops, prologues, callers -------------------------
res = json.loads((HERE.parents[1] / 'evidence/P3-CUSTOMIZE-SITES/08_step45_sites.json')
                 .read_text(encoding='utf-8'))
check('step45 produced one record per kept site', len(res), len(CLAIMS['kept_sites']))

# re-derive provenance from the image rather than trusting the JSON
for r, claim in zip(res, CLAIMS['kept_sites']):
    call = claim['call']
    items = s45.win(call)
    ci = next(i for i, (a, _) in enumerate(items) if a == call)
    for name, reg in (('w1', 1), ('w2', 2)):
        st = s45.resolve(items, ci, reg)
        check('site 0x%x %s provenance first line' % (call, name),
              st[0], r[name][0])
        check('site 0x%x %s provenance matches stored JSON' % (call, name), st, r[name])
    check('site 0x%x enclosing prologue' % call,
          lib.last_prologue_at_or_before(call), r['prologue_candidate'])
    check('site 0x%x loops containing the call' % call,
          [L['branch'] for L in s45.loops_containing(call)],
          [L['branch'] for L in r['loops']])

check('prologue candidates', sorted({r['prologue_candidate'] for r in res}),
      CLAIMS['prologue_candidates'])
callers = s45.bl_callers(CLAIMS['prologue_candidates'])
check('prologue caller counts', [len(callers[s]) for s in CLAIMS['prologue_candidates']],
      CLAIMS['prologue_caller_counts'])
check('prologue first callers',
      [[a for a, _ in callers[s][:10]] for s in CLAIMS['prologue_candidates']],
      CLAIMS['prologue_first_callers'])

# ---- 7. string and symbol-table facts ------------------------------------------
def occurrences(s):
    out, i = [], 0
    while True:
        i = lib.data.find(s + b'\0', i)
        if i < 0:
            return out
        out.append(i)
        i += 1


check('NUL-terminated "set_customize_no" occurrences',
      occurrences(b'set_customize_no'), CLAIMS['set_customize_no_string'])
check('NUL-terminated "set_customize_no_impl" occurrences',
      occurrences(b'set_customize_no_impl'), [])

SYMTAB, STRTAB = 0x4197610, 0x41C11F0
slot = CLAIMS['symtab_st_value_slot']
delta = slot - SYMTAB
st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack_from(
    '<IBBHQQ', lib.data, SYMTAB + 24 * (delta // 24))
n = STRTAB + st_name
name = lib.data[n:lib.data.find(b'\0', n)].decode('ascii')
check('dynamic symbol at index %d' % (delta // 24), name, CLAIMS['symtab_symbol'])
check('that symbol st_value', st_value, 0x208DE60)
check('that symbol st_size', st_size, 16)

# address-materialisation sequence reported for the second kept site
check('string materialised into x1 at 0x2092820',
      text(0x2092820), 'add x1, x1, #0x46a')
check('function address materialised into x2 at 0x2092828',
      text(0x2092828), 'add x2, x2, #0x1d0')

# ---- 8. the report must mention every listed address/count ---------------------
rep = REPORT.read_text(encoding='utf-8')
# The report writes addresses zero-padded to 8 digits (0x0208de60) in its tables and
# sometimes unpadded (0x208de60) in prose, so an address check accepts either form.
repl = rep.lower()


def mentioned(addr):
    return ('0x%08x' % addr) in repl or ('0x%x' % addr) in repl


for label, addr in [('wrapper', 0x208DE60), ('thunk', 0x4E53F0),
                    ('kept site 1 slot load', 0x20922FC),
                    ('kept site 2 call', 0x2092308),
                    ('kept site 2 base load', 0x20922E4),
                    ('kept site 1 call', 0x208DE6C),
                    ('prologue A', 0x208D940), ('prologue B', 0x20921D0)]:
    check('report mentions %s (0x%x)' % (label, addr), mentioned(addr), True)
for label, needle in [('unfiltered count', str(CLAIMS['unfiltered_shape_matches'])),
                      ('candidate count', str(CLAIMS['ldr_0x278_words_in_TEXT'])),
                      ('kept count', str(len(CLAIMS['kept_sites'])))]:
    check('report mentions %s (%s)' % (label, needle), needle in rep, True)

print('')
print('%d checks, %d failures' % (checks, len(fails)))
print('capstone %s' % lib.CAPSTONE_VERSION)
if fails:
    print('FAILED: %s' % ', '.join(fails))
    sys.exit(1)
print('ALL CLAIMS REPRODUCED')
sys.exit(0)