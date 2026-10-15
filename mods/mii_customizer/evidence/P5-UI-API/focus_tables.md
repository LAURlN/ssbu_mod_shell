# P5-UI-API step 4 focus tables (generated from focus_lists.json)

## 4a text family: 31 methods, with real call examples

### set_text_message  calls=81 scripts=22 args={'0': 13, '1': 68}
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p2 pc75: R[7]=string('mnu_footer_ok')
- ui/script/menu/chara_make/make_mii_hat_body_layout.lc main.p4 pc10: R[4]=other(ADD)
- ui/script/menu/chara_make/make_mii_select_actor.lc main.p4 pc10: R[4]=other(ADD)

### set_text_args  calls=28 scripts=7 args={'2': 22, '3': 6}
- ui/script/menu/collection/collection_shop_top.lc main.p7 pc11: R[3]=global-read(g_gold); R[4]=string('i')
- ui/script/menu/collection/collection_shop_top.lc main.p3 pc14: R[7]=other(MOVE); R[8]=string('i')
- ui/script/menu/online/online_watch.lc main.p5 pc14: R[2]=other(up[1]); R[3]=string('i')

### set_text_message_args  calls=26 scripts=5 args={'3': 11, '4': 9, '5': 2, '6': 4}
- ui/script/menu/local/local_mode_select.lc main.p1 pc168: R[6]=string('mnu_local_new_rm_tmb_player_n'); R[7]=integer(2); R[8]=integer(8); R[9]=string('ii')
- ui/script/menu/local/local_mode_select.lc main.p1 pc192: R[6]=string('mnu_local_new_rm_tmb_player_n'); R[7]=integer(2); R[8]=integer(4); R[9]=string('ii')
- ui/script/menu/local/local_mode_select.lc main.p1 pc216: R[6]=string('mnu_local_new_rm_tmb_player_n'); R[7]=integer(2); R[8]=integer(8); R[9]=string('ii')

### play_se_label  calls=14 scripts=7 args={'1': 14}
- ui/script/menu/main/main_menu_common.lc main.p1 pc35: R[4]=string('se_system_fixed')
- ui/script/menu/melee/special_various.lc main.p15 pc6: R[2]=string('se_system_cancel')
- ui/script/menu/melee/special_various.lc main.p16 pc99: R[3]=string('se_system_fixed')

### set_footer_message  calls=13 scripts=2 args={'1': 13}
- ui/script/menu/local/local_mode_select.lc main.p5 pc25: R[4]=string('mnu_local_new_rm_help_mel_btn_00')
- ui/script/menu/local/local_mode_select.lc main.p5 pc39: R[4]=string('mnu_local_new_rm_help_mel_btn_02')
- ui/script/menu/local/local_mode_select.lc main.p5 pc53: R[4]=string('mnu_local_new_rm_help_mel_btn_03')

### update_sort_text  calls=8 scripts=3 args={'0': 8}
- ui/script/menu/chara_make/make_mii_hat_body_layout.lc main.p3 pc2: (no arguments)
- ui/script/menu/chara_make/make_mii_hat_body_layout.lc main.p13 pc60: (no arguments)
- ui/script/menu/chara_make/make_mii_hat_body_layout.lc main.p5 pc106: (no arguments)

### clear_text_string  calls=7 scripts=3 args={'0': 7}
- ui/script/menu/main/main_menu_banner.lc main.p7 pc100: (no arguments)
- ui/script/menu/main/main_menu_banner.lc main.p7 pc102: (no arguments)
- ui/script/menu/main/main_menu_banner.lc main.p7 pc183: (no arguments)

### set_text_number_int32  calls=5 scripts=3 args={'0': 1, '1': 4}
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p4 pc14: R[5]=other(ADD)
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p3 pc15: R[9]=other(ADD)
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p10 pc36: R[8]=other(MOVE)

### set_text_shadow_color  calls=3 scripts=1 args={'1': 3}
- ui/script/menu/main/main_menu_banner.lc main.p8 pc44: R[11]=integer(0)
- ui/script/menu/main/main_menu_banner.lc main.p8 pc77: R[11]=integer(0)
- ui/script/menu/main/main_menu_banner.lc main.p8 pc73: R[11]=other(R[11])

### set_text_string  calls=3 scripts=2 args={'1': 3}
- ui/script/menu/online/online_onmelee.lc main.p0 pc76: R[12]=other(R[12])
- ui/script/menu/online/online_priority.lc main.p1 pc16: R[6]=other(MOVE)
- ui/script/menu/online/online_priority.lc main.p1 pc28: R[6]=other(MOVE)

### update_help_text  calls=3 scripts=1 args={'0': 3}
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p5 pc3: (no arguments)
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p6 pc7: (no arguments)
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p8 pc28: (no arguments)

### set_label  calls=2 scripts=1 args={'2': 2}
- ui/script/menu/main/main_menu_footer.lc main.p6 pc21: R[5]=other(R[5]); R[6]=other(R[6])
- ui/script/menu/main/main_menu_footer.lc main.p6 pc25: R[5]=other(call result); R[6]=other(call result)

### set_text_alignment_x  calls=2 scripts=1 args={'1': 2}
- ui/script/menu/main/main_menu_banner.lc main.p8 pc29: R[11]=other(call result)
- ui/script/menu/main/main_menu_banner.lc main.p8 pc55: R[11]=other(call result)

### set_text_alignment_y  calls=2 scripts=1 args={'1': 2}
- ui/script/menu/main/main_menu_banner.lc main.p8 pc32: R[11]=other(call result)
- ui/script/menu/main/main_menu_banner.lc main.p8 pc58: R[11]=other(call result)

### set_text_border_color  calls=2 scripts=1 args={'1': 2}
- ui/script/menu/main/main_menu_banner.lc main.p8 pc67: R[11]=integer(0)
- ui/script/menu/main/main_menu_banner.lc main.p8 pc41: R[11]=other(call result)

### set_text_border_enable  calls=2 scripts=1 args={'1': 2}
- ui/script/menu/main/main_menu_banner.lc main.p8 pc64: R[11]=boolean(true)
- ui/script/menu/main/main_menu_banner.lc main.p8 pc38: R[11]=other(call result)

### set_text_color  calls=2 scripts=1 args={'1': 2}
- ui/script/menu/main/main_menu_banner.lc main.p8 pc61: R[11]=integer(0)
- ui/script/menu/main/main_menu_banner.lc main.p8 pc35: R[11]=other(call result)

### set_text_desc  calls=2 scripts=1 args={'4': 2}
- ui/script/menu/main/main_menu_banner.lc main.p7 pc50: R[11]=other(MOVE); R[12]=other(MOVE); R[13]=other(MOVE); R[14]=other(R[14])
- ui/script/menu/main/main_menu_banner.lc main.p7 pc117: R[14]=other(MOVE); R[15]=other(MOVE); R[16]=other(MOVE); R[17]=other(R[17])

### update_text  calls=2 scripts=1 args={'0': 2}
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p13 pc20: (no arguments)
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p14 pc21: (no arguments)

### is_text_scroll_scrolling  calls=1 scripts=1 args={'0': 1}
- ui/script/menu/main/main_menu_information.lc main.p2 pc27: (no arguments)

### play_text_scroll_animation  calls=1 scripts=1 args={'0': 1}
- ui/script/menu/main/main_menu_information.lc main.p2 pc24: (no arguments)

### replace_image_texture  calls=1 scripts=1 args={'1': 1}
- ui/script/menu/main/main_menu_banner.lc main.p7 pc24: R[7]=other(call result)

### reset_text_scroll_location  calls=1 scripts=1 args={'0': 1}
- ui/script/menu/main/main_menu_information.lc main.p2 pc14: (no arguments)

### restore_texture  calls=1 scripts=1 args={'0': 1}
- ui/script/menu/main/main_menu_banner.lc main.p7 pc15: (no arguments)

### set_decide_se_label  calls=1 scripts=1 args={'1': 1}
- ui/script/menu/melee/rule_itemswitch_actor.lc main.p22 pc113: R[7]=string('snd_none')

### set_text_scroll_force_scroll  calls=1 scripts=1 args={'1': 1}
- ui/script/menu/main/main_menu_information.lc main.p0 pc47: R[3]=boolean(true)

### set_text_scroll_loop_enabled  calls=1 scripts=1 args={'1': 1}
- ui/script/menu/main/main_menu_information.lc main.p0 pc55: R[3]=boolean(true)

### set_text_scroll_moving_speed  calls=1 scripts=1 args={'1': 1}
- ui/script/menu/main/main_menu_information.lc main.p0 pc43: R[3]=integer(4)

### set_text_scroll_through_mode  calls=1 scripts=1 args={'1': 1}
- ui/script/menu/main/main_menu_information.lc main.p0 pc51: R[3]=boolean(true)

### stop_text_scroll_animation  calls=1 scripts=1 args={'0': 1}
- ui/script/menu/main/main_menu_information.lc main.p2 pc17: (no arguments)

### update_list_text  calls=1 scripts=1 args={'0': 1}
- ui/script/menu/chara_make/make_mii_special_actor.lc main.p5 pc1: (no arguments)

## 4b input-family methods: 37

| is_pressed | 110 | 27 | {'1': 110} | press |
| set_enable_input | 84 | 29 | {'1': 84} | input |
| get_decided_button_id | 68 | 36 | {'0': 68} | decide |
| get_virtual_input | 62 | 50 | {'0': 62} | input |
| is_pressing | 45 | 13 | {'1': 45} | press |
| is_cancel | 35 | 18 | {'0': 35} | cancel |
| is_cancelled | 27 | 21 | {'0': 27} | cancel |
| decide_button | 25 | 13 | {'1': 23, '2': 2} | decide |
| update_pointer_input | 19 | 4 | {'4': 19} | input |
| is_decide | 15 | 10 | {'0': 15} | decide |
| is_repeated | 12 | 6 | {'1': 12} | repeat |
| set_decide_on_trigger | 10 | 7 | {'2': 10} | trigger+decide |
| stop_pressed | 8 | 4 | {'1': 8} | press |
| special_input_is_downward | 7 | 7 | {'1': 7} | input |
| special_input_is_upward | 7 | 7 | {'1': 7} | input |
| press_cancel | 6 | 6 | {'0': 6} | press+cancel |
| set_repeat_frame | 5 | 5 | {'4': 5} | repeat |
| get_decided_item | 4 | 4 | {'0': 4} | decide |
| is_pressed_finished | 4 | 4 | {'0': 4} | press |
| is_released | 4 | 2 | {'1': 4} | release |
| play_pressed | 4 | 4 | {'1': 4} | press |
| set_enable_input_sort | 3 | 1 | {'1': 3} | input |
| set_no_wait_decide | 3 | 2 | {'1': 3} | decide |
| terminate_repeat | 3 | 3 | {'0': 3} | repeat |
| decide | 2 | 2 | {'0': 2} | decide |
| get_decided_id | 2 | 2 | {'0': 2} | decide |
| get_last_input_device_id | 2 | 2 | {'0': 2} | input |
| is_decided | 2 | 2 | {'0': 2} | decide |
| update_cancel | 2 | 2 | {'0': 2} | cancel |
| cancel | 1 | 1 | {'0': 1} | cancel |
| input_direction_is_upward | 1 | 1 | {'0': 1} | input |
| input_direction_is_zero | 1 | 1 | {'0': 1} | input |
| input_direction_is_zero_x | 1 | 1 | {'0': 1} | input |
| release | 1 | 1 | {'0': 1} | release |
| set_decide_se_label | 1 | 1 | {'1': 1} | decide |
| special_input_is_leftward | 1 | 1 | {'1': 1} | input |
| special_input_is_rightward | 1 | 1 | {'1': 1} | input |

## 4b input-family globals: 168

| name | lua reads | lua writes | string in main.bin | adrp+add refs | w3 value (if scanned) |
|---|---|---|---|---|---|
| BUTTON_BACK | 40 | 0 | 1 | 1 | 0 |
| CONTROLLER_FULL_KEY | 30 | 0 | 1 | 1 | 0 |
| BUTTON_ID_NONE | 29 | 0 | 1 | 4 | [-1, -1, -1] |
| BUTTON_FORM_TYPE_0 | 28 | 0 | 1 | 1 | 3 |
| INPUT_BUTTON_RIGHT | 18 | 0 | 1 | 1 | 3 |
| INPUT_BUTTON_LEFT | 16 | 0 | 1 | 1 | 2 |
| BUTTON_ID_BGM | 15 | 0 | 1 | 1 | 1 |
| BUTTON_ID_SE | 15 | 0 | 1 | 1 | 2 |
| BUTTON_ID_VOICE | 15 | 0 | 1 | 1 | 3 |
| VI_BUTTON_DECIDE | 15 | 0 | 1 | 1 | 4 |
| BUTTON_ID_SAVE | 14 | 0 | 1 | 2 | [300, 5] |
| BUTTON_ID_INIT | 13 | 0 | 1 | 10 | [0, 0, 0, 1, 1] |
| BUTTON_ID_PLAY_ALL | 13 | 0 | 1 | 1 | 5 |
| BUTTON_ID_FK_BUTTON_Y | 12 | 0 | 1 | 1 | 11 |
| BUTTON_ID_OK | 12 | 0 | 1 | 2 | [7, 7] |
| BUTTON_ID_JC_LEFT | 11 | 0 | 1 | 1 | 6 |
| BUTTON_TAB_SUB | 11 | 0 | 1 | 1 | 2 |
| BUTTON_ID_FULL_KEY_CON | 10 | 0 | 1 | 1 | 0 |
| BUTTON_ID_GC_CON | 10 | 0 | 1 | 1 | 2 |
| BUTTON_ID_JOY_CON | 10 | 0 | 1 | 4 | 1 |
| BUTTON_ID_CAMERA | 9 | 0 | 1 | 1 | 6 |
| BUTTON_ID_DASH_FIGHTER | 9 | 0 | 1 | 1 | 3 |
| BUTTON_ID_FK_BUTTON_A | 9 | 0 | 1 | 1 | 7 |
| BUTTON_ID_FK_STICK_R | 9 | 0 | 1 | 1 | 9 |
| BUTTON_ID_JC_RIGHT | 9 | 0 | 1 | 1 | 5 |
| BUTTON_ID_TEST | 9 | 0 | 1 | 1 | 200 |
| LIB_BUTTON_A | 9 | 0 | 1 | 1 | 32 |
| VI_BUTTON_DOWN | 9 | 0 | 1 | 1 | 1 |
| VI_BUTTON_UP | 9 | 0 | 1 | 1 | 0 |
| BUTTON_ID_EXIT_MENU | 8 | 0 | 1 | 1 | 6 |
| BUTTON_ID_PRIORITY | 8 | 0 | 1 | 1 | 3 |
| BUTTON_MUSIC_0 | 8 | 0 | 1 | 1 | 4 |
| INPUT_BGM_SELECT | 8 | 0 | 1 | 1 | 8 |
| INPUT_BGM_SELECTOR_TEST | 8 | 0 | 1 | 1 | 6 |
| INPUT_MY_MUSIC_SORT | 8 | 0 | 1 | 1 | 14 |
| INPUT_STAGE_TYPE | 8 | 0 | 1 | 1 | 7 |
| VI_BUTTON_CANCEL | 8 | 0 | 1 | 1 | 5 |
| BUTTON_ID_BODY_OPTION | 7 | 0 | 1 | 1 | 2 |
| BUTTON_ID_BODY_SIZE | 7 | 0 | 1 | 1 | - |
| BUTTON_ID_FK_BUTTON_B | 7 | 0 | 1 | 1 | - |
| BUTTON_ID_HEAD_OPTION | 7 | 0 | 1 | 1 | - |
| BUTTON_ID_INVISIBLE | 7 | 0 | 1 | 1 | - |
| BUTTON_ID_RADAR | 7 | 0 | 1 | 1 | - |
| BUTTON_ID_SOUND_TYPE | 7 | 0 | 1 | 1 | - |
| BUTTON_ID_SPEED | 7 | 0 | 1 | 1 | - |
| BUTTON_ID_STATE_OPTION | 7 | 0 | 1 | 1 | - |
| BUTTON_ID_WEIGHT | 7 | 0 | 1 | 1 | - |
| COMFRAME_FOOTERBUTTON_NONE | 7 | 0 | 1 | 1 | - |
| LIB_BUTTON_B | 7 | 0 | 1 | 1 | - |
| BUTTON_ID_FK_BUTTON_X | 6 | 0 | 1 | 1 | - |
| BUTTON_ID_FK_DOWN | 6 | 0 | 1 | 1 | - |
| BUTTON_ID_JC_DOWN | 6 | 0 | 1 | 1 | - |
| BUTTON_ID_JC_UP | 6 | 0 | 1 | 1 | - |
| BUTTON_ID_OPTION | 6 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_STICK_C | 5 | 0 | 1 | 1 | - |
| BUTTON_ID_JC_TRIGGER_LR | 5 | 0 | 1 | 1 | - |
| BUTTON_ID_JC_TRIGGER_ZLR | 5 | 0 | 1 | 1 | - |
| VI_BUTTON_EXTRA0 | 5 | 0 | 1 | 1 | - |
| BUTTON_FORM_TYPE_1 | 4 | 0 | 1 | 1 | - |
| BUTTON_FORM_TYPE_2 | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_DOUBLE | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_FK_SIDE | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_FK_TRIGGER_L | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_FK_TRIGGER_R | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_FK_TRIGGER_ZL | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_FK_TRIGGER_ZR | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_FK_UP | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_BUTTON_A | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_BUTTON_B | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_BUTTON_X | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_BUTTON_Y | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_DOWN | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_SIDE | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_TRIGGER_L | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_TRIGGER_R | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_TRIGGER_Z | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_GC_UP | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_JC_TRIGGER_SL | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_JC_TRIGGER_SR | 4 | 0 | 1 | 1 | - |
| BUTTON_ID_VIP | 4 | 0 | 1 | 1 | - |
| BUTTON_KIND_MAIN_NUM | 4 | 0 | 1 | 1 | - |
| BUTTON_MUSIC_1 | 4 | 0 | 1 | 1 | - |
| BUTTON_MUSIC_2 | 4 | 0 | 1 | 1 | - |
| BUTTON_TAB_NORMAL | 4 | 0 | 1 | 1 | - |
| INPUT_BUTTON_DOWN | 4 | 0 | 1 | 1 | 1 |
| INPUT_BUTTON_UP | 4 | 0 | 1 | 1 | 0 |
| INPUT_CANCEL | 4 | 0 | 1 | 1 | 5 |
| INPUT_FAVORITE | 4 | 0 | 1 | 2 | [7, 8] |
| INPUT_MY_MUSIC_INCIDENCE_BLOCK_DOWN | 4 | 0 | 1 | 1 | 13 |
| INPUT_MY_MUSIC_INCIDENCE_BLOCK_UP | 4 | 0 | 1 | 1 | 12 |
| INPUT_MY_MUSIC_INCIDENCE_DOWN | 4 | 0 | 1 | 1 | 11 |
| INPUT_MY_MUSIC_INCIDENCE_UP | 4 | 0 | 1 | 1 | 10 |
| INPUT_NEXT_SCENE | 4 | 0 | 1 | 1 | 6 |
| INPUT_TAB_CHANGE_L | 4 | 0 | 1 | 1 | 18 |
| INPUT_TAB_CHANGE_R | 4 | 0 | 1 | 1 | 24 |
| LAYOUTBUTTONSELECTOR_SELECTION_TYPE_POINTER | 4 | 0 | 1 | 1 | - |
| VI_BUTTON_EXTRA1 | 4 | 0 | 1 | 1 | - |
| VI_BUTTON_EXTRA2 | 4 | 0 | 1 | 1 | - |
| BUTTON_EX_LEFT | 3 | 0 | 1 | 3 | - |
| BUTTON_EX_RIGHT | 3 | 0 | 1 | 3 | - |
| BUTTON_ID_FIGHTER | 3 | 0 | 1 | 1 | - |
| BUTTON_ID_HANDICAP | 3 | 0 | 1 | 1 | - |
| BUTTON_ID_LEFT | 3 | 1 | 0 | 0 | - |
| BUTTON_ID_ONLINE | 3 | 0 | 1 | 1 | - |
| BUTTON_ID_RESET | 3 | 0 | 1 | 1 | - |
| BUTTON_ID_RIGHT | 3 | 1 | 0 | 0 | - |
| BUTTON_ID_RULE | 3 | 0 | 1 | 1 | - |
| BUTTON_ID_SINGLE | 3 | 0 | 1 | 1 | - |
| BUTTON_ID_STAGE | 3 | 0 | 1 | 1 | - |
| INPUT_SUB_PAGE_DOWN | 3 | 0 | 1 | 2 | 17 |
| INPUT_SUB_PAGE_UP | 3 | 0 | 1 | 1 | 16 |
| LAYOUTBUTTONSELECTOR_SELECTION_TYPE_GRID | 3 | 0 | 1 | 1 | - |
| LIB_BUTTON_LEFT | 3 | 0 | 1 | 1 | - |
| LIB_BUTTON_RIGHT | 3 | 0 | 1 | 1 | - |
| LIB_BUTTON_SLIDE_L_LEFT | 3 | 0 | 1 | 1 | - |
| LIB_BUTTON_SLIDE_L_RIGHT | 3 | 0 | 1 | 1 | - |
| LIB_BUTTON_Y | 3 | 0 | 1 | 1 | - |
| VI_BUTTON_EXTRA3 | 3 | 0 | 1 | 1 | - |
| BUTTON_ID_BUTTON | 2 | 0 | 1 | 1 | - |
| BUTTON_ID_ITEM | 2 | 0 | 1 | 1 | - |
| BUTTON_ID_LANGUAGE | 2 | 0 | 1 | 1 | - |
| BUTTON_ID_MELEE | 2 | 0 | 1 | 1 | - |
| BUTTON_ID_OTHER | 2 | 0 | 1 | 1 | - |
| BUTTON_ID_SOUND | 2 | 0 | 1 | 1 | - |
| BUTTON_ID_SPIRIT | 2 | 0 | 1 | 1 | - |
| BUTTON_ID_TECHNIQUE | 2 | 0 | 1 | 1 | - |
| BUTTON_ID_VIDEO | 2 | 0 | 1 | 1 | - |
| COMFRAME_FOOTERBUTTON_LARGE_100 | 2 | 0 | 1 | 1 | - |
| INPUT_COMMON_BUTTON | 2 | 0 | 1 | 1 | 6 |
| INPUT_OPEN_SORT_WINDOW | 2 | 0 | 1 | 3 | 6 |
| LIB_BUTTON_START | 2 | 0 | 1 | 1 | - |
| LIB_BUTTON_X | 2 | 0 | 1 | 1 | - |
| VI_BUTTON_EXTRA4 | 2 | 0 | 1 | 1 | - |
| VI_BUTTON_LEFT | 2 | 0 | 1 | 1 | - |
| VI_BUTTON_RIGHT | 2 | 0 | 1 | 1 | - |
| BODY_OPTION_BUTTON_NUM | 1 | 0 | 1 | 1 | - |
| BODY_SIZE_BUTTON_NUM | 1 | 0 | 1 | 1 | - |
| BUTTON_DELETE | 1 | 0 | 1 | 1 | - |
| BUTTON_HELP | 1 | 0 | 1 | 1 | - |
| BUTTON_ID_MODE | 1 | 0 | 1 | 1 | - |
| BUTTON_RESET | 1 | 0 | 1 | 1 | - |
| CAMERA_BUTTON_NUM | 1 | 0 | 1 | 1 | - |
| COMFRAME_FOOTERBUTTON_LARGE_80 | 1 | 0 | 1 | 1 | - |
| HEAD_OPTION_BUTTON_NUM | 1 | 0 | 1 | 1 | - |
| INPUT_HOWTO | 1 | 0 | 1 | 1 | 6 |
| INPUT_HOW_TO_PLAY | 1 | 0 | 1 | 1 | 6 |
| INPUT_MY_MUSIC_INIT | 1 | 0 | 1 | 1 | 15 |
| INPUT_NEXT | 1 | 0 | 1 | 1 | 8 |
| INPUT_OK | 1 | 0 | 1 | 1 | 6 |
| INPUT_OPEN_SUBMENU | 1 | 0 | 1 | 1 | 7 |
| INPUT_PREV | 1 | 0 | 1 | 1 | 7 |
| LIB_BUTTON_ANY_DIRECTION | 1 | 0 | 1 | 1 | - |
| LIB_BUTTON_ANY_SLIDE_L | 1 | 0 | 1 | 1 | - |
| LIB_BUTTON_L | 1 | 0 | 1 | 1 | - |
| LIB_BUTTON_LSL | 1 | 0 | 1 | 1 | - |
| LIB_BUTTON_LSR | 1 | 0 | 1 | 1 | - |
| LIB_BUTTON_MINUS | 1 | 0 | 1 | 1 | - |
| LIB_BUTTON_R | 1 | 0 | 1 | 1 | - |
| LIB_BUTTON_RSL | 1 | 0 | 1 | 1 | - |
| LIB_BUTTON_RSR | 1 | 0 | 1 | 1 | - |
| LIB_BUTTON_ZL | 1 | 0 | 1 | 1 | - |
| MSG_LABEL_FULL_KEY | 1 | 0 | 1 | 1 | - |
| POPUP_RESULT_BUTTON2 | 1 | 0 | 1 | 1 | - |
| SEQUENCE_OPTION_BUTTON | 1 | 0 | 1 | 1 | - |
| SPEED_BUTTON_NUM | 1 | 0 | 1 | 1 | - |
| STATE_OPTION_BUTTON_NUM | 1 | 0 | 1 | 1 | - |
| VI_BUTTON_EXTRA5 | 1 | 0 | 1 | 1 | - |
| WEIGHT_BUTTON_NUM | 1 | 0 | 1 | 1 | - |

## 4c visibility family: 67 methods

| play_animation | 406 | 42 | {'2': 406} |
| set_focus | 253 | 37 | {'0': 1, '1': 251, 'no-following-CALL': 1} |
| get_parts | 243 | 56 | {'0': 49, '1': 194} |
| set_enable | 198 | 38 | {'0': 1, '1': 197} |
| get_pane | 142 | 36 | {'1': 142} |
| select_button | 100 | 33 | {'1': 81, '2': 19} |
| set_enable_input | 84 | 29 | {'1': 84} |
| set_visible | 83 | 23 | {'1': 83} |
| play_animation_parts | 78 | 11 | {'2': 78} |
| get_selected_button_id | 76 | 21 | {'0': 76} |
| has_focus | 67 | 22 | {'0': 67} |
| set_selectable | 64 | 16 | {'1': 3, '2': 61} |
| stop_animation_at_end | 51 | 26 | {'1': 51} |
| select_item | 29 | 13 | {'1': 2, '2': 27} |
| is_animation_finished | 26 | 13 | {'1': 26} |
| stop_animation_frame | 25 | 11 | {'0': 2, '2': 23} |
| is_selectable | 21 | 5 | {'1': 21} |
| set_enable_my_music | 20 | 4 | {'1': 20} |
| visible_parts | 15 | 6 | {'2': 15} |
| clear_selection | 14 | 9 | {'0': 14} |
| get_selected_item | 13 | 4 | {'0': 13} |
| select_com_frame_actor | 12 | 2 | {'0': 12} |
| unselect | 11 | 10 | {'0': 11} |
| get_cursor_parts | 10 | 5 | {'0': 10} |
| get_animation | 9 | 5 | {'1': 9} |
| visible_pane | 9 | 2 | {'2': 9} |
| get_root_pane | 8 | 7 | {'0': 8} |
| play_animation_and_wait | 8 | 4 | {'2': 8} |
| set_parent_pane | 8 | 4 | {'1': 8} |
| set_select_item | 7 | 2 | {'0': 4, '1': 3} |
| is_selected_com_frame_actor | 6 | 2 | {'0': 6} |
| is_visible | 6 | 5 | {'0': 6} |
| select | 6 | 6 | {'0': 2, '2': 4} |
| unselect_com_frame_actor | 6 | 2 | {'0': 6} |
| set_position_pane | 5 | 2 | {'3': 5} |
| bring_to_front_parts | 4 | 4 | {'1': 4} |
| get_position_parts | 4 | 4 | {'1': 4} |
| get_scale_parts | 4 | 4 | {'0': 4} |
| is_enable | 4 | 4 | {'0': 4} |
| is_panel_touching | 4 | 2 | {'0': 4} |
| play_animation_in | 4 | 4 | {'0': 4} |
| play_animation_out | 4 | 4 | {'0': 4} |
| selector_setup_bind_func | 4 | 1 | {'4': 4} |
| set_scale_parts | 4 | 4 | {'3': 4} |
| set_visible_submenu_keyhelp | 4 | 1 | {'1': 4} |
| set_enable_input_sort | 3 | 1 | {'1': 3} |
| setup_selector | 3 | 3 | {'0': 3} |
| update_selector | 3 | 1 | {'0': 3} |
| get_animation_frame | 2 | 1 | {'1': 2} |
| get_position_pane | 2 | 1 | {'1': 2} |
| play_animation_properly | 2 | 2 | {'2': 2} |
| select_visible_arrow | 2 | 1 | {'1': 2} |
| set_select_id | 2 | 2 | {'1': 2} |
| set_text_border_enable | 2 | 1 | {'1': 2} |
| stop_animation | 2 | 2 | {'1': 2} |
| update_selector0 | 2 | 2 | {'0': 2} |
| update_selector1 | 2 | 2 | {'0': 2} |
| anim_update_01 | 1 | 1 | {'0': 1} |
| get_animation_table_function | 1 | 1 | {'0': 1} |
| get_group_panes | 1 | 1 | {'1': 1} |
| init_anim_01 | 1 | 1 | {'0': 1} |
| is_animation_finished_parts | 1 | 1 | {'2': 1} |
| is_visible_gsp_in_result | 1 | 1 | {'0': 1} |
| play_text_scroll_animation | 1 | 1 | {'0': 1} |
| set_back_enable | 1 | 1 | {'1': 1} |
| set_text_scroll_loop_enabled | 1 | 1 | {'1': 1} |
| stop_text_scroll_animation | 1 | 1 | {'0': 1} |

