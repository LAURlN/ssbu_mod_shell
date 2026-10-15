"""Verify the Hero Spin (up-B) clips and patched motion list in the deploy payload.

Why this exists
---------------
Mii Swordfighter's Hero Spin up-B was retargeted onto Mythra (`elight`) `c07`.
The five resulting clips and the patched `motion_list.bin` were written by hand,
so nothing in `deploy.py` used to create, refresh or even look at them. A payload
could therefore ship the current plugin with stale or missing animation assets,
silently.

That is exactly how the "Mythra plays her vanilla up-B" defect reached hardware:
the vanilla up-B plays those same five slots, so missing assets look exactly like
a broken status port, which is what made it hard to see.

What it checks
--------------
Against `references/miiswordsman_special_hi/hero_spin_animation_manifest.json`:

  * each of the five retargeted clips exists in the payload motion directory
    with the manifest's byte size and SHA-256;
  * `motion_list.bin` matches the manifest's size and SHA-256;
  * the two fields the manifest records as patched are actually present in that
    motion list - the loop flag on `special_air_hi1` and the cancel frame on
    `special_air_hi_end` - so a payload carrying old clips with a patched list,
    or the reverse, is caught as well.

Exit status
-----------
  0  everything matches
  1  a mismatch (every mismatch is printed; each names the file and both the
     expected and the found SHA-256)
  2  the check could not run, e.g. the manifest is missing or malformed

It never prints a bare traceback and it never reports success silently.

Run
---
    python mod_files/mythra_gamewatch_swap/tools/verify_hero_spin_payload.py
    python .../verify_hero_spin_payload.py --manifest <path> --payload-dir <path>

The overrides exist so the check can be pointed at a copied payload and a copied
manifest without touching the real ones.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
import zlib

# <workspace_root>/mod_files/mythra_gamewatch_swap/tools/<this file>
WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = (WORKSPACE / 'references' / 'miiswordsman_special_hi'
                    / 'hero_spin_animation_manifest.json')
DEFAULT_PAYLOAD_DIR = (WORKSPACE / 'mod_output' / 'ultimate' / 'mods'
                       / 'mythra_gamewatch_swap' / 'fighter' / 'elight'
                       / 'motion' / 'body' / 'c07')

EXPECTED_CLIP_COUNT = 5

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_CONFIG = 2


class ConfigError(Exception):
    """The verifier cannot run: the manifest itself is missing or malformed."""


def hash40(name):
    """SSBU's 40-bit string hash; mirrors tools/build_hero_spin_assets.py."""
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_motion_list(path):
    """Parse a motion_list.bin; mirrors tools/build_hero_spin_assets.py.

    Entries keep the absolute `start` offset as well, so a caller can locate the
    exact byte a patch touches. Raises ValueError on anything malformed.
    """
    data = Path(path).read_bytes()
    if len(data) < 24:
        raise ValueError('file is shorter than a motion-list header')
    magic, _motion_path, count = struct.unpack_from('<QQQ', data)
    if magic != hash40('motion'):
        raise ValueError(f'bad motion-list header magic {magic:#x}')
    offset = 24
    motions = {}
    for _ in range(count):
        start = offset
        if start + 24 > len(data):
            raise ValueError(f'truncated motion entry at {start:#x}')
        kind, _game_script, flags, _blend, animations, size = struct.unpack_from(
            '<QQHBBI', data, start)
        if animations > 3 or size % 8 not in (0, 4):
            raise ValueError(f'invalid motion entry at {start:#x}')
        offset = start + 24
        if offset + animations * 8 > len(data):
            raise ValueError(f'truncated animation list at {offset:#x}')
        names = (struct.unpack_from('<' + 'Q' * animations, data, offset)
                 if animations else ())
        offset = (offset + animations * 9 + 3) & ~3
        end = offset + size
        if end > len(data):
            raise ValueError(f'truncated motion entry body at {start:#x}')
        if kind in motions:
            raise ValueError(f'duplicate motion entry at {start:#x}')
        motions[kind] = {
            'start': start, 'end': end, 'raw': data[start:end],
            'animations': names, 'flags': flags, 'size': size,
            'cancel': data[end - 2] if size % 8 == 4 else None,
        }
        offset = end
    if offset != len(data):
        raise ValueError(f'unexpected trailing data at {offset:#x}')
    return magic, motions


def build_expectations(manifest, manifest_path):
    """Filename -> expected size/sha256, plus the motion_list section."""
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise ConfigError(f'{manifest_path}: no "files" map')
    motions = manifest.get('motions')
    if not isinstance(motions, list) or len(motions) != EXPECTED_CLIP_COUNT:
        found = len(motions) if isinstance(motions, list) else type(motions).__name__
        raise ConfigError(
            f'{manifest_path}: expected {EXPECTED_CLIP_COUNT} clip records in '
            f'"motions", found {found}')
    motion_list = manifest.get('motion_list')
    if not isinstance(motion_list, dict):
        raise ConfigError(f'{manifest_path}: missing "motion_list" section')

    expected = {}
    for record in motions:
        name = record.get('recipient_animation')
        size = record.get('output_bytes')
        digest = record.get('output_sha256')
        if not name or not isinstance(size, int) or not digest:
            raise ConfigError(
                f'{manifest_path}: a "motions" record lacks '
                f'recipient_animation/output_bytes/output_sha256')
        expected[name] = {'size': size, 'sha256': digest,
                          'slot': record.get('slot'), 'kind': 'clip'}

    if not isinstance(motion_list.get('output_bytes'), int) or not motion_list.get(
            'output_sha256'):
        raise ConfigError(
            f'{manifest_path}: "motion_list" lacks output_bytes/output_sha256')
    expected['motion_list.bin'] = {
        'size': motion_list['output_bytes'],
        'sha256': motion_list['output_sha256'],
        'kind': 'motion_list',
    }

    # The manifest records the same hashes twice (per record and in "files");
    # if those disagree the manifest cannot be trusted to judge the payload.
    if set(files) != set(expected):
        raise ConfigError(
            f'{manifest_path}: "files" lists {sorted(files)} but the clip and '
            f'motion-list records imply {sorted(expected)}')
    for name, info in expected.items():
        if files[name] != info['sha256']:
            raise ConfigError(
                f'{manifest_path}: {name} is {files[name]} in "files" but '
                f'{info["sha256"]} in its record; the manifest contradicts itself')
    return expected, motion_list


def check_files(payload_dir, expected, failures):
    """Existence, size and SHA-256 of every expected file."""
    results = []
    for name in sorted(expected):
        info = expected[name]
        path = payload_dir / name
        if not path.is_file():
            failures.append(
                f'{name}: MISSING from {payload_dir}; manifest expects '
                f'{info["size"]} bytes sha256 {info["sha256"]}')
            continue
        actual_size = path.stat().st_size
        actual_sha = sha256_file(path)
        if actual_size != info['size'] or actual_sha != info['sha256']:
            failures.append(
                f'{name}: expected {info["size"]} bytes sha256 {info["sha256"]}, '
                f'found {actual_size} bytes sha256 {actual_sha}')
        results.append((name, actual_size, actual_sha))
    return results


def expected_patch_byte(patch, byte_offset, raw_len, field):
    """The byte a recorded differing offset should hold, or None if unmodelled."""
    if field == 'flags':
        base = patch.get('offset')
        if not isinstance(base, int):
            return None
        index = byte_offset - base
        packed = struct.pack('<H', int(str(patch['after']), 16))
        return packed[index] if 0 <= index < len(packed) else None
    if field == 'cancel_frame':
        return int(patch['after']) if byte_offset == raw_len - 2 else None
    return None


def check_patched_fields(mlist_path, motion_list, manifest_sha, failures):
    """Confirm the fields the manifest records as patched are really patched."""
    patches = motion_list.get('patches')
    if not isinstance(patches, list) or not patches:
        failures.append(
            f'{mlist_path.name}: the manifest records no "motion_list.patches", '
            f'so the patched fields cannot be checked')
        return []
    try:
        _magic, motions = parse_motion_list(mlist_path)
    except (OSError, ValueError) as exc:
        failures.append(
            f'{mlist_path.name}: could not be parsed to check the patched '
            f'fields: {exc}')
        return []

    lines = []
    for patch in patches:
        slot = patch.get('slot')
        field = patch.get('field')
        if not slot or not field:
            failures.append(f'{mlist_path.name}: a manifest patch lacks slot/field')
            continue
        entry = motions.get(hash40(slot))
        if entry is None:
            failures.append(
                f'{mlist_path.name}: no motion-list entry for slot "{slot}" '
                f'(patch "{field}")')
            continue
        raw = entry['raw']

        if field == 'flags':
            offset = patch.get('offset')
            if not isinstance(offset, int) or offset + 2 > len(raw):
                failures.append(
                    f'{mlist_path.name}: slot "{slot}" entry is too short for '
                    f'its flags field')
                continue
            found = struct.unpack_from('<H', raw, offset)[0]
            want = int(str(patch['after']), 16)
            before = int(str(patch['before']), 16)
            if found != want:
                failures.append(
                    f'{mlist_path.name}: slot "{slot}" field {field} at entry '
                    f'offset {offset} is {found:#06x}, manifest expects the '
                    f'patched {want:#06x} (unpatched {before:#06x}); file sha256 '
                    f'{sha256_file(mlist_path)} vs manifest {manifest_sha}')
            lines.append(
                f'{slot}: {field} {found:#06x} (loop bit {patch.get("bit_set")} set)')
        elif field == 'cancel_frame':
            if entry['size'] % 8 != 4:
                failures.append(
                    f'{mlist_path.name}: slot "{slot}" entry carries no cancel '
                    f'field (size {entry["size"]})')
                continue
            found = entry['cancel']
            want = int(patch['after'])
            before = int(patch['before'])
            if found != want:
                failures.append(
                    f'{mlist_path.name}: slot "{slot}" field {field} is {found}, '
                    f'manifest expects the patched {want} (unpatched {before}); '
                    f'file sha256 {sha256_file(mlist_path)} vs manifest '
                    f'{manifest_sha}')
            lines.append(f'{slot}: {field} {found} (patched)')
        else:
            failures.append(
                f'{mlist_path.name}: unsupported manifest patch field "{field}"')
            continue

        # The recorded differing byte offsets must carry the patched bytes too.
        for byte_offset in patch.get('differing_byte_offsets', []):
            if not isinstance(byte_offset, int) or not 0 <= byte_offset < len(raw):
                failures.append(
                    f'{mlist_path.name}: slot "{slot}" records differing byte '
                    f'{byte_offset!r}, which is outside its entry')
                continue
            want_byte = expected_patch_byte(patch, byte_offset, len(raw), field)
            if want_byte is None:
                continue
            if raw[byte_offset] != want_byte:
                failures.append(
                    f'{mlist_path.name}: slot "{slot}" entry byte {byte_offset} is '
                    f'{raw[byte_offset]:#04x}, manifest expects {want_byte:#04x} at '
                    f'that differing offset')
    return lines


def run(args):
    manifest_path = Path(args.manifest)
    payload_dir = Path(args.payload_dir)

    if not manifest_path.is_file():
        raise ConfigError(f'manifest not found: {manifest_path}')
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ConfigError(f'manifest {manifest_path} is not readable JSON: {exc}')
    if not isinstance(manifest, dict):
        raise ConfigError(f'manifest {manifest_path} is not a JSON object')

    expected, motion_list = build_expectations(manifest, manifest_path)
    manifest_sha = expected['motion_list.bin']['sha256']

    failures = []
    results = check_files(payload_dir, expected, failures)

    field_lines = []
    mlist_path = payload_dir / 'motion_list.bin'
    if mlist_path.is_file():
        field_lines = check_patched_fields(
            mlist_path, motion_list, manifest_sha, failures)

    if failures:
        print(f'hero-spin verify FAILED: {len(failures)} mismatch(es) against '
              f'{manifest_path}')
        for failure in failures:
            print(f'  FAIL {failure}')
        print(f'  payload dir: {payload_dir}')
        return EXIT_MISMATCH

    print(f'hero-spin verify OK: {len(expected)} files match {manifest_path}')
    for name, size, digest in results:
        print(f'  {name:<28} {size:>8} bytes  {digest}')
    for line in field_lines:
        print(f'  patched {line}')
    print(f'  payload dir: {payload_dir}')
    return EXIT_OK


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Verify the Hero Spin (up-B) payload against its manifest.')
    parser.add_argument(
        '--manifest', default=str(DEFAULT_MANIFEST),
        help='hero_spin_animation_manifest.json to check against')
    parser.add_argument(
        '--payload-dir', default=str(DEFAULT_PAYLOAD_DIR),
        help='elight c07 motion directory inside the payload')
    args = parser.parse_args(argv)
    try:
        return run(args)
    except ConfigError as exc:
        print(f'hero-spin verify: cannot check: {exc}', file=sys.stderr)
        return EXIT_CONFIG
    except Exception as exc:  # noqa: BLE001 - never surface a bare traceback
        print(f'hero-spin verify: unexpected error: {type(exc).__name__}: {exc}',
              file=sys.stderr)
        return EXIT_CONFIG


if __name__ == '__main__':
    sys.exit(main())
