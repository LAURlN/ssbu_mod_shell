import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'python_tools'))
import lz4.block

source = next((ROOT.parents[1] / 'Super Smash Bros. Ultimate 13.0.4 [01006A800016E800][v1966080][UPD]').rglob('main'))
raw = source.read_bytes()
assert raw[:4] == b'NSO0', raw[:4]
u32 = lambda offset: struct.unpack_from('<I', raw, offset)[0]
flags = u32(12)
segments = []
image = bytearray()
for i, name in enumerate(('text', 'rodata', 'data')):
    offset, address, size = struct.unpack_from('<III', raw, 16 + 16*i)
    stored_size = u32(0x60 + i*4) if flags & (1 << i) else size
    stored = raw[offset:offset+stored_size]
    assert len(stored) == stored_size
    block = lz4.block.decompress(stored, uncompressed_size=size) if flags & (1 << i) else stored
    assert len(block) == size
    digest = hashlib.sha256(block).digest()
    expected = raw[0xA0+32*i:0xC0+32*i]
    check_enabled = bool(flags & (1 << (i+3)))
    assert not check_enabled or digest == expected, name
    if len(image) < address + size:
        image.extend(bytes(address+size-len(image)))
    image[address:address+size] = block
    segments.append(dict(name=name, address=address, size=size, hash_check_enabled=check_enabled, hash_matches=digest==expected))

mod_offset = struct.unpack_from('<I', image, 4)[0]
assert image[mod_offset:mod_offset+4] == b'MOD0'
dynamic_offset = mod_offset + struct.unpack_from('<i', image, mod_offset+4)[0]
dynamic = {}
for offset in range(dynamic_offset, len(image), 16):
    tag, value = struct.unpack_from('<QQ', image, offset)
    if tag == 0:
        break
    dynamic[tag] = value
str_offset, str_size = dynamic[5], dynamic[10]
sym_offset = dynamic[6]
assert dynamic[11] == 24
symbol_count = struct.unpack_from('<I', image, dynamic[4]+4)[0]
strings = image[str_offset:str_offset+str_size]
symbols = []
for offset in range(sym_offset, sym_offset+symbol_count*24, 24):
    name_offset, info, other, section, value, size = struct.unpack_from('<IBBHQQ', image, offset)
    end = strings.find(0, name_offset)
    name = strings[name_offset:end].decode('utf8', errors='replace')
    if name:
        symbols.append(dict(name=name, address=value, size=size, section=section, type=info & 15))
report = dict(source=str(source), sha256=hashlib.sha256(raw).hexdigest(), build_id=raw[0x40:0x60].hex(), flags=flags, segments=segments, symbol_count=len(symbols))
(ROOT / 'main_inventory.json').write_text(json.dumps(report, indent=2))
(ROOT / 'main_symbols.json').write_text(json.dumps(symbols, indent=2))
(ROOT / 'main_memory.bin').write_bytes(image)
print(json.dumps(report, indent=2))
matches = [s for s in symbols if any(t in s['name'].lower() for t in ('element', 'change_fighter', 'fightermanager', 'fighterentry'))]
(ROOT / 'transformation_symbols.json').write_text(json.dumps(matches, indent=2))
for s in matches:
    if 'element' in s['name'].lower() or 'change' in s['name'].lower():
        print(hex(s['address']), s['size'], s['name'])
