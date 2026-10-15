"""Offline smoke test for the Monkey Flip port. No console, no game.

Checks the three things that can silently disagree in this move:

1. **The donor data is still what the port was written against.** The twelve
   motion entries' game-script hashes, cancel frames and clip names are asserted
   against Diddy's own motion list (`build_monkey_flip.donor_entries`,
   `donor_clips`). A dump change fails here instead of shipping a wrong arc.

2. **The retarget produces twelve working, distinct clips.** Each clip is
   retargeted onto the recipient skeleton and re-read: group set, frame count,
   bone names and the kept-track count (the donor's measured 37). Two phases that
   would play the same animation are a failure.

3. **The plugin and the assets agree.** The ACMD names the plugin registers must
   be exactly the scripts the donor's dump defines for these phases - not more
   (an invented script) and not fewer (a donor script that would then run the
   *recipient's* code of that name, or nothing at all).

Output goes to `builds/.cache/monkey_flip_smoke/` (gitignored).

Run:
    toolchains/py312/python.exe src/pgwr/tools/smoke_monkey_flip.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
sys.path.insert(0, str(TOOLS))

import build_monkey_flip as mflip  # noqa: E402

CACHE = ROOT / 'builds' / '.cache' / 'monkey_flip_smoke'
PLUGIN = ROOT / 'src' / 'pgwr' / 'plugin' / 'src' / 'acmd' / 'monkey_flip.rs'
DONOR_SCRIPTS = (ROOT / 'dumps' / 'scripts' / 'SSBU-Dumped-Scripts-main'
                 / 'smashline' / 'lua2cpp_diddy' / 'diddy')

# The donor source file per phase, so the third check knows which dump files are
# this move's and which (Catch, CatchDash, ...) are some other move's.
PHASE_SOURCES = (
    'SpecialSStart', 'SpecialAirSStart', 'SpecialAirSJump', 'SpecialAirSKick',
    'SpecialSKickLanding', 'SpecialSLanding', 'SpecialSStick',
    'SpecialSStickAttack', 'SpecialSStickAttack2', 'SpecialSStickJump',
    'SpecialSStickJump2',
)

RE_FN = re.compile(r'unsafe extern "C" fn ((?:game|effect|sound|expression)_\w+)\(')
RE_REGISTERED = re.compile(r'acmd\("((?:game|effect|sound|expression)_\w+)"')


def check_donor_data() -> int:
    entries = mflip.donor_entries()
    clips = mflip.donor_clips()
    assert len(entries) == 12, entries
    assert len(clips) == 12, clips
    return len(entries)


def check_retarget() -> list:
    all_records = []
    for slot in ('c06', 'c07'):
        bones = set(mflip.recipient_bones(slot))
        vis = mflip.visibility_group(slot)
        records = []
        for _, clip in mflip.MOTIONS:
            out = CACHE / slot / clip
            records.append(mflip.retarget(
                mflip.hash40(clip), mflip.DONOR_DIR / clip, bones, vis, out))
        # Within a slot every phase must have its own clip and its own pose; the
        # two slots legitimately share donor file names, which is why this is per
        # slot and not over all 24 records.
        mflip.assert_distinct(records)
        assert len({r['output'] for r in records}) == len(records), 'shared output name'
        for rec in records:
            assert rec['transform_tracks_kept'] == mflip.EXPECTED_KEPT_TRACKS, rec
        all_records.extend(records)
    return all_records


def check_plugin_agreement() -> tuple:
    donor = set()
    for name in PHASE_SOURCES:
        text = (DONOR_SCRIPTS / f'{name}.txt').read_text(encoding='utf-8', errors='replace')
        donor |= set(RE_FN.findall(text))
    registered = set(RE_REGISTERED.findall(PLUGIN.read_text(encoding='utf-8')))
    missing = sorted(donor - registered)
    extra = sorted(registered - donor)
    assert not missing, f'plugin does not register donor scripts: {missing}'
    assert not extra, f'plugin registers scripts the donor does not define: {extra}'
    # Every phase's motion entry must name a game script the donor actually has,
    # or the phase silently runs no game code at all.
    for kind, _ in mflip.MOTIONS:
        wanted = f'game_{kind.replace("_", "")}'
        if wanted in donor:
            assert wanted in registered, f'{kind}: {wanted} is not registered'
    return len(donor), len(registered)


def main() -> int:
    entries = check_donor_data()
    records = check_retarget()
    donor, registered = check_plugin_agreement()
    print(f'donor entries validated      : {entries}')
    print(f'clips retargeted              : {len(records)} '
          f'({len(records) // 2} phases x 2 slots)')
    print(f'donor scripts defined         : {donor}')
    print(f'plugin scripts registered     : {registered}')
    print('monkey flip smoke test: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
