"""P11-INT-PARAMS check script (written by P12-INT-PARAMS).

Re-derives every fact this check asserts from the local inputs and exits
nonzero on any mismatch.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
    python mods/mii_customizer/evidence/P11-INT-PARAMS/check_p11_int_params.py [--neg [MODE]] [--selftest]

Inputs (read-only):
  gamedata/ssbu-13.0.4/main.bin                       (image, pinned sha256)
  gamedata/mii_customizer/P10-PRESET-WIDE/fighter_param_full.json   (pinned)
  gamedata/mii_customizer/P10-PRESET-WIDE/fighters.json
  gamedata/mii_customizer/P11-INT-PARAMS/{int_table,others_table}.json  (artifacts under test)
  gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin (pinned)
  gamedata/ssbu-13.0.4/dk_cargo/fighter/<kind>/motion/body/c00/motion_list.bin (9+2 kinds)

What it checks (each comparison is one numbered check):
  A image identity: sha256 + size, fighter_param_full.json sha256,
    Mii Gunner motion list sha256.
  B Q1: slots +0x240..+0x278 of vtable 0x4f89490 via RELA; the words of the
    thunks 0x4e5380..0x4e53fc; PC-relative flag over 0x4e53a0's first four
    words; every relocated pointer to 0x4e53a0 / 0x4e53e0 and their vtable
    runs; the count of `ldr xN,[xM,#0x250]` + `br` sites in .text.
  C Cited instruction words: every word quoted in research/P11-INT-PARAMS.md
    (the eight +0x250 sites: producer, hash composition, x2 writer, call,
    return use; and the 8.2 window), plus hash recomposition at each site.
  D Q2/Q4 site counts: an independent movz/movk scanner (the published
    P2/P4 rule: gap <= 4, no register overwrite, site = movz seed) plus an
    independent first-call / producer / displacement classifier (span 0x400,
    producer lookback 20, x2 lookback 8) is run over all 369 field hashes of
    fighter_param_full.json and compared field-by-field against
    int_table.json (25 i32 rows) and others_table.json (52 bool/hash rows):
    code_sites, class histogram, displacement histogram, via_0x250/0x270,
    per-site producer/call/x2 records, value statistics and `qualifies`.
    Totals (369 fields, 3169 sites) and P4's jump_count_max control
    (5 sites / 1 direct_bl / 1 indirect / 3 none / 1 via 0x250 at 0x622960 /
    0 via 0x270) are asserted. The scanner is re-implemented here and does
    NOT import the scratch scanners, so a shared bug cannot hide.
  E Q3: jump_count_max distribution over the 94 fighters and the nine
    fighters with value > 2; motion-list evidence (extra-jump kinds/anims in
    those nine plus mario and miigunner controls, and their absence from
    Mii Gunner).

Exit codes
  default run : 0 = every check passed, 1 = at least one mismatch,
                2 = an input is missing / an artifact is unreadable.
  --neg MODE  : runs the same suite with ONE expectation deliberately
                corrupted. The suite must FAIL: exit 1 = control detected
                (required), exit 0 = control NOT detected (this checker is
                broken), exit 2 = unknown mode.
                Modes: hash, slot, word, reloc, site, disp, mlist
                (seven controls, each must fail).
  --neg       : runs all seven controls in-process; exit 1 only if every
                control was detected (the printed line says CHECKER OK);
                exit 0 with a BROKEN line otherwise.
  --selftest  : one process: the clean suite (must find 0 failures) plus all
                seven controls (each must be detected); exits 0 only when both
                hold.

Runtime: ~1 minute (one whole-code-range scan in pure Python + capstone).
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

import capstone

HERE = Path(__file__).resolve()
ROOT = HERE.parents[4]
IMAGE = ROOT / "gamedata/ssbu-13.0.4/main.bin"
FULL = ROOT / "gamedata/mii_customizer/P10-PRESET-WIDE/fighter_param_full.json"
FIGHTERS_JSON = ROOT / "gamedata/mii_customizer/P10-PRESET-WIDE/fighters.json"
TABLE_DIR = ROOT / "gamedata/mii_customizer/P11-INT-PARAMS"
INT_TABLE = TABLE_DIR / "int_table.json"
OTHERS_TABLE = TABLE_DIR / "others_table.json"
GUNNER_MLIST = (ROOT / "gamedata/mii_customizer/P1-CATALOG/files/fighter/"
                "miigunner/motion/body/c00/motion_list.bin")
DK = ROOT / "gamedata/ssbu-13.0.4/dk_cargo/fighter"

TEXT = (0x100, 0x39C8000)
RELA0, RELA1 = 0x39C8070, 0x40C9FC8
REC = 24
R_REL = 0x403
SPAN = 0x400
BACK_PROD = 20
BACK_X2 = 8
MAX_GAP = 4

IMAGE_SHA = "f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613"
IMAGE_SIZE = 86672752
FULL_SHA = "9188c7680a86787feaee12f9537157dda64e89c37c87124af2c0bbd8196d70df"
GUNNER_MLIST_SHA = "2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba"

VTABLE = 0x4F89490
VT_OTHER = 0x4F73738

# ---------------------------------------------------------------- Q1 expectations
Q1_SLOTS = {
    0x240: 0x4E5380, 0x248: 0x4E5390, 0x250: 0x4E53A0, 0x258: 0x4E53B0,
    0x260: 0x4E53C0, 0x268: 0x4E53D0, 0x270: 0x4E53E0, 0x278: 0x4E53F0,
}
THUNK_WORDS = {
    0x4E5380: 0xD65F03C0,
    0x4E5390: 0xF9400008, 0x4E5394: 0xF9412903, 0x4E5398: 0xD61F0060,
    0x4E53A0: 0xF9401C00, 0x4E53A4: 0xF9400008, 0x4E53A8: 0xF9401103,
    0x4E53AC: 0xD61F0060,
    0x4E53B0: 0xF9400008, 0x4E53B4: 0xF9413103, 0x4E53B8: 0xD61F0060,
    0x4E53C0: 0xF9401C00, 0x4E53C4: 0xF9400008, 0x4E53C8: 0xF9401503,
    0x4E53CC: 0xD61F0060,
    0x4E53D0: 0xF9400008, 0x4E53D4: 0xF9413903, 0x4E53D8: 0xD61F0060,
    0x4E53E0: 0xF9401C00, 0x4E53E4: 0xF9400008, 0x4E53E8: 0xF9401903,
    0x4E53EC: 0xD61F0060,
    0x4E53F0: 0xF9401C00, 0x4E53F4: 0xF9400008, 0x4E53F8: 0xF9401D03,
    0x4E53FC: 0xD61F0060,
}
RELOC_PTRS_250 = {0x4F896E0: 0x4E53A0, 0x4F73988: 0x4E53A0}
RELOC_PTRS_270 = {0x4F89700: 0x4E53E0, 0x4F739A8: 0x4E53E0}
LDR250_BR_COUNT = 24

# ------------------------------------------- cited words (research report tables)
CITED_WORDS = {
    # thunk block (Q1 disassembly quotes), incl. the entry-evidence word
    0x4E5380: 0xD65F03C0, 0x4E5390: 0xF9400008, 0x4E5394: 0xF9412903,
    0x4E5398: 0xD61F0060, 0x4E539C: 0x00000000,
    0x4E53A0: 0xF9401C00, 0x4E53A4: 0xF9400008, 0x4E53A8: 0xF9401103, 0x4E53AC: 0xD61F0060, 0x4E53E0: 0xF9401C00,
    0x4E53E4: 0xF9400008, 0x4E53E8: 0xF9401903, 0x4E53EC: 0xD61F0060,
    # example 8.2 window (P4 + this report)
    0x622958: 0xF94002E8, 0x62295C: 0xF9412908, 0x622960: 0xD287B041,
    0x622964: 0xF2A6B941, 0x622968: 0xF2C001C1, 0x62296C: 0xAA1703E0,
    0x622970: 0xAA1F03E2, 0x622974: 0xD63F0100, 0x622980: 0x2A0003E1,
    # final_start_turn_frame
    0x62E9FC: 0xD29317E1, 0x62EA00: 0xF2A7F561, 0x62EA04: 0xF2C002C1,
    0x62EA20: 0xF9412908, 0x62EA34: 0xF2C002E2, 0x62EA40: 0xD63F0100,
    0x62EA44: 0x2A0003F7,
    # attack_lw3_rebound_count
    0x6CA660: 0xF9412908, 0x6CA664: 0xD2832021, 0x6CA66C: 0xF2C00301,
    0x6CA674: 0xD63F0100, 0x6CA678: 0x6B00029F,
    # attack_100_rebound_count
    0x34E5678: 0xF9412908, 0x34E567C: 0xD2844D81, 0x34E5684: 0xF2C00301,
    0x34E568C: 0xD63F0100, 0x34E5690: 0x7100041F,
    # scroll_rate_change_frame
    0x62BFB0: 0xF9412908, 0x62BFB4: 0xD292F241, 0x62BFBC: 0xF2C00301,
    0x62BFCC: 0xD63F0100, 0x62BFF8: 0xB90037E0,
    # pickel_capture_fence_type site 1 / 2
    0xF07928: 0xF9412908, 0xF0792C: 0xD28DA141, 0xF07934: 0xF2C00321,
    0xF07940: 0xD63F0100, 0xF07954: 0x2A0003F9,
    0xF1561C: 0xF9412908, 0xF15620: 0xD28DA141, 0xF15628: 0xF2C00321,
    0xF15634: 0xD63F0100, 0xF15648: 0x2A0003F7,
    # unlabelled 0x19f190006a
    0x33F0848: 0xF9412908, 0x33F084C: 0xD2800D41, 0x33F0854: 0xF2C00321,
    0x33F0864: 0xD63F0100, 0x33F0870: 0x2A0003F7,
}

# site -> (hash, expected x2 text, expected x2 immediate value or None)
SITES_250 = {
    0x622960: (0x0E35CA3D82, "mov x2, xzr", 0),
    0x62E9FC: (0x163FAB98BF, "movk x2, #0x17, lsl #32", None),
    0x6CA664: (0x1800B91901, "mov x2, xzr", 0),
    0x34E567C: (0x189AEA226C, "mov x2, xzr", 0),
    0x62BFB4: (0x18CDE09792, "mov x2, xzr", 0),
    0xF0792C: (0x19327D6D0A, "mov x2, xzr", 0),
    0xF15620: (0x19327D6D0A, "mov x2, xzr", 0),
    0x33F084C: (0x19F190006A, "mov x2, xzr", 0),
}

# P4 section 6 / example 8.2 control
JUMP_CONTROL = {"sites": 5, "direct_bl": 1, "indirect": 1, "none": 3,
                "via250": 1, "via270": 0, "site250": 0x622960}

TOTAL_FIELDS = 369
TOTAL_SITES = 3169
I32_FIELDS = 25
OTHERS_FIELDS = 52
QUALIFYING = ["0x0e35ca3d82", "0x1800b91901", "0x189aea226c",
              "0x18cde09792", "0x19327d6d0a", "0x19f190006a"]

OVER2 = {"buddy": 3, "plizardon": 3, "ridley": 3, "pit": 4, "pitb": 4,
         "dedede": 5, "kirby": 6, "metaknight": 6, "purin": 6}
F3_SET = {"pit", "pitb", "dedede", "kirby", "metaknight", "purin"}
KINDS9 = ["jump_squat", "jump_f", "jump_b", "jump_aerial_f",
          "jump_aerial_b", "jump_aerial_f2", "jump_aerial_f3",
          "jump_aerial_b2", "jump_aerial_b3"]
GUNNER_KINDS = ["jump_aerial_b", "jump_aerial_f", "jump_b", "jump_f",
                "jump_squat"]
ANIMS9 = ["a03jumpsquat.nuanmb", "a03jumpf.nuanmb", "a03jumpb.nuanmb",
          "a03jumpaerialf.nuanmb", "a03jumpaerialb.nuanmb",
          "a03jumpaerialf2.nuanmb", "a03jumpaerialf3.nuanmb",
          "a03jumpaerialb2.nuanmb", "a03jumpaerialb3.nuanmb"]
GUNNER_ANIMS = ["a03jumpaerialb.nuanmb", "a03jumpaerialf.nuanmb",
                "a03jumpb.nuanmb", "a03jumpf.nuanmb", "a03jumpsquat.nuanmb"]

# distributions of the six qualifying fields, value -> fighter count
QUALIFYING_DIST = {
    "0x0e35ca3d82": {2: 85, 3: 3, 4: 2, 5: 1, 6: 3},
    "0x1800b91901": {0: 1, 3: 91, 5: 1, 6: 1},
    "0x189aea226c": {2: 1, 4: 2, 5: 61, 8: 7, 10: 23},
    "0x18cde09792": {1: 7, 30: 87},
    "0x19327d6d0a": {0: 74, 1: 20},
    "0x19f190006a": {0: 1, 5: 93},
}

NEG_MODES = ("hash", "slot", "word", "reloc", "site", "disp", "mlist")

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md.detail = True
_VCACHE: dict = {}


# ------------------------------------------------------------------- primitives
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def movz_dec(w):
    if (w & 0xFF800000) == 0xD2800000:
        return (w & 31, (w >> 5) & 0xFFFF, (w >> 21) & 3, 1)
    if (w & 0xFF800000) == 0x52800000:
        return (w & 31, (w >> 5) & 0xFFFF, (w >> 21) & 3, 0)
    return None


def movk_dec(w):
    if (w & 0xFF800000) == 0xF2800000:
        return (w & 31, (w >> 5) & 0xFFFF, (w >> 21) & 3, 1)
    if (w & 0xFF800000) == 0x72800000:
        return (w & 31, (w >> 5) & 0xFFFF, (w >> 21) & 3, 0)
    return None


def dest_regs(w: int) -> set:
    hit = _VCACHE.get(w)
    if hit is not None:
        return hit
    out = set()
    try:
        ins = next(md.disasm(struct.pack("<I", w), 0), None)
        if ins is not None:
            _, writes = ins.regs_access()
            for r in writes:
                nm = ins.reg_name(r)
                if nm and nm[0] in "xw" and nm[1:].isdigit():
                    out.add(int(nm[1:]))
            if ins.mnemonic in ("bl", "blr"):
                out |= set(range(0, 19))
    except capstone.CsError:
        out = set(range(0, 31))
    _VCACHE[w] = out
    return out


def insn_text(data, a):
    ins = next(md.disasm(data[a:a + 4], a), None)
    return (ins.mnemonic + " " + ins.op_str).strip() if ins else ".word"


def load_relocs(data):
    out = {}
    i = RELA0
    while i + REC <= RELA1:
        r_off, r_info, pad, addend = struct.unpack_from("<QIIQ", data, i)
        if r_info == R_REL and pad == 0 and addend != 0:
            out[r_off] = addend
        i += REC
    return out


# ------------------------------------------------------- independent site scanner
def first_call(data, start, limit):
    n = (limit - start) // 4
    if n <= 0:
        return None
    words = struct.unpack_from("<%dI" % n, data, start)
    for i in range(n):
        w = words[i]
        a = start + 4 * i
        if (w & 0xFC000000) == 0x94000000:
            return {"kind": "bl", "addr": a}
        if (w & 0xFFFFFC1F) == 0xD63F0000:
            return {"kind": "blr", "addr": a, "reg": (w >> 5) & 31}
    return None


def ldr64(word):
    if (word & 0xFFC00000) == 0xF9400000:
        return ((word >> 5) & 31, word & 31, ((word >> 10) & 0xFFF) * 8)
    if (word & 0xFFC00000) == 0xF8400000:
        imm = (word >> 12) & 0x1FF
        if imm & 0x100:
            imm -= 0x200
        return ((word >> 5) & 31, word & 31, imm)
    return None


def writer_before(data, addr, reg, back):
    for k in range(1, back + 1):
        a = addr - 4 * k
        if a < TEXT[0]:
            return None
        if reg in dest_regs(struct.unpack_from("<I", data, a)[0]):
            return a
    return None


def x2_fact(data, call_addr):
    a = writer_before(data, call_addr, 2, BACK_X2)
    if a is None:
        return {"addr": None, "text": None, "value": None}
    w = struct.unpack_from("<I", data, a)[0]
    value = None
    mz = movz_dec(w)
    if mz is not None and mz[0] == 2:
        value = mz[1] << (16 * mz[2])
    elif (w & 0xFF200000) == 0xAA000000 and (w & 31) == 2 \
            and ((w >> 5) & 31) == 31 and ((w >> 16) & 31) == 31:
        value = 0                       # mov x2, xzr (orr x2, xzr, xzr)
    return {"addr": a, "text": insn_text(data, a), "value": value}


def classify(data, seed_addr, complete_addr):
    call = first_call(data, complete_addr + 4, complete_addr + 4 + SPAN)
    if call is None:
        return {"class": "none", "call": None, "displacement": None}
    if call["kind"] == "bl":
        return {"class": "direct_bl", "call": call, "displacement": None}
    reg = call["reg"]
    pa = writer_before(data, call["addr"], reg, BACK_PROD)
    if pa is None:
        return {"class": "indirect_no_producer", "call": call,
                "displacement": None}
    pw = struct.unpack_from("<I", data, pa)[0]
    dec = ldr64(pw)
    if dec is None:
        return {"class": "indirect_other_producer", "call": call,
                "displacement": None, "producer_addr": pa,
                "producer_text": insn_text(data, pa)}
    return {"class": "indirect", "call": call, "displacement": dec[2],
            "producer_addr": pa, "producer_text": insn_text(data, pa),
            "x2": x2_fact(data, call["addr"])}


def scan_sequences_with_complete(data, targets):
    """Same rule as scan_sites but also returns each site's complete_addr."""
    targets = set(targets)
    n = (TEXT[1] - TEXT[0]) // 4
    words = struct.unpack_from("<%dI" % n, data, TEXT[0])
    found: dict = {}
    for i in range(n):
        mz = movz_dec(words[i])
        if mz is None:
            continue
        reg, imm16, hw, sf = mz
        value = imm16 << (16 * hw)
        seed = TEXT[0] + 4 * i
        gap = 0
        seq_last = seed
        done = False
        for j in range(i + 1, min(n, i + 13)):
            w2 = words[j]
            mk = movk_dec(w2)
            if mk is not None and mk[0] == reg and mk[3] == sf:
                v, im, hh, _ = mk
                value = (value & ~(0xFFFF << (16 * hh))) | (im << (16 * hh))
                gap = 0
                seq_last = TEXT[0] + 4 * j
            elif movz_dec(w2) is not None and movz_dec(w2)[0] == reg \
                    and movz_dec(w2)[3] == sf:
                break
            else:
                if reg in dest_regs(w2):
                    break
                gap += 1
                if gap > MAX_GAP:
                    break
            if value in targets:
                found.setdefault(value, []).append(
                    {"seed": seed, "complete": seq_last})
                break
    return found


# ---------------------------------------------------------------- motion lists
def hash40(name: str) -> int:
    b = name.encode("utf-8")
    return (len(b) << 32) | zlib.crc32(b)


def decode_mlist(path: Path):
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    magic, _mp, count = struct.unpack_from("<QQQ", data, 0)
    if magic != hash40("motion"):
        raise ValueError("bad magic %s" % path)
    off = 24
    kinds, anims = set(), set()
    kind_index: dict = {}
    for idx in range(count):
        kind, _gs, _fl, _bl, n, size = struct.unpack_from("<QQHBBI", data, off)
        off += 24
        kinds.add(kind)
        kind_index[kind] = idx
        for i in range(n):
            anims.add(struct.unpack_from("<Q", data, off + 8 * i)[0])
        off = (off + n * 9 + 3) & ~3
        off += size
    return sha, kinds, anims, count, kind_index


# ------------------------------------------------------------------- measuring
def measure():
    facts: dict = {}

    # --- A: image identity
    facts["image.sha256"] = sha256_of(IMAGE)
    facts["image.size"] = IMAGE.stat().st_size
    facts["full.sha256"] = sha256_of(FULL)
    facts["full6.sha256"] = sha256_of(ROOT / "gamedata/mii_customizer"
                                      "/P6-PRESET-DATA/fighter_param_full.json")
    data = IMAGE.read_bytes()

    # --- B: Q1
    rel = load_relocs(data)
    facts["q1.rela_records"] = len(rel)
    slots = {off: rel.get(VTABLE + off) for off in Q1_SLOTS}
    facts["q1.slots"] = slots
    facts["q1.slot+0x250"] = slots[0x250]
    facts["q1.slot+0x270"] = slots[0x270]
    words_250 = [struct.unpack_from("<I", data, 0x4E53A0 + 4 * k)[0]
                 for k in range(4)]
    facts["q1.words_4e53a0"] = words_250
    facts["q1.pcrel_4e53a0"] = [
        bool((w & 0x1F000000) == 0x10000000
             or (w & 0x7C000000) == 0x14000000
             or (w & 0xFF000010) == 0x54000000
             or (w & 0xFF000000) == 0x58000000) for w in words_250]
    words_270 = [struct.unpack_from("<I", data, 0x4E53E0 + 4 * k)[0]
                 for k in range(4)]
    facts["q1.words_4e53e0"] = words_270
    thunk_words = {a: struct.unpack_from("<I", data, a)[0]
                   for a in THUNK_WORDS}
    facts["q1.thunk_words"] = thunk_words
    ptrs_250 = {off: add for off, add in rel.items() if add == 0x4E53A0}
    ptrs_270 = {off: add for off, add in rel.items() if add == 0x4E53E0}
    facts["q1.reloc_4e53a0"] = ptrs_250
    facts["q1.reloc_4e53e0"] = ptrs_270
    # vtable runs (contiguous stride-8 relocated code pointers >= 0x288 bytes)
    slots_all = sorted(o for o, v in rel.items()
                       if TEXT[0] <= v < TEXT[1] and o % 8 == 0)
    runs, i = [], 0
    while i < len(slots_all):
        j = i
        while j + 1 < len(slots_all) and slots_all[j + 1] == slots_all[j] + 8:
            j += 1
        if (j - i + 1) * 8 >= 0x288:
            runs.append(slots_all[i])
        i = j + 1
    runset = set(runs)
    facts["q1.vt_runs_count"] = len(runs)
    facts["q1.reloc_4e53a0_bases"] = sorted(o - 0x250 for o in ptrs_250
                                            if (o - 0x250) in runset)
    facts["q1.reloc_4e53e0_bases"] = sorted(o - 0x270 for o in ptrs_270
                                            if (o - 0x270) in runset)
    # ldr xN,[xM,#0x250] within 2 insns of br xN, whole .text
    ldr250_br = 0
    for a in range(TEXT[0], TEXT[1], 4):
        w = struct.unpack_from("<I", data, a)[0]
        if (w & 0xFFFFFC00) == (0xF9400000 | ((0x250 // 8) << 10)):
            rt = w & 31
            for k in range(1, 3):
                w2 = struct.unpack_from("<I", data, a + 4 * k)[0]
                if w2 == (0xD61F0000 | (rt << 5)):
                    ldr250_br += 1
                    break
    facts["q1.ldr250_br_count"] = ldr250_br
    # any direct b/bl anywhere in .text into 0x4e53a0 (report: none)
    direct = 0
    for a in range(TEXT[0], TEXT[1], 4):
        w = struct.unpack_from("<I", data, a)[0]
        if (w & 0x7C000000) == 0x14000000:
            t = a + ((((w & 0x3FFFFFF) << 2) ^ 0x80000000) - 0x80000000)
            if t == 0x4E53A0:
                direct += 1
    facts["q1.direct_branches_4e53a0"] = direct

    # --- C: cited words
    for a, w in CITED_WORDS.items():
        facts["word[0x%08x]" % a] = struct.unpack_from("<I", data, a)[0]
    # hash recomposition at each +0x250 site
    for site, (hv, _t, _v) in SITES_250.items():
        comp = None
        for k in range(3):
            w = struct.unpack_from("<I", data, site + 4 * k)[0]
            mz = movz_dec(w)
            if k == 0 and mz is None:
                comp = "seed-not-movz"
                break
            if k == 0:
                comp = mz[1] << (16 * mz[2])
                continue
            mk = movk_dec(w)
            if mk is None:
                comp = "word%d-not-movk" % k
                break
            comp = (comp & ~(0xFFFF << (16 * mk[2]))) | (mk[1] << (16 * mk[2]))
        facts["compose[0x%08x]" % site] = comp
    # producer / call / x2 / return-use facts at the eight sites
    ret_addrs = {0x622960: 0x622980, 0x62E9FC: 0x62EA44, 0x6CA664: 0x6CA678,
                 0x34E567C: 0x34E5690, 0x62BFB4: 0x62BFF8, 0xF0792C: 0xF07954,
                 0xF15620: 0xF15648, 0x33F084C: 0x33F0870}
    for site, (hv, xt, xv) in SITES_250.items():
        prod = site - 4
        facts["sites250.0x%x.producer_word" % site] = struct.unpack_from(
            "<I", data, prod)[0]
        facts["sites250.0x%x.producer_text" % site] = insn_text(data, prod)
        # find the call: first blr after the seed within the span
        call = first_call(data, site, site + SPAN)
        facts["sites250.0x%x.call" % site] = call["addr"] if call else None
        xf = x2_fact(data, call["addr"]) if call else {"text": None,
                                                       "value": None}
        facts["sites250.0x%x.x2_text" % site] = xf["text"]
        facts["sites250.0x%x.x2_value" % site] = xf["value"]
        facts["sites250.0x%x.ret_word" % site] = struct.unpack_from(
            "<I", data, ret_addrs[site])[0]

    # --- D: full site survey over all 369 hashes
    full_doc = json.loads(FULL.read_text(encoding="utf-8"))
    hashes = set()
    values_by_hash: dict = {}
    fighters = []
    for row in full_doc["rows"]:
        fname = row["fighter_kind_name"] or ("row%d" % row["row_index"])
        fighters.append(fname)
        for f in row["fields"]:
            hashes.add(f["hash"])
            values_by_hash.setdefault(f["hash"], {})[fname] = f["value"]
    facts["total.fields"] = len(hashes)
    targets = {int(h, 16) for h in hashes}
    hits = scan_sequences_with_complete(data, targets)
    facts["total.sites"] = sum(len(v) for v in hits.values())

    per_field: dict = {}
    for hv, sites in hits.items():
        cls: dict = {}
        disp: dict = {}
        recs = []
        for s in sites:
            c = classify(data, s["seed"], s["complete"])
            cls[c["class"]] = cls.get(c["class"], 0) + 1
            d = c.get("displacement")
            key = "none" if d is None else hex(d)
            disp[key] = disp.get(key, 0) + 1
            recs.append((s, c))
        per_field[hv] = {"classes": cls, "displacements": disp, "recs": recs}

    int_doc = json.loads(INT_TABLE.read_text(encoding="utf-8"))
    oth_doc = json.loads(OTHERS_TABLE.read_text(encoding="utf-8"))
    facts["i32.fields"] = len(int_doc["rows"])
    facts["others.fields"] = len(oth_doc["rows"])
    facts["qualifying"] = sorted(r["hash"] for r in int_doc["rows"]
                                 if r.get("qualifies"))

    for row in int_doc["rows"] + oth_doc["rows"]:
        hv = int(row["hash"], 16)
        got = per_field.get(hv, {"classes": {}, "displacements": {},
                                 "recs": []})
        h = row["hash"]
        facts["field.%s.code_sites" % h] = len(got["recs"])
        facts["field.%s.classes" % h] = got["classes"]
        facts["field.%s.displacements" % h] = got["displacements"]
        facts["field.%s.via250" % h] = got["displacements"].get("0x250", 0)
        facts["field.%s.via270" % h] = got["displacements"].get("0x270", 0)
        facts["field.%s.table_code_sites" % h] = row["code_sites"]
        facts["field.%s.table_classes" % h] = row["classes"]
        facts["field.%s.table_displacements" % h] = row["displacements"]

    # value statistics + qualifies for the i32 rows
    for row in int_doc["rows"]:
        h = row["hash"]
        vals = [v for v in values_by_hash.get(h, {}).values()]
        facts["values.%s.miigunner" % h] = values_by_hash.get(h, {}).get(
            "fighter_kind_miigunner")
        facts["values.%s.min" % h] = min(vals) if vals else None
        facts["values.%s.max" % h] = max(vals) if vals else None
        facts["values.%s.distinct" % h] = len(set(vals))
        s250 = [c for _s, c in per_field.get(int(h, 16), {"recs": []})["recs"]
                if c.get("displacement") == 0x250]
        differs = len(set(vals)) > 1
        has_zero = any((c.get("x2") or {}).get("value") == 0 for c in s250)
        facts["values.%s.qualifies" % h] = bool(s250 and has_zero and differs)
        if h in QUALIFYING_DIST:
            dist: dict = {}
            for v in values_by_hash.get(h, {}).values():
                dist[v] = dist.get(v, 0) + 1
            facts["dist.%s" % h] = dist

    # sites_250 records + value stats copied out of the artifact table so the
    # suite can pair them against the independent measurements
    for row in int_doc["rows"]:
        h = row["hash"]
        for stat, key in (("miigunner", "miigunner"), ("min", "min"),
                          ("max", "max"), ("distinct", "distinct")):
            facts["table_values.%s.%s" % (h, key)] = row["values"][stat]
        facts["table_values.%s.qualifies" % h] = row["qualifies"]
    for row in int_doc["rows"]:
        for s in row.get("sites_250") or []:
            site = s["site"]
            facts["table_sites250.0x%x.producer_text" % site] = \
                (s.get("producer") or {}).get("text")
            facts["table_sites250.0x%x.call" % site] = \
                (s.get("call") or {}).get("addr")
            facts["table_sites250.0x%x.x2_text" % site] = s.get("x2_text")
            facts["table_sites250.0x%x.x2_value" % site] = \
                s.get("x2_immediate")

    # P4 jump control
    hv = 0x0E35CA3D82
    got = per_field.get(hv, {"classes": {}, "displacements": {}, "recs": []})
    facts["jump.sites"] = len(got["recs"])
    facts["jump.direct_bl"] = got["classes"].get("direct_bl", 0)
    facts["jump.indirect"] = got["classes"].get("indirect", 0)
    facts["jump.none"] = got["classes"].get("none", 0)
    facts["jump.via250"] = got["displacements"].get("0x250", 0)
    facts["jump.via270"] = got["displacements"].get("0x270", 0)
    facts["jump.site250"] = [s["seed"] for s, c in got["recs"]
                             if c.get("displacement") == 0x250]

    # Q4 aggregates
    others = json.loads(OTHERS_TABLE.read_text(encoding="utf-8"))["rows"]
    facts["q4.fields_with_250"] = sorted(
        r["hash"] for r in others if r["displacements"].get("0x250"))
    facts["q4.fields_with_260"] = sorted(
        r["hash"] for r in others if r["displacements"].get("0x260"))

    # --- E: Q3 / motions
    over2 = {k.replace("fighter_kind_", ""): v
             for k, v in values_by_hash["0x0e35ca3d82"].items() if v > 2}
    facts["q3.over2"] = over2
    sha, kinds, anims, gcount, gidx = decode_mlist(GUNNER_MLIST)
    facts["motion.gunner.sha"] = sha
    facts["motion.gunner.entries"] = gcount
    facts["motion.gunner.entry_index"] = {
        k: gidx.get(hash40(k)) for k in
        ("jump_squat", "jump_f", "jump_b", "jump_aerial_f",
         "jump_aerial_b")}
    facts["motion.gunner.kinds"] = sorted(
        k for k in KINDS9 if hash40(k) in kinds)
    facts["motion.gunner.anims"] = sorted(
        a for a in ANIMS9 if hash40(a) in anims)
    # display labels of the nine fighters with jump_count_max > 2
    fj = json.loads(FIGHTERS_JSON.read_text(encoding="utf-8"))
    label_of = {f["name"]: f.get("display_name_label")
                for f in fj["fighters"]}
    facts["q3.over2_labels"] = {n: label_of.get(n) for n in sorted(OVER2)}
    f2_set, f3_set, b2_set, b3_set = set(), set(), set(), set()
    kind_f_set, kind_b_set, anim_f_set = set(), set(), set()
    for name in list(OVER2) + ["mario", "miigunner"]:
        path = DK / name / "motion/body/c00/motion_list.bin"
        _s, ks, an, _c, _i = decode_mlist(path)
        if name in OVER2:
            if hash40("jump_aerial_f") in ks:
                kind_f_set.add(name)
            if hash40("jump_aerial_b") in ks:
                kind_b_set.add(name)
            if hash40("a03jumpaerialf.nuanmb") in an:
                anim_f_set.add(name)
        if hash40("jump_aerial_f2") in ks:
            f2_set.add(name)
        if hash40("jump_aerial_f3") in ks:
            f3_set.add(name)
        if hash40("jump_aerial_b2") in ks:
            b2_set.add(name)
        if hash40("jump_aerial_b3") in ks:
            b3_set.add(name)
        if name in ("mario", "miigunner"):
            facts["motion.%s.has_base_kinds" % name] = all(
                hash40(k) in ks for k in
                ("jump_aerial_f", "jump_aerial_b")) and \
                hash40("jump_aerial_f2") not in ks and \
                hash40("jump_aerial_f3") not in ks
    facts["motion.f2_set"] = sorted(f2_set)
    facts["motion.f3_set"] = sorted(f3_set)
    facts["motion.b2_set"] = sorted(b2_set)
    facts["motion.b3_set"] = sorted(b3_set)
    facts["motion.kind_f_set"] = sorted(kind_f_set)
    facts["motion.kind_b_set"] = sorted(kind_b_set)
    facts["motion.anim_aerial_f_set"] = sorted(anim_f_set)
    return facts


# ------------------------------------------------------------- expectations
def build_expect(facts):
    exp: dict = {}
    exp["image.sha256"] = IMAGE_SHA
    exp["image.size"] = IMAGE_SIZE
    exp["full.sha256"] = "c46dcd3e344b45f7c11a2b7a250405be9c56873f78a65a3335cea274c14415c3"
    exp["full6.sha256"] = FULL_SHA
    exp["motion.gunner.sha"] = GUNNER_MLIST_SHA

    exp["q1.slots"] = Q1_SLOTS
    exp["q1.slot+0x250"] = 0x4E53A0
    exp["q1.slot+0x270"] = 0x4E53E0
    exp["q1.words_4e53a0"] = [0xF9401C00, 0xF9400008, 0xF9401103,
                              0xD61F0060]
    exp["q1.pcrel_4e53a0"] = [False, False, False, False]
    exp["q1.words_4e53e0"] = [0xF9401C00, 0xF9400008, 0xF9401903,
                              0xD61F0060]
    exp["q1.thunk_words"] = THUNK_WORDS
    exp["q1.reloc_4e53a0"] = RELOC_PTRS_250
    exp["q1.reloc_4e53e0"] = RELOC_PTRS_270
    exp["q1.reloc_4e53a0_bases"] = sorted([VTABLE, VT_OTHER])
    exp["q1.reloc_4e53e0_bases"] = sorted([VTABLE, VT_OTHER])
    exp["q1.ldr250_br_count"] = LDR250_BR_COUNT
    exp["q1.rela_records"] = 306167
    exp["q1.direct_branches_4e53a0"] = 0
    exp["q1.vt_runs_count"] = facts["q1.vt_runs_count"]  # observed, pinned below
    # pin the run count to the value published by P2 (928)
    exp["q1.vt_runs_count"] = 928

    for a, w in CITED_WORDS.items():
        exp["word[0x%08x]" % a] = w
    for site, (hv, xt, xv) in SITES_250.items():
        exp["compose[0x%08x]" % site] = hv
        exp["sites250.0x%x.x2_text" % site] = xt
        exp["sites250.0x%x.x2_value" % site] = xv
        exp["sites250.0x%x.producer_word" % site] = 0xF9412908
        exp["sites250.0x%x.producer_text" % site] = "ldr x8, [x8, #0x250]"
    # call / return-use addresses per site (cited in the report)
    exp["sites250.0x622960.call"] = 0x622974
    exp["sites250.0x62e9fc.call"] = 0x62EA40
    exp["sites250.0x6ca664.call"] = 0x6CA674
    exp["sites250.0x34e567c.call"] = 0x34E568C
    exp["sites250.0x62bfb4.call"] = 0x62BFCC
    exp["sites250.0xf0792c.call"] = 0xF07940
    exp["sites250.0xf15620.call"] = 0xF15634
    exp["sites250.0x33f084c.call"] = 0x33F0864
    exp["sites250.0x622960.ret_word"] = 0x2A0003E1
    exp["sites250.0x62e9fc.ret_word"] = 0x2A0003F7
    exp["sites250.0x6ca664.ret_word"] = 0x6B00029F
    exp["sites250.0x34e567c.ret_word"] = 0x7100041F
    exp["sites250.0x62bfb4.ret_word"] = 0xB90037E0
    exp["sites250.0xf0792c.ret_word"] = 0x2A0003F9
    exp["sites250.0xf15620.ret_word"] = 0x2A0003F7
    exp["sites250.0x33f084c.ret_word"] = 0x2A0003F7

    # D: totals and the table-derived expectations
    exp["total.fields"] = TOTAL_FIELDS
    exp["total.sites"] = TOTAL_SITES
    exp["i32.fields"] = I32_FIELDS
    exp["others.fields"] = OTHERS_FIELDS
    exp["qualifying"] = sorted(QUALIFYING)
    for key, val in facts.items():
        if key.startswith("field."):
            # the artifact tables ARE the expectation for the recount
            pass
    # per-field: recount (facts field.*) vs table copies (field.*.table_*)
    # -> handled by direct comparison in run_suite via pair keys below.
    exp["jump.sites"] = JUMP_CONTROL["sites"]
    exp["jump.direct_bl"] = JUMP_CONTROL["direct_bl"]
    exp["jump.indirect"] = JUMP_CONTROL["indirect"]
    exp["jump.none"] = JUMP_CONTROL["none"]
    exp["jump.via250"] = JUMP_CONTROL["via250"]
    exp["jump.via270"] = JUMP_CONTROL["via270"]
    exp["jump.site250"] = [JUMP_CONTROL["site250"]]

    exp["q4.fields_with_250"] = [
        "0x04f7c0246a", "0x092eb50b90", "0x0b99cc3fbc", "0x0e37b007cd",
        "0x0e6992ff2f", "0x114a6894be", "0x12326f1f2a", "0x13042acb2d",
        "0x13cf982a55", "0x13e3bcfb18", "0x1408832504", "0x145620fd97",
        "0x187608007b", "0x18f0607a99"]
    exp["q4.fields_with_260"] = ["0x085699c32b", "0x0dc9a6e1ba",
                                 "0x0f5c75804b", "0x187367db00"]

    # Q3
    exp["q3.over2"] = OVER2
    exp["motion.gunner.kinds"] = GUNNER_KINDS
    exp["motion.gunner.anims"] = GUNNER_ANIMS
    exp["motion.gunner.entries"] = 774
    exp["motion.gunner.entry_index"] = {"jump_squat": 21, "jump_f": 22,
                                        "jump_b": 23, "jump_aerial_f": 26,
                                        "jump_aerial_b": 27}
    exp["q3.over2_labels"] = {
        "buddy": "nam_chr0_00_buddy", "dedede": "nam_chr0_00_dedede",
        "kirby": None, "metaknight": "nam_chr0_00_metaknight",
        "pit": "nam_chr0_00_pit", "pitb": "nam_chr0_00_pitb",
        "plizardon": None, "purin": "nam_chr0_00_purin",
        "ridley": "nam_chr0_00_ridley"}
    exp["motion.f2_set"] = sorted(OVER2)
    exp["motion.f3_set"] = sorted(F3_SET)
    exp["motion.b2_set"] = []
    exp["motion.b3_set"] = []
    exp["motion.kind_f_set"] = []
    exp["motion.kind_b_set"] = []
    exp["motion.anim_aerial_f_set"] = sorted(set(OVER2) - {"buddy"})
    exp["motion.mario.has_base_kinds"] = True
    exp["motion.miigunner.has_base_kinds"] = True
    for h, dist in QUALIFYING_DIST.items():
        exp["dist.%s" % h] = dist
    return exp


def run_suite(facts, exp, verbose=True):
    """Compare facts against exp; print group summaries and every failure."""
    fails = []
    checked = 0

    # pairwise table-vs-recount keys are folded in here:
    #   field.<h>.* (recount) must equal field.<h>.table_* (artifact)
    # but both are also in exp/ facts differently, so we compare them too.
    pairs = []
    for key in list(facts):
        if key.startswith("field.") and ".table_" in key:
            base = key.replace(".table_", "@@")
            pairs.append((base, key))
    n_groups: dict = {}
    group_fail: dict = {}

    def record(group, ok, detail=""):
        nonlocal checked
        checked += 1
        n_groups[group] = n_groups.get(group, 0) + 1
        if not ok:
            fails.append((group, detail))
            group_fail[group] = group_fail.get(group, 0) + 1

    # explicit expectation keys
    for key, want in exp.items():
        got = facts.get(key)
        grp = key.split(".")[0].split("[")[0]
        record(grp, got == want,
               "%s: got %r want %r" % (key, got, want))
    # recount vs artifact table (site counts / classes / displacements)
    for base, tkey in pairs:
        rkey = base.replace("@@", ".")
        got = facts.get(rkey)
        want = facts.get(tkey)
        record("table", got == want, "%s: recount %r vs table %r"
               % (rkey, got, want))
    # artifact table vs measurement: sites_250 records and value statistics
    for key in list(facts):
        if key.startswith("table_sites250."):
            rkey = key.replace("table_sites250.", "sites250.", 1)
            if rkey in facts:
                record("table250", facts.get(rkey) == facts[key],
                       "%s: measured %r vs table %r"
                       % (rkey, facts.get(rkey), facts[key]))
        if key.startswith("table_values."):
            rkey = key.replace("table_values.", "values.", 1)
            record("tablevalues", facts.get(rkey) == facts[key],
                   "%s: measured %r vs table %r"
                   % (rkey, facts.get(rkey), facts[key]))

    if verbose:
        for g in sorted(n_groups):
            bad = group_fail.get(g, 0)
            print("%-4s %-14s %d checks" % ("FAIL" if bad else "PASS",
                                            g, n_groups[g]))
        shown: dict = {}
        for g, d in fails:
            shown[g] = shown.get(g, 0) + 1
            if shown[g] <= 3:
                print("  FAIL %s" % d)
        if len(fails) > sum(min(v, 3) for v in shown.values()):
            print("  ... %d more failures" %
                  (len(fails) - sum(min(v, 3) for v in shown.values())))
    print("%d checks, %d failures" % (checked, len(fails)))
    return len(fails)


NEG_MUTATIONS = {
    # mode: (expectation key, wrong value)
    "hash": ("image.sha256", "f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7614"),
    "slot": ("q1.slot+0x250", 0x4E53E0),
    "word": ("word[0x004e53a8]", 0xF9401903),
    "reloc": ("q1.reloc_4e53a0", {0x4F896E0: 0x4E53A0, 0x4F73988: 0x4E53A0,
                                  0x4F89708: 0x4E53A0}),
    "site": ("field.0x0e35ca3d82.code_sites", 6),
    "disp": ("field.0x0e35ca3d82.via250", 0),
    "mlist": ("motion.gunner.kinds", GUNNER_KINDS + ["jump_aerial_f2"]),
}


def _hexify(v):
    if isinstance(v, int) and not isinstance(v, bool) and v > 9:
        return "0x%x" % v
    if isinstance(v, dict):
        return "{%s}" % ", ".join("0x%x: 0x%x" % (k, val) if isinstance(k, int)
                                  else "%r: %r" % (k, val)
                                  for k, val in v.items())
    if isinstance(v, list):
        return "[%s]" % ", ".join(_hexify(x) if isinstance(x, int) else repr(x)
                                  for x in v)
    return repr(v)


def main(argv):
    if "--selftest" in argv:
        import contextlib
        import io
        try:
            facts = measure()
        except (OSError, ValueError, KeyError) as exc:
            print("INPUT ERROR: %r" % (exc,))
            return 2
        exp = build_expect(facts)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            clean = run_suite(facts, exp, verbose=False)
        ok = clean == 0
        print("selftest clean : %s (%d failures)"
              % ("PASS" if ok else "FAIL", clean))
        for mode in NEG_MODES:
            key, wrong = NEG_MUTATIONS[mode]
            bad = dict(exp)
            bad[key] = wrong
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                fails = run_suite(facts, bad, verbose=False)
            detected = fails > 0
            ok = ok and detected
            print("selftest neg %-6s : %s"
                  % (mode, "detected (%d mismatches)" % fails if detected
                     else "NOT DETECTED - CHECKER BROKEN"))
        print("SELFTEST", "OK" if ok else "BROKEN")
        return 0 if ok else 1

    neg = None
    neg_all = False
    if "--neg" in argv:
        idx = argv.index("--neg")
        if idx + 1 < len(argv) and not argv[idx + 1].startswith("-"):
            neg = argv[idx + 1]
            if neg not in NEG_MODES:
                print("unknown negative control %r; one of %s"
                      % (neg, ", ".join(NEG_MODES)))
                return 2
        else:
            neg_all = True

    try:
        facts = measure()
    except (OSError, ValueError, KeyError) as exc:
        print("INPUT ERROR: %r" % (exc,))
        return 2
    exp = build_expect(facts)

    if neg_all:
        all_detected = True
        for mode in NEG_MODES:
            key, wrong = NEG_MUTATIONS[mode]
            bad = dict(exp)
            bad[key] = wrong
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                fails = run_suite(facts, bad, verbose=False)
            detected = fails > 0
            all_detected = all_detected and detected
            print("neg %-6s %s (control: %s = %s)"
                  % (mode, "detected (suite failed, %d mismatches)" % fails
                     if detected else "NOT DETECTED - CHECKER BROKEN",
                     key, _hexify(wrong)))
        print("ALL %d CONTROLS DETECTED - CHECKER OK" % len(NEG_MODES)
              if all_detected else "SOME CONTROLS NOT DETECTED - CHECKER BROKEN")
        # house convention: a run of the negative controls exits 1 when every
        # control failed as required; --selftest is the green-light runner.
        return 1 if all_detected else 0

    if neg:
        key, wrong = NEG_MUTATIONS[neg]
        bad = dict(exp)
        bad[key] = wrong
        fails = run_suite(facts, bad, verbose=True)
        detected = fails > 0
        print("neg %r: %s" % (neg, "detected" if detected
                              else "NOT DETECTED - CHECKER BROKEN"))
        # each control must fail: exit 1 when the mutated suite failed
        return 1 if detected else 0

    fails = run_suite(facts, exp, verbose=True)
    if fails:
        print("FAIL")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
