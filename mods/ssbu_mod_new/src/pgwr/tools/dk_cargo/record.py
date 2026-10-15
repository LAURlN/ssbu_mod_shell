"""Publish this task's checked research manifest into its own queue entries.

Run after check.py --manifest. Preserves other agents' sections and existing
failure history. Does not mark READY or write runtime/integration files.
"""
import json
import re
from pathlib import Path
import audit
from audit import ROOT, WS, OUT, sha
from stage import PACKAGE


def replace(path, start, stop, content):
    text = path.read_text(encoding='utf-8')
    a = text.index(start)
    match = re.search(stop, text[a + len(start):], re.M)
    assert match, (path, stop)
    b = a + len(start) + match.start()
    path.write_text(text[:a] + content.rstrip() + '\n\n' + text[b:], encoding='utf-8')


def run():
    manifest_path = PACKAGE / 'MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['status'] == 'INCOMPLETE_NOT_INSTALLABLE'
    for rel, expected in manifest['files'].items():
        assert sha((PACKAGE / rel).read_bytes()) == expected, rel
    for rel, expected in manifest['sources'].items():
        assert sha((ROOT / rel).read_bytes()) == expected, rel
    for rel, expected in manifest['shared_tool_dependencies'].items():
        assert sha((ROOT / rel).read_bytes()) == expected, rel
    mh = sha(manifest_path.read_bytes())
    th = manifest['tree_sha256']
    hashes = f'Manifest SHA-256 `{mh}`.\nPackage tree SHA-256 `{th}`.'
    common = '''Review package `builds/pgwr/dk_cargo-research.1/` pins baseline 0.20.19:
28 attacker clips, four append-only sound banks, SQB/effect merges, 30 victim
pose templates and separate raw motion/config additions; 94 victim motion lists
and symbol-keyed offsets are pinned. Templates are not blanket victim overrides.
No runtime Rust, integration NRO or registration patch exists.

ID requirement: 15 attacker states plus three victim roles per eligible fighter
table (18 roles on eflame c06/c07). No production numbers selected. The 94-list
review universe includes non-playable controls, not 94 proven catchable kinds.

The user authorized cargo extensions at existing +0x170/+0x210 interception
points; these remain unimplemented. No further hook requirement is established.
Remaining work: native victim shared-pose lookup/owned aliases, complete state
and cleanup semantics, callback identity/lifetime, registration coverage and
runtime implementation/build. These are unfinished engineering work, not a
request for more user authorization or missing game inputs.

Shared dependencies: forward grab-dispatch slot global_table[0x45], existing
Monkey Flip/G&W native wrappers, victim status registrations, params, motion
lists, config, SE/VC/SQB/effect banks. Preserve Snake down throw, ordinary grabs
and other directions. Rebase bank merges on collective inputs; do not overwrite
them with 0.20.19 snapshots. No shared build/version/framework change or install.

Offline B: extractor GNU build, input hashes, graph captures, retarget readback,
entry/script hashes, bank preservation, effect round trip and package checks.
No cargo plugin build was run because no runtime Rust was added. Compilation
would not verify capture/release. No game/emulator or console result.

Reproduction: `src/pgwr/tools/dk_cargo/README.md`.
Evidence/failures: `evidence/2026-10-02_pgwr_dk_cargo/RESULT.md`.
Changed/generated files: its `FILES.json`.'''
    checklist = '''**Hardware checklist after a checked runtime integration package exists:**

1. Record package/NRO hashes and logs from boot; compare vanilla DK and Pyra
   c00/c01 controls, ordinary grabs and unrelated throws.
2. c06/c07 stand/dash/pivot grabs: forward throw enters pickup once; verify
   published link and advancing victim status/motion, not just acceptance flags.
3. Ground carry: idle, slow/fast walk, turn, jump squat/backward jump, platform pass.
4. Jump, walk off, drift and landing: compare DK transition rules and attachment.
5. All four ground cargo throws, both facings: timing, damage, angle and one release.
6. All four air cargo throws: compare DK kinetics, recovery and landing behavior.
7. Low/high damage mash escape: clatter timing, release, restored victim control.
8. Victim poses/body variants, G&W and Pickel: advancing clips and aligned anchors.
9. Slopes/platforms/ledges/blast zones: donor restrictions, no orphaned constraints.
10. Third-party interruption, attacker/victim death, rebirth and match reset:
    clear links, invincibility, held-item visibility and owned state.
11. Swap requests/departures: donor restrictions, no link to the dormant body.
12. Regression: Snake down throw, normal grabs, unrelated throws and existing moves;
    repeat vanilla controls. Return boot logs and any Atmosphere crash report.

No cargo pass/fail log markers exist yet; runtime must add bounded diagnostics.'''
    replace(ROOT / 'CURRENT_INSTALL.md', '## dk_cargo — Codex',
            r'^Updated 2026-10-02\.',
            '## dk_cargo — Codex — 2026-10-02 — INCOMPLETE / NOT READY\n\n'
            '**Do not install. Requested runtime implementation is unfinished.**\n\n'
            + hashes + '\n\n' + common + '\n\n' + checklist)
    replace(ROOT / 'projects/pgwr/STATUS.md', '**dk_cargo (2026-10-02, Codex)',
            r'^## ', '**dk_cargo (2026-10-02, Codex): INCOMPLETE / NOT READY.**\n\n'
            + common + '\n\nHashes and hardware checklist: own `CURRENT_INSTALL.md` entry.')
    replace(ROOT / 'projects/pgwr/CHANGELOG.md', '## 2026-10-02 — dk_cargo',
            r'^## ', '''## 2026-10-02 — dk_cargo research.1 (Codex; INCOMPLETE, NOT READY)

- Recovered forward-grab direction dispatch, existing-link pickup/throw events,
  mash message, generic lift callback and native offset dependencies (offline B).
- Pinned 207 conservative donor functions, 97 common functions, 94 victim motion
  lists, body suffix routing and 15 donor pose templates. Semantic graph incomplete.
- Added 30 checked template deltas to the existing 28 attacker clips/bank deltas.
- Recorded explicit authorization for +0x170/+0x210 cargo extensions; unimplemented.
- Corrected PLT artifacts, victim motion names and inferred camera hook requirement.
- Requested 15 attacker + three victim roles per eligible table; no IDs chosen.
- No runtime implementation/build, registration patch, shared version bump or install.
- Package/reproduction/evidence: own `CURRENT_INSTALL.md` entry.''')
    result_path = ROOT / 'evidence/2026-10-02_pgwr_dk_cargo/RESULT.md'
    old = result_path.read_text()
    failures = old[old.index('## Failures and corrections'):]
    marker = 'No emulator/game, SD access'
    failures = failures[:failures.index(marker)].rstrip()
    extra = '''
9. A guessed capture-event hash assertion failed; explicit rehash identified
   `0x5ecd55cc6` as `final`, excluded from cargo. No runtime branch was guessed.
10. Fighter-kind parser initially omitted uppercase hexadecimal values (34
    missing labels); case-aware parsing passed all 94 unique symbol mappings.
11. The earlier 16 donor/22 victim unresolved calls were imported PLT tails.
    Stopping at named imports yielded zero in those Lua graphs; native virtual
    sharing callbacks remain unresolved. Zero does not mean semantic completeness.
12. Default-sandbox evidence writes failed WinError 5; reviewed workspace-only
    generator runs succeeded. No writes outside task roots were needed.
13. ADRP scans found no independent constructor reference to candidate DK vtable
    0x4fa8c80, even with 256-byte windows. Identity remains D, not disproved.
14. All-module +0x190 store scan yielded 883 candidates. Matching an offset is
    insufficient ownership evidence. Retained the address inventory; narrowed
    assembly files to the recovered MotionModule std::function setter.
'''
    if '9. A guessed capture-event' not in failures:
        failures += '\n' + extra
    result_path.write_text('''# dk_cargo — 2026-10-02 — INCOMPLETE / NOT READY

**The requested runtime mechanic is not implemented.** This is an offline
research report, not a console-run report. The complete semantic graph required
before implementation remains incomplete. No additional authorization is being
requested; the two authorized native extensions remain unapplied.

''' + hashes + '\n\n' + common + '''

## Captured semantics and limits

Tier B: `semantic.py`, `native.py`, `victims.py`, `pose_route.py` measure the
pinned 13.0.4 main/DK/common images. Full hashes and exact instruction addresses
are in `refs/donkey_cargo/{SOURCE,local_inputs,DEPENDENCIES}.json`.
DK initializer assigns global_table[0x45]; common CatchCont reads it, and grab
cleanup classifies it as a throw. Pickup sends `shoulder` through the existing
capture link. `shoulder_throw` carries the victim directional motion and generic
target work IDs. Generic native consumers queue common START/THROWN phases.
Common CARRY sends mash-expiry event 0x21ba53a92c. No hand-built capture/link
sequence was added. Candidate DK callbacks still lack independent constructor
identity and exact +0x210 trigger proof (D).

The lift helper's inspected branch toggles COMMON LIGHT_WEIGHT then a callback
also defaulted on recipient Pyra. Calling the DK helper on eflame is prohibited.
Owned kinetic/parameter initialization is still unimplemented.

Native body-hash suffixes and enum families were independently measured; body
motion IDs are not interchangeable with motion-share IDs. Pose resource lookup
passes through native resource callbacks and a MotionModule +0x190 delegate.
The delegate setter is pinned at main+0x49f9e0, but its capture-specific callback
and empty-entry sharing resolver remain unidentified. The 883 store matches are
unclassified candidates, not a complete native dependency graph.

Correction B: main exports Singleton<FighterCutInManager>::instance_E, eight
bytes at 0x52b8850. Missing Rust bindings alone do not require a raw-offset hook.
Extern-symbol pointer/ABI and runtime validation remain unperformed.

Public ACMD/bindings pins are tier C. Asset appearance, attachment and gameplay
remain unverified. No reachable cargo function was found referencing the empty
`shoulder_damage` entry; requiring it is unconfirmed.

''' + failures + '''

No emulator/game, SD access, plugin/framework change, branch, commit, push,
shared regeneration or release-version bump. No console behavior is claimed.
''', encoding='utf-8')
    inventory_path = result_path.parent / 'FILES.json'
    previous = json.loads(inventory_path.read_text())
    files = set(previous['task_file_inventory'])
    for folder in (OUT, PACKAGE, Path(__file__).parent,
                   ROOT / 'builds/.cache/dk_cargo', audit.INPUT, result_path.parent):
        files.update(p.relative_to(WS).as_posix() for p in folder.rglob('*') if p.is_file())
    files = sorted(x for x in files if (WS / x).is_file())
    shared = set(previous['existing_shared_files_edited'])
    shared.update('mods/ssbu_mod_new/' + p for p in (
        'handbook/04_motion_lists_animation.md', 'handbook/graveyard.md'))
    inventory_path.write_text(json.dumps({'task': 'dk_cargo',
        'existing_shared_files_edited': sorted(shared),
        'task_file_inventory': files}, indent=2) + '\n')
    print('PASS: independent manifest/source/tool rehash; own queue entries and file inventory updated')


if __name__ == '__main__':
    run()
