# lua-src

Reconstructed **Lua source** for two SSBU 13.0.4 editor chunks, plus the checks
that compile them and compare the result against the originals.

The two sources are readings of shipped bytecode. The compiled outputs are build
artefacts used only for comparison. Nothing here is meant to be loaded by the
game, and nothing here has been run in the game.

| source | original chunk | prototypes |
|---|---|---|
| `make_mii_special_actor.lua` | `ui/script/menu/chara_make/` (P5) | 17 |
| `make_mii_edit_actor.lua` | `ui/script_patch/chara_make/` (P9) | 18 |

The two differ: the P9 one is the `script_patch` build, which is the version the
game actually loads.

## Files

| file | role |
|---|---|
| `make_mii_special_actor.lua` | reconstructed source, P5 chunk |
| `make_mii_edit_actor.lua` | reconstructed source, P9 chunk |
| `build_check.py` | compiles both with `luac-game -s`, compares per prototype and byte-for-byte, applies the `is_vararg` post-pass |
| `compare_chunks.py` | the per-prototype comparator `build_check.py` calls; also usable on its own |
| `negative_controls.py` | breaks the build seven ways and asserts `build_check.py` catches each |
| `make_probe_source.py` | generates the P9 part 2 probe source from the byte-identical source; `--strip` proves the probe is purely additive |
| `make_entry_source.py` | generates both P10-EDIT-ENTRY variant sources from the byte-identical source; `--strip` proves both variants are purely additive |
| `make_mii_edit_actor_probe.lua` | **generated** by the above; the probe variant. Not a reconstruction — it is the P9 source plus one marked block |
| `make_mii_edit_actor_entry.lua` | **generated** by `make_entry_source.py`; variant `entry`: the P9 source plus the marked Favorite-on-Headgear exit-7 block in `update` |
| `make_mii_edit_actor_entry_marker.lua` | **generated** by `make_entry_source.py`; variant `entry-marker`: the above plus a marked boot-marker block in `initialize` (hides `btn_other_try`) |

## How to run the checks

From the **workspace root**:

```bash
# both chunks: compile, compare, post-pass, re-verify -> exit 0 only if both
# are byte-identical on disk
python mods/mii_customizer/tools/lua-src/build_check.py

# one chunk only
python mods/mii_customizer/tools/lua-src/build_check.py edit

# the negative controls (7 breaks, all must be caught)
python mods/mii_customizer/tools/lua-src/negative_controls.py

# regenerate the probe source and prove it is purely additive
python mods/mii_customizer/tools/lua-src/make_probe_source.py
python mods/mii_customizer/tools/lua-src/make_probe_source.py --strip

# regenerate both P10-EDIT-ENTRY entry sources and prove they are purely additive
python mods/mii_customizer/tools/lua-src/make_entry_source.py
python mods/mii_customizer/tools/lua-src/make_entry_source.py --strip
```

`build_check.py` writes to `gamedata/mii_customizer/P5-LUA-SOURCE/` and
`gamedata/mii_customizer/P9-EDIT-SOURCE/` and compares against the originals
under `gamedata/mii_customizer/P1-UI/`. On any mismatch it prints the
per-prototype table and exits 1.

## Status: both chunks byte-identical

| chunk | bytes | sha256 | result |
|---|---|---|---|
| `make_mii_special_actor.lc` | 7799 | `ffa2bafa…b40d65d` | byte-identical, 17/17 prototypes |
| `make_mii_edit_actor.lc` | 10576 | `c777ecc4…a9417` | byte-identical, 18/18 prototypes |

This is reached only after the `is_vararg` post-pass described below. Before it,
each file is identical to the original except for **one byte**, at offset
**0x28**: the main prototype's `is_vararg`, which the game ships as `2` and this
compiler writes as `1`.

| | original | plain `luac-game -s` output |
|---|---|---|
| main `is_vararg` (offset 0x28) | 2 | 1 |
| every other byte | — | identical |

Stock Lua 5.3.6 cannot produce `2` there:
`tools/luac53-game/src/lua-5.3.6/src/lparser.c` `mainfunc()` sets
`fs->f->is_vararg = 1` unconditionally for the main chunk, so no Lua source can
change it. `ldump.c` writes the byte straight through with no normalisation, so
whatever set it to `2` in the shipped chunks was not this toolchain. All three
SSBU editor chunks carry `2`.

`build_check.py` therefore writes that single byte, deriving the offset from the
parsed chunk and validating it against the neighbouring `numparams` and
`maxstacksize` before writing, and refusing to write unless the byte is `1` and
the original holds `2`. It then re-reads the patched file from disk and re-runs
both comparisons, so the verdict is about the bytes that exist.
`negative_controls.py` includes two controls that specifically attack this: one
disables the write, one shifts the derived offset by one. Both are caught.

## Limits

- **The checks are about bytes only.** Identical bytes say the source compiles
  to the chunk the game ships. They say nothing about whether the game would load
  a modified chunk, hash it, check its length, or behave differently. Only a
  console run settles that, and none was done here.
- **Byte identity with a local compiler is not what the game would accept.** The
  `is_vararg = 2` byte is itself evidence that the shipped chunks did not come
  from stock `luac`. "My chunk matches the game's byte for byte" and "the game
  would take my chunk" are separate claims; only the first is established.
- **Local names are invented.** A stripped chunk stores no local or upvalue
  names, so every name in these sources is my own descriptive choice, not the
  game's.
- **Line numbers are load-bearing, not cosmetic.** `linedefined` and
  `lastlinedefined` are stored for every prototype even in a stripped chunk, so
  each function must start and end on its original line. `lastlinedefined` is the
  line of the function's own `end`, so padding goes *inside* the function,
  immediately before that `end`. The blank lines hold those positions and can be
  moved freely as long as the first and last lines do not move.
- **The shipped file's text between those lines is unknowable.** Only what
  survives compilation is recoverable, so comments and any dead code the original
  had are absent here.
- **No decompiler was used.** The sources were written by reading the
  instruction listing.
- Reconstructed with `luac53-game` only. The `luac-control-*` builds were not
  used for these chunks.
- `make_mii_edit_actor_probe.lua` and `make_mii_edit_actor_entry.lua` /
  `make_mii_edit_actor_entry_marker.lua` are **generated**. Do not edit them;
  edit `make_probe_source.py` / `make_entry_source.py` and regenerate, or the
  next build will overwrite your change. Compiled and staged outputs of the
  entry variants live in `builds/0.4.0-edit-entry/` (see its README).

## 0.6.0 additions (coordinator, 2026-10-07)

| file | role |
|---|---|
| `make_keyhelp_source.py`, `make_mii_edit_actor_keyhelp.lua` | P13-KEYHELP: generator and generated source, base + one marked block in `initialize` (button tip) |
| `make_minus_source.py`, `make_mii_edit_actor_minus.lua` | 0.6.0 edit script: base + the keyhelp block + a marked block in `update` that leaves with exit value 7 when the global `MC_MINUS` is 1 (raised by plugin 0.6.0 on a Minus press). Built and checked by `builds/0.6.0-menu/build_edit_script.py` |
