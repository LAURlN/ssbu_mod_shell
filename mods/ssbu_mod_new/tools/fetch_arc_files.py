"""Read donor ARC files over arc-network into `refs/<set>/arc/`, read-only.

Version 1.0.0. Usage:
    toolchains/py312/python.exe tools/fetch_arc_files.py                # default set: chrom_jab
    toolchains/py312/python.exe tools/fetch_arc_files.py --limit 1      # smoke: one file
    toolchains/py312/python.exe tools/fetch_arc_files.py --check        # verify an existing extraction

Why
---
`dumps/arc` is the ArcExplorer export and is treated as read-only, so a file it
does not contain is fetched live into `refs/` instead (the same route Hero's
motion list and Cloud's motion list/params/skeleton took). The console needs
`libarc_network.nro` on the SD **and** Smash running; the port is 43022 and the
extraction writes nothing to the console (`handbook/03_dumps.md`).

ABI follows `tools/extract_hero_motion_list.py` and
`src/pmclone/tools/extract_missing.py`. Machine values come from `paths.toml`,
never from constants in here.

Provenance
----------
Every file is written to a `.partial` name first and renamed only after the
extractor returns 0, so an interrupted run can never leave a short file looking
like a good one. An existing destination file is left alone unless `--force`, which
makes a interrupted batch resumable. `extraction.json` records per-file size and
sha256 plus the machine values used; `SOURCE.json` states where the material came
from. Re-running `--check` re-hashes everything against that report.
"""
from __future__ import annotations

import argparse
import ctypes as c
import hashlib
import json
from pathlib import Path
import struct
import sys
import tomllib
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'toolchains' / 'py312'))

REGION = 2  # US English; dumps/INDEX.md says the export is region 2 only

SWORD_MODEL_FILES = [
    'model.numdlb', 'model.numshb', 'model.numshexb', 'model.nusktb',
    'model.nusrcmdlb', 'model.nuhlpb', 'model.numatb', 'model.xmb',
    'dark_model.numatb', 'light_model.numatb', 'metamon_model.numatb',
    'met_chrom_001_col.nutexb', 'met_chrom_001_nor.nutexb', 'met_chrom_001_prm.nutexb',
]
SWORD_MOTION_FILES = ['motion_list.bin', 'j00entryl.nuanmb', 'j00entryr.nuanmb']

# Extras on the same run: the donor skeleton (to place `sword1`, as Cloud's was
# pinned for the fair) and the donor params (absent from the export; not needed by
# the jab, whose hitboxes are inline in the ACMD, but wanted for further moves).
EXTRA_FILES = [
    'fighter/chrom/model/body/c00/model.nusktb',
    'fighter/chrom/param/vl.prc',
    'fighter/chrom/param/expression_vl.prc',
]


def chrom_jab_paths() -> list[str]:
    paths = []
    for slot in range(8):
        c0 = f'c{slot:02d}'
        paths += [f'fighter/chrom/model/sword/{c0}/{f}' for f in SWORD_MODEL_FILES]
        paths += [f'fighter/chrom/motion/sword/{c0}/{f}' for f in SWORD_MOTION_FILES]
    return paths + EXTRA_FILES


def index_paths(*patterns: str) -> list[str]:
    """Paths from the vanilla ARC index (`dumps/decoded/arc_files.tsv`) matching any regex, in index order."""
    import re
    rx = [re.compile(p) for p in patterns]
    lines = (ROOT / 'dumps/decoded/arc_files.tsv').read_text(encoding='utf-8').splitlines()
    return [l.split('	')[0] for l in lines if any(r.match(l.split('	')[0]) for r in rx)]


SETS = {
    'brave_special_s_article_motions': (
        ROOT / 'refs/brave_special_s/article_motions',
        index_paths(r'fighter/brave/motion/(spark|lightning)/c0[0-7]/motion_list\.bin$'),
        'Sixteen exact Hero side-B spark/lightning article motion lists across all costume slots; separate provenance preserves the 184-file extraction',
    ),
    'snake_grenade_lower_body': (
        ROOT / 'refs/snake_grenade/lower_body',
        index_paths(r'fighter/snake/motion/body/c00/h10itemlegs[^/]*\.nuanmb$'),
        'Fifteen donor lower-body clips used by the common item-hold status family',
    ),
    'snake_grenade_sequence': (
        ROOT / 'refs/snake_grenade/sequence',
        index_paths(r'sound/sequence/fighter/snake\.sqb$'),
        'Snake neutral-B sequence audit; separate report preserves the earlier 35-file extraction',
    ),
    # Snake neutral-B on Pyra c06/c07 (projects/pgwr/TODO.md, dumps/MISSING.md 2026-09-30 Claude).
    'snake_grenade': (
        ROOT / 'refs/snake_grenade',
        index_paths(r'fighter/snake/motion/body/c00/motion_list\.bin$',
                    r'fighter/snake/model/grenade/c00/',
                    r'sound/bank/fighter/se_snake_c00\.',
                    r'item/snakegrenade/(model|motion)/body/c00/',
                    r'item/snakegrenade/script/animcmd/body/'),
        'Snake body motion list, se_snake_c00 bank, item/snakegrenade model/motion/scripts',
    ),
    # ROB down tilt on Pyra c06/c07 (G&W). ACMD text is in dumps/scripts; the clip, motion list and skeleton are not in dumps/arc.
    'robot_attack_lw3': (
        ROOT / 'refs/robot_attack_lw3',
        index_paths(r'fighter/robot/motion/body/c00/(motion_list\.bin|c02attacklw3\.nuanmb)$',
                    r'fighter/robot/model/body/c00/model\.nusktb$',
                    r'fighter/robot/param/vl\.prc$',
                    r'sound/bank/fighter/se_robot_c00\.',
                    r'sound/bank/fighter_voice/vc_robot_c00\.',
                    r'sound/sequence/fighter/robot\.sqb$'),
        'ROB AttackLw3 clip, body motion list, skeleton, params, se_robot/vc_robot c00 banks, robot.sqb',
    ),
    # Hero side-B for Mythra c06/c07 (dumps/MISSING.md 2026-09-30 Buffy, sections A-D).
    'brave_special_s': (
        ROOT / 'refs/brave_special_s',
        index_paths(r'fighter/brave/model/blue/c0[0-7]/',
                    r'fighter/brave/motion/blue/c0[0-7]/(motion_list\.bin|j01appeallw[lr]\.nuanmb)$',
                    r'fighter/brave/motion/body/c0[67]/(d01special(air)?s[^/]*\.nuanmb|motion_list\.bin)$',
                    r'fighter/brave/motion/body/c0[067]/(swing|swingblend|scharge|update|ik|flip)\.prc$',
                    r'fighter/brave/model/body/c0[67]/model\.nusktb$',
                    r'fighter/brave/ai/param/attack_(data|list)_param\.prc$'),
        'Hero sword article c00-c07, SPECIAL_S body clips/lists c06/c07, body .prc c00/c06/c07, skeletons, AI params',
    ),
    'hero_neutral_b_sound': (
        ROOT / 'refs/brave_special_n/sound',
        ['sound/sequence/fighter/brave.sqb'],
        'sound/sequence/fighter/brave.sqb: original Hero neutral-B voice sequence data',
    ),
    # Little Mac's forward smash (AttackS4) on Pyra/G&W c06/c07. dumps/arc/fighter/littlemac
    # is empty on disk (0 of 4290 indexed files), so the clips, motion list, skeleton, params
    # and both sound banks come off the console. Modelled on robot_attack_lw3, the other
    # single-attack port to this costume. Scope: the forward smash itself, its charge hold,
    # and the up/down-angled forward-smash variants (AttackS4/AttackS4Hold/AttackS4Hi/
    # AttackS4Lw) - not up-smash or down-smash.
    'littlemac_attack_s4': (
        ROOT / 'refs/littlemac_attack_s4',
        index_paths(r'fighter/littlemac/motion/body/c00/(motion_list\.bin|c03attacks4s\.nuanmb|c03attacks4charge\.nuanmb|c03attacks4hi\.nuanmb|c03attacks4lw\.nuanmb)$',
                    r'fighter/littlemac/model/body/c00/model\.nusktb$',
                    r'fighter/littlemac/param/(vl|expression_vl)\.prc$',
                    r'fighter/littlemac/ai/param/attack_(data|list)_param\.prc$',
                    r'effect/fighter/littlemac/ef_littlemac\.eff$',
                    r'sound/bank/fighter/se_littlemac_c00\.',
                    r'sound/bank/fighter_voice/vc_littlemac_c00\.',
                    r'sound/sequence/fighter/littlemac\.sqb$'),
        'Little Mac AttackS4 family clips (s/charge/hi/lw), body motion list, skeleton, params, ef_littlemac.eff, se/vc_littlemac_c00 banks, littlemac.sqb',
    ),
    # Chrom's jab: the Falchion is an article with its own model and clips, and
    # dumps/arc has both directories empty (they exist only as index entries).
    'chrom_jab': (
        ROOT / 'refs/chrom_jab',
        chrom_jab_paths(),
        'fighter/chrom/{model,motion}/sword/c00..c07 + body skeleton + params',
    ),
    # Snake up tilt (AttackHi3) on Pyra c06/c07 (G&W), replacing G&W's own up tilt.
    # dumps/arc holds only the thirteen grenade special_n clips under
    # fighter/snake/motion/body/c00 and no snake voice bank, so the clip, the body
    # motion list, the donor skeleton and vc_snake_c00 come off the console.
    # Not in this set, already pinned elsewhere and referenced from SOURCE.json
    # (AGENTS.md rule 29): the ACMD text (dumps/scripts .../lua2cpp_snake/snake/
    # AttackHi3.txt), se_snake_c00 + snake.sqb (refs/snake_grenade), and
    # fighter/snake/param/*.prc (dumps/arc).
    'snake_attack_hi3': (
        ROOT / 'refs/snake_attack_hi3',
        index_paths(r'fighter/snake/motion/body/c00/(motion_list\.bin|c02attackhi3\.nuanmb)$',
                    r'fighter/snake/model/body/c00/model\.nusktb$',
                    r'fighter/snake/ai/param/attack_(data|list)_param\.prc$',
                    r'sound/bank/fighter_voice/vc_snake_c00\.'),
        'Snake AttackHi3 clip, body motion list, donor body skeleton, AI attack data/list params, vc_snake_c00 voice bank',
    ),
}


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def validate(path: str, data: bytes) -> str:
    """Parse the files whose format we can check, so a bad extraction is caught here."""
    import ssbh_data_py as s

    name = path.rsplit('/', 1)[-1]
    if name == 'motion_list.bin':
        assert struct.unpack_from('<Q', data)[0] == hash40('motion'), f'{path}: wrong magic'
        count = struct.unpack_from('<Q', data, 16)[0]
        assert 0 < count < 2000, f'{path}: implausible motion count {count}'
        kinds = []
        off = 24
        names = [('entry_l', hash40('entry_l')), ('entry_r', hash40('entry_r'))]
        raw = set()
        for _ in range(count):
            kind, _gs, _fl, _bl, n, size = struct.unpack_from('<QQHBBI', data, off)
            off += 24
            off = (off + n * 9 + 3) & ~3
            raw.add(kind)
            off += size
        kinds = [n for n, h in names if h in raw]
        # article and item lists have no entry motions; the walk above already checked the structure
        return f'{count} motions, {"/".join(kinds) or "no entry motions"}'
    if name.endswith('.nuanmb'):
        a = s.anim_data.read_anim(str(_tmp_parse_target(path, data)))
        groups = [(g.group_type.name, len(g.nodes)) for g in a.groups]
        return f'{len(a.groups)} groups {groups}'
    if name.endswith('.nusktb'):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.nusktb', delete=False) as fh:
            fh.write(data)
            tmp = fh.name
        try:
            skel = s.skel_data.read_skel(tmp)
            return f'{len(skel.bones)} bones: ' + ', '.join(b.name for b in skel.bones[:6])
        finally:
            Path(tmp).unlink(missing_ok=True)
    if name.endswith('.numatb'):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.numatb', delete=False) as fh:
            fh.write(data)
            tmp = fh.name
        try:
            matl = s.matl_data.read_matl(tmp)
            tex = sorted({t.data for e in matl.entries for t in e.textures if t.data})
            return f'{len(matl.entries)} material(s), textures {tex}'
        finally:
            Path(tmp).unlink(missing_ok=True)
    return f'{len(data)} bytes'


def _tmp_parse_target(path: str, data: bytes) -> Path:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.nuanmb', delete=False) as fh:
        fh.write(data)
        return Path(fh.name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--set', default='chrom_jab', choices=sorted(SETS))
    ap.add_argument('--limit', type=int, default=0, help='extract only the first N paths (smoke run)')
    ap.add_argument('--force', action='store_true', help='re-extract files that already exist')
    ap.add_argument('--check', action='store_true', help='verify an existing extraction, no console access')
    args = ap.parse_args()

    dest_root, paths, label = SETS[args.set]
    arc_root = dest_root / 'arc'
    report_path = dest_root / 'extraction.json'

    if args.limit:
        paths = paths[:args.limit]

    if args.check:
        report = json.loads(report_path.read_text())
        bad = []
        for rel, rec in sorted(report['files'].items()):
            p = arc_root / rel
            if not p.is_file():
                bad.append(f'{rel}: missing')
                continue
            data = p.read_bytes()
            if len(data) != rec['bytes'] or hashlib.sha256(data).hexdigest() != rec['sha256']:
                bad.append(f'{rel}: changed')
        print(f'{args.set} check: {len(report["files"])} files, {"OK" if not bad else "PROBLEMS"}')
        for line in bad:
            print('  ' + line)
        return 1 if bad else 0

    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    dll = cfg['toolchain']['arc_network_dll']
    ip = cfg['switch']['arc_network_ip']
    version = cfg['switch']['game_version']

    lib = c.CDLL(dll)
    lib.arc_open_networked.argtypes, lib.arc_open_networked.restype = [c.c_char_p], c.c_void_p
    lib.arc_free.argtypes, lib.arc_free.restype = [c.c_void_p], None
    lib.arc_extract_file_regional.argtypes = [c.c_void_p, c.c_uint64, c.c_char_p, c.c_uint32]
    lib.arc_extract_file_regional.restype = c.c_uint8

    print(f'Opening arc-network {ip}:43022 (read only, region {REGION})', flush=True)
    handle = lib.arc_open_networked(ip.encode('ascii'))
    assert handle, 'arc-network returned no handle (is libarc_network.nro on the SD and Smash running?)'

    files, failures, skipped = {}, [], 0
    try:
        for i, path in enumerate(paths, 1):
            out = arc_root / path
            if out.is_file() and not args.force:
                data = out.read_bytes()
                if data:
                    files[path] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                   'note': 'pre-existing, not re-extracted'}
                    skipped += 1
                    print(f'[{i}/{len(paths)}] skip (present) {path}', flush=True)
                    continue
            out.parent.mkdir(parents=True, exist_ok=True)
            partial = out.with_suffix(out.suffix + '.partial')
            partial.unlink(missing_ok=True)
            result = lib.arc_extract_file_regional(handle, hash40(path), str(partial).encode('utf-8'), REGION)
            if result != 0 or not partial.is_file() or partial.stat().st_size == 0:
                failures.append(f'{path}: result {result}')
                partial.unlink(missing_ok=True)
                print(f'[{i}/{len(paths)}] FAIL {path} (result {result})', flush=True)
                continue
            data = partial.read_bytes()
            try:
                detail = validate(path, data)
            except Exception as exc:  # a file that will not parse is not a file we ship
                failures.append(f'{path}: does not parse ({exc})')
                partial.unlink(missing_ok=True)
                print(f'[{i}/{len(paths)}] FAIL {path} ({exc})', flush=True)
                continue
            partial.rename(out)
            files[path] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'detail': detail}
            print(f'[{i}/{len(paths)}] {path}  {len(data)} B  {detail}', flush=True)
    finally:
        lib.arc_free(handle)

    if args.limit:
        print(f'limit run: {len(files)} file(s) handled, {len(failures)} failure(s); no report written')
        return 1 if failures else 0

    report = {'date': '2026-09-30', 'arc_set': args.set, 'label': label, 'region': REGION,
              'game_version': version, 'ip': ip,
              'method': 'tools/fetch_arc_files.py v1.0.0 / arc_extract_file_regional',
              'requested': len(paths), 'extracted': len(files) - skipped,
              'already_present': skipped, 'failures': failures, 'files': files}
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'\n{len(files)}/{len(paths)} files under {arc_root.relative_to(ROOT)}, '
          f'{skipped} already present, {len(failures)} failure(s)')
    print(f'report: {report_path.relative_to(ROOT)}')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
