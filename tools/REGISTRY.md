# Tool registry

Edited by hand (the old `smashlab kb index` generator is retired). Rules for adding tools: `tools/README.md`.

| tool | status | purpose | usage |
|---|---|---|---|
| [data-arc-extract](data-arc-extract/README.md) | experimental | Offline, workspace-confined extraction of the patched SSBU 13.0.4 data.arc (or the unpatched base) from the local split/update NSPs | `python tools/data-arc-extract/run.py <discover|preflight|extract> --base PATH (--base-only | --update PATH) --prod-keys PATH [--title-keys PATH] --backend PATH --output gamedata/.../data.arc` |
| [freebuff-dispatch](freebuff-dispatch/README.md) | experimental | Submit prompts to new Freebuff Desktop sessions through a gpt-6-luna Computer Use controller and block until the Freebuff agents report done | `python tools/freebuff-dispatch/dispatch.py <run|wait|status> --run-dir evidence/freebuff-dispatch/<id>` |
| [arc-extract](arc-extract/README.md) | working | Extract individual files from the local SSBU data.arc by ARC path, so agents do not need ArcExplorer or the running console | `tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/ssbu-13.0.4/files [--index <paths.txt>] <arc path | folder/ | pattern*> ...` |
| [showcase-export](showcase-export/README.md) | experimental | Export a publishable working copy of the workspace without game data, game-derived code, third-party code or personal data | `python <dst>/tools/showcase-export/export.py --src . --dst <dst> --redact <account-name>` |
