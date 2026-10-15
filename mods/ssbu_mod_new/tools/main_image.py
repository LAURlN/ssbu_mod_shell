"""Read-only access to the 13.0.4 `main` image: bytes, R_AARCH64_RELATIVE relocations, disassembly.

`dumps/exefs/13.0.4/main.bin` (located through `paths.toml` [dumps].exefs) is the decompressed
text+rodata+data image with file offset = image offset. Pointers stored in .data are *not* written
in place: each one is an R_AARCH64_RELATIVE (type 0x403) relocation whose addend is the target, so
`ptr()` reads the relocation table first and falls back to the raw word.

Used by `tools/maindesc.py` (article descriptors per fighter kind) and `tools/audit_event_slots.py`
(fighter-class vtable slots). Smoke test: `tools/audit_event_slots.py --smoke`.
"""
from __future__ import annotations

import struct
import sys
import tomllib
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'toolchains' / 'python_tools'))
import capstone  # noqa: E402

R_AARCH64_RELATIVE = 0x403


def main_path() -> Path:
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text(encoding='utf-8'))
    return ROOT / cfg['dumps']['exefs'] / 'main.bin'


class MainImage:
    def __init__(self, path: Path | None = None):
        self.path = path or main_path()
        self.data = self.path.read_bytes()
        self.md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

    @cached_property
    def dynamic(self) -> dict[int, int]:
        d = self.data
        mod0 = struct.unpack_from('<I', d, 4)[0]
        if d[mod0:mod0 + 4] != b'MOD0':
            raise ValueError(f'{self.path}: no MOD0 at {mod0:#x}')
        i = mod0 + struct.unpack_from('<i', d, mod0 + 4)[0]
        tags: dict[int, int] = {}
        while True:
            tag, val = struct.unpack_from('<qQ', d, i)
            i += 16
            if tag == 0:
                return tags
            tags.setdefault(tag, val)

    @cached_property
    def relocs(self) -> dict[int, int]:
        """image offset of a pointer slot -> the image offset it points at (DT_RELA, DT_RELASZ)."""
        off, size = self.dynamic[7], self.dynamic[8]
        out = {}
        for k in range(0, size, 24):
            r_off, r_info, addend = struct.unpack_from('<QQq', self.data, off + k)
            if r_info & 0xffffffff == R_AARCH64_RELATIVE:
                out[r_off] = addend
        return out

    def ptr(self, addr: int) -> int:
        return self.relocs.get(addr, struct.unpack_from('<Q', self.data, addr)[0])

    def u32(self, addr: int) -> int:
        return struct.unpack_from('<I', self.data, addr)[0]

    def i32(self, addr: int) -> int:
        return struct.unpack_from('<i', self.data, addr)[0]

    def disasm(self, addr: int, size: int):
        return list(self.md.disasm(self.data[addr:addr + size], addr))

    def function_text(self, addr: int, limit: int = 64) -> list[str]:
        """Instructions from `addr` up to and including the first ret/br/b, as 'mnemonic op_str'."""
        out = []
        for ins in self.disasm(addr, limit * 4):
            out.append(f'{ins.mnemonic} {ins.op_str}'.strip())
            if ins.mnemonic in ('ret', 'br', 'b'):
                break
        return out
