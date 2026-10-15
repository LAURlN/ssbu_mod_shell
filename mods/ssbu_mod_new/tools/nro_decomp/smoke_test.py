"""Smoke test for tools/nro_decomp (offline, no Ghidra): flatten G&W's NRO and check the status table.

Expected values were measured 2026-09-29 on lua2cpp_gamewatch.nro sha256 7929eeae...b3ae (13.0.4).
Run: toolchains/py312/python.exe tools/nro_decomp/smoke_test.py
"""
import hashlib, sys
from pathlib import Path
here = Path(__file__).resolve().parent; sys.path.insert(0, str(here))
import nro_flatten, status_table

nro = here.parents[1] / 'dumps/arc/prebuilt/nro/release/lua2cpp_gamewatch.nro'
data = nro.read_bytes()
assert hashlib.sha256(data).hexdigest().startswith('7929eeaea7b01d0c'), 'different lua2cpp_gamewatch.nro'
img, meta = nro_flatten.flatten(data)
assert len(meta['labels']) == 579 and meta['text_end'] == 0x105000, (len(meta['labels']), hex(meta['text_end']))
rows = {(s, c): f for s, c, f in status_table.table(img, meta)}
want = {('FIGHTER_STATUS_KIND_SPECIAL_HI', 'LUA_SCRIPT_STATUS_FUNC_STATUS_MAIN'): 0xc6c0,
        ('FIGHTER_STATUS_KIND_SPECIAL_HI', 'LUA_SCRIPT_STATUS_FUNC_EXEC_STATUS'): 0x3b20,
        ('FIGHTER_GAMEWATCH_STATUS_KIND_SPECIAL_HI_FALL', 'LUA_SCRIPT_STATUS_FUNC_INIT_STATUS'): 0x4140,
        ('FIGHTER_GAMEWATCH_STATUS_KIND_SPECIAL_HI_CLOSE', 'LUA_SCRIPT_STATUS_FUNC_STATUS_END'): 0xdee0}
for k, v in want.items():
    assert rows.get(k) == v, (k, rows.get(k))
print('nro_decomp smoke test OK:', len(rows), 'status rows')
