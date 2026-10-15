"""Summarise pgwr capture telemetry from the final boot in a log (1.0.0).

Usage: toolchains/py312/python.exe tools/summarise_pgwr_capture_log.py <log>
Smoke test: --smoke (fixture includes an older successful boot to check isolation).
Read-only; reports observations without inferring contact, animation or causation.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re


def summarise(text):
    lines = text.splitlines()
    boots = [(i, re.search(r'\[PGWR\] BOOT v(\d+\.\d+\.\d+)', line).group(1))
             for i, line in enumerate(lines) if re.search(r'\[PGWR\] BOOT v(\d+\.\d+\.\d+)', line)]
    start, version = boots[-1] if boots else (0, None)
    run = lines[start:]
    marker_names = ['CAPTURE READY', 'CAPTURE REFUSED', 'CAPTURE EVENT', 'CAPTURE ACCEPT',
                    'CAPTURE SETUP', 'CATCH HANDOFF', 'CLING entry', 'VICTIMSTATUS']
    markers = {marker: sum(marker in line for line in run) for marker in marker_names}
    victims = [line for line in run if '[PGWR-MFLIP] VICTIM ' in line]
    donor = [line for line in run if '[PGWR-DIDDY]' in line]
    return {'boot_version': version, 'boot_line': start + 1, 'run_lines': len(run),
            'markers': markers,
            'port_attempts': sum('[PGWR-MFLIP] enter: entry' in line for line in run),
            'port_victim_samples': len(victims),
            'port_catch_true_samples': sum('is_catch=true' in line for line in victims),
            'port_clung_victim_samples': sum('vstatus=0xf0 ' in line for line in victims),
            'nearest_opponent_available_samples': sum('near=0xffffffff' not in line for line in victims),
            'donor_catch_true_samples': sum('catch=true' in line for line in donor),
            'donor_statuses': dict(Counter(re.search(r'status=(0x[0-9a-f]+)', line).group(1)
                                          for line in donor if ' STATUS ' in line)),
            'limitations': 'No inference of contact, visual animation, vanilla controls or cause from absent telemetry.'}


def smoke():
    fixture = '\n'.join(['[PGWR] BOOT v0.20.4', '[PGWR-MFLIP] CAPTURE ACCEPT',
        '[PGWR] BOOT v0.20.5', '[PGWR-MFLIP] CAPTURE REFUSED invalid event/fighter range',
        '[PGWR-MFLIP] enter: entry 0 colour 6',
        '[PGWR-MFLIP] VICTIM JUMP is_catch=false vstatus=0x0 near=0xffffffff',
        '[PGWR-MFLIP] [PGWR-DIDDY] STATUS entry 0 status=0x1e8 catch=true',
        '[PGWR-MFLIP] [PGWR-DIDDY] STATUS entry 0 status=0x1ea catch=false'])
    result = summarise(fixture)
    assert result['boot_version'] == '0.20.5' and result['boot_line'] == 3
    assert result['markers']['CAPTURE ACCEPT'] == 0 and result['markers']['CAPTURE REFUSED'] == 1
    assert result['port_attempts'] == 1 and result['port_catch_true_samples'] == 0
    assert result['donor_statuses'] == {'0x1e8': 1, '0x1ea': 1}
    assert result['donor_catch_true_samples'] == 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', nargs='?')
    p.add_argument('--smoke', action='store_true')
    args = p.parse_args()
    if args.smoke:
        smoke(); print('PASS: final-boot isolation and port/donor fixture')
    else:
        assert args.log, 'Supply a log path'
        print(json.dumps(summarise(Path(args.log).read_text(encoding='utf-8', errors='replace')), indent=2))


if __name__ == '__main__':
    main()
