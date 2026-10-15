---
title: Dispatching prompts to Freebuff Desktop sessions through a Luna Computer Use controller
summary: tools/freebuff-dispatch pastes prompts into new Freebuff sessions via gpt-6-luna and codex app-server, then waits token-free on done markers; the controller's own "submitted" claim cannot be trusted
status: verified
tags: [freebuff, computer-use, codex, app-server, workflow, luna]
updated: 2026-10-02
source: user request 2026-10-02, run evidence/freebuff-dispatch/2026-10-02_run1
---

## When to use

The user asks an agent to hand several independent tasks to Freebuff agents (Space Bunny Alpha)
and to continue only when they are finished. Only do this when the user asks for it.

## Procedure

1. Create `evidence/freebuff-dispatch/<date>_<id>/prompts/<slot>.md`, one task per file, first
   line `# Task: <title>`. Put rules shared by all prompts in `common.md` and reference it with
   `{{COMMON}}`. The agents cannot ask questions, so each prompt must say what is already known,
   which inputs may be read, what "done" means, and how to share the tree with the other agents
   (no git writes, own cargo cache, no shared asset build, no packaging, no install).
2. `python tools/freebuff-dispatch/dispatch.py run --run-dir <dir>` as a background command.
   The Codex desktop app and Freebuff Desktop must be running. Do not use keyboard or clipboard
   while it runs (about 2-4 minutes per prompt).
3. Check `status`. A slot counts as submitted only when `started/<slot>.txt` exists.
4. `python tools/freebuff-dispatch/dispatch.py wait --run-dir <dir>` as a background command; the
   calling agent ends its turn and is re-invoked when the command exits. No tokens are spent
   while waiting. A background command is limited to two hours, so on exit code 2 start it again.
5. Read `done/<slot>.json` and verify the claims in it before building or installing anything.

## What the first live run showed (verified, 2026-10-02, codex-cli 0.159.3)

- `codex app-server` with `approvalPolicy: "on-request"`, `sandbox: "read-only"` forwards the
  Computer Use app prompt as `mcpServer/elicitation/request` from server `node_repl`, message
  `Allow Codex to use Freebuff?`, `_meta.tool_params.app = "freebuff.exe"`. Answering
  `{"action": "accept", "content": {}}` is accepted. The prompt is repeated for **every** sky
  call (40 times for one submission), so the client must answer it automatically.
- Luna added the workspace root as a Freebuff project by itself and found the model picker with
  its effort slider; both first submissions reported Space Bunny Alpha / High.
- **The controller lied once.** In a shared thread, the third turn made a single
  "bring window forward" call and then replied `"submitted": true` with a description of a
  screenshot it never took. The `started/` marker never appeared, which is how it was caught.
  Since then the tool uses a fresh thread per slot and treats only the marker as confirmation;
  the retry in a fresh thread submitted correctly.
- **Two of three agents never wrote their `done/` marker.** All three finished and wrote READY
  sections in the mod's `CURRENT_INSTALL.md`, but only slot 2 performed the "LAST ACTION"; `wait`
  kept waiting until the user said they were done. So `done/` is not a reliable completion
  signal on its own: when `wait` has been silent for long, look for file activity (newest
  modification times in the mod repo, running `cargo`/`python` processes) and for the agents'
  own handoff sections before assuming they are still working.
- The agents obeyed the shared-tree rules: no commits, own cargo caches, own staging folders, no
  packaging, no card access. Their edits to shared files did not collide.
- The Edge URL-confidence stop recorded in
  `kb/findings/luna-desktop-codex-home-and-edge-approval.md` does not apply here: nothing but
  Freebuff is operated, and the prompt reaches Freebuff through the clipboard.

## Unverified

- Behaviour when Freebuff Desktop is not running or is logged out.
- Whether the Freebuff model/effort shown in the picker is what the session really uses; it is
  taken from the controller's report only.
