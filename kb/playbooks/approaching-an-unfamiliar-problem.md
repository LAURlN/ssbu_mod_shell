---
title: How to approach a problem the knowledge base does not cover yet
summary: Default procedure when no playbook fits - narrow the question, find a working example, change one thing, test, write it down
status: seed
tags: [method, research, debugging]
updated: 2026-10-01
source: lab setup 2026-10-01
---

## When to use

No playbook in `kb/INDEX.md` matches the task, or the matching one failed.

## Steps

1. **Search before thinking.** `python -m smashlab kb search <terms>`, including the journal: a
   previous agent may have hit the same wall without writing a finding.
2. **State the question narrowly.** "Make Mario's up-B go higher" becomes "which param or script
   value controls it, where does it live, and how is that file patched".
3. **Find a working example.** In order: `mods/ssbu_mod_new`, then open-source mods that do
   something similar (HDR is the largest), then the framework's own examples and docs.
4. **Reproduce the example unchanged** before adapting it. If the unchanged example does not build
   or load here, that is the real problem, and it is an environment finding worth a note.
5. **Change one thing at a time**, and test after each change (build, then `lab emu test boot`).
   When something breaks you then know which change did it.
6. **When stuck after two different approaches**, stop. Write a `does-not-work` finding for each,
   and report `failed` or `blocked` with what is still untried. The orchestrator will escalate to a
   stronger model, which will read your findings.
7. **Write the playbook** once it works, so this procedure is not needed for that kind of task again.

## How to check it worked

There is a new or updated note in `kb/` that would have saved you most of this run.

## Known pitfalls

- Web posts about SSBU modding are often years old and describe tools or paths that have changed.
  Prefer release pages, repo READMEs and source code over forum posts, and mark anything untested
  as `unverified`.
- Offsets and function addresses are specific to a game version.

## Suitable tier

Step 1-3 research: scout. Getting an unfamiliar example to work: worker. Anything involving
reverse engineering game code: expert.
