"""Classify a pgwr Hero side-B crash-tail log so each repair step is settled, not ranked.

Version 1.1.0. Reads `sd:/ultimate/pgwr_hero_s_log.txt` (or any copy) and counts the
observations that separate the level-3 chain into *reached* vs *never reached*. Built
because T-0034 had to rank ten level-3 hypotheses because no log existed; T-0052
obtained the log and could exclude eight of ten by counting. 1.1.0 adds the donor
lightning event (the owned arrival signal since 2026-10-02) and the bolt's head/tail
work values (the travel discriminator). Re-run it on every new log before theorising
about Kazap again.

    python tools/audit_hero_side_b_log.py evidence/.../pgwr_hero_s_log_card_2026-10-02.txt
    python tools/audit_hero_side_b_log.py <log> --json out.json

Smoke test (no console needed; asserts the T-0052 findings on the archived card log):
    python tools/audit_hero_side_b_log.py --smoke

Tier B: pure text counting over a named input file. It measures the LOG, never the
game, so it can say "the arrival branch was never taken in this log" and cannot say
why. Absence of a line is evidence about the log, not about console behaviour.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

VERSION = '1.1.0'
ROOT = Path(__file__).resolve().parents[1]

# observation -> (regex, what a non-zero count proves)
OBSERVATIONS = [
    ('boot',            r'BOOT v(?P<v>\S+)',
     'which build wrote this log; compare against the NRO you think is on the card'),
    ('registered',      r'REGISTERED c0[67]',
     'costume gate and statuses registered'),
    ('entry',           r'ENTRY entry=',
     'the side-B entry status ran'),
    ('to_kazap',        r'TRANSITION 0x1fe->0x1fc',
     'the charge reached Kazap: level 3 was actually attempted'),
    ('activate',        r'ACTIVATE lightning frame=10',
     'game script reached frame 10 and raised ACTIVATE_LIGHTNING (T-0052 addition)'),
    ('spawn_begin',     r'SPAWN lightning begin',
     'the spawn loop ran'),
    ('spawn_complete',  r'SPAWN lightning complete count=(\d+)',
     'articles were generated; the final count is the per-move bolt total'),
    ('bolt_main',       r'LIGHTNING regular life=(\d+)',
     "the bolt's own Lua Main ran with this life"),
    ('bolt_sample',     r'BOLT life=(\d+)(?: head=([-\d.]+) tail=([-\d.]+) dir=([-\d.]+))? '
                       r'move_dist=([-\d.]+) threshold=([-\d.]+) owner_ok=(\w+)',
     'T-0052 per-frame sample: the donor extension work values, move_dist against '
     'threshold, and owner_ok (owner_ok=false is cause (b); move_dist frozen is (a))'),
    ('lightning_event', r'EVENT begin kind=0x214e64eedd',
     "the donor's own lightning event reached the owned receiver; one per bolt is "
     'the signal the owned arrival flag is raised from'),
    ('arrival_raised',  r'EVENT arrival kind=0x214e64eedd',
     'the owned arrival flag was raised: Kazap may now enter the finisher'),
    ('arrival_suppressed', r'EVENT arrival suppressed|EVENT arrival already raised',
     'the owned arrival was deliberately not raised; read which reason was logged'),
    ('map',             r'MAP lightning begin',
     "the bolt's MapCorrection ran (it travels)"),
    ('arrived',         r'LIGHTNING arrived distance=([-\d.]+)$',
     'the arrival predicate fired AND the owned state was raised (finisher may follow)'),
    ('arrived_no_state', r'LIGHTNING arrived .*but no owned state',
     'the predicate FIRED but owner(w) was null, so the flag was never raised; this is '
     'cause (b) and is a real failure even though "arrived" matched'),
    ('append',          r'TRANSITION 0x1fc->0x1fd',
     'the finisher was entered'),
    ('end_of_clip',     r'TRANSITION 0x1fc->0x0',
     'Kazap ended at the clip end instead: the "never arrived" signature'),
    ('fail',            r'FAIL ',
     'a guarded path refused; read the message, do not count it as noise'),
]

# a step is only *reached* if at least one earlier step produced lines
REACH_CHAIN = ['to_kazap', 'activate', 'spawn_begin', 'spawn_complete',
               'bolt_main', 'map', 'lightning_event', 'arrival_raised', 'append']

# sha256 of the archived pre-T-0052 card log, so its verdict is worded correctly.
PRE_T0052_LOGS = {
    '5311f05919164096f31a040f6f33edca4dd41d0f17d42fd50aa047b250dbdb99',
}

# Logs that predate the T-0052 arrival fix: the event arrived but nothing raised the
# owned flag, so `arrival_raised` being 0 there is the old fault, not a new one.
PRE_ARRIVAL_FIX_LOGS = {
    '5311f05919164096f31a040f6f33edca4dd41d0f17d42fd50aa047b250dbdb99',
    'ff7afc8cdef4dacd692c050eba6064967023078210c3acb2c61e5f853d94e48f',
}

# Lines added by T-0052. A log written before that build cannot contain them, so their
# absence means "not instrumented", NOT "never reached" - conflating the two is how a
# tool talks you into fixing the wrong step. Detected by requiring the new-log marker.
T0052_ONLY = {'activate': 'ACTIVATE lightning frame=10', 'bolt_sample': 'BOLT life='}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(path: Path) -> dict:
    counts: dict[str, int] = {k: 0 for k, _, _ in OBSERVATIONS}
    arrived_distances: list[float] = []
    boot: list[str] = []
    lives: set[str] = set()
    heads: list[float] = []
    tails: list[float] = []
    dirs: list[float] = []
    thresholds: set[str] = set()
    distances: list[float] = []
    owners: set[str] = set()
    fails: list[str] = []
    completed: list[int] = []
    for raw in path.read_text(errors='replace').splitlines():
        line = raw.replace('[PGWR-HERO-S] ', '')
        for key, pattern, _ in OBSERVATIONS:
            m = re.search(pattern, line)
            if not m:
                continue
            counts[key] += 1
            if key == 'boot':
                boot.append(m.group('v'))
            elif key == 'bolt_main':
                lives.add(m.group(1))
            elif key == 'bolt_sample':
                lives.add(m.group(1))
                if m.group(2) is not None:      # head/tail/dir added in tool 1.1.0
                    heads.append(float(m.group(2)))
                    tails.append(float(m.group(3)))
                    dirs.append(float(m.group(4)))
                distances.append(float(m.group(5)))
                thresholds.add(m.group(6))
                owners.add(m.group(7))
            elif key == 'arrived':
                arrived_distances.append(float(m.group(1)))
            elif key == 'spawn_complete':
                completed.append(int(m.group(1)))
            elif key == 'fail':
                fails.append(line)
    return {'file': path.as_posix(), 'sha256': sha(path), 'lines':
            len(path.read_text(errors='replace').splitlines()),
            'counts': counts, 'boots': boot, 'bolt_lives': sorted(lives),
            'thresholds': sorted(thresholds), 'owner_ok_values': sorted(owners),
            'head_range': [min(heads), max(heads)] if heads else None,
            'tail_range': [min(tails), max(tails)] if tails else None,
            'dir_values': sorted(set(dirs)),
            'max_move_dist': max(distances) if distances else None,
            'min_move_dist': min(distances) if distances else None,
            'move_dist_samples': len(distances),
            'max_spawn_count': max(completed) if completed else None,
            'arrived_distances': arrived_distances,
            'fail_lines': fails}


def conclude(report: dict) -> list[str]:
    """Turn counts into the smallest set of statements the log actually supports."""
    c, out = report['counts'], []
    kazaps = c['to_kazap']
    if kazaps == 0:
        return ['No Kazap was attempted in this log: nothing about level 3 is settled.']
    out.append(f'{kazaps} Kazap attempt(s), {c["spawn_begin"]} bolt spawn(s).')
    # A T-0052-only line absent from a pre-T-0052 log is not a failure.
    pre = report['sha256'] in PRE_T0052_LOGS or all(c[k] == 0 for k in T0052_ONLY)
    for step in REACH_CHAIN:
        if c[step] > 0:
            out.append(f'  REACHED      {step} ({c[step]})')
        elif step in T0052_ONLY and pre:
            out.append(f'  NOT INSTRUMENTED {step} (line added by T-0052)')
        else:
            out.append(f'  NEVER REACHED {step} (0)')
    if not pre:
        out.append('This log contains the T-0052 diagnostics, so BOLT/ACTIVATE '
                   'absences are real failures.')
    if report['sha256'] in PRE_ARRIVAL_FIX_LOGS:
        out.append('This log predates the event-driven arrival fix; arrival_raised '
                   'cannot appear in it.')
    graded = [s for s in REACH_CHAIN
              if not (s in T0052_ONLY and pre)]
    # The arrival question is answered from BOLT samples whether or not an earlier
    # step also looks unreached: a negative control (synthetic_stalled.txt) showed
    # that short-circuiting on the first gap hides the one number that matters.
    if c['arrived_no_state']:
        out.append('CAUSE (b): the arrival predicate fired but owner(w) was null, so '
                   'LIGHTNING_ARRIVED was never raised. Fix the owner lookup, not the '
                   'threshold.')
    if report['head_range']:
        lo, hi = report['head_range']
        tlo, thi = report['tail_range']
        if hi - lo < 0.05 and thi - tlo < 0.05:
            out.append(f'TRAVEL: the bolt\'s head/tail work values never change '
                       f'(head {lo}..{hi}, tail {tlo}..{thi}) while MapCorrection runs, '
                       'so the donor extension machinery is not writing them. This is '
                       'the bolt-not-travelling defect, separate from the arrival.')
        else:
            out.append(f'TRAVEL: head {report["head_range"]} tail '
                       f'{report["tail_range"]} dir {report["dir_values"]} - the '
                       'extension work values are moving.')
    if c['lightning_event']:
        out.append(f'The donor lightning event reached the receiver {c["lightning_event"]}x '
                   f'for {c["spawn_begin"]} bolt(s).')
    if c['arrival_raised']:
        out.append(f'OWNED ARRIVAL raised {c["arrival_raised"]}x from that event.')
    if c['arrival_raised'] == 0 and c['lightning_event'] > 0 and \
            report['sha256'] in PRE_ARRIVAL_FIX_LOGS:
        out.append('The event arrived but nothing raised the owned arrival: this log '
                   'predates the 2026-10-02 event-driven arrival fix.')
    if c['arrived'] == 0:
        out.append('CAUSE (a) candidate: the arrival predicate never fired.')
        if report['move_dist_samples']:
            lo, hi = report['min_move_dist'], report['max_move_dist']
            thr = float(report['thresholds'][0]) if report['thresholds'] else None
            out.append(f'  move_dist range {lo}..{hi} against threshold {report["thresholds"]}'
                       f', owner_ok seen: {report["owner_ok_values"]}')
            if thr is not None and hi < thr:
                out.append(f'  => move_dist never reached {thr}: the distance signal '
                           'does not arrive. Fix the predicate or its inputs, not the '
                           'timing.')
            elif thr is not None:
                out.append('  => move_dist DID reach the threshold, so the cause is '
                           'not the distance: re-read owner_ok.')
            if 'true' not in report['owner_ok_values']:
                out.append('  => owner_ok was never true: the owner lookup is the '
                           'likely cause, not the distance.')
        else:
            out.append('  (no BOLT samples: this log predates the T-0052 diagnostic, '
                       'so (a) and (b) are still indistinguishable.)')
    elif c['arrived'] and not c['append']:
        out.append(f'The predicate fired {c["arrived"]}x (distances '
                   f'{report["arrived_distances"][:5]}) but the finisher was never '
                   'entered: look at the APPEND transition, not the predicate.')
    first_missing = next((s for s in graded if c[s] == 0), None)
    if first_missing is None:
        out.append('VERDICT: the whole chain including the finisher ran at least once.')
    else:
        out.append(f'VERDICT: first unreached step in the chain is {first_missing}. '
                   'Do not theorise about later steps; fix this one and re-run the log '
                   '(AGENTS.md rule 11).')
    if c['end_of_clip']:
        out.append(f'{c["end_of_clip"]} Kazap(s) left through the clip end (0x1fc->0x0).')
    if kazaps > c['end_of_clip'] + c['append']:
        out.append(f'  {kazaps - c["end_of_clip"] - c["append"]} Kazap(s) left by some '
                   'other route (hit/interrupt); those exits are not in this tool.')
    if report['fail_lines']:
        out.append(f'{len(report["fail_lines"])} FAIL line(s): {report["fail_lines"][:5]}')
    else:
        out.append('No FAIL lines: every guarded path accepted its input.')
    return out


def smoke() -> int:
    """Assert T-0052's findings on the archived 2026-10-01/02 card log."""
    path = ROOT / 'evidence/2026-10-02_pgwr_T-0052/pgwr_hero_s_log_card_2026-10-02.txt'
    if not path.exists():
        print('smoke: archived log missing', file=__import__('sys').stderr)
        return 1
    r = parse(path)
    c = r['counts']
    assert r['sha256'] == '5311f05919164096f31a040f6f33edca4dd41d0f17d42fd50aa047b250dbdb99', r['sha256']
    assert c['to_kazap'] == 13, c['to_kazap']
    assert c['spawn_begin'] == 26, c['spawn_begin']
    assert c['bolt_main'] == 26, c['bolt_main']
    assert c['map'] == 780, c['map']   # 780 'begin' lines (1560 counting 'complete')
    assert c['arrived'] == 0 and c['append'] == 0, (c['arrived'], c['append'])
    assert c['end_of_clip'] == 4, c['end_of_clip']
    assert c['fail'] == 0, c['fail']
    assert r['bolt_lives'] == ['30'], r['bolt_lives']
    assert r['max_spawn_count'] == 2, r['max_spawn_count']
    assert '0.20.15' in r['boots'] and '0.20.16' in r['boots'], r['boots']
    # this log predates the T-0052 diagnostics, so they must be absent
    assert c['activate'] == 0 and c['bolt_sample'] == 0
    assert c['arrived_no_state'] == 0
    lines = conclude(r)
    body = '\n'.join(lines)
    assert 'NOT INSTRUMENTED activate' in body, body
    assert 'CAUSE (a) candidate' in body, body
    assert '(a) and (b) are still indistinguishable' in body, body

    # Tier A: the 2026-10-02 card log (v0.20.17, the build with the T-0052 BOLT
    # sample) settles Kazap cause (a) - the distance signal never arrives - and
    # shows the donor lightning event reaching the owned receiver once per bolt.
    # Pinning those numbers here means a future edit cannot quietly change what
    # this task's conclusion rests on.
    path2 = ROOT / 'evidence/2026-10-02_pgwr_T-0052/pgwr_hero_s_log_card2_2026-10-02.txt'
    if not path2.exists():
        print('smoke: 2026-10-02 card log missing', file=__import__('sys').stderr)
        return 1
    r2 = parse(path2)
    c2 = r2['counts']
    assert r2['sha256'] == 'ff7afc8cdef4dacd692c050eba6064967023078210c3acb2c61e5f853d94e48f', r2['sha256']
    assert c2['to_kazap'] == 15 and c2['spawn_begin'] == 30, (c2['to_kazap'], c2['spawn_begin'])
    assert c2['bolt_sample'] == 32, c2['bolt_sample']
    assert r2['max_move_dist'] == 0.0 and r2['min_move_dist'] == 0.0, r2['max_move_dist']
    assert r2['owner_ok_values'] == ['true'], r2['owner_ok_values']
    assert c2['lightning_event'] == 30, c2['lightning_event']
    assert c2['arrival_raised'] == 0 and c2['append'] == 0, (c2['arrival_raised'], c2['append'])
    assert c2['fail'] == 0, c2['fail']
    body2 = '\n'.join(conclude(r2))
    assert '=> move_dist never reached 300.0' in body2, body2
    assert 'The event arrived but nothing raised the owned arrival' in body2, body2

    # Negative control. A grader that cannot separate success from failure, or cannot
    # tell cause (a) from cause (b), is worse than no grader: it points the next agent
    # at the wrong step. The first version of this tool failed exactly here (it
    # short-circuited on the first unreached step and hid the BOLT numbers), so the
    # controls are part of the smoke test, not optional.
    tmp = ROOT / 'scratch/2026-10-02_buffy'
    tmp.mkdir(parents=True, exist_ok=True)
    head = ('[PGWR-HERO-S] BOOT v9.9.9\n'
            '[PGWR-HERO-S] TRANSITION 0x1fe->0x1fc hold=26 frame=26.0 end=34.0\n'
            '[PGWR-HERO-S] ACTIVATE lightning frame=10\n'
            '[PGWR-HERO-S] SPAWN lightning begin status=0x1fc count=0\n'
            '[PGWR-HERO-S] LIGHTNING regular life=30\n'
            '[PGWR-HERO-S] SPAWN lightning complete count=1\n')
    maps = ('[PGWR-HERO-S] MAP lightning begin\n'
            '[PGWR-HERO-S] MAP lightning complete\n') * 4
    head_with_maps = head + maps
    def samples(vals, ok, head=0.0):
        return ''.join(f'[PGWR-HERO-S] BOLT life={l} head={head} tail=0.0 dir=1.0 '
                       f'move_dist={v} threshold=300.0 owner_ok={ok} x=0.0 y=0.0\n'
                       for l, v in vals)
    cases = {
        'ok': (head_with_maps
               + '[PGWR-HERO-S] EVENT begin kind=0x214e64eedd status=0x1fc\n'
               + '[PGWR-HERO-S] EVENT complete kind=0x214e64eedd result=1\n'
               + '[PGWR-HERO-S] EVENT arrival kind=0x214e64eedd bolts=2 frame=44.0\n'
               + samples([(30, 300.0), (25, 250.0), (20, 200.0), (15, 150.0),
                          (10, 100.0), (5, 50.0), (2, 20.0)], 'true', head=300.0)
               + '[PGWR-HERO-S] LIGHTNING arrived distance=300.0\n'
               + '[PGWR-HERO-S] APPEND lightning arrived; switching to the finisher\n'
               + '[PGWR-HERO-S] TRANSITION 0x1fc->0x1fd hold=26 frame=44.0 end=77.0\n',
               'whole chain including the finisher ran'),
        'stalled': (head_with_maps
                    + '[PGWR-HERO-S] EVENT begin kind=0x214e64eedd status=0x1fc\n'
                    + '[PGWR-HERO-S] EVENT complete kind=0x214e64eedd result=1\n'
                    + '[PGWR-HERO-S] EVENT arrival kind=0x214e64eedd bolts=2 frame=44.0\n'
                    + samples([(30, 0.0), (25, 0.0), (20, 0.0), (15, 0.0),
                               (10, 0.0), (5, 0.0), (2, 0.0)], 'true')
                    + '[PGWR-HERO-S] TRANSITION 0x1fc->0x0 hold=26 frame=77.0 end=77.0\n',
                    'the distance signal does not arrive'),
        'ownerfail': (head_with_maps
                      + samples([(30, 300.0), (25, 250.0), (20, 200.0), (15, 150.0),
                                 (10, 100.0), (5, 50.0), (2, 20.0)], 'false')
                      + '[PGWR-HERO-S] LIGHTNING arrived distance=300.0 but no owned state\n'
                      + '[PGWR-HERO-S] TRANSITION 0x1fc->0x0 hold=26 frame=77.0 end=77.0\n',
                      'Fix the owner lookup, not the threshold'),
        'no_travel': (head + samples([(30, 0.0), (25, 0.0), (20, 0.0), (15, 0.0),
                                      (10, 0.0), (5, 0.0), (2, 0.0)], 'true')
                      + '[PGWR-HERO-S] TRANSITION 0x1fc->0x0 hold=26 frame=77.0 end=77.0\n',
                      'first unreached step in the chain is map'),
    }
    for name, (text, expected) in cases.items():
        p = tmp / f'_smoke_{name}.txt'
        p.write_text(text)
        got = '\n'.join(conclude(parse(p)))
        assert expected in got, f'{name}: expected {expected!r} in\n{got}'
        p.unlink()
    print('smoke: OK', VERSION, '(real log + 3 negative controls)')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('log', nargs='?', help='path to pgwr_hero_s_log.txt (or a copy)')
    ap.add_argument('--json', help='write the report here')
    ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    if a.smoke:
        return smoke()
    if not a.log:
        ap.error('a log path is required unless --smoke')
    report = parse(Path(a.log))
    report['tool'], report['version'] = Path(__file__).name, VERSION
    for line in conclude(report):
        print(line)
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=2) + '\n')
        print('wrote', a.json)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())