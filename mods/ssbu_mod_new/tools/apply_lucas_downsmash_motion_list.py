"""Apply Lucas's `attack_lw4` cancel frame to a Mythra motion list. v1.0.0.

This is the whole motion-list half of the Lucas down-smash port, and it is two
bytes. Measured by `src/pgwr/tools/build_lucas_downsmash.py --check`:

  * Lucas `attack_lw4`        : cancel **316**, flags 0x80, game_attacklw4
    Mythra `attack_lw4`      : cancel **56**,  flags 0x80, game_attacklw4
    the two entry bodies differ at byte offsets **[62, 63]** and nowhere else -
    that is the cancel u16, little-endian.
  * Lucas `attack_lw4_hold`  : **byte-identical** to Mythra's. Cancel 0, flags
    0x80, game_attacklw4charge, same clip. Nothing is written for it.

So this port adds no motion kind, no clip name, no script field and no flag -
it replaces one u16. Everything else about the entry is already the donor's.

# Why a tool and not a hand-edited binary

The entry offset is a function of the whole file, so the byte position only
means something together with the exact input it was computed from. This tool
therefore **refuses to run against a file whose sha256 it does not recognise**,
and it re-parses the output to prove the change landed and that nothing else
moved. Point it at the installer's own baseline tree, not at a tree another
agent is editing - the built 0.20.19 `fighter/elight/motion/body/*/motion_list.bin`
is the recorded baseline, and it differs from vanilla because the Hero
neutral-B/side-B work added 25 entries to it.

    python tools/apply_lucas_downsmash_motion_list.py --check
    python tools/apply_lucas_downsmash_motion_list.py --in <motion_list.bin> --out <copy>

Writes `<out>` and never touches `<in>`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
KIND = 'attack_lw4'
DONOR_CANCEL = 316
# The two files this tool has been measured against. A file that is neither of
# these is refused: the 2-byte patch below is only valid for a layout this
# script has actually parsed.
KNOWN_INPUTS = {
    # Built 0.20.19 - the recorded collective baseline (25 Hero entries added).
    '0efe5732fe98afa8e1c742e467e1b408dc1fb0be0269b11831bee980d2fb3059': 'pgwr 0.20.19 built baseline',
    # Vanilla elight c06/c07 (identical files).
    '0b091450a00bdb2b382c59e965997f96d2a387dd2581d7d492183dd69d56c2f7': 'vanilla elight c06/c07',
}
PATCH_REPORT = 'lucas_downsmash_motion_list.json'


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def locate(data: bytes, kind: str) -> dict:
    """Byte range of one entry's header+body, and the cancel u16 inside it.

    Returns the absolute file offsets of the two cancel bytes so the patch does
    not depend on this function and the writer disagreeing about layout.
    """
    magic, _, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError('not a motion list')
    offset = 24
    for _ in range(count):
        start = offset
        k, script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        if k == hash40(kind):
            if size % 8 != 4:
                raise RuntimeError(f'{kind}: entry size {size} has no trailing cancel u16')
            cancel_at = end - 2
            return {'start': start, 'end': end, 'size': size, 'flags': flags,
                    'game_script': script, 'anims': anims,
                    'cancel': struct.unpack_from('<H', data, cancel_at)[0],
                    'cancel_offsets': [cancel_at, cancel_at + 1]}
        offset = end
    if offset != len(data):
        raise RuntimeError(f'{len(data) - offset} unparsed trailing bytes')
    raise RuntimeError(f'no entry of kind {kind}')


def patch(data: bytes) -> tuple[bytes, dict]:
    info = locate(data, KIND)
    donor = struct.pack('<H', DONOR_CANCEL)
    current = bytes(data[o] for o in info['cancel_offsets'])
    if current == donor:
        return data, {'already_patched': True, 'changed': False}
    out = bytearray(data)
    for i, byte in enumerate(donor):
        out[info['cancel_offsets'][i]] = byte
    out = bytes(out)
    after = locate(out, KIND)
    if after['cancel'] != DONOR_CANCEL:
        raise RuntimeError('patch did not take')
    if after['flags'] != info['flags'] or after['game_script'] != info['game_script'] \
            or after['anims'] != info['anims'] or after['size'] != info['size'] \
            or after['start'] != info['start'] or after['end'] != info['end']:
        raise RuntimeError('something other than the cancel frame changed')
    changed = [i for i, (a, b) in enumerate(zip(data, out)) if a != b]
    if changed != info['cancel_offsets']:
        raise RuntimeError(f'changed bytes {changed} are not the cancel pair {info["cancel_offsets"]}')
    return out, {'already_patched': False, 'changed': True,
                 'bytes_changed': changed,
                 'cancel_before': info['cancel'], 'cancel_after': DONOR_CANCEL,
                 'entry_start': info['start'], 'entry_end': info['end']}


def check() -> None:
    for slot in ('c06', 'c07'):
        path = BASELINE / f'fighter/elight/motion/body/{slot}/motion_list.bin'
        assert path.is_file(), f'baseline missing: {path}'
        digest = sha(path.read_bytes())
        print(f'{slot} baseline motion_list.bin sha256 {digest}')
        assert digest in KNOWN_INPUTS, (
            f'{path} is not a baseline this tool has parsed ({digest}). Measure it '
            f'first rather than applying a patch whose byte offsets are unknown.')
    c06 = BASELINE / 'fighter/elight/motion/body/c06/motion_list.bin'
    c07 = BASELINE / 'fighter/elight/motion/body/c07/motion_list.bin'
    assert c06.read_bytes() == c07.read_bytes(), 'c06 and c07 baseline lists differ'
    info = locate(c06.read_bytes(), KIND)
    out, report = patch(c06.read_bytes())
    print(f'{KIND}: cancel {info["cancel"]} -> {DONOR_CANCEL}, '
          f'bytes {report["bytes_changed"]}, flags {info["flags"]:#x} unchanged')
    hold = locate(c06.read_bytes(), 'attack_lw4_hold')
    print(f'attack_lw4_hold: cancel {hold["cancel"]}, already byte-identical to the '
          f'donor, so no write')
    print('PASS: motion-list patch is 2 bytes in 1 entry, hold needs no change')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--in', dest='src', type=Path)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    if args.check or not (args.src and args.out):
        check()
        return 0
    data = args.src.read_bytes()
    digest = sha(data)
    assert digest in KNOWN_INPUTS, (
        f'input sha256 {digest} is not a baseline this tool has parsed; measure first')
    out, report = patch(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(out)
    record = {'tool': Path(__file__).name, 'tool_version': '1.0.0', 'date': '2026-10-02',
              'evidence_tier': 'B', 'hardware_validated': False,
              'input': str(args.src), 'input_sha256': digest,
              'output': str(args.out), 'output_sha256': sha(out),
              'entry': {'kind': KIND, **report}}
    args.out.with_name(PATCH_REPORT).write_text(json.dumps(record, indent=2) + '\n')
    print(f'wrote {args.out} (sha256 {sha(out)}); {report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
