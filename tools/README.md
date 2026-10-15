# Shared tools

Scripts and small programs that agents build for recurring jobs. `REGISTRY.md` is generated from
each tool's README frontmatter (`python -m smashlab kb index`).

## Adding a tool

1. Check `REGISTRY.md`. If something close exists, extend it.
2. Create `tools/<name>/` (lowercase-with-dashes) containing the tool and a `README.md`:

```
---
purpose: One sentence: what job this does
usage: python tools/<name>/<script>.py <args>
status: working | experimental | broken
lang: python | rust | powershell
updated: 2026-10-01
source: T-xxxx
---

What it does, inputs and outputs, an example invocation with real output, known limits.
```

3. Make it runnable from the workspace root with no setup beyond what the README states.
   Python tools: standard library where possible; otherwise declare dependencies inline
   (PEP 723) and run with `uv run`. Rust tools: a normal cargo project inside the folder.
4. A tool takes paths as arguments. It never hardcodes the dump location and never writes into `dump/`.
5. Run it once on real input before registering it, and paste that run into the README.
6. Mention the tool in the playbook that uses it.

Third-party tools (ArcExplorer, prc editors, ...) are not copied here. Describe where they are
installed and how to call them in `kb/reference/`.
