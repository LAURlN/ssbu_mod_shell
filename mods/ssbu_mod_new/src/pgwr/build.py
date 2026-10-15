"""Build Pyra/G&W c06 Shadow Purple and c07 Golden Light assets.

Pyra c06/c07 receive themed G&W models. Mythra c06 retains Black & Pink Mythra,
and c07 receives ivory/gold textures, portraits and golden effects. One Slot
Effects isolates the c06/c07 banks and trails; c00-c05 keep vanilla effects.
The package includes its game-13.0.4 dependency. Gameplay overrides live in the
separate plugin crate; this script builds their model and motion assets.

Model files and clip files are written under Pyra's own file names, and the
materials are rewritten to point at the renamed textures. Pyra-only bones
(sword1, h_* helpers, ...) are grafted onto G&W's skeleton at Pyra's bind pose,
because her scripts attach hitboxes and effects to them.

The motion list is Mr. Game & Watch's own. Every G&W motion kind is copied whole
(clip names, flags, blend, cancel frames, script names) into eflame's
`motion_list.bin`, so a G&W move has the timing G&W gives it and G&W-only kinds
(the nine Judge numbers, his up-B open/close, and so on) exist under their own
names. Pyra-only kinds are kept, because the Pyra<->Mythra swap, her entry and the
specials that are not ported yet still need them, but they play G&W stand-in clips.

Clip *files*: G&W's clip file names are used as-is where eflame already has the same
name (301 of 322), and the other 20 are stored under spare eflame names and referenced
from the motion list through that alias. See ALIAS notes in build_motion().

0.9.0 - G&W's `normal_weapon` article. The stool, the manhole cover, the fishbowl,
the turtle and the spray are one article, and it is the first thing in this build
that needs a *directory* created rather than a file overwritten:
`fighter/eflame/model/normal_weapon/<slot>` and
`fighter/eflame/motion/normal_weapon/<slot>`, 16 + 12 files per slot, copied
verbatim. See the ARTICLE comment block below and
REPORT_0.9.0_ARTICLE_ASSETS.md. The article's visibility tracks select the prop and are preserved; the stool
grip transform uses the stock frame-8 spawn pose. The plugin half - registering the
article on eflame - is NOT built, because smashline's `clone_weapon` cannot reach
the installed plugin's article table from a mod NRO without a raw-offset hook that
the global plugin has already installed at the same address. That is the
hand-back condition in REPORT_0.9.0_ARTICLE_ASSETS.md Â§2.

0.8.0 - the file-addition experiment. One clip is deliberately taken out of that rule:
`d01specialsl.nuanmb` (G&W's `special_s_1_l`, Judge's held pose) is shipped under its
own G&W name, and that name exists in no eflame folder in the base game, so the build
now really does introduce a file name eflame has never had. It is declared in the mod's
new `config.json` under ARCropolis' `new-dir-files`, which is the supported route for
adding a file the game's own name-hash lookups cannot otherwise see. Whether that
route works is exactly what the next console run is for; everything else in this build
is unchanged, so nothing else depends on the answer. See PROBE notes in build_motion()
and build_config_json().

Param files that ship in the motion folder (`ik.prc`, `scharge.prc`, `update.prc`,
`flip.prc`) are G&W's own, and G&W's mesh-visibility groups are merged into eflame's
`expression_vl.prc` (see build_expression_vl()).

Param files that ship in the motion folder (`ik.prc`, `scharge.prc`, `update.prc`,
`flip.prc`) are G&W's own, and G&W's mesh-visibility groups are merged into eflame's
`expression_vl.prc` (see build_expression_vl()).

Sound banks. The ported moves play other fighters' sounds (G&W's swings and smashes,
Diddy's Monkey Flip, Chrom's jab), and `PLAY_SE` resolves against the banks the current
fighter loaded - so those names were silent on Pyra, and the generator used to substitute
`se_eflame_*` stand-ins. `tools/merge_donor_sound.py` instead appends each donor's real
tone records to Pyra's own c06/c07 banks. c00-c05 are untouched, so vanilla stays vanilla.
See that tool's docstring and `refs/sound/dump_requests.md` for what is still missing.

Run with a Python that can import the vendored ssbh_data_py (cp312):
    toolchains/py312/python.exe src/pgwr/build.py
"""

from pathlib import Path
import hashlib
import json
import os
import shutil
import struct
import sys
import time
import tomllib
import zlib
import xml.etree.ElementTree as ET

import ssbh_data_py as s

sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))

import build_hero_spin as hi3  # noqa: E402  (Mii Hi3 -> Mythra c06/c07, see its docstring)
import build_mythra_moves as mythra_moves  # noqa: E402  (Corrin U-Air, Luigi D-Throw -> Mythra c06/c07)
import build_cloud_fair as cloud_fair  # noqa: E402  (Cloud AttackAirF -> Pyra c06/c07)
import build_chrom_jab as chrom_jab  # noqa: E402  (Chrom jab animation; the blade is Pyra's esword)
import build_robot_dtilt as robot_dtilt  # noqa: E402  (R.O.B. AttackLw3 -> Pyra c06/c07 down tilt)
import build_snake_uptilt as snake_uptilt  # noqa: E402  (Snake AttackHi3 -> Pyra c06/c07 up tilt)
import build_littlemac_fsmash as littlemac_s4  # noqa: E402  (Little Mac AttackS4 -> Pyra c06/c07 forward smash)
import build_esword_pose as esword_pose  # noqa: E402  (Aegis sword visibility, see its docstring)
import build_monkey_flip as mflip  # noqa: E402  (Diddy Monkey Flip -> Pyra c06/c07 side-B)
import prc  # noqa: E402  (typed .prc reader/writer, see tools/prc.py)
import visibility_table as vis  # noqa: E402  (param_visibility_data_body reader)
import build_color_themes as themes  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import build_hero_neutral_b_assets as hero_n
import merge_hero_neutral_b_sound as hero_sound
import merge_hero_neutral_b_effects as hero_effects
import build_snake_neutral_b_assets as snake_n
import merge_snake_neutral_b_sound as snake_sound
import merge_donor_sound as donor_sound
import merge_robot_dtilt_sound as robot_sound
import merge_snake_uptilt_sound as snake_uptilt_sound
# Little Mac's effect bank for the forward smash's `littlemac_attack_line`. It
# lives in tools/ with the other merge steps because it copies a donor file and
# declares it in config.json; tools/ is already on sys.path above.
import build_littlemac_fsmash_effect as littlemac_s4_eff  # noqa: E402
import build_hero_side_b_assets as hero_s  # noqa: E402  (Hero side-B -> Mythra c06/c07, opt-in)
import merge_hero_side_b_effects as hero_s_effects  # noqa: E402

SNAKE_NEUTRAL_B = os.environ.get('PGWR_SNAKE_NEUTRAL_B') == '1'
# Opt-in like Snake: only a plugin built with Cargo feature `hero-side-b` uses these files.
HERO_SIDE_B = os.environ.get('PGWR_HERO_SIDE_B') == '1'
EXPORT = Path(os.environ.get('MGW_EXPORT', ROOT / 'dumps' / 'arc'))
SKINS_DIR = ROOT / 'refs/skins'
PINK_GW_DIR = SKINS_DIR / 'pink_g_w/Pink G&W'
MYTHRA_SKIN_DIR = SKINS_DIR / 'black_and_pink_mythra/mythra skin'
MOD_NAME = 'pyra_gamewatch_reskin'
VERSION = tomllib.loads((ROOT / 'src/pgwr/plugin/Cargo.toml').read_text())['package']['version']
PACKAGE = Path(os.environ.get('MGW_PACKAGE', ROOT / 'builds' / 'pgwr' / VERSION))
MOD = PACKAGE / 'ultimate' / 'mods' / MOD_NAME
COSTUMES = {'c06': 'c06', 'c07': 'c07'}  # Pyra slot -> G&W source slot


def safe_rmtree(path, max_retries=10, delay=0.5):
    """Remove `path`, retrying the failures Windows throws while something still holds it.

    Catching only `PermissionError` was not enough: a wipe on 2026-09-30 died with
    `[WinError 145] The directory is not empty` part-way through the package, leaving
    a half-deleted tree behind. That is an `OSError` (as is `PermissionError`), and it
    is transient - Defender or the indexer letting go - so retry the whole call rather
    than the individual entry.
    """
    for i in range(max_retries):
        try:
            if path.exists():
                shutil.rmtree(path)
            return
        except OSError:
            if i == max_retries - 1:
                raise
            time.sleep(delay)

MODEL_FILES = ['model.numdlb', 'model.numshb', 'model.numshexb', 'model.nuhlpb',
               'model.xmb', 'model.nusrcmdlb']
MATERIAL_FILES = ['model.numatb', 'dark_model.numatb', 'light_model.numatb',
                  'metamon_model.numatb']

# Pyra motion kinds with no G&W equivalent: first candidate G&W has wins.
# Longest/most specific prefixes must come first, because source_for() returns on
# the first prefix that matches the motion's name.
FALLBACKS = [
    # Pyra's jab is a three-status chain with three motions; G&W has one jab motion
    # plus a rapid-fire follow-up. attack_12/13 replay attack_11, and Pyra's
    # attack_100_start is the wind-up for her rapid, which G&W does not have.
    ('attack_100_start', ['attack_100']),
    ('attack_1', ['attack_11']),
    ('attack_100', ['attack_100', 'attack_11']),
    ('special_air_n', ['special_air_n']),
    ('special_n', ['special_n']),
    ('special_air_s', ['special_air_s_1']),
    ('special_s', ['special_s_1']),
    ('special_air_hi', ['special_air_hi']),
    ('special_hi', ['special_hi']),
    ('special_air_lw_in', ['special_air_lw_start']),
    ('special_air_lw_out', ['special_air_lw_end']),
    ('special_lw_in', ['special_lw_start']),
    ('special_lw_out', ['special_lw_end']),
    ('final_air', ['final_air_start']),
    ('final', ['final_start']),
]

def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


# G&W clip files this build ships under their own G&W name, as genuinely new
# files, for the file-addition experiment. See build_motion()'s PROBE notes.
#
# `d01specialsl.nuanmb` is G&W's `special_s_1_l`: the held half of Judge's side
# special. It is the right probe because the alias it replaces holds byte-identical
# content, so the test isolates the *name lookup* and nothing else, and because
# `judge.rs` already plays that motion kind from a custom status on ground side-B,
# so the probe needs no new status, no new input and no new button.
PROBE_FILES = ['d01specialsl.nuanmb']


# G&W's `normal_weapon` article - the stool, the manhole cover, the fishbowl, the
# turtle and the spray. This is the one article that owns the props the user is
# missing, and it is the last of the nine G&W articles to need any work: the
# other four (rescue, parachute, panel, oil) belong to the specials, which are
# later work.
#
# # Why the whole tree is new
#
# An article is addressed by two directories that the base game does not have
# for `eflame`: `fighter/eflame/model/normal_weapon/<slot>` and
# `fighter/eflame/motion/normal_weapon/<slot>`. Every other article in this
# build replaced a file that already existed, so this is the first thing here
# that needs a *directory* created rather than a file overwritten.
#
# # Why that is no longer the open risk it was
#
# `HANDOFF_ARTICLE_SEARCH.md` Â§6 and Â§11 called `new-dir-infos` "untested" and
# "the cheapest possible probe". It is no longer untested: the working clone
# pack in `src/mgw_standalone/` ships a `config.json` that drives
# `new-dir-infos`, `new-dir-infos-base` and `new-dir-files` for whole new
# fighter trees (`fighter/mgw_pyra/...`, `fighter/mgw_mythra/...`), and its
# Watch Probe loaded and ran on hardware. That is this ARCropolis build, this
# game version and this console, so the directory route is proven and the
# separate probe for it is not needed. See build_config_json() for how the
# shape was copied.
#
# Article visibility selects each prop and must stay donor-authored. Files are
# copied and checked byte-for-byte before the c06/c07 stool grip correction.
# Have is held at the stock frame-8 spawn pose; complete_visibility() remains body-only.
#
# # The names, and why almost none of them are new
#
# Nine of the ten clips are names `eflame` already has - they are G&W's *body*
# versions of the same moves, which live in `motion/body/<slot>`. They are not
# a collision, because these copies sit in a different directory from the ones
# the body's motion list names. Only `j01appeallw` (the down taunt) is a file
# name no `eflame` folder has, and the down taunt is not what the first console
# test asks for. Every model file is a standard name (`model.numdlb`,
# `model.numshb`, the `.nutexb` textures), so this tree is overwhelmingly
# "standard file names in new directories" - the shape the working clone pack
# demonstrates - rather than the "new file name" shape 0.8.0's probe tests.
ARTICLE = 'normal_weapon'
# 0.11.0: the article's files ship for every Pyra slot, c00-c07.
#
# smashline's clone_weapon adds the article to eflame's article table, and that
# table belongs to the fighter kind, not to a colour: vanilla Pyra c00-c05 carry the
# entry too. The engine loads an article's model while it initialises the fighter
# (Space Bunny's crash 01790691291 was a null read in `fighter_initialize_object_data`
# while loading this article's model), so a slot without the files is a slot that
# can crash at match start. Vanilla slots never *spawn* the article - only the
# c06/c07 scripts do - so for them these files are loaded and never shown.
#
# Measured, correcting an older comment that said the donor's eight
# normal_weapon folders were byte-identical to each other: the *motion* folders
# are (all seven compare equal to c00), the *model* folders are not - every
# colour carries its own three .nutexb textures. What is uniform is the set of
# file *names*, which is the only thing this table encodes, and that is why one
# list covers all eight slots here.
ARTICLE_SLOTS = {f'c0{i}': f'c0{i}' for i in range(8)}
ARTICLE_MODEL_FILES = [
    'model.numdlb', 'model.numshb', 'model.numshexb', 'model.nuhlpb',
    'model.nusrcmdlb', 'model.nusktb', 'model.xmb',
    'model.numatb', 'dark_model.numatb', 'light_model.numatb',
    'metamon_model.numatb',
    'black_ha_col.nutexb', 'gray_ha_col.nutexb', 'grayb_ha_col.nutexb',
    'gray_tes_001_col_1.nutexb', 'gw_nor.nutexb',
]
ARTICLE_MOTION_FILES = [
    'motion_list.bin', 'update.prc',
    'c00attack11.nuanmb', 'c00attack100.nuanmb', 'c00attackend.nuanmb',
    'c01attacks3s.nuanmb', 'c02attacklw3.nuanmb',
    'c05attackairn.nuanmb', 'c05landingairn.nuanmb',
    'c05attackairb.nuanmb', 'c05landingairb.nuanmb',
    'j01appeallw.nuanmb',
]

# 0.12.0: `breath`, the up-air projectile, registered on eflame as a second
# clone by plugin/src/article.rs. Same shape as normal_weapon - a weapon article
# with its own model, its own skeleton and its own motion_list.bin, whose only
# clip is `c05attackairhi`.
#
# # Why the file list is per-slot
#
# normal_weapon has the same sixteen names in all eight donor folders, so one
# list covers every slot. breath does not: `model.nuanmb` is present in the
# donor's c00, c01, c02 and c06 and absent from c03, c04, c05 and c07, and every
# slot's three .nutexb textures differ from the others. Both facts are measured
# (`diff -r -q` over the donor's model/breath/c0*), and both are the donor's own
# layout rather than a defect, so each slot is listed as the donor actually has
# it. Copying c00 into c07 instead would ship G&W's black breath textures under
# Pyra's c07 and a `model.nuanmb` that slot has never had.
#
# The motion list has no such variation - all eight donor folders hold the same
# three files and compare byte-equal to c00 - so it is one list.
BREATH_MODEL_CORE = [
    'model.numdlb', 'model.numshb', 'model.numshexb', 'model.nuhlpb',
    'model.nusrcmdlb', 'model.nusktb', 'model.xmb',
    'model.numatb', 'dark_model.numatb', 'light_model.numatb',
    'metamon_model.numatb',
    'black_ha_col.nutexb', 'gray_ha_col.nutexb', 'grayb_ha_col.nutexb',
    'gw_nor.nutexb',
]
BREATH_MODEL_EXTRA = {
    'c00': ['model.nuanmb'], 'c01': ['model.nuanmb'],
    'c02': ['model.nuanmb'], 'c06': ['model.nuanmb'],
}
BREATH_MODEL_FILES = {slot: BREATH_MODEL_CORE + BREATH_MODEL_EXTRA.get(slot, [])
                      for slot in ARTICLE_SLOTS.values()}
BREATH_MOTION_FILES = ['motion_list.bin', 'update.prc', 'c05attackairhi.nuanmb']

# 0.19.0: up-B (Fire). `rescue` is the pair of firemen with the trampoline and
# `parachute` the parachute; plugin/src/article.rs clones both after breath, and
# plugin/src/status/special_hi.rs drives them exactly as G&W's own statuses do.
# Measured on the donor (`ls` over model/{rescue,parachute}/c0*): both model folders
# hold the same sixteen names as breath's c00, except rescue c04, which has no
# `model.nuanmb` - listed per slot for the same reason as breath. The motion folders
# are uniform per article; parachute has the two extra clips its open/close phases play.
UPB_MODEL_CORE = [
    'model.numdlb', 'model.numshb', 'model.numshexb', 'model.nuhlpb',
    'model.nusrcmdlb', 'model.nusktb', 'model.xmb',
    'model.numatb', 'dark_model.numatb', 'light_model.numatb',
    'metamon_model.numatb',
    'black_ha_col.nutexb', 'gray_ha_col.nutexb', 'grayb_ha_col.nutexb',
    'gw_nor.nutexb',
]
RESCUE_MODEL_FILES = {slot: UPB_MODEL_CORE + ([] if slot == 'c04' else ['model.nuanmb'])
                      for slot in ARTICLE_SLOTS.values()}
PARACHUTE_MODEL_FILES = {slot: UPB_MODEL_CORE + ['model.nuanmb'] for slot in ARTICLE_SLOTS.values()}
RESCUE_MOTION_FILES = ['motion_list.bin', 'update.prc',
                       'd02specialhi.nuanmb', 'd02specialairhi.nuanmb']
PARACHUTE_MOTION_FILES = RESCUE_MOTION_FILES + ['d02specialhiopen.nuanmb', 'd02specialhiclose.nuanmb']

# Every cloned article this build ships, in registration order. The order is
# load-bearing on the plugin side, not here: smashline appends each fighter's
# article descriptors in the order `clone_weapon` was called, so `install()` in
# plugin/src/article.rs must call them in this order for `normal_weapon()` and
# `breath()` to return the right local ids.
#
# 0.16.0 added a third entry here, `chrom_sword`, for Chrom's jab. 0.17.0 removed
# it: the clone never rendered on hardware, and the jab now draws Pyra's own
# esword article (which is not a clone - it is one of eflame's own five, so it
# does not belong in this table at all). `refs/chrom_jab/` is kept as the donor
# record for the retargeted animation; the article files it also holds are no
# longer shipped.

ARTICLES = {
    'normal_weapon': {
        'model': {slot: ARTICLE_MODEL_FILES for slot in ARTICLE_SLOTS.values()},
        'motion': {slot: ARTICLE_MOTION_FILES for slot in ARTICLE_SLOTS.values()},
    },
    'breath': {
        'model': BREATH_MODEL_FILES,
        'motion': {slot: BREATH_MOTION_FILES for slot in ARTICLE_SLOTS.values()},
    },
    'rescue': {
        'model': RESCUE_MODEL_FILES,
        'motion': {slot: RESCUE_MOTION_FILES for slot in ARTICLE_SLOTS.values()},
    },
    'parachute': {
        'model': PARACHUTE_MODEL_FILES,
        'motion': {slot: PARACHUTE_MOTION_FILES for slot in ARTICLE_SLOTS.values()},
    },
}

# Where each article's donor files are read from: (donor root, donor directory name).
#
# Both are in the export and their donor directory is the article name itself.
#
# A note from the removed `chrom_sword` entry, kept because it is a trap for the
# next article that is not G&W's: when the donor's own directory name differs from
# the name passed to `clone_weapon`, both are needed. smashline's
# `weapon_name_hook` (be3ef30 `src/cloning/weapons.rs`) substitutes the registered
# name into the engine's `get_file` lookup, so on eflame the files must live under
# the registered name while the donor tree keeps the game's own. Two different
# strings, and getting either one wrong is a silent no-load - which is exactly the
# class of failure 0.16.0 hit and could not diagnose.
ARTICLE_DONOR = {
    'normal_weapon': (EXPORT / 'fighter/gamewatch', 'normal_weapon'),
    'breath': (EXPORT / 'fighter/gamewatch', 'breath'),
    'rescue': (EXPORT / 'fighter/gamewatch', 'rescue'),
    'parachute': (EXPORT / 'fighter/gamewatch', 'parachute'),
}

# Articles whose `_col` textures belong to the G&W reskin and therefore get the
# per-costume colour themes.
ARTICLE_THEMED = {'normal_weapon', 'breath', 'rescue', 'parachute'}


def article_files(article, kind, donor_slot):
    """The file list for one article/kind/donor-slot.

    Strict on purpose: a donor slot with no entry is a build error, never a
    silent substitution from another colour. The donor's own layouts are not
    uniform across slots (see BREATH_MODEL_EXTRA), so "fall back to c00" would
    quietly ship the wrong textures under the wrong name.
    """
    require(article in ARTICLES, f'no file lists for article {article}')
    table = ARTICLES[article][kind]
    require(donor_slot in table,
            f'no {article}/{kind} file list for donor slot {donor_slot}')
    return table[donor_slot]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(cond, msg):
    if not cond:
        raise RuntimeError(msg)


def parse_mlist(path):
    data = Path(path).read_bytes()
    _, _, count = struct.unpack_from('<QQQ', data)
    offset, motions = 24, {}
    for _ in range(count):
        kind, _, _, _, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        require(n_anims <= 3, f'bad motion entry in {path}')
        offset += 24
        motions[kind] = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = ((offset + n_anims * 9 + 3) & ~3) + size
    return motions


def parse_mlist_entries(path):
    """Full motion-list parse: the directory hash plus each entry's raw bytes.

    `parse_mlist` throws the raw entry away, which is fine when you only want to
    know which clip a motion kind plays but useless when you want to *add* an
    entry: an entry carries more than its clip names (flags, blend weight and a
    28-byte tail that differs per kind), and the only way to reproduce G&W's
    entry exactly is to copy G&W's bytes. The recipe is the one validated in
    `references/inject_monkey_flip.py`: copy the donor entry whole, then assert
    the re-encoded list still matches byte for byte everywhere else.
    """
    data = Path(path).read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data)
    require(magic == hash40('motion'), f'bad motion-list header in {path}')
    offset, entries = 24, {}
    for _ in range(count):
        start = offset
        kind, _, _, _, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        require(n_anims <= 3 and size % 8 in (0, 4), f'bad motion entry in {path}')
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = ((offset + n_anims * 9 + 3) & ~3)
        end = offset + size
        require(end <= len(data) and kind not in entries,
                f'truncated or duplicate motion in {path}')
        entries[kind] = {'raw': data[start:end], 'anims': anims}
        offset = end
    require(offset == len(data), f'unexpected trailing data in {path}')
    return magic, motion_path, entries


def load_labels():
    labels = {}
    for line in (ROOT / 'dumps/scripts/ParamLabels.csv').open(encoding='utf-8'):
        key, _, name = line.strip().partition(',')
        try:
            labels[int(key, 16)] = name
        except ValueError:
            pass
    return labels


def build_skeleton(pyra_dir, gw_dir, out_dir):
    pyra = s.skel_data.read_skel(str(pyra_dir / 'model.nusktb'))
    skel = s.skel_data.read_skel(str(gw_dir / 'model.nusktb'))
    index = {b.name.lower(): i for i, b in enumerate(skel.bones)}
    pending = [b for b in pyra.bones if b.name.lower() not in index]
    grafted = []
    while pending:
        progress = []
        for b in pending:
            parent = None if b.parent_index is None else pyra.bones[b.parent_index].name.lower()
            if parent is None or parent in index:
                skel.bones.append(s.skel_data.BoneData(
                    b.name, b.transform, None if parent is None else index[parent], b.billboard_type))
                index[b.name.lower()] = len(skel.bones) - 1
                grafted.append(b.name)
                progress.append(b)
        require(progress, 'unresolvable bone parents: ' + ', '.join(b.name for b in pending))
        pending = [b for b in pending if b not in progress]
    skel.save(str(out_dir / 'model.nusktb'))
    back = s.skel_data.read_skel(str(out_dir / 'model.nusktb'))
    require({b.name.lower() for b in pyra.bones} <= {b.name.lower() for b in back.bones},
            'grafted skeleton lost Pyra bones')
    return grafted


def build_model(slot, gw_slot):
    pyra_dir = EXPORT / 'fighter/eflame/model/body' / slot
    if slot == 'c06' and (PINK_GW_DIR / 'fighter/gamewatch/model/body/c05').is_dir():
        gw_dir = PINK_GW_DIR / 'fighter/gamewatch/model/body/c05'
    else:
        gw_dir = EXPORT / 'fighter/gamewatch/model/body' / gw_slot
    out = MOD / 'fighter/eflame/model/body' / slot
    out.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        shutil.copy2(gw_dir / name, out / name)
    grafted = build_skeleton(pyra_dir, gw_dir, out)

    # Map every G&W texture onto an existing Pyra texture file name.
    pyra_textures = sorted(p.stem for p in pyra_dir.glob('*.nutexb'))
    gw_textures = {p.stem.lower(): p for p in gw_dir.glob('*.nutexb')}
    rename = {}
    for stem, path in sorted(gw_textures.items()):
        target = pyra_textures[len(rename)]
        rename[stem] = target
        if '_col' in stem:
            themes.gw_texture(path, out / (target + '.nutexb'), slot)
        else:
            shutil.copy2(path, out / (target + '.nutexb'))
    for name in MATERIAL_FILES:
        matl = s.matl_data.read_matl(str(gw_dir / name))
        for entry in matl.entries:
            for tex in entry.textures:
                if not tex.data or tex.data.startswith('#'):
                    continue
                require(tex.data.lower() in rename, f'{name}: unknown texture {tex.data}')
                tex.data = rename[tex.data.lower()]
        matl.save(str(out / name))
    require(all((pyra_dir / p.name).exists() for p in out.iterdir()),
            f'{slot}: model output contains a file name Pyra does not have')
    return {'grafted_bones': len(grafted), 'textures': rename}


# `hide_esword()` used to live here. It scaled the esword skeleton's `Root` basis to
# 1e-3 so the sword sat inside the palm. Refuted on hardware 2026-09-30: the sword
# was still drawn, because `Root` is the one esword bone that none of the article's
# own clips animates and a bind-pose scale there has no visible effect. The Aegis
# sword is now placed by `tools/build_esword_pose.py`, which sets the article's
# per-state mesh visibility instead. See `handbook/graveyard.md` R-20.


def build_motion(slot, gw_slot, labels):
    """Write eflame's c06/c07 motion list and clips so they are G&W's.

    ALIAS notes. A motion entry names its clips by file-name hash, and the game
    only finds a clip if that name exists in the costume's motion folder. G&W's
    322 referenced clip names are therefore mapped onto file names eflame has:
      * a name eflame already has (301) is used as-is, and the G&W clip is written
        over eflame's file of that name;
      * the other 20 (`d00specialn`, `c04attackhi4r`, ...) are written under a
        spare eflame name, and the entries that use them are rewritten to
        reference that spare name. The plugin only ever refers to motion *kinds*,
        so the alias is invisible to it.
    The spare names come from eflame clips no G&W clip claims, so no Pyra clip
    is left reachable.

    PROBE notes (0.8.0). `PROBE_FILES` are exempt from the alias rule and are
    written under their own G&W name, which exists in no eflame folder in the
    base game. Each one is therefore a real new file, and the motion entry that
    names it is a real test of whether the engine can see a file the mod added -
    the question the Monkey Flip failure (`HANDOFF.md`, repo root) left open,
    because that mod shipped new clip names with no `config.json` to declare
    them. The probe file is a byte-exact copy of G&W's clip and is excluded from
    `complete_visibility`, so it is verbatim donor data; the asserts below fail
    the build if any *other* new name creeps in, or if a probe file is edited,
    unused, or absent.
    """
    pyra_dir = EXPORT / 'fighter/eflame/motion/body' / slot
    gw_dir = EXPORT / 'fighter/gamewatch/motion/body' / gw_slot
    out = MOD / 'fighter/eflame/motion/body' / slot
    out.mkdir(parents=True, exist_ok=True)

    magic, motion_path, pyra = parse_mlist_entries(pyra_dir / 'motion_list.bin')
    _, _, gw = parse_mlist_entries(gw_dir / 'motion_list.bin')
    pyra_names = {hash40(p.name): p.name for p in pyra_dir.glob('*.nuanmb')}
    gw_files = {hash40(p.name): p for p in gw_dir.glob('*.nuanmb')}

    # 1. every clip G&W's own list names, in list order.
    gw_ref = []
    for entry in gw.values():
        for a in entry['anims']:
            if a not in gw_ref:
                gw_ref.append(a)
    require(all(a in gw_files for a in gw_ref),
            f'{slot}: G&W list references a clip G&W does not have')

    # 1b. Monkey Flip's twelve kinds. Side-B on c06/c07 is that move (see
    # plugin/src/status/monkey_flip.rs and plugin/src/acmd/monkey_flip.rs), so the
    # motion list has to carry the donor's twelve entries and twelve retargeted
    # clips have to exist under file names eflame already has. The donor's entries
    # are copied whole - kind, game script, flags, blend and cancel frame - and
    # only the animation-name field is repointed at an alias target below.
    mf_entries = mflip.donor_entries()
    mf_kinds = mflip.motion_kinds()
    require(not (mf_kinds & set(gw)), f'{slot}: a Monkey Flip kind is also a G&W kind')
    require(not (mf_kinds & set(pyra)), f'{slot}: a Monkey Flip kind is also a Pyra kind')
    mf_clips = mflip.donor_clips()
    for h, path in mf_clips.items():
        # A donor clip name eflame already has would mean writing the retargeted
        # clip over one of Pyra's own files, which her motion list still names.
        require(h not in pyra_names,
                f'{slot}: donor clip {path.name} already exists in eflame {slot}, so '
                f'the retarget would overwrite a Pyra clip instead of aliasing past it')
    mf_ref = [a for e in mf_entries.values() for a in e['anims']]
    mf_bones = set(mflip.recipient_bones(gw_slot))
    mf_vis = mflip.visibility_group(gw_slot)

    def donor_clip_name(name_hash):
        """The donor file a referenced clip hash came from, G&W's or Monkey Flip's."""
        return mf_clips[name_hash].name if name_hash in mf_clips else gw_files[name_hash].name


    # 2. the probe files: real new files, kept under their own G&W names.
    new_files = {hash40(n): n for n in PROBE_FILES}
    for h, n in new_files.items():
        require(h in gw_files, f'{slot}: probe file {n} is not a G&W clip')
        require(h in gw_ref, f'{slot}: no G&W motion names {n}')
        require(h not in pyra_names,
                f'{slot}: probe file {n} already exists in eflame {slot}, '
                f'so it would not test file addition')

    # 3. alias map: donor clip-name hash -> eflame file-name hash. G&W's own
    # clips and Monkey Flip's twelve share this one mechanism and one spare pool,
    # and the spares are consumed in list order so the pool a build uses is a
    # function of the donor data and not of iteration order.
    all_ref = list(gw_ref) + [a for a in mf_ref if a not in gw_ref]
    alias = {a: a for a in all_ref if a in pyra_names or a in new_files}
    pyra_ref = {a for e in pyra.values() for a in e['anims']}
    spare = sorted((a for a in pyra_ref if a not in alias), key=lambda a: pyra_names[a])
    aliased = [a for a in all_ref if a not in alias]
    require(len(aliased) <= len(spare),
            f'{slot}: need {len(aliased)} spare eflame clip names, only {len(spare)} exist')
    for a in aliased:
        alias[a] = spare.pop(0)

    def rename(raw, anims):
        n = len(anims)
        return raw[:24] + struct.pack('<' + 'Q' * n, *anims) + raw[24 + 8 * n:]

    # 4. entries: every G&W kind whole, then eflame-only kinds with stand-in clips.
    entries, standin_report = {}, {}
    for kind, e in gw.items():
        entries[kind] = {'raw': rename(e['raw'], [alias[a] for a in e['anims']]),
                         'anims': tuple(alias[a] for a in e['anims'])}
    # Monkey Flip's twelve kinds: the donor's own entries, whole, with the one
    # animation name field repointed at the alias target.
    for kind, e in mf_entries.items():
        entries[kind] = mflip.repoint(e, alias[e['anims'][0]])

    cf_entry = cloud_fair.get_cloud_motion_entry(hash40('attack_air_f'))
    cl_entry = cloud_fair.get_cloud_motion_entry(hash40('landing_air_f'))
    entries[hash40('attack_air_f')] = {'raw': cf_entry['raw'], 'anims': cf_entry['anims']}
    entries[hash40('landing_air_f')] = {'raw': cl_entry['raw'], 'anims': cl_entry['anims']}

    # 0.16.0: Chrom's jab. The donor's own `attack_11` entry goes in whole - cancel
    # frame 23 against G&W's 16, and Chrom's flags - so the cancel window is his.
    # Its animation field names `c00attack11.nuanmb`, which is also eflame's own clip
    # name, so the retargeted clip lands on the file that entry already points at and
    # no alias is consumed. The clip itself is written below, over G&W's.
    cj_entry = chrom_jab.get_chrom_motion_entry()
    entries[hash40('attack_11')] = {'raw': cj_entry['raw'], 'anims': cj_entry['anims']}

    # R.O.B.'s down tilt: his own `attack_lw3` entry, whole (cancel frame 15, flags 0x80).
    # It names `c02attacklw3.nuanmb`, the file eflame and G&W both call that kind's clip,
    # so the retargeted clip is written over G&W's manhole-cover one below.
    rd_entry = robot_dtilt.get_entry()
    entries[hash40('attack_lw3')] = {'raw': rd_entry['raw'], 'anims': rd_entry['anims']}

    # Snake's up tilt: his own `attack_hi3` entry, whole (cancel frame 38, flags 0x84,
    # `game_script` = game_attackhi3). It names `c02attackhi3.nuanmb`, the file eflame
    # and G&W both call that kind's clip, so the retargeted clip is written over
    # G&W's own up-tilt one below.
    su_entry = snake_uptilt.get_entry()
    entries[hash40('attack_hi3')] = {'raw': su_entry['raw'], 'anims': su_entry['anims']}

    # Little Mac's forward smash family: his own `attack_s4_s`, `attack_s4_hold`,
    # `attack_s4_hi` and `attack_s4_lw` entries, whole (cancel frame 44 against
    # G&W's 43, flags 0x84 against 0x80). The two neutral names are ones eflame
    # and G&W already call, so no alias is consumed and the retargeted clips land
    # on the files those entries already point at. The two angled names are new
    # files, declared in config.json by `declared_new_clips` below.
    lm_entries = {k: littlemac_s4.get_entry(k) for k in littlemac_s4.KINDS}
    for kind_name, e in lm_entries.items():
        require(e['anims'][0] not in pyra_names or e['anims'][0] in gw_files,
                f'{slot}: donor clip for {kind_name} collides with a Pyra clip')
        entries[hash40(kind_name)] = {'raw': e['raw'], 'anims': e['anims']}
    # Clip names of this move that the base game does not ship, read off the
    # pristine export rather than the build output, so the two `referenced` checks
    # below know about them before the clips are written. `declared_new_clips`
    # turns the same list into config.json entries.
    lm_new = {hash40(n): n
              for n in littlemac_s4.new_clip_names(EXPORT / f'fighter/eflame/motion/body/{slot}')}

    def standin_for(kind):
        if kind in gw:
            return gw[kind]['anims'], 'exact'
        name = labels.get(kind, '')
        for prefix, candidates in FALLBACKS:
            if name.startswith(prefix):
                for c in candidates:
                    if hash40(c) in gw:
                        return gw[hash40(c)]['anims'], 'fallback:' + c
        return gw[hash40('wait')]['anims'], 'wait'

    for kind, e in pyra.items():
        if kind in gw:
            continue
        src, how = standin_for(kind)
        anims = [alias[src[min(i, len(src) - 1)]] for i in range(len(e['anims']))]
        entries[kind] = {'raw': rename(e['raw'], anims), 'anims': tuple(anims)}
        standin_report[labels.get(kind, hex(kind))] = how

    # 5. write the list, then read it back and check it.
    encoded = struct.pack('<QQQ', magic, motion_path, len(entries)) + b''.join(
        e['raw'] for e in entries.values())
    (out / 'motion_list.bin').write_bytes(encoded)
    _, path_back, check = parse_mlist_entries(out / 'motion_list.bin')
    require(path_back == motion_path, f'{slot}: motion path changed')
    require(check == entries, f'{slot}: motion list did not survive the write')
    for kind, e in gw.items():
        if kind in (hash40('attack_air_f'), hash40('landing_air_f'), hash40('attack_11'),
                    hash40('attack_lw3'), hash40('attack_hi3')) \
                or kind in {hash40(k) for k in littlemac_s4.KINDS}:
            continue
        want = rename(e['raw'], [alias[a] for a in e['anims']])
        require(check[kind]['raw'] == want, f'{slot}: G&W entry {kind:#x} not copied whole')
    require(check[hash40('attack_air_f')]['raw'] == cf_entry['raw'], f'{slot}: Cloud fair entry mismatch')
    require(check[hash40('landing_air_f')]['raw'] == cl_entry['raw'], f'{slot}: Cloud landing entry mismatch')
    require(check[hash40('attack_11')]['raw'] == cj_entry['raw'], f'{slot}: Chrom jab entry mismatch')
    require(check[hash40('attack_lw3')]['raw'] == rd_entry['raw'], f'{slot}: R.O.B. down tilt entry mismatch')
    require(check[hash40('attack_hi3')]['raw'] == su_entry['raw'], f'{slot}: Snake up tilt entry mismatch')
    for kind_name, e in lm_entries.items():
        require(check[hash40(kind_name)]['raw'] == e['raw'],
                f'{slot}: Little Mac {kind_name} entry mismatch')
    require(set(check) == set(gw) | set(pyra) | mf_kinds | {hash40(k) for k in littlemac_s4.KINDS},
            f'{slot}: kinds lost or invented')

    # 6. write the clips. Every referenced name must be written by us (so no Pyra
    # clip stays reachable) and must be a name eflame already has - except for the
    # declared probe files, which are new files on purpose.
    written, mf_records = {}, []
    for g, target in alias.items():
        name = new_files.get(target) or pyra_names[target]
        if g in mf_clips:
            # Retargeted onto the recipient skeleton as it is built here, then
            # written under an eflame name the base install already has.
            mf_records.append(mflip.retarget(g, mf_clips[g], mf_bones, mf_vis, out / name))
            written[target] = mf_clips[g].name
        else:
            shutil.copy2(gw_files[g], out / name)
            written[target] = gw_files[g].name
    require(len({r['output'] for r in mf_records}) == len(mf_records),
            f'{slot}: two Monkey Flip slots were given the same clip file')
    mflip.assert_distinct(mf_records)
    referenced = {a for e in check.values() for a in e['anims']}
    lm_new_keys = set(lm_new)
    require(referenced - set(new_files) - lm_new_keys <= set(pyra_names),
            f'{slot}: list names a file eflame does not have and is neither a declared '
            f'probe nor a declared Little Mac clip')
    require(referenced - lm_new_keys <= set(written),
            f'{slot}: list still reaches a Pyra clip')
    require(lm_new_keys <= referenced,
            f'{slot}: a declared Little Mac clip is written but no motion names it')
    for h, n in new_files.items():
        require(h in referenced, f'{slot}: probe file {n} is written but no motion names it')
        require((out / n).read_bytes() == gw_files[h].read_bytes(),
                f'{slot}: probe file {n} is not a byte-exact copy of G&W')
    # No sword track here on purpose: the article is posed by its own clips, not by
    # this body clip (graveyard R-21). See tools/build_esword_pose.py.
    cloud_rep = cloud_fair.deploy_for_slot(slot, out, gw_slot)
    # Chrom's jab, over the G&W `c00attack11.nuanmb` written above. The model dir is
    # passed explicitly because the filter is the *built* grafted skeleton (see
    # tools/build_chrom_jab.py): keeping Sword1/Sword2 is what aims the blade, which
    # is Pyra's esword but hangs off the same sword1 chain Chrom's own did.
    chrom_rep = chrom_jab.deploy_for_slot(
        slot, out, gw_slot, MOD / 'fighter/eflame/model/body' / slot)
    # Custom G&W recipient down tilt under the existing c02attacklw3 carrier.
    # R.O.B. timing/ACMD stay intact; build_robot_dtilt.py authors the full pose.
    robot_rep = robot_dtilt.deploy_for_slot(
        slot, out, gw_slot, MOD / 'fighter/eflame/model/body' / slot)
    # Snake's up tilt under the existing c02attackhi3 carrier. Same built-skeleton
    # filter as the jab, the down tilt and the forward smash; the whole leg chain is
    # checked to be moving, which is the R.O.B. down-tilt failure (limbs left in rest
    # pose) this generator exists not to repeat. See tools/build_snake_uptilt.py.
    snake_uptilt_rep = snake_uptilt.deploy_for_slot(
        slot, out, gw_slot, MOD / 'fighter/eflame/model/body' / slot)
    # Little Mac's forward smash family, over G&W's `c03attacks4s` and
    # `c03attacks4charge`, plus the two new `c03attacks4hi` / `c03attacks4lw`
    # files. The first two are files the recipient's own list already reaches, so
    # they are overwrites; the angled pair are new names and are declared in
    # config.json. Same built-skeleton filter as the jab and the dtilt. See
    # tools/build_littlemac_fsmash.py.
    lm_rep = littlemac_s4.deploy_for_slot(
        slot, out, gw_slot, MOD / 'fighter/eflame/model/body' / slot)
    # A clip this slot added must not be a name the base game already ships,
    # because then it is an overwrite and does not belong in config.json.
    for name in lm_rep['new_clips']:
        require(not (EXPORT / f'fighter/eflame/motion/body/{slot}/{name}').exists(),
                f'{slot}: {name} is reported as a new clip but the base game has it')
    # Clips code loads by name rather than through the list (the default eyelid).
    by_name = []
    for h, path in gw_files.items():
        if h in pyra_names and h not in written:
            shutil.copy2(path, out / path.name)
            by_name.append(path.name)
    visibility = complete_visibility(out, gw_slot, skip=set(PROBE_FILES))
    # Use donor names to find both ordinary and aliased right-facing clips.
    helmet_clips = []
    for donor_hash, target in alias.items():
        if donor_clip_name(donor_hash) in UPSMASH_HELMET_CLIPS:
            name = new_files.get(target) or pyra_names[target]
            fix_upsmash_helmet(out / name)
            helmet_clips.append(name)
    return {'entries': len(check), 'gw_kinds': len(gw),
            'pyra_only_kinds_kept': len(standin_report),
            'clips_identity': sum(1 for a, t in alias.items() if a == t),
            'clips_aliased': {donor_clip_name(a): pyra_names[alias[a]] for a in aliased},
            'clips_copied_by_name': by_name,
            'new_files': sorted(new_files.values()),
            'standins': standin_report, 'visibility': visibility,
            'upsmash_helmet_clips': sorted(helmet_clips),
            'cloud_fair': cloud_rep,
            'chrom_jab': chrom_rep,
            'robot_dtilt': robot_rep,
            'snake_uptilt': snake_uptilt_rep,
            'littlemac_fsmash': lm_rep,
            'monkey_flip': mf_records}


UPSMASH_HELMET_CLIPS = {
    'c04attackhi4.nuanmb', 'c04attackhi4r.nuanmb',
    'c04attackhi4charge.nuanmb', 'c04attackhi4rcharge.nuanmb',
}


def fix_upsmash_helmet(path):
    """Make animation visibility agree with ACMD's head/head_diver state."""
    anim = s.anim_data.read_anim(str(path))
    states = {'DiverM': True, 'DiverFLIPM': False, 'HeadM': False, 'HelmetM': False}
    for group in anim.groups:
        if group.group_type.name == 'Visibility':
            for node in group.nodes:
                if node.name in states:
                    for track in node.tracks:
                        track.values = [states[node.name]]
    anim.save(str(path))
    back = s.anim_data.read_anim(str(path))
    actual = {n.name: t.values for g in back.groups if g.group_type.name == 'Visibility'
              for n in g.nodes for t in n.tracks if n.name in states}
    require(actual == {n: [v] for n, v in states.items()},
            f'{path}: up-smash helmet visibility did not survive save')


# Stock AttackS3 generates the stool at frame 8. The donor Have track switches
# from its startup pose to its extended pose at frame 7, then stays there through
# frame 44. An article starting its own clip at zero must use this visible pose,
# rather than replaying the seven startup frames after the fighter has thrust.
STOOL_SPAWN_FRAME = 8


def fix_stool_grip(path):
    """Use the exact stock visible pose, not the pre-spawn retracted pose."""
    anim = s.anim_data.read_anim(str(path))
    have = next(n for g in anim.groups if g.group_type.name == 'Transform'
                for n in g.nodes if n.name == 'Have')
    expected = {}
    for track in have.tracks:
        require(len(track.values) > STOOL_SPAWN_FRAME, f'{path}: stock spawn pose missing')
        grip = track.values[STOOL_SPAWN_FRAME]
        pose = lambda value: (value.scale, value.rotation, value.translation)
        require(all(pose(value) == pose(grip)
                    for value in track.values[STOOL_SPAWN_FRAME:]),
                f'{path}: donor stool no longer stays rigid after spawn')
        expected[track.name] = pose(grip)
        track.values = [grip]
    # chair_c is already constant. Preserve it and all mesh visibility tracks.
    anim.save(str(path))
    back = s.anim_data.read_anim(str(path))
    actual = next(n for g in back.groups if g.group_type.name == 'Transform'
                  for n in g.nodes if n.name == 'Have')
    require(all(len(t.values) == 1 and
                (t.values[0].scale, t.values[0].rotation, t.values[0].translation) == expected[t.name]
                for t in actual.tracks), f'{path}: stock stool grip did not survive save')


# Item-hand clips are partial layers over the body clip; giving them a visibility
# group would override the body clip's props, so they are left untouched.
VISIBILITY_LAYERS = ('a00itemhand',)


def complete_visibility(out, gw_slot, skip=()):
    """Give every G&W mesh an explicit on/off track in every clip.

    G&W's body model holds all of his props and alternate-pose silhouettes (98
    meshes). Clips with no visibility group at all (being thrown) drew all 98
    meshes stacked, and a mesh with no track in G&W's own clip keeps its previous
    state, so missing tracks are filled with False; clips with no visibility group
    get the idle clip's full state.

    # The hammer is NOT one of the untracked meshes - do not "fix" it here

    An earlier version of this docstring claimed `LHammerM`, `RHammerM`,
    `flagman1M_FLIP` and `flagman2M_FLIP` were the four meshes G&W's clips never
    track, hidden by native visibility groups. That is measurably false for the
    hammer, and believing it costs a real regression: `f03downattacku`,
    `f04downattackd` and `g03slipattack` each carry a 50-value `RHammerM` track
    (False x11, then True x36, then False), so the hammer plays on its own with
    no help from this function. Writing False over that track is exactly what
    broke it, and that mistake is what rule R22 was an attempt to work around
    before 0.8.1 retracted it. The claim was the same wrong theory twice.

    A mesh that *is* absent from a given clip still gets False here, which is
    correct: the clip is played under Pyra's name, so Pyra's visibility state is
    what "no track" would otherwise inherit, and vanilla Pyra has no such mesh
    visible. That is also why the manhole's hole survives - `c02attacklw3`
    already carries real `manhole1M` / `manhole2M` tracks, so it is not "missing"
    and is never touched.

    `skip` holds clips that must stay verbatim donor data: the file-addition
    probe files. Leaving untracked meshes alone there is deliberate - a clip
    copied byte for byte is the strongest form of that test, and if the probe
    does load, its extra meshes appearing for the probe's few frames is itself
    further evidence that the new file was read.

    The `normal_weapon` article's clips need no entry in `skip`: they are
    protected by location, not by this list. This function only ever globs the
    body motion directory, and those clips live in
    `fighter/eflame/motion/normal_weapon/<slot>`, which is why their own
    visibility tracks - the thing that actually selects the prop - survive
    untouched. Do not widen the glob to reach them.
    """
    mesh = s.mesh_data.read_mesh(str(EXPORT / 'fighter/gamewatch/model/body' / gw_slot / 'model.numshb'))
    meshes = sorted({o.name.split('_VIS_')[0] for o in mesh.objects})
    idle = s.anim_data.read_anim(str(EXPORT / 'fighter/gamewatch/motion/body' / gw_slot / 'a00wait1.nuanmb'))
    idle_state = {n.name: n.tracks[0].values[0] for g in idle.groups
                  if g.group_type.name == 'Visibility' for n in g.nodes}
    filled, whole = 0, []
    for path in sorted(out.glob('*.nuanmb')):
        if path.name.startswith(VISIBILITY_LAYERS) or path.name in skip:
            continue
        for attempt in range(10):
            try:
                anim = s.anim_data.read_anim(str(path))
                break
            except Exception:
                if attempt == 9:
                    raise
                time.sleep(0.1)
        groups = [g for g in anim.groups if g.group_type.name == 'Visibility']
        if groups:
            group, default = groups[0], lambda name: False
        else:
            group, default = s.anim_data.GroupData(s.anim_data.GroupType.Visibility, []),                 lambda name: idle_state.get(name, False)
            whole.append(path.name)
        present = {n.name for n in group.nodes}
        missing = [m for m in meshes if m not in present]
        if not missing:
            continue
        for name in missing:
            group.nodes.append(s.anim_data.NodeData(name, [s.anim_data.TrackData('Visibility', values=[default(name)])]))
        if not groups:
            anim.groups.append(group)
        anim.save(str(path))
        for attempt in range(10):
            try:
                back = s.anim_data.read_anim(str(path))
                break
            except Exception:
                if attempt == 9:
                    raise
                time.sleep(0.1)
        covered = {n.name for g in back.groups if g.group_type.name == 'Visibility' for n in g.nodes}
        require(set(meshes) <= covered, f'{path.name}: visibility still incomplete after save')
        filled += 1
    return {'clips_completed': filled, 'clips_given_idle_state': whole}


MOTION_PARAM_FILES = ['ik.prc', 'update.prc', 'flip.prc', 'scharge.prc']


def build_motion_params(slot, gw_slot):
    """G&W's own param files that live in the motion folder.

    `ik.prc` (foot/arm two-bone IK), `scharge.prc` (foot IK while charging a smash),
    `update.prc` (which bones the engine updates) and `flip.prc` (mirroring) are per
    fighter and they name bones and weights tuned for that skeleton. Pyra's leave G&W's
    legs pinned by her stance, which is the "legs get stuck" symptom. eflame has all
    four names, so this overwrites and adds nothing. `swing.prc`/`swingblend.prc` are
    Pyra sword-swing data with no G&W counterpart; nothing on G&W reaches them.
    """
    gw_dir = EXPORT / 'fighter/gamewatch/motion/body' / gw_slot
    pyra_dir = EXPORT / 'fighter/eflame/motion/body' / slot
    out = MOD / 'fighter/eflame/motion/body' / slot
    record = {}
    for name in MOTION_PARAM_FILES:
        require((pyra_dir / name).exists(), f'{slot}: eflame has no {name}; would add a file')
        shutil.copy2(gw_dir / name, out / name)
        require(sha(out / name) == sha(gw_dir / name), f'{slot}: {name} copy failed')
        record[name] = sha(out / name)
    return record


# Mesh-visibility tables that G&W's fighter params define and eflame's do not.
# `param_visibility_data_body` is the model's own group table (head, helmet, lhand,
# hand, panel, zzz, oil, body, ...): what `VisibilityModule::set_int64(hash40("hand"),
# hash40("hand_hold_lr"))` looks up. Without it every such call in the ported scripts
# does nothing and G&W's props (the diver's fishbowl, the helmet, the stool, the
# number cards) never appear. The other four belong to G&W's articles.
GW_VISIBILITY_KEYS = ['param_visibility_data_body', 'param_visibility_data_oil',
                      'param_visibility_data_rescue', 'param_visibility_data_octopus',
                      'param_visibility_data_parachute']


def build_expression_vl():
    """Add G&W's mesh-visibility groups to eflame's `param/expression_vl.prc`.

    Per fighter, not per costume: the file is loaded for all eight Pyra costumes, so
    only keys eflame lacks are added and nothing of hers changes. That is safe for
    c00-c05 because none of the 110 mesh names those tables reference exists in any
    Pyra model (checked for c00-c07), so the groups find no mesh to show or hide.
    `virtual_node_data`, `effect_emit_node_data` and the rest exist in both files with
    different values and stay Pyra's, because changing them would change vanilla Pyra.
    That is a known limit of a per-fighter file and is recorded in the handoff.
    """
    stock = EXPORT / 'fighter/eflame/param/expression_vl.prc'
    donor = EXPORT / 'fighter/gamewatch/param/expression_vl.prc'
    ours = prc.read(stock)
    theirs = prc.as_dict(prc.read(donor))
    have = {k for k, _ in ours[1]}
    added = []
    for name in GW_VISIBILITY_KEYS:
        key = prc.hash40(name)
        require(key in theirs, f'gamewatch expression_vl.prc has no {name}')
        require(key not in have, f'eflame expression_vl.prc already has {name}')
        ours[1].append((key, theirs[key]))
        added.append(name)
    out = MOD / 'fighter/eflame/param/expression_vl.prc'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(prc.write(ours))

    back = prc.as_dict(prc.read(out))
    original = prc.as_dict(prc.read(stock))
    require(all(back[k] == v for k, v in original.items()), 'eflame keys changed by the merge')
    require(all(back[prc.hash40(n)] == theirs[prc.hash40(n)] for n in added),
            "added tables differ from G&W's")
    require(set(back) == set(original) | {prc.hash40(n) for n in added}, 'unexpected keys')
    head = vis.find_group(back[prc.hash40('param_visibility_data_body')], prc.hash40('head'))
    require(head is not None and
            vis.state_meshes(head, prc.hash40('head_diver')) == [prc.hash40('diverm')],
            'head/head_diver must select DiverM')
    # independent reader: pyprc must resolve every key of the written file
    import pyprc
    probe = pyprc.param(str(out))
    for k in back:
        probe[pyprc.hash(k)]
    return {'added': added, 'kept_from_eflame': len(original), 'sha256': sha(out)}


def build_article(article, slot, gw_slot):
    """Copy one G&W article's model and motion into eflame's namespace.

    Preserve donor files except the c06/c07 normal_weapon stool grip transform.
    Article visibility remains unchanged so each clip still selects its own prop.

    `normal_weapon` carries its own skeleton - it has `Manhole`, `Tank` and
    `Body2` bones that the fighter's skeleton does not have - and its own
    `motion_list.bin` with eleven entries. That is why it cannot be faked by
    reusing a fighter body mesh: there is no mesh to reveal, and scanning every
    body clip for `chairM`, `TankM` and `Kame` returns zero hits (measured,
    `HANDOFF_ARTICLE_SEARCH.md` Â§1). The article is the article.

    The article's name is load-bearing and is not ours to choose. smashline
    resolves a cloned article's files from its owner fighter and its weapon name,
    so the directory this writes is the directory the engine will look in.

    Returns the two directory paths relative to the mod root, which is what
    build_config_json() needs to declare them.
    """
    out = {}
    for kind in ('model', 'motion'):
        names = article_files(article, kind, gw_slot)
        donor_root, donor_dir = ARTICLE_DONOR[article]
        if (article in ARTICLE_THEMED and slot == 'c06' and kind == 'model'
                and (PINK_GW_DIR / f'fighter/gamewatch/model/{article}/c05').is_dir()):
            src = PINK_GW_DIR / f'fighter/gamewatch/model/{article}/c05'
        else:
            src = donor_root / kind / donor_dir / gw_slot
        require(src.is_dir(), f'G&W {article} {kind} folder missing at {src}')
        for name in names:
            require((src / name).is_file(), f'G&W {article} {kind} file missing: {name}')
        # Nothing may be shipped that this list does not name: an unlisted file in
        # a new directory would be written to the card but never declared, and
        # would then be the one thing that silently fails to mount.
        on_disk = {p.name for p in src.iterdir() if p.is_file()}
        require(on_disk == set(names),
                f'G&W {article} {kind} ({gw_slot}) has files this build does not list: '
                f'{sorted(on_disk - set(names))}; missing: {sorted(set(names) - on_disk)}')

        rel = f'fighter/eflame/{kind}/{article}/{slot}'
        dst = MOD / rel
        dst.mkdir(parents=True, exist_ok=True)
        for name in names:
            shutil.copy2(src / name, dst / name)
        # Check donor copies before applying the targeted stool transform correction.
        for name in names:
            require(sha(src / name) == sha(dst / name),
                    f'{rel}/{name} is not byte-identical to the source')
        if kind == 'model' and slot in COSTUMES and article in ARTICLE_THEMED:
            for name in names:
                if name.endswith('.nutexb') and '_col' in name:
                    themes.gw_texture(src / name, dst / name, slot)
        if article == ARTICLE and kind == 'motion' and slot in COSTUMES:
            stool = dst / 'c01attacks3s.nuanmb'
            fix_stool_grip(stool)
            out['stool_grip'] = {'clip': stool.name, 'pose_frame': STOOL_SPAWN_FRAME, 'sha256': sha(stool)}
        out[kind] = rel
    return out


def build_mythra_skin():
    """Copy Black & Pink Mythra body and sword textures to Mythra c06."""
    require(MYTHRA_SKIN_DIR.is_dir(), f'Mythra skin directory missing at {MYTHRA_SKIN_DIR}')
    copied = {}

    # 1. Body textures
    src_body = MYTHRA_SKIN_DIR / 'fighter/elight/model/body/c06'
    dst_body = MOD / 'fighter/elight/model/body/c06'
    dst_body.mkdir(parents=True, exist_ok=True)
    body_files = sorted(p.name for p in src_body.glob('*.nutexb'))
    require(len(body_files) > 0, 'No body textures found in mythra skin')
    for name in body_files:
        shutil.copy2(src_body / name, dst_body / name)
    copied['body_textures'] = len(body_files)

    # 2. Sword textures
    src_sword = MYTHRA_SKIN_DIR / 'fighter/elight/model/esword/c06'
    dst_sword = MOD / 'fighter/elight/model/esword/c06'
    dst_sword.mkdir(parents=True, exist_ok=True)
    sword_files = sorted(p.name for p in src_sword.glob('*.nutexb'))
    require(len(sword_files) > 0, 'No sword textures found in mythra skin')
    for name in sword_files:
        shutil.copy2(src_sword / name, dst_sword / name)
    copied['sword_textures'] = len(sword_files)

    # Costume-specific banks and trails are written by themes.build().
    # Never replace the shared bank: c00-c05 must keep vanilla effects.

    return copied


def build_ui():
    """Deploy G&W portraits for both Pyra slots and the Mythra c06 skin."""
    copied = {'eflame_c06': [], 'eflame_c07': [], 'elight_c06': []}
    dst_ui = MOD / 'ui/replace_patch/chara'
    for slot, gw_slot in COSTUMES.items():
        suffix = slot[1:]
        for category in (0, 1, 2, 3, 4, 6):
            # Vanilla black artwork provides distinct body and outline shading.
            src_file = EXPORT / f'ui/replace/chara/chara_{category}/chara_{category}_gamewatch_00.bntx'
            require(src_file.is_file(), f'G&W UI file missing: {src_file}')
            # Stage select/replay only has the "only" variant in the base game.
            variants = ('only',) if category == 6 else ('first', 'only')
            for variant in variants:
                rel = f'chara_{category}/chara_{category}_eflame_{variant}_{suffix}.bntx'
                target = dst_ui / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, target)
                require(sha(target) == sha(src_file), f'UI copy failed: {rel}')
                copied[f'eflame_{slot}'].append(rel)

    # 2. Mythra c06 UI portraits
    src_mythra_ui = MYTHRA_SKIN_DIR / 'ui/replace_patch/chara'
    require(src_mythra_ui.is_dir(), f'Mythra UI directory missing at {src_mythra_ui}')
    for src_file in src_mythra_ui.rglob('*.bntx'):
        rel = src_file.relative_to(src_mythra_ui)
        target = dst_ui / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, target)
        copied['elight_c06'].append(str(rel).replace('\\', '/'))

    return copied


def build_name_database():
    """Route Pyra/G&W and Mythra c06/c07 to their costume-specific message indices."""
    rel = 'ui/param/database/ui_chara_db.prc'
    tree = prc.read(EXPORT / rel)
    original = prc.read(EXPORT / rel)
    changes = []
    target_names = {('str', x) for x in (
        'eflame_first', 'eflame_only', 'elight_first', 'elight_only', 'element')}
    for _, rows in tree[1]:
        if rows[0] != 'list':
            continue
        for row in rows[1]:
            fields = dict(row[1])
            if fields.get(prc.hash40('name_id')) not in target_names:
                continue
            for slot in COSTUMES:
                key = prc.hash40(f'n{slot[1:]}_index')
                require(key in fields, f'missing name index {slot}')
                row[1][:] = [(k, ('u8', int(slot[1:]))) if k == key else (k, v)
                             for k, v in row[1]]
                changes.append(f'{fields[prc.hash40("name_id")][1]}/{slot}')
    require(len(changes) == len(target_names) * len(COSTUMES),
            'unexpected Pyra/Mythra UI name database entries')
    target = MOD / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(prc.write(tree))
    require(prc.read(target) == tree, 'name database round trip failed')
    # Verify every other field and row against the original.
    for (_, old_rows), (_, new_rows) in zip(original[1], tree[1]):
        for old, new in zip(old_rows[1], new_rows[1]):
            name = dict(old[1]).get(prc.hash40('name_id'))
            allowed = {prc.hash40('n06_index'), prc.hash40('n07_index')} if name in target_names else set()
            require([(k,v) for k,v in old[1] if k not in allowed] ==
                    [(k,v) for k,v in new[1] if k not in allowed], 'unrelated UI field changed')
    return {'path': rel, 'changes': changes, 'sha256': sha(target)}


def build_vs_portraits():
    """Compose both starting orders in the game's original chara_3 containers."""
    from PIL import Image
    import tempfile
    result = []
    ui = MOD / 'ui/replace_patch/chara/chara_3'
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        for slot in COSTUMES:
            suffix = slot[1:]
            images = {}
            for fighter in ('eflame', 'elight'):
                source = ui / f'chara_3_{fighter}_only_{suffix}.bntx'
                if not source.exists():
                    source = EXPORT / f'ui/replace_patch/chara/chara_3/chara_3_{fighter}_only_{suffix}.bntx'
                themes.convert(source, temp / f'{fighter}.png')
                image = Image.open(temp / f'{fighter}.png').convert('RGBA')
                # The costume portrait already carries the body/outline palette.
                images[fighter] = image.crop(image.getbbox())
            for starter in ('eflame', 'elight'):
                relative = f'chara_3/chara_3_{starter}_first_{suffix}.bntx'
                stock = EXPORT / 'ui/replace_patch/chara' / relative
                raw = stock.read_bytes()
                brti, = themes.brtis(raw)
                width, height = themes.u32(raw, brti+0x24), themes.u32(raw, brti+0x28)
                canvas = Image.new('RGBA', (width, height))
                # Retain the original combined canvas and place the selected fighter
                # in front, with their partner visible behind them.
                other = 'elight' if starter == 'eflame' else 'eflame'
                for fighter, left, top, max_w, max_h in (
                        (other, .43, .03, .54, .92), (starter, .02, .12, .66, .88)):
                    image = images[fighter].copy()
                    image.thumbnail((int(width*max_w), int(height*max_h)), Image.Resampling.LANCZOS)
                    canvas.alpha_composite(image, (int(width*left), int(height*top)))
                canvas.save(temp / 'pair.png')
                fmt = themes.BNTX_FORMATS[themes.u32(raw, brti+0x1c)]
                themes.convert(temp/'pair.png', temp/'pair.bntx', fmt)
                data = bytearray(raw)
                themes.replace_bntx_texture(data, brti, (temp/'pair.bntx').read_bytes())
                target = MOD / 'ui/replace_patch/chara' / relative
                target.write_bytes(data)
                # Deliver a PNG preview of the actual encoded texture.
                preview = Path(__file__).parent / 'assets/vs_previews' / f'{starter}_{suffix}.png'
                preview.parent.mkdir(parents=True, exist_ok=True)
                themes.convert(target, preview)
                result.append({'path': target.relative_to(MOD).as_posix(), 'sha256': sha(target)})
    return result


def build_names():
    """Package and validate the costume-specific ARCropolis message patch."""
    rel = 'ui/message/msg_name.xmsbt'
    source = Path(__file__).parent / rel
    root = ET.parse(source).getroot()
    costume_names = {'c06': 'Ursula', 'c07': 'Wilhelmine'}
    target_names = ('eflame_first', 'eflame_only', 'elight_first', 'elight_only', 'element')
    expected = {f'nam_chr{category}_{slot[1:]}_{name_id}':
                costume_names[slot].upper() if category == 1 else costume_names[slot]
                for slot in COSTUMES for category in range(4)
                for name_id in target_names}
    entries = root.findall('entry')
    actual = {entry.get('label'): entry.findtext('text') for entry in entries}
    require(root.tag == 'xmsbt' and len(entries) == len(expected) and actual == expected,
            'msg_name.xmsbt does not contain the expected costume name overrides')
    target = MOD / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    require(sha(source) == sha(target), 'message patch copy failed')
    return {'path': rel, 'entries': actual, 'sha256': sha(target)}


def build_config_json():
    """Write the mod's `config.json`: the files this mod adds, per costume group.

    # How ARCropolis groups files (0.11.0 correction)

    `data.arc` loads a fighter's files through one directory entry per costume,
    `fighter/<fighter>/c0N`, which lists every file that colour needs: body model,
    body motion, *and each article's model and motion*. `fighter/eflame/model/
    normal_weapon/c06` is a path, not one of those entries. 0.9.0 declared such
    paths under `new-dir-infos`, i.e. told ARCropolis to invent eight load groups
    the game never asks for, and then attached the files to them. That produced
    "Cannot get file info range" and a null read in `fighter_initialize_object_data`
    (crash 01790691291), and with a donor base a crash inside ARCropolis
    (01790692083). The files were never in the group the fighter actually loads.

    The working clone pack (`src/mgw_standalone/staging/p8-j0bpxve3/.../
    config.json`) shows the correct shape: its keys are the costume groups
    (`fighter/mgw_mythra/c00`) and its values are full file paths anywhere in the
    tree (`effect/fighter/mgw_mythra/...`). It needed `new-dir-infos` only because
    its whole fighter was new. Here every costume group already exists, so
    `new-dir-infos` is empty and each new file is added to `fighter/eflame/c0N`.

    Only files the base game does not have are declared: the article's tree for
    every slot and the Judge probe clip for c06/c07. Everything else this mod
    ships replaces an existing file and needs no declaration.
    """
    declared = {}

    def add(slot, path):
        require((MOD / path).is_file(),
                f'config.json would declare {path}, which the build did not write')
        require(not (EXPORT / path).exists(),
                f'{path} exists in the base game, so it is not a new file')
        declared.setdefault(f'fighter/eflame/{slot}', []).append(path)

    for slot, gw_slot in ARTICLE_SLOTS.items():
        for article in ARTICLES:
            for kind in ('model', 'motion'):
                for name in article_files(article, kind, gw_slot):
                    add(slot, f'fighter/eflame/{kind}/{article}/{slot}/{name}')
    # The esword article's own clips replace vanilla files, so they need no
    # declaration - except the jab's, which are new names carrying a different
    # blade size. See tools/build_esword_pose.py for why they exist.
    for slot in COSTUMES:
        for clip in esword_pose.JAB_STATES:
            add(slot, f'fighter/eflame/motion/esword/{slot}/{clip}.nuanmb')
    for slot in COSTUMES:
        for name in PROBE_FILES:
            add(slot, f'fighter/eflame/motion/body/{slot}/{name}')
    # Little Mac's angled forward-smash clips, `c03attacks4hi` / `c03attacks4lw`.
    # New file names in each slot, so they need declaring like any other: without
    # this the motion entries name files the loader is never told about, which is
    # the silent "animates but does nothing" shape. `add()` re-checks that each
    # one is genuinely absent from the base game, and the agreement check below
    # catches any clip that was written but not declared.
    for slot in COSTUMES:
        for name in littlemac_s4.new_clip_names(EXPORT / f'fighter/eflame/motion/body/{slot}'):
            add(slot, f'fighter/eflame/motion/body/{slot}/{name}')
    for slot in COSTUMES:
        paths = [MOD / f'effect/fighter/elight/ef_elight_{slot}.eff']
        paths += sorted((MOD / f'effect/fighter/elight/trail_{slot}').glob('*.nutexb'))
        for path in paths:
            require(path.is_file(), f'missing one-slot effect asset: {path}')
            rel = path.relative_to(MOD).as_posix()
            require(not (EXPORT / rel).exists(), f'one-slot effect unexpectedly replaces vanilla: {rel}')
            declared.setdefault(f'fighter/elight/{slot}', []).append(rel)
    for slot in COSTUMES:
        paths = sorted((MOD / f'effect/fighter/eflame/trail_{slot}').glob('*.nutexb'))
        for path in paths:
            require(path.is_file(), f'missing eflame trail asset: {path}')
            rel = path.relative_to(MOD).as_posix()
            require(not (EXPORT / rel).exists(), f'eflame trail unexpectedly replaces vanilla: {rel}')
            declared.setdefault(f'fighter/eflame/{slot}', []).append(rel)
    # Recipient-owned banks: one reachable file per gated costume.
    for slot in COSTUMES:
        add(slot, f'effect/fighter/eflame/ef_eflame_{slot}.eff')
    declared = {k: sorted(v) for k, v in sorted(declared.items())}

    for slot_id in range(8):
        slot = f'c{slot_id:02}'
        for kind in ('model', 'motion'):
            folder = MOD / f'fighter/elight/{kind}/pgwr_hero_fireball/{slot}'
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    declared.setdefault(f'fighter/elight/{slot}', []).append(path.relative_to(MOD).as_posix())
    for slot in COSTUMES:
        for _, _, clip in hero_n.motions():
            declared.setdefault(f'fighter/elight/{slot}', []).append(f'fighter/elight/motion/body/{slot}/{clip}')
    if SNAKE_NEUTRAL_B:
        for slot, rel in snake_n.declared_clips() + snake_n.declared_pin_files():
            declared.setdefault(f'fighter/eflame/{slot}', []).append(rel)
    if HERO_SIDE_B:
        for slot in COSTUMES:
            for _, _, clip in hero_s.motions():
                declared.setdefault(f'fighter/elight/{slot}', []).append(f'fighter/elight/motion/body/{slot}/{clip}')
        for slot_id in range(8):
            slot = f'c{slot_id:02}'
            for article in ('pgwr_hero_spark', 'pgwr_hero_lightning'):
                declared.setdefault(f'fighter/elight/{slot}', []).append(
                    f'fighter/elight/motion/{article}/{slot}/motion_list.bin')
    declared = {k: sorted(v) for k, v in sorted(declared.items())}

    # Every file under the mod that the base game lacks must be declared, and
    # nothing else: an undeclared new file is the "silently not loaded" failure.
    new_files = sorted(str(p.relative_to(MOD)).replace('\\', '/')
                       for p in MOD.rglob('*') if p.is_file()
                       and p.name not in ('config.json', 'info.toml')
                       # XMSBT is a patch consumed by ARCropolis, not an ARC file.
                       and p.relative_to(MOD).as_posix() != 'ui/message/msg_name.xmsbt'
                       and not (EXPORT / p.relative_to(MOD)).exists())
    require(new_files == sorted(f for fs in declared.values() for f in fs),
            'config.json and the new files on disk disagree')

    config = {
        'new-dir-infos': [],
        'new-dir-infos-base': {},
        'new-dir-files': declared,
        'share-to-vanilla': {},
        'share-to-added': {},
    }
    out = MOD / 'config.json'
    out.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    require(json.loads(out.read_text(encoding='utf-8')) == config, 'config.json did not survive the write')
    return {'sha256': sha(out), 'groups': {k: len(v) for k, v in declared.items()}}


def main():
    require(EXPORT.is_dir(), f'game dump not found at {EXPORT} (set MGW_EXPORT)')
    # Refuse an incomplete Snake package before touching a previous build.
    if SNAKE_NEUTRAL_B:
        require(snake_sound.SQB.is_file(), 'Snake sequence dump missing; see dumps/MISSING.md')
        snake_n.checked_inputs()
        snake_n.pin_inputs()
        snake_n.checked_lower_inputs()
        require(snake_n.LOWER_RUNTIME_TRANSLATED, 'Snake lower gait dispatch/ACMD remains unported; CURRENT_INSTALL.md')
    safe_rmtree(PACKAGE)
    MOD.mkdir(parents=True)
    labels = load_labels()
    record = {}
    for slot, gw_slot in COSTUMES.items():
        record[slot] = {'model': build_model(slot, gw_slot), 'motion': build_motion(slot, gw_slot, labels),
                        'motion_params': build_motion_params(slot, gw_slot),
                        # The Aegis sword is hidden from the article's own clips, not from
                        # its model: see tools/build_esword_pose.py for why.
                        'esword': esword_pose.build_slot(slot, MOD)}
    # All eight slots, not just c06/c07: see ARTICLE_SLOTS.
    record['article'] = {slot: {article: build_article(article, slot, gw_slot)
                                for article in ARTICLES}
                         for slot, gw_slot in ARTICLE_SLOTS.items()}
    record['expression_vl'] = build_expression_vl()
    # Hero's Spin on Mythra c06/c07. The Pyra/G&W half above is untouched by
    # this: it writes into `fighter/elight`, which nothing else here opens.
    record['hero_spin'] = {slot: hi3.build_slot(slot, MOD)
                           for slot in COSTUMES}
    # Corrin Up Air and Luigi Down Throw on Mythra c06/c07.
    record['mythra_moves'] = {slot: mythra_moves.build_slot(slot, MOD)
                              for slot in COSTUMES}
    # The dark donor, then both themes and their costume-specific effect banks.
    record['mythra_skin'] = build_mythra_skin()
    record['ui'] = build_ui()
    record['color_themes'] = themes.build(EXPORT, MOD, PACKAGE, MYTHRA_SKIN_DIR)
    record['hero_neutral_b'] = hero_n.build(MOD)
    (MOD / 'hero_neutral_b_assets.json').replace(PACKAGE / 'hero_neutral_b_assets.json')
    record['hero_neutral_b_sound'] = hero_sound.build(MOD)
    (MOD / 'hero_neutral_b_sound.json').replace(PACKAGE / 'hero_neutral_b_sound.json')
    if HERO_SIDE_B:
        # Appends to the motion lists written just above; sounds came with neutral-B's full banks.
        hero_s.build(MOD)
        (MOD / 'hero_side_b_assets.json').replace(PACKAGE / 'hero_side_b_assets.json')
        record['hero_side_b'] = json.loads((PACKAGE / 'hero_side_b_assets.json').read_text())
        # One-slot banks read trails from trail_<slot>/, declared with the bank below.
        for slot in COSTUMES:
            for path in hero_s_effects.trail_files():
                dest = MOD / f'effect/fighter/elight/trail_{slot}' / path.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
                require(sha(dest) == sha(path), f'trail copy differs: {path.name}')
    # G&W / Diddy / Chrom sounds into Pyra's own c06/c07 banks, so the ported
    # scripts play the donor's real sounds instead of eflame stand-ins.
    # Retires gen_acmd.py's R2 substitution and acmd::monkey_flip's SOUND_MAP.
    record['donor_sound'] = donor_sound.build(MOD)
    (MOD / 'donor_sound.json').replace(PACKAGE / 'donor_sound.json')
    if SNAKE_NEUTRAL_B:
        record['snake_neutral_b'] = snake_n.build(MOD)
        (PACKAGE / 'snake_neutral_b_assets.json').write_text(json.dumps(record['snake_neutral_b'], indent=2) + '\n')
        record['snake_neutral_b_sound'] = snake_sound.build(MOD)
        (MOD / 'snake_neutral_b_sound.json').replace(PACKAGE / 'snake_neutral_b_sound.json')
    # R.O.B. down tilt sounds append last: they chain onto whatever the merges above wrote.
    record['robot_dtilt_sound'] = robot_sound.build(MOD)
    (MOD / 'robot_dtilt_sound.json').replace(PACKAGE / 'robot_dtilt_sound.json')
    # Snake up tilt sounds append after the R.O.B. ones: they chain onto whatever the
    # merges above wrote into the same Pyra banks. Runs whether or not
    # PGWR_SNAKE_NEUTRAL_B is set, because the up tilt is unconditional (its own ACMD
    # module and its own clip are not behind the neutral-B feature).
    record['snake_uptilt_sound'] = snake_uptilt_sound.build(MOD)
    (MOD / 'snake_uptilt_sound.json').replace(PACKAGE / 'snake_uptilt_sound.json')
    # Little Mac's effect bank for the forward smash's `littlemac_attack_line`.
    record['littlemac_fsmash_effect'] = littlemac_s4_eff.build(MOD, generated_dir=PACKAGE / 'generated_effects')
    for slot in COSTUMES:
        recipient = MOD / f'effect/fighter/elight/ef_elight_{slot}.eff'
        output = PACKAGE / 'generated_effects' / f'ef_elight_{slot}.eff'
        hero_effects.merge(recipient, output)
        output.replace(recipient)
        if HERO_SIDE_B:
            output = PACKAGE / 'generated_effects' / f'ef_elight_{slot}_side_b.eff'
            hero_s_effects.merge(recipient, output)
            output.replace(recipient)
    record['vs_portraits'] = build_vs_portraits()
    record['name_database'] = build_name_database()
    record['names'] = build_names()
    # PGWR_UI_BASELINE=<mod dir of an earlier package> keeps that package's two name files, so a
    # release whose scope is another change does not silently carry the queued naming work
    # (AGENTS.md rule 23). Unset (the default) builds the current names as before.
    ui_baseline = os.environ.get('PGWR_UI_BASELINE')
    if ui_baseline:
        record['ui_baseline'] = {}
        for rel in ('ui/param/database/ui_chara_db.prc', 'ui/message/msg_name.xmsbt'):
            src = Path(ui_baseline) / rel
            require(src.is_file(), f'PGWR_UI_BASELINE has no {rel}')
            shutil.copy2(src, MOD / rel)
            record['ui_baseline'][rel] = sha(MOD / rel)
    # Recorded with mesh names resolved against c06's model, so a future dump that
    # changes the table shows up as a reviewable diff instead of a silent change on
    # hardware. The table stores lowercased mesh names; see tools/visibility_table.py.
    record['expression_vl']['visibility_groups'] = vis.summarise_groups(
        MOD / 'fighter/eflame/param/expression_vl.prc',
        vis.mesh_names(MOD / 'fighter/eflame/model/body/c06/model.numshb'))
    record['config_json'] = build_config_json()
    (MOD / 'info.toml').write_text(
        'display_name = "Pyra G&W reskin"\n'
        'authors = "LAURlN"\n'
        # From Cargo.toml (VERSION), so info.toml cannot fall behind the plugin:
        # 0.20.0-0.20.3 shipped a hard-coded "0.19.0" here.
        f'version = "{VERSION}"\n'
        'description = "Pyra c06/c07 are Mr. Game & Watch: model, G&W own motion list, '
        'IK/param files and mesh-visibility groups, plus the ported moves (see the plugin crate). '
        '0.11.0 registered G&W\'s normal_weapon article (stool, manhole cover, fishbowl, turtle, '
        'spray) on eflame from this mod\'s own plugin via smashline clone_weapon, and 0.12.0 adds '
        'the breath article, so up air shoots G&W\'s projectile instead of doing nothing. Both '
        'articles\' files are added to every Pyra costume group through config.json. '
        '0.15.0 gives c06/c07 Diddy\'s Monkey Flip on side-B (eleven custom statuses, the donor\'s '
        'ACMD, twelve retargeted clips), replacing the Judge probe that used to own that button. '
        '0.19.0 gives c06/c07 G&W\'s own up special, Fire: his three statuses, his scripts and '
        'his rescue and parachute articles."\n'
        'category = "Fighter"\n', encoding='utf-8')
    record['files'] = {str(p.relative_to(PACKAGE)).replace('\\', '/'): sha(p)
                       for p in sorted(PACKAGE.rglob('*')) if p.is_file()}
    (Path(__file__).parent / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if k != 'files'}, indent=2))
    print(f'{len(record["files"])} files in {PACKAGE}')


if __name__ == '__main__':
    main()
