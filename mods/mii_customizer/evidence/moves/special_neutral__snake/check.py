#!/usr/bin/env python3
"""Offline check of move unit MV-special_neutral__snake. Run from the workspace root:

    python -I mods/mii_customizer/evidence/moves/special_neutral__snake/check.py

Exit 0 when every check passes, 1 on the first group of mismatches. Tier B only: nothing here shows the
move in the game. What is compared:
  1. every generated file against manifest.json (size, sha256), every pinned input against its pin;
  2. the reference motion list: vanilla entries untouched, 29 added entries whose kind / script / clip hashes
     are hash40 of the names used in unit.rs, flags / blend / cancel equal to the donor entry;
  3. the clips: frame count equal to the donor clip, node set, partial hold clip, pin files byte-equal to donor;
  4. the scripts in unit.rs against the decode of the user's lua2cpp_snake.nro (tables/acmd_calls.json): frames
     and macro arguments; against the other mod's generated acmd.rs (rename only); Snake's params against vl.prc;
  5. the native facts the code relies on, read from main.bin and lua2cpp_item.nro (life() bytes and its single
     call site, the `haver` joint, the ear-close handler's constants, the BORN init that sends the event);
  6. sounds: the nine tones in both reference banks, samples equal to the donor's, nothing vanilla lost;
  7. the plugin copy: unit.rs identical, diff against the base limited to the wiring, every game import of the
     built NRO exported by main / lua2cpp_common;
  8. negative controls (a damaged cancel frame, a damaged life() word and a damaged frame must be caught).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import struct
import sys
import zlib
from pathlib import Path

WS = Path.cwd()
MOD = WS / 'mods/mii_customizer'
UNIT = 'special_neutral__snake'
G = WS / 'gamedata/mii_customizer/moves' / UNIT
UNIT_RS = MOD / 'moves' / UNIT / 'unit.rs'
PLUGIN = MOD / 'scratch/2026-10-08_MV-special_neutral__snake/plugin'
BASE = MOD / 'builds/.cache/plugin_base_0.10.0'
NRO = MOD / 'builds/.cache/MV-special_neutral__snake-target/aarch64-skyline-switch/release/libmii_customizer.nro'
MAIN = WS / 'gamedata/ssbu-13.0.4/main.bin'
MAIN_SHA = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
ITEM_NRO = G / 'prebuilt;/nro/release/lua2cpp_item.nro'
SNAKE_NRO = G / 'prebuilt;/nro/release/lua2cpp_snake.nro'
COMMON_NRO = WS / 'gamedata/mii_customizer/P14-SWORD-FACTS/prebuilt;/nro/release/lua2cpp_common.nro'
MAIN_SYMBOLS = WS / 'mods/ssbu_mod_new/dumps/decoded/main_symbols.json'
OTHER_ACMD = WS / 'mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/acmd.rs'

checks = 0
failures = []


def ok(cond, what):
    global checks
    checks += 1
    if not cond:
        failures.append(what)
    return bool(cond)


def h40(s):
    b = s.encode()
    return (len(b) << 32) | zlib.crc32(b)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_build():
    spec = importlib.util.spec_from_file_location('snake_build', MOD / 'moves' / UNIT / 'build_assets.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B = load_build()
unit_src = UNIT_RS.read_text(encoding='utf-8')
manifest = json.loads((G / 'manifest.json').read_text(encoding='utf-8'))


# ---------------------------------------------------------------- 1. manifest and pins
def check_manifest():
    for relp, info in manifest['files'].items():
        p = G / relp
        if not ok(p.is_file(), f'missing {relp}'):
            continue
        data = p.read_bytes()
        ok(len(data) == info['bytes'] and sha(data) == info['sha256'], f'{relp} differs from the manifest')
    on_disk = {p.relative_to(G).as_posix() for root in (G / 'package', G / 'reference') for p in root.rglob('*')
               if p.is_file()}
    ok(on_disk == set(manifest['files']), f'files not in the manifest: {sorted(on_disk ^ set(manifest["files"]))[:5]}')
    for relp, digest in B.PINS.items():
        ok(sha((G / relp).read_bytes()) == digest, f'pin mismatch {relp}')
    ok(sha(MAIN.read_bytes()) == MAIN_SHA, 'main.bin is not the 13.0.4 image')


# ---------------------------------------------------------------- 2. motion list
def unit_strings():
    return set(re.findall(r'"([a-z0-9_]+)"', unit_src))


def check_motion_list(damage_cancel=False):
    local = []
    vanilla = (G / B.GUNNER_MLIST).read_bytes()
    ref = bytearray((G / 'reference/motion_list_vanilla_plus_owned.bin').read_bytes())
    _, _, v_entries = B.parse_mlist(vanilla)
    _, _, r_entries = B.parse_mlist(bytes(ref))
    if damage_cancel:
        e = r_entries[len(v_entries)]
        start = bytes(ref).index(e['raw'])
        struct.pack_into('<H', ref, start + e['tail_offset'] + 26, 30)
        _, _, r_entries = B.parse_mlist(bytes(ref))
    local.append((len(r_entries) == len(v_entries) + 29, 'reference list is not vanilla + 29'))
    local.append(([e['raw'] for e in r_entries[:len(v_entries)]] == [e['raw'] for e in v_entries],
                  'a vanilla entry changed'))
    _, _, d_entries = B.parse_mlist((G / B.SNAKE_MLIST).read_bytes())
    donors = {e['kind']: e for e in d_entries}
    strings = unit_strings()
    registered = set(re.findall(r'agent\.(?:game|effect|sound|expression)_acmd\("(\w+)"', unit_src))
    motions_const = re.search(r'pub const MOTIONS: \[&str; 29\] = \[(.*?)\];', unit_src, re.S).group(1)
    motions_list = re.findall(r'"(\w+)"', motions_const)
    local.append((motions_list == [B.owned_kind(k) for k in B.KINDS], 'MOTIONS in unit.rs differs from the built kinds'))
    script_hashes = set()
    for kind, e in zip(B.KINDS, r_entries[len(v_entries):]):
        d = donors[h40(kind)]
        names = B.owned_scripts(kind)
        t = e['tail_offset']
        exp, snd, eff = struct.unpack_from('<QQQ', e['raw'], t)
        cancel = struct.unpack_from('<H', e['raw'], t + 26)[0]
        d_cancel = struct.unpack_from('<H', d['raw'], d['tail_offset'] + 26)[0]
        local.append((e['kind'] == h40(B.owned_kind(kind)) and B.owned_kind(kind) in strings, f'{kind}: kind hash/name'))
        local.append((e['anims'] == (h40(B.owned_clip(kind)),), f'{kind}: clip hash'))
        local.append(((e['game'], exp, snd, eff) == tuple(h40(names[c]) for c in ('game', 'expression', 'sound', 'effect')),
                      f'{kind}: script hashes'))
        local.append(((e['flags'], e['blend'], e['size'], cancel) == (d['flags'], d['blend'], d['size'], d_cancel),
                      f'{kind}: flags/blend/cancel differ from the donor entry'))
        local.append(((G / 'package' / B.GUNNER_BODY / B.owned_clip(kind)).is_file(), f'{kind}: clip file missing'))
        script_hashes |= {e['game'], exp, snd, eff}
        m = manifest['motion_list']['motions'][B.owned_kind(kind)]
        local.append((m['cancel_frame'] == d_cancel and int(m['kind_hash'], 16) == e['kind'], f'{kind}: manifest row'))
    local.append((all(h40(n) in script_hashes for n in registered), 'a registered script is not named by any entry'))
    local.append((len(registered) == 69, f'{len(registered)} registered scripts, expected 69'))
    # apply-motion on the reference itself must refuse (entries already present)
    try:
        B.apply_motion(bytes(ref))
        local.append((False, 'apply_motion accepted a list that already has the entries'))
    except AssertionError:
        local.append((True, ''))
    return local


# ---------------------------------------------------------------- 3. clips and pin
def check_clips():
    import ssbh_data_py as s
    skel = {b.name for b in s.skel_data.read_skel(str(G / B.GUNNER_SKEL)).bones}
    idle = s.anim_data.read_anim(str(G / B.GUNNER_IDLE))
    idle_nodes = [n.name for g in idle.groups if g.group_type.name == 'Transform' for n in g.nodes]
    for kind in B.KINDS:
        clip = s.anim_data.read_anim(str(G / 'package' / B.GUNNER_BODY / B.owned_clip(kind)))
        donor = s.anim_data.read_anim(str(G / B.SNAKE_BODY / (B.DONOR_CLIPS[kind] + '.nuanmb')))
        ok(clip.final_frame_index == donor.final_frame_index, f'{kind}: frame count differs from the donor clip')
        ok([g.group_type.name for g in clip.groups] == ['Transform', 'Visibility'], f'{kind}: groups')
        nodes = [n.name for n in clip.groups[0].nodes]
        d_nodes = {n.name for g in donor.groups if g.group_type.name == 'Transform' for n in g.nodes}
        if kind in B.PARTIAL_KINDS:
            ok(set(nodes) == {n for n in idle_nodes if n in d_nodes and n in skel} and 'Hip' not in nodes
               and 'Trans' not in nodes and 'LegL' not in nodes, f'{kind}: partial clip node set')
        else:
            ok(nodes == idle_nodes, f'{kind}: node set is not the Gunner idle set')
        moving = sum(1 for n in clip.groups[0].nodes if len(n.tracks[0].values) > 1)
        ok(moving >= 1 or donor.final_frame_index <= 1, f'{kind}: nothing moves')
    pin = manifest['pin']
    for slot in B.MII_SLOTS:
        for n in B.PIN_MODEL_FILES:
            ok((G / f'package/fighter/miigunner/model/mc_snake_pin/{slot}/{n}').read_bytes()
               == (G / B.PIN_MODEL / n).read_bytes(), f'pin model {slot}/{n}')
        for n in B.PIN_CLIPS:
            ok((G / f'package/fighter/miigunner/motion/mc_snake_pin/{slot}/{n}').read_bytes()
               == (G / B.PIN_MOTION / n).read_bytes(), f'pin clip {slot}/{n}')
        _, _, ents = B.parse_mlist((G / f'package/fighter/miigunner/motion/mc_snake_pin/{slot}/motion_list.bin').read_bytes())
        ok({e['kind'] for e in ents} == {h40(v) for v in B.PIN_KINDS.values()}, f'pin list kinds {slot}')
        ok({e['anims'][0] for e in ents} == {h40(n) for n in B.PIN_CLIPS}, f'pin list clips {slot}')
    for name in ('mc_snake_pin', 'mc_snake_pin_start', 'mc_snake_pin_air_start'):
        ok(f'"{name}"' in unit_src, f'unit.rs does not name {name}')
    ok(pin['file_count'] == 12 * 19, 'pin file count')
    cfg = manifest['config_needed_by_coordinator']['new-dir-files']
    listed = {p for files in cfg.values() for p in files}
    ok(listed == {k[len('package/'):] for k in manifest['files'] if k.startswith('package/')},
       'config additions do not list exactly the packaged files')


# ---------------------------------------------------------------- 4. scripts
def split_fns(text):
    out = {}
    for m in re.finditer(r'unsafe extern "C" fn (\w+)\(agent: &mut L2CAgentBase\) \{', text):
        end = text.find('\npub(super) ', m.end())
        out[m.group(1)] = text[m.end():end if end != -1 else len(text)]
    return out


MACROS = ('EFFECT', 'FOOT_EFFECT', 'LANDING_EFFECT', 'PLAY_SE', 'PLAY_STATUS', 'PLAY_LANDING_SE', 'FT_MOTION_RATE',
          'CORRECT')


def f32(x):
    return struct.unpack('<f', struct.pack('<f', float(x)))[0]


def rust_calls(body):
    calls = []
    for m in re.finditer(r'\b(' + '|'.join(MACROS) + r')\(agent(?:, )?(.*?)\);', body):
        args = []
        for a in [x.strip() for x in re.split(r',\s*(?![^()]*\))', m.group(2)) if x.strip()]:
            hm = re.fullmatch(r'Hash40::new\("(\w+)"\)', a)
            if hm:
                args.append(hm.group(1))
            elif a in ('true', 'false'):
                args.append(a == 'true')
            elif a.startswith('*'):
                args.append(a[1:])
            else:
                args.append(f32(a))
        calls.append((m.group(1), args))
    return calls


def decoded_calls(entry):
    calls = []
    for c in entry['calls']:
        if c['kind'] not in MACROS:
            continue
        args = []
        for a in c['args']:
            if a['t'] == 'hash':
                args.append(a.get('name') or a['v'])
            elif a['t'] == 'bool':
                args.append(bool(a['v']))
            elif a['t'] == 'const':
                args.append(a['name'])
            else:
                args.append(f32(a['v']))
        calls.append((c['kind'], args))
    return calls


def check_scripts(damage_frame=False):
    local = []
    acmd_src = unit_src.split('//@ACMD@')[1]
    if damage_frame:
        acmd_src = acmd_src.replace('frame(lua_state, 9.0);', 'frame(lua_state, 11.0);', 1)
    fns = split_fns(acmd_src)
    decode = json.loads((G / 'tables/acmd_calls.json').read_text(encoding='utf-8'))
    regs = [l.split('\t') for l in (G / 'tables/registrations.tsv').read_text(encoding='utf-8').splitlines()[1:]]
    wrapper_size = {}
    for r in regs:
        wrapper_size.setdefault(r[1], set()).add(r[5])
    compared = 0
    for key, entry in decode.items():
        script = entry['script']
        m = re.fullmatch(r'(game|effect|sound|expression)_(special(?:air)?n\w+)', script)
        if not m:
            continue
        # A 268-byte wrapper is an empty script (it calls no body); the old decoder attached a neighbour's body.
        if wrapper_size.get(script) != {'124'}:
            local.append((f'{m.group(1)}_mcsnake{m.group(2)}' not in fns or m.group(1) == 'expression',
                          f'{script}: donor script is empty but unit.rs has a body'))
            continue
        own = f'{m.group(1)}_mcsnake{m.group(2)}'
        if own not in fns:
            local.append((False, f'{own} missing in unit.rs'))
            continue
        d_frames = [float(c['args'][0]['v']) for c in entry['calls'] if c['kind'] == 'frame']
        r_frames = [float(x) for x in re.findall(r'frame\(lua_state, ([\d.]+)\)', fns[own])]
        local.append((d_frames == r_frames, f'{own}: frames {r_frames} vs donor {d_frames}'))
        local.append((decoded_calls(entry) == rust_calls(fns[own]), f'{own}: macro arguments differ from the decode'))
        compared += 1
    local.append((compared >= 18, f'only {compared} scripts compared with the decode'))
    # Article calls of the donor start script map to the helpers, at the donor's frames.
    start = fns['game_mcsnakespecialnstart']
    local.append((re.sub(r'\s+', ' ', start).count('super::pull(agent); super::pin::generate(agent); super::pin::visibility(boma, false);') == 1
                  and 'frame(lua_state, 9.0); if is_excute(agent) { super::pin::visibility(boma, true);' in re.sub(r'\s+', ' ', start),
                  'start script: pull / pin order'))
    for which, frame in (('lw', 9), ('m', 8), ('hi', 10)):
        for air in ('', 'air'):
            body = re.sub(r'\s+', ' ', fns[f'game_mcsnakespecial{air}nthrow{which}'])
            local.append((body.startswith(f' let lua_state = agent.lua_state_agent; let boma = agent.module_accessor; '
                                          f'frame(lua_state, {frame}.0); if super::holding(boma) {{ if is_excute(agent) {{ '
                                          f'super::release(agent); }} }}'), f'throw {air}{which}: release frame'))
    # Rename-only relation to the other mod's generated file (which covers the air and leg scripts too).
    other = OTHER_ACMD.read_text(encoding='utf-8').split('pub(super) fn install() {')[0]
    other_fns = {k.replace('pgwrsnake', 'mcsnake'): v for k, v in split_fns(other).items()}
    mine = split_fns(unit_src.split('//@ACMD@')[1].split('pub(super) fn register(')[0])
    local.append((set(other_fns) == set(mine), 'script set differs from the other mod'))
    for k in sorted(set(other_fns) & set(mine)):
        local.append((other_fns[k].strip() == mine[k].strip(), f'{k}: body differs from the other mod (beyond the name)'))
    return local


def check_params():
    sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/src/pgwr/tools'))
    import prc
    tree = prc.as_dict(prc.read(G / 'fighter/snake/param/vl.prc'))

    def first(key):
        tag, items = tree[h40(key)]
        return prc.as_dict(items[0])
    special = first('param_special_n')
    for key in ('throw_m_speed_x', 'throw_m_speed_y', 'throw_hi_speed_x', 'throw_hi_speed_y', 'throw_lw_speed_x',
                'throw_lw_speed_y', 'throw_hi_threshold', 'throw_lw_threshold', 'ear_close_distance'):
        m = re.search(rf'pub const {key.upper()}: f32 = ([-\d.]+)f32;', unit_src)
        ok(m and struct.pack('<f', float(m.group(1))) == struct.pack('<f', special[h40(key)][1]), f'param {key}')
    life = first('param_snakegrenade')[h40('life')][1]
    ok(re.search(rf'pub const GRENADE_LIFE: i32 = {life};', unit_src) and life == 150, 'param life')
    # throw selection: hi uses the hi speeds, etc.
    ok(re.search(r'special_n_throw_hi"\)\s*\|\| motion == hash40\("mc_snake_special_air_n_throw_hi"\) \{\s*'
                 r'\(params::THROW_HI_SPEED_X, params::THROW_HI_SPEED_Y', unit_src), 'release: hi speeds')
    ok(re.search(r'special_air_n_throw_lw"\) \{\s*\(params::THROW_LW_SPEED_X, params::THROW_LW_SPEED_Y', unit_src),
       'release: lw speeds')


# ---------------------------------------------------------------- 5. native facts
def words(data, off, n):
    return list(struct.unpack_from('<%dI' % n, data, off))


def mov_const(data, off, reg):
    """Value built by movz/movk on `reg` in the 6 instructions from off."""
    value = None
    for w in words(data, off, 6):
        if (w & 0x1f) != reg:
            continue
        if (w & 0x7f800000) == 0x52800000:
            value = ((w >> 5) & 0xffff) << (16 * ((w >> 21) & 3))
        elif (w & 0x7f800000) == 0x72800000 and value is not None:
            sh = 16 * ((w >> 21) & 3)
            value = (value & ~(0xffff << sh)) | (((w >> 5) & 0xffff) << sh)
    return value


def check_native(damage_life=False):
    local = []
    main = MAIN.read_bytes()
    life_words = [int(x, 16) for x in re.search(r'pub const LIFE_WORDS: \[u32; 6\] = \[(.*?)\];', unit_src).group(1).split(', ')]
    if damage_life:
        life_words[4] ^= 0x20
    off = int(re.search(r'pub const LIFE_OFFSET: usize = (0x[0-9a-f]+);', unit_src).group(1), 16)
    local.append((words(main, off, 6) == life_words, 'life() bytes differ from main.bin'))
    w0, w1 = words(main, off, 2)
    page = ((off >> 12) << 12) + ((((w0 >> 5) & 0x7ffff) << 2 | ((w0 >> 29) & 3)) << 12)
    slot = page + ((w1 >> 10) & 0xfff) * 8
    local.append((slot == int(re.search(r'pub const MANAGER_SLOT: usize = (0x[0-9a-f]+);', unit_src).group(1), 16),
                  'MANAGER_SLOT is not the adrp/ldr target of life()'))
    local.append((words(main, off + 8, 3) == [0xf943f108, 0xf9407908, 0xb9400100], 'life() chain offsets 0x7e0 / 0xf0'))
    # Snake's article init attaches the item to `haver`; the ear-close handler's constants.
    local.append((mov_const(main, 0x11b6c90, 2) == h40('haver'), 'article init joint is not haver'))
    local.append((mov_const(main, 0x11b6030, 10) == 0x248952aeca, 'bomb link event hash'))
    local.append((words(main, 0x11b6064, 1)[0] == 0x7107c01f, 'handler does not compare with 0x1f0'))   # cmp w0,#0x1f0
    local.append((mov_const(main, 0x11b60ac, 1) == h40('param_special_n')
                  and mov_const(main, 0x11b60dc, 2) == h40('ear_close_distance'), 'ear_close_distance read'))
    local.append((words(main, 0x11b6090, 1)[0] & 0xff00001f == 0x35000000, 'handler: status must be 0 (WAIT)'))
    # shoot callback: Snake's THROW id and the power read
    local.append((words(main, 0x11b6e04, 1)[0] == 0x7107bc1f, 'shoot callback does not compare with 0x1ef'))
    local.append((mov_const(main, 0x11b70b4, 1) == h40('power_special_n'), 'power_special_n read'))
    # item script: one call of life(), and the BORN init sends the link event
    item = ITEM_NRO.read_bytes()
    n = len(item) // 4
    iw = struct.unpack_from('<%dI' % n, item)

    def bl_sites(target):
        out = []
        for idx, w in enumerate(iw):
            if (w & 0xfc000000) == 0x94000000:
                o = w & 0x3ffffff
                if o & 0x2000000:
                    o -= 0x4000000
                if idx * 4 + o * 4 == target:
                    out.append(idx * 4)
        return out
    local.append((bl_sites(0x9efd20) == [0x7c921c], 'life() is not called from exactly one place in the item script'))
    local.append((bl_sites(0x9efd30) == [0x7ca300], 'send_bomb_link_event call site'))
    # Snake's game_specialnclose wrapper calls no script body (empty script).
    snake = SNAKE_NRO.read_bytes()
    sw = struct.unpack_from('<67I', snake, 0xdf390)
    local_bl = [w for i, w in enumerate(sw[:28]) if (w & 0xfc000000) == 0x94000000
                and 0xdf390 + i * 4 + (((w & 0x3ffffff) ^ 0x2000000) - 0x2000000) * 4 < 0x100000]
    local.append((not local_bl, 'game_specialnclose wrapper calls a body'))
    for const, text in (('FOREIGN_BRIDGE', 'first & 0xfc00_0000 == 0x1400_0000'), ('PULLING', '!PULLING.load(Ordering::Acquire) || chain_readable()')):
        local.append((text in unit_src, f'fuse logic changed ({const})'))
    return local


# ---------------------------------------------------------------- 6. sounds
def check_sound():
    donor = dict((n.lower(), d) for n, d in B.audio_read((G / (B.SE_DONOR_STEM + '.nus3audio')).read_bytes()))
    used = set(re.findall(r'"(se_snake_\w+)"', unit_src))
    ok(used <= set(B.SE_TONES), f'unit.rs plays a Snake tone that is not added: {sorted(used - set(B.SE_TONES))}')
    ok(set(B.SE_TONES) - used == {'se_snake_special_n04'}, 'only the item explosion tone may be unused by unit.rs')
    for stem in B.SE_RECIPIENT_STEMS:
        vanilla = B.audio_read((G / (stem + '.nus3audio')).read_bytes())
        ref_stem = G / 'reference' / stem
        merged, chunks, labels = B.read_bank(ref_stem)
        ok(merged[:len(vanilla)] == vanilla, f'{stem}: a vanilla tone changed')
        ok(len(merged) == len(vanilla) + 9, f'{stem}: tone count')
        names = [n for n, _ in merged]
        crcs = {crc: value >> 8 for crc, value in labels}
        for tone in B.SE_TONES:
            idx = crcs.get(zlib.crc32(tone.encode()))
            ok(idx is not None and names[idx].lower() == tone and merged[idx][1] == donor[tone],
               f'{stem}: {tone} does not resolve to the donor sample')
        ok(len(B.tones_read(dict(chunks)[b'TONE'])) == len(merged), f'{stem}: tone records')
    ok(manifest['sound']['sequence_records_needed'] == 0, 'sequence note')


# ---------------------------------------------------------------- 7. plugin copy
def nro_imports(data):
    mod0 = struct.unpack_from('<I', data, 4)[0]
    dyn = mod0 + struct.unpack_from('<I', data, mod0 + 4)[0]
    tags = {}
    i = dyn
    while True:
        t, v = struct.unpack_from('<qQ', data, i)
        i += 16
        if t == 0:
            break
        tags.setdefault(t, v)
    symtab, strtab = tags[6], tags[5]
    imports, exports = set(), set()
    k = 1
    while symtab + k * 24 < strtab:
        name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', data, symtab + k * 24)
        s = data[strtab + name:data.index(b'\0', strtab + name)].decode('latin1')
        (exports if shndx else imports).add(s)
        k += 1
    return imports, exports


def check_plugin():
    ok((PLUGIN / 'src/unit_special_neutral_snake.rs').read_bytes() == UNIT_RS.read_bytes(),
       'plugin copy of unit.rs differs from moves/special_neutral__snake/unit.rs')
    changed, added = [], []
    for p in sorted((PLUGIN / 'src').glob('*.rs')):
        b = BASE / 'src' / p.name
        if not b.is_file():
            added.append(p.name)
        elif b.read_bytes() != p.read_bytes():
            changed.append(p.name)
    ok(added == ['unit_special_neutral_snake.rs'], f'added files {added}')
    ok(changed == ['lib.rs', 'menu.rs', 'moves.rs'], f'changed files {changed}')
    ok((PLUGIN / 'Cargo.toml').read_bytes() == (BASE / 'Cargo.toml').read_bytes()
       and (PLUGIN / 'Cargo.lock').read_bytes() == (BASE / 'Cargo.lock').read_bytes(), 'Cargo files changed')
    for name, plus in (('lib.rs', 1), ('menu.rs', 1), ('moves.rs', None)):
        base_lines = (BASE / 'src' / name).read_text(encoding='utf-8').splitlines()
        new_lines = (PLUGIN / 'src' / name).read_text(encoding='utf-8').splitlines()
        if plus is not None:
            ok(len(new_lines) == len(base_lines) + plus, f'{name}: line delta')
        removed = [l for l in base_lines if l not in new_lines]
        ok(len(removed) <= 1, f'{name}: base lines removed: {removed[:3]}')
    moves = (PLUGIN / 'src/moves.rs').read_text(encoding='utf-8')
    for text in ('let chosen = mii_chose(fighter, crate::unit_special_neutral_snake::ENTRY);',
                 'original_status(Pre, fighter, *FIGHTER_STATUS_KIND_SPECIAL_N)(fighter)',
                 'original_status(Main, fighter, *FIGHTER_STATUS_KIND_SPECIAL_N)(fighter)',
                 'original_status(End, fighter, *FIGHTER_STATUS_KIND_SPECIAL_N)(fighter)',
                 'crate::unit_special_neutral_snake::prepare();',
                 'crate::unit_special_neutral_snake::register(&mut agent);'):
        ok(moves.count(text) == 1, f'moves.rs wiring: {text}')
    ok(moves.index('unit_special_neutral_snake::prepare()') < moves.index('let mut agent = Agent::new("miigunner")'),
       'prepare() must run before the agent is built')
    ok('fn mii_chose' not in unit_src and 'read_player' not in unit_src, 'unit.rs copies the saved-Mii lookup')
    if not ok(NRO.is_file(), 'plugin NRO not built'):
        return
    nro = NRO.read_bytes()
    newest = max(p.stat().st_mtime for p in (PLUGIN / 'src').glob('*.rs'))
    ok(NRO.stat().st_mtime >= newest, 'NRO is older than the plugin copy sources')
    for name in B.KINDS:
        ok(B.owned_kind(name).encode() in nro, f'NRO lacks the motion name {B.owned_kind(name)}')
    imports, _ = nro_imports(nro)
    main_syms = {s['name'] for s in json.loads(MAIN_SYMBOLS.read_text(encoding='utf-8'))}
    _, common_exports = nro_imports(COMMON_NRO.read_bytes())
    game = [s for s in imports if s.startswith('_ZN3app') or s.startswith('_ZN3lib9Singleton') or s.startswith('_ZN2nn4util')]
    lua = [s for s in imports if s.startswith('_ZN7lua2cpp')]
    ok(len(game) > 80 and len(lua) > 20, 'import scan found too little')
    missing = [s for s in game if s not in main_syms] + [s for s in lua if s not in common_exports and s not in main_syms]
    ok(not missing, f'imports the game does not export: {missing[:4]}')


def main():
    check_manifest()
    for cond, what in check_motion_list():
        ok(cond, what)
    check_clips()
    for cond, what in check_scripts():
        ok(cond, what)
    check_params()
    for cond, what in check_native():
        ok(cond, what)
    check_sound()
    check_plugin()
    # negative controls
    ok(any(not c for c, _ in check_motion_list(damage_cancel=True)), 'negative control: damaged cancel frame not caught')
    ok(any(not c for c, _ in check_native(damage_life=True)), 'negative control: damaged life() word not caught')
    ok(any(not c for c, _ in check_scripts(damage_frame=True)), 'negative control: damaged script frame not caught')
    if failures:
        print(f'FAIL: {len(failures)} of {checks} checks')
        for f in failures[:40]:
            print('  -', f)
        return 1
    print(f'PASS: {checks} checks (manifest, pins, motion list, clips, pin, scripts, params, native facts, sounds, '
          f'plugin copy, NRO imports, negative controls)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
