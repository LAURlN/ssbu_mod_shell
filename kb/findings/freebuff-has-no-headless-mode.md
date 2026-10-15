---
title: Freebuff has no headless mode; Luna can drive interactive worker handoffs
summary: The Manager schedules worker-only Freebuff tasks and the popup dispatches Luna desktop automation; its first live attempt was blocked by Edge app access
status: verified
tags: [freebuff, orchestrator, providers]
updated: 2026-10-02
source: lab setup 2026-10-01
---

## What

`freebuff` has no `--print` / `-p` / `--headless` flag and does not read a prompt from stdin. The
orchestrator therefore cannot run it unattended like `claude -p`, `codex exec` or `gemini -p`.

## Evidence

`freebuff --help` on v0.2.11 lists only `--continue`, `--cwd`, `--trust-agents`, and the `login`
command. Upstream request for a headless flag: github.com/CodebuffAI/freebuff/issues/947 (open,
filed 2026-08-06, no maintainer reply seen on 2026-10-01). The `@codebuff/sdk` can run agents
programmatically but needs a paid `CODEBUFF_API_KEY`.

## What to do instead / next

- `lab handoff T-xxxx --to freebuff` writes the task prompt to `state/handoff/`, reserves one
  of three slots, plays the local chime and shows a GUI popup. As of 2026-10-02, the popup calls
  gpt-6-luna/high through `codex app-server` to use the computer-use skill to paste and start
  a separate Freebuff task on Space Bunny Alpha/high reasoning. This is desktop automation;
  Freebuff's headless adapter remains disabled.
  The prompt tells the agent how to collect its result using `python -m smashlab complete`
  with a handoff token. `lab collect T-xxxx` remains available for the user.
  See [Manager workflow](../playbooks/user-driven-workflow.md) for capacity and review rules.
  This replaces the older terminal-launch handoff. New handoff execution/sound has not been
  observed live while tests are benched; the no-headless finding retains its setup evidence.
- When the upstream issue ships, add a `_run_freebuff` adapter in `smashlab/providers.py` and set
  `headless = true` under `[providers.freebuff]` in `config/lab.toml`.

## Scheduler policy

As of 2026-10-02, the Manager may automatically assign independent worker-tier tasks to a
Freebuff handoff; expert and scout tasks must use automatic providers. Prompt creation and slot
reservation and desktop-controller dispatch are automated. A live Luna call for T-0042 was
observed, but Computer Use denied Microsoft Edge access before the popup was read; Freebuff
was untouched. Successful automatic task submission remains unverified. See the workflow note.
The denial was `codex exec` declining the app-access prompt; the controller now runs through
`codex app-server`, see [the controller finding](luna-desktop-codex-home-and-edge-approval.md).
Existing handoffs are allowed to finish; the restriction applies to new assignments.

## Update 2026-10-02: working replacement for the retired handoff

The `lab handoff` flow above belongs to the retired orchestrator. Its replacement is
`tools/freebuff-dispatch` ([playbook](../playbooks/dispatching-freebuff-agents.md)), whose first
live run submitted three prompts to Freebuff Desktop on Space Bunny Alpha / High. The claim above
that successful automatic submission is unverified no longer holds for that tool.
