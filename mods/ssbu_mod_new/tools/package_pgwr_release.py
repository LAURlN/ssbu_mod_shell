"""Stage a versioned pgwr NRO and measure the complete release (v1.3.0).

Uses builds/.cache only. Checks costume declarations, owned motion/script
bindings, copied article hashes, effect merge proofs and sound relocations.
Smoke test: run --version <version>, then --version <version> --check.
This records offline evidence; console behavior requires a separate test.
1.1.0 (2026-09-30): `--scope` states what the release is for (was fixed to 0.18.0's text);
the up-B audit tools are hashed with the sources.
1.3.0 (2026-10-02): `--skip-donor-checks` runs the package checks that do not need the
ArcExplorer export, for the case where dumps/arc exists but is empty. Only the two
donor motion-entry comparisons are skipped, the omission is printed and recorded in
MANIFEST.json as "donor_checks", and --check refuses a manifest that claims more.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = Path('atmosphere/contents/01006A800016E000/romfs/skyline/plugins')
NRO = 'libpyra_gamewatch_reskin.nro'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(folder):
    files = {p.relative_to(folder).as_posix(): sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    digest = hashlib.sha256(''.join(f'{value}  ./{name}\n' for name, value in files.items()).encode()).hexdigest()
    return files, digest


def validate(package, version, snake=False, donor_checks=True):
    """Check the packaged mod tree. `donor_checks=False` skips only the two
    comparisons that read the ArcExplorer export (dumps/arc), which is empty in
    this workspace; everything else - owned clips, config declarations, handler
    registrations, the effect-merge hash chain, article hashes, sound banks
    including Snake's tones - still runs. The caller must pass
    --skip-donor-checks explicitly and the manifest records the omission.
    """
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    import build_hero_neutral_b_assets as hero
    mod = package / 'ultimate/mods/pyra_gamewatch_reskin'
    assert tomllib.loads((mod / 'info.toml').read_text())['version'] == version
    config = json.loads((mod / 'config.json').read_text())['new-dir-files']
    code = (ROOT / 'src/pgwr/plugin/src/mythra/hero_neutral_b/acmd.rs').read_text()
    registrations = {hero.base.hash40(name) for name in re.findall(r'_acmd\("([^"]+)"', code)}
    donor = {}
    if donor_checks:
        _, donor = hero.checked_inputs()
    else:
        print('WARNING: --skip-donor-checks: dumps/arc is empty, so the Hero '
              'neutral-B motion entries are NOT compared against the donor export. '
              'This is recorded in MANIFEST.json.')
    # The motion-list tail stores expression, sound, effect in that order.
    for slot in ('c06', 'c07'):
        _, _, entries = hero.base.parse_mlist(mod / f'fighter/elight/motion/body/{slot}/motion_list.bin')
        for original, owned, clip in hero.motions():
            entry = entries[hero.base.hash40(owned)]
            if donor_checks:
                assert entry['raw'] == hero.entry_bytes(donor[hero.base.hash40(original)], owned, clip)
            assert (mod / f'fighter/elight/motion/body/{slot}/{clip}').is_file()
            for category in ('game', 'effect', 'sound', 'expression'):
                donor_script = category + '_' + original.replace('_', '')
                if f'fn {donor_script}(' in code:
                    assert hero.base.hash40(category + '_' + owned.replace('_', '')) in registrations
        effects = json.loads((package / f'generated_effects/ef_elight_{slot}.merge.json').read_text())
        assert effects['geometry_texture_shader_payloads_checked']
        final = effects['output_sha256']
        side_b = package / f'generated_effects/ef_elight_{slot}_side_b.merge.json'
        if side_b.is_file():  # Hero side-B merges on top of the neutral-B bank
            chained = json.loads(side_b.read_text())
            assert chained['recipient_sha256'] == final and chained['geometry_texture_shader_payloads_checked']
            final = chained['output_sha256']
        assert final == sha(mod / f'effect/fighter/elight/ef_elight_{slot}.eff')
        assert len(effects['resource_names']) == 16
    assets = json.loads((package / 'hero_neutral_b_assets.json').read_text())
    assert len(assets['motions']) == 26 and len(assets['article_files']) == 88
    for entry in assets['article_files']:
        assert sha(mod / entry['path']) == entry['sha256']
        slot = Path(entry['path']).parts[4]
        assert entry['path'] in config['fighter/elight/' + slot]
    for entry in assets['motions']:
        path = f"fighter/elight/motion/body/{entry['slot']}/{entry['clip']}"
        assert sha(mod / path) == entry['sha256'] and path in config['fighter/elight/' + entry['slot']]
    sounds = json.loads((package / 'hero_neutral_b_sound.json').read_text())
    assert sum(bank['rebased_group_links'] for bank in sounds['banks']) == 102
    if snake:
        import build_snake_neutral_b_assets as sn
        import merge_snake_neutral_b_sound as ss
        assert sn.LOWER_RUNTIME_TRANSLATED
        report = json.loads((package / 'snake_neutral_b_assets.json').read_text())
        assert len(report['motions']) == 58 and len(report['pin_files']) == 152
        inputs = sn.checked_inputs() if donor_checks else {}
        for slot in ('c06', 'c07'):
            _, _, entries = hero.base.parse_mlist(mod / f'fighter/eflame/motion/body/{slot}/motion_list.bin')
            for original, owned, clip in sn.motions():
                if donor_checks:
                    assert entries[sn.base.hash40(owned)]['raw'] == sn.entry_bytes(inputs[original][0], owned, clip)
        for row in report['motions']:
            path = f"fighter/eflame/motion/body/{row['slot']}/{row['clip']}"
            assert sha(mod / path) == row['sha256']
            assert path in config['fighter/eflame/' + row['slot']]
        for row in report['pin_files']:
            assert sha(mod / row['path']) == row['sha256']
            slot = Path(row['path']).parts[4]
            assert row['path'] in config['fighter/eflame/' + slot]
        sound = json.loads((package / 'snake_neutral_b_sound.json').read_text())
        assert sound['sequence_table_present']
        # Later merges (R.O.B. dtilt) append to the same banks and sqb, so the final files are
        # checked against the last merge's record and Snake's tones must still be present.
        # The last merge in the chain wins: Snake up tilt appends after the R.O.B. dtilt.
        later = next((package / name for name in ('snake_uptilt_sound.json', 'robot_dtilt_sound.json')
                      if (package / name).is_file()), None)
        chained = json.loads(later.read_text()) if later else None
        for bank in sound['banks']:
            assert set(bank['appended_names']) == ss.REQUIRED
            path = mod / f"sound/bank/fighter/se_eflame_{bank['slot']}"
            if chained is None:
                for ext, digest in bank['output_hashes'].items():
                    assert sha(path.with_suffix(ext)) == digest
            else:
                import merge_hero_neutral_b_sound as codec
                names = {n.lower() for n, _ in codec.audio_read(path.with_suffix('.nus3audio').read_bytes())}
                assert ss.REQUIRED <= names, 'a later merge dropped a Snake tone'
        if chained is None:
            assert sha(mod / 'sound/sequence/fighter/eflame.sqb') == sound['sqb_sha256']
        else:
            for bank in chained['banks']:
                path = mod / f"sound/bank/{bank['folder']}/{bank['recipient']}"
                for ext, digest in bank['output_hashes'].items():
                    assert sha(path.with_suffix(ext)) == digest
            assert sha(mod / 'sound/sequence/fighter/eflame.sqb') == chained['sqb_sha256']
    return mod


def _manifest_cache_name(package: Path) -> str:
    """The `cargo_target` a previously written manifest recorded, if any."""
    man = package / 'MANIFEST.json'
    if not man.is_file():
        return ''
    try:
        return str(json.loads(man.read_text(encoding='utf-8')).get('cargo_target') or '')
    except (ValueError, OSError):
        return ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--snake-neutral-b', action='store_true', help='validate Snake resources and use its isolated cache')
    parser.add_argument('--hero-side-b', action='store_true', help='record the hero-side-b Cargo feature')
    parser.add_argument('--cargo-target', help='cargo target dir (name under builds/.cache or absolute) holding the NRO')
    parser.add_argument('--skip-donor-checks', action='store_true',
                        help='skip the two motion-entry comparisons that read the ArcExplorer '
                             'export (dumps/arc is empty in this workspace); recorded in the manifest')
    parser.add_argument('--scope', default='Hero neutral-B without mana on Mythra c06/c07, '
                        'including staged 0.17.0 sword/trail changes at user request.')
    args = parser.parse_args()
    assert re.fullmatch(r'\d+\.\d+\.\d+', args.version)
    cargo = tomllib.loads((ROOT / 'src/pgwr/plugin/Cargo.toml').read_text())
    assert cargo['package']['version'] == args.version
    package = ROOT / 'builds/pgwr' / args.version
    mod = validate(package, args.version, args.snake_neutral_b, not args.skip_donor_checks)
    # Which cargo target dir holds the NRO for this package. An explicit
    # --cargo-target wins; otherwise a `cargo_target` recorded in an existing
    # manifest is honoured, so a package built in an isolated cache keeps being
    # packaged from that same cache. Falls back to the feature-derived name.
    # (This exists because two agents sharing one cache silently packaged each
    # other's stale NRO; see CURRENT_INSTALL.md 0.20.14.)
    cache_name = (args.cargo_target
                  or _manifest_cache_name(package)
                  or ('pgwr-snake-target' if args.snake_neutral_b else 'pgwr-target'))
    cache = cache_name if os.path.isabs(cache_name) else ROOT / 'builds/.cache' / cache_name
    built = cache / 'aarch64-skyline-switch/release' / NRO
    staged = package / PLUGINS / NRO
    if not args.check:
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built, staged)
        shutil.copyfile(ROOT / 'src/pgwr/build-record.json', package / 'asset_build_record.json')
    assert sha(built) == sha(staged), 'packaged NRO differs from built NRO'
    files, digest = tree(mod)
    manifest_path = package / 'MANIFEST.json'
    if args.check:
        record = json.loads(manifest_path.read_text())
        assert record['artifacts']['reskin_nro']['sha256'] == sha(built)
        assert record['artifacts']['mod_tree']['tree_sha256'] == digest
        assert record['artifacts']['mod_tree']['files'] == len(files)
        # The manifest must name the cache this package was actually built in, or
        # install-to-card.sh falls back to the feature-derived default and can pick
        # up another agent's stale NRO. See CURRENT_INSTALL.md 0.20.14.
        assert record.get('cargo_target') == cache_name, (
            f'manifest records cargo_target {record.get("cargo_target")!r}, '
            f'but this check read the NRO from {cache_name!r}')
        if args.skip_donor_checks:
            assert str(record.get('donor_checks', '')).startswith('SKIPPED'), (
                'this check skipped the donor comparisons but the manifest records them complete')
    else:
        rust_info = json.loads((cache / '.rustc_info.json').read_text())
        rust_version = next(v['stdout'].splitlines()[0] for v in rust_info['outputs'].values()
                            if v.get('stdout', '').startswith('rustc '))
        source_files = [p for p in (ROOT / 'src/pgwr/plugin/src').rglob('*') if p.is_file()]
        source_files += [ROOT / p for p in ('src/pgwr/plugin/Cargo.toml', 'src/pgwr/plugin/Cargo.lock',
                         'src/pgwr/build.py', 'src/pgwr/build-plugin.sh', 'src/pgwr/install-to-card.sh')]
        source_files += list((ROOT / 'src/pgwr/tools').glob('*.py'))
        source_files += [p for p in (ROOT / 'tools').glob('*.py')
                         if 'hero' in p.name or 'snake' in p.name or p.name in ('package_pgwr_release.py', 'audit_event_slots.py',
                                                           'main_image.py', 'maindesc.py',
                                                            'audit_mflip_capture_native.py', 'gen_mflip_capture_data.py',
                                                            'audit_pgwr_svc_guard.py', 'summarise_pgwr_capture_log.py',
                                                            'audit_diddy_special_lockout.py')]
        record = {'project': 'pgwr', 'version': args.version, 'built_on': '2026-09-30',
                  'game_version': '13.0.4', 'git': None, 'git_note': 'No git repository; source hashes pin this release.',
                  'toolchain': {'cargo_skyline': '3.5.0', 'rustc': rust_version,
                                'rustup_toolchain': 'skyline-v3', 'target': 'aarch64-skyline-switch',
                                'profile': 'release', 'offline': True, 'python': '3.12',
                                'effect_library_commit': 'd5491138d645221ec92189eeff3ded8c43fd0a1a'},
                  'scope': args.scope,
                  'features': (['snake-neutral-b'] if args.snake_neutral_b else [])
                              + (['hero-side-b'] if args.hero_side_b else []),
                  'cargo_target': cache_name,
                  'donor_checks': ('complete' if not args.skip_donor_checks else
                                   'SKIPPED: dumps/arc empty, Hero neutral-B and Snake motion '
                                   'entries not compared against the donor export in this run'),
                  'hardware_validated': False,
                  'artifacts': {'reskin_nro': {'path': staged.relative_to(ROOT).as_posix(), 'sha256': sha(staged), 'bytes': staged.stat().st_size},
                                'mod_tree': {'path': mod.relative_to(ROOT).as_posix(), 'files': len(files), 'tree_sha256': digest},
                                'one_slot_eff': {'sha256': sha(package / PLUGINS / 'libone_slot_eff.nro')}},
                  'tree_hash_definition': 'sha256 of sorted sha256 + two spaces + ./relative/path + newline records',
                  'source_hashes': {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(source_files)},
                  'snake_evidence_hashes': {p.relative_to(ROOT).as_posix(): sha(p)
                      for p in sorted((ROOT / 'refs/snake_grenade').rglob('*'))
                      if args.snake_neutral_b and p.is_file() and p.suffix in ('.json', '.c', '.asm')},
                  # The Little Mac forward-smash donor extraction and its own audit
                  # output. Pinned for the same reason as the Snake set: the port's
                  # clips, motion entries, banks and effect all come from these bytes.
                  'littlemac_evidence_hashes': {p.relative_to(ROOT).as_posix(): sha(p)
                      for p in sorted((ROOT / 'refs/littlemac_attack_s4').rglob('*'))
                      if p.is_file() and p.suffix in ('.json',)},
                  'mod_file_hashes': files}
        manifest_path.write_text(json.dumps(record, indent=2) + '\n')
    print(f'PASS: {args.version}; {len(files)} mod files; NRO {sha(staged)}; tree {digest}')


if __name__ == '__main__':
    main()
