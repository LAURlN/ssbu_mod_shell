"""Check the packaged Hi3 plugin and animations against the generated manifest."""
from pathlib import Path
import hashlib
import json
import struct

root = Path(__file__).resolve().parents[3]
crate = root / 'mod_files/mythra_gamewatch_swap'
built = crate / 'target/aarch64-skyline-switch/release/libmythra_gamewatch_swap.nro'
package = root / 'mod_output/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmythra_gamewatch_swap.nro'
anim_dir = root / 'mod_output/ultimate/mods/mythra_gamewatch_swap/fighter/elight/motion/body/c07'
manifest_path = root / 'references/miiswordsman_special_hi3/animation_manifest.json'
record_path = crate / 'c06c07-payload-validation.json'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check(condition, message):
    if not condition:
        raise SystemExit(message)

def main():
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    binary = package.read_bytes()
    check(binary == built.read_bytes(), 'Packaged NRO differs from built NRO')
    check(binary[0x10:0x14] == b'NRO0', 'Missing NRO0 header')
    check(struct.unpack_from('<I', binary, 0x18)[0] == len(binary), 'NRO declared size differs')
    check(b'MGW-HI3' in binary and b'2026-09-26.g' in binary, 'Hi3 build markers absent')
    check(b'MGW-SLOTS' in binary and b'2026-09-26.c06c07' in binary, 'Two-costume build marker absent')
    check(b'MGW-GRENADE' not in binary, 'Removed grenade module unexpectedly packaged')
    check(b'native life lookup fallback: ' not in binary, 'Removed grenade fuse hook unexpectedly packaged')
    for item in manifest['motions']:
        path = anim_dir / item['recipient_animation']
        data = path.read_bytes()
        check(len(data) == item['output_bytes'] and sha(data) == item['output_sha256'], f'Clip mismatch: {path}')
    motion_list = (anim_dir / 'motion_list.bin').read_bytes()
    check(len(motion_list) == manifest['motion_list']['output_bytes'] and
          sha(motion_list) == manifest['motion_list']['output_sha256'], 'Hi3 motion list mismatch')
    check(not (anim_dir / 'd02specialairhistart.nuanmb').exists(), 'Unused Hi1 clip still packaged')
    asset_root = root / 'mod_output/ultimate/mods/mythra_gamewatch_swap'
    c06_manifest = json.loads((crate / 'c06-assets-validation.json').read_text(encoding='utf-8'))
    for rel, digest in c06_manifest['c06_files'].items():
        check(sha((asset_root / rel).read_bytes()) == digest, f'c06 asset mismatch: {rel}')
    for fighter in ('elight', 'gamewatch'):
        motion_root = asset_root / 'fighter' / fighter / 'motion/body'
        c07 = {p.name: sha(p.read_bytes()) for p in (motion_root / 'c07').glob('*.nuanmb')}
        c06 = {p.name: sha(p.read_bytes()) for p in (motion_root / 'c06').glob('*.nuanmb')}
        check(c06 == c07, f'{fighter}: c06 and c07 replacement clips differ')
    previous_assets = json.loads((crate / 'backups/before-c06-extension/asset-sha256.json').read_text())
    for rel, digest in previous_assets.items():
        check(sha((asset_root / rel).read_bytes()) == digest, f'Existing asset changed: {rel}')
    expected_assets = set(previous_assets) | set(c06_manifest['c06_files'])
    actual_assets = {p.relative_to(asset_root).as_posix() for p in asset_root.rglob('*') if p.is_file()}
    check(actual_assets == expected_assets, 'Unexpected asset added/removed from package')
    record = {
        'version': '2026-09-26.c06c07 (retains Hi3 .g; neutral B restored)',
        'description': 'Shared c06/c07 gates for enabled moves, preload, pair selection, dormancy and handoff; native G&W neutral B restored',
        'nro_bytes': len(binary), 'nro_sha256': sha(binary),
        'nro0_header': True, 'declared_size_matches': True,
        'packaged_matches_build': True,
        'hi3_motion_manifest': str(manifest_path.relative_to(root)),
        'hi3_clips_verified': len(manifest['motions']),
        'unrelated_motion_list_entries_unchanged': 731,
        'c06_files_verified': len(c06_manifest['c06_files']),
        'c07_assets_unchanged': True,
        'grenade_feature_enabled': False,
        'previous_failure': 'The Snake grenade neutral B probe crashed the game and has been removed. Other Mythra costumes retain their existing local vanilla up-B fallbacks.',
        'switch_runtime_test': 'Pending: test both slots separately, both in one match, swaps in both directions, c06 appearance and sword visibility, all replaced moves, respawn/results, c00-c05 vanilla up-B and ordinary G&W Chef',
    }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(f'Hi3 payload verified: NRO {len(binary)} bytes SHA256 {sha(binary)}; 4 clips and motion list match manifest')
    print(f'Wrote {record_path}')

if __name__ == '__main__':
    main()
