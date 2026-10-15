"""Read-only inspection of the user's native grenade code and NRO imports."""
from pathlib import Path
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent / 'analysis_lib'))
sys.path.insert(0, str(ROOT / 'references/mythra_gamewatch_feasibility'))
import capstone
from inspect_nro import parse_nro

OUT = ROOT / 'references/snake_grenade'


def main():
    cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    main_symbols = json.loads((ROOT / 'references/mythra_gamewatch_feasibility/main_symbols.json').read_text())
    main_data = (ROOT / 'references/mythra_gamewatch_feasibility/main_memory.bin').read_bytes()
    labels = {s['address']: s['name'] for s in main_symbols if s['address']}
    wanted = ['snakegrenade', 'ItemModule__have_item_impl', 'ItemModule__drop_item_impl']
    lines = []
    for sym in main_symbols:
        if sym['address'] and any(key in sym['name'] for key in wanted):
            lines.append(f"\n{sym['name']} @ {sym['address']:#x} size={sym['size']:#x}")
            for ins in cs.disasm(main_data[sym['address']:sym['address'] + min(sym['size'] or 256, 1024)], sym['address']):
                target = int(ins.op_str[1:], 16) if ins.mnemonic in ('b', 'bl') and ins.op_str.startswith('#0x') else 0
                lines.append(f'{ins.address:#x}: {ins.mnemonic:8} {ins.op_str} {labels.get(target, "")}')
    for fighter in ('snake', 'item'):
        path = ROOT / f'export/prebuilt/nro/release/lua2cpp_{fighter}.nro'
        symbols = parse_nro(path)
        (OUT / f'{fighter}_symbols.json').write_text(json.dumps(symbols, indent=2), encoding='utf-8')
        lines.append(f'\n{fighter}: {len(symbols)} dynamic symbols')
        for sym in symbols:
            if any(key in sym['name'].lower() for key in ('grenade', 'have_item', 'create_item', 'special_n', 'specialn')):
                lines.append(f"{sym['address']:#x} {sym['size']:#x} {sym['name']}")
        if fighter == 'item':
            data = path.read_bytes()
            mod = struct.unpack_from('<I', data, 4)[0]
            dyn_off = mod + struct.unpack_from('<i', data, mod + 4)[0]
            dyn = {}
            while True:
                tag, value = struct.unpack_from('<QQ', data, dyn_off)
                dyn_off += 16
                if not tag:
                    break
                dyn[tag] = value
            got = {}
            for off in range(dyn[23], dyn[23] + dyn[2], 24):
                target, info, addend = struct.unpack_from('<QQq', data, off)
                got[target] = symbols[info >> 32]['name']
            text_off, text_size = struct.unpack_from('<II', data, 0x20)
            plt = {}
            for off in range(text_off, text_off + text_size - 8, 4):
                a, b = struct.unpack_from('<II', data, off)
                if (a & 0x9f00001f) == 0x90000010 and (b & 0xffc003ff) == 0xf9400211:
                    imm = (((a >> 5) & 0x7ffff) << 2) | ((a >> 29) & 3)
                    if imm & 0x100000:
                        imm -= 0x200000
                    addr = (off & ~0xfff) + (imm << 12) + (((b >> 10) & 0xfff) * 8)
                    if addr in got:
                        plt[off] = got[addr]
            for off in range(text_off, text_off + text_size, 4):
                word = struct.unpack_from('<I', data, off)[0]
                if word & 0xfc000000 != 0x94000000:
                    continue
                imm = word & 0x3ffffff
                if imm & 0x2000000:
                    imm -= 0x4000000
                target = off + imm * 4
                if 'snakegrenade' not in plt.get(target, ''):
                    continue
                lines.append(f'\nItem callsite {off:#x}: {plt[target]}')
                for ins in cs.disasm(data[max(0, off - 192):off + 256], max(0, off - 192)):
                    dest = int(ins.op_str[1:], 16) if ins.mnemonic in ('b', 'bl') and ins.op_str.startswith('#0x') else 0
                    lines.append(f'{ins.address:#x}: {ins.mnemonic:8} {ins.op_str} {plt.get(dest, "")}')
    (OUT / 'native_item_inspection.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
