"""Build gamedata/mii_customizer/moves/normal_jab__miifighter/tables/expected_calls.json (scratch, 2026-10-08).

Bounds each donor script to its own function. The decoder's first-ret rule runs past the end of
game_attack100, sound_attack100, effect_attack100 and expression_attack100 into the next registered
function (addresses below). The rapid hit is the helper 0x158370 (macros::ATTACK with its own is_excute),
emitted here as one event 'rapid_hit'; its body is checked separately in check.py.
Manual events: ControlModule::set_rumble_impl arguments, read from the donor disassembly
(rbkind hash register, int, bool false, u32 0x50000000 = BATTLE_OBJECT_ID_INVALID).
Run from the workspace root: python -I mods/mii_customizer/scratch/2026-10-08_MV-normal_jab__miifighter/make_expected.py
"""
import json
from pathlib import Path

ACMD = Path("gamedata/mii_customizer/moves/normal_jab__miifighter/tables/acmd_calls.json")
OUT = Path("gamedata/mii_customizer/moves/normal_jab__miifighter/tables/expected_calls.json")
d = json.load(open(ACMD, encoding="utf-8"))
HELPER = "0x158370"
KEEP = {"wait_loop_clear", "wait_loop_sync_mot", "ATTACK", "PLAY_SE", "PLAY_SEQUENCE",
        "EFFECT_ALPHA", "EFFECT_FOLLOW_FLIP_ALPHA", "EFFECT_FOLLOW_ALPHA", "EFFECT_OFF_KIND",
        "LANDING_EFFECT", "RUMBLE_HIT", "slope"}
# donor script -> first address that belongs to another function
BOUND = {
    "miifighter/game_attack100": 0x158f20,
    "miifighter/sound_attack100": 0x17a790,
    "miifighter/effect_attack100": 0xa1470,
    "miifighter/expression_attack100": 0xde030,
}
# the Gunner keeps its own jab labels for the stage 1/2 swings (unit.json known_differences)
RENAME = {"se_miifighter_swing_s": "se_miigunner_swing_s_hand", "se_miifighter_swing_m": "se_miigunner_swing_m_hand"}


def v(a):
    t = a.get("t")
    if t in ("int", "float"):
        return float(a["v"])
    if t == "hash":
        return a.get("name") or a["v"]
    if t == "const":
        return a["name"]
    if t == "bool":
        return "True" if a["v"] else "False"
    if t == "global":
        return "NIL"
    return json.dumps(a, sort_keys=True)


def events(key, rows, bound=None, drop_flags_after_frame=None):
    out, frame = [], None
    for r in rows:
        if bound is not None and int(r["addr"], 16) >= bound:
            break
        k = r["kind"]
        if k == "frame":
            frame = float(r["args"][0]["v"])
            if frame == 0.0:
                continue   # frame(0) is the script start; no call of its own
            if drop_flags_after_frame is None or frame != drop_flags_after_frame:
                out.append(["frame", frame, None])
            continue
        if k == "wait":
            out.append(["wait", float(r["args"][0]["v"]), None])
            continue
        if k in ("wait_loop_clear", "wait_loop_sync_mot"):
            out.append([k, None, None])
            continue
        if k == "lua_bind":
            tgt = r["target"]
            if "AttackModule__clear_all" in tgt:
                out.append(["clear_all", None, None])
            elif "WorkModule__on_flag" in tgt:
                if drop_flags_after_frame is not None and frame == drop_flags_after_frame:
                    continue
                out.append(["on_flag", None, None])
            continue
        if k not in KEEP:
            continue
        args = [v(a) for a in r["args"]]
        out.append([k, None, args])
    return out


# Rapid loop frames: the donor hits call the helper at these frames (0x158b30 is the frame-17 hit at the loop head)
rapid_frames = [float(r["frame"]) for r in d["miifighter/game_attack100"]["calls"]
                if r.get("via_helper") == HELPER and r["frame"] is not None and int(r["addr"], 16) < 0x158f20]
rapid_frames.append(17.0)
assert rapid_frames == [1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0, 17.0], rapid_frames

expected = {}
game100 = []
for f in rapid_frames:
    game100.append(["frame", f, None])
    game100.append(["rapid_hit", None, None])
game100.append(["wait_loop_clear", None, None])
expected["game_mcmiifighterattack100"] = game100

# stage 2 ENABLE_COMBO (frame 7) is omitted on purpose; the flag count is checked in check.py
expected["game_mcmiifighterattack11"] = events("miifighter/game_attack11", d["miifighter/game_attack11"]["calls"])
expected["game_mcmiifighterattack12"] = events("miifighter/game_attack12", d["miifighter/game_attack12"]["calls"],
                                               drop_flags_after_frame=7.0)
expected["game_mcmiifighterattack100end"] = events("miifighter/game_attack100end", d["miifighter/game_attack100end"]["calls"])

pairs = {
    "effect_mcmiifighterattack11": "miifighter/effect_attack11",
    "effect_mcmiifighterattack12": "miifighter/effect_attack12",
    "effect_mcmiifighterattack100end": "miifighter/effect_attack100end",
    "sound_mcmiifighterattack11": "miifighter/sound_attack11",
    "sound_mcmiifighterattack12": "miifighter/sound_attack12",
    "sound_mcmiifighterattack100start": "miifighter/sound_attack100start",
    "sound_mcmiifighterattack100end": "miifighter/sound_attack100end",
    "expression_mcmiifighterattack100start": "miifighter/expression_attack100start",
    "expression_mcmiifighterattack100end": "miifighter/expression_attack100end",
    "expression_mcmiifighterattack11": "miifighter/expression_attack11",
    "expression_mcmiifighterattack12": "miifighter/expression_attack12",
    "effect_mcmiifighterattack100": "miifighter/effect_attack100",
    "sound_mcmiifighterattack100": "miifighter/sound_attack100",
    "expression_mcmiifighterattack100": "miifighter/expression_attack100",
}
for owned, key in pairs.items():
    expected[owned] = events(key, d[key]["calls"], BOUND.get(key))

# manual set_rumble_impl events, inserted right after the frame event they follow in the donor
RUMBLE = [
    ("expression_mcmiifighterattack11", 1.0, "rbkind_nohits", 3.0),
    ("expression_mcmiifighterattack12", 1.0, "rbkind_nohits", 0.0),
    ("expression_mcmiifighterattack100", 2.0, "rbkind_nohits", 4.0),
    ("expression_mcmiifighterattack100", 8.0, "rbkind_nohits", 4.0),
    ("expression_mcmiifighterattack100", 14.0, "rbkind_nohits", 4.0),
    ("expression_mcmiifighterattack100end", 2.0, "rbkind_nohitm", 0.0),
]
for script, frame, name, n in RUMBLE:
    ev = expected[script]
    idx = next(i + 1 for i, e in enumerate(ev) if e[0] == "frame" and e[1] == frame)
    ev.insert(idx, ["set_rumble", None, [name, n, "False"]])

# on_flag events carry no name in the decode; they are compared by count in check.py, so drop them here
for k in expected:
    expected[k] = [e for e in expected[k] if e[0] != "on_flag"]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"note": "bounded donor events, generated by scratch make_expected.py",
                           "scripts": expected}, indent=1) + "\n", encoding="utf-8")
print("scripts:", len(expected))
for k in sorted(expected):
    print(f"{k}: {len(expected[k])} events")
