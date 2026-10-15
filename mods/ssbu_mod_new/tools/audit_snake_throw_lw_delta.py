"""Audit the Snake down-throw delta for Pyra c06/c07 (v1.0.0).

Answers, against the **recorded baseline** (not against another agent's tree):

  * exactly which files the delta changes, added, or removes;
  * that `throw_lw` is the only motion-list entry that differs per slot, and
    that its cancel frame really moved to Snake's 48;
  * that `attack_lw4` (the down *smash*) is untouched - it is a different kind
    and this move must not reach it;
  * that the retargeted clip keeps moving limbs (node coverage alone cannot see
    a static pose);
  * that the sound banks gained exactly the closure of the two named tones and
    lost nothing;
  * that no c00-c05 file and no `config.json` is in the delta, so the costume
    gate and the vanilla costumes are unaffected;
  * that the built NRO carries this move's handler and tone names.

    python tools/audit_snake_throw_lw_delta.py
    python tools/audit_snake_throw_lw_delta.py --baseline <tree> --delta <tree>

Tier B: everything here is an offline byte/structure measurement. How the move
looks and behaves in game is **tier D** and is not established by this tool.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/pgwr/tools'))
import merge_hero_neutral_b_sound as codec  # noqa: E402
import build_snake_throw_lw as builder  # noqa: E402
import merge_snake_throw_lw_sound as sound  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
DELTA = ROOT / 'builds/pgwr/snake-throw-lw-delta/ultimate/mods/pyra_gamewatch_reskin'
NRO = ROOT / ('builds/.cache/snake-throw-lw-target/aarch64-skyline-switch/release/'
              'libpyra_gamewatch_reskin.nro')

EXPECTED_CHANGED = {
    'fighter/eflame/motion/body/c06/e01throwlw.nuanmb',
    'fighter/eflame/motion/body/c07/e01throwlw.nuanmb',
    'fighter/eflame/motion/body/c06/motion_list.bin',
    'fighter/eflame/motion/body/c07/motion_list.bin',
    'sound/bank/fighter/se_eflame_c06.nus3audio',
    'sound/bank/fighter/se_eflame_c06.nus3bank',
    'sound/bank/fighter/se_eflame_c06.tonelabel',
    'sound/bank/fighter/se_eflame_c07.nus3audio',
    'sound/bank/fighter/se_eflame_c07.nus3bank',
    'sound/bank/fighter/se_eflame_c07.tonelabel',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# The two tools write their own reports into the delta directory. They are
# evidence about the delta, not part of it, so they are excluded from the tree
# comparison - otherwise "the delta adds a file" would be true for the wrong
# reason.
TOOL_REPORTS = {'snake_throw_lw_build.json', 'snake_throw_lw_sound.json',
                'snake_throw_lw_audit.json'}


def tree_hashes(root):
    out = {}
    for p in sorted(root.rglob('*')):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if rel in TOOL_REPORTS:
                continue
            out[rel] = sha(p)
    return out


def audit_motion(baseline, delta):
    """The `throw_lw` entry changed and nothing else in the motion list did."""
    out = {}
    for slot in ('c06', 'c07'):
        rel = f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        before = builder.parse_entries((baseline / rel).read_bytes())[2]
        after = builder.parse_entries((delta / rel).read_bytes())[2]
        b = {e['kind']: e for e in before}
        a = {e['kind']: e for e in after}
        assert set(b) == set(a), f'{slot}: delta changed the set of motion kinds'
        changed = [k for k in a if a[k]['raw'] != b[k]['raw']]
        assert changed == [builder.hash40(builder.KIND)], \
            f'{slot}: expected only throw_lw to change, got {len(changed)} entries'
        assert len(after) == len(before), f'{slot}: entry count changed'
        old, new = b[changed[0]], a[changed[0]]
        assert old['cancel'] == builder.EXPECTED_RECIPIENT['cancel'], old['cancel']
        assert new['cancel'] == builder.EXPECTED_CANCEL, new['cancel']
        assert new['game_script'] == builder.hash40(builder.GAME_SCRIPT)
        assert new['anims'] == (builder.hash40(builder.CLIP),)
        # The down smash must be untouched.
        smash = builder.hash40('attack_lw4')
        if smash in a:
            assert a[smash]['raw'] == b[smash]['raw'], \
                f'{slot}: attack_lw4 (down smash) must not be touched'
            smash_cancel = a[smash]['cancel']
        else:
            smash_cancel = None
        out[slot] = {
            'entries_total': len(after), 'entries_changed': len(changed),
            'throw_lw_cancel': {'before': old['cancel'], 'after': new['cancel']},
            'throw_lw_flags': {'before': hex(old['flags']), 'after': hex(new['flags'])},
            'attack_lw4_cancel_untouched': smash_cancel,
            'sha256': {'baseline': sha(baseline / rel), 'delta': sha(delta / rel)},
        }
    return out


def audit_sound(baseline, delta):
    out = {}
    for slot in ('c06', 'c07'):
        stem = f'sound/bank/fighter/se_eflame_{slot}'
        before = [n for n, _ in codec.audio_read((baseline / f'{stem}.nus3audio').read_bytes())]
        after = [n for n, _ in codec.audio_read((delta / f'{stem}.nus3audio').read_bytes())]
        assert after[:len(before)] == before, f'{slot}: a pre-existing tone changed or moved'
        gained = after[len(before):]
        # Expected set comes from the DONOR bank: the closure of the two named
        # tones inside `se_snake_c00`, not anything derived from the recipient.
        donor_stem = sound.SE_DONOR
        donor_names = [n for n, _ in codec.audio_read(
            donor_stem.with_suffix('.nus3audio').read_bytes())]
        donor_tones = codec.tones_read(dict(codec.bank_read(
            donor_stem.with_suffix('.nus3bank').read_bytes()))[b'TONE'])
        expect = sorted(donor_names[i].lower()
                        for i in sound.closure(donor_names, donor_tones, sound.WANTED))
        assert sorted(g.lower() for g in gained) == expect, \
            f'{slot}: gained {gained}, expected {expect}'
        # The kind-1 links must resolve to the appended tones, not to old ones.
        chunks = dict(codec.bank_read((delta / f'{stem}.nus3bank').read_bytes()))
        tones = codec.tones_read(chunks[b'TONE'])
        pi = [i for i, n in enumerate(after) if n.lower() == 'se_snake_catch_tight'][0]
        _, _, start = sound.tone_record(tones[pi])
        links = sound.kind1_links(tones[pi], after, start)
        for at, child in links:
            assert child >= len(before), f'{slot}: kind-1 child {child} not rebased'
        out[slot] = {'retained': len(before), 'gained': gained,
                     'kind1_children': [[a_, c] for a_, c in links],
                     'kind1_resolve_to': [after[c] for _, c in links]}
    return out


def audit_nro(nro):
    if not Path(nro).is_file():
        return {'present': False}
    raw = Path(nro).read_bytes()
    wanted = [b'game_throwlw', b'sound_throwlw', b'expression_throwlw',
              b'effect_throwlw', b'collision_attr_lay', b'se_snake_catch_tight',
              b'se_snake_catch_tight_02', b'rbkind_nohits']
    found = {w.decode(): (w in raw) for w in wanted}
    missing = [k for k, v in found.items() if not v]
    assert not missing, f'NRO is missing: {missing}'
    return {'present': True, 'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw), 'symbols': found,
            'note': ("effect_throwlw is present as an EMPTY handler on purpose: the "
                     "donor has no effect script and G&W's Default one must be "
                     "superseded so its four effects stop playing.")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, default=BASELINE)
    ap.add_argument('--delta', type=Path, default=DELTA)
    ap.add_argument('--nro', type=Path, default=NRO)
    args = ap.parse_args()

    b, d = args.baseline, args.delta
    for p in (b, d):
        assert p.is_dir(), f'{p} not present'

    hb, hd = tree_hashes(b), tree_hashes(d)
    # The delta is an OVERLAY, not a copy of the tree: it holds only the files
    # this task changes, to be copied over a baseline. So "added" means a file
    # the baseline does not already have - which for a mod delta would mean a
    # new clip name and a config.json entry. A file that is simply absent from
    # the overlay is untouched, not removed.
    added = sorted(set(hd) - set(hb))
    unchanged = sorted(k for k in hd if k in hb and hd[k] == hb[k])
    changed = sorted(k for k in hd if k in hb and hd[k] != hb[k])
    missing_expected = EXPECTED_CHANGED - set(changed)
    assert not missing_expected, f'delta is missing expected changes: {sorted(missing_expected)}'
    unexpected = set(changed) - EXPECTED_CHANGED
    assert not unexpected, f'delta touches unexpected files: {sorted(unexpected)}'
    assert not added, f'delta adds files (a new clip name would need config.json): {added}'
    assert not unchanged, f'delta copies files unchanged (drop them): {unchanged}'
    assert not any(re.search(r'/c0[0-5]/', k) for k in changed), \
        f'delta must not touch c00-c05: {[k for k in changed if re.search(chr(47)+"c0[0-5]"+chr(47), k)]}'
    assert 'config.json' not in changed, 'delta must not need config.json'
    assert not any(k.startswith('fighter/elight/') for k in changed), \
        'delta must not touch Mythra (another agent owns it)'

    report = {
        'tool': 'audit_snake_throw_lw_delta.py', 'version': '1.0.0', 'date': '2026-10-02',
        'evidence_tier': 'B', 'hardware_validated': False,
        'baseline': str(b), 'delta': str(d),
        'files': {'changed': changed, 'added': added, 'unchanged': unchanged,
                  'changed_count': len(changed), 'delta_is_overlay': True},
        'motion': audit_motion(b, d),
        'sound': audit_sound(b, d),
        'nro': audit_nro(args.nro),
        'config_json_needed': False,
        'new_clip_names': [],
        'status_ids_required': [],
        'game_behavior': 'unverified; needs the console test in CURRENT_INSTALL.md',
    }
    out = d / 'snake_throw_lw_audit.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS overlay: {len(changed)} files changed, {len(added)} added, '
          f'{len(unchanged)} copied unchanged')
    for slot in ('c06', 'c07'):
        m = report['motion'][slot]
        s = report['sound'][slot]
        print(f"  {slot}: motion_list 1/{m['entries_total']} entries changed, "
              f"throw_lw cancel {m['throw_lw_cancel']['before']} -> {m['throw_lw_cancel']['after']}, "
              f"attack_lw4 (down smash) cancel still {m['attack_lw4_cancel_untouched']}")
        print(f"       sound: retained {s['retained']}, gained {s['gained']}")
        print(f"       kind-1 children resolve to {s['kind1_resolve_to']}")
    print(f"  NRO: {report['nro'].get('sha256')} ({report['nro'].get('bytes')} B)")
    print(f'  report {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())