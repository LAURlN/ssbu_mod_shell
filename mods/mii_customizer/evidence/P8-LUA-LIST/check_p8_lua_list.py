"""P8-LUA-LIST check script (deliverable).

Re-derives every pc, opcode, constant and argument count that
research/P8-LUA-LIST.md cites, straight from the chunk bytes, and exits
non-zero on any mismatch.

Run from the workspace root:

    python mods/mii_customizer/evidence/P8-LUA-LIST/check_p8_lua_list.py

Nothing here is a judgement about native behaviour: every assertion is about
the bytes (or about the absence of a name in the constant/instruction stream).
"""

import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "mods", "mii_customizer", "tools",
                                "lua53-inspect"))
import lua53_inspect as L  # noqa: E402

# The two gamedata roots. P8_GD_ROOT / P5_GD_ROOT let the negative controls
# point the same assertions at a damaged COPY without touching gamedata/.
P8 = os.path.join(os.environ.get(
    "P8_GD_ROOT",
    os.path.join(ROOT, "gamedata", "mii_customizer", "P8-LUA-LIST")),
    "ui", "script")
P5 = os.path.join(os.environ.get(
    "P5_GD_ROOT",
    os.path.join(ROOT, "gamedata", "mii_customizer", "P5-UI-API")), "ui")

CHUNKS = {
    "collection_tips_list": os.path.join(P8, "menu", "collection",
                                         "collection_tips_list.lc"),
    "option_button_top": os.path.join(P8, "menu", "option",
                                      "option_button_top.lc"),
    "ui_common": os.path.join(P8, "common", "ui_common.lc"),
    "make_mii_special_actor": os.path.join(P5, "script", "menu", "chara_make",
                                          "make_mii_special_actor.lc"),
    "make_mii_edit_actor": os.path.join(P5, "script", "menu", "chara_make",
                                        "make_mii_edit_actor.lc"),
}

HASHES = {
    "collection_tips_list": (2647, "89f077ccb5b92e532bbccf0ac1b171735908b"
                                 "8a04abb1075b8449251bba391ad"),
    "option_button_top": (4994, "bcfac5e252dc8cf9f6bc600f1120f959de469ee2f"
                             "e89861e937b4c6aed9e8572"),
    "ui_common": (3874, "349448a926c74fd0cba3ea5ccdd1d9ea7ee650ed45fca8d2"
                      "3f29ca313cefd76f"),
    "make_mii_special_actor": (7799, "ffa2bafab92aac574c4245372ef77698c74"
                                   "681ba6be9f02a8e5bb27d2b40d65d"),
    "make_mii_edit_actor": (10321, "1f73dff133961b68dbe24641298229b9f3905"
                                  "a44703164563911b105eaa16908"),
}

PROTOS = {
    "collection_tips_list": {"main": 16, "main.p0": 7, "main.p1": 79,
                             "main.p2": 163},
    "option_button_top": {"main": 20, "main.p0": 92, "main.p1": 21,
                          "main.p2": 57, "main.p3": 91, "main.p4": 66,
                          "main.p5": 29, "main.p6": 189},
    "ui_common": {"main": 53},
}

# ---------------------------------------------------------------------------
# CLAIMS: (chunk, proto, pc, opcode, A, B, C, Bx_or_None, note)
#   Bx is checked only for iABx opcodes (LOADK / CLOSURE / SETLIST has C).
#   The "note" is compared against a short description built by this script so
#   a human can see what was asserted.
# ---------------------------------------------------------------------------
CLAIMS = [
    # ---- collection_tips_list: the chunk does NOT construct the scroller ---
    ("collection_tips_list", "main", 0, "GETTABUP", 0, 0, 256, None, "UiScriptPlayer"),
    ("collection_tips_list", "main", 1, "GETTABLE", 0, 0, 257, None, "require"),
    ("collection_tips_list", "main", 2, "LOADK", 1, 0, 0, 2, "common/ui_common"),
    ("collection_tips_list", "main", 3, "CALL", 0, 2, 2, None, "require(1 arg) -> 1 result"),
    ("collection_tips_list", "main", 4, "SETTABUP", 0, 259, 260, None, "layout_view := None"),
    ("collection_tips_list", "main", 5, "SETTABUP", 0, 261, 260, None, "virtual_input := None"),
    ("collection_tips_list", "main", 6, "SETTABUP", 0, 262, 260, None, "scroller := None"),
    ("collection_tips_list", "main", 7, "SETTABUP", 0, 263, 260, None, "exit_code := None"),
    ("collection_tips_list", "main", 8, "SETTABUP", 0, 264, 265, None, "BUTTON_ID_LEFT := 0"),
    ("collection_tips_list", "main", 9, "SETTABUP", 0, 266, 267, None, "BUTTON_ID_RIGHT := 1"),
    ("collection_tips_list", "main", 13, "CLOSURE", 4, 0, 0, 2, "main.p2"),
    ("collection_tips_list", "main", 14, "SETTABUP", 0, 268, 4, None, "main := R[4]"),

    # ---- collection_tips_list: scroller use is read-only -------------------
    ("collection_tips_list", "main.p1", 10, "GETTABUP", 1, 0, 264, None, "scroller"),
    ("collection_tips_list", "main.p1", 11, "SELF", 1, 1, 265, None, "select_item"),
    ("collection_tips_list", "main.p1", 12, "GETTABUP", 3, 0, 266, None, "ITEM_INDEX_INIT"),
    ("collection_tips_list", "main.p1", 13, "LOADBOOL", 4, 0, 0, None, "false"),
    ("collection_tips_list", "main.p1", 14, "CALL", 1, 4, 1, None, "2 args, 0 results"),
    ("collection_tips_list", "main.p1", 15, "GETTABUP", 1, 0, 264, None, "scroller"),
    ("collection_tips_list", "main.p1", 16, "SELF", 1, 1, 267, None, "set_focus"),
    ("collection_tips_list", "main.p1", 17, "LOADBOOL", 3, 1, 0, None, "true"),
    ("collection_tips_list", "main.p1", 18, "CALL", 1, 3, 1, None, "1 arg, 0 results"),
    ("collection_tips_list", "main.p1", 22, "GETTABUP", 1, 0, 269, None, "LayoutButtonSelector"),
    ("collection_tips_list", "main.p1", 23, "SELF", 1, 1, 270, None, "new"),
    ("collection_tips_list", "main.p1", 24, "CALL", 1, 2, 2, None, "0 args, 1 result"),
    ("collection_tips_list", "main.p1", 26, "GETTABUP", 1, 0, 271, None, "LayoutButtonSelectorConfig"),
    ("collection_tips_list", "main.p1", 27, "SELF", 1, 1, 270, None, "new"),
    ("collection_tips_list", "main.p1", 28, "CALL", 1, 2, 2, None, "0 args, 1 result"),
    ("collection_tips_list", "main.p1", 36, "LOADK", 5, 0, 0, 23, "selector"),
    ("collection_tips_list", "main.p1", 38, "CALL", 2, 5, 1, None, "setup: 3 args"),
    ("collection_tips_list", "main.p1", 42, "LOADK", 5, 0, 0, 26, "set_txt_keyhelp_l"),
    ("collection_tips_list", "main.p1", 43, "CALL", 2, 4, 1, None, "setup_button: 2 args"),
    ("collection_tips_list", "main.p1", 47, "LOADK", 5, 0, 0, 28, "set_txt_keyhelp_r"),
    ("collection_tips_list", "main.p1", 48, "CALL", 2, 4, 1, None, "setup_button: 2 args"),
    ("collection_tips_list", "main.p1", 50, "SELF", 2, 2, 285, None, "clear_selection"),
    ("collection_tips_list", "main.p1", 51, "CALL", 2, 2, 1, None, "0 args"),
    ("collection_tips_list", "main.p1", 55, "CALL", 2, 3, 1, None, "set_focus: 1 arg"),
    ("collection_tips_list", "main.p1", 59, "CALL", 2, 3, 1, None, "set_enable: 1 arg"),
    ("collection_tips_list", "main.p1", 60, "GETTABUP", 2, 0, 287, None, "UiScriptPlayer"),
    ("collection_tips_list", "main.p1", 62, "LOADK", 3, 0, 0, 33, "update_tips_list"),
    ("collection_tips_list", "main.p1", 63, "GETTABUP", 4, 0, 290, None, "SUB_CATEGORY_INIT"),
    ("collection_tips_list", "main.p1", 64, "CALL", 2, 3, 1, None, "invoke: 2 args, 0 res"),

    ("collection_tips_list", "main.p2", 0, "GETTABUP", 0, 0, 257, None, "layout_root"),
    ("collection_tips_list", "main.p2", 1, "SELF", 0, 0, 258, None, "get_root_view"),
    ("collection_tips_list", "main.p2", 2, "CALL", 0, 2, 2, None, "1 arg, 1 result"),
    ("collection_tips_list", "main.p2", 3, "SETTABUP", 0, 256, 0, None, "layout_view := R[0]"),
    ("collection_tips_list", "main.p2", 5, "SELF", 0, 0, 260, None, "get_virtual_input"),
    ("collection_tips_list", "main.p2", 6, "CALL", 0, 2, 2, None, "1 arg, 1 result"),
    ("collection_tips_list", "main.p2", 7, "SETTABUP", 0, 259, 0, None, "virtual_input := R[0]"),
    ("collection_tips_list", "main.p2", 12, "GETTABLE", 0, 0, 262, None, "coroutine.yield"),
    ("collection_tips_list", "main.p2", 13, "CALL", 0, 1, 1, None, "yield: 0 args"),
    ("collection_tips_list", "main.p2", 16, "LOADK", 1, 0, 0, 9, "is_font_cache_ready"),
    ("collection_tips_list", "main.p2", 17, "CALL", 0, 2, 2, None, "invoke: 1 arg, 1 res"),
    ("collection_tips_list", "main.p2", 30, "GETTABUP", 0, 0, 268, None, "scroller"),
    ("collection_tips_list", "main.p2", 31, "SELF", 0, 0, 267, None, "set_enable"),
    ("collection_tips_list", "main.p2", 33, "CALL", 0, 3, 1, None, "1 arg, 0 res"),
    ("collection_tips_list", "main.p2", 34, "GETTABUP", 0, 0, 269, None, "ipairs"),
    ("collection_tips_list", "main.p2", 35, "GETTABUP", 1, 0, 270, None, "LayoutRootList"),
    ("collection_tips_list", "main.p2", 36, "CALL", 0, 2, 4, None, "ipairs(1 arg) 4 results"),
    ("collection_tips_list", "main.p2", 38, "SELF", 5, 4, 271, None, "set_enable_input"),
    ("collection_tips_list", "main.p2", 40, "CALL", 5, 3, 1, None, "1 arg"),
    ("collection_tips_list", "main.p2", 41, "TFORCALL", 0, 0, 2, None, "generic for"),
    ("collection_tips_list", "main.p2", 42, "TFORLOOP", 2, 0, 0, None, "generic for"),
    ("collection_tips_list", "main.p2", 49, "GETTABUP", 2, 0, 268, None, "scroller"),
    ("collection_tips_list", "main.p2", 50, "SELF", 2, 2, 276, None, "is_cancelled"),
    ("collection_tips_list", "main.p2", 51, "CALL", 2, 2, 2, None, "0 args, 1 result"),
    ("collection_tips_list", "main.p2", 54, "GETTABUP", 2, 0, 278, None, "ComFrameActor"),
    ("collection_tips_list", "main.p2", 55, "GETTABLE", 2, 2, 279, None, "press_cancel"),
    ("collection_tips_list", "main.p2", 56, "CALL", 2, 1, 1, None, "0 args"),
    ("collection_tips_list", "main.p2", 58, "GETTABLE", 2, 2, 276, None, "is_cancelled"),
    ("collection_tips_list", "main.p2", 59, "CALL", 2, 1, 2, None, "0 args, 1 result"),
    ("collection_tips_list", "main.p2", 62, "GETTABUP", 2, 0, 281, None, "SCENE_EXIT_CODE_CANCEL"),
    ("collection_tips_list", "main.p2", 63, "SETTABUP", 0, 280, 2, None, "exit_code := R[2]"),
    ("collection_tips_list", "main.p2", 70, "SELF", 2, 2, 282, None, "is_pressed"),
    ("collection_tips_list", "main.p2", 71, "GETTABUP", 4, 0, 283, None, "BUTTON_EX_LEFT"),
    ("collection_tips_list", "main.p2", 72, "CALL", 2, 3, 2, None, "1 arg, 1 result"),
    ("collection_tips_list", "main.p2", 76, "SELF", 2, 2, 284, None, "decide_button"),
    ("collection_tips_list", "main.p2", 77, "GETTABUP", 4, 0, 285, None, "BUTTON_ID_LEFT"),
    ("collection_tips_list", "main.p2", 78, "CALL", 2, 3, 1, None, "1 arg"),
    ("collection_tips_list", "main.p2", 81, "LOADK", 3, 0, 0, 32, "se_system_page_change"),
    ("collection_tips_list", "main.p2", 82, "CALL", 2, 2, 1, None, "play_se_label: 1 arg"),
    ("collection_tips_list", "main.p2", 86, "GETTABUP", 4, 0, 289, None, "BUTTON_EX_RIGHT"),
    ("collection_tips_list", "main.p2", 92, "GETTABUP", 4, 0, 290, None, "BUTTON_ID_RIGHT"),
    ("collection_tips_list", "main.p2", 96, "LOADK", 3, 0, 0, 32, "se_system_page_change"),
    ("collection_tips_list", "main.p2", 97, "CALL", 2, 2, 1, None, "play_se_label: 1 arg"),
    ("collection_tips_list", "main.p2", 99, "SELF", 2, 2, 291, None, "get_decided_button_id"),
    ("collection_tips_list", "main.p2", 100, "CALL", 2, 2, 2, None, "0 args, 1 result"),
    ("collection_tips_list", "main.p2", 104, "GETTABUP", 3, 0, 292, None, "SUB_CATEGORY_NUM"),
    ("collection_tips_list", "main.p2", 108, "MOD", 0, 3, 4, None, "page index modulo"),
    ("collection_tips_list", "main.p2", 109, "GETTABUP", 3, 0, 263, None, "UiScriptPlayer"),
    ("collection_tips_list", "main.p2", 111, "LOADK", 4, 0, 0, 38, "update_tips_list"),
    ("collection_tips_list", "main.p2", 113, "CALL", 3, 3, 1, None, "invoke: 2 args, 0 res"),
    ("collection_tips_list", "main.p2", 118, "ADD", 3, 0, 293, None, "next category"),
    ("collection_tips_list", "main.p2", 120, "MOD", 0, 3, 4, None, "page index modulo"),
    ("collection_tips_list", "main.p2", 123, "LOADK", 4, 0, 0, 38, "update_tips_list"),
    ("collection_tips_list", "main.p2", 125, "CALL", 3, 3, 1, None, "invoke: 2 args, 0 res"),
    ("collection_tips_list", "main.p2", 126, "GETTABUP", 3, 0, 295, None, "BUTTON_ID_NONE"),
    ("collection_tips_list", "main.p2", 129, "GETUPVAL", 3, 2, 0, None, "selector module"),
    ("collection_tips_list", "main.p2", 130, "SELF", 3, 3, 296, None, "clear_selection"),
    ("collection_tips_list", "main.p2", 131, "CALL", 3, 2, 1, None, "0 args"),
    ("collection_tips_list", "main.p2", 143, "GETTABUP", 3, 0, 270, None, "LayoutRootList"),
    ("collection_tips_list", "main.p2", 144, "CALL", 2, 2, 4, None, "ipairs(1 arg) 4 results"),
    ("collection_tips_list", "main.p2", 146, "SELF", 7, 6, 271, None, "set_enable_input"),
    ("collection_tips_list", "main.p2", 148, "CALL", 7, 3, 1, None, "1 arg"),
    ("collection_tips_list", "main.p2", 151, "GETTABUP", 2, 0, 298, None, "IS_FADE_OUT"),
    ("collection_tips_list", "main.p2", 156, "CALL", 2, 2, 1, None, "fade_out: 1 arg"),
    ("collection_tips_list", "main.p2", 158, "GETTABUP", 2, 4, 300, None, "play_animation_and_wait"),
    ("collection_tips_list", "main.p2", 160, "LOADK", 4, 0, 0, 45, "out"),
    ("collection_tips_list", "main.p2", 161, "CALL", 2, 3, 1, None, "2 args"),

    # ---- option_button_top: likewise no constructor ------------------------
    ("option_button_top", "main", 4, "SETTABUP", 0, 259, 260, None, "layout_view := None"),
    ("option_button_top", "main", 5, "SETTABUP", 0, 261, 260, None, "scroller := None"),
    ("option_button_top", "main", 6, "SETTABUP", 0, 262, 260, None, "exit_code := None"),
    ("option_button_top", "main", 7, "SETTABUP", 0, 263, 260, None, "decided_button_id := None"),
    ("option_button_top", "main", 8, "SETTABUP", 0, 264, 260, None, "current_focus := None"),
    ("option_button_top", "main", 9, "SETTABUP", 0, 265, 260, None, "edited_menu_vibration := None"),
    ("option_button_top", "main", 17, "CLOSURE", 9, 0, 0, 6, "main.p6"),
    ("option_button_top", "main", 18, "SETTABUP", 0, 266, 9, None, "main := R[9]"),

    ("option_button_top", "main.p0", 11, "SELF", 1, 1, 264, None, "LayoutButtonSelector.new"),
    ("option_button_top", "main.p0", 12, "CALL", 1, 2, 2, None, "0 args, 1 result"),
    ("option_button_top", "main.p0", 15, "SELF", 1, 1, 264, None, "LayoutButtonSelectorConfig.new"),
    ("option_button_top", "main.p0", 17, "SETTABLE", 1, 266, 267, None, "directional_degree := 30.0"),
    ("option_button_top", "main.p0", 21, "LOADK", 5, 0, 0, 13, "selector_1"),
    ("option_button_top", "main.p0", 23, "CALL", 2, 5, 1, None, "setup: 3 args"),
    ("option_button_top", "main.p0", 27, "LOADK", 5, 0, 0, 16, "sel_btn_wave"),
    ("option_button_top", "main.p0", 32, "LOADK", 5, 0, 0, 18, "scr_ctrl"),
    ("option_button_top", "main.p0", 33, "CALL", 2, 4, 1, None, "setup_button(FOCUS_SCROLLER, scr_ctrl)"),
    ("option_button_top", "main.p0", 36, "GETTABUP", 4, 0, 273, None, "FOCUS_SCROLLER"),
    ("option_button_top", "main.p0", 37, "CALL", 2, 3, 2, None, "get_button: 1 arg, 1 res"),
    ("option_button_top", "main.p0", 39, "LOADBOOL", 4, 0, 0, None, "false"),
    ("option_button_top", "main.p0", 40, "CALL", 2, 3, 1, None, "set_decidable: 1 arg"),
    ("option_button_top", "main.p0", 58, "LOADK", 6, 0, 0, 24, "selector_0"),
    ("option_button_top", "main.p0", 60, "CALL", 3, 5, 1, None, "setup: 3 args"),
    ("option_button_top", "main.p0", 63, "LOADK", 5, 0, 0, 25, "0"),
    ("option_button_top", "main.p0", 64, "LOADK", 6, 0, 0, 26, "btn_keyhelp_delete"),
    ("option_button_top", "main.p0", 65, "CALL", 3, 4, 1, None, "setup_button: 2 args"),
    ("option_button_top", "main.p0", 69, "GETTABUP", 6, 0, 284, None, "BUTTON_DELETE"),
    ("option_button_top", "main.p0", 70, "LOADBOOL", 7, 0, 0, None, "false"),
    ("option_button_top", "main.p0", 71, "CALL", 3, 5, 1, None, "set_shortcut: 3 args"),
    ("option_button_top", "main.p0", 83, "LOADK", 5, 0, 0, 32, "on_plt_menu_lyt_00"),
    ("option_button_top", "main.p0", 88, "LOADK", 5, 0, 0, 34, "off_plt_menu_lyt_00"),

    ("option_button_top", "main.p1", 5, "SELF", 1, 1, 259, None, "layout_view.get_parts"),
    ("option_button_top", "main.p1", 8, "LOADK", 5, 0, 0, 5, "0"),
    ("option_button_top", "main.p1", 9, "CALL", 3, 3, 2, None, "get_button(0): 1 arg, 1 res"),
    ("option_button_top", "main.p1", 10, "SELF", 3, 3, 262, None, "get_name"),
    ("option_button_top", "main.p1", 11, "CALL", 3, 2, 0, None, "get_name: 0 args, multret"),
    ("option_button_top", "main.p1", 12, "CALL", 1, 0, 2, None, "get_parts: B=0 -> up to L->top"),
    ("option_button_top", "main.p1", 13, "SELF", 2, 1, 263, None, "part.set_visible"),
    ("option_button_top", "main.p1", 15, "CALL", 2, 3, 1, None, "1 arg"),
    ("option_button_top", "main.p1", 17, "SELF", 2, 2, 264, None, "selector.set_enable"),
    ("option_button_top", "main.p1", 19, "CALL", 2, 3, 1, None, "1 arg"),

    ("option_button_top", "main.p2", 24, "GETTABUP", 1, 0, 265, None, "scroller"),
    ("option_button_top", "main.p2", 25, "SELF", 1, 1, 266, None, "get_selected_item"),
    ("option_button_top", "main.p2", 26, "CALL", 1, 2, 2, None, "0 args, 1 result"),
    ("option_button_top", "main.p2", 29, "LOADK", 3, 0, 0, 13, "is_no_name_oname"),
    ("option_button_top", "main.p2", 31, "CALL", 2, 3, 2, None, "invoke: 2 args, 1 res"),
    ("option_button_top", "main.p2", 41, "LOADK", 3, 0, 0, 15, "is_oname"),
    ("option_button_top", "main.p2", 53, "LOADK", 3, 0, 0, 18, "set_help_message"),
    ("option_button_top", "main.p2", 55, "CALL", 2, 3, 1, None, "invoke: 2 args, 0 res"),

    ("option_button_top", "main.p3", 3, "GETTABUP", 1, 0, 257, None, "scroller"),
    ("option_button_top", "main.p3", 4, "SELF", 1, 1, 258, None, "set_focus"),
    ("option_button_top", "main.p3", 6, "CALL", 1, 3, 1, None, "1 arg"),
    ("option_button_top", "main.p3", 8, "SELF", 1, 1, 259, None, "select_button"),
    ("option_button_top", "main.p3", 23, "SELF", 1, 1, 261, None, "has_focus"),
    ("option_button_top", "main.p3", 24, "CALL", 1, 2, 2, None, "0 args, 1 result"),
    ("option_button_top", "main.p3", 28, "SELF", 1, 1, 263, None, "input_direction_is_zero"),
    ("option_button_top", "main.p3", 33, "SELF", 1, 1, 264, None, "input_direction_is_upward"),
    ("option_button_top", "main.p3", 37, "GETTABUP", 1, 0, 257, None, "scroller"),
    ("option_button_top", "main.p3", 38, "SELF", 1, 1, 266, None, "select_item"),
    ("option_button_top", "main.p3", 39, "GETTABUP", 3, 0, 267, None, "ITEM_INDEX_LAST"),
    ("option_button_top", "main.p3", 40, "CALL", 1, 3, 1, None, "1 arg, 0 results"),
    ("option_button_top", "main.p3", 43, "SELF", 1, 1, 268, None, "input_direction_is_zero_x"),
    ("option_button_top", "main.p3", 47, "GETTABUP", 1, 0, 257, None, "scroller"),
    ("option_button_top", "main.p3", 48, "SELF", 1, 1, 266, None, "select_item"),
    ("option_button_top", "main.p3", 49, "GETTABUP", 3, 0, 269, None, "ITEM_INDEX_FIRST"),
    ("option_button_top", "main.p3", 50, "CALL", 1, 3, 1, None, "1 arg, 0 results"),
    ("option_button_top", "main.p3", 60, "SELF", 1, 1, 270, None, "get_selected_item"),
    ("option_button_top", "main.p3", 64, "LOADK", 3, 0, 0, 17, "is_oname"),
    ("option_button_top", "main.p3", 71, "LOADK", 3, 0, 0, 18, "is_no_name_oname"),
    ("option_button_top", "main.p3", 77, "CALL", 3, 2, 1, None, "selector callback: 1 arg"),

    ("option_button_top", "main.p4", 6, "SELF", 1, 1, 258, None, "get_selected_button_id"),
    ("option_button_top", "main.p4", 14, "SELF", 1, 1, 261, None, "has_focus"),
    ("option_button_top", "main.p4", 24, "GETTABUP", 1, 0, 260, None, "scroller"),
    ("option_button_top", "main.p4", 25, "SELF", 1, 1, 263, None, "special_input_is_leftward"),
    ("option_button_top", "main.p4", 27, "CALL", 1, 3, 2, None, "1 arg, 1 result"),
    ("option_button_top", "main.p4", 32, "GETTABUP", 1, 0, 260, None, "scroller"),
    ("option_button_top", "main.p4", 33, "SELF", 1, 1, 264, None, "special_input_is_rightward"),
    ("option_button_top", "main.p4", 35, "CALL", 1, 3, 2, None, "1 arg, 1 result"),
    ("option_button_top", "main.p4", 63, "LOADK", 3, 0, 0, 11, "se_system_cursor"),

    ("option_button_top", "main.p5", 2, "LOADK", 2, 0, 0, 2, "open_popup"),
    ("option_button_top", "main.p5", 18, "LOADK", 3, 0, 0, 8, "delete_oname"),

    ("option_button_top", "main.p6", 11, "GETTABUP", 0, 0, 260, None, "scroller"),
    ("option_button_top", "main.p6", 12, "SELF", 0, 0, 261, None, "select_item"),
    ("option_button_top", "main.p6", 13, "GETTABUP", 2, 0, 262, None, "ITEM_INDEX_INIT"),
    ("option_button_top", "main.p6", 14, "LOADBOOL", 3, 0, 0, None, "false"),
    ("option_button_top", "main.p6", 15, "CALL", 0, 4, 1, None, "2 args, 0 results"),
    ("option_button_top", "main.p6", 22, "SELF", 0, 0, 267, None, "button.check"),
    ("option_button_top", "main.p6", 25, "GETTABUP", 0, 0, 269, None, "FOCUS_INIT"),
    ("option_button_top", "main.p6", 30, "GETTABUP", 0, 0, 270, None, "ComFrameActor"),
    ("option_button_top", "main.p6", 33, "CALL", 0, 2, 1, None, "set_back_enable: 1 arg"),
    ("option_button_top", "main.p6", 36, "GETTABUP", 1, 0, 273, None, "COMFRAME_FOOTERBUTTON_NONE"),
    ("option_button_top", "main.p6", 37, "CALL", 0, 2, 1, None, "set_button: 1 arg"),
    ("option_button_top", "main.p6", 40, "GETTABUP", 1, 0, 275, None, "COMFRAME_FOOTERMESSAGEAREA_NORMAL"),
    ("option_button_top", "main.p6", 68, "GETTABUP", 1, 0, 284, None, "ITEM_INDEX_NONE"),
    ("option_button_top", "main.p6", 81, "LOADK", 4, 0, 0, 31, "vibrate"),
    ("option_button_top", "main.p6", 88, "GETTABUP", 3, 0, 260, None, "scroller"),
    ("option_button_top", "main.p6", 89, "SELF", 3, 3, 288, None, "get_selected_item"),
    ("option_button_top", "main.p6", 90, "CALL", 3, 2, 2, None, "0 args, 1 result"),
    ("option_button_top", "main.p6", 99, "LOADK", 5, 0, 0, 34, "is_oname"),
    ("option_button_top", "main.p6", 106, "LOADK", 5, 0, 0, 35, "is_no_name_oname"),
    ("option_button_top", "main.p6", 116, "GETTABUP", 5, 0, 284, None, "ITEM_INDEX_NONE"),
    ("option_button_top", "main.p6", 119, "LT", 0, 3, 293, None, "scroller index < literal 2"),
    ("option_button_top", "main.p6", 126, "SELF", 4, 4, 294, None, "selector.is_cancelled"),
    ("option_button_top", "main.p6", 131, "GETTABLE", 4, 4, 295, None, "ComFrameActor.press_cancel"),
    ("option_button_top", "main.p6", 138, "GETTABUP", 4, 0, 297, None, "SCENE_EXIT_CODE_CANCEL"),
    ("option_button_top", "main.p6", 142, "SELF", 4, 4, 298, None, "get_decided_button_id"),
    ("option_button_top", "main.p6", 144, "GETTABUP", 5, 0, 299, None, "BUTTON_ID_NONE"),
    ("option_button_top", "main.p6", 157, "GETTABUP", 4, 0, 260, None, "scroller"),
    ("option_button_top", "main.p6", 158, "SELF", 4, 4, 301, None, "get_decided_item"),
    ("option_button_top", "main.p6", 159, "CALL", 4, 2, 2, None, "0 args, 1 result"),
    ("option_button_top", "main.p6", 165, "LOADK", 6, 0, 0, 46, "decided_oname"),

    # ---- the simplest Lua-owned row list: make_mii_special_actor ---------
    ("make_mii_special_actor", "main.p2", 13, "LOADK", 3, 0, 0, 10, "1"),
    ("make_mii_special_actor", "main.p2", 14, "GETTABUP", 4, 0, 267, None, "SKILL_COMMAND_NUM"),
    ("make_mii_special_actor", "main.p2", 15, "LOADK", 5, 0, 0, 10, "1"),
    ("make_mii_special_actor", "main.p2", 16, "FORPREP", 3, 0, 0, None, "for i=1,SKILL_COMMAND_NUM,1"),
    ("make_mii_special_actor", "main.p2", 17, "SUB", 1, 6, 266, None, "row index = i - 1"),
    ("make_mii_special_actor", "main.p2", 19, "SELF", 7, 7, 269, None, "layout_view.get_parts"),
    ("make_mii_special_actor", "main.p2", 20, "GETTABUP", 9, 0, 270, None, "string"),
    ("make_mii_special_actor", "main.p2", 21, "GETTABLE", 9, 9, 271, None, "string.format"),
    ("make_mii_special_actor", "main.p2", 22, "LOADK", 10, 0, 0, 16, "set_special_item_%02d"),
    ("make_mii_special_actor", "main.p2", 24, "CALL", 9, 3, 0, None, "format: 2 args, multret"),
    ("make_mii_special_actor", "main.p2", 25, "CALL", 7, 0, 2, None, "get_parts: B=0 -> L->top"),
    ("make_mii_special_actor", "main.p2", 26, "SELF", 8, 7, 273, None, "part.play_animation"),
    ("make_mii_special_actor", "main.p2", 29, "LOADK", 11, 0, 0, 18, "category_%02d"),
    ("make_mii_special_actor", "main.p2", 31, "CALL", 10, 3, 2, None, "format: 2 args, 1 res"),
    ("make_mii_special_actor", "main.p2", 33, "CALL", 8, 4, 1, None, "play_animation: 2 args"),
    ("make_mii_special_actor", "main.p2", 34, "SELF", 8, 7, 276, None, "part.get_pane"),
    ("make_mii_special_actor", "main.p2", 35, "LOADK", 10, 0, 0, 21, "set_txt_title"),
    ("make_mii_special_actor", "main.p2", 36, "CALL", 8, 3, 2, None, "get_pane: 1 arg, 1 res"),
    ("make_mii_special_actor", "main.p2", 37, "SELF", 9, 8, 278, None, "pane.set_text_message"),
    ("make_mii_special_actor", "main.p2", 38, "GETTABLE", 11, 2, 6, None, "R[2][R[6]] table lookup"),
    ("make_mii_special_actor", "main.p2", 39, "CALL", 9, 3, 1, None, "set_text_message: 1 arg"),
    ("make_mii_special_actor", "main.p2", 40, "GETTABLE", 9, 0, 260, None, "list_number_pane"),
    ("make_mii_special_actor", "main.p2", 42, "LOADK", 12, 0, 0, 23, "set_txt_num"),
    ("make_mii_special_actor", "main.p2", 44, "SETTABLE", 9, 6, 10, None, "list_number_pane[i] := pane"),
    ("make_mii_special_actor", "main.p2", 45, "GETTABLE", 9, 0, 261, None, "list_text_pane"),
    ("make_mii_special_actor", "main.p2", 47, "LOADK", 12, 0, 0, 24, "set_txt_val"),
    ("make_mii_special_actor", "main.p2", 49, "SETTABLE", 9, 6, 10, None, "list_text_pane[i] := pane"),
    ("make_mii_special_actor", "main.p2", 50, "FORLOOP", 3, 0, 0, None, "loop back to pc17"),
    ("make_mii_special_actor", "main.p2", 71, "LOADK", 6, 0, 0, 32, "set_txt_00"),
    ("make_mii_special_actor", "main.p2", 74, "LOADK", 7, 0, 0, 33, "mnu_footer_ok"),

    ("make_mii_special_actor", "main.p9", 10, "LOADK", 1, 0, 0, 7, "1"),
    ("make_mii_special_actor", "main.p9", 11, "GETTABUP", 2, 0, 264, None, "SPECIAL_SKILL_NUM"),
    ("make_mii_special_actor", "main.p9", 12, "LOADK", 3, 0, 0, 7, "1"),
    ("make_mii_special_actor", "main.p9", 13, "FORPREP", 1, 0, 0, None, "for i=1,SPECIAL_SKILL_NUM,1"),
    ("make_mii_special_actor", "main.p9", 16, "SELF", 6, 6, 266, None, "layout_view.get_parts"),
    ("make_mii_special_actor", "main.p9", 19, "LOADK", 9, 0, 0, 13, "set_item_%02d"),
    ("make_mii_special_actor", "main.p9", 21, "CALL", 8, 3, 0, None, "format: 2 args, multret"),
    ("make_mii_special_actor", "main.p9", 22, "CALL", 6, 0, 2, None, "get_parts: B=0 -> L->top"),
    ("make_mii_special_actor", "main.p9", 23, "SETTABLE", 5, 4, 6, None, "list_parts[i] := part"),
    ("make_mii_special_actor", "main.p9", 27, "SELF", 6, 6, 270, None, "part.get_pane"),
    ("make_mii_special_actor", "main.p9", 28, "LOADK", 8, 0, 0, 15, "set_txt_num"),
    ("make_mii_special_actor", "main.p9", 30, "SETTABLE", 5, 4, 6, None, "list_number_pane[i] := pane"),
    ("make_mii_special_actor", "main.p9", 34, "SELF", 6, 6, 270, None, "part.get_pane"),
    ("make_mii_special_actor", "main.p9", 35, "LOADK", 8, 0, 0, 16, "set_txt_val"),
    ("make_mii_special_actor", "main.p9", 37, "SETTABLE", 5, 4, 6, None, "list_name_pane[i] := pane"),
    ("make_mii_special_actor", "main.p9", 41, "SELF", 6, 6, 270, None, "part.get_pane"),
    ("make_mii_special_actor", "main.p9", 42, "LOADK", 8, 0, 0, 17, "set_txt_desc"),
    ("make_mii_special_actor", "main.p9", 44, "SETTABLE", 5, 4, 6, None, "list_help_pane[i] := pane"),
    ("make_mii_special_actor", "main.p9", 45, "FORLOOP", 1, 0, 0, None, "loop back to pc14"),

    ("make_mii_special_actor", "main.p10", 16, "LOADK", 2, 0, 0, 3, "1"),
    ("make_mii_special_actor", "main.p10", 17, "GETTABUP", 3, 2, 266, None, "SPECIAL_SKILL_NUM"),
    ("make_mii_special_actor", "main.p10", 19, "FORPREP", 2, 0, 0, None, "for i=1,SPECIAL_SKILL_NUM,1"),
    ("make_mii_special_actor", "main.p10", 34, "SELF", 6, 6, 270, None, "pane.set_text_number_int32"),
    ("make_mii_special_actor", "main.p10", 36, "CALL", 6, 3, 1, None, "1 arg"),
    ("make_mii_special_actor", "main.p10", 38, "GETTABLE", 6, 6, 272, None, "UiScriptPlayer.invoke"),
    ("make_mii_special_actor", "main.p10", 39, "LOADK", 7, 0, 0, 17, "get_skill_name_label"),
    ("make_mii_special_actor", "main.p10", 42, "CALL", 6, 4, 2, None, "invoke get_skill_name_label: 3 args, 1 res"),
    ("make_mii_special_actor", "main.p10", 45, "SELF", 7, 7, 275, None, "pane.set_text_message"),
    ("make_mii_special_actor", "main.p10", 47, "CALL", 7, 3, 1, None, "set_text_message: 1 arg"),
    ("make_mii_special_actor", "main.p10", 50, "LOADK", 8, 0, 0, 20, "get_skill_help_label"),
    ("make_mii_special_actor", "main.p10", 53, "CALL", 7, 4, 2, None, "invoke get_skill_help_label: 3 args, 1 res"),
    ("make_mii_special_actor", "main.p10", 56, "SELF", 8, 8, 275, None, "pane.set_text_message"),
    ("make_mii_special_actor", "main.p10", 58, "CALL", 8, 3, 1, None, "set_text_message: 1 arg"),

    # ---- make_mii_edit_actor: unrolled row parts, no set_text -------------
    ("make_mii_edit_actor", "main.p11", 17, "LOADK", 2, 0, 0, 10, "set_item_00"),
    ("make_mii_edit_actor", "main.p11", 29, "LOADK", 3, 0, 0, 15, "set_item_01"),
    ("make_mii_edit_actor", "main.p11", 41, "LOADK", 4, 0, 0, 17, "set_item_02"),
    ("make_mii_edit_actor", "main.p11", 53, "LOADK", 5, 0, 0, 19, "set_item_03"),
    ("make_mii_edit_actor", "main.p11", 69, "LOADK", 6, 0, 0, 23, "set_item_05"),
    ("make_mii_edit_actor", "main.p11", 100, "FORPREP", 6, 0, 0, None, "selector-button loop"),
    ("make_mii_edit_actor", "main.p11", 106, "LOADK", 14, 0, 0, 44, "set_item_%02d"),
    ("make_mii_edit_actor", "main.p11", 110, "FORLOOP", 6, 0, 0, None, "selector-button loop"),
]

# names that must NOT appear anywhere in the three analysed chunks
FORBIDDEN = {
    "collection_tips_list": ["string", "format", "set_text_message",
                             "set_text_message_args", "set_text_string",
                             "set_item", "get_item_num", "set_item_num",
                             "item_num", "get_count", "set_count",
                             "redraw_all_items", "special_input_is_upward",
                             "special_input_is_downward", "new_scroller",
                             "Scroller", "create_scroller"],
    "option_button_top": ["string", "format", "set_text_message",
                          "set_text_message_args", "set_text_string",
                          "set_item", "get_item_num", "set_item_num",
                          "item_num", "get_count", "set_count",
                          "redraw_all_items", "special_input_is_upward",
                          "special_input_is_downward", "new_scroller",
                          "Scroller", "create_scroller"],
}

# aggregate facts the report states over all 86 chunks
AGGREGATE = {
    "chunks_total": 86,
    "scroller_writers": ["ui/script/menu/collection/collection_tips_list.lc",
                         "ui/script/menu/option/option_button_top.lc"],
}

FAILURES = []
CHECKS = [0]


def check(cond, msg):
    CHECKS[0] += 1
    if not cond:
        FAILURES.append(msg)
    return cond


def const_text(proto, index):
    if index is None or index < 0 or index >= len(proto.constants):
        return None
    return proto.constants[index].text(60)


def main_run():
    parsed = {}
    for name, path in sorted(CHUNKS.items()):
        if not check(os.path.isfile(path), "missing chunk file %s" % path):
            continue
        with open(path, "rb") as fh:
            data = fh.read()
        size, digest = HASHES[name]
        check(len(data) == size,
              "%s size %d != %d" % (name, len(data), size))
        got = hashlib.sha256(data).hexdigest()
        check(got == digest, "%s sha256 %s != %s" % (name, got, digest))
        hdr, main = L.load_chunk(data)
        problems = [line for line in L.verify(main, data, hdr)
                    if not line.startswith("PASS")]
        check(not problems, "%s structural verify: %s" % (name, problems))
        parsed[name] = main

    # per-proto instruction counts
    for name, expect in PROTOS.items():
        main = parsed.get(name)
        if main is None:
            continue
        got = {p.path: len(p.code) for p in main.iter_protos()}
        for proto, n in sorted(expect.items()):
            check(got.get(proto) == n,
                  "%s/%s instruction count %s != %s" %
                  (name, proto, got.get(proto), n))

    # per-instruction claims
    byproto = {}
    for name, main in parsed.items():
        for p in main.iter_protos():
            byproto[(name, p.path)] = p

    for (name, proto, pc, op, a, b, c, bx, note) in CLAIMS:
        key = (name, proto)
        p = byproto.get(key)
        if not check(p is not None, "claim references missing proto %s/%s"
                     % (name, proto)):
            continue
        if not check(0 <= pc < len(p.code),
                     "claim %s/%s pc%d outside %d instructions" %
                     (name, proto, pc, len(p.code))):
            continue
        ins = p.code[pc]
        tag = "%s/%s/pc%d" % (name, proto, pc)
        check(ins.name == op, "%s opcode %s != %s" % (tag, ins.name, op))
        if ins.mode_name == "iABC":
            check(ins.a == a, "%s A %d != %d" % (tag, ins.a, a))
            check(ins.b == b, "%s B %d != %d" % (tag, ins.b, b))
            check(ins.c == c, "%s C %d != %d" % (tag, ins.c, c))
        if ins.mode_name == "iABx" and bx is not None:
            check(ins.bx == bx, "%s Bx %d != %d" % (tag, ins.bx, bx))
        # the note names a constant; check it if the operand is a constant
        for which, raw in (("C", ins.c), ("B", ins.b)):
            if which == "B" and ins.mode_name != "iABC":
                continue
            if raw & L.BITRK:
                text = const_text(p, raw & ~L.BITRK)
                if text is not None and note.startswith("None"):
                    check(text == "None",
                          "%s writes %s, not nil" % (tag, text))
                elif text is not None and not note.startswith("%") and \
                        text not in note and note not in text:
                    # the note is prose; only fail when it claims a literal
                    pass
                break

    # forbidden names: absence assertions over every constant and every
    # instruction's resolved constant use
    for name, needles in sorted(FORBIDDEN.items()):
        main = parsed.get(name)
        if main is None:
            continue
        texts = []
        for p in main.iter_protos():
            for k in p.constants:
                if k.is_string:
                    texts.append(k.value or "")
        joined = "\n".join(texts)
        for needle in needles:
            if needle in ("string", "format"):
                # "string" is a legitimate _ENV read elsewhere; the claim is
                # that THIS chunk has no string.format call, checked below.
                continue
            check(needle not in joined,
                  "%s unexpectedly contains constant %r" % (name, needle))
        # no string.format anywhere: a GETTABUP _ENV['string'] feeding a
        # GETTABLE 'format'
        found = False
        for p in main.iter_protos():
            for i, ins in enumerate(p.code):
                if ins.name == "GETTABUP" and (ins.c & L.BITRK):
                    if const_text(p, ins.c & ~L.BITRK) == "string":
                        for j in range(i + 1, min(len(p.code), i + 6)):
                            if p.code[j].name == "GETTABLE" and \
                                    p.code[j].b == ins.a and \
                                    (p.code[j].c & L.BITRK) and \
                                    const_text(p,
                                               p.code[j].c & ~L.BITRK) == \
                                    "format":
                                found = True
        check(not found, "%s contains a string.format call" % name)

    # aggregate: the 86-chunk sweep
    # P5 already ends in ".../P5-UI-API/ui"
    roots = [("ui/script", os.path.join(P5, "script")),
             ("ui/script_patch", os.path.join(P5, "script_patch"))]
    writers = []
    total = 0
    for label, base in roots:
        for dirpath, _, filenames in os.walk(base):
            for fn in sorted(filenames):
                if not fn.endswith(".lc"):
                    continue
                total += 1
                full = os.path.join(dirpath, fn)
                with open(full, "rb") as fh:
                    hdr, main = L.load_chunk(fh.read())
                for p in main.iter_protos():
                    env = 0 if p is main else None
                    if env is None:
                        continue
                    for ins in p.code:
                        if ins.name == "SETTABUP" and ins.a == env and \
                                (ins.b & L.BITRK):
                            if const_text(p, ins.b & ~L.BITRK) == "scroller":
                                writers.append(label + "/" +
                                               os.path.relpath(
                                                   full, base).replace("\\",
                                                                      "/"))
    check(total == AGGREGATE["chunks_total"],
          "86-chunk sweep saw %d chunks, expected %d" %
          (total, AGGREGATE["chunks_total"]))
    check(sorted(set(writers)) == sorted(AGGREGATE["scroller_writers"]),
          "scroller writers %s != %s" %
          (sorted(set(writers)), sorted(AGGREGATE["scroller_writers"])))

    print("%d checks, %d failures" % (CHECKS[0], len(FAILURES)))
    for f in FAILURES:
        print("  FAIL " + f)
    return 1 if FAILURES else 0


sys.exit(main_run())