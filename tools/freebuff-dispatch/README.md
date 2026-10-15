---
purpose: Submit prompts to new Freebuff Desktop sessions through a gpt-6-luna Computer Use controller and block until the Freebuff agents report done
usage: python tools/freebuff-dispatch/dispatch.py <run|wait|status> --run-dir evidence/freebuff-dispatch/<id>
status: experimental
lang: python
updated: 2026-10-02
source: user request 2026-10-02 (Claude)
---

Freebuff has no headless mode (`kb/findings/freebuff-has-no-headless-mode.md`), so a Codex model
drives the Freebuff Desktop window instead. Standard library only.

## Run directory

```
evidence/freebuff-dispatch/<id>/
  prompts/<slot>.md   one task per file, written by the calling agent; the stem is the slot name
  common.md           optional; replaces {{COMMON}} in every prompt
  rendered/<slot>.md  what was actually pasted (header + prompt, placeholders filled)
  started/<slot>.txt  written by the Freebuff agent as its first action
  done/<slot>.json    written by the Freebuff agent as its last action
  luna/               app-server transcript (*.jsonl) and run-result.json
```

Placeholders in a prompt: `{{COMMON}}`, `{{SLOT}}`, `{{OTHERS}}` (slot + title of the other prompts,
taken from each prompt's first line).

## Commands

- `run` - for each slot without a `started/` marker: render the prompt, put it on the clipboard
  (`Set-Clipboard`), and run one `gpt-6-luna` turn (default effort `high`) through
  `codex app-server` that opens a **new** Freebuff session, selects `--freebuff-model`
  (default `Space Bunny Alpha`) at `--freebuff-effort` (default `High`), pastes and sends. It then
  waits up to `--start-timeout` seconds for the `started/` marker. Stops at the first slot that is
  not submitted, so nothing is sent twice; re-running skips slots that already started.
  `--only <slot> ...` limits the slots, `--render-only` just writes `rendered/`.
- `wait` - polls `done/` every `--poll` seconds and exits 0 when every slot has a non-empty done
  file (exit 2 on `--timeout`, default 7000 s). Uses no model tokens; run it as a background
  command and act when it exits.
- `status` - prints `not started` / `running` / `done` per slot.

## Requirements and limits

- The Codex desktop app must be running: it owns the Computer Use pipe that `codex app-server`
  reuses (`kb/findings/luna-desktop-codex-home-and-edge-approval.md`).
- Freebuff Desktop must be running and logged in.
- The controller only gets Computer Use access to apps whose name contains an entry of
  `APPROVED_APPS` (`freebuff`). Every other app-access prompt, URL elicitation, shell command and
  file change the controller asks for is declined.
- It uses the clipboard and the foreground window while `run` is active; do not type during it.
- `done/` is written by the Freebuff agent itself. A session that dies never writes it, so `wait`
  then ends by timeout - check `status` and the Freebuff window.

- The controller's `"submitted": true` is not trusted: a slot is confirmed only by its `started/`
  marker. If `run` stops with `NOT confirmed`, look at the Freebuff window before re-running.

## Observed run (2026-10-02, `evidence/freebuff-dispatch/2026-10-02_run1`)

```
[1-littlemac-fist-trails] submitted=True started_marker=True
[2-snake-up-tilt] submitted=True started_marker=True
[3-mythra-mana] turn completed: {"submitted": true, ...}      <- false claim, nothing was pasted
$ dispatch.py run --run-dir ... --only 3-mythra-mana          (v1.1.0, fresh thread per slot)
[3-mythra-mana] submitted=True started_marker=True
$ dispatch.py status --run-dir ...
1-littlemac-fist-trails: running
2-snake-up-tilt: running
3-mythra-mana: running
```

Details: `kb/playbooks/dispatching-freebuff-agents.md`.
