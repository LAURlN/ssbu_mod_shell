"""Audit the Ness back throw on Mythra c06/c07 and emit the integration delta (v1.0.0).

Checks the *whole* change set against a recorded baseline and writes a
mergeable delta. It does not build anything and it does not install anything.

Baseline: the collective 0.20.19 package (`builds/pgwr/0.20.19/...`), which is
what the card holds. Every assertion below is a property that must hold for the
delta to be safe to hand an installer, and three of them have negative controls
so "PASS" is not the tool agreeing with itself.

What it establishes (tier B, offline):

1. **The motion-list delta is one byte.** `throw_b` differs from the baseline at
   exactly offset 62 (cancel 36 -> 53) and no other entry in the list moved.
   All three other throws and all four victim (`thrown_*`) entries are
   byte-identical to the baseline.
2. **The clip name did not have to change.** Donor and recipient both name
   `e01throwb.nuanmb`, so the delta adds no new file name and needs no
   `config.json` entry; the file is an in-place override of a file the base game
   already has in that costume group.
3. **The retarget kept the bones that matter.** 66 of the donor's 68 transform
   nodes exist on Mythra's skeleton; the two dropped are `Bat`/`BatL` (Ness's
   baseball bat), no case-only match happened, and the limb chain including the
   `Throw` bone that carries the victim attachment measurably moves.
4. **The donor's absolute throw numbers are the ones in the binary.** The two
   `ATTACK_ABS` lines and the release are compared against the pinned donor text
   field by field, so a typo in a constant fails here.
5. **Donor-owned resources were merged into recipient-owned assets.**
   `NESS_PSI_RUSH` is in both `ef_elight_c06/c07.eff`, the three `se_ness_*`
   tones and four `vc_ness_attack*` tones are in the recipient banks, and
   `seq_ness_rnd_attack` is in `elight.sqb`. Nothing is shipped under a donor
   fighter folder.
6. **The gating is install-time and costume-scoped**, from the Rust source, and
   c00-c05 are untouched by the whole delta.

What it cannot establish: anything about behaviour. No console, no emulator, no
in-game observation. See CURRENT_INSTALL.md for the manual test.

    python -B tools/audit_ness_throw_b.py --check
    python -B tools/audit_ness_throw_b.py --candidate <dir> --baseline <pkg> --delta <out.json>
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

ROOT = Path(__file__).resolve().parents[1]
from mlist import parse, hash40  # noqa: E402

DONOR_ACMD = ROOT / 'refs/ness_throw_b/donor_acmd'
RUST = ROOT / 'src/pgwr/plugin/src/mythra/ness_throw_b.rs'
GAMEDATA = ROOT.parents[1] / 'gamedata/ssbu-13.0.4/files'
DEFAULT_BASELINE = ROOT / 'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
SLOTS = ('c06', 'c07')
DONOR_CLIP = 'e01throwb.nuanmb'

# The donor's own absolute throw numbers, read from the pinned text. Compared
# field by field against the Rust below, so a mistyped constant fails here.
DONOR_ATTACK_ABS = [
    ('*FIGHTER_ATTACK_ABSOLUTE_KIND_THROW', '0', '11.0', '135', '130', '0', '15'),
    ('*FIGHTER_ATTACK_ABSOLUTE_KIND_CATCH', '0', '3.0', '361', '100', '0', '60'),
]
DONOR_RELEASE_FRAME = '27.0'
DONOR_CAMERA = 'macros::CHECK_FINISH_CAMERA(agent, -5, 18)'
DONOR_CANCEL = 53
# The three donor-owned resource groups, as the ACMD names them.
DONOR_RESOURCES = {
    'effect': ['ness_psi_rush'],
    'sound': ['se_ness_throw_pk01', 'se_ness_throw_pk02', 'se_ness_pk_s',
              'seq_ness_rnd_attack'],
    'voice': ['vc_ness_attack01', 'vc_ness_attack02', 'vc_ness_attack03', 'vc_ness_attack04'],
}
# Things the donor does NOT do, which Mythra's own script does. Recorded so a
# reviewer does not read them as porting slips.
DELIBERATE_OMISSIONS = {
    'REVERSE_LR': 'Ness throw_b omits it; 6 of 11 sampled fighters do too (see SOURCE.json)',
    'pickup ATTACK box + set_catch_only_all': 'Ness catches with the ATTACK_ABS(CATCH) pair alone',
    'AttackModule::clear_all after ATK_HIT_ABS': 'Ness does not clear',
    'FT_ATTACK_ABS_CAMERA_QUAKE': 'not in the donor',
    'set_throw_finish_zoom_rate / set_throw_finish_offset':
        'no FighterCutInManager accessor in the pinned skyline-smash 315e4e8; dropped, not guessed',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def donor_text():
    return (DONOR_ACMD / 'ness__ThrowB.txt').read_text(encoding='utf-8')


def check_donor_constants(rust):
    """The Rust must carry the donor's numbers, not a lookalike."""
    text = donor_text()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('macros::ATTACK_ABS(agent, *FIGHTER_ATTACK_ABSOLUTE_KIND_'):
            args = re.findall(r'(?:Hash40::new\("[a-z_]+"\)|\*?[A-Za-z_][A-Za-z0-9_]*|'
                              r'-?\d+(?:\.\d+)?)', line.split('agent,', 1)[1])
            got = tuple(a.lstrip('*') for a in args[:7])
            want = tuple(a.lstrip('*') for a in DONOR_ATTACK_ABS[
                0 if 'KIND_THROW' in line else 1])
            assert got == want, f'donor text {got} != pinned {want}'
            assert re.sub(r'\s+', ' ', line) in re.sub(r'\s+', ' ', rust), \
                f'donor ATTACK_ABS line is not in the Rust verbatim:\n  {line}'
    assert f'frame(agent.lua_state_agent, {DONOR_RELEASE_FRAME});' in rust, 'release frame missing'
    assert re.sub(r'\s+', ' ', DONOR_CAMERA) in re.sub(r'\s+', ' ', rust), 'camera call missing'
    assert 'ATK_HIT_ABS' in rust and 'FIGHTER_STATUS_THROW_WORK_INT_TARGET_OBJECT' in rust
    for name in DONOR_RESOURCES['effect'] + DONOR_RESOURCES['sound']:
        assert f'"{name}"' in rust, f'{name} is not named in the Rust'
    for name in DONOR_RESOURCES['voice']:
        assert name not in rust, f'{name} must reach the voice bank via the sequence record, not ACMD'
    return {'attack_abs_lines_verified': 2, 'release_frame': DONOR_RELEASE_FRAME}


def check_gating(rust, mod_rs):
    """Install-time costume gate; no runtime `if colour` in the scripts."""
    assert '.set_costume(crate::TARGET_COSTUMES.to_vec())' in rust, \
        'the throw is not gated by TARGET_COSTUMES'
    assert 'Agent::new("elight")' in rust, 'must register on elight'
    assert 'pub mod ness_throw_b;' in mod_rs and 'ness_throw_b::install();' in mod_rs, \
        'module is declared but not installed'
    for script in ('game_throwb', 'effect_throwb', 'sound_throwb', 'expression_throwb'):
        assert f'.{script.split("_")[0]}_acmd("{script}"' in rust, f'{script} not registered'
    body = rust.split('pub fn install()')[0]
    assert 'FIGHTER_INSTANCE_WORK_ID_INT_COLOR' not in body, \
        'a runtime colour check crept into the scripts; the gate is install-time'
    return {'gate': 'install-time set_costume([6,7])', 'fighter': 'elight',
            'acmd_registered': ['game_throwb', 'effect_throwb', 'sound_throwb',
                                'expression_throwb']}


def audit_motion(baseline, candidate):
    """Exactly one entry changes, and it changes by one byte."""
    result = {}
    for slot in SLOTS:
        rel = f'fighter/elight/motion/body/{slot}/motion_list.bin'
        a = parse(baseline / rel)
        b = parse(candidate / rel)
        assert len(a['entries']) == len(b['entries']), \
            f'{slot}: entry count changed {len(a["entries"])} -> {len(b["entries"])}'
        changed = [x['kind'] for x, y in zip(a['entries'], b['entries']) if x['raw'] != y['raw']]
        assert changed == [hash40('throw_b')], \
            f'{slot}: entries other than throw_b changed: {[hex(k) for k in changed]}'
        ea = next(e for e in a['entries'] if e['kind'] == hash40('throw_b'))
        eb = next(e for e in b['entries'] if e['kind'] == hash40('throw_b'))
        diff = [i for i in range(len(ea['raw'])) if ea['raw'][i] != eb['raw'][i]]
        assert diff == [62], f'{slot}: throw_b differs at {diff}, expected only offset 62'
        assert eb['cancel'] == DONOR_CANCEL, eb['cancel']
        assert ea['anims'] == eb['anims'] == (hash40(DONOR_CLIP),), 'the clip name moved'
        others = {}
        for name in ('throw_f', 'throw_hi', 'throw_lw', 'thrown_b', 'thrown_f',
                     'thrown_hi', 'thrown_lw'):
            xa = next(e for e in a['entries'] if e['kind'] == hash40(name))
            xb = next(e for e in b['entries'] if e['kind'] == hash40(name))
            assert xa['raw'] == xb['raw'], f'{slot}: {name} changed'
            others[name] = xb['cancel']
        result[slot] = {
            'motion_list_sha256_baseline': sha(baseline / rel),
            'motion_list_sha256_candidate': sha(candidate / rel),
            'entries': len(b['entries']),
            'entries_changed': ['throw_b'],
            'throw_b_cancel': {'baseline': ea['cancel'], 'candidate': eb['cancel']},
            'throw_b_diff_offsets': diff,
            'other_throws_byte_identical': others,
        }
    return result


def audit_clip(candidate, report):
    clip = candidate / f'fighter/elight/motion/body/c06/{DONOR_CLIP}'
    for slot in SLOTS:
        other = candidate / f'fighter/elight/motion/body/{slot}/{DONOR_CLIP}'
        assert sha(other) == sha(clip), f'{slot}: clip differs from c06 although the skeletons match'
    doc = json.loads(Path(report).read_text())
    c = doc[DONOR_CLIP]
    assert c['bones_dropped'] == ['Bat', 'BatL'], c['bones_dropped']
    assert not c['case_only'], c['case_only']
    assert c['required_bones_all_moving'], c['required_bone_motion']
    assert c['donor_transform_nodes'] == 68 and c['bones_kept'] == 66, \
        (c['donor_transform_nodes'], c['bones_kept'])
    return {'clip_sha256': sha(clip),
            'identical_across_slots': True,
            'donor_nodes': c['donor_transform_nodes'], 'kept': c['bones_kept'],
            'dropped': c['bones_dropped'], 'case_only': c['case_only'],
            'material_groups_dropped': c['material_groups_dropped'],
            'frames': c['frames'], 'final_frame_index': c['final_frame_index'],
            'required_bone_motion': c['required_bone_motion']}


def audit_effects(candidate):
    """NESS_PSI_RUSH must be reachable from Mythra's own bank, not a donor's."""
    out = {}
    donor_dir = candidate / 'effect/fighter/ness'
    assert not donor_dir.exists(), \
        'a donor-folder effect bank is staged; nothing loads that (handbook/10)'
    for slot in SLOTS:
        rel = f'effect/fighter/elight/ef_elight_{slot}.eff'
        assert (candidate / rel).is_file(), f'{rel} missing from the candidate'
        record = json.loads((candidate / f'effect/fighter/elight/ef_elight_{slot}.merge.json')
                            .read_text())
        assert record['resource_names'] == ['NESS_PSI_RUSH'], record['resource_names']
        assert record['decoded_emitter_fields_preserved'] is True
        assert record['hardware_validated'] is False
        out[slot] = {'path': rel, 'sha256': sha(candidate / rel),
                     'merged_from_sha256': record['donor_sha256'],
                     'texture_relocations': len(record['texture_id_relocations']),
                     'model_relocations': len(record['model_id_relocations'])}
    return out


def audit_sounds(candidate):
    report_path = candidate / 'ness_throw_sound.json'
    assert report_path.is_file(), 'ness_throw_sound.json missing'
    rep = json.loads(report_path.read_text())
    out = {'sequence': rep['sequence'], 'sequence_sha256': rep['sqb_sha256'],
           'voice_tones': rep['sequence_voice_tones'], 'banks': {}}
    appended = {}
    for b in rep['banks']:
        appended.setdefault((b['folder'], b['slot']), []).extend(b['appended_names'])
    for folder, prefix, wanted in (
            ('fighter', 'se_elight', set(DONOR_RESOURCES['sound'][:3])),
            ('fighter_voice', 'vc_elight', set(DONOR_RESOURCES['voice']))):
        for slot in SLOTS:
            names = {n.lower() for n, _ in codec.audio_read(
                (candidate / f'sound/bank/{folder}/{prefix}_{slot}.nus3audio').read_bytes())}
            got = set(appended[(folder, slot)])
            assert got == wanted, f'{prefix}_{slot}: appended {sorted(got)}, wanted {sorted(wanted)}'
            assert wanted <= names, f'{prefix}_{slot}: a required tone is absent from the bank'
            out['banks'][f'{prefix}_{slot}'] = {
                'appended': sorted(got),
                'sha256': {ext: sha(candidate / f'sound/bank/{folder}/{prefix}_{slot}{ext}')
                           for ext in ('.nus3audio', '.nus3bank', '.tonelabel')}}
    recs = codec.sqb_read((candidate / 'sound/sequence/fighter/elight.sqb').read_bytes())
    key = (len('seq_ness_rnd_attack') << 32) | zlib.crc32(b'seq_ness_rnd_attack')
    assert sum(1 for r in recs if int.from_bytes(r[:8], 'little') == key) == 1, \
        'elight.sqb does not carry exactly one seq_ness_rnd_attack record'
    return out


def _slot_of(rel):
    """Which costume a mod-tree path belongs to, or None if it is slot-agnostic.

    Slots appear two ways in this tree: as a directory (`motion/body/c06/`) and
    inside per-slot file names (`ef_elight_c06.eff`, `se_elight_c06.nus3bank`).
    A path with no slot at all is shared, not vanilla-facing, so `None` is a legal
    answer and is checked separately rather than treated as a violation.
    """
    parts = rel.split('/')
    for part in parts:
        if len(part) == 3 and part.startswith('c') and part[1:].isdigit():
            return part
    stem = parts[-1]
    hit = re.findall(r'_c(\d\d)', stem)
    if len(set(hit)) > 1:
        raise AssertionError(f'ambiguous slot in file name: {rel}')
    return f'c{hit[0]}' if hit else None


def audit_scope(baseline, candidate):
    """The delta must not touch any costume other than c06/c07."""
    changed = []
    for path in sorted(candidate.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(candidate).as_posix()
        if rel.endswith('.json'):
            continue
        base = baseline / rel
        if not base.is_file():
            changed.append({'path': rel, 'status': 'added'})
        elif sha(base) != sha(path):
            changed.append({'path': rel, 'status': 'modified',
                            'baseline_sha256': sha(base), 'candidate_sha256': sha(path)})
    for entry in changed:
        rel = entry['path']
        parts = rel.split('/')
        slot = _slot_of(rel)
        assert slot not in ('c00', 'c01', 'c02', 'c03', 'c04', 'c05'), \
            f'the delta touches a vanilla costume: {rel}'
        assert slot in (None, 'c06', 'c07'), \
            f'the delta touches costume {slot}: {rel}'
        # Mythra may appear as a directory (`fighter/elight/...`) or inside the
        # per-slot bank file name (`se_elight_c06.nus3bank`). Both are hers; what
        # must never appear is another fighter's name.
        assert 'elight' in rel, f'the delta touches a non-Mythra path: {rel}'
        entry['slot'] = slot
    return changed


def negative_controls(candidate, baseline, tmp):
    """Each refusal must actually refuse.

    Without these, every PASS above would only show the audit agreeing with
    itself. Three mutations, each the smallest one that has to trip a check.
    """
    import shutil
    fired = {}

    # (1) a motion list with a second entry altered must be rejected.
    src = candidate / 'fighter/elight/motion/body/c06/motion_list.bin'
    bad = tmp / 'bad_motion_list.bin'
    shutil.copy2(src, bad)
    ml = parse(bad)
    victim = next(e for e in ml['entries'] if e['kind'] == hash40('throw_hi'))
    raw = bytearray(victim['raw'])
    raw[-1] = (raw[-1] + 1) & 0xFF
    victim['raw'] = bytes(raw)
    data = bytearray()
    data += struct.pack('<QQQ', ml['magic'], ml['motion_path'], len(ml['entries']))
    for e in ml['entries']:
        data += e['raw']
    bad.write_bytes(bytes(data))
    tree = tmp / 'c1'
    (tree / 'fighter/elight/motion/body/c06').mkdir(parents=True)
    shutil.copy2(bad, tree / 'fighter/elight/motion/body/c06/motion_list.bin')
    fired['other_throw_entry_touched'] = not _passes(
        lambda: audit_motion(baseline, tree))

    # (2) a candidate that ships the donor's effect bank must be rejected.
    tree2 = tmp / 'c2'
    (tree2 / 'effect/fighter/ness').mkdir(parents=True)
    (tree2 / 'effect/fighter/ness/ef_ness.eff').write_bytes(b'not a bank')
    fired['donor_effect_folder_shipped'] = not _passes(
        lambda: audit_effects(tree2))

    # (3) a sound bank missing one required tone must be rejected.
    tree3 = tmp / 'c3'
    shutil.copytree(candidate / 'sound', tree3 / 'sound')
    shutil.copy2(candidate / 'ness_throw_sound.json', tree3 / 'ness_throw_sound.json')
    bank = tree3 / 'sound/bank/fighter/se_elight_c06.nus3audio'
    entries = codec.audio_read(bank.read_bytes())
    kept = [(n, s) for n, s in entries if n.lower() not in DONOR_RESOURCES['sound'][:3]]
    bank.write_bytes(codec.audio_write(kept))
    fired['required_tone_missing'] = not _passes(lambda: audit_sounds(tree3))
    return fired


def _scratch():
    """A dated scratch dir for the negative controls, created on demand.

    Recreated per run rather than assumed: `scratch/` is disposable by rule 3 and
    is pruned without warning, so any tool that depends on a directory already
    being there breaks for reasons that have nothing to do with its subject.
    """
    path = ROOT / 'scratch/2026-10-02_buffy/ness_throw_b'
    path.mkdir(parents=True, exist_ok=True)
    return path


def _passes(fn):
    try:
        fn()
        return True
    except AssertionError:
        return False


def run(candidate, baseline, animation_report, delta_path=None):
    rust = RUST.read_text(encoding='utf-8')
    mod_rs = (ROOT / 'src/pgwr/plugin/src/mythra/mod.rs').read_text(encoding='utf-8')
    report = {
        'tool': 'tools/audit_ness_throw_b.py 1.0.0',
        'date': '2026-10-02',
        'move': "vanilla Ness back throw (throw_b) on Mythra (elight) c06/c07",
        'evidence_tier': 'B (offline, byte-checkable)',
        'hardware_validated': False,
        'runtime_statement': 'No console, no emulator, no in-game observation. '
                             'All runtime behaviour is unverified (tier D).',
        'baseline': str(baseline), 'candidate': str(candidate),
        'donor_acmd': {p.name: sha(p) for p in sorted(DONOR_ACMD.glob('*.txt'))},
        'donor_constants': check_donor_constants(rust),
        'gating': check_gating(rust, mod_rs),
        'deliberate_omissions': DELIBERATE_OMISSIONS,
        'motion': audit_motion(baseline, candidate),
        'clip': audit_clip(candidate, animation_report),
        'effects': audit_effects(candidate),
        'sounds': audit_sounds(candidate),
        'delta': audit_scope(baseline, candidate),
    }
    if delta_path:
        Path(delta_path).parent.mkdir(parents=True, exist_ok=True)
        Path(delta_path).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--baseline', type=Path, default=DEFAULT_BASELINE)
    parser.add_argument('--animation-report', type=Path)
    parser.add_argument('--delta', type=Path)
    args = parser.parse_args()

    if args.check:
        import tempfile
        cand = args.candidate or ROOT / 'builds/pgwr/ness-throw-b-candidate/ult_mod'
        anim = (args.animation_report
                or ROOT / 'builds/pgwr/ness-throw-b-candidate/animation_c06.json')
        report = run(cand, args.baseline, anim)
        with tempfile.TemporaryDirectory(dir=str(_scratch())) as tmp:
            fired = negative_controls(cand, args.baseline, Path(tmp))
        assert all(fired.values()), f'a negative control did not fire: {fired}'
        report['negative_controls'] = fired
        print(f'PASS: {len(report["delta"])} changed files; motion delta = 1 byte in '
              f'throw_b per slot; 66/68 bones kept; all three negative controls fired')
        for entry in report['delta']:
            print(f'  {entry["status"]:9s} {entry["path"]}')
        if args.delta:
            Path(args.delta).parent.mkdir(parents=True, exist_ok=True)
            Path(args.delta).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        return

    if not args.candidate:
        parser.error('choose --check, or --candidate/--animation-report/--delta')
    report = run(args.candidate, args.baseline,
                 args.animation_report
                 or ROOT / 'builds/pgwr/ness-throw-b-candidate/animation_c06.json',
                 args.delta)
    print(json.dumps({'changed': len(report['delta'])}, indent=2))


if __name__ == '__main__':
    main()