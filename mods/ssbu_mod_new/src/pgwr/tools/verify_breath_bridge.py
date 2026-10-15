"""Cross-check the bridge against the actual 13.0.4 decoder and donor PRC."""
from pathlib import Path
import hashlib
import json
import re
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prc

project = Path(__file__).resolve().parents[1]
root = project.parents[1]
image = (root / 'dumps/exefs/13.0.4/main.bin').read_bytes()
source = (project / 'plugin/src/breath.rs').read_text()
donor = prc.as_dict(prc.read(root / 'dumps/arc/fighter/gamewatch/param/vl.prc'))
params = prc.as_dict(donor[prc.hash40('param_breath')])

# MOVZ/MOVK decoding, independent of the Rust bridge. The game's generated
# PRC decoder builds a hash, finds that key, then stores it at the listed offset.
def hash_at(address, register):
    value = 0
    for address in range(address, address + 24, 4):
        word = struct.unpack_from('<I', image, address)[0]
        if word & 31 != register:
            continue
        opcode = word & 0xff800000
        if opcode not in (0xd2800000, 0xf2800000):
            continue
        shift = ((word >> 21) & 3) * 16
        immediate = ((word >> 5) & 0xffff) << shift
        value = immediate if opcode == 0xd2800000 else (value & ~(0xffff << shift)) | immediate
    return value

fields = [
    ('pos_offset_x', 'pos_x', 0xa98210, 15, 0xa9829c, 0x118, 0.5),
    ('pos_offset_y', 'pos_y', 0xa982c0, 15, 0xa98350, 0x11c, 21.5),
    ('life', 'life', 0xa98374, 15, 0xa98438, 0x120, 34),
    ('move_interval', 'interval', 0xa9845c, 15, 0xa98520, 0x124, 7),
    ('speed_y', 'speed_y', 0xa98544, 15, 0xa985d0, 0x128, 8.5),
    ('scale_mul', 'scale', 0xa985f4, 14, 0xa98684, 0x12c, 1.9),
]
for key, rust, selector, register, store, offset, value in fields:
    assert hash_at(selector, register) == prc.hash40(key), key
    word = struct.unpack_from('<I', image, store)[0]
    assert (word >> 5) & 31 == 24, key  # destination object x24
    assert ((word >> 10) & 0xfff) * 4 == offset, key
    actual = params[prc.hash40(key)][1]
    assert struct.pack('<f', actual) == struct.pack('<f', value), key
    assert re.search(rf'\b{rust}: {value}[,\n]', source), key

signature = (project / 'plugin/src/breath_init_1304.bin').read_bytes()
assert signature == image[0x33fc110:0x33fc294]
assert struct.unpack_from('<I', image, 0x33fc13c)[0] == 0xf9434918
assert len(signature) == 0x184
print(json.dumps({'decoder_fields_verified': len(fields),
                  'constructor_sha256': hashlib.sha256(signature).hexdigest(),
                  'donor_params': {key: params[prc.hash40(key)][1] for key, *_ in fields}}, indent=2))
