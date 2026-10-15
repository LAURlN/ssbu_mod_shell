"""Disassemble ranges in the pinned user main dump (start:end hex pairs)."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
sys.path.insert(0, str(WORKSPACE / 'mod_files/mythra_gamewatch_swap/tools/analysis_lib'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

reference = WORKSPACE / 'references/mythra_gamewatch_feasibility'
data = (reference / 'main_memory.bin').read_bytes()
symbols = json.loads((reference / 'main_symbols.json').read_text())
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
for arg in sys.argv[1:]:
    start, end = (int(value, 16) for value in arg.split(':'))
    print(f'RANGE {start:#x}:{end:#x}')
    for symbol in symbols:
        if symbol['address'] <= end and symbol['address'] + symbol['size'] > start:
            print('SYMBOL', symbol)
    for ins in md.disasm(data[start:end], start):
        print(f'{ins.address:#x}: {ins.mnemonic} {ins.op_str}')
