---
title: Mod wish list, Manager assignments, Freebuff slots and manual check-ins
summary: Only user goals are queued, stopped work is reviewed before new goals, automatic testing is benched, and the desktop GUI reloads idle source changes
status: verified
tags: [orchestrator, workflow, providers, desktop, gui, tasks]
updated: 2026-10-02
source: user-requested workflow reset 2026-10-01; static checks and direct local GUI observations
---

The current user preference is no automated testing, including Ryujinx. Only user goals and
their necessary subtasks are runnable. Follow-up suggestions are never automatically queued.
The policy lives in root AGENTS.md, config/lab.toml `[workflow]`, worker/planner prompts,
and the emulator entry point's disabled-testing guard. Report unverified behavior honestly.

## Use

1. Launch the desktop Smash Lab shortcut. Its target is Python's `pythonw.exe` with the absolute
   `launch_lab.pyw` argument and this workspace as the working directory.
   The launcher pins imports to this checkout. The exclusive localhost server on port 8765
   reuses only a matching workspace/version and watches Python/HTML/JS sources for updates.
2. Use the GUI's My mod list as primary input. Entries live in tasks/WISHLIST.json; only
   the user-facing UI edits this intent. The Manager reconciles entries into user-rooted tasks
   on Start working. Each list edit has a revision; removed items are retained as history.
   Unstarted obsolete tasks/dependency trees are terminated. An existing or possibly partial
   implementation gets a removal goal; active agents must stop first. Re-adding the same text
   restores the item with a new revision, allowing removal/addition cycles without losing intent.
   Direct tasks remain under Add a task directly, and user-authored INBOX.md bullets still work. Intake leaves the inbox
   untouched and remembers imported bullet hashes in state/intake.json. IDs are monotonic
   through state/task-counter.json, including after a queue reset.
3. Start working or Manager. Both reconcile the list and gate fresh work on reviewing
   stopped tasks. The Manager chooses automatic routing, Freebuff, or defer for each ready task.
   Freebuff participates in automatic scheduling for worker-tier tasks only: when independent work
   can safely overlap active tasks, the Manager should fill available Freebuff slots (up to three).
   Opening the popup queues a serialized gpt-6-luna/high computer-use controller to paste and
   start it on Space Bunny Alpha/high reasoning. Automatic CLI/API development work remains
   sequential in the shared workspace. Do not overlap tasks likely to touch the same files or that
   depend on each other. Invalid assignments hold work; no unrelated goals are allowed.
   The reviewer group in Settings defaults to gpt-6.1-sol/low priority 1, sonnet alias/low
   priority 2. It is separate from Jev's three task difficulty groups.
4. Every paused, deferred, failed or blocked task is classified continue, terminate, handoff or
   defer. Invalid/incomplete output stops fresh work. Unanswered result-file user questions
   are held blocked even if the reviewer chooses continue. Automatic handoffs must use an enabled
   provider in the task's model group. Enabled Freebuff is also a valid manual choice, with
   at most THREE simultaneous reserved slots. Active manual handoffs remain with the user.
   Manager termination cannot terminate a goal while an assigned descendant is still running. Terminating a goal terminates its active dependency tree.
5. Resumed ready tasks precede new goals. A failure pauses for the next continuation decision,
   rather than immediately rerunning. Each stopped task is reviewed once per run; a defer is
   eligible for reconsideration on the next run. Necessary dependency tasks carry a parent
   chain to a user goal. Standalone agent suggestions are never made runnable.
6. Only in-game checks require approval. Research/plan/docs and offline tool checks finish without
   approval; missing user answers still block. New result files carry needs_ingame_test explicitly.
   Work stops at the configured number of in-game checks, or one urgent in-game check. It queues a
   worker collective build/install batch, waits for active agents to stop, builds all completed READY
   changes and installs to the validated Switch card on E:. If absent, show the SD popup and install
   once it appears. Do not include unfinished sources or overwrite framework plugins.
   Check-ins stop watch mode too. Configure
   the normal manual-check threshold in Settings; optional explicit task caps still apply.

## Manual Freebuff completion

Each handoff writes state/handoff/T-xxxx.md with a fresh token, reserves a task marked
in_progress/last_run=handoff, plays smashlab/webui/freebuff-handoff.wav through Windows, and
is discovered by GUI polling as a copyable popup. GUI and CLI allocation/collection share
state/manual.lock, so the fourth concurrent allocation is refused. Popup creation calls the Luna
desktop controller, which preserves sessions with loading circles and ambiguous sessions, archives (right-click, Archive; never deletes)
visibly idle sessions under the user's standing authorization, and launches exactly one new task.
Three slots is the user's declared capacity, not a measured provider quota. Desktop controllers
run sequentially, while the resulting Freebuff workers run concurrently. Uncertain submissions
are blocked and never replayed automatically.

An agent writes the normal result JSON then runs the exact token-bearing command in its prompt:
`python -m smashlab complete T-xxxx --from freebuff --token <current token>`. It must stop writing
before this command. Missing/stale tokens or inactive handoffs are refused. Valid completion
collects done/needs_review/blocked/failed; a completed result with user checks stays in review.
The user can check Done in the sidebar or task view once the agent has stopped. If it
was stopped without finishing, use Agent stopped — return to Manager instead; this releases
the slot and pauses the task for review without claiming completion. Checking Done
is an explicit user acceptance and releases the slot. Unchecking a done task reopens it.
Closing the prompt popup only acknowledges it in this browser session; it never frees a slot.
The prompt can be reopened from the task or Freebuff slots. A reported task closes its popup.

List edits and user handoff assignment require the automatic run to be stopped to avoid stale
Manager decisions. Manual agents may remain active; removal reconciliation waits for them.
Task IDs use a process-shared counter lock; task markdown and list JSON are replaced atomically.

## Queue reset performed

All 28 old task files, their review reports and directly associated result/plan/live/handoff
records were removed from the visible stores to the recoverable workspace folder
state/trash/queue-reset-20261001-215122/. Game dumps, knowledge notes, provider usage and quota
ledgers were preserved. Task T-0029 is the only new goal: build an offline data.arc extraction
tool from local inputs, with output under gamedata and manual checks. No agent was launched.
Read tasks/queue/T-0029-*.md for the exact request.

Ryujinx/build/Ryujinx.exe and related binaries were found by listing local executable paths;
no executable was run, and no version or emulator compatibility claim was verified.

## Evidence and limits

Direct local API inspection reported one task (T-0029), no running agent, all testing/follow-up
workflow flags false, and the manual-check threshold 3. The updated GUI visibly showed
Start working, Manager, Settings, and the single new task. Python and JavaScript syntax
checks passed. No automated tests or model calls were run during this workflow change.
The reviewer decision behavior and check-in thresholds have not yet been observed with a live
agent. A full extraction tool is queued, not implemented in this run.

## Parallel Freebuff scheduling update (2026-10-01)

Static review found why the Manager did not use Freebuff: `config/settings.local.json` overrode the
enabled provider in `config/lab.toml` with `providers.freebuff.enabled = false`. The saved Manager
decision for T-0031 also said Freebuff was disabled. The Manager prompt previously received only
the task being assigned and the active-slot snapshot, so it could not compare that task with other
ready work. The queue at review time had one ready task at a time; T-0032 depended on T-0031 and
shared its output directory, so that specific queue had no safe parallel pair.

The local enable override is now true. The assignment prompt now includes other ready tasks and
active Freebuff tasks, and instructs the Manager to choose Freebuff when it finds safe independent
work so the scheduler can continue to the next task while Freebuff runs. Freebuff choices must name
their parallel task ID; stale or missing targets fall back to automatic assignment. The run loop
already returns to the queue after each Freebuff handoff. As of the 2026-10-02 update, the popup
queues a Luna computer-use controller instead of requiring prompt paste from the user.
Automatic CLI/API development tasks still run sequentially in the shared workspace.
These changes have only been statically reviewed; the current T-0032 run started with the old
loaded configuration, and live dispatch has not been observed. No tests were run because testing is
benched.

The planner prompt now also favors independent subtasks and requires dependencies only for real
output prerequisites or file-conflict avoidance. That helps create a ready queue the Manager can
actually parallelize. Existing dependency chains are preserved; this does not invent new goals or
remove real prerequisites. The run loop plans only enough authorized work to fill one sequential
automatic slot and the currently available Freebuff slots, so it can compare independent tasks
without planning the entire backlog first.

Six stale desktop GUI processes were closed after inspecting their exact command lines.
The desktop launcher started the new server (pid 18500); after subsequent authorized source
edits the watcher automatically restarted it (pid 9800) and its source revision changed,
showing that the idle update mechanism works here. Updates wait while agents/jobs are active.
The launcher writes failures to state/gui-launch-error.log. Do not kill unrelated Python
processes when diagnosing a stale GUI.

Desktop inspection from the restricted sandbox returned an empty Desktop path; inspection and
the user-authorized shortcut edit succeeded under the normal Windows account. GUI runtime
also needs that account for the encrypted API key store; see configuring-model-routing.md.

## Mod list / Manager update evidence and limits (2026-10-01)

Direct browser inspection showed My mod list, add/remove affordances (empty list), Start working,
Manager, the preserved T-0029 extraction task, Done checkbox, manual handoff button, and three
available Freebuff slots. Settings showed the renamed Manager group and the user's saved
manual-check threshold of 4, preserved rather than reset. The local state API reported capacity
3, no manual agents, no automatic run, and no new list entries. The source watcher applied the
new GUI revision automatically. Python syntax/import/CLI parser and JavaScript syntax checks
succeeded. No automated tests, agents, model calls, handoffs/chimes, extraction or Ryujinx runs
were executed. Reconciliation, live Manager decisions, overlapping slots and result collection
are implemented and inspected but still require the user's live check. Earlier screenshots and
the reset evidence above describe the prior workflow, not the renamed current buttons.

## Approval, console batches and desktop handoff update (2026-10-02)

Implemented in smashlab/automation.py, runner.py, prompts.py, web.py and webui/manager.js.
The GUI server monitors state every two seconds, including when browser polling is inactive.
Automation state is persisted in state/automation.json under a cross-process file lock.
Batch fingerprints prevent duplicate builds/installs; queued batches absorb newly completed
parallel work before building. Builds/installations wait for all writing agents to stop.
Packaged MANIFEST.json hash and included task coverage are checked before accepting a built
package. The installer worker must verify package/card tree hashes and backups through the
existing installer; restart during a build/install blocks for inspection rather than replaying.
Blocked batches have an explicit Retry worker button. Research checks no longer contribute to
the threshold. The user's existing threshold of four remains configured.

Observed: sd:/atmosphere/contents/01006A800016E000 and sd:/ultimate exist. An automatic
gpt-6-luna/medium desktop call for T-0042 completed with a blocked report: Computer Use
denied Microsoft Edge access before the popup could be read; Freebuff was untouched.
See state/results/freebuff-desktop-7a000fc6411c4ed199d645f8a2103383.json and its run log.
Grant app access before trying a fresh automatic handoff. The popup has a Retry Luna button
after resolving app access. Retries inspect the previous attempt and refuse a second submission
if the earlier one is uncertain. Successful launch, idle-tab archiving, Space Bunny Alpha/high
selection, collective builds and automatic SD installation remain
unverified. No automated tests or emulator runs were performed for this update.

## Console popup correction (2026-10-02)

## Desktop versus CLI app access diagnosis (2026-10-02)

Superseded later the same day: the cause was established and the controller now runs through
`codex app-server`, not `codex exec`. See
[the app-server finding](../findings/luna-desktop-codex-home-and-edge-approval.md). The
paragraph below is kept as the diagnosis history; its "plausible, not proven" mismatch is
resolved there, and Freebuff was observed as a desktop app, not a terminal.

Luna was launched as a separate `codex exec` subprocess by providers.py, inheriting the lab's
environment; it is not a desktop chat. Read-only inspection found no computer_use section in
%USERPROFILE%/.codex/config.toml and no CODEX_HOME override in this shell. The GUI process's
effective account/home was not established: Win32_Process inspection was denied by the sandbox.
The latest T-0047 controller also reported Edge denial before touching Freebuff. Thus a
desktop/CLI permission-context mismatch is plausible, not proven. The user's saved UI approval
must not be treated as evidence that this particular CLI process has app access.
Official documentation says persistent Windows approvals use computer_use.windows.
always_allowed_app_ids in CODEX_HOME/config.toml. It also states Computer Use cannot automate
terminal apps or ChatGPT itself. If Freebuff is hosted in a terminal, that restriction prevents
this proposed controller workflow even after resolving Edge permission; do not bypass it.
Source: https://learn.chatgpt.com/docs/computer-use (read 2026-10-02). Earlier instructions to
allow Windows Terminal and expectations of unrestricted terminal automation were incorrect.

The console package popup now has a sticky Close button, scrolls long checklists, strips
redundant item numbers and remembers dismissal in localStorage for that batch/status/message.
A changed status or new batch can notify again; closing does not retry or alter installation.
The stale batch containing T-0036/T-0042 became blocked when T-0042 moved to done. Its
task report records an already-completed, hash-verified installation of 0.20.16+robot-dtilt.4.
Obsolete batches are now retired as cancelled instead of showing an unresolvable Retry popup;
the old stale-blocked state is migrated when its tasks have completed/cancelled. This avoids
reinstalling that package. Source inspection only for this correction; no tests run.
