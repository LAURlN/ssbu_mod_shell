"""Offline package/mapping/native audit and union controls; no game execution.

Usage: python -B src/pgwr/tools/loading_presentation/audit.py
Uses the already workspace-local Capstone install read-only.
"""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import package as p

EVIDENCE = p.ROOT / 'evidence/2026-10-03_pgwr_loading_presentation'
EVIDENCE.mkdir(parents=True, exist_ok=True)
manifest = json.loads((p.BASE.parents[2] / 'MANIFEST.json').read_text())
expected = manifest.get('mod_files', manifest.get('mod_file_hashes'))
assert expected is not None
if isinstance(expected, list):
    expected = {x['path']: x['sha256'] for x in expected}
actual = {f.relative_to(p.BASE).as_posix(): p.sha(f) for f in p.BASE.rglob('*') if f.is_file()}
for name, value in expected.items():
    if isinstance(value, dict): value = value['sha256']
    assert actual[name] == value, name
assert set(actual) == set(expected)
nro = p.BASE.parents[2] / manifest['nro_path']
assert p.sha(nro) == manifest['nro_sha256']
delta = p.OUT / 'delta'
shipped = {f.relative_to(delta).as_posix(): p.sha(f) for f in delta.rglob('*') if f.is_file()}
assert shipped == json.loads((p.OUT / 'MANIFEST.json').read_text())['mod_files']
assert set(shipped) == {p.DB, p.LAYOUT, *p.TARGETS}
final = actual | shipped
tree_hash = lambda entries: hashlib.sha256(''.join(f'{n}\t{h}\n' for n,h in sorted(entries.items())).encode()).hexdigest()
assert tree_hash(actual) == 'dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e'
# Unrelated concurrent name/layout changes survive the semantic union.
c,l = p.prc.read(p.BASE / p.DB), p.prc.read(p.GAME / p.LAYOUT)
name_row = p.row(c,'name_id',('str','elight_first'))
key = p.prc.hash40('n06_index')
name_row[1][:] = [(k,('u8',42) if k==key else v) for k,v in name_row[1]]
layout_row = p.row(l,'ui_chara_id',('hash',p.prc.hash40('ui_chara_flame_first')))
key2 = p.prc.hash40('chara_1_offset_x')
layout_row[1][:] = [(k,('float',123.0) if k==key2 else v) for k,v in layout_row[1]]
p.union(c,l)
assert dict(name_row[1])[key] == ('u8',42)
for r in p.rows(l):
    fields=dict(r[1])
    if fields.get(p.prc.hash40('ui_chara_id'))==('hash',p.prc.hash40('ui_chara_flame_first')):
        assert fields[key2] == ('float',123.0)
broken=copy.deepcopy(l)
r=next(r for r in p.rows(broken) if dict(r[1]).get(p.prc.hash40('chara_color'))==('u8',6)
       and dict(r[1]).get(p.prc.hash40('ui_chara_id'))==('hash',p.prc.hash40('ui_chara_flame_first')))
r[1][:]=[(k,('float',99.0) if k==p.prc.hash40('chara_3_0_scale') else v) for k,v in r[1]]
try: p.union(copy.deepcopy(c),broken)
except AssertionError: pass
else: raise AssertionError('layout conflict control missed')

# Inspect native category lookup and actual relocation-backed path table.
sys.path.insert(0,str(p.ROOT/'builds/.cache/gaogaen_throw_b/python'))
sys.path.insert(0,str(p.ROOT/'tools'))
from main_image import MainImage
main=MainImage(p.WORKSPACE/'gamedata/ssbu-13.0.4/main.bin')
data=main.data
assert struct.unpack_from('<I',data,0x1eea890)[0] == 0x320007e3 # mov alias: w3,#3
assert struct.unpack_from('<I',data,0x1eea89c)[0] == 0x944d5139 # bl 323ed80
pointer=main.ptr(0x5180998+3*8)
assert data[pointer:].split(b'\0')[0] == b'chara/chara_3/chara_3_'
assert data[0x426d44b:].split(b'\0')[0] == b'c%02d_index'
windows=[(0x1eea808,0xac),(0x1eea92c,0x28),(0x1eeaa20,0x24),
         (0x32384c0,0x1d4),(0x3239370,0x150),(0x32648c0,0x1cc),
         (0x3280910,0x1b0),(0x32643e0,0x260)]
text=[]
for a,size in windows:
    text.append(f'\nmain+{a:x}, size {size:x}')
    text.extend(f'{i.address:08x} {i.mnemonic} {i.op_str}' for i in main.disasm(a,size))
(EVIDENCE/'NATIVE.asm.txt').write_text('\n'.join(text)+'\n')
# A mapping matrix inferred from measured native call/branch and database rows.
matrix=[]
c,l=p.prc.read(delta/p.DB),p.prc.read(delta/p.LAYOUT)
for count in (2,4,5,8):
    for slot in (6,7):
        for starter in ('eflame','elight'):
            name=starter+('_first' if count<=4 else '_only')
            r=p.row(c,'name_id',('str',name));fields=dict(r[1])
            color=fields[p.prc.hash40(f'c{slot:02d}_index')][1]
            layout_rows=[r for r in p.rows(l) if dict(r[1]).get(p.prc.hash40('ui_chara_id'))==fields[p.prc.hash40('ui_chara_id')]
                         and dict(r[1]).get(p.prc.hash40('chara_color'))==('u8',color)]
            assert len(layout_rows)==1
            asset=f'ui/replace_patch/chara/chara_3/chara_3_{name}_{slot:02d}.bntx'
            assert asset in final
            assert color == (slot if starter=='eflame' else 0)
            matrix.append({'fighters':count,'costume':slot,'starter':starter,'asset':asset,'layout_color':color})
report={'tier':'B verified offline; runtime unverified','baseline_files_verified':len(actual),
        'baseline_tree_sha256':tree_hash(actual),'union_files':len(final),'union_tree_sha256':tree_hash(final),
        'changed':sorted(n for n,h in actual.items() if final[n]!=h),'added':sorted(set(final)-set(actual)),
        'preserved_existing_files':sum(final[n]==h for n,h in actual.items()),
        'main_sha256':hashlib.sha256(data).hexdigest(),'category_3_table_pointer':hex(pointer),
        'inherited_nro_sha256':p.sha(nro),
        'source_game_files':{f.relative_to(p.GAME).as_posix():p.sha(f) for f in p.GAME.rglob('*') if f.is_file()},
        'negative_layout_control':'PASS','concurrent_name_and_css_union_control':'PASS',
        'matrix':matrix,'delta':shipped}
layout_data=(p.GAME/'ui/layout/system/matchup/matchup/layout.arc').read_bytes()
assert all(f'set_panel_fighter_{n:02d}'.encode() in layout_data for n in range(8))
report['matchup_player_panes_verified'] = 8
reproduction=p.ROOT/'builds/pgwr/loading-presentation-reproduction/delta'
assert {f.relative_to(reproduction).as_posix():p.sha(f) for f in reproduction.rglob('*') if f.is_file()} == shipped
report['reproduction_four_file_hashes'] = 'PASS'
(EVIDENCE/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['matrix','source_game_files']},indent=2))
