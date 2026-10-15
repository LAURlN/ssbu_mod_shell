"""Reduce a captured Skyline log to the Monkey Flip story, one attempt per line.

The question this answers is narrow and has changed since the first version: the
leap's CATCH entry is now known to be live and to enclose the victim, so the
question is no longer "did a box get created" but

  * which build produced this log at all,
  * was the leap ACMD reached (the CATCH calls and the module arming ran),
  * where is the box actually stored, relative to the fighter,
  * did the engine register a capture, and if so from which path,
  * how close did the victim get while the box was live,
  * did the victim ever enter a clung status.

Every pattern below names the source line that prints it, so this file can be
re-checked against the sources instead of trusted:

  build         monkey_flip_status.rs  install()
  START         monkey_flip_status.rs  main(START)
  MOTION        monkey_flip_status.rs  motion()
  CATCH ACMD    monkey_flip.rs         game_specialairsjump, frame 7
  GRABARM       monkey_flip.rs         game_specialairsjump, frame 7
  CATCHGEO      monkey_flip_status.rs  log_catch_boxes()
  CATCHW        monkey_flip_status.rs  main(JUMP)
  NOCATCH *     monkey_flip_status.rs  main(JUMP), observer branch
  CATCH HANDOFF monkey_flip_status.rs  main(JUMP)
  JUMP tick     monkey_flip_status.rs  main(JUMP)
  JUMP kick     monkey_flip_status.rs  main(JUMP)
  CLING         monkey_flip_status.rs  main(STICK)
  OBS           lib.rs                 gamewatch_frame()

Three traps this version is written to avoid, each of which cost real time:

  * It reports the build banner first. A log with no banner came from an NRO
    older than the banner, which already caused one test to be read as if it
    exercised code that was not in the binary.
  * OBS prints only when the status or the catch *changes* (lib.rs:561), and only
    within 60 frames of leaving the Monkey Flip block (lib.rs:552-558). Absence
    of an OBS line is not evidence of anything, and the previous version inferred
    "no capture" from exactly that silence.
  * It never states a conclusion the log does not carry. Where the log is
    ambiguous it prints the samples and says so.

Read-only and streaming, so it is safe on a 100 MB log.

Usage:
    python scratch/summarise_mflip_log.py logs/switch-20260918-0100.log
    python scratch/summarise_mflip_log.py logs/*.log
    python scratch/summarise_mflip_log.py --all-frames logs/switch-*.log
"""
import re
import sys
from pathlib import Path

# 0x50000000 is this codebase's own "no link" sentinel: the initial value of
# LAST_ACTIVE in diagnostics.rs and the unavailable marker in monkey_flip_status.rs.
NO_LINK = 0x50000000

# -999.0 is what catch_center() returns when the centre pointer fails its range
# check, which is how an out-of-bounds entry surfaces in the log.
UNSET = -999.0

VEC = r'\(\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)\)'
HEX = r'(0x[0-9a-f]+)'
BOOL = r'(\w+)'

# Group counts are asserted at start-up. Every index below is written by hand, and
# a wrong index does not raise: it silently reports a coordinate as a distance.
# That is how the first version of this file went wrong, so the contract is now
# checked instead of trusted.
GROUP_COUNTS = {}

BANNER = re.compile(r'\[MGW-MFLIP\] build (.+?)\s*$')
ATTEMPT_START = re.compile(r'\[MGW-MFLIP\] START entry=(\d+) situation=(\d+) ')
STALE_CATCH = re.compile(
    r'\[MGW-MFLIP\] START cleared a stale catch is_catch=' + BOOL + r' link=' + HEX
)
MOTION = re.compile(r'\[MGW-MFLIP\] MOTION requested_name=(\S+)')
CATCH_ACMD = re.compile(r'\[MGW-MFLIP\] CATCH ACMD frame=([-\d.]+) situation=(\d+)')
GRABARM = re.compile(
    r'\[MGW-MFLIP\] GRABARM acmd7 rebound=' + BOOL + r' sleep=' + BOOL
    + r' size_mul=([\d.]+) check_front=' + BOOL + r' size2_raw=' + HEX
)
GRABDIS = re.compile(r'\[MGW-MFLIP\] GRABDIS acmd(\d+) rebound=' + BOOL)
CATCHGEO = re.compile(
    r'\[MGW-MFLIP\] CATCHGEO (\S+) centre0=' + VEC + r' centre1=' + VEC
    + r' centre2=' + VEC + r' self=' + VEC + r' size2=' + HEX
)
CATCHW = re.compile(
    r'\[MGW-MFLIP\] CATCHW entry=\d+ elapsed=(\d+) is_catch=' + BOOL
    + r' capture=' + HEX + r' link=' + HEX
    + r' grab0=' + BOOL + r' grab1=' + BOOL + r' grab2=' + BOOL + r' grab3=' + BOOL
    + r' anchor=' + VEC + r' self=' + VEC + r' victim=' + HEX + r' vs=' + HEX
    + r' vsit=(\d+) vpos=' + VEC + r' dist=([\d.]+) rebound=' + BOOL
)
NOCATCH = re.compile(
    r'\[MGW-MFLIP\] NOCATCH elapsed=(\d+) victim=' + HEX + r' dist=([\d.]+) gated_at=([\d.]+)'
    + r' vstatus=' + HEX + r' is_catch=' + BOOL + r' capture=' + HEX + r' link=' + HEX
    + r' grab0=' + BOOL + r' grab1=' + BOOL + r' grab2=' + BOOL + r' grab3=' + BOOL
)
NOCATCH_FAR = re.compile(
    r'\[MGW-MFLIP\] NOCATCH FAR elapsed=(\d+) victim=' + HEX + r' dist=([\d.]+) gated_at=([\d.]+)'
)
NOCATCH_NOVICTIM = re.compile(r'\[MGW-MFLIP\] NOCATCH NOVICTIM elapsed=(\d+)')
HANDOFF = re.compile(
    r'\[MGW-MFLIP\] CATCH HANDOFF elapsed=(\d+) capture=' + HEX + r' via=(\w+)'
)
JUMP_TICK = re.compile(r'\[MGW-MFLIP\] JUMP tick entry=\d+ elapsed=(\d+)')
KICK_INPUT = re.compile(
    r'\[MGW-MFLIP\] JUMP kick input elapsed=(\d+) kick_frame=(\d+) window_open=(\w+)'
)
CLING = re.compile(
    r'\[MGW-MFLIP\] CLING frame=([\d.]+) motion=' + HEX + r' end=([\d.]+) is_catch=' + BOOL
    + r' is_linked=' + BOOL + r' capture=' + HEX + r' link=' + HEX + r' grab_live=' + BOOL
    + r' victim=' + HEX + r' vstatus=' + HEX + r' vsit=(\d+) vpos=' + VEC + r' self=' + VEC
)
OBS = re.compile(
    r'\[MGW-MFLIP\] OBS entry=\d+ status=(\d+) \(0x([0-9a-f]+)\) prev=0x[0-9a-f]+ ours=(\w+)'
    + r' situation=(\d+) catch=' + BOOL + r' link=' + HEX
)

GROUP_COUNTS.update({
    'STALE_CATCH': (STALE_CATCH, 2),
    'CATCH_ACMD': (CATCH_ACMD, 2),
    'GRABARM': (GRABARM, 5),
    'GRABDIS': (GRABDIS, 2),
    'CATCHGEO': (CATCHGEO, 14),
    'CATCHW': (CATCHW, 22),
    'NOCATCH': (NOCATCH, 12),
    'NOCATCH_FAR': (NOCATCH_FAR, 4),
    'NOCATCH_NOVICTIM': (NOCATCH_NOVICTIM, 1),
    'HANDOFF': (HANDOFF, 3),
    'JUMP_TICK': (JUMP_TICK, 1),
    'KICK_INPUT': (KICK_INPUT, 3),
    'CLING': (CLING, 17),
    'OBS': (OBS, 6),
})


def self_check():
    """Fail loudly if a pattern stops agreeing with the sources it was written for."""
    bad = []
    for name, (pattern, expected) in sorted(GROUP_COUNTS.items()):
        got = pattern.groups
        if got != expected:
            bad.append(f'{name}: {got} capture groups, expected {expected}')
    if bad:
        raise SystemExit(
            'summarise_mflip_log.py is out of step with the sources it parses:\n  '
            + '\n  '.join(bad)
            + '\n\nFix the indices in this file against the println! format strings; do not'
            '\nre-run it on a log until it agrees, or it will report wrong numbers quietly.'
        )


def _vec(groups, offset):
    return (float(groups[offset]), float(groups[offset + 1]), float(groups[offset + 2]))


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _close(a, b, tol=0.05):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def _fmt(v):
    return '(' + ', '.join(f'{c:.2f}' for c in v) + ')'


class Attempt:
    def __init__(self, situation):
        self.situation = situation
        self.motions = []
        self.catch_acmd = 0
        self.grabarm = None
        self.grabdis = None
        self.stale_catch = None
        self.geo = []          # (phase, c0, c1, c2, self)
        self.catchw = []       # dicts
        self.nocatch = []      # dicts
        self.far = []
        self.no_victim = 0
        self.handoffs = []     # (elapsed, capture, via)
        self.cling = []        # dicts
        self.obs = []          # (status, catch, link)
        self.leap_last = None
        self.kick = None

    def grab2_rows(self):
        rows = [r for r in self.catchw if r['grab2']]
        rows += [r for r in self.nocatch if r['grab2']]
        return rows

    def capture_evidence(self):
        """Every place the log claims a capture, with the line it came from.

        OBS is included but marked, because it samples the engine directly and is
        therefore the only witness that does not depend on our own status code.
        """
        found = []
        for elapsed, capture, via in self.handoffs:
            found.append(f'CATCH HANDOFF  elapsed={elapsed:<3} via={via:<7} capture=0x{capture:x}')
        for r in self.catchw:
            if r['is_catch']:
                found.append(
                    f'CATCHW         elapsed={r["elapsed"]:<3} is_catch=true '
                    f'capture=0x{r["capture"]:x} link=0x{r["link"]:x}'
                )
        for r in self.nocatch:
            if r['is_catch']:
                found.append(
                    f'NOCATCH        elapsed={r["elapsed"]:<3} is_catch=true '
                    f'capture=0x{r["capture"]:x}'
                )
        for r in self.cling:
            if r['is_catch']:
                found.append(
                    f'CLING          frame={r["frame"]:<6} is_catch=true '
                    f'is_linked={r["is_linked"]} capture=0x{r["capture"]:x}'
                )
        for status, catch, link in self.obs:
            if catch:
                found.append(
                    f'OBS (engine)   status=0x{status:x} catch=true link=0x{link:x}'
                )
        return found


def _geometry(attempt):
    """Where the box centre is stored, measured against the fighter's own origin."""
    out = []
    if not attempt.geo:
        out.append('  no CATCHGEO line: log_catch_boxes() was never reached, so the')
        out.append('  leap ACMD did not run at all on this attempt')
        return out

    usable = [g for g in attempt.geo if g[3][0] > UNSET + 1.0]
    out.append('  box centre vs fighter origin (2.5 is the intended y offset):')
    for phase, c0, _c1, c2, self_ in attempt.geo:
        if c2[0] <= UNSET + 1.0:
            out.append(f'    {phase:<7} centre2 out of range (pointer failed the range check)')
            continue
        out.append(
            f'    {phase:<7} centre2={_fmt(c2)} self={_fmt(self_)} '
            f'delta={_fmt(_sub(c2, self_))}'
        )

    if not usable:
        out.append('  every centre2 sample was out of range, so nothing can be concluded')
        return out

    deltas = [(_p, _sub(c2, self_)) for _p, _c0, _c1, c2, self_ in usable]
    centres = [c2 for _p, _c0, _c1, c2, _self in usable]

    if all(_close(d, (0.0, 0.0, 0.0)) for _p, d in deltas):
        out.append('  VERDICT: the stored centre equals the fighter origin on every sample.')
        out.append('    The 2.5-unit y offset was never applied, so the box has sat at the')
        out.append('    fighter\'s feet, 2.5 units below where it was assumed, in every run.')
        out.append('    First thing to try is the module\'s own positioning, not the ACMD:')
        out.append('    GrabModule::set_constraint / GrabModule::relocate.')
    elif all(_close(d, (0.0, 2.5, 0.0)) for _p, d in deltas):
        out.append('  VERDICT: fighter-relative, at the intended (0.00, 2.50, 0.00) offset.')
        out.append('    The box is exactly where it has always been assumed to be, so every')
        out.append('    positional explanation is exhausted. The remaining suspect is the')
        out.append('    status side: our JUMP is a status Smashline added, the donor\'s is')
        out.append('    native, and the engine may not evaluate grab entries for it.')
        out.append('    Next isolation: issue a CATCH from a status the engine already knows.')
    elif all(_close(d, deltas[0][1]) for _p, d in deltas):
        out.append(f'  VERDICT: fighter-relative, but at offset {_fmt(deltas[0][1])},')
        out.append('    which is not the intended (0.00, 2.50, 0.00).')
    elif all(_close(c, centres[0]) for c in centres):
        out.append(f'  VERDICT: the centre is fixed in world space at {_fmt(centres[0])}.')
        out.append('    It does not follow the fighter at all, so the box has never been where')
        out.append('    the ACMD arguments said it was.')
    elif all(_close(c, (0.0, 0.0, 0.0)) for c in centres):
        out.append('  VERDICT: the centre is the stage origin.')
    else:
        out.append('  VERDICT: the centre tracks neither the fighter nor any fixed point.')
        out.append('    See the samples above; nothing further is claimed from them.')
    return out


def _reach(attempt):
    out = []
    rows = attempt.grab2_rows()
    if rows:
        closest = min(rows, key=lambda r: r['dist'])
        live = sorted(r['elapsed'] for r in rows)
        out.append(
            f'  closest approach with a live (grab2=true) box: dist={closest["dist"]:.2f} '
            f'at elapsed={closest["elapsed"]}'
        )
        out.append(
            f'  live box on {len(rows)} sample(s), elapsed {live[0]}..{live[-1]}; '
            f'the reach only needs to cover that window'
        )
    else:
        out.append('  no sample had grab2=true: the leap never held a live box while logging')
    if attempt.catchw:
        rebound = sum(1 for r in attempt.catchw if r['rebound'])
        out.append(
            f'  rebound true on {rebound} of {len(attempt.catchw)} sampled window frame(s); '
            'if that is 0 the activation never took'
        )
    if attempt.no_victim:
        out.append(f'  {attempt.no_victim} NOCATCH NOVICTIM sample(s): no second fighter was found')
    return out


def _victim(attempt):
    out = []
    if attempt.cling:
        statuses = []
        for r in attempt.cling:
            if not statuses or statuses[-1] != r['vstatus']:
                statuses.append(r['vstatus'])
        out.append(
            '  victim status under our cling: '
            + ' -> '.join(f'0x{s:x}' for s in statuses)
        )
        routed = [s for s in statuses if s not in (0x0, 0x1, 0x6)]
        if routed:
            out.append(f'  the victim did leave the plain states; ids seen: '
                       + ', '.join(f'0x{s:x}' for s in routed))
        else:
            out.append('  the victim stayed in 0x0/0x1/0x6 (wait-ish) throughout: it was')
            out.append('  never routed into a clung status by the capture')
    if attempt.nocatch:
        seen = []
        for r in attempt.nocatch:
            if not seen or seen[-1] != r['vstatus']:
                seen.append(r['vstatus'])
        out.append('  victim status during the window: ' + ' -> '.join(f'0x{s:x}' for s in seen))
    return out


def summarise(path, all_frames):
    if not path.is_file():
        print(f'{path}: not a file')
        return

    attempts = []
    current = None
    banner = None
    banners = []
    unattributed = {'catch_acmd': 0, 'grabarm': 0, 'geo': 0}

    with path.open('r', encoding='utf-8', errors='replace') as handle:
        for raw in handle:
            line = raw.rstrip('\n')

            m = BANNER.search(line)
            if m:
                banner = m.group(1)
                banners.append(banner)
                continue

            m = ATTEMPT_START.search(line)
            if m:
                if current:
                    attempts.append(current)
                current = Attempt(m.group(2))
                current.entry = int(m.group(1))
                continue

            if CATCH_ACMD.search(line):
                unattributed['catch_acmd'] += 1
            if GRABARM.search(line):
                unattributed['grabarm'] += 1
            if CATCHGEO.search(line):
                unattributed['geo'] += 1

            if current is None:
                continue

            m = MOTION.search(line)
            if m:
                current.motions.append(m.group(1))
                continue

            m = STALE_CATCH.search(line)
            if m:
                current.stale_catch = (m.group(1), int(m.group(2), 16))
                continue

            m = CATCH_ACMD.search(line)
            if m:
                current.catch_acmd += 1
                continue

            m = GRABARM.search(line)
            if m:
                # rebound, sleep, size_mul, check_front, size2_raw
                current.grabarm = (
                    m.group(1) == 'true', m.group(2) == 'true', float(m.group(3)),
                    m.group(4) == 'true', int(m.group(5), 16),
                )
                continue

            m = GRABDIS.search(line)
            if m:
                current.grabdis = (int(m.group(1)), m.group(2) == 'true')
                continue

            m = CATCHGEO.search(line)
            if m:
                g = m.groups()
                current.geo.append((
                    g[0], _vec(g, 1), _vec(g, 4), _vec(g, 7), _vec(g, 10),
                ))
                continue

            m = CATCHW.search(line)
            if m:
                g = m.groups()
                current.catchw.append({
                    'elapsed': int(g[0]),
                    'is_catch': g[1] == 'true',
                    'capture': int(g[2], 16),
                    'link': int(g[3], 16),
                    'grab2': g[6] == 'true',
                    # g[8..10] are anchor, g[11..13] self, g[14] victim, g[15] vs,
                    # g[16] vsit, g[17..19] vpos. g[17] is a coordinate, not a distance.
                    'dist': float(g[20]),
                    'rebound': g[21] == 'true',
                })
                continue

            m = NOCATCH.search(line)
            if m:
                g = m.groups()
                current.nocatch.append({
                    'elapsed': int(g[0]),
                    'dist': float(g[2]),
                    'vstatus': int(g[4], 16),
                    'is_catch': g[5] == 'true',
                    'capture': int(g[6], 16),
                    'link': int(g[7], 16),
                    'grab2': g[10] == 'true',
                })
                continue

            m = NOCATCH_FAR.search(line)
            if m:
                # group(2) is the victim id, not the distance; the distance is group(3).
                current.far.append((int(m.group(1)), float(m.group(3))))
                continue

            m = NOCATCH_NOVICTIM.search(line)
            if m:
                current.no_victim += 1
                continue

            m = HANDOFF.search(line)
            if m:
                current.handoffs.append((int(m.group(1)), int(m.group(2), 16), m.group(3)))
                continue

            m = JUMP_TICK.search(line)
            if m:
                current.leap_last = int(m.group(1))
                continue

            m = KICK_INPUT.search(line)
            if m:
                current.kick = (int(m.group(1)), int(m.group(2)))
                continue

            m = CLING.search(line)
            if m:
                g = m.groups()
                # g[0] frame, g[1] motion, g[2] end, g[3] is_catch, g[4] is_linked,
                # g[5] capture, g[6] link, g[7] grab_live, g[8] victim,
                # g[9] vstatus, g[10] vsit, g[11..13] vpos, g[14..16] self.
                current.cling.append({
                    'frame': float(g[0]),
                    'is_catch': g[3] == 'true',
                    'is_linked': g[4] == 'true',
                    'capture': int(g[5], 16),
                    'link': int(g[6], 16),
                    'vstatus': int(g[9], 16),
                })
                continue

            m = OBS.search(line)
            if m:
                current.obs.append((int(m.group(2), 16), m.group(5) == 'true', int(m.group(6), 16)))

    if current:
        attempts.append(current)

    print(f'=== {path} ===')

    if not banner:
        print('  BUILD: no banner line. This log came from an NRO older than the banner,')
        print('         so it does not prove anything about the build it is labelled with.')
    elif len(set(banners)) > 1:
        print(f'  BUILD: {len(set(banners))} different banners in one file: {sorted(set(banners))}')
    else:
        print(f'  BUILD: {banner}')

    if not attempts:
        if unattributed['catch_acmd'] or unattributed['grabarm']:
            print(f'  lines exist outside any attempt (catch_acmd={unattributed["catch_acmd"]}, '
                  f'grabarm={unattributed["grabarm"]}); no START was seen, so the status main')
            print('  never ran and the ACMD fired without our status block.')
            return
        print('  no MFLIP attempts found; was the plugin loaded for this capture?')
        return

    captured = sum(1 for a in attempts if a.capture_evidence())
    print(f'  {len(attempts)} attempt(s), {captured} with a registered capture')
    print()

    for index, a in enumerate(attempts, 1):
        print(f'  attempt #{index}: start_situation={a.situation} '
              f'catch_acmd={a.catch_acmd} '
              f'leap_last_elapsed={"none" if a.leap_last is None else a.leap_last} '
              f'kick={"none" if a.kick is None else a.kick[0]}')
        if a.motions:
            print(f'    motions requested: {", ".join(a.motions)}')
        if a.grabarm:
            print(f'    GRABARM: rebound={a.grabarm[0]} sleep={a.grabarm[1]} '
                  f'size_mul={a.grabarm[2]} check_front={a.grabarm[3]} '
                  f'size2_raw=0x{a.grabarm[4]:x}')
        else:
            print('    GRABARM: absent, so the module arming in the frame-7 block never ran')
        if a.grabdis:
            print(f'    GRABDIS at acmd{a.grabdis[0]}: rebound={a.grabdis[1]}')
        if a.stale_catch:
            print(f'    a stale catch was cleared at START: is_catch={a.stale_catch[0]} '
                  f'link=0x{a.stale_catch[1]:x}')

        for line in _geometry(a):
            print(line)
        for line in _reach(a):
            print(line)

        evidence = a.capture_evidence()
        if evidence:
            print('    CAPTURE REGISTERED:')
            for line in evidence:
                print(f'      {line}')
        else:
            print('    capture: never registered, on any witness')

        for line in _victim(a):
            print(line)

        if a.far:
            print(f'    {len(a.far)} NOCATCH FAR sample(s), nearest dist={min(d for _e, d in a.far):.2f}')
        if a.obs:
            transitions = [(s, c) for s, c, _l in a.obs]
            print(f'    OBS sampled the engine on {len(a.obs)} change(s); '
                  f'catch was true on {sum(1 for _s, c in transitions if c)}; '
                  'silence between changes means nothing')
        else:
            print('    OBS printed nothing. It only fires on a change or within 60 frames of')
            print('    leaving the block, so this is not evidence either way.')
        if all_frames:
            for r in a.catchw:
                print(f'      CATCHW  elapsed={r["elapsed"]:<3} grab2={r["grab2"]!s:<5} '
                      f'dist={r["dist"]:.2f} is_catch={r["is_catch"]} link=0x{r["link"]:x}')
            for r in a.cling:
                print(f'      CLING   frame={r["frame"]:<6} is_catch={r["is_catch"]!s:<5} '
                      f'is_linked={r["is_linked"]!s:<5} vstatus=0x{r["vstatus"]:x} '
                      f'capture=0x{r["capture"]:x}')
        print()


def main(argv):
    self_check()
    all_frames = '--all-frames' in argv
    files = [a for a in argv[1:] if not a.startswith('-')]
    if not files:
        print(__doc__)
        return 1
    for arg in files:
        summarise(Path(arg), all_frames)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
