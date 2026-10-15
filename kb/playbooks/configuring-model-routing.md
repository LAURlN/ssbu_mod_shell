---
title: Configure providers and prioritized model groups in the lab Settings menu
summary: Configure providers, quota-aware model groups, and worker-default Jev routing with a stricter expert gate
status: verified
tags: [orchestrator, providers, settings, routing, jev]
updated: 2026-10-02
source: user-requested settings menu implementation, offline settings_selftest, and routing policy update
---

The Settings menu edits the lab's three task groups (`expert`, `worker`, `scout`), its separate
Manager group (the saved `continuation` configuration key is retained), manual-check threshold, and its
providers without changing emulator paths. Group names and descriptions are editable; the
internal tier IDs remain fixed for task compatibility and escalation.

## Steps

1. Open the desktop Smash Lab shortcut or run `python -m smashlab gui`, then open Settings.
   Source updates now restart the GUI server while idle and reload open pages automatically.
2. Enable the desired providers; CLI providers use the existing subscription login or their
   configured API key environment variable. API providers need a base URL and a key.
3. Paste keys in password inputs. Blank means preserve. Remove saved key removes the encrypted
   override only; legacy environment or `.env` configuration can still supply a key.
4. Set each group's description, model IDs, reasoning levels, and numeric priorities. Lower
   numbers win; Jev breaks ties. Set strict budget to wait if every candidate exceeds its
   budget share. Without strict budget, the old estimated-budget overrun fallback is retained.
5. OpenRouter model IDs are configured in candidate rows. Hosting slugs, ordering, allow/deny
   lists, sort preferences, fallback and parameter support are separate routing options.
6. Save while all lab jobs are idle. Changes apply to the next run. Saving does not contact
   a provider or validate model availability; exact IDs and supported efforts remain the user's
   responsibility.

## Persistence and verification

`config/settings.local.json` is gitignored and overrides base/local TOML settings. The settings
API exposes only whether keys exist. Keys use Windows DPAPI in gitignored
`state/credentials.dpapi.json`, consumed directly by Jev/API adapters and passed into configured
CLI child environments. Removing a provider from a group does not delete that provider.

Verified on Windows on 2026-10-01 with `python -m smashlab.settings_selftest`: nine passing
offline tests covering encryption/redaction, save/reload with machine settings preserved,
invalid input rejection, priorities, quota/cooldown fallback, exhausted-budget waiting, missing
and disabled providers, API spending caps, fallback after an agent quota error, CLI key
propagation, OpenRouter request fields and token-protected HTTP settings endpoints. Mock model
APIs are used; this is not a live-provider quota or model availability test.

Browser verification on `http://127.0.0.1:8876/#/settings`: saved Sol/high priority 1 and
Opus alias/medium priority 2, reloaded and observed persistence, added/removed a candidate,
edited OpenRouter ordering/sort and discarded those draft changes. No browser console errors.
Screenshot: `state/scratch/settings-menu.png`.

OpenRouter request format follows its official
[provider routing](https://openrouter.ai/docs/guides/routing/provider-selection) and
[reasoning tokens](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens) documentation:
`provider` contains hosting preferences; `reasoning.effort` contains the candidate effort.
Empty lists/sort fields are omitted. Delivery was checked against a mocked endpoint.

## Tier-routing calibration (2026-10-02)

Worker is now the explicit default for most bounded implementations, routine mod changes, tools,
documentation and clearly scoped research. Scout remains for quick, low-risk lookups and mechanical
edits. Jev may select expert only with at least the configured `expert_min_confidence` (default
0.8) and a positive `expert_required` judgment meeting `expert_required_probability` (default 0.7);
the question describes deep reverse engineering,
novel architecture and cross-component root-cause work as the expert cases. The keyword fallback
was narrowed so generic words such as “debug”, “design” and “investigate” do not independently
promote work to expert. Planner instructions use the same worker-default rule for subtasks; its
own run uses the parent task's tier, and an unusable plan no longer promotes a worker task.

Freebuff assignment is restricted to `worker` tasks in the Manager, resume routing, the handoff
API, stopped-task continuation review and task UI. Existing handoffs are not re-tiered or stopped,
since their agents may still be writing. The Freebuff interactive session still needs the user to
paste its prompt. These changes were reviewed statically only; no live Jev decision or Freebuff
handoff was run because automated tests and live agent checks are benched.

## Pitfalls

## Quota rule and its exemptions (2026-10-02)

A hard "20% of the five-hour window must remain" reserve (`router.worker_reserve_reason`) existed
for a few hours and was removed again at the user's request. Quota is governed only by each
group's budget share and strict budget, applied to the real five-hour reading when the CLI gives
one and to the ledger estimate otherwise. To keep 20% back, set the group's share to 0.8.

Two things are exempt and start no matter what the quota says: the Manager group (`router.pick`
skips the share, strict-budget and exhausted-window checks for `continuation`) and Luna's Codex
desktop controller that starts Freebuff sessions (`automation.py` makes no quota check). A
provider on cooldown after a rejected run or a failed login is still skipped for the Manager,
which then uses its next candidate.

- DPAPI tests returned `Windows could not access the encrypted API key store (error 2)` inside
  the Codex restricted sandbox. The same tests passed outside it under the Windows user account.
  Run the desktop lab normally; encryption intentionally fails rather than saving plaintext.
- Claude and Codex subscription limits are read from the CLIs themselves before each provider
  choice and override the estimated budget, including exhausted five-hour and seven-day windows
  (see [the finding](../findings/claude-and-codex-clis-report-real-subscription-limits.md)).
  A provider whose real five-hour figure is at or above the group's budget share counts as over
  budget, so with strict budget a group whose only automatic provider is that full waits.
  Gemini and Freebuff expose nothing and stay on the estimate.
- An `opus` alias does not pin Opus 5.5. Enter the exact supported model ID to pin a version.
- The source watcher waits until agents/jobs are idle before restarting. An old pre-watcher
  server needs a one-time restart; that desktop server was replaced on 2026-10-01.
