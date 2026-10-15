"""Reproduce the relevant native trace from the supplied decompressed main."""
import json
import sys
from pathlib import Path

workspace = Path(__file__).resolve().parents[3]
reference = workspace / "references/mythra_gamewatch_feasibility"
sys.path.insert(0, str(reference / "python_tools"))
import capstone

data = (reference / "main_memory.bin").read_bytes()
symbols = {s["address"]: s["name"] for s in
           json.loads((reference / "main_symbols.json").read_text()) if s["address"]}
disassembler = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
regions = [
    (0x6581f0, 0x6585f8, "switch coordinator: capture outgoing fighter"),
    (0x649980, 0x649a84, "save position, facing, situation and speeds"),
    (0x64aa20, 0x64aa78, "character-specific capture callback and deactivation"),
    (0x65661c, 0x656728, "activate incoming fighter, then restore callback"),
    (0x64aea0, 0x64b030, "restore dispatcher; character callback at vtable+0x2f0"),
    (0x64fb70, 0x64fc20, "active subfighter table selection"),
    (0x20cbc40, 0x20cbd10, "entry ID accessor semantics"),
    (0x206ade0, 0x206aee0, "PostureModule wrappers identify position operations"),
]
for start, end, label in regions:
    print(f"\n{label}\n")
    for instruction in disassembler.disasm(data[start:end], start):
        symbol = ""
        if instruction.mnemonic in ("b", "bl") and instruction.op_str.startswith("#"):
            symbol = symbols.get(int(instruction.op_str[1:], 16), "")
        print(f"{instruction.address:08x}: {instruction.mnemonic:8} {instruction.op_str} {symbol}")
