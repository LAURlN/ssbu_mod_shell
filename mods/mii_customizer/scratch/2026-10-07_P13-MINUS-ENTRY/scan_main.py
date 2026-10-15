"""One-off P13 native text scan; input main.bin is read-only."""
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

IMAGE = Path("gamedata/ssbu-13.0.4/main.bin")
data = IMAGE.read_bytes()
for label in (b"is_pressed", b"is_pressing", b"is_released",
              b"virtual_input", b"Minus", b"zl_or_zr_held"):
    offsets = []
    start = 0
    needle = label + b"\0"
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            break
        offsets.append(pos)
        start = pos + 1
    print(label.decode(), ", ".join(hex(x) for x in offsets[:40]))
for addr in (0x42e47f2, 0x4337947, 0x4463214, 0x4369aa2):
    needle = addr.to_bytes(8, "little")
    refs = []
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            break
        refs.append(pos)
        start = pos + 1
    print("qword refs", hex(addr), ", ".join(hex(x) for x in refs[:40]))

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
sample = int.from_bytes(data[0x1809004:0x1809008], "little")
print("ADRP sample", hex(sample), hex(sample & 0x9f000000))
string_addrs = {0x42e47f2, 0x4337947, 0x4463214, 0x4369aa2,
                0x4306e80}
page_targets = {a & ~0xfff for a in string_addrs}
hits = []
for pos in range(0, len(data) - 8, 4):
    a = int.from_bytes(data[pos:pos + 4], "little")
    if a & 0x9f000000 != 0x90000000:  # ADRP
        continue
    imm = (((a >> 5) & 0x7ffff) << 2) | ((a >> 29) & 3)
    if imm & (1 << 20):
        imm -= 1 << 21
    page = (pos & ~0xfff) + (imm << 12)
    if page not in page_targets:
        continue
    b = int.from_bytes(data[pos + 4:pos + 8], "little")
    rd = a & 31
    if b & 0x7f000000 != 0x11000000 or ((b >> 5) & 31) != rd:
        continue
    lo = (b >> 10) & 0xfff
    if b & (1 << 22):
        lo <<= 12
    target = page + lo
    if pos == 0x1809004:
        print("KNOWN REF", hex(page), hex(target), hex(b), hex(rd), hex((b >> 5) & 31))
    if target in string_addrs:
        hits.append(pos)
for pos in hits:
    print("\nXREF at", hex(pos))
    for ins in md.disasm(data[pos - 16:pos + 40], pos - 16):
        print("0x%08x: %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
