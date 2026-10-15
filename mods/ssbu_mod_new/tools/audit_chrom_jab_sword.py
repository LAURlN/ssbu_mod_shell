#!/usr/bin/env python3
"""Check the Chrom jab's Aegis sword on eflame c06/c07, offline, with controls.

What this asserts, and why each one exists
------------------------------------------

1. **The jab's motion-list entries name their clips with the file extension.**
   `hash40` in this project covers the *name as written*, and an animation-name
   hash in a motion list covers `'<stem>.nuanmb'`. Measured on the vanilla
   eflame esword list: `open` -> `0xe32317ab0` == `hash40('z00open.nuanmb')`, not
   `hash40('z00open')`. The 0.20.0-0.20.20 builds wrote the bare stem, so the two
   appended jab entries named files that do not exist and the blade was never
   drawn on hardware (user, 2026-10-03). Nothing errors when a name misses: the
   article keeps playing the clip it already had, `z00close`, whose `flamesword`
   visibility track is False, and that mesh track overrides the ACMD's
   `set_visibility_whole(true)`. So this is checked, not assumed.

2. **Nothing else in the article's motion list moved.** All 15 vanilla entries
   are compared byte for byte against the baseline, and the two appended entries
   must match their donors in every field except the kind and the animation name
   (flags, blend, `game_script`, per-anim flag bytes and payload).

3. **The per-state drawing decision still holds.** `close`, `to_close` and the
   four `d01specials*` clips carry `flamesword = False`; `open`/`to_open` carry
   True at `Sword1` scale 1.4 (the Cloud fair); `jab_open`/`jab_to_open` carry
   True at 0.9 (the jab). This is the pair of levers that is allowed to decide
   visibility, and it is per-move - a global "always show" would break the fair's
   put-away and the jab put-away with it.

4. **The body jab and the fair are untouched.** `attack_11`, `attack_12`,
   `attack_13` still name `c00attack11.nuanmb` with cancel frame 23 (Chrom's), and
   `attack_air_f` still names `c05attackairf.nuanmb`. The fix is article-side; a
   body-side change would move the hitboxes that hardware already confirmed.

5. **The jab's clips are declared in `config.json`.** A name that is not declared
   is not resolved, which is the same silent miss as (1) one level up.

6. **Nothing outside the two `motion_list.bin` files changed** against the
   baseline tree.

Controls
--------

`--check` runs every negative control on deliberately damaged copies in a
temporary directory and fails unless each one is caught, so a `PASS` cannot be
produced by an audit that stopped looking.

    python -B tools/audit_chrom_jab_sword.py --baseline <tree> [--candidate <tree>] [--check]

`<tree>` is a built mod tree, i.e. one containing `config.json` and
`fighter/eflame/...`. Runtime behaviour is not covered by any of this: the sword
appearing on screen is tier D until a console run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import ssbh_data_py as s

ARTICLE = 'fighter/eflame/motion/esword'
BODY = 'fighter/eflame/motion/body'
ANIM_SUFFIX = '.nuanmb'

SLOTS = ('c06', 'c07')

# The article motion list's shipped entries and what each must decide.
HIDDEN_CLIPS = ('z00close', 'z00toclose',
                'd01specials1', 'd01specials2', 'd01specialsmovel', 'd01specialsmover')
FAIR_CLIPS = {'z00open': 1.4, 'z00toopen': 1.4}
JAB_CLIPS = {'jabopen': 0.9, 'jabtoopen': 0.9}
# new motion kind -> (new clip stem, the vanilla motion kind its entry is cloned from)
JAB_ENTRIES = {
    'jab_open': ('jabopen', 'open'),
    'jab_to_open': ('jabtoopen', 'to_open'),
}
MESH = 'flamesword'
SWORD_BONE = 'Sword1'

JAB_BODY_CLIP = 'c00attack11'
FAIR_BODY_CLIP = 'c05attackairf'
# How many entries the vanilla article list has, and therefore where the jab's two
# are appended. Everything before this index must be byte-identical to the baseline.
VANILLA_ARTICLE_ENTRIES = 15
JAB_CANCEL = 23


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_mlist(path: Path):
    """`(kind, anims, game_script, flags, blend, payload, raw, file_offset)` per entry."""
    data = Path(path).read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset, entries = 24, []
    for _ in range(count):
        start = offset
        kind, script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = list(struct.unpack_from('<' + 'Q' * n_anims, data, offset))
        offset = (offset + n_anims * 9 + 3) & ~3
        payload = data[offset:offset + size]
        offset += size
        entries.append((kind, anims, script, flags, blend, payload, data[start:offset], start))
    if offset != len(data):
        raise RuntimeError(f'{path}: {len(data) - offset} trailing bytes after {count} entries')
    return magic, motion_path, entries


def roundtrip_ok(path: Path) -> bool:
    data = Path(path).read_bytes()
    magic, motion_path, entries = parse_mlist(path)
    rebuilt = (struct.pack('<QQQ', magic, motion_path, len(entries))
               + b''.join(raw for _k, _a, _s, _f, _b, _p, raw, _o in entries))
    return rebuilt == data


def clip_visibility_and_scale(path: Path):
    anim = s.anim_data.read_anim(str(path))
    vis, scales = {}, {}
    for group in anim.groups:
        if group.group_type.name == 'Visibility':
            for node in group.nodes:
                for track in node.tracks:
                    if track.name == 'Visibility':
                        vis[node.name] = sorted({bool(v) for v in track.values})
        elif group.group_type.name == 'Transform':
            for node in group.nodes:
                if node.name != SWORD_BONE:
                    continue
                for track in node.tracks:
                    if track.name == 'Transform':
                        scales = sorted({round(float(v.scale[0]), 4) for v in track.values})
    return vis, scales


def set_visibility(path: Path, drawn: bool) -> None:
    anim = s.anim_data.read_anim(str(path))
    for group in anim.groups:
        if group.group_type.name != 'Visibility':
            continue
        for node in group.nodes:
            for track in node.tracks:
                if track.name == 'Visibility':
                    track.values = [drawn] * max(1, len(list(track.values)))
    anim.save(str(path))


def body_entry(tree: Path, slot: str, kind: str):
    for entry in parse_mlist(tree / BODY / slot / 'motion_list.bin')[2]:
        if entry[0] == hash40(kind):
            return entry
    raise RuntimeError(f'{slot}: no body motion entry for {kind}')


class Audit:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks: list[str] = []

    def check(self, ok: bool, message: str) -> bool:
        self.checks.append(('PASS  ' if ok else 'FAIL  ') + message)
        if not ok:
            self.failures.append(message)
        return ok

    def report(self) -> dict:
        return {'ok': not self.failures, 'checks': len(self.checks),
                'failures': self.failures}


def audit_slot(tree: Path, baseline: Path | None, slot: str, a: Audit) -> dict:
    folder = tree / ARTICLE / slot
    if not a.check(folder.is_dir(), f'{slot}: article folder present'):
        return {}

    mlist = folder / 'motion_list.bin'
    a.check(roundtrip_ok(mlist), f'{slot}: motion_list.bin re-serializes from its own parse')
    _magic, _path, entries = parse_mlist(mlist)
    by_kind = {e[0]: e for e in entries}
    report: dict = {'slot': slot, 'entries': len(entries)}

    # (1) every animation hash this build authored must name a real file, and it
    #     must be the extension-carrying name.
    present = {hash40(p.name) for p in folder.glob(f'*{ANIM_SUFFIX}')}
    for kind, (clip, _donor) in JAB_ENTRIES.items():
        entry = by_kind.get(hash40(kind))
        if not a.check(entry is not None, f'{slot}: motion_list has an entry for {kind}'):
            continue
        anims = entry[1]
        want = hash40(f'{clip}{ANIM_SUFFIX}')
        a.check(anims == [want],
                f'{slot}: {kind} names {clip}{ANIM_SUFFIX} ({want:#x}), '
                f'not the bare stem ({hash40(clip):#x})')
        a.check(all(x in present for x in anims),
                f'{slot}: {kind} animation hash resolves to a file in the folder')
        report[kind] = {'anim': f'{want:#x}', 'flags': entry[3], 'blend': entry[4]}

    # The two jab entries must be appended, not spliced into the middle: everything
    # before them is vanilla and has to stay byte-identical to the baseline.
    tail_kinds = [e[0] for e in entries[VANILLA_ARTICLE_ENTRIES:]]
    a.check(tail_kinds == [hash40(k) for k in JAB_ENTRIES],
            f'{slot}: the last two entries are jab_open then jab_to_open')

    # (2) the vanilla entries are byte-identical to the baseline, and the two jab
    #     ones differ from their donors only in kind and animation name.
    if baseline is not None:
        base_entries = parse_mlist(baseline / ARTICLE / slot / 'motion_list.bin')[2]
        a.check(len(base_entries) == len(entries),
                f'{slot}: entry count unchanged from the baseline '
                f'({len(entries)} vs {len(base_entries)})')
        if len(base_entries) == len(entries):
            drifted = [i for i, (x, y) in enumerate(zip(entries[:VANILLA_ARTICLE_ENTRIES],
                                                        base_entries[:VANILLA_ARTICLE_ENTRIES]))
                       if x[6] != y[6]]
            a.check(not drifted,
                    f'{slot}: all {VANILLA_ARTICLE_ENTRIES} vanilla entries are '
                    f'byte-identical (drifted: {drifted})')
            # The fix is expected to change exactly the two appended entries.
            moved = [i for i in range(VANILLA_ARTICLE_ENTRIES, len(entries))
                     if entries[i][6] != base_entries[i][6]]
            a.check(moved == list(range(VANILLA_ARTICLE_ENTRIES, len(entries))),
                    f'{slot}: the jab entries are the only ones this delta changes '
                    f'(changed indices {moved})')
        for kind, (_clip, donor) in JAB_ENTRIES.items():
            new, old = by_kind.get(hash40(kind)), by_kind.get(hash40(donor))
            if not a.check(new is not None and old is not None,
                           f'{slot}: both {kind} and its donor {donor} are present'):
                continue
            a.check(new[2:6] == old[2:6],
                    f'{slot}: {kind} matches {donor} in game_script/flags/blend/payload')
            a.check(new[6][24:32] != old[6][24:32],
                    f'{slot}: {kind} carries its own animation name')

    # (3) the drawing decision, per state, is unchanged.
    def read_clip(clip: str):
        """(visibility, scale) for one clip, or a recorded failure if unreadable.

        A missing or corrupt clip must be a reported failure, not an exception: an
        audit that dies loudly is still caught by the caller, but one that reports
        what it managed to check and stops is how a PASS gets produced from a tree
        it never looked at.
        """
        try:
            return clip_visibility_and_scale(folder / f'{clip}{ANIM_SUFFIX}')
        except Exception as exc:  # noqa: BLE001 - ssbh_data_py raises its own type
            a.check(False, f'{slot}/{clip}: clip unreadable ({type(exc).__name__}: {exc})')
            return None, None

    for clip in HIDDEN_CLIPS:
        vis, scales = read_clip(clip)
        if vis is None:
            continue
        a.check(vis.get(MESH) == [False], f'{slot}/{clip}: {MESH} is not drawn')
        a.check(not scales or scales == [1.0], f'{slot}/{clip}: {SWORD_BONE} is unscaled')
    for clip, factor in {**FAIR_CLIPS, **JAB_CLIPS}.items():
        vis, scales = read_clip(clip)
        if vis is None:
            continue
        a.check(vis.get(MESH) == [True], f'{slot}/{clip}: {MESH} is drawn')
        a.check(scales == [factor], f'{slot}/{clip}: {SWORD_BONE} scale is {factor}')

    # (4) the body entries that carry the jab and the fair did not move.
    jab = body_entry(tree, slot, 'attack_11')
    a.check(jab[1] == [hash40(f'{JAB_BODY_CLIP}{ANIM_SUFFIX}')],
            f'{slot}: attack_11 still names {JAB_BODY_CLIP}')
    a.check(struct.unpack_from('<H', jab[5], len(jab[5]) - 2)[0] == JAB_CANCEL,
            f'{slot}: attack_11 cancel frame is still {JAB_CANCEL}')
    for kind in ('attack_12', 'attack_13'):
        a.check(body_entry(tree, slot, kind)[1] == jab[1],
                f'{slot}: {kind} still names {JAB_BODY_CLIP}')
    fair = body_entry(tree, slot, 'attack_air_f')
    a.check(fair[1] == [hash40(f'{FAIR_BODY_CLIP}{ANIM_SUFFIX}')],
            f'{slot}: attack_air_f still names {FAIR_BODY_CLIP}')

    # (5) the new clip names are declared, or they are not resolved at all.
    config = (tree / 'config.json').read_text(encoding='utf-8', errors='replace')
    for clip in JAB_CLIPS:
        name = f'{ARTICLE}/{slot}/{clip}{ANIM_SUFFIX}'
        a.check(name in config, f'{slot}: config.json declares {name}')
    return report


def audit_tree_scope(tree: Path, baseline: Path, a: Audit) -> dict:
    """Only the two esword motion lists may differ from the baseline."""
    allowed = {f'{ARTICLE}/{slot}/motion_list.bin' for slot in SLOTS}
    changed = []
    for path in sorted(baseline.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(baseline).as_posix()
        other = tree / rel
        if not other.is_file():
            changed.append(('missing', rel))
        elif sha256(path) != sha256(other):
            changed.append(('changed', rel))
    added = sorted(p.relative_to(tree).as_posix() for p in tree.rglob('*')
                   if p.is_file() and not (baseline / p.relative_to(tree)).is_file())
    a.check(all(kind == 'changed' and rel in allowed for kind, rel in changed),
            f'baseline tree differs only in the two esword motion lists (saw {changed})')
    a.check(not added, f'candidate adds no file to the baseline tree (added {added})')
    return {'changed': sorted(rel for _k, rel in changed), 'added': added}


def negative_controls(baseline: Path, a: Audit) -> None:
    """Each control must be caught; an audit that misses one fails the run."""
    with tempfile.TemporaryDirectory() as tmp:
        def fresh(name: str) -> Path:
            dst = Path(tmp) / name
            shutil.copytree(baseline, dst)
            return dst

        # C1: the shipped bug - the animation name hashed without the extension.
        tree = fresh('c1_stem_name')
        mlist = tree / ARTICLE / 'c06' / 'motion_list.bin'
        data = bytearray(mlist.read_bytes())
        struct.pack_into('<Q', data, len(data) - 48 + 24, hash40('jabtoopen'))
        mlist.write_bytes(bytes(data))
        probe = Audit()
        audit_slot(tree, baseline, 'c06', probe)
        a.check(bool(probe.failures),
                'control C1 (jab_to_open names the bare stem) is caught')

        # C2: the jab's own clip says not-drawn while its entry claims to open.
        tree = fresh('c2_hidden_clip')
        set_visibility(tree / ARTICLE / 'c06' / 'jabtoopen.nuanmb', False)
        probe = Audit()
        audit_slot(tree, baseline, 'c06', probe)
        a.check(any('drawn' in f for f in probe.failures),
                'control C2 (jab_to_open drawn=False) is caught')# C3: a jab body entry whose cancel frame moved would move the timing
    #     hardware already confirmed.
        tree = fresh('c3_cancel')
        body = tree / BODY / 'c06' / 'motion_list.bin'
        data = bytearray(body.read_bytes())
        entry = next(e for e in parse_mlist(body)[2] if e[0] == hash40('attack_11'))
        offset = entry[7] + len(entry[6]) - 2
        current = struct.unpack_from('<H', data, offset)[0]
        struct.pack_into('<H', data, offset, current + 1)
        body.write_bytes(bytes(data))
        probe = Audit()
        audit_slot(tree, baseline, 'c06', probe)
        a.check(any('cancel frame' in f for f in probe.failures),
                'control C3 (attack_11 cancel frame moved) is caught')

        # C4: a missing jab clip file must not be reported as a pass either.
        tree = fresh('c4_missing_clip')
        (tree / ARTICLE / 'c06' / 'jabtoopen.nuanmb').unlink()
        probe = Audit()
        audit_slot(tree, baseline, 'c06', probe)
        a.check(bool(probe.failures), 'control C4 (jab clip file missing) is caught')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--baseline', required=True, help='installed baseline mod tree')
    ap.add_argument('--candidate', help='full mod tree to check (defaults to --baseline)')
    ap.add_argument('--check', action='store_true', help='also run the negative controls')
    ap.add_argument('--out', help='write the JSON report here')
    args = ap.parse_args()

    baseline = Path(args.baseline)
    tree = Path(args.candidate) if args.candidate else baseline
    for path in (baseline, tree):
        if not path.is_dir():
            ap.error(f'{path} is not a directory')
        if not (path / 'config.json').is_file():
            ap.error(
                f'{path} has no config.json, so it looks like a two-file overlay rather '
                f'than a mod tree. This audit needs the whole tree, because it also has to '
                f'prove that nothing *else* moved. Copy the overlay onto the merged tree '
                f'first and point --candidate at that.')

    a = Audit()
    result: dict = {'baseline': str(baseline), 'candidate': str(tree), 'slots': {}}
    for slot in SLOTS:
        result['slots'][slot] = audit_slot(tree, baseline, slot, a)
    result['scope'] = audit_tree_scope(tree, baseline, a)
    result['files'] = {
        f'{ARTICLE}/{slot}/motion_list.bin': sha256(tree / ARTICLE / slot / 'motion_list.bin')
        for slot in SLOTS}
    result['baseline_files'] = {
        f'{ARTICLE}/{slot}/motion_list.bin': sha256(baseline / ARTICLE / slot / 'motion_list.bin')
        for slot in SLOTS}
    if args.check:
        negative_controls(baseline, a)
    result.update(a.report())

    text = json.dumps(result, indent=1, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + '\n', encoding='utf-8')
    for line in a.checks:
        print(line)
    for failure in a.failures:
        print('  ->', failure)
    print(f'checks={result["checks"]} failures={len(result["failures"])}')
    print('RESULT:', 'PASS' if result['ok'] else 'FAIL')
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())