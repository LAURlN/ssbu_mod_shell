# P13-KEYHELP - edit-menu Advanced Options tip

> **Coordinator review, 2026-10-07.** `check_keyhelp.py` rerun: exit 0 (rebuild, layout names,
> label `cmn_button_nx_minus`, only `initialize` changed). `build_check.py` both chunks
> byte-identical. The pattern `parts:get_pane(name):set_text_message(...)` has precedent in
> the game's own special-move script (reconstructed source lines 71-81). Accepted as target
> (2), replacing the Favourite tip. The block is reused unchanged in the 0.6.0 edit script
> (`tools/lua-src/make_minus_source.py`); the keyhelp-only package here is not installed.

Status: DONE (offline package staged; no console verification). Evidence labels: B = offline measurement; D = player-visible/runtime behavior hypothesis.

## Scope and method

Investigate the edit-menu Favourite keyhelp and the smallest safe way to show “- Advanced Options”. Inputs remain read-only; all game-derived extraction goes under workspace `gamedata/mii_customizer/P13-KEYHELP/`. No emulator, console, plugin changes, commits, branches, or out-of-scope edits.

## Part A — facts

### A1. Favourite tip anatomy

**Verified B:** the game-loaded archive is `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc` (927,100 bytes, SHA-256 `f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212`; also measured in `research/P6-EDIT-MENU.md` §0). The edit layout part `set_btn_keyhelp_00` is at BFLYT offset `0x003fb4`, position `(421,481)`, extent `(560,56)`, and references child layout `com_btn_keyhelp_00`; it has children `set_txt_icon` and `set_txt_help`. P6 source `research/P6-EDIT-MENU.md` §5 reports the `favorite_grp` group separately (`favorite` node); this group is not the keyhelp text.

The child BFLYT re-extracted into this task folder is 2,432 bytes, SHA-256 `a8d18b6a71b103888c3a2475081237835bb7693ad67ba28959c54141696a5df9`. Its `hit_txt` group contains `set_txt_icon`, `set_txt_help`, `bg`. Both named text panes are `txt1` blocks; the layout contains no `pic1` block. Their local origin is `(0,0)`, scale `(1,1)`, pane size `(40,48)`; z values differ (7 for icon, 53 for help). The `txt1` records include float pairs `(38.4,57.6)` for the icon and `(32,48)` for help (block offsets `0x45c/0x460` and `0x538/0x53c`). The only `fnl1` entry is font face `nintendo64`. The remaining text-format bytes differ between panes; the repo inspector does not decode their alignment enum, so I report stored values rather than infer left/center semantics. These are local layout measurements, not screen pixels.

The parent edit BFLYT was re-extracted to `gamedata/mii_customizer/P13-KEYHELP/blyt/make_mii_edit.bflyt` (21,004 bytes, SHA-256 `2668a7ecf146a31e5003df682208d21d3a4cd2d032d4d68e839dfe0853b6dd34`). It agrees with P6's 13-part inventory: the only `set_btn_keyhelp_00` instance is the part above; `all` contains `nul_keyhelp`, and `favorite_grp` contains `favorite`.

The parent part tail embeds message ids `mnu_mmiif_favorite_guide` and `mnu_mmiif_favorite` for the two text panes (BFLYT offsets `0x004204` and `0x0042cc` in the P6 inventory). Extracted English `msg_menu.msbt` is 268,096 bytes, SHA-256 `4b4f3d23640032858334ab0b51939f3675271cad326131bcb5c70c1a4f25b26b`: the guide is raw UTF-16 units `000e 0001 0005 0002 000c 0000` (an input-guide substitution tag); the second is `Favorite\0`. The tag is expanded by native message handling (`0x37adbc0`) before applying text (`0x37a1cc0` via `0x3779b70`), rather than being a picture embedded in the layout. The Lua chunk has no keyhelp text call in `initialize` or its frame update; its only keyhelp-specific action is hiding `set_btn_keyhelp_00` for `FROM_AMIIBO` (`make_mii_edit_actor.lua`, init around line 542; source SHA-256 `86648c36a9a050657ff56262d9d8d6631d7f8b0a9e54650e1a38999e2e8ec327`).

`com_btn_keyhelp_00` includes animation members `BlinkOn`, `BlinkOff`, `OnOff`, and `Disable` per the layout archive list and `research/P6-EDIT-MENU.md` §5. `BlinkOn`/`BlinkOff` are the named blink pair; which state the host uses when the Favourite hint appears is not established offline. No keyhelp animation call exists in `make_mii_edit_actor.lua`.

Native Lua method registrations are in the pinned `main.bin` (SHA-256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`): `get_parts` handler `0x3355520`, `get_pane` handler `0x3355680`, `set_text_message` handler `0x335a100`, and `set_text_string` handler `0x335a490`. Lookup paths dispatch into layout wrapper helpers `0x3776090` and `0x3776360`. The literal setter handler has an explicit null-inner-pane guard at `0x335a554`; when the pane pointer is null, it skips the setter and returns. This is not a missing-name runtime probe, and exact `get_parts`/`get_pane` absent-name results are not elevated beyond the inspected wrapper path. The package checker verifies every name it uses against the extracted layouts.

### A2. Minus glyph representation

**Verified B:** extracted `msg_common.msbt` from P11's task output is SHA-256 `f1a0e6e328cf49366959d00f10e9ed62faf6ea129f067414117e632eab6643fa`. Existing labels whose whole text is a Minus glyph are `cmn_button_nx_minus` (U+E0B6), `cmn_button_fill_nx_minus` (U+E0F2), `cmn_button_fill_nx_round_minus` (U+E0F0), `cmn_controller_joy_left_minus` (U+E125), and `cmn_controller_joy_side_left_minus` (U+E128), each followed by UTF-16 NUL. These are private-use glyph code points, not the `0x000e` message substitution tag. The task's exact `msg_menu.msbt` guide example above is a tag sequence that resolves through the message expander; `set_text_string` goes through `0x335a490` -> `0x37a22f0` -> `0x37a1cc0`, with a 1/2/3-byte UTF-8 decoder and no call to `0x37adbc0` (see `research/P11-ROW-TEXT.md` §Q2 and evidence files `10_set_text_string_0x335a490.txt`, `12_setstr_0x37a22f0.txt`). Therefore U+E0B6 itself can pass through as UTF-8 `EE 82 B6`; a message tag cannot. The generated script calls existing label `cmn_button_nx_minus`, which has one UTF-16 unit U+E0B6 plus NUL.

### A3. Tip lifetime

**Verified B for the Lua chunk:** initialization runs the keyhelp hide only under `FROM_AMIIBO`; frame update checks Favourite and invokes `switch_favorite`, but does not set the keyhelp text. The menu's ordinary show path is `initialize` once, then `main` enters its update/yield loop; no sub-screen return is handled by this script (P6 §6). The new block runs during `initialize`, after the layout view exists and before it is shown, and skips `FROM_AMIIBO`. No later Lua rewrite exists in this actor. Whether native focus/keyhelp code or the `switch_favorite` bridge reinitializes/replaces the text is not resolved offline; persistence across those actions remains tier D until console check.

### A4. Second-tip feasibility

**Verified B:** the edit layout has one keyhelp part instance and one icon/text pair; no second existing keyhelp part or spare pane is identified. A second tip would require an added layout pane/instance (longer BFLYT member); the current `sarc-layout` replacement path only supports equal-length members. The existing pair supports replacing both glyph and wording in script. Whether a combined wording fits the existing box is not established; the staged variant follows fallback (2) and does not depend on combined text fitting.

## Part B — deliverable

**Implemented fallback (2), supported by offline facts:** the additive initialize block gets part `set_btn_keyhelp_00`, changes `set_txt_icon` to existing `cmn_button_nx_minus`, and sets `set_txt_help` to literal `Advanced Options`. Both pane names and the part are verified by the checker against the extracted layouts. The block is skipped for `FROM_AMIIBO`. This is purely additive relative to `make_mii_edit_actor.lua`; `--strip` reproduces that source byte-for-byte. No pane/part name is invented.

The registered handlers are `get_parts=0x3355520` and `get_pane=0x3355680` in `main.bin`; they dispatch into layout wrapper helpers `0x3776090` and `0x3776360`. The literal setter handler `0x335a490` gets the inner pane and skips `0x37a22f0` if it is null (`cbz` at `0x335a554`), so a missing inner text pane is a no-op at that setter. The exact absent-part / absent-pane Lua return value was not exercised; this variant's names are checked present in the extracted layouts.

## Evidence and verification

**Verified B:** `make_keyhelp_source.py` generated the variant and `--strip` restored the base (19,857 bytes). `check_keyhelp.py --write-manifest` compiled the custom source with `luac-game -s`, changed only main `is_vararg` at offset `0x28` from 1 to original value 2, checked the extracted part/panes/child-layout reference, diffed all 18 prototype instruction streams against the original and staged the chunk. Only `main.p11` (`initialize`) instruction words changed; the other 17 streams are identical. Staged payload: 10,764 bytes, SHA-256 `b266ee0a53e97e1e516b2fb1aab06926e01661f8a2cc0738037ac4d39b26974b`. `MANIFEST.json` records the staged hash. Baseline `build_check.py` passed both chunks byte-identically (18 edit prototypes, 17 special prototypes); `negative_controls.py` caught 7/7 controls and verified its inputs remained unchanged. `check_keyhelp.py --neg` emitted the expected missing-pane mismatch and exited 1.

## Console check and rollback

1. Use the existing `CURRENT_INSTALL.md` workflow to install `builds/0.6.0-edit-keyhelp/mii_customizer_ui/`, then open an ordinary saved Mii in the editor.
2. Check the top-corner keyhelp shows the Minus glyph followed by `Advanced Options`.
3. Toggle Favourite and navigate away/back within the editor; check the new hint remains visible. Reopen an Amiibo edit only if you also want to confirm its keyhelp stays hidden.

Rollback: remove/disable this package and restore the previous edit-menu chunk through the same `CURRENT_INSTALL.md` workflow. No console run has been performed by this task. Every player-visible result, including glyph rendering, fit, and persistence, remains tier D until user console evidence.

## Final report

- Task ID: P13-KEYHELP
- Status: DONE (offline package staged; no console verification)
- Changed files: `research/P13-KEYHELP.md`; `tools/lua-src/make_keyhelp_source.py`; generated `tools/lua-src/make_mii_edit_actor_keyhelp.lua`; `builds/0.6.0-edit-keyhelp/{check_keyhelp.py,MANIFEST.json,mii_customizer_ui/info.toml,mii_customizer_ui/ui/script_patch/chara_make/make_mii_edit_actor.lc}`; `evidence/P13-KEYHELP/`; `scratch/2026-10-07_P13-KEYHELP/`; task-local extracted inputs under workspace `gamedata/mii_customizer/P13-KEYHELP/`.
- Could not verify: visible glyph/font rendering, text fit, host animation selection, or persistence after focus/favourite events; these require the user's console check. Exact absent-name Lua return behavior remains untested; every name in the staged block is checked present.
