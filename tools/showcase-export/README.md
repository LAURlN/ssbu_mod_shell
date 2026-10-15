---
purpose: Export a publishable working copy of this workspace (own text and code only; no game data, game-derived code, third-party code, binaries, logs or personal data)
usage: python <dst>/tools/showcase-export/export.py --src . --dst <dst> --redact <account-name> [--redact ...]
status: experimental
lang: python
updated: 2026-10-15
source: showcase export request, 2026-10-15
---

Walks `AGENTS.md`, `kb/`, `tools/`, `evidence/` and `mods/` of the workspace and copies text files into
`<dst>` with the same relative paths. Exclusion rules (directories, extensions, a reviewed list of
game-derived Rust files, decoded-data JSON names, refs data) and text edits are constants at the top of
`export.py`. From `scratch/` it copies only files that a copied document references by exact path, plus
the files those scripts name in the same folder.

In copied text it replaces workspace paths with relative ones, user-profile paths with `%USERPROFILE%`,
SD-card drive letters with `sd:/`, other drive paths with `<drive>:/`, the account names passed with
`--redact` with `<user>`, and e-mail addresses with `<email>`. In `.md` files it replaces runs of 12 or
more disassembly lines with a one-line note.

Output: the copy, plus `tools/showcase-export/export-report.json` (exclusion counts per reason and folder,
excluded source files, redactions per file, removed disassembly lines, copied scratch files).
Then run `make_manifest.py --src . --dst <dst>` (writes `MANIFEST.md` from the report) and
`check_export.py --dst <dst> --name <account-or-real-name> ...` (personal-data, size and link checks).
Run the export into an empty destination; it never deletes anything. Run the checks listed in the copy's
`MANIFEST.md` afterwards: the rules are heuristics, not a guarantee.

Observed run (2026-10-15): 1,144 files copied, 49 files redacted, 5 reports with disassembly removed;
`check_export.py` results are in the copy's `MANIFEST.md` ("Final checks").
