"""Flatten an uncompressed Switch NRO (e.g. `lua2cpp_<fighter>.nro`) into a raw image for Ghidra's BinaryLoader.

Usage: python nro_flatten.py <in.nro> <out.bin> <out_labels.json>

* MOD0 offsets are relative to the MOD0 header itself (file offset = u32 at NRO+4). `.dynamic` gives
  symtab/strtab/rela/jmprel. (The older `src/pgwr/tools/nro_syms.py` docstring missed this.)
* RELATIVE (1027) relocations are written in place; every *imported* symbol gets a 16-byte `ret` stub
  in an extern region at ext_base (file size rounded up to 0x10000; G&W: 0x160000), and its JUMP_SLOT / GLOB_DAT / ABS64 slots point there.
* labels.json maps address -> mangled name for exported symbols and stubs; `ghidra_scripts/NroLabels.py` applies it.
Load in Ghidra with `-processor AARCH64:LE:64:v8A -loader BinaryLoader -loader-baseAddr 0` (see run_ghidra.sh).
"""
import struct, sys, json

R_ABS64, R_GLOB_DAT, R_JUMP_SLOT, R_RELATIVE = 257, 1025, 1026, 1027


def parse(d):
    mod0 = struct.unpack_from('<I', d, 4)[0]
    assert d[mod0:mod0 + 4] == b'MOD0', 'no MOD0'
    dyn = mod0 + struct.unpack_from('<i', d, mod0 + 4)[0]
    tags = {}; i = dyn
    while True:
        t, v = struct.unpack_from('<qQ', d, i); i += 16
        if t == 0: break
        tags.setdefault(t, v)
    symtab, strtab = tags[6], tags[5]
    syms = []
    for k in range((strtab - symtab) // 24):
        nm, info, oth, shn, val, sz = struct.unpack_from('<IBBHQQ', d, symtab + 24 * k)
        e = d.index(b'\0', strtab + nm)
        syms.append((d[strtab + nm:e].decode('latin1'), info, shn, val, sz))
    rel = []
    for off, sz in ((tags[7], tags[8]), (tags[0x17], tags[2])):
        rel += [struct.unpack_from('<QQq', d, off + 24 * j) for j in range(sz // 24)]
    text_end = struct.unpack_from('<I', d, 0x10 + 0x10 + 4)[0]  # segment[0].size
    return syms, rel, text_end


def flatten(d):
    syms, rel, text_end = parse(d)
    ext_base = (len(d) + 0xffff) & ~0xffff
    img = bytearray(d) + bytearray(ext_base - len(d))
    ext = bytearray(); labels = {}; extaddr = {}

    def ext_for(k):
        if k not in extaddr:
            a = ext_base + len(ext); ext.extend(struct.pack('<IIII', 0xd65f03c0, 0, 0, 0))
            extaddr[k] = a; labels[hex(a)] = syms[k][0]
        return extaddr[k]
    for s in syms:
        if s[2] != 0 and s[0]: labels[hex(s[3])] = s[0]
    for off, info, add in rel:
        typ, k = info & 0xffffffff, info >> 32
        if typ == R_RELATIVE: val = add
        else:
            s = syms[k]
            val = (s[3] if s[2] != 0 else ext_for(k)) + (add if typ == R_ABS64 else 0)
        struct.pack_into('<Q', img, off, val)
    return bytes(img + ext), {'labels': labels, 'text_end': text_end, 'ext_base': ext_base,
                              'ext_size': len(ext)}


if __name__ == '__main__':
    src, out_bin, out_json = sys.argv[1:4]
    img, meta = flatten(open(src, 'rb').read())
    open(out_bin, 'wb').write(img); json.dump(meta, open(out_json, 'w'), indent=0)
    print(len(meta['labels']), 'labels', hex(len(img)))
