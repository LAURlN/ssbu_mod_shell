# P8-EDIT-DISPATCH - coordinator note (2026-10-05)

This task stopped without a report (the worker left 56 evidence files). Its check script
`check_p8.py` fails. Both causes are in the check script, not in the mod facts:

1. its `mov_imm32` decoder handles only MOVZ/MOVN, so the logical-immediate `mov` aliases at
   0x1808fa8 and 0x1808fcc are mis-decoded (the values P8 reported, -2 and -1, are correct);
2. its handler-table walk pairs the wrong accumulator — the install block alternates between
   x8 and x9, so it reads the neighbouring slot's `adrp`/`add`.

The task was continued as **P9-EDIT-DISPATCH**, which re-read every address from the image and
supersedes this evidence. P9's report section 8 lists the corrections. Run
`scratch/2026-10-05_P9-EDIT-DISPATCH/check_p9.py` (774 claims, 0 failures, six negative
controls; coordinator rerun in `evidence/P9-EDIT-DISPATCH/18_coordinator_rerun.txt`), not this
folder's check script.
