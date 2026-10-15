#!/usr/bin/env python3
"""Re-derive every claim cited in research/P6-HAT-UI.md from the four chunks.

Exit 0 only if every check passes. Nothing is written.

Usage (from the workspace root):
    python mods/mii_customizer/evidence/P6-HAT-UI/check_p6_hat_ui.py

Optional: pass an alternative extraction root as argv[1]; it must contain
``ui/script/menu/chara_make/<chunk>.lc`` for the four chunks.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.normpath(os.path.join(HERE, "..", ".."))       # mods/mii_customizer
ROOT = os.path.normpath(os.path.join(MOD, "..", ".."))        # workspace root
sys.path.insert(0, os.path.join(MOD, "tools", "lua53-inspect"))

import lua53_inspect as L  # noqa: E402

H = "make_mii_hat_actor"
L_ = "make_mii_hat_body_layout"
U = "make_mii_utility"
B = "make_mii_body_actor"

# size, sha256 -- as reported by tools/arc-extract and recorded in the report
EXPECTED_FILES = {
    H: (1042, "bf3648f5de367907e30cd1086a3cef957ef5d5c7447ef5aac4f144116d875e9b"),
    L_: (5936, "87a3706af2bbedb2059efb10d759acb72fd984c5b3334ef5187c976d10bac199"),
    U: (3263, "ff62bea184d129d9bd94137a92ba910314f3e9ef61bb2b663c2aa698d7109f25"),
    B: (1046, "b2e262ed584f8c108a77502bebb200afb38c969f123405690af0d9d695cf5518"),
}

# (protos, instructions, constants) per chunk, from `summary`
EXPECTED_TOTALS = {
    H: (6, 70, 33),
    L_: (16, 568, 216),
    U: (5, 134, 94),
    B: (6, 70, 33),
}

# proto path -> (code count, params, maxstack, env-upvalue indices)
EXPECTED_PROTOS = {
    H: {
        "main": (16, 0, 2, [0]),
        "main.p0": (28, 0, 2, [0]),
        "main.p1": (11, 0, 7, [1]),
        "main.p2": (5, 1, 4, []),
        "main.p3": (5, 1, 4, []),
        "main.p4": (5, 0, 2, []),
    },
    L_: {
        "main": (53, 0, 13, [0]),
        "main.p0": (2, 2, 2, []),
        "main.p1": (3, 1, 2, []),
        "main.p2": (23, 2, 5, []),
        "main.p3": (12, 2, 5, [0]),
        "main.p4": (12, 1, 5, []),
        "main.p5": (113, 6, 14, [0]),
        "main.p6": (22, 6, 15, [1]),
        "main.p7": (22, 6, 15, [1]),
        "main.p8": (29, 1, 5, []),
        # p9's single upvalue is (instack=1, idx=9) = the parent's local R[9],
        # which holds the ui_common module, not _ENV
        "main.p9": (12, 1, 4, []),
        "main.p10": (1, 1, 2, []),
        "main.p11": (142, 1, 7, [0]),
        "main.p12": (35, 1, 4, [0]),
        "main.p13": (73, 1, 6, [0]),
        "main.p14": (14, 1, 3, []),
    },
    U: {
        "main": (55, 0, 5, [0]),
        "main.p0": (24, 3, 11, [0]),
        "main.p1": (24, 3, 11, [0]),
        "main.p2": (24, 3, 11, [0]),
        "main.p3": (7, 2, 8, [0]),
    },
    B: {
        "main": (16, 0, 2, [0]),
        "main.p0": (28, 0, 2, [0]),
        "main.p1": (11, 0, 7, [1]),
        "main.p2": (5, 1, 4, []),
        "main.p3": (5, 1, 4, []),
        "main.p4": (5, 0, 2, []),
    },
}

# (chunk, proto, pc, opcode, {field: value}, [(field, const index, value)])
# ``field`` is A / B / C / Bx / sBx. ``const index`` is the resolved constant
# index when the field has BITRK set, or the LOADK Bx for LOADK/CLOSURE.
CLAIMS = [
    # -- 1. structure: the two actor chunks are identical except the title ----
    (H, "main", 0, "GETTABUP", {"A": 0, "B": 0, "C": 256}, [("C", 0, "UiScriptPlayer")]),
    (H, "main", 1, "GETTABLE", {"A": 0, "B": 0, "C": 257}, [("C", 1, "require")]),
    (H, "main", 2, "LOADK", {"A": 1, "Bx": 2}, [("Bx", 2, "menu/chara_make/make_mii_hat_body_layout")]),
    (H, "main", 3, "CALL", {"A": 0, "B": 2, "C": 2}, []),
    (H, "main", 4, "SETTABUP", {"A": 0, "B": 259, "C": 260},
     [("B", 3, "is_finish"), ("C", 4, False)]),
    (H, "main", 6, "SETTABUP", {"A": 0, "B": 261, "C": 1}, [("B", 5, "main")]),
    (H, "main", 8, "SETTABUP", {"A": 0, "B": 262, "C": 1}, [("B", 6, "initialize")]),
    (H, "main", 10, "SETTABUP", {"A": 0, "B": 263, "C": 1}, [("B", 7, "set_select_id")]),
    (H, "main", 12, "SETTABUP", {"A": 0, "B": 264, "C": 1}, [("B", 8, "set_sort_id")]),
    (H, "main", 14, "SETTABUP", {"A": 0, "B": 265, "C": 1}, [("B", 9, "get_decided_id")]),
    (B, "main", 2, "LOADK", {"A": 1, "Bx": 2}, [("Bx", 2, "menu/chara_make/make_mii_hat_body_layout")]),
    (B, "main", 3, "CALL", {"A": 0, "B": 2, "C": 2}, []),
    # the only difference between the two actor chunks' title message
    (H, "main.p0", 3, "LOADK", {"A": 1, "Bx": 4}, [("Bx", 4, "mnu_mmiif_setup_hat_title")]),
    (B, "main.p0", 3, "LOADK", {"A": 1, "Bx": 4}, [("Bx", 4, "mnu_mmiif_setup_outfit_title")]),
    (H, "main.p1", 1, "SELF", {"A": 0, "B": 0, "C": 256}, [("C", 0, "initialize_hat")]),
    (B, "main.p1", 1, "SELF", {"A": 0, "B": 0, "C": 256}, [("C", 0, "initialize_body")]),
    (H, "main.p1", 2, "GETTABUP", {"A": 2, "B": 1, "C": 257}, [("C", 1, "LayoutRootList")]),
    (H, "main.p1", 3, "GETTABLE", {"A": 2, "B": 2, "C": 258}, [("C", 2, "make_mii_hat_body")]),
    (H, "main.p1", 4, "GETTABUP", {"A": 3, "B": 1, "C": 257}, [("C", 1, "LayoutRootList")]),
    (H, "main.p1", 5, "GETTABLE", {"A": 3, "B": 3, "C": 259}, [("C", 3, "com_sort_window")]),
    (H, "main.p1", 6, "GETTABUP", {"A": 4, "B": 1, "C": 260}, [("C", 4, "scroller")]),
    (H, "main.p1", 7, "GETTABUP", {"A": 5, "B": 1, "C": 261}, [("C", 5, "sub_list_window")]),
    (H, "main.p1", 8, "GETTABUP", {"A": 6, "B": 1, "C": 262}, [("C", 6, "sub_list_window_facade")]),
    (H, "main.p1", 9, "CALL", {"A": 0, "B": 7, "C": 1}, []),
    (H, "main.p2", 3, "CALL", {"A": 1, "B": 3, "C": 1}, []),
    (H, "main.p3", 3, "CALL", {"A": 1, "B": 3, "C": 1}, []),
    (H, "main.p4", 2, "TAILCALL", {"A": 0, "B": 2, "C": 0}, []),

    # -- 2. hat_body_layout exports (a table, not _ENV) ---------------------
    (L_, "main", 0, "NEWTABLE", {"A": 0, "B": 0, "C": 0}, []),
    (L_, "main", 1, "NEWTABLE", {"A": 1, "B": 0, "C": 0}, []),
    (L_, "main", 10, "LOADK", {"A": 9, "Bx": 8}, [("Bx", 8, "common/state_function")]),
    (L_, "main", 11, "CALL", {"A": 8, "B": 2, "C": 2}, []),
    (L_, "main", 14, "LOADK", {"A": 10, "Bx": 9}, [("Bx", 9, "common/ui_common")]),
    (L_, "main", 15, "CALL", {"A": 9, "B": 2, "C": 2}, []),
    (L_, "main", 17, "SETTABLE", {"A": 1, "B": 266, "C": 10}, [("B", 10, "set_select_id")]),
    (L_, "main", 19, "SETTABLE", {"A": 1, "B": 267, "C": 10}, [("B", 11, "get_decided_id")]),
    (L_, "main", 21, "SETTABLE", {"A": 1, "B": 268, "C": 10}, [("B", 12, "set_enable_input")]),
    (L_, "main", 23, "SETTABLE", {"A": 1, "B": 269, "C": 10}, [("B", 13, "set_sort_id")]),
    (L_, "main", 25, "SETTABLE", {"A": 1, "B": 270, "C": 10}, [("B", 14, "update_sort_text")]),
    (L_, "main", 27, "SETTABLE", {"A": 1, "B": 271, "C": 10}, [("B", 15, "initialize")]),
    (L_, "main", 29, "SETTABLE", {"A": 1, "B": 272, "C": 10}, [("B", 16, "initialize_body")]),
    (L_, "main", 31, "SETTABLE", {"A": 1, "B": 273, "C": 10}, [("B", 17, "initialize_hat")]),
    (L_, "main", 33, "SETTABLE", {"A": 1, "B": 274, "C": 10}, [("B", 18, "update_in")]),
    (L_, "main", 35, "SETTABLE", {"A": 1, "B": 275, "C": 10}, [("B", 19, "update_out")]),
    (L_, "main", 37, "SETTABLE", {"A": 1, "B": 276, "C": 10}, [("B", 20, "update_idle")]),
    (L_, "main", 39, "SETTABLE", {"A": 1, "B": 277, "C": 10}, [("B", 21, "update_main")]),
    (L_, "main", 41, "SETTABLE", {"A": 1, "B": 278, "C": 10}, [("B", 22, "update_sub_list_window_in")]),
    (L_, "main", 43, "SETTABLE", {"A": 1, "B": 279, "C": 10}, [("B", 23, "update_sub_list_window")]),
    (L_, "main", 45, "SETTABLE", {"A": 1, "B": 280, "C": 10}, [("B", 24, "update")]),
    (L_, "main", 46, "GETTABUP", {"A": 10, "B": 0, "C": 281}, [("C", 25, "setmetatable")]),
    (L_, "main", 49, "SETTABLE", {"A": 12, "B": 282, "C": 1}, [("B", 26, "__index")]),
    (L_, "main", 50, "TAILCALL", {"A": 10, "B": 3, "C": 0}, []),

    # -- 2b. utility writes 32 globals and exports 4 functions --------------
    (U, "main", 2, "SETTABUP", {"A": 0, "B": 256, "C": 257},
     [("B", 0, "MII_FIGHTER_DEFAULT_ROTATE"), ("C", 1, 60.0)]),
    (U, "main", 5, "SETTABUP", {"A": 0, "B": 262, "C": 263},
     [("B", 6, "F_CAMERA_DEFAULT_POSITION_Z"), ("C", 7, 136.6999969482422)]),
    (U, "main", 41, "SETTABLE", {"A": 1, "B": 303, "C": 2}, [("B", 47, "set_defines_camera")]),
    (U, "main", 43, "SETTABLE", {"A": 1, "B": 304, "C": 2}, [("B", 48, "set_right_side_0_fighter_camera")]),
    (U, "main", 45, "SETTABLE", {"A": 1, "B": 305, "C": 2}, [("B", 49, "set_right_side_1_fighter_camera")]),
    (U, "main", 47, "SETTABLE", {"A": 1, "B": 306, "C": 2}, [("B", 50, "set_head_position_fighter_camera")]),
    (U, "main", 52, "TAILCALL", {"A": 2, "B": 3, "C": 0}, []),

    # -- 8. Mii class read (utility only) -----------------------------------
    (U, "main.p0", 1, "GETTABUP", {"A": 6, "B": 0, "C": 256}, [("C", 0, "MII_TYPE_SWORDSMAN")]),
    (U, "main.p0", 2, "EQ", {"A": 0, "B": 2, "C": 6}, []),
    (U, "main.p0", 8, "GETTABUP", {"A": 6, "B": 0, "C": 260}, [("C", 4, "MII_TYPE_GUNNER")]),
    (U, "main.p0", 9, "EQ", {"A": 0, "B": 2, "C": 6}, []),
    (U, "main.p0", 22, "CALL", {"A": 6, "B": 5, "C": 1}, []),
    (U, "main.p3", 5, "CALL", {"A": 2, "B": 6, "C": 1}, []),

    # -- 3/6. bridge calls: name, argument count, provenance ---------------
    (L_, "main.p3", 4, "GETTABLE", {"A": 2, "B": 2, "C": 259}, [("C", 3, "invoke")]),
    (L_, "main.p3", 5, "LOADK", {"A": 3, "Bx": 4}, [("Bx", 4, "sort_id_list")]),
    (L_, "main.p3", 7, "CALL", {"A": 2, "B": 3, "C": 1}, []),
    (L_, "main.p5", 104, "SETTABLE", {"A": 0, "B": 303, "C": 295},
     [("B", 47, "sort_id"), ("C", 39, 0)]),
    (L_, "main.p5", 107, "GETTABUP", {"A": 8, "B": 0, "C": 305}, [("C", 49, "UiScriptPlayer")]),
    (L_, "main.p5", 108, "GETTABLE", {"A": 8, "B": 8, "C": 306}, [("C", 50, "invoke")]),
    (L_, "main.p5", 109, "LOADK", {"A": 9, "Bx": 51}, [("Bx", 51, "sort_id_list")]),
    (L_, "main.p5", 111, "CALL", {"A": 8, "B": 3, "C": 1}, []),
    (L_, "main.p11", 56, "GETTABUP", {"A": 2, "B": 0, "C": 273}, [("C", 17, "UiScriptPlayer")]),
    (L_, "main.p11", 57, "GETTABLE", {"A": 2, "B": 2, "C": 274}, [("C", 18, "invoke")]),
    (L_, "main.p11", 58, "LOADK", {"A": 3, "Bx": 19}, [("Bx", 19, "get_top_index")]),
    (L_, "main.p11", 59, "CALL", {"A": 2, "B": 2, "C": 2}, []),
    (L_, "main.p12", 7, "GETTABUP", {"A": 1, "B": 0, "C": 260}, [("C", 4, "UiScriptPlayer")]),
    (L_, "main.p12", 8, "GETTABLE", {"A": 1, "B": 1, "C": 261}, [("C", 5, "invoke")]),
    (L_, "main.p12", 9, "LOADK", {"A": 2, "Bx": 6}, [("Bx", 6, "backup_list_selected_id")]),
    (L_, "main.p12", 10, "CALL", {"A": 1, "B": 2, "C": 1}, []),
    (L_, "main.p13", 37, "GETTABUP", {"A": 3, "B": 0, "C": 272}, [("C", 16, "UiScriptPlayer")]),
    (L_, "main.p13", 38, "GETTABLE", {"A": 3, "B": 3, "C": 273}, [("C", 17, "invoke")]),
    (L_, "main.p13", 39, "LOADK", {"A": 4, "Bx": 18}, [("Bx", 18, "select_list_from_backup_id")]),
    (L_, "main.p13", 40, "CALL", {"A": 3, "B": 2, "C": 1}, []),
    (L_, "main.p13", 61, "GETTABUP", {"A": 3, "B": 0, "C": 272}, [("C", 16, "UiScriptPlayer")]),
    (L_, "main.p13", 62, "GETTABLE", {"A": 3, "B": 3, "C": 273}, [("C", 17, "invoke")]),
    (L_, "main.p13", 63, "LOADK", {"A": 4, "Bx": 24}, [("Bx", 24, "sort_id_list")]),
    (L_, "main.p13", 65, "CALL", {"A": 3, "B": 3, "C": 1}, []),

    # -- 4. input detection --------------------------------------------------
    (L_, "main.p11", 1, "SELF", {"A": 1, "B": 1, "C": 257}, [("C", 1, "is_cancel")]),
    (L_, "main.p11", 2, "CALL", {"A": 1, "B": 2, "C": 2}, []),
    (L_, "main.p11", 6, "GETTABLE", {"A": 1, "B": 1, "C": 259}, [("C", 3, "press_cancel")]),
    (L_, "main.p11", 37, "SELF", {"A": 2, "B": 2, "C": 267}, [("C", 11, "is_pressed")]),
    (L_, "main.p11", 38, "GETTABUP", {"A": 4, "B": 0, "C": 268}, [("C", 12, "INPUT_BUTTON_UP")]),
    (L_, "main.p11", 39, "CALL", {"A": 2, "B": 3, "C": 2}, []),
    (L_, "main.p11", 44, "GETTABUP", {"A": 4, "B": 0, "C": 270}, [("C", 14, "SCROLLER_ITEM_NUM")]),
    (L_, "main.p11", 45, "SUB", {"A": 4, "B": 4, "C": 271}, [("C", 15, 1)]),
    (L_, "main.p11", 47, "CALL", {"A": 2, "B": 4, "C": 1}, []),
    (L_, "main.p11", 52, "GETTABUP", {"A": 4, "B": 0, "C": 272}, [("C", 16, "INPUT_BUTTON_DOWN")]),
    (L_, "main.p11", 53, "CALL", {"A": 2, "B": 3, "C": 2}, []),
    (L_, "main.p11", 78, "GETTABUP", {"A": 3, "B": 0, "C": 278}, [("C", 22, "UI_SE_ID_CURSOR")]),
    (L_, "main.p11", 82, "SELF", {"A": 1, "B": 1, "C": 280}, [("C", 24, "get_decided_item")]),
    (L_, "main.p11", 83, "CALL", {"A": 1, "B": 2, "C": 2}, []),
    (L_, "main.p11", 84, "SETTABLE", {"A": 0, "B": 279, "C": 1}, [("B", 23, "decided_id")]),
    (L_, "main.p11", 86, "LE", {"A": 0, "B": 281, "C": 1}, [("B", 25, 0)]),
    (L_, "main.p11", 99, "SELF", {"A": 1, "B": 1, "C": 283}, [("C", 27, "get_selected_item")]),
    (L_, "main.p11", 100, "CALL", {"A": 1, "B": 2, "C": 2}, []),
    (L_, "main.p11", 101, "GETTABUP", {"A": 2, "B": 0, "C": 284}, [("C", 28, "BUTTON_ID_NONE")]),
    (L_, "main.p11", 105, "SELF", {"A": 2, "B": 2, "C": 285}, [("C", 29, "special_input_is_upward")]),
    (L_, "main.p11", 111, "SELF", {"A": 2, "B": 2, "C": 286}, [("C", 30, "special_input_is_downward")]),
    (L_, "main.p11", 129, "GETTABLE", {"A": 1, "B": 1, "C": 287}, [("C", 31, "is_cancelled")]),
    (L_, "main.p11", 130, "CALL", {"A": 1, "B": 1, "C": 2}, []),

    # -- 5. the sort sub-window is the only category switch ------------------
    (L_, "main.p5", 50, "GETUPVAL", {"A": 10, "B": 1}, []),
    (L_, "main.p5", 51, "GETTABUP", {"A": 11, "B": 0, "C": 284},
     [("C", 28, "INPUT_OPEN_SORT_WINDOW")]),
    (L_, "main.p5", 53, "CALL", {"A": 8, "B": 5, "C": 1}, []),
    (L_, "main.p12", 23, "SELF", {"A": 1, "B": 1, "C": 269}, [("C", 13, "activate")]),
    (L_, "main.p12", 27, "SELF", {"A": 1, "B": 1, "C": 271}, [("C", 15, "open")]),
    (L_, "main.p12", 28, "GETTABLE", {"A": 3, "B": 0, "C": 272}, [("C", 16, "sort_id")]),
    (L_, "main.p13", 6, "SELF", {"A": 3, "B": 3, "C": 259}, [("C", 3, "get_result")]),
    (L_, "main.p13", 7, "CALL", {"A": 3, "B": 2, "C": 3}, []),
    (L_, "main.p13", 11, "SELF", {"A": 3, "B": 3, "C": 260}, [("C", 4, "is_busy")]),
    (L_, "main.p13", 70, "SELF", {"A": 3, "B": 3, "C": 282}, [("C", 26, "close")]),
    (L_, "main.p13", 71, "CALL", {"A": 3, "B": 2, "C": 1}, []),

    # -- 6. text sources ----------------------------------------------------
    (L_, "main.p4", 0, "NEWTABLE", {"A": 1, "B": 3, "C": 0}, []),
    (L_, "main.p4", 1, "LOADK", {"A": 2, "Bx": 0}, [("Bx", 0, "mnu_mmiif_sort_1")]),
    (L_, "main.p4", 2, "LOADK", {"A": 3, "Bx": 1}, [("Bx", 1, "mnu_mmiif_sort_3")]),
    (L_, "main.p4", 3, "LOADK", {"A": 4, "Bx": 2}, [("Bx", 2, "mnu_mmiif_sort_4")]),
    (L_, "main.p4", 4, "SETLIST", {"A": 1, "B": 3, "C": 1}, []),
    (L_, "main.p4", 6, "SELF", {"A": 2, "B": 2, "C": 260}, [("C", 4, "set_text_message")]),
    (L_, "main.p4", 8, "ADD", {"A": 4, "B": 4, "C": 262}, [("C", 6, 1)]),
    (L_, "main.p4", 10, "CALL", {"A": 2, "B": 3, "C": 1}, []),
    (H, "main.p0", 2, "GETTABLE", {"A": 0, "B": 0, "C": 259}, [("C", 3, "set_sub_title")]),
    (H, "main.p0", 4, "CALL", {"A": 0, "B": 2, "C": 1}, []),

    # -- 2. the 9 animation parts per initialise_* -------------------------
    (L_, "main.p6", 15, "LOADK", {"A": 13, "Bx": 7}, [("Bx", 7, "set_parts_scr_item_%02d")]),
    (L_, "main.p6", 16, "MOVE", {"A": 14, "B": 9}, []),
    (L_, "main.p6", 18, "LOADK", {"A": 13, "Bx": 8}, [("Bx", 8, "category_01")]),
    (L_, "main.p6", 19, "CALL", {"A": 10, "B": 4, "C": 1}, []),
    (L_, "main.p7", 15, "LOADK", {"A": 13, "Bx": 7}, [("Bx", 7, "set_parts_scr_item_%02d")]),
    (L_, "main.p7", 18, "LOADK", {"A": 13, "Bx": 8}, [("Bx", 8, "category_00")]),
    (L_, "main.p7", 19, "CALL", {"A": 10, "B": 4, "C": 1}, []),
    (L_, "main", 7, "LOADK", {"A": 7, "Bx": 5}, [("Bx", 5, 9)]),
    (L_, "main.p6", 7, "LOADK", {"A": 6, "Bx": 1}, [("Bx", 1, 0)]),
    (L_, "main.p6", 8, "GETUPVAL", {"A": 7, "B": 0}, []),
    (L_, "main.p6", 9, "LOADK", {"A": 8, "Bx": 2}, [("Bx", 2, 1)]),
    (L_, "main.p6", 10, "FORPREP", {"A": 6, "sBx": 9}, []),
    (L_, "main.p6", 11, "GETTABLE", {"A": 10, "B": 0, "C": 259}, [("C", 3, "main_view")]),
    (L_, "main.p6", 12, "SELF", {"A": 10, "B": 10, "C": 260}, [("C", 4, "play_animation_parts")]),
    (L_, "main.p6", 14, "GETTABLE", {"A": 12, "B": 12, "C": 262}, [("C", 6, "format")]),

    # -- 2b. initialize(): where the six arguments land -------------------
    (L_, "main.p5", 0, "SETTABLE", {"A": 0, "B": 256, "C": 1}, [("B", 0, "main_root")]),
    (L_, "main.p5", 11, "SETTABLE", {"A": 0, "B": 263, "C": 2}, [("B", 7, "sub_root")]),
    (L_, "main.p5", 18, "SETTABLE", {"A": 0, "B": 266, "C": 3}, [("B", 10, "scroller")]),
    (L_, "main.p5", 19, "SETTABLE", {"A": 0, "B": 267, "C": 4}, [("B", 11, "sub_list_window")]),
    (L_, "main.p5", 20, "SETTABLE", {"A": 0, "B": 268, "C": 5},
     [("B", 12, "sub_list_window_facade")]),
    (L_, "main.p5", 21, "GETTABLE", {"A": 6, "B": 0, "C": 257}, [("C", 1, "main_view")]),
    (L_, "main.p5", 22, "SELF", {"A": 6, "B": 6, "C": 269}, [("C", 13, "get_parts")]),
    (L_, "main.p5", 23, "LOADK", {"A": 8, "Bx": 14}, [("Bx", 14, "scr_sort")]),
    (L_, "main.p5", 25, "SELF", {"A": 7, "B": 6, "C": 272}, [("C", 16, "get_pane")]),
    (L_, "main.p5", 26, "LOADK", {"A": 9, "Bx": 17}, [("Bx", 17, "set_txt_list")]),
    (L_, "main.p5", 28, "SETTABLE", {"A": 0, "B": 271, "C": 7}, [("B", 15, "sort_text_pane")]),
    (L_, "main.p5", 29, "GETTABUP", {"A": 7, "B": 0, "C": 274},
     [("C", 18, "LayoutButtonSelectorConfig")]),
    (L_, "main.p5", 30, "GETTABLE", {"A": 7, "B": 7, "C": 275}, [("C", 19, "new")]),
    (L_, "main.p5", 31, "CALL", {"A": 7, "B": 1, "C": 2}, []),
    (L_, "main.p5", 32, "SETTABLE", {"A": 7, "B": 276, "C": 277},
     [("B", 20, "is_unique_se"), ("C", 21, True)]),
    (L_, "main.p5", 33, "GETTABUP", {"A": 8, "B": 0, "C": 279},
     [("C", 23, "LayoutButtonSelector")]),
    (L_, "main.p5", 34, "GETTABLE", {"A": 8, "B": 8, "C": 275}, [("C", 19, "new")]),
    (L_, "main.p5", 35, "CALL", {"A": 8, "B": 1, "C": 2}, []),
    (L_, "main.p5", 36, "SETTABLE", {"A": 0, "B": 278, "C": 8}, [("B", 22, "selector")]),
    (L_, "main.p5", 38, "SELF", {"A": 8, "B": 8, "C": 280}, [("C", 24, "setup")]),
    (L_, "main.p5", 40, "LOADK", {"A": 11, "Bx": 25}, [("Bx", 25, "selector_sort")]),
    (L_, "main.p5", 41, "MOVE", {"A": 12, "B": 7}, []),
    (L_, "main.p5", 42, "CALL", {"A": 8, "B": 5, "C": 1}, []),
    (L_, "main.p5", 44, "SELF", {"A": 8, "B": 8, "C": 282}, [("C", 26, "setup_button")]),
    (L_, "main.p5", 47, "CALL", {"A": 8, "B": 4, "C": 1}, []),
    (L_, "main.p5", 49, "SELF", {"A": 8, "B": 8, "C": 283}, [("C", 27, "set_shortcut")]),
    (L_, "main.p5", 53, "CALL", {"A": 8, "B": 5, "C": 1}, []),
    (L_, "main.p5", 55, "SELF", {"A": 8, "B": 8, "C": 285}, [("C", 29, "select_button")]),
    (L_, "main.p5", 57, "CALL", {"A": 8, "B": 3, "C": 1}, []),
    (L_, "main.p5", 58, "GETUPVAL", {"A": 8, "B": 2}, []),
    (L_, "main.p5", 59, "SELF", {"A": 8, "B": 8, "C": 280}, [("C", 24, "setup")]),
    (L_, "main.p5", 63, "LOADK", {"A": 13, "Bx": 31}, [("Bx", 31, "STATE_UPDATE_NONE")]),
    (L_, "main.p5", 64, "CALL", {"A": 8, "B": 6, "C": 1}, []),
    (L_, "main.p5", 70, "LOADK", {"A": 13, "Bx": 33}, [("Bx", 33, "STATE_UPDATE_MAIN")]),
    (L_, "main.p5", 71, "CALL", {"A": 8, "B": 6, "C": 1}, []),
    (L_, "main.p5", 77, "LOADK", {"A": 13, "Bx": 35},
     [("Bx", 35, "STATE_UPDATE_SUB_LIST_WINDOW_IN")]),
    (L_, "main.p5", 78, "CALL", {"A": 8, "B": 6, "C": 1}, []),
    (L_, "main.p5", 84, "LOADK", {"A": 13, "Bx": 37},
     [("Bx", 37, "STATE_UPDATE_SUB_LIST_WINDOW")]),
    (L_, "main.p5", 85, "CALL", {"A": 8, "B": 6, "C": 1}, []),
    (L_, "main.p5", 86, "SETTABLE", {"A": 0, "B": 294, "C": 295},
     [("B", 38, "select_id"), ("C", 39, 0)]),
    (L_, "main.p5", 87, "SETTABLE", {"A": 0, "B": 296, "C": 297},
     [("B", 40, "decided_id"), ("C", 41, -1)]),
    (L_, "main.p5", 88, "SETTABLE", {"A": 0, "B": 298, "C": 299},
     [("B", 42, "on_cursor_list"), ("C", 43, False)]),

    # -- 4. the actor's main loop and the screen's finished test -----------
    (H, "main.p0", 1, "GETTABUP", {"A": 0, "B": 0, "C": 258}, [("C", 2, "ComFrameActor")]),
    (H, "main.p0", 2, "GETTABLE", {"A": 0, "B": 0, "C": 259}, [("C", 3, "set_sub_title")]),
    (H, "main.p0", 4, "CALL", {"A": 0, "B": 2, "C": 1}, []),
    (H, "main.p0", 5, "GETUPVAL", {"A": 0, "B": 1}, []),
    (H, "main.p0", 6, "SELF", {"A": 0, "B": 0, "C": 261}, [("C", 5, "update_in")]),
    (H, "main.p0", 7, "CALL", {"A": 0, "B": 2, "C": 1}, []),
    (H, "main.p0", 8, "GETTABUP", {"A": 0, "B": 0, "C": 256}, [("C", 0, "is_finish")]),
    (H, "main.p0", 9, "EQ", {"A": 0, "B": 0, "C": 257}, [("C", 1, False)]),
    (H, "main.p0", 10, "JMP", {"A": 0, "sBx": 9}, []),
    (H, "main.p0", 12, "SELF", {"A": 0, "B": 0, "C": 262}, [("C", 6, "update")]),
    (H, "main.p0", 13, "CALL", {"A": 0, "B": 2, "C": 2}, []),
    (H, "main.p0", 14, "EQ", {"A": 1, "B": 0, "C": 263}, [("C", 7, True)]),
    (H, "main.p0", 15, "JMP", {"A": 0, "sBx": 4}, []),
    (H, "main.p0", 16, "GETTABUP", {"A": 0, "B": 0, "C": 264}, [("C", 8, "coroutine")]),
    (H, "main.p0", 17, "GETTABLE", {"A": 0, "B": 0, "C": 265}, [("C", 9, "yield")]),
    (H, "main.p0", 18, "CALL", {"A": 0, "B": 1, "C": 1}, []),
    (H, "main.p0", 19, "JMP", {"A": 0, "sBx": -12}, []),
    (H, "main.p0", 20, "GETTABUP", {"A": 0, "B": 0, "C": 258}, [("C", 2, "ComFrameActor")]),
    (H, "main.p0", 21, "GETTABLE", {"A": 0, "B": 0, "C": 266},
     [("C", 10, "set_footer_area")]),
    (H, "main.p0", 22, "GETTABUP", {"A": 1, "B": 0, "C": 267},
     [("C", 11, "COMFRAME_FOOTERMESSAGEAREA_NONE")]),
    (H, "main.p0", 25, "SELF", {"A": 0, "B": 0, "C": 268}, [("C", 12, "update_out")]),
    (L_, "main.p14", 2, "CALL", {"A": 1, "B": 2, "C": 1}, []),
    (L_, "main.p14", 4, "SELF", {"A": 1, "B": 1, "C": 257}, [("C", 1, "get")]),
    (L_, "main.p14", 5, "CALL", {"A": 1, "B": 2, "C": 2}, []),
    (L_, "main.p14", 7, "EQ", {"A": 0, "B": 1, "C": 2}, []),

    # -- 4b. update_main: the focus and page-scroll branch -----------------
    (L_, "main.p11", 10, "SELF", {"A": 1, "B": 1, "C": 261},
     [("C", 5, "get_decided_button_id")]),
    (L_, "main.p11", 11, "CALL", {"A": 1, "B": 2, "C": 2}, []),
    (L_, "main.p11", 22, "SELF", {"A": 1, "B": 1, "C": 263}, [("C", 7, "has_focus")]),
    (L_, "main.p11", 27, "SELF", {"A": 1, "B": 1, "C": 263}, [("C", 7, "has_focus")]),
    (L_, "main.p11", 46, "LOADBOOL", {"A": 5, "B": 1, "C": 0}, []),
    (L_, "main.p11", 47, "CALL", {"A": 2, "B": 4, "C": 1}, []),
    (L_, "main.p11", 63, "LOADBOOL", {"A": 6, "B": 1, "C": 0}, []),
    (L_, "main.p11", 64, "CALL", {"A": 3, "B": 4, "C": 1}, []),
    (L_, "main.p11", 76, "GETTABUP", {"A": 2, "B": 0, "C": 276}, [("C", 20, "UiSoundManager")]),
    (L_, "main.p11", 77, "GETTABLE", {"A": 2, "B": 2, "C": 277}, [("C", 21, "play_se")]),
    (L_, "main.p11", 78, "GETTABUP", {"A": 3, "B": 0, "C": 278}, [("C", 22, "UI_SE_ID_CURSOR")]),
    (L_, "main.p11", 79, "CALL", {"A": 2, "B": 2, "C": 1}, []),
    (L_, "main.p11", 91, "CALL", {"A": 1, "B": 3, "C": 1}, []),
    (L_, "main.p11", 140, "CALL", {"A": 1, "B": 3, "C": 1}, []),
    (L_, "main.p8", 0, "SETTABLE", {"A": 0, "B": 256, "C": 257},
     [("B", 0, "decided_id"), ("C", 1, -1)]),
    (L_, "main.p8", 4, "LOADBOOL", {"A": 4, "B": 0, "C": 0}, []),
    (L_, "main.p8", 5, "CALL", {"A": 1, "B": 4, "C": 1}, []),
    (L_, "main.p8", 7, "LOADBOOL", {"A": 3, "B": 1, "C": 0}, []),
    (L_, "main.p8", 22, "LOADK", {"A": 3, "Bx": 11}, [("Bx", 11, "in")]),
    (L_, "main.p8", 27, "CALL", {"A": 1, "B": 3, "C": 1}, []),
    (L_, "main.p9", 2, "LOADK", {"A": 3, "Bx": 2}, [("Bx", 2, "out")]),
    (L_, "main.p12", 3, "SETTABLE", {"A": 0, "B": 256, "C": 1}, [("B", 0, "on_cursor_list")]),
    (L_, "main.p12", 29, "CALL", {"A": 1, "B": 3, "C": 1}, []),
    (L_, "main.p13", 58, "SETTABLE", {"A": 0, "B": 278, "C": 2}, [("B", 22, "sort_id")]),
]

# globals each chunk writes to _ENV, and globals it only reads
EXPECTED_WRITES = {
    H: {"get_decided_id", "initialize", "is_finish", "main", "set_select_id",
        "set_sort_id"},
    B: {"get_decided_id", "initialize", "is_finish", "main", "set_select_id",
        "set_sort_id"},
    L_: set(),
    U: {"MII_FIGHTER_DEFAULT_ROTATE", "F_CAMERA_DEFAULT_POSITION_X",
        "F_CAMERA_DEFAULT_POSITION_Y", "F_CAMERA_DEFAULT_POSITION_Z",
        "S_CAMERA_DEFAULT_POSITION_X", "S_CAMERA_DEFAULT_POSITION_Y",
        "S_CAMERA_DEFAULT_POSITION_Z", "G_CAMERA_DEFAULT_POSITION_X",
        "G_CAMERA_DEFAULT_POSITION_Y", "G_CAMERA_DEFAULT_POSITION_Z",
        "F_RIGHT_SIDE_0_CAMERA_TRANSLATE_X", "F_RIGHT_SIDE_0_CAMERA_TRANSLATE_Y",
        "F_RIGHT_SIDE_0_CAMERA_POSITION_Z", "S_RIGHT_SIDE_0_CAMERA_TRANSLATE_X",
        "S_RIGHT_SIDE_0_CAMERA_TRANSLATE_Y", "S_RIGHT_SIDE_0_CAMERA_POSITION_Z",
        "G_RIGHT_SIDE_0_CAMERA_TRANSLATE_X", "G_RIGHT_SIDE_0_CAMERA_TRANSLATE_Y",
        "G_RIGHT_SIDE_0_CAMERA_POSITION_Z", "F_RIGHT_SIDE_1_CAMERA_TRANSLATE_X",
        "F_RIGHT_SIDE_1_CAMERA_TRANSLATE_Y", "F_RIGHT_SIDE_1_CAMERA_POSITION_Z",
        "S_RIGHT_SIDE_1_CAMERA_TRANSLATE_X", "S_RIGHT_SIDE_1_CAMERA_TRANSLATE_Y",
        "S_RIGHT_SIDE_1_CAMERA_POSITION_Z", "G_RIGHT_SIDE_1_CAMERA_TRANSLATE_X",
        "G_RIGHT_SIDE_1_CAMERA_TRANSLATE_Y", "G_RIGHT_SIDE_1_CAMERA_POSITION_Z",
        "HAT_SELECT_CAMERA_TRANSLATE_X", "HAT_SELECT_CAMERA_TRANSLATE_Y",
        "HAT_SELECT_CAMERA_TRANSLATE_LOOK_AT_Y", "HAT_SELECT_CAMERA_POSITION_Z"},
}

EXPECTED_READS = {
    H: {"COMFRAME_FOOTERMESSAGEAREA_NONE", "ComFrameActor", "UiScriptPlayer",
        "LayoutRootList", "coroutine", "is_finish", "scroller",
        "sub_list_window", "sub_list_window_facade"},
    B: {"COMFRAME_FOOTERMESSAGEAREA_NONE", "ComFrameActor", "UiScriptPlayer",
        "LayoutRootList", "coroutine", "is_finish", "scroller",
        "sub_list_window", "sub_list_window_facade"},
    L_: {"BUTTON_ID_NONE", "ComFrameActor", "INPUT_BUTTON_DOWN",
         "INPUT_BUTTON_UP", "INPUT_OPEN_SORT_WINDOW", "LayoutButtonSelector",
         "LayoutButtonSelectorConfig", "SCROLLER_ITEM_NUM", "UI_SE_ID_CURSOR",
         "UiScriptPlayer", "UiSoundManager", "setmetatable", "string"},
    U: {"MII_TYPE_SWORDSMAN", "MII_TYPE_GUNNER", "setmetatable",
        "F_CAMERA_DEFAULT_POSITION_X", "F_CAMERA_DEFAULT_POSITION_Y",
        "F_CAMERA_DEFAULT_POSITION_Z", "S_CAMERA_DEFAULT_POSITION_X",
        "S_CAMERA_DEFAULT_POSITION_Y", "S_CAMERA_DEFAULT_POSITION_Z",
        "G_CAMERA_DEFAULT_POSITION_X", "G_CAMERA_DEFAULT_POSITION_Y",
        "G_CAMERA_DEFAULT_POSITION_Z", "F_RIGHT_SIDE_0_CAMERA_TRANSLATE_X",
        "F_RIGHT_SIDE_0_CAMERA_TRANSLATE_Y", "F_RIGHT_SIDE_0_CAMERA_POSITION_Z",
        "S_RIGHT_SIDE_0_CAMERA_TRANSLATE_X", "S_RIGHT_SIDE_0_CAMERA_TRANSLATE_Y",
        "S_RIGHT_SIDE_0_CAMERA_POSITION_Z", "G_RIGHT_SIDE_0_CAMERA_TRANSLATE_X",
        "G_RIGHT_SIDE_0_CAMERA_TRANSLATE_Y", "G_RIGHT_SIDE_0_CAMERA_POSITION_Z",
        "F_RIGHT_SIDE_1_CAMERA_TRANSLATE_X", "F_RIGHT_SIDE_1_CAMERA_TRANSLATE_Y",
        "F_RIGHT_SIDE_1_CAMERA_POSITION_Z", "S_RIGHT_SIDE_1_CAMERA_TRANSLATE_X",
        "S_RIGHT_SIDE_1_CAMERA_TRANSLATE_Y", "S_RIGHT_SIDE_1_CAMERA_POSITION_Z",
        "G_RIGHT_SIDE_1_CAMERA_TRANSLATE_X", "G_RIGHT_SIDE_1_CAMERA_TRANSLATE_Y",
        "G_RIGHT_SIDE_1_CAMERA_POSITION_Z", "HAT_SELECT_CAMERA_TRANSLATE_X",
        "HAT_SELECT_CAMERA_TRANSLATE_Y", "HAT_SELECT_CAMERA_TRANSLATE_LOOK_AT_Y",
        "HAT_SELECT_CAMERA_POSITION_Z"},
}

# (chunk, proto, SELF pc, method) for every scroller method the report names.
# SELF's B operand is the receiver register; the instruction before it is a
# GETTABLE with B=0, i.e. self['scroller'].
SCROLLER_CALLS = [
    (L_, "main.p2", 5, "set_enable"),
    (L_, "main.p2", 15, "set_focus"),
    (L_, "main.p3", 9, "redraw_all_items"),
    (L_, "main.p8", 2, "select_item"),
    (L_, "main.p8", 10, "set_focus"),
    (L_, "main.p8", 14, "redraw_all_items"),
    (L_, "main.p11", 27, "has_focus"),
    (L_, "main.p11", 32, "set_focus"),
    (L_, "main.p11", 43, "select_item"),
    (L_, "main.p11", 61, "select_item"),
    (L_, "main.p11", 73, "set_focus"),
    (L_, "main.p11", 82, "get_decided_item"),
    (L_, "main.p11", 99, "get_selected_item"),
    (L_, "main.p11", 105, "special_input_is_upward"),
    (L_, "main.p11", 111, "special_input_is_downward"),
    (L_, "main.p12", 1, "has_focus"),
    (L_, "main.p13", 34, "set_focus"),
    (L_, "main.p13", 67, "redraw_all_items"),
]

# strings that must NOT appear anywhere in the four chunks (Q7: not in Lua)
MUST_NOT_APPEAR = [
    "get_item_num", "set_item_num", "item_count", "get_num_items",
    "set_item_text", "set_item_name", "set_item_icon", "set_item_texture",
    "set_text", "set_icon", "load_texture", "set_equipped", "set_new_mark",
    "preview", "set_preview", "apply_hat", "set_hat", "get_hat_id",
    "set_hat_id", "equip", "on_decide", "on_item", "on_scroll",
]

# ---------------------------------------------------------------------------
# Report coverage. research/P6-HAT-UI.md section 11 is chunk-scoped by its own
# headings; every table row's first column names a proto and a pc or pc range.
# We re-parse the report so that (a) every pc it cites really exists in the chunk
# it is attributed to, and (b) no CLAIMS entry has drifted away from the report.
REPORT = os.path.join(MOD, "research", "P6-HAT-UI.md")
REPORT_CHUNK_OF_SECTION = {
    "11.1": "make_mii_hat_actor",
    "11.2": "make_mii_hat_body_layout",
    "11.3": "make_mii_hat_body_layout",
    "11.4": "make_mii_hat_body_layout",
    "11.5": "make_mii_hat_body_layout",
    "11.6": "make_mii_utility",
}
_REPORT_CELL = re.compile(r"^\s*(main(?:\.p\d+)?|p\d+)\s*(.*?)\s*$")
_REPORT_SPAN = re.compile(r"(\d+)(?:\s*-\s*(\d+))?")
_REPORT_HEAD = re.compile(r"^###\s+(11\.\d)\b")


def report_cites():
    """{(chunk, proto_path, pc)} -> every pc the report's call-flow tables cite.

    A row's first cell names one prototype and then one or more pc or pc-range
    references, e.g. ``p11 107 / pc113`` or ``p5 58-85``. Every reference counts.
    """
    cites = set()
    chunk = None
    with open(REPORT, "r", encoding="utf-8") as fh:
        for line in fh:
            head = _REPORT_HEAD.match(line)
            if head:
                chunk = REPORT_CHUNK_OF_SECTION[head.group(1)]
                continue
            if chunk is None or not line.startswith("|"):
                continue
            cells = line.split("|")
            if len(cells) < 3:
                continue
            cell = _REPORT_CELL.match(cells[1])
            if not cell:
                continue
            proto = cell.group(1)
            if proto.startswith("p"):          # the report abbreviates main.pN as pN
                proto = "main." + proto
            for lo, hi in _REPORT_SPAN.findall(cell.group(2)):
                for pc in range(int(lo), int(hi or lo) + 1):
                    cites.add((chunk, proto, pc))
    return cites


FAILURES = []
CHECKS = 0


def ok(label):
    global CHECKS
    CHECKS += 1


def bad(label, detail):
    FAILURES.append("%s: %s" % (label, detail))
    print("  FAIL %s: %s" % (label, detail))


def env_ups(main):
    index = {p.path: p for p in L.walk(main)}

    def is_env(path, n, seen=None):
        seen = seen or set()
        if (path, n) in seen:
            return False
        seen.add((path, n))
        instack, idx = index[path].upvalues[n]
        parent = index[path].path.rsplit(".p", 1)[0] \
            if ".p" in index[path].path else None
        if path == "main":
            return instack == 1 and idx == 0
        if instack == 1:
            return False
        return is_env(parent, idx, seen)

    return {p.path: sorted(n for n in range(len(p.upvalues)) if is_env(p.path, n))
            for p in L.walk(main)}


def const_at(p, inst, field, idx):
    """Value of the constant an instruction operand names."""
    if field == "Bx":
        return p.constants[idx].value
    raw = inst.b if field == "B" else inst.c
    return p.constants[raw & ~L.BITRK].value


def main() -> int:
    gd = os.path.join(
        sys.argv[1] if len(sys.argv) > 1
        else os.path.join(ROOT, "gamedata", "mii_customizer", "P6-HAT-UI"),
        "ui", "script", "menu", "chara_make")

    chunks = {}
    for name, (size, sha) in EXPECTED_FILES.items():
        path = os.path.join(gd, name + ".lc")
        if not os.path.isfile(path):
            bad("file-present", "%s missing" % path)
            continue
        with open(path, "rb") as fh:
            data = fh.read()
        label = "hash/%s" % name
        if len(data) != size:
            bad(label, "size %d != %d" % (len(data), size))
        else:
            ok(label)
        got = hashlib.sha256(data).hexdigest()
        if got != sha:
            bad(label, "sha256 %s != %s" % (got, sha))
        else:
            ok(label)
        hdr, m = L.load_chunk(data)
        chunks[name] = (hdr, m, {p.path: p for p in L.walk(m)}, env_ups(m))
        if hdr.version != 0x53 or hdr.num_size != 4 or hdr.size_t_size != 8:
            bad("header/%s" % name, "unexpected header %r" % hdr.as_dict())
        else:
            ok("header/%s" % name)

    for name, (m, idx, env) in ((n, (c[1], c[2], c[3])) for n, c in chunks.items()):
        protos = list(L.walk(m))
        nconst = sum(len(p.constants) for p in protos)
        ncode = sum(len(p.code) for p in protos)
        want = EXPECTED_TOTALS[name]
        if (len(protos), ncode, nconst) != want:
            bad("totals/%s" % name,
                "protos/instrs/consts = %s != %s" % ((len(protos), ncode, nconst), want))
        else:
            ok("totals/%s" % name)
        for path, (code, params, ms, envs) in EXPECTED_PROTOS[name].items():
            p = idx.get(path)
            if p is None:
                bad("proto/%s/%s" % (name, path), "absent")
                continue
            if (len(p.code), p.numparams, p.maxstacksize) != (code, params, ms):
                bad("proto/%s/%s" % (name, path),
                    "code/params/maxstack = %s != %s"
                    % ((len(p.code), p.numparams, p.maxstacksize), (code, params, ms)))
            elif env[p.path] != envs:
                bad("proto/%s/%s" % (name, path),
                    "env upvalues %s != %s" % (env[p.path], envs))
            else:
                ok("proto/%s/%s" % (name, path))

    for chunk, path, pc, opname, fields, consts in CLAIMS:
        label = "claim/%s/%s/pc%d" % (chunk, path, pc)
        if chunk not in chunks:
            bad(label, "chunk not loaded")
            continue
        idx = chunks[chunk][2]
        p = idx.get(path)
        if p is None:
            bad(label, "no such proto")
            continue
        if not 0 <= pc < len(p.code):
            bad(label, "pc out of range (%d instructions)" % len(p.code))
            continue
        inst = p.code[pc]
        if inst.name != opname:
            bad(label, "opcode %s != %s" % (inst.name, opname))
            continue
        mismatch = [("%s=%d != %d" % (f, getattr(inst, f.lower()), v))
                    for f, v in fields.items()
                    if getattr(inst, f.lower()) != v]
        if mismatch:
            bad(label, "; ".join(mismatch))
            continue
        for field, cidx, cval in consts:
            got = const_at(p, inst, field, cidx)
            same = (got == cval) or (isinstance(got, float)
                                     and isinstance(cval, float)
                                     and abs(got - cval) < 1e-9)
            if not same:
                bad(label, "%s constant %r != %r" % (field, got, cval))
                break
        else:
            ok(label)

    for chunk, path, pc, method in SCROLLER_CALLS:
        label = "scroller/%s/%s/pc%d" % (chunk, path, pc)
        idx = chunks.get(chunk, (None, None, {}, {}))[2]
        p = idx.get(path)
        if p is None:
            bad(label, "no such proto")
            continue
        inst = p.code[pc]
        if inst.name != "SELF":
            bad(label, "expected SELF, got %s" % inst.args_text())
            continue
        name = p.constants[inst.c & ~L.BITRK].value
        if name != method:
            bad(label, "method %r != %r" % (name, method))
            continue
        prev = p.code[pc - 1] if pc else None
        if prev is None or prev.name != "GETTABLE" or prev.b != 0 \
                or prev.a != inst.b:
            bad(label, "receiver is not R[0]['scroller'] (prev %s, SELF %s)"
                % (prev.args_text() if prev else "-", inst.args_text()))
            continue
        field = p.constants[prev.c & ~L.BITRK].value
        if field != "scroller":
            bad(label, "receiver field %r != 'scroller'" % field)
            continue
        ok(label)

    # globals read / written, resolved through the upvalue chain
    for name, (hdr, m, idx, env) in chunks.items():
        reads, writes = set(), set()
        for p in L.walk(m):
            for inst in p.code:
                if inst.name == "GETTABUP" and env[p.path] and \
                        inst.b in env[p.path]:
                    reads.add(p.constants[inst.c & ~L.BITRK].value)
                elif inst.name == "SETTABUP" and env[p.path] and \
                        inst.a in env[p.path]:
                    writes.add(p.constants[inst.b & ~L.BITRK].value)
        for label, got, want in (("reads", reads, EXPECTED_READS[name]),
                                 ("writes", writes, EXPECTED_WRITES[name])):
            if got != want:
                bad("globals-%s/%s" % (label, name),
                    "extra %s / missing %s"
                    % (sorted(got - want) or "-", sorted(want - got) or "-"))
            else:
                ok("globals-%s/%s" % (label, name))

    # Q7: nothing in the four chunks names any of these
    for name, (hdr, m, idx, env) in chunks.items():
        present = []
        for p in L.walk(m):
            for k in p.constants:
                if isinstance(k.value, str):
                    present.append(k.value)
        blob = set(present)
        hits = [s for s in MUST_NOT_APPEAR if s in blob]
        if hits:
            bad("absent-names/%s" % name, "unexpected constant(s) %s" % hits)
        else:
            ok("absent-names/%s" % name)

    # -- report coverage -----------------------------------------------------
    if not os.path.isfile(REPORT):
        bad("report-present", "missing %s" % REPORT)
    else:
        ok("report-present")
        cites = report_cites()
        for chunk, proto, pc in sorted(cites):
            label = "cite/%s/%s/pc%d" % (chunk, proto, pc)
            idx = chunks.get(chunk, (None, None, {}, {}))[2]
            p = idx.get(proto)
            if p is None:
                bad(label, "report cites a proto that does not exist")
            elif not 0 <= pc < len(p.code):
                bad(label, "report cites pc outside %d instructions" % len(p.code))
            else:
                ok(label)
        # The report's tables are semantic ranges, not instruction-by-instruction
        # dumps, so the reverse direction is only asserted for the sites the
        # report names one by one: the 6 bridge invocations and the scroller
        # calls. Those must appear in the report's cited pc set.
        named = {(c, p, n) for c, p, n, _m in SCROLLER_CALLS}
        named |= {(c, p, n) for c, p, n, _o, _f, _cs in CLAIMS
                  if _cs and any(k == "Bx" and isinstance(v, str)
                                 and v in ("sort_id_list", "get_top_index",
                                           "backup_list_selected_id",
                                           "select_list_from_backup_id")
                                 for _k, _i, v in _cs)}
        for site in sorted(named):
            label = "report-names/%s/%s/pc%d" % site
            # The report cites the CALL pc; SCROLLER_CALLS records the SELF pc that
            # precedes it by 1-3 instructions. Accept any cited pc in that window.
            chunk, proto, pc = site
            near = any((chunk, proto, pc + d) in cites for d in (-3, -2, -1, 0, 1, 2, 3))
            if not near:
                bad(label, "the report does not cite this call site")
            else:
                ok(label)

    print("\n%d checks, %d failures" % (CHECKS, len(FAILURES)))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())