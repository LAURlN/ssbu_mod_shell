"""List the donor ACMD script paths recorded in the rubendal/ssbu tree index.

ssbu.json is not script content. It is a GitHub tree listing - path, size and
blob sha for every file in rubendal/ssbu - which is the repo the acmd .txt dumps
in references/ come from (references/AttackAirF_gamewatch.txt and friends).

monkey_flip.rs cites references/diddy_specials/donor_acmd/SpecialAirSJump.txt as
its pinned donor. That file is not in this workspace and never was, so the CATCH
geometry, its argument order and the CLUNG_DIDDY argument are unverifiable
against anything local. This prints the canonical upstream path, size and blob
sha for Diddy's Monkey Flip scripts, so the real donor can be fetched instead of
remembered.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / 'references' / 'diddy_specials' / 'source_audit' / 'ssbu.json'

data = json.loads(TREE.read_text(encoding='utf-8', errors='replace'))
print('top-level keys:', list(data.keys()) if isinstance(data, dict) else type(data).__name__)
entries = data['tree'] if isinstance(data, dict) and 'tree' in data else data
print('tree entries:', len(entries))
print('entry keys:', sorted(entries[0].keys()))
print()

diddy = [e for e in entries if '/diddy/' in e.get('path', '')]
diddy_txt = [e for e in diddy if e['path'].endswith('.txt')]
print(f'diddy entries: {len(diddy)}   diddy .txt entries: {len(diddy_txt)}')
print()

print('--- every diddy .txt the tree records ---')
for name in sorted({Path(e['path']).name for e in diddy_txt}):
    print('  ' + name)
print()

print('--- diddy SpecialS* entries, path + size + blob sha ---')
for e in diddy_txt:
    if 'SpecialS' in e['path']:
        print(f"  {e.get('size')}\t{e['path']}\t{e.get('sha')}")
