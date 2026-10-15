"""Record preserved hardware failure and checked single-change retest candidate.

Smoke: record_revision.py. Updates only cargo entries; no card writes.
"""
from audit import ROOT,sha
from revision import PACKAGE,EVIDENCE,check,read,save
from record import replace

def run():
    check();m=read(PACKAGE/'MANIFEST.json');mh=sha((PACKAGE/'MANIFEST.json').read_bytes())
    hardware=ROOT/'evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_hardware'
    capture=read(hardware/'CAPTURE.json')
    result='''# dk_cargo 0.1.0 hardware result — 2026-10-03

Tier A: user reported pickup, mounted walking/jumping and grab release successful;
cargo directional throws crashed. Preserved log supports owned START/CARRY,
walk/jump/fall/landing transitions and clatter expiry -> catch cut -> victim
release/control state. This is evidence for the exercised cases, not every
victim/costume/direction/cleanup scenario. Vanilla DK/Pyra controls were not
reported, so a causal diagnosis remains a hypothesis.

Tested NRO 270bc6723393767b7ae0dd639faae821fe0ffde6357938a552bed41a7faa7795.
CAPTURE.json pins cargo log and all three 2026-10-03 crash reports.
All fail main+0x483130 (`ldr x8,[x8,#8]`) with X8=0, called from native
shared motion lookup main+0x49a594, through stock common
status_ShoulderedDonkeyThrown+0x270. Requested motion hashes are owned cargo
victim high/down motions. No c7 -> owned411 VICTIM_ROUTE was logged.

Correction to initial CAPTURE.json annotation: X21=0 is the valid capture link
slot index, not the null parent pointer. The object reference loaded from slot
+0x58 into X8 is null. That decoded register distinction is tier B. Native
instruction windows are preserved; game binaries were not modified.

Tier B: owned common Carry End compares NEXT_STATUS only to owned THROWN at
25c748; shared START/CARRY Exit compares owned CARRY/THROWN at 25dd2c/25dd64.
False comparisons reach set_invalid_capture and MA_MSC_CAPTURE_CAPTURE_CUT.
The native shoulder_throw receiver queues stock c7, whereas the Pre bridge
depends on the still-existing capture parent to route c7 to owned411.
Thus End/Exit cleanup can cut the link before Pre gets that chance (D diagnosis
until a controlled console retest). This is a transition-boundary bug in our
port, not evidence that a raw hook/framework rebuild is needed.

0.1.1 changes only those three comparisons to accept the queued stock semantic
alias as well as the owned role. No new capture/link construction, frame forcing,
native hook or assets. Existing good pickup/carry/release path is preserved in
source; runtime preservation still requires a regression check.
Build and 8448 compiled comparison controls passed offline. Corrected runtime
outcome remains unverified. Retest record: evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test/RESULT.md.
'''
    assert not (hardware/'RESULT.md').exists()
    (hardware/'RESULT.md').write_text(result,encoding='utf-8')
    block=f'''**dk_cargo (2026-10-03, Codex): 0.1.1-test READY for controlled cargo-throw retest; NOT INSTALLED.**

0.1.0 hardware A: user reports pickup, carrying/walking/jumping and grab release
successful; cargo throws crash. All three reports share a null capture object
reference at main+0x483130 during stock victim Thrown motion lookup.
Evidence: `evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_hardware/RESULT.md`.

Retest package `builds/pgwr/dk_cargo-0.1.1-test/`; NRO
`{m['nro_sha256']}` ({m['nro_size']} bytes), manifest `{mh}`.
5098 assets unchanged, tree `{m['mod_tree_sha256']}` (sorted path/TAB/hash/LF).
Single behavioral change: three owned End/Exit comparisons accept queued stock
victim carry/thrown semantic aliases so capture can survive to owned Pre routing.
Diagnosis remains D until controlled retest; no claim that throws now work.
Offline B: isolated release build, exact three-call-site delta, 8448 compiled
comparison controls, same assets/IDs, preserved source baseline and NRO checks passed.

Existing shared 0.20.20 / Gaogaen/Snake/Lucas/Ness baseline retained. No live shared
registration or framework changes. Four-file integration.patch still unapplied.
ID requirement unchanged: 15 attacker + 3 victim roles per eligible table, 18 on
eflame; production unallocated, private test IDs 0x400..0x411. Native generic
capture/shared-motion and actual victim native pickup scripts remain dependencies.
Host physics, attachment geometry, all four directional throws and death/swap/
interruption cleanup need hardware verification. No new reserved hook blocker.

Reproduction: `src/pgwr/tools/dk_cargo/revision.py prepare`; private snapshot
`builds/.cache/dk_cargo/test-plugin-0.1.1`, cargo-home under dk_cargo, target
`builds/.cache/dk_cargo/runtime-target-0.1.1`; offline cargo skyline build with
snake-neutral-b,hero-side-b, then `revision.py package`/`check` and
`check_transition.py`. Completed snapshots/packages remain immutable.
Assets inherit 0.1.0 ASSET_DELTA.json; zero new asset/config/motion/bank edits.
Full pins, hashes, controls and test sheet: `evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test/RESULT.md`.
'''
    queue='## dk_cargo — Codex — 2026-10-03 — READY: controlled cargo-throw retest\n\n'+block+'''
Test c06/c07 pickup, carry, jumping and escape first as the 0.1.0 positive control.
Then four ground cargo throws, both facings, and repeat airborne. Expect
`REGISTERED task=dk_cargo-0.1.1-test`, `VICTIM_ROUTE stock=0xc7 owned=0x411`,
advancing throw clips and one actual release. Compare vanilla DK/Pyra and unrelated
throws. Fail: same crash, missing victim route, frozen clips, stale links/control.
Log from boot: `sd:/ultimate/pgwr_dk_cargo_log.txt`; crash reports:
`sd:/atmosphere/crash_reports/`. Remaining twelve-step full checklist is in the
0.1.0 offline RESULT.md. No game/emulator has been run by this agent.
'''
    replace(ROOT/'CURRENT_INSTALL.md','## dk_cargo —',r'^Updated 2026-10-02\.',queue)
    replace(ROOT/'projects/pgwr/STATUS.md','**dk_cargo (',r'^## gaogaen_throw_b',block)
    path=ROOT/'projects/pgwr/CHANGELOG.md';text=path.read_text(encoding='utf-8');anchor='## 2026-10-03 — dk_cargo 0.1.0-test'
    at=text.index(anchor)
    text=text[:at]+'''## 2026-10-03 — dk_cargo 0.1.1-test (controlled retest candidate)

- Hardware 0.1.0: pickup/carry/jumping/release exercised successfully; three
  directional cargo throw crashes at null native shared-motion capture reference.
- Preserve queued stock victim states through three owned End/Exit comparisons;
  exact scalar alias control checks and isolated build passed. Runtime fix unverified.
- No assets, status allocations, shared registrations or frameworks changed.
  Evidence and hashes: `evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test/RESULT.md`.

'''+text[at:];path.write_text(text,encoding='utf-8')
    sheet=block+'''
Comparison controls: TRANSITION_CHECK.json evaluates exact compiled scalar
comparison branches, not a game/capture simulation. CHECKS.json includes linked
adapter disassembly. SOURCE.json pins the two changed runtime files and all
unchanged shared files. Native instruction labels/ABI remain; only three BL
targets differ in callbacks.S. Only other change is task boot version 0.1.1.

Reproduce existing candidate: python -B src/pgwr/tools/dk_cargo/revision.py check;
python -B src/pgwr/tools/dk_cargo/check_transition.py. Build command/source/cache
are in SOURCE.json and BUILD.txt in package. No build was run on shared source.

Controlled hardware retest:

1. Boot marker 0.1.1, baseline pickup/carry/jump/escape on c06/c07 unchanged.
2. Ground forward/back/up/down throws, both facings: victim stock c7 -> owned411
   route, advancing attacker/victim clips and exactly one actual release.
3. Repeat four directions airborne; landing/recovery/control restored.
4. Vanilla DK/Pyra controls and unrelated throws; then interruption/death/swap
   cleanup and the complete twelve-step 0.1.0 checklist. Return log from boot and
   crash reports. If earlier crash/new failure occurs, revert to backed-up 0.1.0
   and record the control before another variant. No causality claim yet.
'''
    (EVIDENCE/'RESULT.md').write_text(sheet,encoding='utf-8')
    files=[ROOT/'CURRENT_INSTALL.md',ROOT/'projects/pgwr/STATUS.md',ROOT/'projects/pgwr/CHANGELOG.md',
       ROOT/'src/pgwr/plugin/src/status/dk_cargo/mod.rs',ROOT/'src/pgwr/plugin/src/status/dk_cargo/callbacks.S',
       ROOT/'src/pgwr/tools/dk_cargo/emit_callbacks.py',OUT/'callback_translation.json']
    for folder in [hardware,EVIDENCE,PACKAGE]:files.extend(p for p in folder.rglob('*') if p.is_file() and p.name!='FILES.json')
    files.extend(ROOT/'src/pgwr/tools/dk_cargo'/n for n in ['crash_audit.py','revision.py','check_transition.py','record_revision.py'])
    save(EVIDENCE/'FILES.json',{'created_or_updated_files':{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(set(files))},
       'shared_live_registration_changes':False,'framework_changes':False,'card_writes':False})
    print('Recorded 0.1.0 hardware failure and controlled 0.1.1 candidate; no install')

if __name__=='__main__':
    from audit import OUT
    run()
