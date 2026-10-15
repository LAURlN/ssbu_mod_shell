"""Coordinator check for plugin 0.4.0 (the P10-UI-SLICE worker stopped before writing its own).

Reads every `Site { offset: 0x.., words: [..] }` record and the named word-array constants
out of plugin/src/ui.rs and compares the four instruction words with workspace
gamedata/ssbu-13.0.4/main.bin (flat image, address == file offset). Also checks the image
hash, the strings and vtable-related constants the UI code uses, and that every site offset
occurs in the built NRO next to its first word. Run from the workspace root. Exit 1 on any
mismatch.
"""
import hashlib
import re
import struct
import sys

IMAGE = "gamedata/ssbu-13.0.4/main.bin"
IMAGE_SHA = "f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613"
UI_RS = "mods/mii_customizer/plugin/src/ui.rs"
NRO = "mods/mii_customizer/builds/0.4.0-ui/libmii_customizer.nro"

fails = 0
checks = 0


def check(ok, text):
    global fails, checks
    checks += 1
    if not ok:
        fails += 1
    print(("PASS " if ok else "FAIL ") + text)


def num(text):
    return int(text.replace("_", ""), 16)


image = open(IMAGE, "rb").read()
check(hashlib.sha256(image).hexdigest() == IMAGE_SHA, "image sha256")
src = open(UI_RS, encoding="utf-8").read()
nro = open(NRO, "rb").read()

named = {}
for m in re.finditer(r"const (\w+): \[u32; 4\] = \[([^\]]+)\];", src):
    named[m.group(1)] = [num(w.strip()[2:]) for w in m.group(2).split(",") if w.strip()]

sites = []
for m in re.finditer(r"Site \{ offset: 0x([0-9a-f_]+), words: (\[[^\]]+\]|\w+) \}", src):
    off = num(m.group(1))
    w = m.group(2)
    words = named[w] if w in named else [num(x.strip()[2:]) for x in w.strip("[]").split(",") if x.strip()]
    sites.append((off, words))
check(len(sites) == 20, "20 site/probe records parsed (5 sites + 15 probes), got %d" % len(sites))
for off, words in sites:
    found = list(struct.unpack_from("<4I", image, off))
    check(found == words, "words at 0x%x: %s" % (off, " ".join("%08x" % x for x in found)))
    # the record as compiled: u64 offset followed by the four words
    rec = struct.pack("<Q4I", off, *words)
    check(rec in nro, "record for 0x%x present in the NRO" % off)

consts = {m.group(1): num(m.group(2)) for m in re.finditer(r"pub const (\w+): usize = 0x([0-9a-f_]+);", src)}


def cstr(addr):
    end = image.index(b"\0", addr)
    return image[addr:end].decode("ascii", "replace")


check(cstr(consts["STR_ITEM_NUM"]) == "SCROLLER_ITEM_NUM", "string SCROLLER_ITEM_NUM at 0x%x" % consts["STR_ITEM_NUM"])
check(cstr(consts["STR_INT"]) == "i", "string 'i' at 0x%x" % consts["STR_INT"])
check(consts["HAT_STATIC"] - consts["WORK_RECORD"] == 0x138, "HAT_STATIC = WORK_RECORD + 0x138")

# Relocation array: {u64 r_offset, u32 r_info, u32 pad, u64 r_addend}; a vtable address is
# plausible when its first slot is a relocated code pointer.
RELA0, RELA1 = 0x39C8070, 0x40C9FC8
slots = {}
for at in range(RELA0, RELA1, 24):
    r_off, r_info, _pad, addend = struct.unpack_from("<QIIQ", image, at)
    if r_info == 0x403:
        slots[r_off] = addend
for name in ("VT_LIST_OBJECT", "VT_SUB_OBJECT", "VT_SCROLLER"):
    a = consts[name]
    check(a in slots and slots[a] < 0x39C0000, "%s 0x%x: first slot relocates to code 0x%x" % (name, a, slots.get(a, 0)))
check(slots.get(consts["VT_SUB_OBJECT"]) == 0x19CC9E0, "sub-object vtable slot 0 = 0x19cc9e0 (P10-HAT-OPEN)")
check(slots.get(consts["VT_LIST_OBJECT"] + 0x18) == 0x19CFDB0, "list vtable slot +0x18 = 0x19cfdb0 (P10-HAT-OPEN)")

for label in (b"nam_mii_hat_none_m", b"nam_mii_hat_unknown"):
    check(label in open("gamedata/ssbu-13.0.4/files/ui/message/msg_name.msbt", "rb").read(),
          "label %s exists in msg_name.msbt" % label.decode())

print("%d checks, %d failed" % (checks, fails))
sys.exit(1 if fails else 0)
