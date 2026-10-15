# gaogaen_throw_b enabled tools (0.3.0)

Current package is **READY and enabled** at `builds/pgwr/gaogaen_throw_b-0.3.0/`.
Eflame 0x208 is allocated in live source, next free 0x209; no environment gate or
registration patch is required. No SD install or game run was performed.

Check current package:

```powershell
python -B src/pgwr/tools/gaogaen_throw_b/enabled_package.py check
```

`enabled_package.py prepare` packages a fresh 0.20.20-derived full tree and enabled
private build; it refuses an existing destination. Build/cache/source and all hashes
are pinned by MANIFEST.json. User instructions/build/installer commands and manual
checks: `evidence/2026-10-03_pgwr_gaogaen_throw_b/RESULT.md`.

The instructions below describe the historical 0.2.0 source/delta-only package. Its
NRO stays disabled and its allocation/patch steps must not be applied to current source.

## Offline checks

Run from the mod root:

```powershell
python -B src/pgwr/tools/gaogaen_throw_b/pipeline.py check
python -B src/pgwr/tools/gaogaen_throw_b/routes.py
python -B src/pgwr/tools/gaogaen_throw_b/engine_audit.py
python -B src/pgwr/tools/gaogaen_throw_b/collision_audit.py
python -B src/pgwr/tools/gaogaen_throw_b/runtime_package.py --check
python -B src/pgwr/tools/gaogaen_throw_b/handoff.py --check
git apply --check builds/pgwr/gaogaen_throw_b-0.2.0/integration.patch
```

`extract_native.py` reads pinned ARC entries from the local dump and writes task-owned
extracted NROs in workspace `gamedata/`. It uses an isolated copy of the existing ARC
tool to accommodate Windows path sanitization; shared tools remain unchanged. `routes.py`,
`engine_audit.py` and `collision_audit.py` audit pinned native/script inputs and emit
bounded evidence. They make no gameplay claim.

`runtime_package.py` generates the owned donor offset table and private Cargo snapshot.
`--check` verifies donor row mappings, exact float bits and source equality. `handoff.py`
without `--check` builds one package and one current-baseline merge smoke; it refuses
existing destinations. `--check` verifies package/snapshot/asset baseline hashes. Cargo
home, targets, Python/Capstone and merge smokes stay under `builds/.cache/gaogaen_throw_b`.

The asset merger semantically appends owned motion entries, sounds and config additions.
DK/Snake changes share some files: always replay onto an installer-owned fresh collective
tree. Never replace combined banks/lists/config with the packaged baseline files.
The current 0.20.20 smoke preserved all old samples/tones/labels and motion entries;
duplicate tone preflight rejected a repeated merge before mutation.

## Collective integration

Check/apply the narrow patch and combine its back-throw direction with DK cargo if DK also
registers stock THROW PRE. Preserve one dispatch. The status ID is **not selected here**;
installer checks all reservations and supplies its decimal allocation:

```powershell
git apply --check builds/pgwr/gaogaen_throw_b-0.2.0/integration.patch
git apply builds/pgwr/gaogaen_throw_b-0.2.0/integration.patch
python -B src/pgwr/tools/gaogaen_throw_b/pipeline.py merge --target builds/pgwr/<combined-version>/ultimate/mods/pyra_gamewatch_reskin
$env:PGWR_GAOGAEN_THROW_B_STATUS = $collectivelyAllocatedStatus.ToString()
# CARGO_HOME and CARGO_TARGET_DIR must point inside builds/.cache.
cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline
```

Missing/invalid allocation disables the status. Only install the newly built combined
NRO after comparing its hash with the installer package. Do not use the checked disabled
NRO. Donor intended behavior is unboosted; no Revenge system is added. Runtime manual
checks and the limits of the native capture/FFI path are listed in RESULT.md.
