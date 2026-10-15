"""P1-CATALOG scratch: decode fighter/miigunner/motion/body/c00/motion_list.bin.

Uses the mod repo's byte-faithful reader
(mods/ssbu_mod_new/src/pgwr/tools/mlist.py, read-only import) and resolves three
independent hash namespaces by computing hash40 = (len << 32) | crc32(name):

  * motion kind      - candidate names generated in this file
  * game script      - hash40("game_" + name) candidates
  * animation        - clip file names taken from the local ARC path index

A hash that matches no candidate stays unresolved and is reported as such; no
name is invented from the game's on-screen move name.

Usage (workspace root):
  python mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/dump_motion_list.py \
      gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin
"""
import importlib.util
import json
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
MLIST = os.path.join(ROOT, 'mods', 'ssbu_mod_new', 'src', 'pgwr', 'tools', 'mlist.py')
ARC_INDEX = os.path.join(ROOT, 'mods', 'ssbu_mod_new', 'dumps', 'decoded', 'arc_files.tsv')


def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def load_mlist():
    spec = importlib.util.spec_from_file_location('pgwr_mlist', MLIST)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def candidate_names():
    kinds = {}
    scripts = {}
    for name in dict.fromkeys(kind_candidates()):
        kinds[hash40(name)] = name
        for cand in (f'game_{name}', f'game_{name}s', f'game_{name}hit'):
            scripts.setdefault(hash40(cand), cand)
    return kinds, scripts


def kind_candidates():
    out = [
        # normal attacks
        'attack11', 'attack12', 'attack13', 'attackdash', 'attackhi3', 'attacklw3',
        'attackairn', 'attackairf', 'attackairb', 'attackairhi', 'attackairlw',
        'attacks3s', 'attacks4s', 'attackhi4', 'attacklw4',
        'attackhi4charge', 'attacklw4charge', 'attacks3scharge', 'attacks4charge',
        'attackairf', 'attackairb',
        # landing / squat / dash / wait helpers
        'landing', 'landinglight', 'landingheavy', 'landingairn', 'landingairf',
        'landingairb', 'landingairhi', 'landingairlw', 'squat', 'squatwait',
        'squatrv', 'dash', 'turn', 'run', 'walk', 'wait', 'waititem',
        # specials by stem + index + phase
        'specialhi1', 'specialhi2', 'specialhi3', 'specialhi2squat', 'specialhi3b',
        'specialhi3f', 'specialhi3start', 'specialhi3end',
        'speciallw1', 'speciallw2', 'speciallw3',
        'specialairhi1', 'specialairhi2squat', 'specialairhi3end', 'specialairhi3start',
    ]
    for stem in ('specialn', 'specialairn', 'specialhi', 'specialairhi', 'speciallw',
                 'specialairlw'):
        for i in (1, 2, 3):
            for suffix in ('start', 'loop', 'end', 'hold', 'cancel', 'jumpcancel',
                           'squat', 'hit', 'hitl', 'endl', 'loopl', 'startl'):
                out.append(f'{stem}{i}{suffix}')
    for stem in ('specials', 'specialairs'):
        for i in (1, 2, 3):
            for b in (1, 2, 3):
                out.append(f'{stem}{i}{b}')
    out += [
        'final', 'finalair', 'finalstart', 'finalend', 'finalairstart', 'finalairend',
        'throwf', 'throwb', 'throwhi', 'throwlw',
        'thrownf', 'thrownb', 'thrownhi', 'thrownlw',
        'catch', 'catchattack', 'catchdash', 'catchpull', 'catchwait', 'catchturn',
        'capturepulledhi', 'capturewaithi', 'capturedamagehi', 'capturejump',
        'capturewaitlw', 'capturedamagelw',
        'damagehi', 'damagelw', 'damagen', 'damageair', 'damageelec',
        'escapeair', 'escapef', 'escapeb', 'escapen', 'rebound',
        'guard', 'guardon', 'guardoff', 'justshieldoff', 'guarddamage',
        'fall', 'fallf', 'fallb', 'jumpsquat', 'jumpf', 'jumpb',
        'jumpaerialf', 'jumpaerialb', 'steppose', 'stepback', 'stepairpose',
        'stepfall', 'stepjump', 'turndash', 'turnrun',
        'share', 'sharewait', 'sharefinish', 'sharedamage',
        'share_cliff', 'share_finish', 'share_sleep', 'share_fistdown', 'share_damage',
        'win1', 'win2', 'win3', 'lose', 'menupose', 'menupose2',
        'appealhil', 'appealhir', 'appeallwl', 'appeallwr', 'appealsl', 'appealsr',
        'swim', 'swimf', 'swimup', 'swimturn', 'swimend', 'swimrise', 'swimupdamage',
        'entryl', 'entryr', 'sleeploop', 'sleepstart', 'sleepend', 'swallowed',
        'downwaitu', 'downstandu', 'downboundu', 'downattacku', 'downbacku',
        'downdamageu', 'downwaitd', 'downstandd', 'downboundd', 'downattackd',
        'downbackd', 'downdamaged', 'downspotd',
        'cliffwait', 'cliffcatch', 'cliffattack', 'cliffclimb', 'cliffescape',
        'cliffjump1', 'cliffjump2',
        'passive', 'passivestandb', 'passivestandf', 'passivewall',
        'passivewalljump', 'passiveceil',
        'slip', 'slipwait', 'slipattack', 'slipescapeb', 'slipescapef', 'slipstand',
        'slipdown',
        'getup', 'getupwait', 'wakeup', 'rise', 'bounce', 'edgecancelslide',
        'stopceil', 'stopwall', 'ceildamage', 'walldamage', 'missfoot', 'ottoto',
        'ottottowait', 'pass', 'ladderwait', 'ladderup', 'ladderdown',
        'laddercatchl', 'laddercatchr',
    ]
    return out


def load_anim_names():
    names = {}
    with open(ARC_INDEX, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            p = line.rstrip('\n').split('\t')[0]
            if not p.startswith('fighter/miigunner/') or not p.endswith('.nuanmb'):
                continue
            names.setdefault(hash40(os.path.basename(p)), p)
    return names


def main():
    mlist = load_mlist()
    path = sys.argv[1]
    kinds, scripts = candidate_names()
    anims = load_anim_names()
    ml = mlist.parse(path)
    assert mlist.encode(ml) == ml['data'], 'motion list round trip failed'
    out = {
        'motion_path_field': f'{ml["motion_path"]:#012x}',
        'entry_count': len(ml['entries']),
        'roundtrip': 'ok',
        'entries': [],
    }
    for i, e in enumerate(ml['entries']):
        out['entries'].append({
            'index': i,
            'offset': e['start'],
            'kind_hash': f'{e["kind"]:#012x}',
            'kind': kinds.get(e['kind']),
            'game_script_hash': f'{e["gs"]:#012x}',
            'game_script': scripts.get(e['gs']),
            'flags': f'{e["flags"]:#06x}',
            'blend': e['blend'],
            'n_anims': e['n'],
            'anims': [f'{h:#012x}' for h in e['anims']],
            'anim_paths': [anims.get(h) for h in e['anims']],
            'size': e['size'],
            'cancel': e['cancel'],
        })
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == '__main__':
    main()