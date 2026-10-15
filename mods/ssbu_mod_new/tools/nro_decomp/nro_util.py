"""Shared helpers for tools/nro_decomp: lua constant names, PLT stub -> import name."""
import re, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'toolchains' / 'python_tools'))
import capstone  # noqa: E402

COMMON_NRO = ROOT / 'dumps/arc/prebuilt/nro/release/lua2cpp_common.nro'
_CONST = {}


def const_name(off):
    """Name of the lua constant at byte offset `off` of lua2cpp's const_value_table (method of tools/constmap.py)."""
    if not _CONST:
        src = (ROOT / 'tools/constmap.py').read_text().split("if __name__")[0]
        src = re.sub(r"d=open\([^)]*\)", "d=open(%r,'rb')" % COMMON_NRO.as_posix(), src)
        exec(compile(src, 'constmap', 'exec'), _CONST)
    return _CONST['name'](off)


def disasm(img, start, size):
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    return md.disasm(img[start:start + size], start)


def bl_callers(img, text_end, target):
    """Addresses of every `bl target` in [0, text_end), decoded from the words (no linear-sweep stop on data)."""
    out = []
    for a in range(0, text_end, 4):
        w = struct.unpack_from('<I', img, a)[0]
        if (w & 0xfc000000) == 0x94000000:
            off = (w & 0x3ffffff) << 2
            if off & (1 << 27): off -= 1 << 28
            if a + off == target: out.append(a)
    return out


def plt_map(img, labels, text_end):
    """{plt stub address: mangled import name} for `adrp x16; ldr x17,[x16,#o]; add; br x17` stubs."""
    out = {}
    for a in range(0, text_end, 16):
        w0 = struct.unpack_from('<I', img, a)[0]
        if (w0 & 0x9f00001f) != 0x90000010:  # adrp x16
            continue
        ins = list(disasm(img, a, 16))
        if len(ins) == 4 and ins[1].mnemonic == 'ldr' and ins[3].mnemonic == 'br':
            page = int(ins[0].op_str.split('#')[1], 0)
            m = re.search(r'#(0x[0-9a-f]+|\d+)\]', ins[1].op_str)
            off = int(m.group(1), 0) if m else 0
            tgt = struct.unpack_from('<Q', img, page + off)[0]
            if hex(tgt) in labels:
                out[a] = labels[hex(tgt)]
    return out
