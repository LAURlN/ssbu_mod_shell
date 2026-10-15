---
title: Luna desktop controllers run through codex app-server so Smash Lab can answer the Computer Use app approval
summary: codex exec declines the app-access elicitation and ignores the saved Edge approval; the controller now uses app-server and answers it for approved apps, with a live handoff still unobserved
status: unverified
tags: [orchestrator, computer-use, permissions, codex, freebuff, app-server]
updated: 2026-10-02
source: user request to investigate the Luna Computer Use launcher; Codex session logs, installed @oai/sky and node_repl, app-server schema and handshake
---

## Conclusion

A supported integration exists and is implemented, but no handoff has been observed through it.
Status stays `unverified` until one live handoff reaches Freebuff.

Windows Computer Use needs two separate things from its host:

1. **Desktop transport.** `@oai/sky` connects through `nodeRepl.nativePipe` to the named pipe
   in `[mcp_servers.node_repl.env] SKY_CUA_NATIVE_PIPE_DIRECTORY` of the Codex config.toml.
   The running Codex desktop app (ChatGPT.exe) owns that pipe and its
   `codex-computer-use.exe --parent-pid <desktop pid>` helper. Any Codex process that shares
   the same CODEX_HOME gets the transport for free **while the desktop app is running**.
2. **App approval.** When the helper wants an app, sky calls `nodeRepl.createElicitation`
   ("Allow Codex to use Microsoft Edge?", `_meta.codex_approval_kind = "mcp_tool_call"`,
   `connector_id = "computer-use"`, `tool_params.app`). That is an ordinary MCP elicitation
   and the Codex host has to answer it.

`codex exec` supplies the first and can never supply the second: it runs with approval policy
`never`, which declines every elicitation. `codex app-server` forwards the elicitation to its
client as `mcpServer/elicitation/request`, so a client can accept it. That is the same
mechanism T3 Code added, and it needs no custom helper client.

## Evidence (all on this machine, 2026-10-02, codex-cli 0.159.3, @oai/sky 0.7.5)

- Session log `~/.codex/sessions/2026/10/02/rollout-2026-10-02T01-47-10-...jsonl` (the T-0053
  controller, originator `codex_exec`, `approval_policy: never`): `sky.list_apps()` returned
  the real app list in 1.9 s, including `MSEdge` with window "(3) Smash Lab" and
  `com.freebuff.desktop` with window "Freebuff Desktop". `sky.activate_window` on the Edge
  window then failed after 0.1 s with `Computer Use was not approved to use Microsoft Edge`.
  So the transport worked under exec and only the approval failed.
- That error string is thrown in sky's `helper_transport.js` only when the elicitation
  answer is not `accept`. If no elicitation channel existed the error would instead be
  `Computer Use requires app approval but elicitations are unavailable`.
- `codex app-server` prints, on start: `computer_use.windows.always_allowed_app_ids is
  ignored` (unrecognized setting). The CLI core does not read the saved approval, and neither
  `codex.exe` nor `node_repl.exe` contains that key. The documented "Always allow" list is
  applied by the desktop app when it answers the elicitation. Saving `msedge.exe` there was
  correct for desktop chats and never could have helped an exec controller.
- The earlier "computer-use controls are unavailable" report (T-0048, 01:43) was not a
  transport failure. Its log shows the model importing `@oai/sky` successfully and then
  never calling a sky method, because the prompt of that revision forbade the file tools it
  needed to read the skill. The next two runs, with the corrected prompt, reached the desktop.
- Freebuff is the Electron app `Freebuff.exe` ("Freebuff Desktop"), not a terminal, so the
  Computer Use terminal restriction does not apply to it.
- Handshake run with `state/scratch/luna_app_server_check.py --handshake` (no turn, no
  quota): `initialize` succeeded with `codexHome` = the pinned home, and `thread/start` with
  `approvalPolicy: "on-request"`, `sandbox: "workspace-write"`, `approvalsReviewer: "user"`
  was accepted. `approvalPolicy: {"granular": ...}` was rejected with
  `askForApproval.granular requires experimentalApi capability`, so the stable `on-request`
  is used.

## What the lab does now

`smashlab/providers.py`: `run_agent(..., elicit=fn)` routes a codex run through
`_run_codex_app_server` (stdio JSON-RPC: `initialize` with `mcpServerOpenaiFormElicitation`,
`thread/start`, `turn/start`, wait for `turn/completed`). Elicitations go to `fn(params)`;
`True` answers `{"action": "accept", "content": {}}`, anything else `decline`. Command,
file-change and permission requests are declined or granted nothing, as under exec.

`smashlab/automation.py`:

- `_desktop_setup` also requires the Computer Use pipe to exist and otherwise blocks with
  "The Codex desktop app is not running".
- `_approver` accepts an app-access prompt only when it comes from the `node_repl` server
  with `codex_approval_kind = mcp_tool_call` and `connector_id = computer-use`, and the
  executable name of `tool_params.app` is in the approved set: the Codex "Always allow" list
  (`msedge.exe`) plus `[desktop_controller] approved_apps` in `config/lab.toml`
  (`freebuff.exe`). Audio recording, URL elicitations and every other app are declined.
  Decisions are stored per handoff as `approvals`, and declined apps are appended to the
  blocked message.
- Every server request and answer is written to `state/runs/freebuff-desktop-<token>.jsonl`.
- Serialization (`_desktop` lock), the three worker-only Freebuff slots, the quota exemption
  and duplicate-submission protection are unchanged. `controller_revision` is 3; the popup
  offers "Retry with updated launcher" for attempts made by older revisions.

## Still unverified

- No turn has run through the new path. Whether `on-request` forwards this elicitation, and
  whether `{"action": "accept", "content": {}}` is the shape node_repl accepts, is inferred
  from the schema and the sky source, not observed.
- The app id the helper reports for Freebuff. The approver matches the executable name
  (`freebuff.exe`); `list_apps` showed `process:C:\...\Freebuff.exe`. If it differs, the
  handoff blocks and the message names the declined id; add that name to `approved_apps`.
- Popup reading, idle-session deletion, Space Bunny Alpha/high selection and popup closing.

If the first live retry blocks, read `state/runs/freebuff-desktop-<token>.jsonl` first: it
holds the exact elicitation the server sent.

## Do not

Do not spawn `codex-computer-use.exe` or write a client for its protocol; the installed skill
forbids both. Do not add terminals, Codex or ChatGPT to `approved_apps`.

## History

- The persistent `msedge.exe` approval was saved to the desktop config with a backup at
  `config.before-luna-edge-access.toml`, and the controller's CODEX_HOME was pinned to
  `%USERPROFILE%/.codex`. Pinning is still required (it is where the pipe setting lives).
- `automation._report` reads `utf-8-sig`, because a controller wrote its JSON with a BOM.
- The claim that a Codex desktop chat is the only possible host was wrong, and so was the
  later suspicion that exec lacked the transport.

Sources: https://learn.chatgpt.com/docs/computer-use (approvals, desktop-only statement),
https://github.com/pingdotgg/t3code/discussions/6726,
https://github.com/pingdotgg/t3code/issues/8318 (read 2026-10-02).
Related workflow: ../playbooks/user-driven-workflow.md

## Update 2026-10-02: URL-confidence stop, and clipboard workaround (unverified)

After the approval fix, every controller attempt (T-0052, T-0056 x2+) stopped inside
`sky.activate_window` on Smash Lab with "could not determine the current browser URL on Windows
with enough confidence to enforce policy", before touching Freebuff. It happened with the
chrome-less `--app=` window and with a normal Edge window ("Smash Lab - Profil 1 - Edge"), so
the app-mode theory was wrong; the plugin cannot read Edge's URL here. No handoff on file in
`state/results/` ever reached `submitted`. Workaround implemented, untested: `automation.py`
puts the prompt on the clipboard itself (`Set-Clipboard`) and Luna only operates Freebuff, never
Edge. `_handoff_job` also retries up to 5 times when the report says `freebuff_touched: false`.
