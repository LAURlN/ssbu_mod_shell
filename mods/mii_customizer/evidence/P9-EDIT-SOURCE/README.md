# P9-EDIT-SOURCE evidence

Worker: Space Bunny Alpha, 2026-10-05. Evidence tier **B** throughout: offline
measurement of bytes and of the parsed chunk. Nothing was installed, loaded or
run in the game.

Reproduce from the workspace root:

```bash
python mods/mii_customizer/tools/lua-src/build_check.py
python mods/mii_customizer/tools/lua-src/negative_controls.py
python mods/mii_customizer/builds/0.3.1-edit-probe/check_probe.py --build
```

| file | what it is |
|---|---|
| `build_check_output.txt` | `build_check.py` for both chunks: per-prototype table before the `is_vararg` post-pass, the post-pass itself, and the table after. Ends `BYTE-IDENTICAL (18 prototypes…)` and `BYTE-IDENTICAL` for both targets, exit 0. |
| `negative_controls_output.txt` | seven deliberate breaks, all caught, exit 0. Also records that the real source and the original chunk were untouched. |
| `check_probe_output.txt` | the probe package build: source regenerated, purely-additive check passed, chunk compiled, post-pass applied, payload staged, manifest written and verified. |
| `original.dis.txt` / `rebuilt.dis.txt` | full disassembly of the original and of the rebuilt chunk, for independent inspection. |
| `original.protos.txt` / `rebuilt.protos.txt` | per-prototype summaries. Identical apart from the filename header line. |
| `probe_manifest.json` | copy of the probe package `MANIFEST.json`: sizes, sha256s, per-prototype deltas and the probe's parameters. |

The single most important line for Part 1 is in `build_check_output.txt`:

```
-- per-prototype comparison after the post-pass --
bytes orig 10576  mine 10576  IDENTICAL
prototypes differing: 0 of 18
```

and the honest caveat is that this says the source compiles to the shipped
bytes. It does **not** say the game would accept a locally compiled chunk at
that path; that is untested.
