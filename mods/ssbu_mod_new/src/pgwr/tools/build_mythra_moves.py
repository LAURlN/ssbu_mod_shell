"""Deploy Corrin Up Air and Luigi Down Throw animation clips to Mythra (elight) c06 and c07.

Used by ``build.py`` so the ``mythra`` module in the plugin has real animation to
play. The moves themselves are hooked in:
  - ``plugin/src/mythra/attack_air_hi.rs`` (Corrin Up Air hitboxes & timings)
  - ``plugin/src/mythra/throw_lw.rs``      (Luigi Down Throw hitboxes & timings)

# Provenance
In the swap mod (``mod_files/mythra_gamewatch_swap`` and ``mod_backup_2``):
  - Corrin Up Air donor:
      Origin: ``export/fighter/kamui/motion/body/c00/c05attackairhi.nuanmb``
      SHA-256: a09b93ce5905f9bff570800cd3e8eb3b5b5803a93d5b9237d268bc4b934c56ac
      Size: 48,479 bytes
  - Luigi Down Throw donor:
      Origin: ``export/fighter/luigi/motion/body/c00/e01throwlw.nuanmb``
      SHA-256: 57bafacc700e8efbcd5493e0eaf57b67a3c124dcac6508493528c0d327050802
      Size: 46,024 bytes

Both donor animations play directly on Mythra's skeleton in Smash Ultimate's
engine without bone transforms/retargeting, exactly as validated on hardware in
``mod_backup_2``.

# In-Place Replacement (No motion-list surgery, no config.json additions)
In vanilla Smash Ultimate, Mythra's own ``motion_list.bin`` already assigns:
  - ``attack_air_hi`` -> ``c05attackairhi.nuanmb``
  - ``throw_lw``      -> ``e01throwlw.nuanmb``

Because the donor clips have identical filenames to Mythra's stock clips and
stock clips exist in the base-game dump (``export/fighter/elight/motion/body/...``):
1. These files replace base-game files in-place.
2. They are NOT new files, so they must NOT be declared in ``config.json``.
3. Mythra's ``motion_list.bin`` requires zero modifications.
"""
from pathlib import Path
import hashlib
import os
import shutil
import sys

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
EXPORT = Path(os.environ.get('MGW_EXPORT', ROOT / 'dumps' / 'arc'))
BACKUP_DIR = ROOT / 'refs' / 'swap_mod_snapshot' / 'ultimate' / 'mods' / 'mythra_gamewatch_swap'

SWAP_TOOLS = ROOT / 'src' / 'mgw_swap' / 'tools'
sys.path.insert(0, str(SWAP_TOOLS))
sys.path.insert(0, str(SWAP_TOOLS / 'vendor'))

import build_hero_spin_assets as base  # noqa: E402


DONOR_MOVES = {
    'attack_air_hi': {
        'donor_fighter': 'kamui',
        'donor_slot': 'c00',
        'clip_name': 'c05attackairhi.nuanmb',
        'expected_sha256': 'a09b93ce5905f9bff570800cd3e8eb3b5b5803a93d5b9237d268bc4b934c56ac',
        'expected_size': 48479,
        'description': "Corrin (Kamui) Up Air",
    },
    'throw_lw': {
        'donor_fighter': 'luigi',
        'donor_slot': 'c00',
        'clip_name': 'e01throwlw.nuanmb',
        'expected_sha256': '57bafacc700e8efbcd5493e0eaf57b67a3c124dcac6508493528c0d327050802',
        'expected_size': 46024,
        'description': "Luigi Down Throw",
    },
}


def fail(message: str):
    raise SystemExit(f'mythra moves: {message}')


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_motions(path: Path):
    """Parse motion_list.bin and return motions dict."""
    _, _, motions = base.parse_mlist(str(path))
    return motions


def deploy_move_for_slot(motion_kind: str, slot: str, out_dir: Path, stock_motions_dict: dict) -> dict:
    """Validate, copy, and verify one donor clip for the given costume slot."""
    info = DONOR_MOVES[motion_kind]
    clip_name = info['clip_name']
    expected_sha = info['expected_sha256']
    expected_size = info['expected_size']

    # 1. Verify donor source in export dump
    src = EXPORT / 'fighter' / info['donor_fighter'] / 'motion' / 'body' / info['donor_slot'] / clip_name
    if not src.is_file():
        fail(f"missing donor source file: {src}")
    src_sha = sha(src)
    if src_sha != expected_sha:
        fail(f"donor source {src} SHA-256 mismatch: got {src_sha}, expected {expected_sha}")
    if src.stat().st_size != expected_size:
        fail(f"donor source {src} size mismatch: got {src.stat().st_size}, expected {expected_size}")

    # 2. Verify against working backup copy if present
    backup_file = BACKUP_DIR / 'fighter' / 'elight' / 'motion' / 'body' / slot / clip_name
    if backup_file.is_file():
        b_sha = sha(backup_file)
        if b_sha != expected_sha:
            fail(f"backup reference {backup_file} SHA-256 mismatch: got {b_sha}, expected {expected_sha}")

    # 3. Verify stock Mythra file exists in dump (ensuring this is an in-place replacement)
    stock_clip = EXPORT / 'fighter' / 'elight' / 'motion' / 'body' / slot / clip_name
    if not stock_clip.is_file():
        fail(f"no stock Mythra clip to replace: {stock_clip}")

    # 4. Verify stock motion list maps this motion_kind to this clip_name
    kind_hash = base.hash40(motion_kind)
    clip_hash = base.hash40(clip_name)
    mapped_anims = stock_motions_dict.get(kind_hash, {}).get('animations', ())
    if mapped_anims != (clip_hash,):
        fail(f"Mythra {slot} motion {motion_kind} does not map to {clip_name}: got {mapped_anims}")

    # 5. Copy donor clip to destination
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / clip_name
    shutil.copy2(src, dst)

    # 6. Read back and verify destination file
    if not dst.is_file():
        fail(f"destination file was not created: {dst}")
    dst_sha = sha(dst)
    if dst_sha != expected_sha:
        fail(f"written destination {dst} SHA-256 mismatch: got {dst_sha}, expected {expected_sha}")
    if dst.stat().st_size != expected_size:
        fail(f"written destination {dst} size mismatch: got {dst.stat().st_size}, expected {expected_size}")

    return {
        'motion_kind': motion_kind,
        'clip': clip_name,
        'donor_fighter': info['donor_fighter'],
        'donor_slot': info['donor_slot'],
        'size': expected_size,
        'sha256': dst_sha,
    }


def build_slot(slot: str, out_root: Path) -> dict:
    """Deploy Up Air and Down Throw donor clips for one Mythra costume slot."""
    if slot not in ('c06', 'c07'):
        fail(f"unsupported slot for Mythra moves: {slot}")

    out_dir = out_root / 'fighter' / 'elight' / 'motion' / 'body' / slot
    stock_mlist_path = EXPORT / 'fighter' / 'elight' / 'motion' / 'body' / slot / 'motion_list.bin'
    if not stock_mlist_path.is_file():
        fail(f"no stock Mythra motion list for {slot}: {stock_mlist_path}")
    stock_motions_dict = read_motions(stock_mlist_path)

    clips = []
    for motion_kind in ('attack_air_hi', 'throw_lw'):
        record = deploy_move_for_slot(motion_kind, slot, out_dir, stock_motions_dict)
        clips.append(record)

    return {
        'slot': slot,
        'clips': clips,
    }


def main():
    import json
    target_mod = ROOT / 'builds' / 'pgwr' / 'pyra_gamewatch_reskin' / 'ultimate' / 'mods' / 'pyra_gamewatch_reskin'
    print(f"Building Mythra moves into {target_mod}...")
    report = {slot: build_slot(slot, target_mod) for slot in ('c06', 'c07')}
    print(json.dumps(report, indent=2))
    print("Mythra moves deployment completed successfully.")


if __name__ == '__main__':
    main()
