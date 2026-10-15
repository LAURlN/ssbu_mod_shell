"""Record the checked cargo candidate in only this task's entries.

Smoke: python -B src/pgwr/tools/dk_cargo/record_test.py. Never installs.
"""
import json
from audit import ROOT, OUT, sha
from package import PACKAGE, check
from record import replace

CHECKLIST='''1. Save hashes and log from boot. Expect `REGISTERED task=dk_cargo-0.1.0-test private_ids=0x400..0x411 costumes=[6, 7] production=unallocated`. Compare vanilla DK and Pyra c00/c01; normal grabs and other throw directions must remain ordinary.
2. c06 and c07 standing/dash/pivot grabs, forward direction: one `PICKUP`, attacker 0x400, `VICTIM_ROUTE` to 0x40f. Confirm actual published capture and advancing attacker/victim frame/end values, rather than status requests alone.
3. Ground carry: pickup completion, idle, slow/fast walk, turn, forward/backward jump squat and platform pass. Compare vanilla DK priorities and attachment.
4. Jump, drift, walk off a platform and land. Confirm ground/air transitions and recovery; host G&W baseline physics remain.
5. Four ground cargo throws, both facings: states 0x40b..0x40e, victim 0x411, donor damage/angle/timing and one release.
6. Repeat all four throws airborne: donor kinetics/recovery/landing; victim gains normal control after release.
7. Low/high-damage mash escape: decreasing clatter, `ESCAPE event=0x21ba53a92c`, catch-cut and victim control restored.
8. Victim poses: several sizes, body suffix variants, G&W, another c06/c07 pair and Pickel overlay. Confirm advancing clips/end frames and aligned carry/throw anchors.
9. Slopes, platforms, ledges and blast zones: compare donor restrictions; no orphaned capture constraints.
10. Third-party hits, attacker/victim death, rebirth and match reset: interruption/end/cleanup, no stale link, invincibility or hidden items.
11. Swap requests/departures while carrying or throwing: compare restrictions; no victim attached to the dormant body and no stale state on return.
12. Regression: Snake down throw, Incineroar back throw, Ness back throw, Lucas down smash, normal grabs and unrelated moves. Repeat vanilla DK/Pyra controls; return log from boot and any crash report.'''

def run():
    check();m=json.loads((PACKAGE/'MANIFEST.json').read_text());mh=sha((PACKAGE/'MANIFEST.json').read_bytes())
    block=f'''**dk_cargo (2026-10-03, Codex): READY for private hardware test; NOT INSTALLED, gameplay unverified.**

Package `builds/pgwr/dk_cargo-0.1.0-test/`; task version 0.1.0-test, shared
plugin/info version 0.20.20. Includes the checked Gaogaen 0.3.0 baseline and
Snake/Lucas/Ness changes. NRO `{m['nro_sha256']}` ({m['nro_size']} bytes).
Mod tree `{m['mod_tree_sha256']}` ({m['file_count']} files; SHA256 sorted path/TAB/hash/LF).
Manifest `{mh}`. Asset delta: 3126 declared paths; 725 list append operations;
2359 victim clips including 36 full shared templates; 28 attacker clips;
append-only SE/VC/SQB and checked effect merges. Baseline entries preserved.

Offline B: isolated release build passed; source/baseline, callback, ID,
motion/config/bank/hash and linked SIMD-return checks passed. No game/emulator
or console result; compilation does not verify capture or release.
Implementation owns 15 attacker states, three victim roles, native translated
callback closure, clatter/offset parameters, motion aliases, four ACMD families,
escape/release/cleanup. Host G&W baseline physics and geometry require review.

Full collective ID requirement: 15 attacker + 3 victim states per eligible
table, 18 on eflame. Production IDs unallocated. Private test uses audited
0x400..0x411, above native NUM maximum 0x37d, disjoint from shared IDs.
No production shared ID edits. Additional pending moves must be conflict-checked.

Shared integration: UNAPPLIED four-file `src/pgwr/tools/dk_cargo/integration.patch`;
Patch check: `git apply --ignore-whitespace --check` passed against the exact
recorded live baseline. Plain apply check rejects mixed LF/CRLF context.
status registration, existing Monkey Flip +0x170 receiver, G&W +0x210 callback
(only explicitly authorized cargo extensions), existing exported Gaogaen throw
classifier. Forward slot global_table[0x45] changes only eflame c06/c07.
Victim bridges are gated by an owned captor; actual victim native pickup scripts
and generic engine link/shared-motion interfaces remain dependencies. No DK
specializer on eflame, manual capture/link construction or per-frame forcing.
Framework plugins untouched; no further reserved hook requirement established.

Mergeable deltas: package `ASSET_DELTA.json`, config/motion-list additions,
sound/effect/animation audits and `integration.patch`; regenerate semantic banks
against a different collective baseline. Runtime sources under
`src/pgwr/plugin/src/status/dk_cargo/`; private compile snapshot/cache under
`builds/.cache/dk_cargo/`. Reproduction: task tools `README.md`.
Checks/evidence/failures/files and twelve hardware checks:
`evidence/2026-10-03_pgwr_dk_cargo/RESULT.md`, `FILES.json`, `LINKED_ABI.json`.
'''
    queue='## dk_cargo — Codex — 2026-10-03 — READY: private hardware test\n\n'+block+'''
Designated installer: use the complete checked package as a replacement over
the recorded Gaogaen 0.3.0 baseline. Copy only its mod tree and two task/helper
NROs, keep framework installation OFF, verify hashes/overlaps and use the
canonical backup/staging workflow. Do not apply the source patch to install a
prebuilt NRO. Pending production allocation is a collective integration blocker,
not a blocker for this isolated candidate. No additional pending task is included.

Cargo log: `sd:/ultimate/pgwr_dk_cargo_log.txt`; crashes:
`sd:/atmosphere/crash_reports/`. `STATE`/`VICTIM` frame/end, `VICTIM_ROUTE`,
`ESCAPE`, `INTERRUPT`, `CLEANUP`, `RELEASE` are diagnostics, not pass claims.
Fail: absent pickup/routing, nonadvancing/wrong clip, retained link/control after
release, missing escape/cleanup, `FAIL unsupported victim offset`, or a crash.

'''+CHECKLIST+'\n'
    replace(ROOT/'CURRENT_INSTALL.md','## dk_cargo —',r'^Updated 2026-10-02\.',queue)
    replace(ROOT/'projects/pgwr/STATUS.md','**dk_cargo (',r'^## gaogaen_throw_b',block)
    change='''## 2026-10-03 — dk_cargo 0.1.0-test (Codex; READY for hardware test)

- Added owned pickup/carry/ground-air/directional throw and victim callback
  runtime, escape/release/cleanup, approved receiver extensions as a narrow
  unapplied patch, and an isolated combined candidate over Gaogaen 0.3.0.
- Offline build and package/ABI checks passed; production allocation pending;
  no install or runtime conclusion. Full hashes, dependencies, failures and
  hardware checklist: `evidence/2026-10-03_pgwr_dk_cargo/RESULT.md`.

'''
    path=ROOT/'projects/pgwr/CHANGELOG.md';text=path.read_text(encoding='utf-8');anchor='## 2026-10-02 — dk_cargo research.1'
    assert anchor in text
    if change not in text:path.write_text(text.replace(anchor,change+anchor,1),encoding='utf-8')
    result=block+'''\nEvidence tiers: B = measured local bytes/build, C = pinned public source,
D = predicted recipient behavior. No tier A result. Native inputs: main
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613;
DK NRO 14030b3cfb605cddf114ba5f140dbd554515b7834209e15067a6dd632c9b555b;
common NRO 43876f961a80e413370629d32c23af9de6e4cc26b448bab88d5433714a566097.
Public ACMD commit 59004685238a3f6f93bae905d3a4e079701c40b4 (C).
Reviewed contract pins 71 attacker + 48 common/helper functions, 10911
translated instructions and 152 classified relocations; no unresolved indirect
calls in that owned closure. Generic engine interface internals are dependencies,
not a claim of complete engine decompilation. Donor class-factory identity remains
a D hypothesis; no donor class callback is invoked by this port.

Verified failures/corrections (B): private getter missing-key path returns zero,
not neighboring value 13; long-lived const-bank registers defeated older semantic
annotations, fixed with independently decoded bank; ABI signature extra parent-ID
argument caused E0061, corrected to SDK; own-ID ADR_PREL/LDST PIC linker errors
fixed with hidden symbols; ABS64 text callback pointers replaced with owned
ADRP/ADD. Cached BUILD-linker-failure.txt and BUILD-pointer-relocation-failure.txt
record exact errors. Victimlocal pickup filenames collided with eflame captor
templates, corrected before final stage. Prepackage retry appended aliases twice,
corrected to native ARC baseline for newly introduced lists. Native callback
registration measured 18, replacing guessed 24 (no Exec/MapCorrection).
Framework source supports wildcard statuses but concrete-kind ACMD only;
per-kind scripts now registered without a framework change. Final checker first
compared an intermediate append hash to the final twice-appended list, then
incorrectly assumed 96 victim-template nodes; corrected to exact native 26/67
track lists. Final package and linked SIMD checks passed after corrections.

Record tool initially used Windows default cp1252 for the changelog and failed
UnicodeDecodeError on byte 0x9d; corrected to explicit UTF-8 before recording.
Integration patch normalizes text line endings while the shared baseline is
mixed LF/CRLF. Plain git apply --check failed at status/mod.rs:61 and
gaogaen_throw_b.rs:71; all four baseline hashes still matched. The explicit
git apply --ignore-whitespace --check passed. No source patch was applied.

Build retains SDK SIMD Vector3 FFI warning; LINKED_ABI.json checks supported
returns load x/y/z into v0 and reach the epilogue without mutation. This verifies
only this compiled artifact. Generic capture check_damage_thrown virtual
implementation is not fully decompiled; console routing/cleanup must be tested.
Host baseline physics, retarget alignment, runtime clipping, playback and all
capture/release behavior remain D/unverified. There is no established additional
reserved-hook/framework blocker. Production allocation is pending as above.

Installer: complete package over its exact baseline using CURRENT_INSTALL.md
workflow, protected framework plugins OFF. No files have been installed here.
Reproduction: src/pgwr/tools/dk_cargo/README.md; CHECKS.json and BUILD.txt in
package. Manifest source_tool_pins are packaging-time provenance; task docs and
the secondary verifier were updated afterward without modifying payload.

Hardware checks (maximum twelve). Send log from boot and any crash report:

'''+CHECKLIST+'\n'
    folder=ROOT/'evidence/2026-10-03_pgwr_dk_cargo';folder.mkdir(exist_ok=True)
    (folder/'RESULT.md').write_text(result,encoding='utf-8')
    paths=set(m['source_tool_pins'])
    paths.update(p.relative_to(ROOT).as_posix() for p in folder.rglob('*') if p.is_file() and p.name!='FILES.json')
    paths.update(['CURRENT_INSTALL.md','projects/pgwr/STATUS.md','projects/pgwr/CHANGELOG.md',
        'handbook/15_grabs_catch.md','handbook/04_motion_lists_animation.md','handbook/graveyard.md',
        'src/pgwr/tools/dk_cargo/verify_linked.py','src/pgwr/tools/dk_cargo/record_test.py'])
    report={'description':'Task paths created/updated, including prior research tools; shared documents have only task-owned edits.',
       'workspace_files':{p:sha((ROOT/p).read_bytes()) for p in sorted(paths) if (ROOT/p).is_file()},
       'package_files':{p.relative_to(PACKAGE).as_posix():sha(p.read_bytes()) for p in sorted(PACKAGE.rglob('*')) if p.is_file()},
       'private_compile_snapshot':'refs/donkey_cargo/integration_snapshot.json',
       'extracted_inputs':'Package ASSET_DELTA.json input_files and clip source hashes; refs/donkey_cargo/local_inputs.json',
       'shared_live_registration_files_changed':False}
    (folder/'FILES.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Recorded checked candidate in own queue/status/changelog; no install')

if __name__=='__main__':run()
