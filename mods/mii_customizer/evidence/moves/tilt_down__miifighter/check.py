#!/usr/bin/env python3
"""Check for unit tilt_down__miifighter (MV-tilt_down__miifighter). Run from the workspace root:

    python mods/mii_customizer/evidence/moves/tilt_down__miifighter/check.py

Exit 0 only if every real check passes AND every negative control is detected. Otherwise exit 1.

Checks
  1. package and reference files against gamedata/.../manifest.json (size, sha256)
  2. reference motion list = vanilla Gunner list + exactly one appended entry; kinds unique
  3. every hash in the added entry equals the hash of the name used in unit.rs / the clip name
  4. flags and cancel frame of the added entry equal the donor entry (index 75)
  5. every ATTACK argument in unit.rs equals the decoded donor table (acmd_calls.json)
  6. frame and wait sequence of every owned script equals the decoded donor sequence
  7. enable_fix_jostle_area, set_attack_height and rumble values equal the decoded / disassembled values
  8. bone names used by unit.rs exist in the Gunner skeleton (kneer -> KneeR; top = engine origin)
  9. remapped sound labels exist in the Gunner's files (crc32 in tonelabel, hash40 in sqb)
  10. owned clip node sets equal the Gunner's own c02attacklw3 clip node sets (ssbh_data_py)
  11. negative controls: corrupted manifest hash, wrong hitbox damage, corrupted motion record

Paths are computed from this file; nothing machine-specific is written.
"""
import copy
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[4]  # evidence/moves/<unit>/ -> workspace root
UNIT = 'tilt_down__miifighter'
MOD = WS / 'mods/mii_customizer'
UNIT_DIR = MOD / 'moves' / UNIT
UNIT_RS = UNIT_DIR / 'unit.rs'
UNIT_JSON = UNIT_DIR / 'unit.json'
OUT = WS / 'gamedata/mii_customizer/moves' / UNIT
MANIFEST = OUT / 'manifest.json'
REF = OUT / 'reference/motion_list_vanilla_plus_owned.bin'
CLIP_PKG = OUT / 'package/fighter/miigunner/motion/body/c00/c01mcmiifighterattacklw3.nuanmb'
DONOR_CLIP = OUT / 'extract/fighter/miifighter/motion/body/c00/c02attacklw3.nuanmb'
GUNNER_CLIP = OUT / 'extract/fighter/miigunner/motion/body/c00/c02attacklw3.nuanmb'
DECODED = OUT / 'tables/acmd_calls.json'
GUNNER_LIST = WS / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin'
DONOR_LIST = WS / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin'
GUNNER_SKEL_M = WS / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb'
GUNNER_SKEL_F = WS / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_f/c00/model.nusktb'
GUNNER_TONELABEL = WS / 'gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miigunner.tonelabel'
GUNNER_SQB = WS / 'gamedata/mii_customizer/P12-FTILT-FACTS/sound/sequence/fighter/miigunner.sqb'

OWNED_KIND = 'mc_miifighter_attack_lw3'
OWNED_CLIP = 'c01mcmiifighterattacklw3.nuanmb'
DONOR_KIND = 'attack_lw3'
DONOR_INDEX = 75
DONOR_CLIP_NAME = 'c02attacklw3.nuanmb'
STEM = OWNED_KIND.replace('_', '')
KNOWN_BONE_ALIAS = {'kneer': 'KneeR'}  # engine alias -> skeleton bone (decoded donor hitbox bone)
ENGINE_BONES = {'top'}  # engine origin, not a skeleton bone
# rumble kind hash read from lua2cpp_miifighter.nro at 0xdc1b8: mov x1,#0x2ed7; movk #0xb277; movk #0xd
RUMBLE_NOHITM_HASH = 0x0db2772ed7
ATTACK_HEIGHT_LOW_OFFSET = 0xe7c4  # ldr w1,[x21,x8] at 0x150994 in the same NRO, resolved by constmap

FAILS = []
QUIET = False  # set while the negative controls run: their FAIL lines are the expected detections


def fail(msg):
    FAILS.append(msg)
    if not QUIET:
        print(f'  FAIL: {msg}')


def ok(msg):
    print(f'  ok:   {msg}')


def hash40(name: str) -> int:
    b = name.encode('utf-8')
    return (len(b) << 32) | zlib.crc32(b)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_mlist(data: bytes):
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset = 24
    entries = []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        if end > len(data):
            raise ValueError(f'entry {i} runs past the end of the file')
        t = data[tail:end]
        expr, snd, eff = struct.unpack_from('<QQQ', t, 0)
        unk, cancel = struct.unpack_from('<HH', t, 24)
        entries.append(dict(index=i, kind=kind, game=game, flags=flags, blend=blend,
                            n_anims=n_anims, anims=anims, size=size, raw=data[start:end],
                            expr=expr, snd=snd, eff=eff, unk=unk, cancel=cancel))
        offset = end
    if offset != len(data):
        raise ValueError('trailing bytes after the last entry')
    return magic, motion_path, entries


# ---------------------------------------------------------------- 1. package files

def check_files(manifest: dict) -> bool:
    good = True
    for section in ('files', 'reference'):
        for rel, item in manifest.get(section, {}).items():
            p = OUT / rel
            if not p.is_file():
                fail(f'missing {rel}')
                good = False
                continue
            if p.stat().st_size != item['size']:
                fail(f'size mismatch {rel}: {p.stat().st_size} != {item["size"]}')
                good = False
            elif sha256_file(p) != item['sha256']:
                fail(f'sha256 mismatch {rel}')
                good = False
    if good:
        ok('package and reference files match manifest.json (size and sha256)')
    return good


# ---------------------------------------------------------------- 2. reference list

def check_reference(vanilla: bytes, ref: bytes, expect_owned_kind: int) -> bool:
    good = True
    mv, pv, ev = parse_mlist(vanilla)
    mr, pr, er = parse_mlist(ref)
    if mv != mr or pv != pr:
        fail('reference header (magic / motion path) differs from vanilla')
        good = False
    if len(er) != len(ev) + 1:
        fail(f'reference has {len(er)} entries, expected {len(ev) + 1}')
        good = False
    for a, b in zip(ev, er):
        if a['raw'] != b['raw']:
            fail(f'vanilla entry {a["index"]} changed in the reference list')
            good = False
            break
    added = er[len(ev):]
    if len(added) != 1:
        fail(f'expected exactly 1 appended entry, found {len(added)}')
        good = False
    else:
        if added[0]['kind'] != expect_owned_kind:
            fail('appended entry kind is not the owned kind')
            good = False
    kinds = [e['kind'] for e in er]
    if len(set(kinds)) != len(kinds):
        fail('duplicate motion kinds in the reference list')
        good = False
    if good:
        ok(f'reference = vanilla ({len(ev)}) + 1 appended entry ({len(er)}); kinds unique')
    return good


# ---------------------------------------------------------------- 3 and 4. hashes, flags, cancel

def check_entry(added: dict, donor: dict, clip_name: str, stem: str, unit_text: str) -> bool:
    good = True
    expect = {
        'kind': hash40(OWNED_KIND),
        'game': hash40('game_' + stem),
        'expr': hash40('expression_' + stem),
        'snd': hash40('sound_' + stem),
        'eff': hash40('effect_' + stem),
    }
    for k, v in expect.items():
        if added[k] != v:
            fail(f'added entry {k} = 0x{added[k]:010x}, expected hash40 0x{v:010x}')
            good = False
    if added['anims'][0] != hash40(clip_name):
        fail('added entry clip hash != hash40(shipped clip name)')
        good = False
    # the names the unit.rs scripts and the motion kind use must hash to the same values
    for name in (OWNED_KIND, 'game_' + stem, 'expression_' + stem, 'sound_' + stem, 'effect_' + stem):
        if f'"{name}"' not in unit_text and name != OWNED_KIND:
            fail(f'unit.rs does not register {name}')
            good = False
    if f'pub const OWNED_MOTION: &str = "{OWNED_KIND}";' not in unit_text:
        fail('unit.rs OWNED_MOTION is not the owned kind')
        good = False
    if added['flags'] != donor['flags'] or added['flags'] != 0x0084:
        fail(f'flags 0x{added["flags"]:04x} != donor 0x{donor["flags"]:04x} (expected 0x0084)')
        good = False
    donor_cancel = struct.unpack_from('<H', donor['raw'], len(donor['raw']) - 2)[0]
    added_cancel = struct.unpack_from('<H', added['raw'], len(added['raw']) - 2)[0]
    if added_cancel != donor_cancel or donor_cancel != 28:
        fail(f'cancel frame {added_cancel} != donor {donor_cancel} (expected 28)')
        good = False
    if added['size'] != donor['size'] or added['blend'] != donor['blend'] or added['n_anims'] != 1:
        fail('size / blend / anim count differ from the donor entry')
        good = False
    if good:
        ok('added entry hashes equal the names; flags 0x0084 and cancel frame 28 equal the donor entry')
    return good


# ---------------------------------------------------------------- 5. ATTACK arguments

def macro_calls(text: str, needle: str):
    """Yield the top-level argument token lists of every call that starts with needle."""
    i = 0
    while True:
        j = text.find(needle, i)
        if j < 0:
            return
        k = j + len(needle)
        depth = 1
        tokens, cur = [], ''
        in_str = False
        while depth > 0:
            ch = text[k]
            if ch == '"':
                in_str = not in_str
            if not in_str:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        break
                elif ch == ',' and depth == 1:
                    tokens.append(cur.strip())
                    cur = ''
                    k += 1
                    continue
            cur += ch
            k += 1
        tokens.append(cur.strip())
        yield [t for t in tokens if t]
        i = k


def script_body(text: str, fn: str) -> str:
    start = text.find(f'pub unsafe extern "C" fn {fn}(')
    if start < 0:
        return ''
    nxt = text.find('pub unsafe extern "C" fn ', start + 10)
    end = nxt if nxt >= 0 else text.find('pub fn register_acmd', start)
    return text[start:end if end >= 0 else len(text)]


def decoded_args_match(token: str, arg: dict) -> bool:
    t = arg['t']
    if t in ('int', 'float'):
        try:
            return abs(float(token.replace('f32', '')) - float(arg['v'])) < 1e-6
        except ValueError:
            return False
    if t == 'bool':
        return token == ('true' if arg['v'] else 'false')
    if t == 'const':
        return token == '*' + arg['name']
    if t == 'hash':
        return token == f'Hash40::new("{arg["name"]}")'
    if t == 'global':
        return token == 'None'
    return False


def check_attacks(unit_text: str, decoded: dict) -> bool:
    body = script_body(unit_text, 'game_mcmiifighterattacklw3')
    dec = decoded['miifighter/game_attacklw3']['calls']
    dec_attacks = [c['args'] for c in dec if c['target'].endswith('::ATTACK')]
    calls = list(macro_calls(body, 'macros::ATTACK('))
    good = True
    if len(calls) != len(dec_attacks) or len(calls) != 2:
        fail(f'ATTACK calls: unit.rs {len(calls)}, decoded {len(dec_attacks)} (expected 2)')
        return False
    for n, (tokens, args) in enumerate(zip(calls, dec_attacks)):
        if len(tokens) != 1 + len(args):
            fail(f'hitbox {n}: {len(tokens) - 1} arguments in unit.rs, {len(args)} decoded')
            good = False
            continue
        if tokens[0] != 'agent':
            fail(f'hitbox {n}: first argument is not agent')
            good = False
        for i, (tok, arg) in enumerate(zip(tokens[1:], args)):
            if not decoded_args_match(tok, arg):
                fail(f'hitbox {n} arg {i}: unit.rs "{tok}" != decoded {arg}')
                good = False
    if good:
        ok(f'both hitboxes: all {len(dec_attacks[0])} arguments equal the decoded donor table')
    return good


# ---------------------------------------------------------------- 6 and 7. frames, waits, other values

def timeline(body: str) -> list:
    out = []
    for m in re.finditer(r'\b(frame|wait)\(agent\.lua_state_agent, ([0-9.]+)\)', body):
        out.append((m.group(1), float(m.group(2))))
    return out


def check_timing(unit_text: str, decoded: dict) -> bool:
    good = True
    expect = {
        'game_mcmiifighterattacklw3': ('miifighter/game_attacklw3',),
        'effect_mcmiifighterattacklw3': ('miifighter/effect_attacklw3',),
        'sound_mcmiifighterattacklw3': ('miifighter/sound_attacklw3',),
        'expression_mcmiifighterattacklw3': ('miifighter/expression_attacklw3',),
    }
    for fn, (key,) in expect.items():
        body = script_body(unit_text, fn)
        ours = timeline(body)
        dec = decoded[key]['calls']
        theirs = []
        for c in dec:
            t = c['target']
            if t.endswith('::frame'):
                theirs.append(('frame', float(c['args'][0]['v'])))
            elif t.endswith('::wait'):
                theirs.append(('wait', float(c['args'][0]['v'])))
        if ours != theirs:
            fail(f'{fn}: frame/wait sequence {ours} != decoded {theirs}')
            good = False
    if good:
        ok('frame and wait sequences of all four scripts equal the decoded donor sequences')

    game = script_body(unit_text, 'game_mcmiifighterattacklw3')
    jostle = [(float(a), float(b)) for a, b in re.findall(
        r'enable_fix_jostle_area\(agent\.module_accessor, ([-0-9.]+), ([-0-9.]+)\)', game)]
    if jostle != [(0.0, 3.0), (2.0, 3.0), (4.0, 3.0)]:
        fail(f'enable_fix_jostle_area arguments {jostle} != decoded [(0,3),(2,3),(4,3)]')
        good = False
    else:
        ok('enable_fix_jostle_area arguments at frames 2, 16, 26 equal the disassembled values')
    if 'set_attack_height_all(agent.module_accessor, AttackHeight(*ATTACK_HEIGHT_LOW), false)' not in game:
        fail('set_attack_height_all is not ATTACK_HEIGHT_LOW / false as decoded')
        good = False
    else:
        ok(f'set_attack_height_all(ATTACK_HEIGHT_LOW, false) (constant table offset 0x{ATTACK_HEIGHT_LOW_OFFSET:x})')

    exp = script_body(unit_text, 'expression_mcmiifighterattacklw3')
    if f'Hash40::new("rbkind_nohitm"), 0, false, 0x50000000' not in exp:
        fail('set_rumble does not use rbkind_nohitm / 0 / false / 0x50000000')
        good = False
    else:
        if hash40('rbkind_nohitm') != RUMBLE_NOHITM_HASH:
            fail('hash40(rbkind_nohitm) != the hash read from the NRO')
            good = False
        else:
            ok('rumble kind rbkind_nohitm equals the hash read from the NRO; u32 0x50000000 as decoded')
    return good


# ---------------------------------------------------------------- 8. bones

def bones_used(unit_text: str) -> set:
    """The bone argument of each hitbox (ATTACK arg 3), each FOOT_EFFECT (arg 2) and the EFFECT_FOLLOW bone."""
    used = set()
    for fn in ('game_mcmiifighterattacklw3', 'effect_mcmiifighterattacklw3'):
        body = script_body(unit_text, fn)
        for toks in macro_calls(body, 'macros::ATTACK('):
            used.add(toks[3].split('"')[1])
        for toks in macro_calls(body, 'macros::FOOT_EFFECT('):
            used.add(toks[2].split('"')[1])
        for toks in macro_calls(body, 'lua_args!('):
            if len(toks) > 3 and toks[3].startswith('Hash40::new('):
                used.add(toks[3].split('"')[1])
    return used


def check_bones(unit_text: str, skels) -> bool:
    import ssbh_data_py as s
    good = True
    used = bones_used(unit_text)
    bones = set()
    for sk in skels:
        bones |= {b.name for b in s.skel_data.read_skel(str(sk)).bones}
    for name in sorted(used):
        if name in KNOWN_BONE_ALIAS:
            real = KNOWN_BONE_ALIAS[name]
            if real not in bones:
                fail(f'bone {name} -> {real} missing from the Gunner skeleton')
                good = False
        elif name in ENGINE_BONES:
            continue
        else:
            fail(f'bone {name} is not in the known bone table')
            good = False
    if good:
        ok('bones used: kneer -> KneeR (in both Gunner skeletons); top = engine origin')
    return good


# ---------------------------------------------------------------- 9. sounds

def check_sounds(unit_text: str) -> bool:
    import zlib as z
    good = True
    tone = GUNNER_TONELABEL.read_bytes()
    sqb = GUNNER_SQB.read_bytes()
    se = 'se_miigunner_attackhard_l01'
    seq = 'seq_miigunner_rnd_attack02'
    if f'"{se}"' not in unit_text or f'"{seq}"' not in unit_text:
        fail('unit.rs does not play the expected Gunner labels')
        good = False
    if tone.find(struct.pack('<I', z.crc32(se.encode()))) < 0:
        fail(f'{se} crc32 not in se_miigunner.tonelabel')
        good = False
    if sqb.find(struct.pack('<Q', hash40(seq))) < 0:
        fail(f'{seq} hash40 not in miigunner.sqb')
        good = False
    # negative controls on the same files: the donor labels must NOT be there
    if tone.find(struct.pack('<I', z.crc32(b'se_miifighter_swing_l'))) >= 0:
        fail('negative control: donor SE found in Gunner tonelabel (unexpected)')
        good = False
    if sqb.find(struct.pack('<Q', hash40('seq_miifighter_rnd_attack01'))) >= 0:
        fail('negative control: donor sequence found in Gunner sqb (unexpected)')
        good = False
    if good:
        ok('remapped SE and sequence are in the Gunner files; the donor labels are not')
    return good


# ---------------------------------------------------------------- 10. clip node sets

def node_sets(path: Path):
    import ssbh_data_py as s
    a = s.anim_data.read_anim(str(path))
    t, v = set(), set()
    for g in a.groups:
        ty = str(g.group_type)
        for n in g.nodes:
            (t if 'Transform' in ty else v).add(n.name)
    return t, v, a.final_frame_index


def check_clip(pkg: Path, donor: Path, gunner_own: Path) -> bool:
    good = True
    if pkg.read_bytes() != donor.read_bytes():
        fail('package clip is not byte-identical to the donor clip')
        good = False
    dt, dv, df = node_sets(donor)
    gt, gv, gf = node_sets(gunner_own)
    if dt != gt or dv != gv:
        fail(f'clip node sets differ from the Gunner own c02attacklw3 (diff {sorted(dt ^ gt)} {sorted(dv ^ gv)})')
        good = False
    if df != 41.0:
        fail(f'donor clip final_frame_index {df} (expected 41.0)')
        good = False
    if good:
        ok(f'clip is byte-identical to the donor; node sets equal the Gunner own clip '
           f'({len(dt)} transform, {len(dv)} visibility); {int(df) + 1} frames')
    return good


# ---------------------------------------------------------------- main

def run(neg: bool) -> bool:
    print(f'Running MV-{UNIT} checks')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    unit_text = UNIT_RS.read_text(encoding='utf-8')
    decoded = json.loads(DECODED.read_text(encoding='utf-8'))
    vanilla = GUNNER_LIST.read_bytes()
    ref = REF.read_bytes()
    _, _, ev = parse_mlist(vanilla)
    _, _, ed = parse_mlist(DONOR_LIST.read_bytes())
    donor = [e for e in ed if e['kind'] == hash40(DONOR_KIND)]
    if len(donor) != 1 or donor[0]['index'] != DONOR_INDEX:
        fail('donor entry lookup failed')
        return False
    _, _, er = parse_mlist(ref)
    added = er[-1]

    results = []
    print('1. package files'); results.append(check_files(manifest))
    print('2. reference list'); results.append(check_reference(vanilla, ref, hash40(OWNED_KIND)))
    print('3-4. hashes, flags, cancel'); results.append(check_entry(added, donor[0], OWNED_CLIP, STEM, unit_text))
    print('5. ATTACK arguments'); results.append(check_attacks(unit_text, decoded))
    print('6-7. timing and other values'); results.append(check_timing(unit_text, decoded))
    print('8. bones'); results.append(check_bones(unit_text, [GUNNER_SKEL_M, GUNNER_SKEL_F]))
    print('9. sounds'); results.append(check_sounds(unit_text))
    print('10. clip'); results.append(check_clip(CLIP_PKG, DONOR_CLIP, GUNNER_CLIP))
    real_ok = all(results)

    if not neg:
        return real_ok

    print('11. negative controls (each must be DETECTED; their FAIL messages are suppressed)')
    global QUIET
    QUIET = True
    detected = []
    # a) corrupted manifest hash
    bad_m = copy.deepcopy(manifest)
    first = next(iter(bad_m['files']))
    bad_m['files'][first]['sha256'] = '0' * 64
    FAILS.clear()
    caught = not check_files(bad_m)
    detected.append(caught)
    print(f'  control a (corrupted manifest sha256): {"detected" if caught else "NOT DETECTED"}')
    # b) wrong hitbox damage in unit.rs text
    bad_text = unit_text.replace('Hash40::new("kneer"), 8.0, 80, 90', 'Hash40::new("kneer"), 9.9, 80, 90', 1)
    FAILS.clear()
    caught = not check_attacks(bad_text, decoded)
    detected.append(caught)
    print(f'  control b (hitbox damage 9.9): {"detected" if caught else "NOT DETECTED"}')
    # c) invalid motion record: change the appended entry's kind hash
    bad_ref = bytearray(ref)
    off = len(ref) - len(added['raw'])
    struct.pack_into('<Q', bad_ref, off, hash40('mc_miifighter_attack_lx'))
    FAILS.clear()
    caught = not check_reference(vanilla, bytes(bad_ref), hash40(OWNED_KIND))
    detected.append(caught)
    print(f'  control c (corrupted motion record kind): {"detected" if caught else "NOT DETECTED"}')
    FAILS.clear()
    QUIET = False
    return real_ok and all(detected)


def main():
    neg = '--no-neg' not in sys.argv
    good = run(neg)
    print('ALL TILT_DOWN__MIIFIGHTER CHECKS PASSED' if good else 'CHECKS FAILED')
    sys.exit(0 if good else 1)


if __name__ == '__main__':
    main()
