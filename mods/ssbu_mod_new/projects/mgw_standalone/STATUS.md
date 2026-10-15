# mgw_standalone - Clone Engine standalone characters (FROZEN)

Source: `src/mgw_standalone` (probe crate, packaging tools, `smashline_1304` overlay, engine/workbench patches, `vendor/` pinned upstreams). History: `history/{README,DIAGNOSIS,ARCHITECTURE,MISSING_DUMPS}.md`; crash evidence in `evidence/mgw_standalone_*`.
Scripts still use the old layout (`target*`, `staging`, `downloads` were not copied; rebuild needs the upstream fetch scripts).

| Item | State |
| --- | --- |
| Stand-alone G&W clone in its own CSS slot with skin + portraits | works on hardware (p6+) |
| Mythra clone | always crashes; 8 distinct native faults found and decoded (`handbook/14`); p16 (body-model routing) never tested |
| Mythra+Pyra pair | never reached |
| `smashline_1304` | the corrected 13.0.4 smashline; build `5f4091ee…` is the plugin on the card. Rebuild instructions: `history/README.md` |
Why frozen: user moved to the reskin (2026-09-29). Value: offset corrections, ARCropolis config template, clone-pack workflow.
