# SSBU mod workspace

This repository contains the working sources, project notes, pinned references, evidence, and decompiled text for the Super Smash Bros. Ultimate 13.0.4 mod workspace. The current Pyra Game & Watch Reskin release is **0.20.16**; its staged package and `MANIFEST.json` are in `builds/pgwr/0.20.16/`.

## Set up another device

1. Clone this private repository.
2. Copy `paths.example.toml` to `paths.toml` and fill in paths for that device. `paths.toml` is local and ignored by Git.
3. Create fresh game dumps under `dumps/arc/`, `dumps/exefs/13.0.4/`, and `dumps/scripts/` as needed. Those raw dump directories are ignored by Git.
4. Read `AGENTS.md`, `projects/pgwr/STATUS.md`, and the relevant pages linked from `handbook/00_INDEX.md` before changing the mod.

Example on PowerShell:

```powershell
Copy-Item paths.example.toml paths.toml
```

The repository keeps derived text, analysis scripts, symbol tables, and decompiled code in `dumps/decoded/`, plus `dumps/INDEX.md` and `dumps/MISSING.md`. Raw ARC exports, ExeFS binaries, and dumped script trees are not included. Game binaries copied into `src/pmclone/native/` are excluded too.

## Workspace map

- `src/pgwr/` — active Pyra c06/c07 to Mr. Game & Watch mod source.
- `projects/` and `handbook/` — current status, history, procedures, and findings.
- `refs/` — pinned donor/reference material with provenance.
- `tools/` — shared analysis and packaging tools.
- `dumps/decoded/` — derived, text-based decompilation and analysis outputs.
- `builds/pgwr/0.20.16/` — current staged release, including NRO, mod tree, and manifest.
- `evidence/` — dated test reports and supporting records.

Only the current staged release is tracked under `builds/`; other build outputs, toolchains, caches, scratch work, and local card backups remain local.
