# Monkey Flip 0.20.5 console result - 2026-09-30

Tier A: user reports "it didn't grab". Capture failed; victim animation and attack/jump release were not exercised by a successful port capture.

Installed: `builds/pgwr/0.20.5/MANIFEST.json`; verified install `evidence/install-record-2026-09-30_114510.json`.
NRO sha256 `b4fe0235df36ff948bde88da2294abcbf2dfdccc4a181c105b46fb2f6d59b5eb`.
Mod tree sha256 `202a4a4f89a5c21018efb43007b151ba3b4674278a0c2ecc3ad3547eea005c7c` (1701 files).
Boot log `pgwr_log.txt`, sha256 `58e8c5be9ec1eaaad0d3f11c043b7638efc3aaf81000e92dfaeeb600470df44b`. Final boot begins at line 1834.

The requested run included stock Diddy and the port. Five port entry attempts are logged.
One CAPTURE READY, 276 CAPTURE REFUSED invalid event/fighter range; zero CAPTURE EVENT, ACCEPT, SETUP, CATCH HANDOFF, CLING entry or VICTIMSTATUS.
96 port VICTIM samples: zero is_catch=true or CLUNG_DIDDY victim samples.
Stock Diddy control: 98 is_catch=true samples, cling 0x1e8 and attack 0x1e9/release 0x1ea transitions. Jump release is not established by the retained telemetry.
No new crash report was found on the mounted card; crash/freeze was not reported by the user. This does not prove every other move remained correct.
Nearest-opponent telemetry scanned low object IDs and did not resolve the run's opponent; box contact remains unmeasured.

Summary measured by `tools/summarise_pgwr_capture_log.py` 1.0.0, smoke checked; see `capture_summary.json`.
Verdict: FAIL to grab. The port receiver did not reach capture setup. Cause of range rejection is unconfirmed.
Next experiment: 0.20.6 C-ABI QueryMemory guard correction, bounded result/address/range logging and original-handler forwarding on rejection; ordinary Pyra grab as negative regression control.
