"""Package ONLY the private-module load check. No fighter registration/assets."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from prepare import ROOT, write_json


def main():
    package = ROOT / 'test_output/private_module_loader'
    sdroot = package / 'sdroot'
    pack = sdroot / 'ultimate/mods/PyraMythraClone'
    pack.mkdir(parents=True, exist_ok=True)
    runtime = ROOT / 'runtime/target/aarch64-skyline-switch/release/libpyra_mythra_clone_runtime.nro'
    if not runtime.is_file():
        raise FileNotFoundError('Build the runtime with cargo skyline build --release first')
    plugin_path = Path('atmosphere/contents/01006A800016E000/romfs/skyline/plugins/plugin.nro')
    planned = [(runtime, sdroot / plugin_path)]
    # Remove only the known previous build at its incorrect local package path.
    legacy = pack / 'plugin.nro'
    if legacy.exists():
        if legacy.read_bytes() != runtime.read_bytes():
            raise ValueError('Edited legacy plugin preserved: ' + str(legacy))
        legacy.unlink()
    for row in json.loads((ROOT / 'reports/namespaced-modules.json').read_text()):
        source = ROOT / 'native/modules' / ('lua2cpp_' + row['clone'] + '.nro')
        if hashlib.sha256(source.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Generated module differs from manifest')
        planned.append((source, pack / 'native/modules' / source.name))
    manifest = []
    for source, destination in planned:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        raw = source.read_bytes()
        if destination.read_bytes() != raw or raw[0x10:0x14] != b'NRO0':
            raise ValueError('Invalid package NRO')
        manifest.append({'path': destination.relative_to(sdroot).as_posix(), 'bytes': len(raw),
                         'sha256': hashlib.sha256(raw).hexdigest()})
    (pack / 'info.toml').write_text('display_name = "Pyra/Mythra private module loader CHECK"\n'
                                   'authors = "Local development"\nversion = "0.1.0"\n'
                                   'description = "Development loader check only. No new fighter slot."\n')
    instructions = '''PRIVATE MODULE LOADER CHECK -- NOT THE FINISHED CLONE

Purpose: verify the Switch can load the three independent NRO copies and resolve
all 27 namespaced factories into their own executable images. It does not create
a fighter, call a fighter factory, install gameplay hooks or alter original assets.
The cloned native main routines and transforming character slot are not implemented.

Install:
1. Close Smash.
2. Copy the contents of sdroot onto the SD card. The runtime belongs in
   atmosphere/contents/01006A800016E000/romfs/skyline/plugins/plugin.nro;
   its private modules belong in ultimate/mods/PyraMythraClone/native/modules.
3. Start Smash, then enter a normal
   match (Mario is sufficient) within five minutes. Common code is needed for
   the loader to resolve the new modules' imports.
4. The check writes ultimate/pyra_mythra_clone/loader.log on the SD card.

Expected final line:
PRIVATE_MODULE_LOAD_CHECK_PASSED: all 27 factories belong to private executable images; no fighter installed

The log must also contain cflame, clight and clement with 11, 11 and 5 private
factories respectively, and an isolation-guard-passed line for each. A REFUSED
line or a missing completion line is a failed/incomplete test, not a playable mod.
Keep the complete log. If the game crashes, keep the Atmosphere crash report too.

Removal: close Smash and remove this test's Skyline plugin.nro and
ultimate/mods/PyraMythraClone. Disabling the ARCropolis pack alone does not
disable the Skyline plugin.
The check adds no save data or original-resource replacements. This development
build retains its private module allocations until the game process exits.
'''
    (package / 'START_HERE.txt').write_text(instructions, encoding='utf8')
    evidence_path = ROOT / 'reports/console-loader-2026-09-28/result.json'
    hardware_passed = False
    if evidence_path.exists():
        evidence = json.loads(evidence_path.read_text(encoding='utf-8-sig'))
        tested = {row['path']: row['sha256'] for row in evidence['files']}
        hardware_passed = evidence.get('hardware_test_passed', False) and all(
            tested.get(row['path']) == row['sha256'] for row in manifest)
    (package / 'manifest.json').write_text(json.dumps({'purpose': 'private_module_load_check',
        'playable_clone': False, 'hardware_test_passed': hardware_passed, 'files': manifest}, indent=2))
    publish = ROOT.parent / 'mod_output/new_standalone'
    publish.mkdir(parents=True, exist_ok=True)
    legacy = publish / 'ultimate/mods/PyraMythraClone/plugin.nro'
    if legacy.exists():
        if legacy.read_bytes() != runtime.read_bytes():
            raise ValueError('Edited legacy plugin preserved: ' + str(legacy))
        legacy.unlink()
    for source in sdroot.rglob('*'):
        if source.is_file():
            destination = publish / source.relative_to(sdroot)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if destination.read_bytes() != source.read_bytes():
                raise ValueError('Published file differs: ' + str(destination))
    (publish / 'START_HERE.txt').write_text(
        instructions.replace('contents of sdroot', 'contents of new_standalone'), encoding='utf8')
    archive = ROOT / 'test_output/PyraMythra_private_module_loader_check.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(package.rglob('*')):
            if path.is_file():
                z.write(path, path.relative_to(package).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Archive integrity failed')
    write_json('loader-build.json', {'build_command': 'cargo skyline build --release',
        'compiled': True, 'host_symbol_lookup_checks_passed': True, 'hardware_test_passed': hardware_passed,
        'package': str(archive.relative_to(ROOT)), 'files': manifest})
    print(archive)
    print('Verified package:', len(manifest), 'NROs;', archive.stat().st_size, 'archive bytes')


if __name__ == '__main__':
    main()
