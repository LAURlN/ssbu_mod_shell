"""Audit the Pikachu back-air delta for Pyra c06/c07 (v1.1.0; supersedes the 1.0.0 candidate).

Answers, against the **recorded baseline** `builds/pgwr/0.20.23` (never against
another agent's live tree):

  * that the package holds exactly the 19 intended mod files - nothing extra,
    nothing omitted, and specifically no `config.json`, no `param/`, no
    `effect/`, no `ui/` and no c00-c05 file, so the costume gate, the five
    vanilla costumes, the effect banks and the fighter params are provably
    untouched by this task;
  * that both clips are the retargeted donor *as 1.1.0 builds it*: the
    recipient's own 41 native nodes and idle visibility, the donor's absolute
    rotations, the donor's motion on the recipient's own bone offsets (never
    Pikachu's offsets - the 1.0.0 defect), the donor's unscaled root motion, the
    ground contact held, and every hitbox window containing a body joint
    (`audit_pikachu_airb_pose.py`);
  * that every ATTACK of the Rust module equals the donor script field for
    field and agrees with the game's own AI start/end frames
    (`audit_pikachu_airb_hitboxes.py`), and that the landing-lag parameter is
    Pikachu's own, found in `fighter_param.prc`, with the other aerials unchanged
    (`audit_pikachu_airb_params.py`);
  * that the motion list moved exactly two bytes per slot for `attack_air_b`
    (cancel 296 -> 300, flags 0x0080 -> 0x0084) and **zero** for
    `landing_air_b`, and that every other entry in the list is byte-identical;
  * that the sound banks gained exactly the named tones and lost nothing, and
    that `eflame.sqb` carries exactly one `seq_pikachu_rnd_attack` record, byte
    for byte the donor's;
  * that the Rust source obeys the two rules that cannot be read out of a
    binary: no per-frame state forcing (rule 19) and a costume gate (rule 12);
  * that the shipped patch applies to the baseline snapshot and reproduces the
    live module byte for byte, so the installer gets the same source I built;
  * that the NRO differs from the baseline NRO and carries all eight handler
    names plus the three sound names the scripts ask for.

Tier B: everything here is an offline byte/structure measurement. Whether the
move looks or feels right in game is **tier D** and is not established by this
tool.

    python -B tools/audit_pikachu_airb_delta.py
    python -B tools/audit_pikachu_airb_delta.py --negative-controls
    python -B tools/audit_pikachu_airb_delta.py --package <dir> --json <file>

Every check is a *live* assertion, not a claim: `--negative-controls` damages a
copy of the package and the source in twelve ways and asserts the audit fails on
each one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
sys.path.insert(0, str(ROOT / 'tools'))

import mlist  # noqa: E402
import audit_pikachu_airb_donor as donor  # noqa: E402
import build_pikachu_airb as builder  # noqa: E402
import merge_pikachu_airb_sound as merge  # noqa: E402
import merge_hero_neutral_b_sound as codec  # noqa: E402
import audit_pikachu_airb_pose as pose  # noqa: E402
import audit_pikachu_airb_hitboxes as hitboxes  # noqa: E402
import audit_pikachu_airb_params as params  # noqa: E402

BASELINE = ROOT / 'builds/pgwr/0.20.23/ultimate/mods/pyra_gamewatch_reskin'
PACKAGE = ROOT / 'builds/pgwr/pikachu-airb-1.1.0'
PKG_MOD = PACKAGE / 'ultimate/mods/pyra_gamewatch_reskin'
NRO_REL = ('atmosphere/contents/01006A800016E000/romfs/skyline/plugins/'
           'libpyra_gamewatch_reskin.nro')
BASELINE_NRO = ROOT / 'builds/pgwr/0.20.23' / NRO_REL
BUILT_NRO = (ROOT / 'builds/.cache/pikachu-airb/plugin/target/'
             'aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro')
# The pristine 0.20.23 source the patches are written against, and the live tree
# the patches are extracted from. Reading the patches against the *snapshot* is
# what lets the installer merge them without inheriting another agent's edits.
SNAPSHOT = ROOT / 'builds/.cache/silent-0.20.23/plugin'
LIVE = ROOT / 'src/pgwr/plugin'
# The tree the NRO was built from. Patches are checked against this one, not the
# live tree: another agent may legitimately edit live files (mod.rs, params.rs
# neighbours) while this package is waiting to be installed.
ISOLATED = ROOT / 'builds/.cache/pikachu-airb/plugin'
PATCHED_FILES = ('src/acmd/mod.rs', 'src/acmd/pikachu_attack_air_b.rs', 'src/params.rs')

SLOTS = ('c06', 'c07')
MODULE_REL = 'src/acmd/pikachu_attack_air_b.rs'

# The 19 files this task is allowed to touch in the mod tree.
EXPECTED_MOD_FILES = set()
for _slot in SLOTS:
    EXPECTED_MOD_FILES |= {
        f'fighter/eflame/motion/body/{_slot}/{builder.CLIPS[donor.KIND]}',
        f'fighter/eflame/motion/body/{_slot}/{builder.CLIPS[donor.LANDING_KIND]}',
        f'fighter/eflame/motion/body/{_slot}/motion_list.bin',
    }
    for _kind in ('fighter', 'fighter_voice'):
        _pre = 'se' if _kind == 'fighter' else 'vc'
        for _ext in ('nus3audio', 'nus3bank', 'tonelabel'):
            EXPECTED_MOD_FILES.add(
                f'sound/bank/{_kind}/{_pre}_eflame_{_slot}.{_ext}')
EXPECTED_MOD_FILES.add('sound/sequence/fighter/eflame.sqb')

# The eight donor handlers and the sounds/effects the scripts name. Effects are
# listed because they are a claim too: all three are common-bank `sys_*` names,
# which is why no donor emitter is merged and no effect bank is in the package.
HANDLERS = ('game_attackairb', 'effect_attackairb', 'sound_attackairb',
            'expression_attackairb', 'game_landingairb', 'effect_landingairb',
            'sound_landingairb', 'expression_landingairb')
SOUND_NAMES = ('se_pikachu_swing_s', 'se_pikachu_landing02',
               'seq_pikachu_rnd_attack')
EFFECT_NAMES = ('sys_spin_wind', 'sys_attack_impact', 'sys_down_smoke')

# Measured, not assumed: the exact per-slot byte delta of the two entries.
EXPECTED_DIFF = {donor.KIND: [16, 62], donor.LANDING_KIND: []}

# Rule 19 forbids forcing state per frame. These are the spellings that would
# do it; `set_rumble` is deliberately absent because the donor's own expression
# scripts use it and porting them faithfully is the point.
FORCING_PATTERNS = (
    r'\bWorkModule::set_',
    r'\bControlModule::set_(?!rumble)',
    r'\bset_float\b', r'\bset_int\b', r'\bset_vel\b',
    r'\bset_gravity\b', r'\bset_angular_vel\b',
)


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def rel_path(path: Path) -> str:
    """Workspace-relative posix path: a shipped report carries no drive letter."""
    try:
        return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def rel_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob('*')
            if p.is_file()}


class Report:
    """Collects failures; never raises, so one damaged check cannot hide another."""

    def __init__(self):
        self.checks: list[dict] = []
        self.failures: list[str] = []

    def check(self, name: str, ok: bool, detail: str = '') -> bool:
        self.checks.append({'check': name, 'pass': bool(ok), 'detail': detail})
        if not ok:
            self.failures.append(f'{name}: {detail}')
        return bool(ok)


# ---------------------------------------------------------------------------
# Package contents
# ---------------------------------------------------------------------------

def check_package(mod_root: Path, rep: Report) -> None:
    present = rel_files(mod_root)
    missing = sorted(EXPECTED_MOD_FILES - present)
    extra = sorted(present - EXPECTED_MOD_FILES)
    rep.check('package/exact-file-set', not missing and not extra,
              f'missing={missing} extra={extra}')
    # Named separately because these are the four things a reviewer asks about:
    # the gate lives in config.json, the numbers in param/, the visuals in
    # effect/, the slot table in ui/. None of them may appear in this delta.
    for label, pattern in (('no config.json', r'(^|/)config\.json$'),
                           ('no param/', r'(^|/)param/'),
                           ('no effect/', r'(^|/)effect/'),
                           ('no ui/', r'(^|/)ui/'),
                           ('no vanilla costume c00-c05',
                            r'motion/body/c0[0-5]/|model/body/c0[0-5]/')):
        hits = sorted(p for p in present if re.search(pattern, p))
        rep.check(f'package/{label}', not hits, f'offending={hits}')


# ---------------------------------------------------------------------------
# Clips
# ---------------------------------------------------------------------------

def check_clips(mod_root: Path, rep: Report) -> None:
    for clip_name in builder.CLIPS.values():
        paths = [mod_root / f'fighter/eflame/motion/body/{s}/{clip_name}'
                 for s in SLOTS]
        if not rep.check(f'clips/{clip_name}/present',
                         all(p.is_file() for p in paths),
                         f'missing={[str(p) for p in paths if not p.is_file()]}'):
            continue
        digests = [sha(p) for p in paths]
        rep.check(f'clips/{clip_name}/identical-across-slots',
                  len(set(digests)) == 1, f'sha={digests}')
        base = BASELINE / f'fighter/eflame/motion/body/c06/{clip_name}'
        rep.check(f'clips/{clip_name}/differs-from-baseline',
                  digests[0] != sha(base),
                  'shipped clip is byte-identical to the G&W clip')
        rep.check(f'clips/{clip_name}/differs-from-donor',
                  digests[0] != builder.sha(builder.DONOR / clip_name),
                  'shipped clip is the unretargeted donor clip')

        kind = next(k for k, v in builder.CLIPS.items() if v == clip_name)
        for slot in SLOTS:
            skel = BASELINE / f'fighter/eflame/model/body/{slot}/model.nusktb'
            idle = BASELINE / f'fighter/eflame/motion/body/{slot}/a00wait1.nuanmb'
            clip = mod_root / f'fighter/eflame/motion/body/{slot}/{clip_name}'
            try:
                m = pose.analyse(clip, kind, skel, idle)
                bad = pose.verdict(m, kind)
                rep.check(f'clips/{clip_name}/{slot}/pose-world-space',
                          not bad, '; '.join(bad))
                rep.check(f'clips/{clip_name}/{slot}/limbs-move',
                          not donor.static_limbs(donor.retarget_measurement(
                              builder.DONOR / clip_name, skel, idle)),
                          'a limb bone of the donor clip is static against the recipient idle')
            except Exception as exc:  # noqa: BLE001 - report, do not crash
                rep.check(f'clips/{clip_name}/{slot}/pose-world-space', False,
                          f'{type(exc).__name__}: {exc.args or exc}')


# ---------------------------------------------------------------------------
# Motion list
# ---------------------------------------------------------------------------

def check_motion(mod_root: Path, rep: Report) -> None:
    for slot in SLOTS:
        rel = f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        new_path, base_path = mod_root / rel, BASELINE / rel
        if not rep.check(f'motion/{slot}/present', new_path.is_file(), rel):
            continue
        new_bytes, base_bytes = new_path.read_bytes(), base_path.read_bytes()
        rep.check(f'motion/{slot}/size-preserved',
                  len(new_bytes) == len(base_bytes),
                  f'{len(base_bytes)} -> {len(new_bytes)}')
        new, base = mlist.parse_bytes(new_bytes), mlist.parse_bytes(base_bytes)
        rep.check(f'motion/{slot}/round-trips',
                  mlist.encode(new) == new_bytes
                  and mlist.encode(base) == base_bytes, 're-encode differs')

        # Only the two named entries may differ; every other one is compared
        # byte for byte so "this move did not touch anything else" is measured.
        # Entries are keyed by their motion-kind hash: the kind *names* live in
        # the generated Rust, not in the file, and inventing a name table here
        # would be exactly the kind of unverified assumption this tool avoids.
        base_kinds = [e['kind'] for e in base['entries']]
        new_kinds = [e['kind'] for e in new['entries']]
        rep.check(f'motion/{slot}/entry-table-unchanged',
                  base_kinds == new_kinds,
                  f'{[hex(k) for k in base_kinds]} != '
                  f'{[hex(k) for k in new_kinds]}')
        moved = [k for k, a, b in zip(base_kinds, base['entries'], new['entries'])
                 if bytes(a['raw']) != bytes(b['raw'])]
        # `landing_air_b` is in EXPECTED_DIFF with an *empty* offset list: the
        # donor entry is already byte-identical, so its correct outcome is that
        # it does not appear here at all.
        want = sorted(hash40(k) for k, diffs in EXPECTED_DIFF.items() if diffs)
        rep.check(f'motion/{slot}/only-named-entries-moved',
                  sorted(moved) == want, f'moved={[hex(k) for k in sorted(moved)]}')

        for kind in (donor.KIND, donor.LANDING_KIND):
            want = builder.EXPECTED[kind]
            entry = mlist.find(new, kind)
            old = mlist.find(base, kind)
            diffs = mlist.diff_offsets(bytes(old['raw']), bytes(entry['raw']))
            rep.check(f'motion/{slot}/{kind}/differing-offsets',
                      diffs == EXPECTED_DIFF[kind], f'{diffs}')
            rep.check(f'motion/{slot}/{kind}/cancel+flags',
                      entry['cancel'] == want['cancel']
                      and entry['flags'] == want['flags'],
                      f'cancel={entry["cancel"]} flags={entry["flags"]:#x}')
            # The bare-stem Chrom jab lesson: the animation-name hash covers the
            # file name *with* its extension.
            rep.check(f'motion/{slot}/{kind}/names-its-own-clip',
                      list(entry['anims']) == [hash40(builder.CLIPS[kind])],
                      f'anims={[hex(a) for a in entry["anims"]]}')
            if kind == donor.LANDING_KIND:
                rep.check(f'motion/{slot}/{kind}/unchanged-from-baseline',
                          bytes(entry['raw']) == bytes(old['raw']),
                          'landing entry was modified although the donor entry '
                          'is already byte-identical')


# ---------------------------------------------------------------------------
# Sound
# ---------------------------------------------------------------------------

def _bank(stem: Path):
    entries = codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())
    chunks = dict(codec.bank_read(stem.with_suffix('.nus3bank').read_bytes()))
    labels = codec.labels_read(stem.with_suffix('.tonelabel').read_bytes(),
                               [n for n, _ in entries])
    return entries, chunks, labels


def check_sound(mod_root: Path, rep: Report) -> None:
    for slot in SLOTS:
        for folder, pre, wanted in (
                ('fighter', 'se', merge.SE_REQUIRED),
                ('fighter_voice', 'vc', set(merge.EXPECTED_VOICE))):
            rel = f'sound/bank/{folder}/{pre}_eflame_{slot}'
            new_stem, base_stem = mod_root / rel, BASELINE / rel
            if not rep.check(f'sound/{rel}/present',
                             new_stem.with_suffix('.nus3audio').is_file()
                             and new_stem.with_suffix('.nus3bank').is_file()
                             and new_stem.with_suffix('.tonelabel').is_file(), rel):
                continue
            try:
                n_ent, n_ch, n_lab = _bank(new_stem)
                b_ent, b_ch, b_lab = _bank(base_stem)
            except Exception as exc:  # noqa: BLE001
                rep.check(f'sound/{rel}/reads-back', False,
                          f'{type(exc).__name__}: {exc.args or exc}')
                continue
            rep.check(f'sound/{rel}/reads-back', True, f'tones={len(n_ent)}')
            gained = [n for n, _ in n_ent[len(b_ent):]]
            rep.check(f'sound/{rel}/appended-set',
                      sorted(g.lower() for g in gained)
                      == sorted(wanted), f'appended={gained}')
            rep.check(f'sound/{rel}/retained-prefix-byte-equal',
                      n_ent[:len(b_ent)] == b_ent
                      and [n for n, _ in n_ent][:len(b_ent)]
                      == [n for n, _ in b_ent],
                      'a pre-existing tone was renamed, reordered or altered')
            rep.check(f'sound/{rel}/retained-tone-records',
                      codec.tones_read(n_ch[b'TONE'])[:len(b_ent)]
                      == codec.tones_read(b_ch[b'TONE']),
                      'a pre-existing tone record changed')
            kept = {(c, v) for c, v in n_lab if v >> 8 < len(b_ent)}
            rep.check(f'sound/{rel}/retained-labels',
                      kept == {(c, v) for c, v in b_lab},
                      'a pre-existing tone label was lost or rebased')
            # Independent of the codec's own reader of the *new* file: every
            # pre-existing tone's raw bytes must still be present in it.
            new_raw = new_stem.with_suffix('.nus3audio').read_bytes()
            lost = [n for n, data in b_ent if bytes(data) not in new_raw]
            rep.check(f'sound/{rel}/retained-tone-bytes-in-raw-file',
                      not lost, f'lost={lost[:5]} of {len(b_ent)}')
            rep.check(f'sound/{rel}/identity-chunks-kept',
                      all(n_ch[t] == b_ch[t] for t in (b'BINF', b'PROP')),
                      'bank identity chunk changed')
            rep.check(f'sound/{rel}/appended-resolve',
                      {zlib.crc32(w.lower().encode()) for w in wanted}
                      <= {c for c, _ in n_lab},
                      'an appended tone has no label, so it cannot resolve')
            rep.check(f'sound/{rel}/no-common-sound-merged',
                      not (merge.COMMON_SOUNDS
                           & {g.lower() for g in gained}),
                      f'appended={gained}')

    sqb_rel = 'sound/sequence/fighter/eflame.sqb'
    new_sqb, base_sqb = mod_root / sqb_rel, BASELINE / sqb_rel
    if not rep.check(f'sound/{sqb_rel}/present', new_sqb.is_file(), sqb_rel):
        return
    try:
        new_recs = codec.sqb_read(new_sqb.read_bytes())
        base_recs = codec.sqb_read(base_sqb.read_bytes())
        donor_rec = merge.sequence_record()
    except Exception as exc:  # noqa: BLE001
        rep.check(f'sound/{sqb_rel}/reads-back', False,
                  f'{type(exc).__name__}: {exc.args or exc}')
        return
    key = hash40(merge.SEQUENCE)
    new_hits = [r for r in new_recs if int.from_bytes(r[:8], 'little') == key]
    rep.check(f'sound/{sqb_rel}/exactly-one-{merge.SEQUENCE}',
              len(new_hits) == 1, f'found={len(new_hits)}')
    if new_hits:
        rep.check(f'sound/{sqb_rel}/record-is-the-donor-record',
                  new_hits[0] == donor_rec,
                  f'{len(new_hits[0])} bytes, donor {len(donor_rec)}')
    rep.check(f'sound/{sqb_rel}/base-records-retained',
              all(r in new_recs for r in base_recs),
              f'dropped={len([r for r in base_recs if r not in new_recs])}')


# ---------------------------------------------------------------------------
# Rust source
# ---------------------------------------------------------------------------

def check_source(src_root: Path, rep: Report) -> None:
    module = src_root / MODULE_REL
    mod_rs = src_root / 'src/acmd/mod.rs'
    if not rep.check('source/module-present', module.is_file(), MODULE_REL):
        return
    text = module.read_text(encoding='utf-8')
    norm = re.sub(r'\s+', ' ', text)

    rep.check('source/no-per-frame-forcing',
              not any(re.search(p, text) for p in FORCING_PATTERNS),
              'a per-frame state setter is present (rule 19)')
    rep.check('source/costume-gate',
              'Agent::new("eflame")' in text
              and 'crate::TARGET_COSTUMES.to_vec()' in text,
              'the module is not gated to the modded costumes')
    rep.check('source/eight-handlers-high',
              all(f'"{h}"' in text for h in HANDLERS)
              and text.count('Priority::High') == 8
              and 'Priority::Default' not in text,
              f'high={text.count("Priority::High")}')

    # The claim made in the finisher's comment: the last hitbox opens at 24 and
    # a clear_all follows it before the landing flag is released at 38. Checked
    # as literals, because that is the claim. There are exactly three
    # clear_all calls for the three places boxes open: the jab loop, the
    # finisher and the landing.
    frames = [int(m) for m in
              re.findall(r'frame\(agent\.lua_state_agent, (\d+)\.\d\)', text)]
    clear = 'AttackModule::clear_all(agent.module_accessor);'
    rep.check('source/last-hitbox-frame-is-24',
              24 in frames and max(frames) == 38,
              f'frame literals={frames} (38 releases ENABLE_LANDING; the last '
              f'ATTACK-bearing frame is 24)')
    rep.check('source/one-clear-per-open-box', norm.count(clear) == 3,
              f'{norm.count(clear)} clear_all calls, expected 3')
    finisher_at = norm.find('3.6, 45, 160')
    next_clear = norm.find(clear, max(finisher_at, 0))
    rep.check('source/finisher-is-cleared',
              finisher_at >= 0 and next_clear > finisher_at
              and next_clear < norm.find('frame(agent.lua_state_agent, 38'),
              'no clear_all between the finisher ATTACK and frame 38')
    landing_at = norm.find('4.0, 361, 80')
    rep.check('source/landing-box-is-cleared',
              landing_at >= 0 and norm.find(clear, landing_at) > landing_at,
              'no clear_all after the landing ATTACK')
    rep.check('source/no-article-or-status-install',
              'install_fighter' not in text and 'WorkModule::install' not in text
              and 'L2CArticle' not in text,
              'the module installs an article or a status')

    # Field-for-field equality with the donor script, and the game's own AI
    # start/end frames (a source independent of the dump text).
    try:
        for kind in ('attack_air_b', 'landing_air_b'):
            same = hitboxes.donor_events(kind) == hitboxes.rust_events(kind, module)
            rep.check(f'source/{kind}/attack-events-equal-donor', same,
                      'the Rust ATTACK / clear_all events differ from the donor script')
        measured = hitboxes.measure()
        for kind, v in measured['moves'].items():
            rep.check(f'source/{kind}/ai-window-matches',
                      v['ai_start_matches'] and v['ai_end_matches'] and v['every_box_closed'],
                      f'first open {v["first_open"]}, last clear {v["last_clear"]}, '
                      f'AI {v["ai_data"]}')
        rep.check('source/attack-signature-verified',
                  measured['signature_verified_against_smash_script'] is not False,
                  'macros::ATTACK in the pinned smash-script no longer matches the field list')
    except Exception as exc:  # noqa: BLE001
        rep.check('source/hitbox-audit-ran', False, f'{type(exc).__name__}: {exc.args or exc}')
    try:
        tbl, rs, snap = params.measure(src_root)
        bad = params.verdict(tbl, rs, snap)
        rep.check('source/landing-lag-is-pikachus-own', not bad, '; '.join(bad))
    except Exception as exc:  # noqa: BLE001
        rep.check('source/params-audit-ran', False, f'{type(exc).__name__}: {exc.args or exc}')

    if mod_rs.is_file():
        mtext = mod_rs.read_text(encoding='utf-8')
        rep.check('source/mod-rs-declares-module',
                  f'pub mod {Path(MODULE_REL).stem};' in mtext,
                  'acmd/mod.rs does not declare the module')
        rep.check('source/mod-rs-calls-install',
                  'pikachu_attack_air_b::install();' in mtext,
                  'acmd/mod.rs never calls the module install')


def check_patches(package: Path, rep: Report) -> None:
    """Apply the shipped patches to a clean copy of the baseline snapshot."""
    patches = sorted((package / 'patches').glob('*.patch'))
    if not rep.check('patches/present', len(patches) == 3,
                     f'found={[p.name for p in patches]}'):
        return
    work = Path(tempfile.mkdtemp(prefix='pikachu-airb-apply-',
                                 dir=ROOT / 'builds/.cache'))
    try:
        tree = work / 'plugin'
        shutil.copytree(SNAPSHOT / 'src', tree / 'src')
        env = {'GIT_AUTHOR_NAME': 'a', 'GIT_AUTHOR_EMAIL': 'a@b',
               'GIT_COMMITTER_NAME': 'a', 'GIT_COMMITTER_EMAIL': 'a@b',
               'PATH': '/usr/bin:/bin:/mingw64/bin'}
        subprocess.run(['git', 'init', '-q', str(tree)], check=True, env=env,
                       capture_output=True)
        for patch in patches:
            check = subprocess.run(['git', 'apply', '--check', str(patch)],
                                   cwd=tree, capture_output=True, text=True,
                                   env=env)
            if not rep.check(f'patches/{patch.name}/applies', check.returncode == 0,
                             check.stderr.strip()[:400]):
                return
            subprocess.run(['git', 'apply', str(patch)], cwd=tree, check=True,
                           env=env, capture_output=True)
        rep.check('patches/applied', True, f'{len(patches)} patches')
        for rel in PATCHED_FILES:
            got, want = (work / 'plugin' / rel), (ISOLATED / rel)
            rep.check(f'patches/reproduce-{Path(rel).name}',
                      got.is_file() and sha(got) == sha(want),
                      'patched result differs from the isolated build tree')
        # The live tree: my two own files must equal the built ones; mod.rs may
        # carry other agents' edits, so it is only required to hold my lines
        # (checked in check_source).
        for rel in (MODULE_REL, 'src/params.rs'):
            rep.check(f'patches/live-{Path(rel).name}-equals-built',
                      (LIVE / rel).is_file() and sha(LIVE / rel) == sha(ISOLATED / rel),
                      'the live copy differs from what the NRO was built from')
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# NRO
# ---------------------------------------------------------------------------

def check_nro(nro: Path, rep: Report) -> None:
    if not rep.check('nro/present', nro.is_file(), str(nro)):
        return
    data = nro.read_bytes()
    base = BASELINE_NRO.read_bytes()
    rep.check('nro/differs-from-baseline',
              hashlib.sha256(data).hexdigest()
              != hashlib.sha256(base).hexdigest(),
              'the shipped NRO is the unmodified baseline NRO')
    text = data.decode('latin-1')
    for name in HANDLERS:
        rep.check(f'nro/has/{name}', name in text, 'handler name absent')
    for name in SOUND_NAMES:
        rep.check(f'nro/has/{name}', name in text, 'sound name absent')
    for name in EFFECT_NAMES:
        rep.check(f'nro/has/{name}', name in text,
                  'common-bank effect name absent; re-audit the "no emitter '
                  'merged" claim')


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(package: Path, src_root: Path, nro: Path) -> Report:
    rep = Report()
    mod_root = package / 'ultimate/mods/pyra_gamewatch_reskin'
    if not rep.check('package/present', mod_root.is_dir(), str(mod_root)):
        return rep
    # Each group is wrapped: a damaged file can make a *parser* throw, and a
    # crash that aborts the run would hide the other groups' verdicts. A crash
    # is recorded as a failed check, never swallowed.
    for label, fn, args in (
            ('package', check_package, (mod_root,)),
            ('clips', check_clips, (mod_root,)),
            ('motion', check_motion, (mod_root,)),
            ('sound', check_sound, (mod_root,)),
            ('source', check_source, (src_root,)),
            ('patches', check_patches, (package,)),
            ('nro', check_nro, (package / NRO_REL
                                if (package / NRO_REL).is_file() else nro,))):
        try:
            fn(*args, rep)
        except Exception as exc:  # noqa: BLE001 - a crash is a failure, not a stop
            rep.check(f'{label}/ran-to-completion', False,
                      f'{type(exc).__name__}: {exc.args or exc}')
    return rep


def _damage(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


def negative_controls() -> list[dict]:
    """Twelve damaged inputs the audit must reject, plus one it must accept."""
    work = ROOT / 'builds/.cache/pikachu-airb/controls'
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    results = []

    def record(label: str, damage) -> None:
        """`ok` means the control behaved as intended: the audit REJECTED it."""
        pkg = _damage(PACKAGE, work / f'pkg-{label}')
        src = _damage(LIVE, work / f'src-{label}')
        damage(pkg, src)
        rep = run(pkg, src, BUILT_NRO)
        caught = [f for f in rep.failures if not f.startswith('package/present')]
        results.append({'control': label, 'kind': 'damage',
                        'ok': bool(caught),
                        'detail': caught[0] if caught else 'NOT CAUGHT'})
        print(f'{"PASS" if caught else "FAIL"}: {label}: '
              f'{caught[0] if caught else "NOT CAUGHT"}')

    def flip_flags_byte(pkg: Path, _src: Path) -> None:
        # Offset 16 *inside* the attack_air_b entry is the flags field. Damaging
        # that exact byte is the point: the audit must catch a wrong flags value,
        # not merely a file that no longer parses.
        p = pkg / ('ultimate/mods/pyra_gamewatch_reskin/'
                   'fighter/eflame/motion/body/c06/motion_list.bin')
        start = mlist.find(mlist.parse(p), donor.KIND)['start']
        data = bytearray(p.read_bytes())
        data[start + 16] ^= 0x04
        p.write_bytes(bytes(data))

    def truncate_clip(pkg: Path, _src: Path) -> None:
        p = pkg / ('ultimate/mods/pyra_gamewatch_reskin/'
                   'fighter/eflame/motion/body/c07/c05attackairb.nuanmb')
        p.write_bytes(p.read_bytes()[:-16])

    def strip_tone(pkg: Path, _src: Path) -> None:
        p = pkg / ('ultimate/mods/pyra_gamewatch_reskin/'
                   'sound/bank/fighter_voice/vc_eflame_c06.nus3audio')
        p.write_bytes(p.read_bytes()[:-64])

    def extra_file(pkg: Path, _src: Path) -> None:
        (pkg / 'ultimate/mods/pyra_gamewatch_reskin/config.json').write_text('{}')

    def nro_rolled_back(pkg: Path, _src: Path) -> None:
        (pkg / NRO_REL).write_bytes(BASELINE_NRO.read_bytes())

    def drop_the_clear(_pkg: Path, src: Path) -> None:
        # The *last* clear_all is the finisher's, so removing it is the damage
        # the "every box this move creates is closed" claim is about.
        p = src / MODULE_REL
        text = p.read_text(encoding='utf-8')
        needle = 'AttackModule::clear_all(agent.module_accessor);'
        at = text.rfind(needle)
        assert at >= 0, 'the control found no clear_all to remove'
        p.write_text(text[:at] + text[at + len(needle):], encoding='utf-8')

    def add_forcing(_pkg: Path, src: Path) -> None:
        p = src / MODULE_REL
        text = p.read_text(encoding='utf-8')
        p.write_text(text.replace(
            'pub fn install() {',
            'fn _rule19(p: &mut L2CAgentBase) { WorkModule::set_float(p.module_accessor, 0, 1.0); }\n\npub fn install() {', 1),
            encoding='utf-8')

    def ungate_costume(_pkg: Path, src: Path) -> None:
        p = src / MODULE_REL
        text = p.read_text(encoding='utf-8')
        p.write_text(text.replace('crate::TARGET_COSTUMES.to_vec()',
                                  'Vec::new()', 1), encoding='utf-8')

    def donor_offsets_clip(pkg: Path, _src: Path) -> None:
        # The real 1.0.0 artefact: the clip that carried Pikachu's bone offsets.
        for slot in SLOTS:
            shutil.copyfile(
                pose.package_clip(pose.OLD_PACKAGE, slot, donor.KIND),
                pkg / ('ultimate/mods/pyra_gamewatch_reskin/fighter/eflame/motion/body/'
                       f'{slot}/{builder.CLIPS[donor.KIND]}'))

    def landing_lag_changed(_pkg: Path, src: Path) -> None:
        p = src / 'src/params.rs'
        text = p.read_text(encoding='utf-8')
        needle = '0x1a4262b54f => Some(18.0f32)'
        assert needle in text, 'the control found no landing_attack_air_frame_b entry'
        p.write_text(text.replace(needle, '0x1a4262b54f => Some(14.0f32)', 1), encoding='utf-8')

    def another_aerial_changed(_pkg: Path, src: Path) -> None:
        p = src / 'src/params.rs'
        text = p.read_text(encoding='utf-8')
        needle = '0x1b64c11828 => Some(22.0f32)'
        assert needle in text, 'the control found no landing_attack_air_frame_lw entry'
        p.write_text(text.replace(needle, '0x1b64c11828 => Some(20.0f32)', 1), encoding='utf-8')

    def hitbox_field_swapped(_pkg: Path, src: Path) -> None:
        p = src / MODULE_REL
        text = p.read_text(encoding='utf-8')
        needle = '1.0, 367, 100, 40, 0, 4.2'
        assert needle in text, 'the control found no jab ATTACK'
        p.write_text(text.replace(needle, '1.0, 367, 40, 100, 0, 4.2', 1), encoding='utf-8')

    record('motion-entry-flags-flipped', flip_flags_byte)
    record('clip-truncated', truncate_clip)
    record('voice-tone-stripped', strip_tone)
    record('stray-config-json', extra_file)
    record('nro-rolled-back-to-baseline', nro_rolled_back)
    record('finisher-clear-all-removed', drop_the_clear)
    record('per-frame-forcing-added', add_forcing)
    record('costume-gate-removed', ungate_costume)
    record('donor-bone-offsets-clip-restored', donor_offsets_clip)
    record('landing-lag-changed', landing_lag_changed)
    record('another-aerial-landing-lag-changed', another_aerial_changed)
    record('hitbox-kbg-fkb-swapped', hitbox_field_swapped)

    # Positive control: the undamaged package must PASS, or "every damage was
    # caught" would only prove the audit rejects everything. `ok` here means
    # the audit ACCEPTED it - the opposite sense from the controls above, which
    # is why `kind` exists and why nothing shares one flag between them.
    rep = run(PACKAGE, LIVE, BUILT_NRO)
    ok = not rep.failures
    results.append({'control': 'undamaged-package-passes', 'kind': 'positive',
                    'ok': ok,
                    'detail': rep.failures[0] if rep.failures else 'no failures'})
    print(f'{"PASS" if ok else "FAIL"}: undamaged-package-passes: '
          f'{rep.failures[0] if rep.failures else "no failures"}')
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--package', type=Path, default=PACKAGE)
    ap.add_argument('--source', type=Path, default=LIVE)
    ap.add_argument('--nro', type=Path, default=BUILT_NRO)
    ap.add_argument('--json', type=Path, help='write the report here')
    ap.add_argument('--negative-controls', action='store_true')
    args = ap.parse_args()

    if args.negative_controls:
        results = negative_controls()
        damage = [r for r in results if r['kind'] == 'damage']
        positive = [r for r in results if r['kind'] == 'positive']
        not_caught = [r for r in damage if not r['ok']]
        rejected_positive = [r for r in positive if not r['ok']]
        print(f'\n{len(damage) - len(not_caught)}/{len(damage)} damaged inputs '
              f'rejected; {len(positive) - len(rejected_positive)}/'
              f'{len(positive)} undamaged input(s) accepted')
        if not_caught:
            print('FAIL: the audit did not reject: '
                  + ', '.join(r['control'] for r in not_caught))
        if rejected_positive:
            print('FAIL: the audit wrongly rejected the undamaged package: '
                  + '; '.join(r['detail'] for r in rejected_positive))
        return 1 if (not_caught or rejected_positive) else 0

    rep = run(args.package, args.source, args.nro)
    payload = {'tool': Path(__file__).name, 'version': '1.1.0',
               'evidence_tier': 'B', 'hardware_validated': False,
               'package': rel_path(args.package),
               'baseline': rel_path(BASELINE.parent.parent.parent),
               'checks': rep.checks, 'failures': rep.failures,
               'passed': sum(1 for c in rep.checks if c['pass']),
               'total': len(rep.checks)}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=1), encoding='utf-8')
    for check in rep.checks:
        print(f'{"PASS" if check["pass"] else "FAIL"}: {check["check"]}'
              + (f' -- {check["detail"]}' if check['detail'] and not check['pass']
                 else ''))
    print(f'\n{payload["passed"]}/{payload["total"]} checks passed')
    if rep.failures:
        print('audit_pikachu_airb_delta FAILED')
        return 1
    print('audit_pikachu_airb_delta OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())