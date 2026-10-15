# P13-KEYHELP evidence

Evidence tier: **B** for offline layout/message/code measurements and build checks. **D** for all player-visible behavior; no console or emulator was run.

## Input identity

| Input | SHA-256 |
|---|---|
| `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc` | `f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212` |
| `gamedata/mii_customizer/P13-KEYHELP/blyt/make_mii_edit.bflyt` | `2668a7ecf146a31e5003df682208d21d3a4cd2d032d4d68e839dfe0853b6dd34` |
| `gamedata/mii_customizer/P13-KEYHELP/blyt/com_btn_keyhelp_00.bflyt` | `a8d18b6a71b103888c3a2475081237835bb7693ad67ba28959c54141696a5df9` |
| `gamedata/mii_customizer/P13-KEYHELP/ui/message/msg_menu.msbt` | `4b4f3d23640032858334ab0b51939f3675271cad326131bcb5c70c1a4f25b26b` |
| `gamedata/mii_customizer/P11-ROW-TEXT/ui/message/msg_common.msbt` | `f1a0e6e328cf49366959d00f10e9ed62faf6ea129f067414117e632eab6643fa` |
| `gamedata/ssbu-13.0.4/main.bin` | `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` |
| `gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc` | `c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417` |

## Measured names and code units

- Parent part: `set_btn_keyhelp_00`, parent BFLYT offset `0x003fb4`; child layout reference `com_btn_keyhelp_00`.
- Child text panes: `set_txt_icon`, `set_txt_help`; both `txt1`. The child layout has no `pic1` node. It also has animation members `BlinkOn`, `BlinkOff`, `OnOff`, `Disable`.
- Existing baked labels: `mnu_mmiif_favorite_guide` = UTF-16 units `000e 0001 0005 0002 000c 0000`; `mnu_mmiif_favorite` = `Favorite\0`.
- Existing Minus label: `cmn_button_nx_minus` = UTF-16 `e0b6 0000`, a private-use glyph; its UTF-8 byte sequence is `ee 82 b6`.
- Literal setter route: Lua method handler `0x335a490` -> UTF-8 converter/setter `0x37a22f0` -> pane text apply `0x37a1cc0`. Message-key expansion route: message helper `0x3779b70` calls `0x37adbc0`; the literal setter does not call the tag expander.
- Getter handlers: `get_parts` at `0x3355520`, `get_pane` at `0x3355680`. Missing-name return behavior is not probed; checker verifies all package names exist.

## Commands and results

From the workspace root:

```text
python mods/mii_customizer/tools/lua-src/make_keyhelp_source.py
python mods/mii_customizer/tools/lua-src/make_keyhelp_source.py --strip
python mods/mii_customizer/builds/0.6.0-edit-keyhelp/check_keyhelp.py --write-manifest
python mods/mii_customizer/builds/0.6.0-edit-keyhelp/check_keyhelp.py --neg
python mods/mii_customizer/tools/lua-src/build_check.py
python mods/mii_customizer/tools/lua-src/negative_controls.py
```

- Generator `--strip`: PASS; generated source returns byte-for-byte to the base (19,857 UTF-8 bytes).
- Custom build: PASS; `luac-game -s`, followed by the validated `is_vararg` post-pass at `0x28` (1 -> 2).
- Layout names: PASS; parent part and child panes exist, and parent part references the exact child layout.
- Prototype diff: only `main.p11` (`initialize`) instruction words change; other 17 prototype instruction streams match the original. Candidate has 10,764 bytes, SHA-256 `b266ee0a53e97e1e516b2fb1aab06926e01661f8a2cc0738037ac4d39b26974b`.
- `check_keyhelp.py --neg`: expected `MISMATCH: child layout lacks txt1 pane(s): set_txt_help`, exit 1.
- Baseline `build_check.py`: both `edit` and `special` byte-identical after post-pass (18 and 17 prototypes).
- Baseline `negative_controls.py`: 7/7 controls caught; original source and game chunk unchanged.

## Limits and manual check

The top-corner icon/text, clipping, animation state and persistence are not established by layout parsing or compilation. Check on console: install the staged `mii_customizer_ui` via `CURRENT_INSTALL.md`, open an ordinary Mii edit, verify the Minus glyph and `Advanced Options`, then toggle Favourite and navigate away/back to see whether the hint persists. Roll back by removing this package and restoring the previous edit chunk through `CURRENT_INSTALL.md`.
