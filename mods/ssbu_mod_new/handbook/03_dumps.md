# Dumps

Tiers: **A** hardware-confirmed (console or decoded crash report) - **B** measured offline by a script that still exists - **C** read from pinned third-party source - **D** hypothesis. Anything without a tier below is A/B unless marked otherwise. Paths in the source column refer to the *old* workspace (`modpack_test_1`); the same material now lives under `projects/*/history/`, `dumps/` and `evidence/`.

- Offline, without the console: any base-game file can be extracted from the workspace's 13.0.4 `data.arc` with the workspace tool `tools/arc-extract` (workspace root; procedure in the workspace `kb/playbooks/extracting-single-files-from-data-arc.md`). Output lands in `gamedata/ssbu-13.0.4/files/`; pin what you use into `refs/` with its sha256. (B: two files byte-compared against ArcExplorer and arc-network copies, 2026-10-02)
- Live dumping = `libarc_network.nro` on the SD **and** Smash running, port 43022, close ArcExplorer during scripted extraction; "refused" means the plugin is missing, not that the tool is broken. Region 2 only. (A, memory)
- Two "dumps" in `source_audit` are GitHub tree listings only; `rubendal/ssbu` holds diffs (404s on raw fetch). Cite only files that exist locally. (A)
