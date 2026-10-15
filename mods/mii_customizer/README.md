# Mii Customizer

Separate mod project established 2026-10-04. No runtime implementation or installable build yet.

Goal: select and save moves and stats in Smash's Mii Fighter editor for individual Mii Gunners.
Initial move library: Gunner only; expand to Brawler/Swordfighter after the foundation is verified.
Existing Gunner normals have one available choice initially; special slots retain vanilla alternatives.
The precise slot/stat list and native editor extension points are research outputs, not settled facts.

Start with [STATUS.md](STATUS.md) and [AGENTS.md](AGENTS.md).
The current dispatch is [Phase 1](phases/01_discovery.md); its three prompts live in `prompts/`.
Each worker reports to its own `research/` file. The coordinating chat reviews them together.

Skills are optional reusable workflows, not substitutes for project rules. Use AGENTS.md for
standing requirements; consider a skill once a move-audit or packaging procedure is repeatable.
Freebuff skill discovery/support has not been verified; explicit prompt file reads work independently
of that feature. No custom skill or agent service has been installed.
