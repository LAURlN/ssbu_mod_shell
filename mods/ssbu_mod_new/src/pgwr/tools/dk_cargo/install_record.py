"""Verify and record a user-authorized cargo installation. Does not write card.

Usage: install_record.py pre|post --card <mounted drive root>.
Run pre, canonical installer with frameworks OFF, then post. Offline tier B.
"""
import argparse
import datetime
import json
from pathlib import Path
from audit import ROOT, sha
from package import PACKAGE, BASE_PACKAGE, NRO, catalog, tree_hash

REPORT=ROOT/'evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_install'
MOD='ultimate/mods/pyra_gamewatch_reskin'
PLUGINS=Path(NRO).parent

def digest(path):return sha(path.read_bytes())
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def protected(card):
    files=[p for p in (card/PLUGINS).iterdir() if p.is_file() and p.name not in ['libpyra_gamewatch_reskin.nro','libone_slot_eff.nro']]
    files.extend(p for p in (card/'atmosphere/contents/01006A800016E000/exefs').rglob('*') if p.is_file())
    return {p.relative_to(card).as_posix():digest(p) for p in sorted(files)}

def run(phase,card):
    assert (card/PLUGINS).is_dir() and (card/MOD).is_dir() and (card/'atmosphere').is_dir()
    manifest=read(PACKAGE/'MANIFEST.json')
    version=manifest['task_version']
    expected_manifest={'0.1.0-test':'ad10838399da61f99b63f52b36ab58e0f1ed2980c9af4ffa957b3de24c9f339e',
        '0.1.1-test':'144d8a3ee2990a97a04230a860039bbe188a8e4384658b80443066f41da3014d'}
    assert digest(PACKAGE/'MANIFEST.json')==expected_manifest[version]
    files=catalog(card/MOD);nro=digest(card/NRO);guard=protected(card)
    REPORT.mkdir(exist_ok=True)
    if phase=='pre':
        assert not (REPORT/'PRE_INSTALL.json').exists(),'Preserve the original pre-install record'
        baseline=read(BASE_PACKAGE/'MANIFEST.json')
        assert files==baseline['mod_files'],'Card mod baseline drift'
        assert nro==digest(BASE_PACKAGE/NRO),'Card plugin baseline drift'
        assert digest(card/PLUGINS/'libone_slot_eff.nro')==digest(PACKAGE/PLUGINS/'libone_slot_eff.nro')
        assert any('libsmashline_plugin.nro' in p and h.startswith('5f4091ee') for p,h in guard.items())
        save(REPORT/'PRE_INSTALL.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'card_root':str(card),'baseline_package':BASE_PACKAGE.relative_to(ROOT).as_posix(),
             'file_count':len(files),'mod_files':files,'nro_sha256':nro,'protected_hashes':guard})
        print('PASS pre-install baseline:',len(files),'files; protected plugins + Skyline recorded')
        return
    before=read(REPORT/'PRE_INSTALL.json')
    assert str(card)==before['card_root']
    assert guard==before['protected_hashes'],'Protected plugins/Skyline changed'
    assert files==manifest['mod_files'] and tree_hash(files)==manifest['mod_tree_sha256']
    assert nro==manifest['nro_sha256']==digest(PACKAGE/NRO)
    target=manifest.get('cargo_target','builds/.cache/dk_cargo/runtime-target')
    built=ROOT/target/'aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro'
    assert digest(built)==nro
    for p,h in manifest['payload_files'].items():assert digest(card/p)==h,p
    assert not (card/(MOD+'.new')).exists(),'Staging folder remains'
    stamp=(ROOT/'src/pgwr/.last-sd-backup').read_text().strip()
    backup=ROOT/'evidence/sd-backups'/('sd-backup-'+stamp)
    assert backup.is_dir() and (backup/'card-mod-folder.tar').is_file()
    assert digest(backup/'plugins/libpyra_gamewatch_reskin.nro')==before['nro_sha256']
    record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'task':'dk_cargo-'+version,
       'installed':True,'runtime_verified':False,'evidence_tier':'B','card_root':str(card),
       'package':PACKAGE.relative_to(ROOT).as_posix(),'manifest_sha256':digest(PACKAGE/'MANIFEST.json'),
       'nro_sha256':nro,'nro_size':(card/NRO).stat().st_size,'mod_tree_sha256':tree_hash(files),
       'file_count':len(files),'backup':backup.relative_to(ROOT).as_posix(),'protected_hashes_unchanged':guard,
       'one_slot_eff_sha256':digest(card/PLUGINS/'libone_slot_eff.nro'),
       'pre_install_nro_sha256':before['nro_sha256'],'private_ids':'0x400..0x411',
       'source_patch_applied':False,'framework_installation':False,'mod_files':files}
    assert not (REPORT/'INSTALL.json').exists(),'Completed installation records are immutable'
    save(REPORT/'INSTALL.json',record)
    note=f'''# Cargo installation — 2026-10-03 — dk_cargo {version}

User explicitly requested installation. Installed the checked complete cargo
candidate over `{BASE_PACKAGE.relative_to(ROOT).as_posix()}` / shared 0.20.20. No shared version
bump, source integration patch or framework installation. Runtime unverified.

Package: `{record['package']}`.
NRO: `{nro}` ({record['nro_size']} bytes).
Mod tree: `{record['mod_tree_sha256']}` ({len(files)} files; sorted path/TAB/hash/LF).
Manifest: `{record['manifest_sha256']}`.
Helper unchanged: `{record['one_slot_eff_sha256']}`.
Backup: `{record['backup']}`; backed-up NRO matches the original card NRO.

Verified offline (tier B): package check and canonical installer dry run passed;
pre-card {before['file_count']}/{before['file_count']} baseline files and NRO matched; installer used backup/.new
staging/cmp/diff/sync with frameworks OFF. Post-card 5098/5098 files, no extra or
missing paths, and all packaged/built/card NRO hashes matched. Protected plugin
and Skyline executable hashes matched before/after. No game/emulator was run.
Machine records: PRE_INSTALL.json and INSTALL.json; installer output INSTALLER.txt.

Private status IDs 0x400..0x411; production allocation remains pending. Existing
Snake/Lucas/Ness/Incineroar changes remain included. Other pending changes excluded.
No capture/release/cleanup behavior claim follows from card byte verification.

Hardware checklist and pass/fail diagnostic guidance:
`evidence/2026-10-03_pgwr_dk_cargo/RESULT.md` (twelve checks), plus controlled
0.1.1 retest `evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test/RESULT.md` when applicable.
Send the log from boot: `sd:/ultimate/pgwr_dk_cargo_log.txt`, and any new report
under `sd:/atmosphere/crash_reports/`. First check c06/c07 pickup against vanilla
DK/Pyra controls before progressing to carry, throws, escape and cleanup.
'''
    (REPORT/'INSTALL.md').write_text(note,encoding='utf-8')
    path=ROOT/'CURRENT_INSTALL.md';text=path.read_text(encoding='utf-8')
    is_revision=version=='0.1.1-test'
    title='## dk_cargo — Codex — 2026-10-03 — READY: '+('controlled cargo-throw retest' if is_revision else 'private hardware test')
    assert text.count(title)==1
    title2=title.replace('READY:','INSTALLED:')
    old_status='**dk_cargo (2026-10-03, Codex): 0.1.1-test READY for controlled cargo-throw retest; NOT INSTALLED.**' if is_revision else '**dk_cargo (2026-10-03, Codex): READY for private hardware test; NOT INSTALLED, gameplay unverified.**'
    new_status='**dk_cargo (2026-10-03, Codex): '+version+' INSTALLED for hardware retest; corrected throws unverified.**'
    text=text.replace(title,title2,1).replace(old_status,new_status,1)
    if is_revision:
        text=text.replace('## dk_cargo 0.1.0-test on Gaogaen 0.3.0 / 0.20.20 — INSTALLED 2026-10-03 (current card state)',
            '## dk_cargo 0.1.0-test on Gaogaen 0.3.0 / 0.20.20 — INSTALLED 2026-10-03 (superseded by controlled retest above)',1)
    banner=f'''## dk_cargo {version} on Gaogaen 0.3.0 / 0.20.20 — INSTALLED 2026-10-03 (current card state)

User-authorized cargo test installation, 5098/5098 mod files verified; built/package/card
NRO `{nro}`. Tree `{record['mod_tree_sha256']}`.
Backup `{record['backup']}`. Protected plugins and Skyline byte-unchanged;
framework installation OFF. Shared version remains 0.20.20, private IDs 0x400..0x411.
Includes existing Snake/Lucas/Ness/Incineroar changes; other pending tasks excluded.
No game/emulator run. Record `{REPORT.relative_to(ROOT).as_posix()}/INSTALL.md`.
Hardware test/log from boot: `evidence/2026-10-03_pgwr_dk_cargo/RESULT.md`.

'''
    text=text.replace('# Collective install queue\n','# Collective install queue\n\n'+banner,1)
    text=text.replace('## gaogaen_throw_b 0.3.0 on 0.20.20 — INSTALLED 2026-10-03 (current card state)',
                      '## gaogaen_throw_b 0.3.0 on 0.20.20 — INSTALLED 2026-10-03 (superseded by cargo test above)',1)
    path.write_text(text,encoding='utf-8')
    path=ROOT/'projects/pgwr/STATUS.md';text=path.read_text(encoding='utf-8')
    old=old_status
    assert text.count(old)==1
    text=text.replace(old,new_status+'\n\n'
        +f'Card 5098/5098 files and NRO checked; frameworks unchanged. Install record:\n`{REPORT.relative_to(ROOT).as_posix()}/INSTALL.md`.\n',1)
    path.write_text(text,encoding='utf-8')
    path=ROOT/'projects/pgwr/CHANGELOG.md';text=path.read_text(encoding='utf-8')
    anchor='## 2026-10-03 — dk_cargo 0.1.1-test (controlled retest candidate)' if is_revision else '## 2026-10-03 — dk_cargo 0.1.0-test (Codex; READY for hardware test)'
    text=text.replace(anchor,anchor.replace('READY for hardware test','INSTALLED for hardware test').replace('controlled retest candidate','INSTALLED controlled retest')
        +'\n\n- User-authorized installation: 5098/5098 card files verified, NRO matches\n'
        +'  build/package, protected plugins/Skyline unchanged; backup and record in\n'
        +f'  `{REPORT.relative_to(ROOT).as_posix()}/INSTALL.md`. Gameplay unverified.',1)
    path.write_text(text,encoding='utf-8')
    print('PASS installed cargo:',len(files),'files; built/package/card NRO equal; protected plugins + Skyline unchanged')
    changed=[ROOT/'CURRENT_INSTALL.md',ROOT/'projects/pgwr/STATUS.md',ROOT/'projects/pgwr/CHANGELOG.md',
             ROOT/'src/pgwr/.last-sd-backup',Path(__file__)]
    if is_revision:
        changed.extend(ROOT/p for p in ['src/pgwr/tools/dk_cargo/README.md',
             'handbook/15_grabs_catch.md','handbook/graveyard.md','src/pgwr/tools/dk_cargo/crash_audit.py'])
    changed.extend(p for p in REPORT.rglob('*') if p.is_file() and p.name!='FILES.json')
    changed.extend(p for p in backup.rglob('*') if p.is_file())
    save(REPORT/'FILES.json',{'created_or_updated_workspace_files':{
        p.relative_to(ROOT).as_posix():digest(p) for p in sorted(changed)},
        'card_payload_inventory':'INSTALL.json mod_files plus package payload_files',
        'framework_changes':False,'runtime_verified':False})
    print('BACKUP',record['backup'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['pre','post']);parser.add_argument('--card',required=True)
    parser.add_argument('--version',choices=['0.1.0-test','0.1.1-test'],default='0.1.0-test')
    args=parser.parse_args()
    if args.version=='0.1.1-test':
        PACKAGE=ROOT/'builds/pgwr/dk_cargo-0.1.1-test'
        BASE_PACKAGE=ROOT/'builds/pgwr/dk_cargo-0.1.0-test'
        REPORT=ROOT/'evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test_install'
    run(args.phase,Path(args.card))
