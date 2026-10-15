"""P12-INT-PARAMS step 2 (Q1): slot +0x250 of vtable 0x4f89490.

Reads workspace gamedata/ssbu-13.0.4/main.bin only (flat, VA == file offset).

  python scratch/2026-10-07_P12-INT-PARAMS/q1_slot.py

Does:
  1. sha256 of the image (pinned f70c97d2...7613).
  2. Parses the RELA table; prints slots +0x240..+0x288 of vtable 0x4f89490.
  3. Disassembles the function behind slot +0x250 with raw words and a
     PC-relative flag per instruction; same for 0x4e53e0 (slot +0x270).
  4. Finds every .text site that re-dispatches into slot +0x250
     (`ldr xN, [xM, #0x250]` then `br xN` within 2 insns) and lists the
     enclosing slot if the site is itself a thunk in 0x4e5390..0x4e53f0.
  5. Scans every RELA addend for the +0x250 function address: which
     other vtable slots (and, for runs >= 0x288 bytes, which vtables)
     point at it.
  6. Per-slot re-dispatch check: does the body of slot +0x248..+0x278
     branch into the +0x250 function?
Exits 1 on any failed check.
"""
import hashlib
import struct
import sys
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

IMAGE = Path(__file__).resolve().parents[4] / "gamedata/ssbu-13.0.4/main.bin"
PINNED = "f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613"
VTABLE = 0x4F89490
CODE = (0x100, 0x39C8000)
RELA = (0x39C8070, 0x40C9FC8)
REC = 24
R_AARCH64_RELATIVE = 0x403

data = IMAGE.read_bytes()
md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
fails = []


def check(cond, msg):
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        fails.append(msg)


def load_relocs():
    out = {}
    i = RELA[0]
    while i + REC <= RELA[1]:
        r_off, r_info, pad, addend = struct.unpack_from("<QIIQ", data, i)
        if r_info == R_AARCH64_RELATIVE and pad == 0 and addend != 0:
            out[r_off] = addend
        i += REC
    return out


def disasm(addr, n):
    rows = []
    for ins in md.disasm(data[addr:addr + 4 * n], addr):
        w = struct.unpack_from("<I", data, ins.address)[0]
        pcrel = bool(
            (w & 0x1F000000) == 0x10000000        # adrp
            or (w & 0x7C000000) == 0x14000000     # b / bl
            or (w & 0xFF000010) == 0x54000000     # b.cond
            or (w & 0xFF000000) == 0x58000000     # ldr (literal)
        )
        rows.append((ins.address, w, ins.mnemonic, ins.op_str, pcrel))
    return rows


def show(addr, n, tag=""):
    print("  --- 0x%x %s ---" % (addr, tag))
    for a, w, mn, op, pr in disasm(addr, n):
        print("  0x%08x: %08x  %-7s %-24s%s"
              % (a, w, mn, op, "  PC-RELATIVE" if pr else ""))


def main():
    sha = hashlib.sha256(data).hexdigest()
    print("image %s" % IMAGE)
    print("size  %d" % len(data))
    print("sha   %s" % sha)
    check(sha == PINNED, "image sha256 matches pinned f70c97d2...7613")

    rel = load_relocs()
    print("\nRELA records parsed: %d" % len(rel))
    print("\n=== vtable 0x%x slots +0x240..+0x288 (RELA addends) ===" % VTABLE)
    slots = {}
    for off in range(0x240, 0x290, 8):
        v = rel.get(VTABLE + off)
        slots[off] = v
        print("  [0x%x]+0x%03x = %s"
              % (VTABLE, off, ("0x%x" % v) if v else "none"))

    fn250 = slots.get(0x250)
    fn270 = slots.get(0x270)
    check(fn250 is not None, "slot +0x250 has a relocated function pointer")
    check(fn270 == 0x4E53E0, "slot +0x270 == 0x4e53e0 (per prompt/background)")
    if fn250 is None:
        print("no +0x250 target; stopping")
        return 1

    print()
    show(fn250, 8, "slot +0x250 target")
    print()
    show(0x4E53E0, 8, "0x4e53e0, slot +0x270 target (comparison)")

    rows250 = disasm(fn250, 4)
    words250 = [r[1] for r in rows250]
    print("\nfirst four words of 0x%x: %s" % (fn250, " ".join("0x%08x" % w for w in words250)))
    print("mnemonics: %s" % " ".join(r[2] for r in rows250))
    check(all(not r[4] for r in rows250),
          "0x%x first four instructions are not PC-relative" % fn250)

    # Which other slots re-dispatch into fn250: bodies of the neighbouring
    # thunks, plus any .text `ldr ..., #0x250` + `br` site.
    print("\n=== re-dispatch into slot +0x250 ===")
    found = []
    for i in range(CODE[0], CODE[1], 4):
        w = struct.unpack_from("<I", data, i)[0]
        if (w & 0xFFFFFC00) == (0xF9400000 | ((0x250 // 8) << 10)):
            rt, rn = w & 31, (w >> 5) & 31
            for k in range(1, 3):
                w2 = struct.unpack_from("<I", data, i + 4 * k)[0]
                if w2 == (0xD61F0000 | (rt << 5)):
                    found.append((i, rt, rn, k))
                    break
    print("  `ldr xN,[xM,#0x250]` within 2 insns of `br xN`: %d" % len(found))
    thunk_lo, thunk_hi = 0x4E5390, 0x4E53FC
    for i, rt, rn, k in found:
        print("    0x%x: ldr x%d,[x%d,#0x250] then br x%d after %d insn%s"
              % (i, rt, rn, rt, k, "s" if k > 1 else ""))

    # bodies of neighbour slots: any direct b into fn250?
    print("\n  branch targets in neighbour thunk bodies (0x4e5390..0x4e53f0):")
    for base in range(0x4E5390, 0x4E53FC, 4):
        for a, w, mn, op, pr in disasm(base, 4):
            if mn in ("b", "bl") and op.startswith("#"):
                t = int(op[1:], 16)
                if t == fn250:
                    print("    0x%x: %s %s -> 0x%x (= +0x250 fn)"
                          % (a, mn, op, t))
    # which slots are thunks whose body ends `br` into fn250 indirectly
    slot_of = {v: k for k, v in slots.items() if v}

    # every RELA addend equal to fn250
    hits = sorted(off for off, add in rel.items() if add == fn250)
    print("\n=== RELA slots holding fn 0x%x ===" % fn250)
    print("  %d relocated slots: %s"
          % (len(hits), ", ".join("0x%x" % h for h in hits[:20])
             + (" ..." if len(hits) > 20 else "")))
    # vtable runs
    slots_all = sorted(a for a, v in rel.items()
                       if CODE[0] <= v < CODE[1] and a % 8 == 0)
    runs = []
    i = 0
    while i < len(slots_all):
        j = i
        while j + 1 < len(slots_all) and slots_all[j + 1] == slots_all[j] + 8:
            j += 1
        if (j - i + 1) * 8 >= 0x288:
            runs.append(slots_all[i])
        i = j + 1
    runset = set(runs)
    at250 = [h for h in hits if (h - 0x250) in runset]
    print("  of those, %d sit at +0x250 of a vtable run (>=0x288 bytes);"
          " bases: %s" % (len(at250), ", ".join("0x%x" % (h - 0x250) for h in at250)))
    other = [h for h in hits if h not in at250]
    if other:
        print("  other slot addresses: %s" % ", ".join("0x%x" % h for h in other))
    print("  total qualifying vtable runs in image: %d" % len(runs))

    # same for +0x270 for comparison
    hits270 = sorted(off for off, add in rel.items() if add == 0x4E53E0)
    at270 = [h for h in hits270 if (h - 0x270) in runset]
    print("  comparison: fn 0x4e53e0 sits in %d slots, %d at +0x270 of a run"
          % (len(hits270), len(at270)))

    print("\n%s  (%d failures)" % ("ALL PASS" if not fails else "FAILURES", len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
