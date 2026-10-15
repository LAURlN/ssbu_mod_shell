# dk_cargo 0.1.0 hardware result — 2026-10-03

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
