---
title: Claude Code and Codex CLIs report the real subscription limits on request
summary: get_usage (Claude stream-json control request) and account/rateLimits/read (codex app-server) return the 5-hour and 7-day utilisation without spending quota; the lab probes both
status: verified
tags: [orchestrator, providers, usage, limits, claude, codex]
updated: 2026-10-02
source: user request "smashlab can't read the usage limits"; method read from the installed T3 Code server bundle and run here
---

## What

Both subscription CLIs answer a usage question on their machine-readable channel, with no model
turn and no quota cost. `smashlab/providers.py` (`probe_limits`) asks them, `smashlab/usage.py`
(`refresh_limits`, `set_limits`, `real_limits`) stores the answer in `state/limits.json`, and
`router.pick` trusts it over the unit ledger. Readings are refreshed before a provider is chosen
when older than 120 s, every 5 min while the GUI is open, and by `python -m smashlab usage`.

Before this the lab only listened for Claude's mid-run `rate_limit_event` and parsed a field
(`unifiedWindows`) that the event does not have, so `state/limits.json` never held usable data
and every bar in the GUI was the lab's own estimate.

## Evidence

Claude Code 2.1.286, Codex CLI 0.159.3, Windows 11, 2026-10-02.

Claude: start `claude -p --input-format stream-json --output-format stream-json --verbose` and
write one line to stdin:

```
{"type":"control_request","request_id":"usage","request":{"subtype":"get_usage"}}
```

The reply is a `control_response` whose `response.response` holds `subscription_type`,
`rate_limits_available` and `rate_limits.{five_hour,seven_day}` as
`{"utilization": 4, "resets_at": "2026-10-02T04:20:00.301733+00:00"}`. Utilisation is 0-100 here.
`rate_limits.model_scoped[]` (`display_name`, `utilization`, `resets_at`) carries extra weekly
windows for single models; it was empty on the account used. An unused window can come back
without a reset time. Answered in about 1.3 s.

The mid-run event is different: `{"type":"rate_limit_event","rate_limit_info":{"status",
"rateLimitType":"five_hour","utilization":0.04,"resetsAt":<epoch seconds>}}`. Utilisation is 0-1,
one window per event, and `utilization` can be missing.

Codex: start `codex app-server` and write JSON-RPC lines:

```
{"id":1,"method":"initialize","params":{"clientInfo":{"name":"smashlab","title":"SSBU mod lab","version":"1"}}}
{"method":"initialized"}
{"id":2,"method":"account/rateLimits/read"}
```

Reply `result.rateLimitsByLimitId.codex` (same as `result.rateLimits`) has `planType` and
`primary` / `secondary` as `{"usedPercent": 85, "windowDurationMins": 300, "resetsAt": 1790906471}`.
`primary` and `secondary` are positions; the duration tells which window it is (300 = 5 hours,
10080 = 7 days).

`python -m smashlab usage` then printed `claude 5h 8%, 7d 1%` and `codex 5h 87%, 7d 14%`, and no
probe process was left running afterwards.

## Why (if known)

`get_usage` is what the Claude Agent SDK calls `usage_EXPERIMENTAL_MAY_CHANGE_DO_NOT_RELY_ON_THIS_API_YET`,
so the shape can change with a CLI update. A probe that fails keeps the last good reading and the
lab falls back to the ledger estimate once that reading expires.

## What to do instead / next

- Gemini CLI and Freebuff have no equivalent that was found; they stay on `budget_units`.
- The reading is account-wide: usage from T3 Code, the desktop apps or another machine shows up
  too, which is the point.
- Not done: using the real reset time as the cooldown length after a rejected run. Cooldowns still
  use `cooldown_minutes` with back-off.
