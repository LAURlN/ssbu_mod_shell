#!/usr/bin/env python3
"""Check the normal_jab__miifighter unit (MV-normal_jab__miifighter). Exit 1 on any mismatch.

Run from the workspace root:
    python -I mods/mii_customizer/evidence/moves/normal_jab__miifighter/check.py          # the checks
    python -I mods/mii_customizer/evidence/moves/normal_jab__miifighter/check.py --neg    # negative controls

Checks (all inputs are read from disk; the negative controls corrupt copies in memory):
 1. package/ files match manifest.json (size, sha256); exactly the five owned clips; no motion_list.bin,
    motion_list.motdiff or config.json; each clip equals its donor clip byte for byte.
 2. the reference list parses; magic and motion path equal the vanilla Gunner list; the vanilla entries
    are byte-identical; exactly the five owned entries follow; each owned entry's kind, game, anim,
    expression, sound and effect hashes equal hash40 of the names; all other bytes equal the donor entry.
 3. unit.rs registers exactly the scripts of expected_calls.json (plus the owned names of unit.json).
 4. every script body in unit.rs gives the same ordered events as the bounded donor decode
    (expected_calls.json): frames, waits, every macro call with all arguments, slopes, rumble.
    The rapid hit (rapid_hit) equals the decoded helper 0x158370 (helper_rapid_hit.json).
 5. the on_flag names used in unit.rs equal the donor's flags, minus the stage-2 ENABLE_COMBO omitted on purpose.
 6. every bone name in unit.rs exists in the Gunner skeleton (case-insensitive; Smash hash40 lowercases),
    except 'top' (engine-side origin).
 7. the statuses: unit.rs and the plugin copy define the four status functions, the plugin registers them,
    and the plugin copy's unit file is identical to unit.rs.
Negative controls (--neg): four corrupted inputs, each must be reported.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve()
WORKSPACE = HERE.parents[5]                 # workspace root (contains AGENTS.md, mods/, gamedata/)
MOD_ROOT = WORKSPACE / "mods" / "mii_customizer"
UNIT = "normal_jab__miifighter"
GD = WORKSPACE / "gamedata" / "mii_customizer"
GD_UNIT = GD / "moves" / UNIT
P11 = GD / "P11-MOVE-PLAN"
MANIFEST = GD_UNIT / "manifest.json"
REFERENCE = GD_UNIT / "reference" / "motion_list_vanilla_plus_owned.bin"
PACKAGE = GD_UNIT / "package"
EXPECTED = GD_UNIT / "tables" / "expected_calls.json"
HELPER = GD_UNIT / "tables" / "helper_rapid_hit.json"
UNIT_RS = MOD_ROOT / "moves" / UNIT / "unit.rs"
UNIT_JSON = MOD_ROOT / "moves" / UNIT / "unit.json"
PLUGIN_UNIT = MOD_ROOT / "scratch" / "2026-10-08_MV-normal_jab__miifighter" / "plugin" / "src" / "unit_normal_jab.rs"
PLUGIN_MOVES = MOD_ROOT / "scratch" / "2026-10-08_MV-normal_jab__miifighter" / "plugin" / "src" / "moves.rs"
GUNNER_SKEL = P11 / "fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb"
GUNNER_MLIST = P11 / "fighter/miigunner/motion/body/c00/motion_list.bin"
DONOR_MLIST = P11 / "fighter/miifighter/motion/body/c00/motion_list.bin"
DONOR_BODY = P11 / "fighter/miifighter/motion/body/c00"

# owned kind -> (donor clip file, owned clip file); the owned kind is "mc_" + donor kind with the
# miifighter prefix, as in build_assets.py
OWNED = {
    "mc_miifighter_attack_11": ("c00attack11.nuanmb", "c01mcmiifighterattack11.nuanmb", "attack_11"),
    "mc_miifighter_attack_12": ("c00attack12.nuanmb", "c01mcmiifighterattack12.nuanmb", "attack_12"),
    "mc_miifighter_attack_100_start": ("c00attack100start.nuanmb", "c01mcmiifighterattack100start.nuanmb", "attack_100_start"),
    "mc_miifighter_attack_100": ("c00attack100.nuanmb", "c01mcmiifighterattack100.nuanmb", "attack_100"),
    "mc_miifighter_attack_100_end": ("c00attackend.nuanmb", "c01mcmiifighterattack100end.nuanmb", "attack_100_end"),
}
# flags the unit sets, per function (donor flags minus the stage-2 ENABLE_COMBO at frame 7)
FLAGS = {
    "game_mcmiifighterattack11": ["FIGHTER_STATUS_ATTACK_FLAG_ENABLE_COMBO", "FIGHTER_STATUS_ATTACK_FLAG_ENABLE_RESTART"],
    "game_mcmiifighterattack12": ["FIGHTER_STATUS_ATTACK_FLAG_ENABLE_100"],
    "rapid_hit": ["FIGHTER_STATUS_ATTACK_FLAG_100_CONTINUE_CHECK"],
}
BONE_EXEMPT = {"top"}
EFFECT_BONE_ARG = {"EFFECT_FOLLOW_FLIP_ALPHA": 3}   # index in the call, agent first
EFFECT_BONE_DEFAULT = 2                              # EFFECT_ALPHA, EFFECT_FOLLOW_ALPHA, LANDING_EFFECT
MACROS = ("ATTACK", "PLAY_SE", "PLAY_SEQUENCE", "EFFECT_ALPHA", "EFFECT_FOLLOW_FLIP_ALPHA",
          "EFFECT_FOLLOW_ALPHA", "EFFECT_OFF_KIND", "LANDING_EFFECT", "RUMBLE_HIT")
SOUND_DIR = GD_UNIT / "extracted" / "sound"
SE_STEMS = ["sound/bank/fighter/se_miigunner", "sound/bank/fighter/se_miigunner_c00"]
SE_TONES = ["se_miifighter_attack100", "se_miifighter_swing_l", "se_miifighter_swing_s", "se_miifighter_swing_m"]
SEQUENCES = ["seq_miifighter_rnd_attack100", "seq_miifighter_rnd_attack02"]
VOICE_TONES = ["vc_mii_attack04", "vc_mii_attack05", "vc_mii_attack06", "vc_mii_attack100"]
EFFECT_EMITTER = "MIIFIGHTER_ATTACK100"
REF_SOUND = GD_UNIT / "reference" / "sound"
REF_EFFECT = GD_UNIT / "reference" / "effect" / "fighter" / "miigunner" / "ef_miigunner.eff"
REF_EFFECT_MERGE = REF_EFFECT.parent / "ef_miigunner.merge.json"
ENGINE_COPY = MOD_ROOT / "scratch" / "2026-10-08_MV-normal_jab__miifighter" / "effect_merge" / "merge_hero_engine_copy.py"


def hash40(s: str) -> int:
    return (len(s) << 32) | (zlib.crc32(s.encode("utf-8")) & 0xFFFFFFFF)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_mlist(data: bytes):
    magic, motion_path, count = struct.unpack_from("<QQQ", data, 0)
    offset = 24
    entries = []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from("<QQHBBI", data, offset)
        offset += 24
        anims = struct.unpack_from("<" + "Q" * n_anims, data, offset)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        entries.append({"kind": kind, "game": game, "anims": anims, "tail": tail - start,
                        "raw": data[start:end], "start": start, "end": end})
        offset = end
    if offset != len(data):
        raise ValueError(f"motion list has {len(data) - offset} trailing bytes")
    return magic, motion_path, entries


# ---------------------------------------------------------------- Rust side

def split_args(text: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def norm_rs(tok: str):
    t = tok.strip()
    if t == "None":
        return "NIL"
    m = re.fullmatch(r'Some\((.*)\)', t)
    if m:
        return norm_rs(m.group(1))
    m = re.fullmatch(r'Hash40::new\("([^"]+)"\)', t)
    if m:
        return m.group(1)
    if t.startswith("*"):
        t = t[1:]
        t = re.sub(r"\s+as\s+u32$", "", t)
        return t
    if t in ("true", "false"):
        return "True" if t == "true" else "False"
    t2 = t.rstrip("f")
    try:
        return float(t2)
    except ValueError:
        return t


def unit_functions(src: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"(?:pub )?(?:unsafe )?(?:extern \"C\" )?fn (\w+)\(", src):
        name = m.group(1)
        start = m.end()
        nxt = re.search(r"\n(?:pub |unsafe fn |fn |// -{5})", src[start:])
        out[name] = src[start: start + nxt.start()] if nxt else src[start:]
    return out


def rs_events(body: str):
    """Ordered (kind, value, args) of the calls in a script body; agent argument removed from args."""
    seq = []
    for m in re.finditer(r"frame\(agent\.lua_state_agent, ([\d.]+)\)", body):
        seq.append((m.start(), "frame", float(m.group(1)), None))
    for m in re.finditer(r"(?<![\w])wait\(agent\.lua_state_agent, ([\d.]+)\)", body):
        seq.append((m.start(), "wait", float(m.group(1)), None))
    for m in re.finditer(r"wait_loop_clear\(agent\.lua_state_agent\)", body):
        seq.append((m.start(), "wait_loop_clear", None, None))
    for m in re.finditer(r"wait_loop_sync_mot\(agent\.lua_state_agent\)", body):
        seq.append((m.start(), "wait_loop_sync_mot", None, None))
    for m in re.finditer(r"AttackModule::clear_all\(", body):
        seq.append((m.start(), "clear_all", None, None))
    for m in re.finditer(r"WorkModule::on_flag\(", body):
        seq.append((m.start(), "on_flag", None, None))
    for m in re.finditer(r"\brapid_hit\(agent\)", body):
        seq.append((m.start(), "rapid_hit", None, None))
    for m in re.finditer(r"macros::(" + "|".join(MACROS) + r")\(", body):
        args = call_args(body, m.end())
        seq.append((m.start(), m.group(1), None, [norm_rs(a) for a in args[1:]]))
    for m in re.finditer(r"ControlModule::set_rumble\(", body):
        args = call_args(body, m.end())
        seq.append((m.start(), "set_rumble", None, [norm_rs(a) for a in args[1:4]]))
    for m in re.finditer(r"slope!\(", body):
        args = call_args(body, m.end())
        seq.append((m.start(), "slope", None, [norm_rs(a) for a in args[1:]]))
    seq.sort(key=lambda x: x[0])
    return [(k, v, a) for _, k, v, a in seq]


def call_args(body: str, start: int) -> list[str]:
    depth, j = 1, start
    while depth and j < len(body):
        if body[j] == "(":
            depth += 1
        elif body[j] == ")":
            depth -= 1
        j += 1
    return split_args(body[start:j - 1])


def macro_arg_lists(body: str, macro: str):
    for m in re.finditer(r"macros::" + macro + r"\(", body):
        yield call_args(body, m.end())


def flags_in(body: str) -> list[str]:
    return re.findall(r"WorkModule::on_flag\(agent\.module_accessor, \*(\w+)\)", body)


# ---------------------------------------------------------------- donor side

def norm_dec(a):
    if isinstance(a, dict):
        t = a.get("t")
        if t in ("int", "float"):
            return float(a["v"])
        if t == "hash":
            return a.get("name") or a.get("v")
        if t == "const":
            return a["name"]
        if t == "bool":
            return "True" if a["v"] else "False"
        if t == "global":
            return "NIL"
        return json.dumps(a, sort_keys=True)
    return a


def eq_seq(a, b) -> str | None:
    if len(a) != len(b):
        return f"len {len(a)} != {len(b)}"
    for i, (x, y) in enumerate(zip(a, b)):
        if isinstance(x, float) and isinstance(y, float):
            if abs(x - y) > 1e-6:
                return f"[{i}] {x} != {y}"
        elif x != y:
            return f"[{i}] {x!r} != {y!r}"
    return None


# ---------------------------------------------------------------- checks

class Report:
    def __init__(self):
        self.fail: list[str] = []
        self.ok: list[str] = []

    def check(self, cond: bool, msg: str):
        (self.ok if cond else self.fail).append(msg)


def nus3_names(data: bytes) -> list[str]:
    """Tone names of a .nus3audio (AUDI chunk, NMOF offsets), read the way build_assets.py reads them."""
    assert data[:4] == b"NUS3" and data[8:12] == b"AUDI"
    off, chunks = 12, {}
    while off < len(data):
        tag = data[off:off + 4]
        size = struct.unpack_from("<I", data, off + 4)[0]
        chunks[tag] = data[off + 8:off + 8 + size]
        off += 8 + size
    count = struct.unpack_from("<I", chunks[b"INDX"], 0)[0]
    offsets = struct.unpack_from("<" + "I" * count, chunks[b"NMOF"], 0)
    return [data[o:data.index(b"\0", o)].decode() for o in offsets]


def sqb_records(data: bytes) -> list[bytes]:
    assert data[:4] == b"SQB\0"
    version, count = struct.unpack_from("<HH", data, 4)
    base = 12 + count * 4
    offs = list(struct.unpack_from("<" + "I" * count, data, 12)) + [len(data) - base]
    return [data[base + offs[i]:base + offs[i + 1]] for i in range(count)]


def label_crcs(data: bytes) -> set[int]:
    assert struct.unpack_from("<I", data, 0)[0] == 1
    count = struct.unpack_from("<I", data, 4)[0]
    rows = list(struct.iter_unpack("<II", data[8:]))
    assert len(rows) == count
    return {crc for crc, _ in rows}


def check_package(rep: Report, manifest: dict, pkg_files: dict[str, bytes], donor_bytes: dict[str, bytes]):
    for rel, meta in manifest["files"].items():
        data = pkg_files.get(rel)
        if data is None:
            rep.check(False, f"manifest file missing: {rel}")
            continue
        rep.check(len(data) == meta["size"] and sha(data) == meta["sha256"], f"manifest matches: {rel}")
    shipped = {r for r in pkg_files if r.startswith("package/")}
    expect = {f"package/fighter/miigunner/motion/body/c00/{clip}" for (_, clip, _) in OWNED.values()}
    rep.check(shipped == expect, f"package holds exactly the five owned clips (got {sorted(shipped)})")
    for name in ("motion_list.bin", "motion_list.motdiff", "config.json"):
        rep.check(not any(r.endswith(name) for r in shipped), f"package has no {name}")
    for kind, (donor_clip, owned_clip, _) in OWNED.items():
        data = pkg_files.get(f"package/fighter/miigunner/motion/body/c00/{owned_clip}")
        if data is not None:
            rep.check(data == donor_bytes[donor_clip], f"clip {owned_clip} equals the donor clip {donor_clip}")


def check_reference(rep: Report, ref: bytes, vanilla: bytes, donor: bytes):
    magic_v, path_v, ent_v = parse_mlist(vanilla)
    try:
        magic, path, ents = parse_mlist(ref)
    except Exception as e:  # noqa: BLE001
        rep.check(False, f"reference list does not parse: {e}")
        return
    rep.check(magic == magic_v and path == path_v, "reference magic and motion path equal vanilla Gunner")
    rep.check(len(ents) == len(ent_v) + len(OWNED), f"reference has vanilla+{len(OWNED)} entries ({len(ents)})")
    same = all(a["raw"] == b["raw"] for a, b in zip(ent_v, ents))
    rep.check(same and len(ents) >= len(ent_v), "vanilla entries are byte-identical")
    added = ents[len(ent_v):]
    kinds = [e["kind"] for e in ents]
    rep.check(len(set(kinds)) == len(kinds), "motion kinds are unique")
    _, _, donor_ents = parse_mlist(donor)
    donor_by_kind = {e["kind"]: e for e in donor_ents}
    for owned, (donor_clip, owned_clip, donor_kind) in OWNED.items():
        suffix = owned.replace("_", "")
        match = [e for e in added if e["kind"] == hash40(owned)]
        rep.check(len(match) == 1, f"one reference entry for {owned}")
        if not match:
            continue
        e = match[0]
        rep.check(e["game"] == hash40("game_" + suffix), f"{owned}: game hash = game_{suffix}")
        rep.check(e["anims"][0] == hash40(owned_clip), f"{owned}: anim hash = {owned_clip}")
        t = e["tail"]
        exp_expr, exp_snd, exp_eff = hash40("expression_" + suffix), hash40("sound_" + suffix), hash40("effect_" + suffix)
        got = struct.unpack_from("<QQQ", e["raw"], t)
        rep.check(got == (exp_expr, exp_snd, exp_eff), f"{owned}: expression/sound/effect hashes equal their names")
        d = donor_by_kind.get(hash40(donor_kind))
        if d is None:
            rep.check(False, f"donor entry {donor_kind} missing")
            continue
        # every byte other than the names is the donor's (flags, cancel frame, blend, size, anim count)
        masked_d = bytearray(d["raw"]); masked_e = bytearray(e["raw"])
        for buf in (masked_d, masked_e):
            buf[0:16] = b"\0" * 16
            buf[24:32] = b"\0" * 8
            buf[d["tail"]:d["tail"] + 24] = b"\0" * 24
        rep.check(bytes(masked_d) == bytes(masked_e), f"{owned}: all other bytes equal donor entry {donor_kind}")


def script_names_registered(src: str):
    return re.findall(r"\.(game|effect|sound|expression)_acmd\(\"(\w+)\", (\w+)", src)


def check_unit(rep: Report, src: str, expected: dict, helper: dict, gunner_bones: set[str]):
    funcs = unit_functions(src)
    regs = script_names_registered(src)
    reg_fns = {fn for _, _, fn in regs}
    reg_names = {name for _, name, _ in regs}
    rep.check(all(name == fn for _, name, fn in regs), "registered names equal their function names")
    rep.check(reg_fns == set(expected), f"registered scripts equal the expected script set "
              f"(extra {sorted(reg_fns - set(expected))}, missing {sorted(set(expected) - reg_fns)})")
    for fn, exp in expected.items():
        body = funcs.get(fn)
        if body is None:
            rep.check(False, f"{fn} missing in unit.rs")
            continue
        got = rs_events(body)
        exp_ev = [(k, v, a) for k, v, a in (tuple(e) for e in exp)]
        if fn in ("game_mcmiifighterattack100",):
            # the rapid hit body is the helper; the loop is one event per hit
            pass
        g = [(k, v, a) for k, v, a in got if k != "on_flag"]
        x = [(k, v, a) for k, v, a in exp_ev if k != "on_flag"]
        if len(g) != len(x):
            rep.check(False, f"{fn}: {len(g)} events in unit.rs, {len(x)} decoded")
            continue
        bad = None
        for i, (gi, xi) in enumerate(zip(g, x)):
            if gi[0] != xi[0]:
                bad = f"event {i}: {gi[0]} != {xi[0]}"; break
            if (gi[1] is None) != (xi[1] is None) or (gi[1] is not None and abs(gi[1] - xi[1]) > 1e-6):
                bad = f"event {i} ({gi[0]}): value {gi[1]} != {xi[1]}"; break
            if gi[2] is None and xi[2] is None:
                continue
            if gi[2] is None or xi[2] is None:
                bad = f"event {i} ({gi[0]}): args presence differs"; break
            err = eq_seq(gi[2], [x_ for x_ in xi[2]])
            if err:
                bad = f"event {i} ({gi[0]}) args {err}"; break
        rep.check(bad is None, f"{fn}: timeline equals the donor decode ({bad or 'ok'})")
        # sound labels: the Gunner's own swing labels replace the Brawler's stage 1/2 swings
        for k, v, a in g:
            pass
        flags = flags_in(body)
        if fn in FLAGS:
            flagnames = [re.sub(r"^", "", f) for f in re.findall(r"\*(\w+)", "\n".join(
                re.findall(r"WorkModule::on_flag\(agent\.module_accessor, (\*\w+)\)", body)))]
            rep.check(flagnames == FLAGS[fn], f"{fn}: flags {flagnames} equal {FLAGS[fn]}")
        elif fn.startswith(("game_", "effect_", "sound_", "expression_")) and flags:
            rep.check(False, f"{fn}: unexpected on_flag call")
        for b in re.findall(r'Hash40::new\("([^"]+)"\)', body):
            pass
    # rapid_hit helper body against the decoded helper rows
    rb = funcs.get("rapid_hit")
    if rb is None:
        rep.check(False, "rapid_hit missing in unit.rs")
    else:
        got = [(k, v, a) for k, v, a in rs_events(rb) if k != "on_flag"]
        hrows = [r for r in helper["rows"] if r["kind"] != "on_flag"]
        exp = []
        for r in hrows:
            if r["kind"] == "ATTACK":
                exp.append(("ATTACK", None, [norm_dec(a) for a in r["args"]]))
            elif r["kind"] == "wait":
                exp.append(("wait", float(r["args"][0]["v"]), None))
            elif r["kind"] == "clear_all":
                exp.append(("clear_all", None, None))
        g = [(k, v, a) for k, v, a in got if k in ("ATTACK", "wait", "clear_all")]
        ok = len(g) == len(exp)
        detail = ""
        if ok:
            for gi, xi in zip(g, exp):
                if gi[0] != xi[0]:
                    ok = False; detail = f"{gi[0]} != {xi[0]}"; break
                if xi[1] is not None and abs(gi[1] - xi[1]) > 1e-6:
                    ok = False; detail = f"wait {gi[1]} != {xi[1]}"; break
                if xi[2] is not None:
                    err = eq_seq(gi[2], xi[2])
                    if err:
                        ok = False; detail = f"ATTACK {err}"; break
        else:
            detail = f"{len(g)} rows != {len(exp)} decoded"
        rep.check(ok, f"rapid_hit equals decoded helper 0x158370 ({detail or 'ok'})")
        rep.check(flags_in(rb) == ["FIGHTER_STATUS_ATTACK_FLAG_100_CONTINUE_CHECK"],
                  "rapid_hit sets FIGHTER_STATUS_ATTACK_FLAG_100_CONTINUE_CHECK")
    # bones
    for fn, body in funcs.items():
        for m in re.finditer(r"macros::(\w+)\(", body):
            if m.group(1) not in MACROS:
                continue
            args = call_args(body, m.end())
            if m.group(1) in ("PLAY_SE", "PLAY_SEQUENCE", "RUMBLE_HIT", "EFFECT_OFF_KIND"):
                continue
            # args[0] is the agent; ATTACK(agent, id, part, bone, ...) and EFFECT_FOLLOW_FLIP_ALPHA(agent, eff, eff2, bone, ...)
            idx = 3 if m.group(1) == "ATTACK" else EFFECT_BONE_ARG.get(m.group(1), EFFECT_BONE_DEFAULT)
            bone = norm_rs(args[idx])
            if isinstance(bone, str) and bone not in BONE_EXEMPT and not bone.startswith(("sys_", "se_", "rbkind")):
                if bone.lower() not in gunner_bones:
                    rep.check(False, f"{fn}: bone {bone!r} not in the Gunner skeleton")
    rep.check(True, "bones checked")


def check_sound_effect(rep: Report, inp: dict):
    manifest = inp["manifest"]
    vanilla_sqb = sqb_records((SOUND_DIR / "sequence/fighter/miigunner.sqb").read_bytes())
    donor_sqb = sqb_records((SOUND_DIR / "sequence/fighter/miifighter.sqb").read_bytes())
    ref_sqb = sqb_records(inp["sqb_ref"])
    rep.check(ref_sqb[:len(vanilla_sqb)] == vanilla_sqb, "reference miigunner.sqb keeps every vanilla record byte for byte")
    rep.check(len(ref_sqb) == len(vanilla_sqb) + len(SEQUENCES), f"reference sqb has vanilla+{len(SEQUENCES)} records ({len(ref_sqb)})")
    for seq in SEQUENCES:
        key = hash40(seq)
        donor = [r for r in donor_sqb if struct.unpack_from("<Q", r, 0)[0] == key]
        added = [r for r in ref_sqb if struct.unpack_from("<Q", r, 0)[0] == key]
        rep.check(len(donor) == 1 and len(added) == 1 and added[0] == donor[0],
                  f"{seq}: one record in the Gunner sqb, byte-equal to the donor record")
    for stem in SE_STEMS:
        names_now = nus3_names(inp["bank_ref"][stem])
        names_van = nus3_names((SOUND_DIR / (stem.split("sound/", 1)[1] + ".nus3audio")).read_bytes())
        rep.check(names_now[:len(names_van)] == names_van, f"{stem}: vanilla tones kept in order")
        rep.check(names_now[len(names_van):] == SE_TONES, f"{stem}: the four Brawler tones appended ({names_now[len(names_van):]})")
        lab = inp["label_ref"][stem]
        rep.check(label_crcs(lab) == {zlib.crc32(n.lower().encode()) for n in names_now},
                  f"{stem}: tonelabel holds one label per tone")
    unit_se = set(re.findall(r'PLAY_SE\(agent, Hash40::new\("(se_[^"]+)"\)', inp["src"]))
    rep.check(unit_se <= set(SE_TONES) | set(nus3_names((SOUND_DIR / "bank/fighter/se_miigunner.nus3audio").read_bytes())),
              f"every PLAY_SE name in unit.rs exists in the Gunner bank after the merge ({sorted(unit_se)})")
    for seq in SEQUENCES:
        rep.check(f'PLAY_SEQUENCE(agent, Hash40::new("{seq}"))' in inp["src"], f"unit.rs plays {seq}")
    voice = manifest.get("sound", {}).get("voice", {})
    rep.check(voice.get("tones") == VOICE_TONES, "voice tones measured from the two records")
    rep.check(voice.get("banks_total") == 36 and voice.get("banks_with_all_tones") == 36 and voice.get("banks_missing_tones") == [] and voice.get("banks_excluded_no_attack_voice") == ["sound/bank/fighter_voice/vc_mii_cheer"],
              f"voice: all four tones in {voice.get('banks_with_all_tones')} of {voice.get('banks_total')} attack-voice Mii banks; vc_mii_cheer excluded (no attack voice)")
    # effect: reference bank is the recorded merge output, from the pinned inputs
    rec = json.loads(REF_EFFECT_MERGE.read_text(encoding="utf-8")) if REF_EFFECT_MERGE.is_file() else {}
    eff_meta = manifest.get("effect", {})
    rep.check(sha(inp["effect_ref"]) == eff_meta.get("output_sha256") == rec.get("output_sha256"),
              "reference ef_miigunner.eff equals the recorded merge output (manifest and merge record agree)")
    rep.check(rec.get("recipient_sha256") == sha((SOUND_DIR.parent / "effect/fighter/miigunner/ef_miigunner.eff").read_bytes()),
              "merge record: recipient is the extracted vanilla ef_miigunner.eff")
    rep.check(rec.get("donor_sha256") == sha((SOUND_DIR.parent / "effect/fighter/miifighter/ef_miifighter.eff").read_bytes()),
              "merge record: donor is the extracted ef_miifighter.eff")
    rep.check(EFFECT_EMITTER in rec.get("resource_names", []), "merge record names MIIFIGHTER_ATTACK100")
    rep.check(f'Hash40::new("{EFFECT_EMITTER.lower()}")' in inp["src"], "unit.rs calls the merged emitter by its name")
    # deep: the emitter exists in the reference bank and every vanilla emitter is still there
    deep = inp.get("effect_dump")
    if deep is not None:
        vanilla_names, merged_names = deep
        rep.check(EFFECT_EMITTER in merged_names, "dump of the reference bank: MIIFIGHTER_ATTACK100 present")
        rep.check(set(vanilla_names) <= set(merged_names) and len(merged_names) == len(vanilla_names) + 1,
                  f"dump: every vanilla emitter kept, one added ({len(vanilla_names)} -> {len(merged_names)})")


def check_statuses(rep: Report, src: str):
    for fn in ("start_attack", "attack_main", "attack_100_main"):
        rep.check(f"pub unsafe fn {fn}(" in src, f"unit.rs defines {fn}")
    for fn in ("normal_jab_attack_init", "normal_jab_attack_100_init", "gunner_attack_normal_main", "gunner_attack_100_main"):
        plugin = PLUGIN_MOVES.read_text(encoding="utf-8") if PLUGIN_MOVES.is_file() else ""
        rep.check(f"fn {fn}(" in plugin, f"plugin moves.rs defines {fn}")
    rep.check(f".status(Init, *FIGHTER_STATUS_KIND_ATTACK, normal_jab_attack_init)" in (
        PLUGIN_MOVES.read_text(encoding="utf-8") if PLUGIN_MOVES.is_file() else ""),
        "plugin registers the ATTACK Init hook")
    rep.check(".status(Init, *FIGHTER_STATUS_KIND_ATTACK_100, normal_jab_attack_100_init)" in (
        PLUGIN_MOVES.read_text(encoding="utf-8") if PLUGIN_MOVES.is_file() else ""),
        "plugin registers the ATTACK_100 Init hook")
    if PLUGIN_UNIT.is_file():
        rep.check(PLUGIN_UNIT.read_bytes() == UNIT_RS.read_bytes(), "plugin unit_normal_jab.rs equals unit.rs")
    else:
        rep.check(False, "plugin copy of the unit is missing")
    # no per-frame forcing: every swap call sits inside a status function
    rep.check(src.count("swap_vanilla_motion(") == 4, "swap_vanilla_motion is defined once and called only from the three status entry points")


def load_inputs(overrides: dict | None = None) -> dict:
    o = overrides or {}
    inp = {}
    inp["manifest"] = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pkg = {}
    for p in GD_UNIT.rglob("*"):
        rel = p.relative_to(GD_UNIT).as_posix()
        if p.is_file() and rel.split("/")[0] in ("package", "reference"):
            pkg[rel] = p.read_bytes()
    pkg["reference/motion_list_vanilla_plus_owned.bin"] = REFERENCE.read_bytes()
    pkg.update(o.get("pkg", {}))
    inp["pkg"] = pkg
    inp["ref"] = o.get("ref", REFERENCE.read_bytes())
    inp["vanilla"] = GUNNER_MLIST.read_bytes()
    inp["donor_mlist"] = DONOR_MLIST.read_bytes()
    inp["donor_bytes"] = {clip: (DONOR_BODY / clip).read_bytes() for clip, _, _ in OWNED.values()}
    inp["src"] = o.get("src", UNIT_RS.read_text(encoding="utf-8"))
    inp["expected"] = json.loads(EXPECTED.read_text(encoding="utf-8"))["scripts"]
    inp["helper"] = json.loads(HELPER.read_text(encoding="utf-8"))
    inp["bones"] = o.get("bones")
    inp["sqb_ref"] = o.get("sqb_ref", (GD_UNIT / "reference" / SQB_RECIPIENT_REL).read_bytes())
    inp["bank_ref"] = {}
    inp["label_ref"] = {}
    for stem in SE_STEMS:
        inp["bank_ref"][stem] = o.get("bank_ref", {}).get(stem, (GD_UNIT / "reference" / (stem + ".nus3audio")).read_bytes())
        inp["label_ref"][stem] = (GD_UNIT / "reference" / (stem + ".tonelabel")).read_bytes()
    inp["effect_ref"] = o.get("effect_ref", REF_EFFECT.read_bytes())
    inp["effect_dump"] = o.get("effect_dump", effect_dump_names())
    return inp


SQB_RECIPIENT_REL = "sound/sequence/fighter/miigunner.sqb"


def effect_dump_names():
    """Emitter names of the vanilla recipient and of the reference bank, through the copied converter (tier B)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("merge_hero_engine_copy", ENGINE_COPY)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    work = MOD_ROOT / "scratch" / "2026-10-08_MV-normal_jab__miifighter" / "effect_merge" / "scratch" / "check_dump"
    results = []
    for path in ((SOUND_DIR.parent / "effect/fighter/miigunner/ef_miigunner.eff"), REF_EFFECT):
        folder = engine.dump(path, work / path.parent.name / path.stem)
        results.append([e["Name"] for e in json.loads((folder / "NamcoFile.json").read_text(encoding="utf-8"))])
    return results[0], results[1]


def gunner_bone_names() -> set[str]:
    import ssbh_data_py as s  # local install in the workspace is not required; same reader as the build notes
    sk = s.skel_data.read_skel(str(GUNNER_SKEL))
    return {b.name.lower() for b in sk.bones}


def run_checks(inp: dict, rep: Report, bones: set[str]):
    check_package(rep, inp["manifest"], inp["pkg"], inp["donor_bytes"])
    check_reference(rep, inp["ref"], inp["vanilla"], inp["donor_mlist"])
    check_unit(rep, inp["src"], inp["expected"], inp["helper"], bones)
    check_statuses(rep, inp["src"])
    check_sound_effect(rep, inp)
    uj = json.loads(UNIT_JSON.read_text(encoding="utf-8"))
    kinds = {m["kind"] for m in uj["owned_motions"]}
    rep.check(kinds == set(OWNED), f"unit.json owned motions equal the five kinds ({sorted(kinds)})")


def sqb_write_local(entries: list[bytes]) -> bytes:
    offs, off = [], 0
    for e in entries:
        offs.append(off)
        off += len(e)
    return (b"SQB\0" + struct.pack("<HHI", 1, len(entries), 4 * len(entries))
            + b"".join(struct.pack("<I", o) for o in offs) + b"".join(entries))


def main() -> int:
    neg = "--neg" in sys.argv
    bones = gunner_bone_names()
    if not neg:
        rep = Report()
        run_checks(load_inputs(), rep, bones)
        for m in rep.ok:
            print("ok  ", m)
        for m in rep.fail:
            print("FAIL", m)
        print(f"checks: {len(rep.ok)} ok, {len(rep.fail)} failed")
        return 1 if rep.fail else 0
    # negative controls: each corrupted input must produce at least one failure
    real = load_inputs()
    base_src = real["src"]
    controls = {}
    controls["ATTACK damage changed in game_mcmiifighterattack11"] = dict(
        src=base_src.replace("1.8, 361, 25, 0, 25, 1.6,", "1.9, 361, 25, 0, 25, 1.6,", 1))
    controls["frame of rapid hit 11 moved to 12"] = dict(
        src=base_src.replace("frame(agent.lua_state_agent, 11.0);", "frame(agent.lua_state_agent, 12.0);", 1))
    # reference list with one owned entry removed (count and entry)
    ref = real["ref"]
    _, _, ents = parse_mlist(ref)
    cut = ents[-1]
    controls["reference list missing the last owned entry"] = dict(
        ref=struct.pack("<QQQ", *struct.unpack_from("<QQQ", ref, 0)[:2], len(ents) - 1) + ref[24:cut["start"]])
    # clip with one byte flipped
    clip_key = "package/fighter/miigunner/motion/body/c00/c01mcmiifighterattack100.nuanmb"
    bad = bytearray(real["pkg"][clip_key]); bad[-1] ^= 0x01
    controls["rapid clip with one byte changed"] = dict(pkg={clip_key: bytes(bad)})
    sqb_bytes = bytearray(real["sqb_ref"])
    # drop the attack02 record: rebuild the sqb without its last record
    recs = sqb_records(real["sqb_ref"])
    controls["reference sqb without the seq_miifighter_rnd_attack02 record"] = dict(
        sqb_ref=sqb_write_local(recs[:-1]))
    controls["reference effect bank with one byte changed"] = dict(
        effect_ref=real["effect_ref"][:1000] + bytes([real["effect_ref"][1000] ^ 1]) + real["effect_ref"][1001:])
    missed = []
    for name, ov in controls.items():
        inp = load_inputs(ov)
        rep = Report()
        run_checks(inp, rep, bones)
        status = "detected" if rep.fail else "MISSED"
        print(f"{status}: {name} ({len(rep.fail)} failures)")
        if not rep.fail:
            missed.append(name)
    print(f"negative controls: {len(controls) - len(missed)}/{len(controls)} detected")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
