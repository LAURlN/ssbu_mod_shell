"""Verify the installed pgwr card against a versioned manifest (1.1.0).

Usage/smoke test: toolchains/py312/python.exe tools/verify_pgwr_card.py --version 0.20.5
Reads the card location from paths.toml, checks Switch directory contents,
compares every mod file and packaged/built/card NRO, and checks protected hashes
when an install record is supplied. No writes and no console behavior claim.
"""
import argparse
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from package_pgwr_release import PLUGINS, NRO, sha, tree


def verify(version, record=None):
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    card = Path(cfg['switch']['sd_drive'] + '/')
    assert (card / PLUGINS).is_dir() and (card / 'ultimate/mods').is_dir(), 'Not a Switch card'
    package = ROOT / 'builds/pgwr' / version
    manifest = json.loads((package / 'MANIFEST.json').read_text())
    cache = 'pgwr-snake-target' if 'snake-neutral-b' in manifest.get('features', []) else 'pgwr-target'
    built = ROOT / 'builds/.cache' / cache / 'aarch64-skyline-switch/release' / NRO
    expected = manifest['artifacts']['reskin_nro']['sha256']
    assert sha(card / PLUGINS / NRO) == sha(package / PLUGINS / NRO) == sha(built) == expected
    files, digest = tree(card / 'ultimate/mods/pyra_gamewatch_reskin')
    assert files == manifest['mod_file_hashes'], 'Installed mod files differ'
    assert digest == manifest['artifacts']['mod_tree']['tree_sha256']
    assert sha(card / PLUGINS / 'libone_slot_eff.nro') == manifest['artifacts']['one_slot_eff']['sha256']
    if record:
        installed = json.loads((ROOT / record).read_text())
        assert installed['version'] == version and installed['reskin_nro_sha256'] == expected
        for name, expected_hash in installed['protected_plugin_sha256_unchanged'].items():
            assert sha(card / PLUGINS / name) == expected_hash, name
    return {'version': version, 'nro_sha256': expected, 'mod_files': len(files),
            'tree_sha256': digest, 'hardware_validated': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', required=True)
    p.add_argument('--record', help='Workspace-relative installation record')
    args = p.parse_args()
    print(json.dumps(verify(args.version, args.record), indent=2))


if __name__ == '__main__':
    main()
