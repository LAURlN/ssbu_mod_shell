# Knowledge base

The lab's long-term memory. Agents start every run by reading `INDEX.md` and end it by writing
down what they learned. `INDEX.md` is generated from note frontmatter (`python -m smashlab kb index`).

## Scope

This kb is about **the lab**: the orchestrator, providers, the emulator harness, this machine,
getting files out of the dump. Knowledge about the game and the mod (moves, scripts, params,
offsets, crash reading, what was tried and failed) belongs in the mod workspace's handbook,
`mods/ssbu_mod_new/handbook/`, under that repo's rules and evidence tiers. One place per fact:
link across, never copy. `python -m smashlab kb search` searches both.

## Folders

| folder | holds | write one when |
|---|---|---|
| `playbooks/` | Step-by-step approaches to a *kind* of problem ("change a move's hitbox", "debug a boot crash"). | You solved something that will come up again, or found a better way than the existing playbook. |
| `findings/` | Atomic facts learned by doing: this works, this does not, this gotcha exists. One finding per note. | Every time reality surprised you, in either direction. |
| `reference/` | Stable descriptions: file formats, toolchain setup, the test environment, external links. | You had to look something up that the next agent will also need. |
| `journal/` | One file per day, appended automatically by the orchestrator after each task. | Never by hand. |
| `_templates/` | Copy these. | - |

## Frontmatter (required)

```
---
title: Short and specific
summary: One sentence that lets a reader decide whether to open this note
status: verified | unverified | does-not-work | outdated | seed
tags: [smashline, hitbox, ryujinx]
updated: 2026-10-01
source: T-0012 (task id), or a URL, or "training knowledge"
---
```

Status meanings:

- **verified** - an agent ran it in this workspace and saw it work. Say how in the note.
- **unverified** - from the web, docs, or model memory; plausible but untested here.
- **does-not-work** - tried here and failed. Keep these; they stop the next agent from repeating it.
- **outdated** - was true, no longer is. Say what replaced it.
- **seed** - written during lab setup without testing. Treat as unverified.

## Writing rules

- File names: lowercase-with-dashes, named after the fact, not the task (`arcropolis-needs-plugin-nro-at-mod-root.md`, not `task-12-notes.md`).
- Lead with the conclusion. Then the evidence: exact commands, exact error text, versions, file paths, emulator run ids.
- One fact per finding. If you are writing "also", start a second note.
- Link related notes with relative links. When a finding changes a playbook, update the playbook too.
- Fix wrong notes in place and bump `updated`; do not add a contradicting note next to them.
- Game version, emulator version and tool versions matter. Record them when a result could depend on them.
- No game assets, keys or copyrighted dumps in the kb. Describe structures; do not paste content.
