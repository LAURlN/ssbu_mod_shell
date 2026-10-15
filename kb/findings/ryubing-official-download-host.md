---
title: Ryujinx must come from update.ryujinx.app; the host was unreachable on 2026-10-01
summary: The official Ryubing download endpoint and why look-alike download sites are off limits; the host refused connections at setup time
status: verified
tags: [ryujinx, download, supply-chain]
updated: 2026-10-01
source: lab setup 2026-10-01
---

## What

The official Windows build is served by
`https://update.ryujinx.app/download/query?os=win&arch=x64&rc=stable`. That URL was read out of the
HTML of `https://ryujinx.app/download`, the project's own site. Releases and source live on the
project's Forgejo at `https://git.ryujinx.app`. The Ryubing GitHub organisation has no emulator
binaries (only the website, update server, LDN server, docs and issue trackers).

## Evidence

- 2026-10-01 (T-0003): retried official source https://git.ryujinx.app/ryubing/ryujinx; web fetch returned `Failed to fetch https://git.ryujinx.app/ryubing/ryujinx: (400) Timeout fetching`. Python urllib requests (20-second timeout) to that URL and https://git.ryujinx.app/projects/Ryubing returned `URLError <urlopen error timed out>`. No current revision obtained; used explicitly labelled pinned source mirror for CLI/log research, never mirror binaries.

- 2026-10-01: `git.ryujinx.app` and `update.ryujinx.app` (91.239.78.255) refused TCP connections on
  port 443 from this machine and from an independent fetch service, while `ryujinx.app` itself
  (behind Cloudflare) loaded normally. So the outage was on the project's side.
- A web search for "Ryujinx download" returned `ryujinx.co`, `ryujinx.io`, `ryujinxcanary.com`,
  `ryujinxcanary.org`, `ryujinxemulator.io` and others. None are linked from the official site.

## What to do instead / next

`lab emu install` uses the official endpoint. If it fails, retry later; do not substitute another
site. If the host stays down, ask the user to download a build themselves from
`https://ryujinx.app/download` and unzip it into `testenv/ryujinx/app/`.
