"""Stage a private Snake up-tilt candidate package for the offline audit (v1.0.0).

    python tools/stage_snake_uptilt_candidate.py
    python tools/audit_snake_uptilt_delta.py --baseline 0.20.17 \
        --version builds/.cache/fb-2-snake-up-tilt/0.20.18+snake-uptilt.1

**This is not a substitute for `src/pgwr/build.py`, and it does not replace the
installer's build.** It exists because this workspace has no ArcExplorer export
(`dumps/arc` is absent and the path `paths.toml` names is nearly empty), so the
real pipeline cannot run here. It applies exactly what `build.py` applies for
this move - the retargeted clip, the `attack_hi3` motion-list entry and the sound
merge - on top of the **installed** `builds/pgwr/0.20.17` tree, and writes only
into `builds/.cache/fb-2-snake-up-tilt/`, never into the shared
`builds/pgwr/<version>/` tree that two concurrent asset builds corrupt.

`info.toml` is bumped to the plugin crate version because
`audit_snake_uptilt_delta.py` expects `info.toml` in the delta, and a locally
compiled NRO is copied in because the audit checks the packaged NRO for the
handler and sound names. `nro` can be pointed at the installer's own build with
`--nro`; the default is the compile-check cache of the session that wrote this
tool, and a stale NRO would make the NRO check meaningless - so the file that was
copied is reported with its sha256.

Offline only (tier B). Nothing it produces says how the move behaves in game.
"""
import argparse
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import build_snake_uptilt as su  # noqa: E402
import merge_snake_uptilt_sound as us  # noqa: E402

MOD = 'ultimate/mods/pyra_gamewatch_reskin'
NRO = 'atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro'
DEFAULT_BASELINE = ROOT / 'builds/pgwr/0.20.17'
DEFAULT_NRO = (ROOT / 'builds/.cache/pgwr-fb-2-snake-up-tilt-target/aarch64-skyline-switch/release'
               '/libpyra_gamewatch_reskin.nro')
DEFAULT_OUT = ROOT / 'builds/.cache/fb-2-snake-up-tilt'
VERSION = '0.20.18+snake-uptilt.1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def entries(data):
    _, _, count = struct.unpack_from('<QQQ', data, 0)
    off, out = 24, {}
    for _ in range(count):
        start = off
        kind, gs, fl, bl, n, size = struct.unpack_from('<QQHBBI', data, off)
        off = (off + 24 + n * 9 + 3) & ~3
        out[kind] = {'raw': data[start:off + size], 'game_script': gs,
                     'flags': fl, 'blend': bl, 'n': n}
        off += size
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, default=DEFAULT_BASELINE)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT,
                    help='parent directory for the staged package (must be under builds/.cache)')
    ap.add_argument('--version', default=VERSION)
    ap.add_argument('--nro', type=Path, default=DEFAULT_NRO)
    args = ap.parse_args()
    out_root = args.out.resolve()
    assert out_root.is_relative_to(ROOT / 'builds'), 'stage only under builds/'
    assert not out_root.is_relative_to(ROOT / 'builds/pgwr'), \
        'never stage into the shared builds/pgwr/<version> tree'

    pkg = out_root / args.version
    if pkg.exists():
        shutil.rmtree(pkg)
    shutil.copytree(args.baseline, pkg)
    info = pkg / MOD / 'info.toml'
    version = (ROOT / 'src/pgwr/plugin/Cargo.toml').read_text(encoding='utf-8')
    new_version = version.split('version = "', 1)[1].split('"', 1)[0]
    text = info.read_text(encoding='utf-8')
    import re
    info.write_text(re.sub(r'version = "[^"]+"', f'version = "{new_version}"', text, count=1),
                    encoding='utf-8')
    shutil.copy2(args.nro, pkg / NRO)

    reports = {}
    for slot in ('c06', 'c07'):
        motion = pkg / MOD / f'fighter/eflame/motion/body/{slot}'
        model = pkg / MOD / f'fighter/eflame/model/body/{slot}'
        reports[slot] = su.deploy_for_slot(slot, motion, slot, model)

        path = motion / 'motion_list.bin'
        data = path.read_bytes()
        head, table = data[:24], entries(data)
        donor = su.get_entry()
        kind = su.hash40(su.KIND)
        assert kind in table, f'{slot}: no attack_hi3 entry to replace'
        table[kind] = {'raw': donor['raw'], 'game_script': donor['game_script'],
                       'flags': donor['flags'], 'blend': donor['blend'], 'n': donor['n_anims']}
        path.write_bytes(head + b''.join(table[k]['raw'] for k in table))
        back = entries(path.read_bytes())
        assert back[kind]['raw'] == donor['raw'], f'{slot}: entry did not survive the write'
        assert list(back) == list(table), f'{slot}: kind order changed'

    sound = us.build(pkg / MOD)
    (pkg / MOD / 'snake_uptilt_sound.json').replace(pkg / 'snake_uptilt_sound.json')
    print(json.dumps({
        'package': pkg.relative_to(ROOT).as_posix(),
        'baseline': args.baseline.relative_to(ROOT).as_posix(),
        'info_toml_sha256': sha(info),
        'nro_source': str(args.nro), 'nro_sha256': sha(pkg / NRO),
        'clip_c06': reports['c06'][su.CLIP]['sha256'],
        'clip_c07': reports['c07'][su.CLIP]['sha256'],
        'legs_all_moving': reports['c06'][su.CLIP]['legs_all_moving'],
        'sound_retained': sorted({b['retained_tones'] for b in sound['banks']}),
        'sequence_appended': sound['sequence_appended'],
    }, indent=2))


if __name__ == '__main__':
    main()