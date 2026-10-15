"""Measure the two message-key constants with lua53-inspect's own parser (tier B).

The task prompt says both keys are 29 characters; this prints the measured length
and the on-disk extent of each stored string so that figure is checked, not trusted.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[4]
TOOL = ROOT / "mods/mii_customizer/tools/lua53-inspect/lua53_inspect.py"
SRC = ROOT / ("gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/"
              "make_mii_special_actor.lc")

spec = importlib.util.spec_from_file_location("lua53_inspect", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

raw = SRC.read_bytes()
header, proto = mod.load_chunk(raw)

for path, index in [("main.p2", 7), ("main.p14", 2)]:
    p = mod.find_proto(proto, path)
    k = p.constants[index]
    text = k.value
    size_bytes = 8 if k.long_form else 1
    body = len(text.encode())
    # k.offset is the size byte; the string ends after body bytes plus the NUL
    end = k.offset + size_bytes + body + 1
    on_disk = raw[k.offset + size_bytes:end - 1].decode()
    print(f"{path} K[{index}]")
    print(f"  text={text!r}")
    print(f"  chars={len(text)} utf8_bytes={body} long_form={k.long_form}")
    print(f"  tag_offset=0x{k.tag_offset:x} size_byte_offset=0x{k.offset:x} "
          f"first_text_byte=0x{k.offset + size_bytes:x} end=0x{end:x}")
    print(f"  bytes_on_disk_match_text={on_disk == text}")
    print(f"  uses={[(i.pc, m) for i, m in mod.const_uses(p, index)]}")
