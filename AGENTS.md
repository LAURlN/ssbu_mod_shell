# SSBU mod workspace - rules for every agent

This is the user's Super Smash Bros. Ultimate modding workspace. The user prompts agents (Claude, Codex,
Gemini, Freebuff, ...) by hand. For `mods/mii_customizer/`, the user authorized the current chat to
coordinate phased work on 2026-10-04: it provides prompts; the user starts workers manually and reports
when they finish. Up to three Space Bunny Alpha workers in Freebuff may work concurrently. Complex
tasks may be assigned to Claude Opus 5.5 or GPT 6.1 Sol through user-copied prompts; conserve their quota.
This is chat-based coordination, not an automated dispatcher. The old `smashlab` software is retired;
do not read, run, or write to its former workspace. Other projects keep their existing workflows.

Do what the user's prompt says and stay inside it. If you find something out of scope, say so in your final
message. Do not start on it. Do not spawn other agents unless the user asks.

## Layout

| path | what it is |
|---|---|
| `mods/ssbu_mod_new/` | The mod workspace, its own git repo with its own `AGENTS.md`, `handbook/`, `projects/<p>/STATUS.md`, `evidence/`, `refs/`, `tools/`. **Whenever you read or change anything inside it, its `AGENTS.md` governs.** Where it is stricter than this file, the stricter rule wins. |
| `mods/mii_customizer/` | Separate Mii Gunner customization mod. Read its `AGENTS.md`, `STATUS.md` and assigned prompt; existing mod code is reference-only. |
| `dump/` | The user's game dump. **Read-only. Never modify, never copy out of the workspace, never commit.** |
| `gamedata/` | Files extracted from the dump (data.arc, single ARC files). Extract here, never into `dump/`, `kb/`, `tools/` or a mod's source tree. |
| `Ryujinx/` | Ryujinx source/build (LibHac etc.), used by tools. |
| `testenv/` | Portable Ryujinx install (`testenv/ryujinx/`), test scenarios and run output (`testenv/runs/`). |
| `tools/` | Shared tools that are not tied to one mod (dump extraction, emulator helpers). Check `tools/REGISTRY.md` before writing a script. Rules: `tools/README.md`. |
| `kb/` | Notes about the environment and the research done so far. Read `kb/INDEX.md` first. Rules: `kb/README.md`. |
| `evidence/` | Workspace-level evidence. Mod-specific evidence goes in `mods/ssbu_mod_new/evidence/`. |

## One place per fact

| kind of knowledge | where it goes |
|---|---|
| How SSBU / the mod works: moves, scripts, params, offsets, crashes, what was tried and failed | the mod repo: `handbook/`, `handbook/graveyard.md`, `projects/<p>/STATUS.md`, with an evidence tier |
| Mod-specific scripts (audits, generators, packaging) | the mod repo: `tools/` |
| This machine, the emulator setup, dump extraction | `kb/` |
| Tools that are not tied to one mod | `tools/` |

Do not copy handbook content into `kb/` or the other way round; link to it. The kb and the tools registry
used to be indexed with `python -m smashlab kb index`. That command is gone, so edit `kb/INDEX.md` and
`tools/REGISTRY.md` by hand when you add or rename a note or a tool.

An emulator run is not hardware. In the mod repo's tier system it counts as **tier B** (name the scenario
and the run folder under `testenv/runs/`), never tier A. Only the user's console gives tier A.

## How to work

1. **Orient.** Read `kb/INDEX.md` for anything touching your task. Read the target mod's `AGENTS.md`
   and status. Before reading inside `mods/ssbu_mod_new/`, read its `AGENTS.md`, relevant project status
   and the applicable pages listed in `handbook/00_INDEX.md`.
2. **Work.** Do what was asked.
3. **Verify.** Run the build or script when your change needs it, and report what you actually observed. Say
   plainly what you could not verify. Do not run Ryujinx or the emulator unless the user asked for it, and do
   not claim "works" for behaviour only the console can show. Give the user clear manual checks instead.
4. **Record.** Write down what you learned, including failures. A dead end is as valuable as a success:
   record what you tried, the exact error and your best guess why it failed (mod facts in the handbook or its
   `graveyard.md`, environment facts in `kb/`). Mark each claim `verified` (you ran it and saw it) or
   `unverified` (read or recalled, not tested). If an existing note is wrong, fix it in place and say what
   changed. Do not leave contradicting notes side by side.
5. **Report** briefly in your final message: what changed, what you verified, what is left, and any
   out-of-scope suggestions.

## Tools

Reusable scripts go in `tools/<name>/` (or the mod repo's `tools/` if mod-specific) with a `README.md` saying
purpose, usage and status. Prefer improving an existing tool over adding a near-duplicate. One-off scratch
scripts follow the mod repo's dated-scratch rule and do not go in `tools/`.

## Paths

This workspace lives at `<workspace>`. Do not hardcode that path in code or docs. Use relative paths
or the mod repo's `paths.toml`. Some old notes still show `<old workspace path>`; correct them when you
touch them.

## Hard rules

- Stay inside this workspace. Do not touch files elsewhere on the machine, except reading tool installs you
  were pointed to.
- Never push to any remote, never publish anything, never upload game files. Commits are local and only when
  the user asks.
- Never rewrite the user's existing git history. Do not create branches unless asked.
- Never install to the Switch SD card yourself. Follow the mod repo's `CURRENT_INSTALL.md` workflow.
- Do not read or print `.env` files or secrets. Do not put secrets in notes, logs or commits.
- Do not download game content, keys or firmware from the internet. Emulator and mod-loader binaries come only
  from their official project releases (see `kb/reference/emulator-test-env.md`).
- Do not install system-wide software. Project-local dependencies (cargo, uv, npm inside the workspace) are
  fine; note them in the kb.
- If you are blocked on something only the user can provide (the dump, a login, a decision), stop and ask a
  precise question instead of guessing.
