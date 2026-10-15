# P2-STAT-API - bounded per-fighter stat API assessment

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Before reading old-mod material read its rules, project status and relevant
handbook pages. Inputs remain read-only. Keep game-derived files in your assigned
workspace-relative gamedata/mii_customizer/<task>/ folder, never source/evidence.
Report exact inputs/hashes, commands, observed checks, failures and limits. B is
offline observation, C pinned source, D hypothesis; no runtime behavior claims.
Coordinator owns STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report
and chat with task ID, DONE/PARTIAL/BLOCKED, changed files and next experiment.
Paths below are mod-relative unless marked workspace-relative.

One goal: identify supported runtime APIs for overriding ONE Gunner instance's
walk speed and weight, independently of another Gunner. A source-based assessment,
not production hooks or a general native reverse engineering task.

Read research/P1-DATASET.md and inspect the existing catalogue's weight and
walk_speed_max records. The exact file defaults are known; runtime scope is not.
Read old-mod handbook/09_params_prc.md and 11_smashline_skyline.md after its rules,
handbook index and projects/pgwr/STATUS.md. Use pinned bindings/framework sources
already referenced locally, with Cargo.lock revision and exact symbol locations.
Start with local refs and the old plugin's narrow parameter/accessor-hook examples.
Do not search archived investigations broadly. Tool-install source caches may be
read only if workspace notes explicitly point to them. If a necessary source is
absent, consult primary upstream documentation/source only, pin its revision and
stay within this question; no library downloads/installations.

Answer for both parameters: is there a per-object accessor/callback, how is its
fighter owner available, when can values be cached, and what resets on stock loss,
respawn or object destruction? Separate a binding declaration from an actual
implementation or measured behavior. A global PRC replacement is not per-instance.
Setting current kinetic speed is not equivalent to overriding walk_speed_max;
no per-frame state forcing, fighter-kind casts or invented work IDs.

Inspect at most two relevant implementation paths plus one declaration path for
parameter retrieval. Give a small API/signature/provenance table and an honest
candidate call flow. If supported scoping cannot be demonstrated from sources,
report it unresolved and name the exact smallest native/runtime question needed.
Do not guess offsets or build a hook. Known fighter object identity can scope a
future diagnostic without solving saved-Mii persistence; do not design a saved-ID
map or loadout schema in this task.

Deliver one proposed future diagnostic comparing two Gunners with distinguishable
weight/walk settings, including no-override control and lifecycle checks, and what
logs/results would distinguish true parameter override from temporary kinetic
changes. Values/ranges are proposals only, not declared safe. No runtime runs,
no Rust/plugin build, UI analysis, layout changes or stat catalogue modifications.
Stop once these two parameters are assessed or two implementation paths exhausted.

Exclusive writes: research/P2-STAT-API.md, evidence/P2-STAT-API/,
scratch/2026-10-04_P2-STAT-API/,
workspace-relative gamedata/mii_customizer/P2-STAT-API/ (only if needed).
