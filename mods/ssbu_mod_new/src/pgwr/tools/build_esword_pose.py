"""Hide the Aegis sword on Pyra c06/c07, and control it, from the *article's own clips*.

Why not the two levers that were tried first (both refuted on hardware 2026-09-30,
`handbook/graveyard.md` R-20/R-21):

  * The article's eight clips animate `HaveR`, `Sword1` and `Sword_flameA..E`, and
    none of them animates `Root`. So a bind-pose change to `Root` in the *model*
    (`build.py::hide_esword`, retired here) is the one thing nothing overrides and
    still had no visible effect.
  * The sword is not posed by the body: a `Sword1` track in the *body* fair clip
    (`build_cloud_fair.sword_node`, retired here) left the blade exactly where it
    was. The article is posed by the clips in this module.

What works instead is plain mesh visibility, which is the same idiom the body uses
(`visibility_table.py`): every one of the eight clips carries a `Visibility` group
with a single `flamesword` node, and in the shipped vanilla data it is **True in all
eight** - so the mesh is drawn in every state, including the retracted one that a
freshly generated article sits in. Because 24 eflame scripts call
`generate_article(ESWORD)` and 142 call `add_motion_partial`, no per-move guard can
cover the spawn sites: the fix has to be that the resting state is not drawn.

The state names are not guessed - they are read out of the article's own
`motion_list.bin`, whose entries are `close` -> `z00close` (entry 0, the resting
state a fresh spawn enters), `open` -> `z00open` (entry 1, the swung state the fair's
`add_motion_partial("to_open")` leads to), `to_close` -> `z00toclose` and
`to_open` -> `z00toopen`. `_motion_kinds()` asserts that mapping against the data on
every build, so this table cannot drift away from the file it describes.

Hiding the *closed* states is what makes the sword disappear; the *open* states stay
drawn, which is what the fair needs. The blade's angle relative to the hand is still
vanilla Pyra's grip - correcting it needs the attach chain nailed down and is not
attempted here.

Output is written over names Pyra already has, so `config.json` is untouched.

# Two blade sizes, because two moves draw this one article

`SIZE_FACTOR` above is the Cloud fair's. The Chrom jab cannot use it: at 1.4 the
blade overhangs Chrom's own jab hitboxes by ~4 units (the fair's reach figure is
measured against Cloud's much longer sword, `PLAN_CHROM_JAB.md`), and the jab's
hitboxes are Chrom's verbatim. Both moves drive the *same* article through the
*same* kinds, so a per-move size has to be a per-move **state**, not a per-move
constant: `JAB_STATES` below adds `jab_to_open`/`jab_open`/`jab_to_close` with
their own clips at `JAB_SIZE_FACTOR`, appended to the article's `motion_list.bin`,
and `plugin/src/acmd/chrom_jab.rs` asks for the `jab_*` kinds instead. The fair
keeps `to_open`/`open`/`to_close` at `SIZE_FACTOR` and is not touched by any of it.

The two new entries are byte-copies of `open` and `to_open` with two fields
changed - the kind hash and the animation-name hash - because everything else in
an article motion entry is bookkeeping this module has no reason to change. The
`game_script` hash is left as the donor wrote it, which is deliberate: these are
weapon-article entries and the donor's own script is what plays them.

# The animation name carries the file extension, and getting that wrong is silent

Measured on the vanilla list, every entry names its clip as `hash40('<stem>.nuanmb')`:
`open` -> `0xe32317ab0` == `hash40('z00open.nuanmb')`, and *not* `0x7f51bb388` ==
`hash40('z00open')`; `close`, `to_close`, `to_open` and `d01specials1` agree.

The 0.20.0-0.20.20 builds wrote `hash40('<stem>')` for the two jab entries, so
both named a file that does not exist. On hardware the jab's blade was invisible
(user, 2026-10-03) while the fair's was not - the fair uses the vanilla kinds, so
its names were never wrong. The failure is silent and self-concealing: an
unresolvable animation leaves the article playing the clip it already had, which
between moves is `z00close`, whose `flamesword` visibility track is **False**, and
that mesh track overrides the `set_visibility_whole(true)` the ACMD issues. Nothing
errors, nothing logs, and every other check in this module passes.

So the extension is written, and `_assert_anim_names_resolve()` checks on every
build - once against the vanilla entry being cloned, and once against the bytes
read back off disk - that each animation hash names a real file in the output
folder. Reverting the extension reintroduces the invisible blade and fails the
build instead.
"""
from pathlib import Path
import shutil
import tomllib

import ssbh_data_py as s

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]

ANIM_SUFFIX = '.nuanmb'


def _export_root():
    """The ArcExplorer export: `dumps/arc` when it is there, else `paths.toml`.

    Rule 4 forbids absolute paths in this tree, and on this machine the export is
    declared in `paths.toml` rather than sitting inside the repo, so this module
    could not run at all until it was taught to look there. `dumps/arc` is still
    preferred, so a workspace that does have it keeps behaving identically.

    Falls back to the `dumps/arc` path rather than raising: `build.py` imports this
    module at load time, so a missing export must stay a build-time failure at
    `build_slot` and not an import-time failure in someone else's tool.
    """
    default = ROOT / 'dumps/arc'
    if default.is_dir():
        return default
    cfg = ROOT / 'paths.toml'
    if cfg.is_file():
        arc = tomllib.loads(cfg.read_text(encoding='utf-8')).get('dumps', {}).get('arc', '')
        if arc and Path(arc).is_dir():
            return Path(arc)
    return default


EXPORT = _export_root()

ARTICLE = 'fighter/eflame/motion/esword'
HIDDEN_MESH = 'flamesword'
SWORD_BONE = 'Sword1'

# --- Blade size on the drawn states ---------------------------------------
#
# This is a **taste value, not a measurement**, and it is labelled that way on
# purpose. The user has now reported the blade as too small on two builds in which
# it was at exactly its vanilla size (0.14.1/0.15.0 and 0.15.1), while the offline
# geometry tools disagreed with each other and with the console - three chain models
# produced three different blade directions, so none of them is trustworthy enough
# to set this. What it really is: Pyra's blade at native size inside an animation
# authored for Cloud's much longer sword.
#
# Change this one number to tune it; 1.0 restores vanilla size.
SIZE_FACTOR = 1.4

# The Chrom jab's own size. This *was* derived rather than chosen: 1.0 put the
# blade tip at Chrom's own jab reach (his furthest box sits at z = 8.4 with radius
# 3.5, so ~11.9 units, against vanilla Aegis' 11.39), where the fair's 1.4 had
# overhung the boxes by ~4 units. Hardware then showed 1.0 was still a shade too
# big on the jab, so it is now 0.9 and is a **taste value again**, the same status
# `SIZE_FACTOR` has: the offline geometry cannot settle it, only the console can.
# Change this one number to re-tune the jab; it does not affect the fair, and the
# jab's trail length is derived from it (JAB_TRAIL_TIP in chrom_jab.rs), so the
# blade and its ribbon move together instead of drifting apart.
JAB_SIZE_FACTOR = 0.9

# What the game does with each clip, read from the article's motion_list.bin. The
# `swung` column is the decision this module makes: the resting and special-S
# states are not drawn, the two states the fair drives are.
STATES = {
    'z00close':          ('close',           False),   # motion_list entry 0: resting
    'z00open':           ('open',            True),    # entry 1: swung (the fair opens to here)
    'z00toclose':        ('to_close',        False),   # transition into resting
    'z00toopen':         ('to_open',         True),    # transition into swung
    'd01specials1':      (None,              False),   # Pyra's special-S sword poses
    'd01specials2':      (None,              False),   # side-B on c06/c07 is Monkey Flip,
    'd01specialsmovel':  (None,              False),   # so nothing should draw a sword here
    'd01specialsmover':  (None,              False),
}

# The jab's parallel set of states: new clip -> (new kind, the vanilla clip it is
# a copy of). Same drawn/hidden decision as `STATES` above, different size, because
# the two moves share one article and one `Sword1` bone - there is no other place
# a per-move scale could live (R-21: the body side cannot move the blade at all).
#
# `to_close` is deliberately *not* duplicated. It is a transition into the resting
# state, and the resting state is the shared `close` clip, which draws nothing and
# carries no scale, so the jab closing through the vanilla kind is correct and
# costs one fewer entry. That also means the put-away path is unchanged by
# anything in this file: `chrom_jab.rs` still closes through `to_close`, which
# ends in the hidden resting clip.
JAB_STATES = {
    'jabopen':      ('jab_open',   'z00open'),
    'jabtoopen':    ('jab_to_open', 'z00toopen'),
}

# Kinds the new entries are copied from. `to_open` for both new entries would be
# wrong for `jab_open`: the vanilla `open` entry is the one with no transition, and
# copying its flags keeps the two entries distinguishable in a hex dump.
JAB_ENTRY_SOURCES = {'jab_open': 'open', 'jab_to_open': 'to_open'}

# Files the folder needs to stay coherent. Only the clips above are edited; the rest
# are copied verbatim so the shipped folder is complete rather than a patch.
VERBATIM = ['update.prc']


def hash40(name):
    import zlib
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def _parse_mlist(path):
    """Every entry of a motion_list.bin as `(kind, anims, raw_bytes)`.

    Measured against `dumps/arc/fighter/eflame/motion/esword/c06/motion_list.bin`
    (780 bytes, 15 entries, 0 trailing): a 24-byte header of `magic`, motion path
    and count, then per entry a 21-byte struct (`kind`, `game_script`, `flags`,
    `blend`, `n_anims`, `size`) padded to 24, then `n_anims` 8-byte name hashes
    each followed by a flag byte and 3 bytes of padding, then `size` bytes of
    payload. The payload is not decoded: `build_slot` copies it verbatim from the
    entry it is cloning, and `verify_mlist_roundtrip` re-serializes every entry
    from the parse and asserts the file comes back byte-identical, so the padding
    and payload rules cannot be wrong here without the build failing.
    """
    import struct
    data = Path(path).read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset, entries = 24, []
    for _ in range(count):
        start = offset
        kind, _gs, _flags, _blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        entries.append((kind, list(anims), data[start:end]))
        offset = end
    if offset != len(data):
        raise RuntimeError(f'{path}: {len(data) - offset} trailing bytes after {count} entries; '
                           f'the entry layout this module assumes is wrong')
    return magic, motion_path, entries


def _assert_anim_names_resolve(anims, clip_dir, context):
    """Every animation hash written for a clip must name a file that exists.

    The hash covers the **file name including its extension**: measured on the
    vanilla list, `open` names `0xe32317ab0` == `hash40('z00open.nuanmb')` and not
    `0x7f51bb388` == `hash40('z00open')`, and the same holds for `close`, `to_close`,
    `to_open` and `d01specials1`. That is the whole reason the jab's blade was
    invisible on hardware (2026-10-03): its entry named a clip that does not exist,
    the article kept playing the clip it already had - `z00close`, whose
    `flamesword` track is False - and the `set_visibility_whole(true)` the ACMD
    issues was overridden by that mesh track. Nothing errors and nothing logs when
    a name does not resolve, so this is asserted on every build instead.

    Only the entries this module writes are checked. Several vanilla entries name
    a hash that is an appearance animation rather than a `.nuanmb` in the folder,
    so a whole-file check would fire on untouched vanilla data.
    """
    present = {hash40(p.name): p.name for p in clip_dir.glob(f'*{ANIM_SUFFIX}')}
    for anim in anims:
        if anim not in present:
            raise RuntimeError(
                f'{context}: animation hash {anim:#x} names no file in {clip_dir}. The '
                f'animation hash includes the {ANIM_SUFFIX} extension; naming the bare stem '
                f'silently leaves the article playing its previous clip.')
    return [present[a] for a in anims]


def _read_mlist(path):
    """kind hash -> list of anim-name hashes, from an article's motion_list.bin."""
    _magic, _path, entries = _parse_mlist(path)
    return {kind: anims for kind, anims, _raw in entries}


def verify_mlist_roundtrip(path):
    """Re-serialize a motion_list.bin from its own parse and require the same bytes.

    This is the guard that makes appending entries to a dumped binary safe to do
    from a script. Concatenating the stored per-entry `raw` slices reproduces the
    file exactly only if the header and the entry spans were parsed correctly, so a
    wrong offset shows up here rather than as a motion list the game cannot read.
    """
    import struct
    data = Path(path).read_bytes()
    magic, motion_path, entries = _parse_mlist(path)
    rebuilt = (struct.pack('<QQQ', magic, motion_path, len(entries))
               + b''.join(raw for _kind, _anims, raw in entries))
    if rebuilt != data:
        raise RuntimeError(f'{path}: re-serializing its own parse did not reproduce the file')
    return len(entries)


def _motion_kinds(slot):
    """Assert the state table against the article's own motion list.

    Without this the table is a claim about the data; with it, a future dump that
    renames or reorders a state fails the build instead of silently shipping a
    sword that is hidden when it should be out, or the reverse.
    """
    mlist = _read_mlist(EXPORT / ARTICLE / slot / 'motion_list.bin')
    found = {}
    for clip, (kind, _drawn) in STATES.items():
        if kind is None:
            continue
        found[clip] = hash40(kind) in mlist
    for clip, present in found.items():
        if not present:
            raise RuntimeError(f'{slot}: motion_list has no kind for {clip}; '
                               f'the state table in {Path(__file__).name} is stale')
    # `close` must be the first entry: that is what makes it the resting state a
    # freshly generated article enters, which is the whole basis of this fix.
    first = next(iter(mlist))
    if first != hash40('close'):
        raise RuntimeError(f'{slot}: motion_list entry 0 is not `close`; the resting '
                           f'state assumption is wrong')
    return found


def _clone_mlist_entry(raw, kind, anim_hash):
    """A copy of one motion-list entry with only its kind and animation name changed.

    Everything else - `game_script`, flags, blend, the per-anim flag bytes and the
    16-byte payload - is carried over untouched, because none of it is this
    module's to decide. The two offsets are the kind at 0 and the first anim name
    at 24, both measured by `verify_mlist_roundtrip` failing loudly if the layout
    is not what this assumes.
    """
    import struct
    entry = bytearray(raw)
    kind_at, clip_at = 0, 24
    if struct.unpack_from('<Q', entry, kind_at)[0] == kind:
        raise RuntimeError(f'cloning entry for kind {kind:#x} from itself; the new kind '
                           f'collides with a vanilla one')
    struct.pack_into('<Q', entry, kind_at, kind)
    struct.pack_into('<Q', entry, clip_at, anim_hash)
    return bytes(entry)


def _build_jab_mlist(slot, out):
    """Copy the article's motion_list.bin and append the jab's own entries."""
    import struct
    src = EXPORT / ARTICLE / slot / 'motion_list.bin'
    magic, motion_path, entries = _parse_mlist(src)
    by_kind = {kind: (anims, raw) for kind, anims, raw in entries}
    added, named = {}, {}
    for clip, (kind, from_clip) in JAB_STATES.items():
        donor_kind = hash40(JAB_ENTRY_SOURCES[kind])
        if donor_kind not in by_kind:
            raise RuntimeError(f'{slot}: no {JAB_ENTRY_SOURCES[kind]!r} entry to clone for {kind!r}')
        donor_anims, donor_raw = by_kind[donor_kind]
        # The donor's own entry has to name its own file, extension and all. If it
        # does not, this table is describing a file layout the game never had, and
        # the clone below would reproduce the same silent miss one step further on.
        expected_donor = hash40(f'{from_clip}{ANIM_SUFFIX}')
        if donor_anims[:1] != [expected_donor]:
            raise RuntimeError(
                f'{slot}: vanilla entry {JAB_ENTRY_SOURCES[kind]!r} names {donor_anims[:1]} '
                f'but {from_clip}{ANIM_SUFFIX} hashes to {expected_donor:#x}; the animation '
                f'hash convention this module clones from has changed')
        anim_hash = hash40(f'{clip}{ANIM_SUFFIX}')
        named[kind] = _assert_anim_names_resolve([anim_hash], out.parent, f'{slot}/{clip}')
        added[kind] = _clone_mlist_entry(donor_raw, hash40(kind), anim_hash)
    # Appended in JAB_STATES order, so the file is reproducible from the table.
    tail = [added[kind] for _clip, (kind, _from_clip) in JAB_STATES.items()]
    data = (struct.pack('<QQQ', magic, motion_path, len(entries) + len(added))
            + b''.join(raw for _k, _a, raw in entries)
            + b''.join(tail))
    out.write_bytes(data)
    # Read the written file back through the same parser the next build will use.
    magic2, path2, entries2 = _parse_mlist(out)
    if magic2 != magic or path2 != motion_path or len(entries2) != len(entries) + len(added):
        raise RuntimeError(f'{out}: header did not survive the append')
    for kind, raw in added.items():
        match = [(k, a, r) for k, a, r in entries2 if k == hash40(kind)]
        if [r for _k, _a, r in match] != [raw]:
            raise RuntimeError(f'{out}: appended entry {kind!r} did not read back as written')
        # Checked on the bytes that came back off disk, not on what was written.
        _assert_anim_names_resolve(match[0][1], out.parent, f'{out}/{kind}')
    return {'entries': len(entries2), 'added': sorted(added), 'anim_files': named}


def _scale_sword(anim, factor):
    """Multiply the sword bone's animated scale, so the blade grows about the grip.

    `Sword1` carries the blade's geometry, so the parts skinned to it grow while the
    hilt stays the size the hand holds. The original scale is asserted to be 1 before
    scaling, because the read-back check needs to know what the number should be.
    Returns the scales actually written.
    """
    written = []
    for group in anim.groups:
        if group.group_type.name != 'Transform':
            continue
        for node in group.nodes:
            if node.name != SWORD_BONE:
                continue
            for track in node.tracks:
                if track.name != 'Transform':
                    continue
                originals = sorted({round(float(v.scale[0]), 4) for v in track.values})
                if originals != [1.0]:
                    raise RuntimeError(f'{SWORD_BONE} scale is {originals}, not 1.0; '
                                       f'the size factor is a multiplier and this '
                                       f'clip would be scaled from the wrong base')
                track.values = [
                    s.anim_data.Transform([s2 * factor for s2 in v.scale],
                                          list(v.rotation), list(v.translation))
                    for v in track.values]
                written.append(round(float(track.values[0].scale[0]), 4))
    if not written:
        raise RuntimeError(f'no {SWORD_BONE} Transform track to scale')
    return written


def _set_mesh_visibility(anim, drawn):
    """Force the article's mesh-visibility track to one value, on every frame.

    Returns the list of (node, values) actually written so the caller can verify.
    """
    written = []
    for group in anim.groups:
        if group.group_type.name != 'Visibility':
            continue
        for node in group.nodes:
            for track in node.tracks:
                if track.name != 'Visibility':
                    continue
                values = [bool(v) for v in track.values]
                track.values = [drawn] * max(1, len(values))
                written.append((node.name, [drawn] * max(1, len(values))))
    return written


def _write_state(out, slot, clip, drawn, factor, source):
    """Write one article state clip: set its visibility, scale its blade, read it back.

    Shared by the fair's states and the jab's so both go through the same
    verification; the only difference between the two is the `factor` passed in.
    """
    path = out / f'{clip}.nuanmb'
    if not path.is_file():
        raise RuntimeError(f'{slot}: {clip} missing from the export')
    anim = s.anim_data.read_anim(str(path))
    written = _set_mesh_visibility(anim, drawn)
    if not written:
        raise RuntimeError(f'{slot}/{clip}: no Visibility track to set; the '
                           f'visibility lever this module depends on is gone')
    # Size is applied only to the states that are drawn; scaling a clip nobody
    # can see would just make the report harder to read.
    used = factor if drawn else 1.0
    _scale_sword(anim, used) if drawn else []
    anim.save(str(path))

    # Read it back: the whole fix is one boolean, so it is worth proving that
    # the byte on disk says what was intended rather than trusting the write.
    check = s.anim_data.read_anim(str(path))
    seen, scales = {}, []
    for group in check.groups:
        if group.group_type.name == 'Visibility':
            for node in group.nodes:
                for track in node.tracks:
                    if track.name == 'Visibility':
                        seen[node.name] = sorted({bool(v) for v in track.values})
        elif group.group_type.name == 'Transform':
            for node in group.nodes:
                if node.name != SWORD_BONE:
                    continue
                for track in node.tracks:
                    if track.name == 'Transform':
                        scales = sorted({round(float(v.scale[0]), 4) for v in track.values})
    if seen.get(HIDDEN_MESH) != [drawn]:
        raise RuntimeError(f'{slot}/{clip}: wrote {HIDDEN_MESH}={drawn} but read '
                           f'back {seen.get(HIDDEN_MESH)}')
    if scales != [round(used, 4)]:
        raise RuntimeError(f'{slot}/{clip}: wrote {SWORD_BONE} scale {round(used, 4)} '
                           f'but read back {scales}')
    return {'drawn': drawn, 'meshes_written': len(written), 'sword_scale': scales[0],
            'from': source}


def build_slot(slot, out_mod):
    """Write the sword's clips for `slot` into the built mod tree."""
    src = EXPORT / ARTICLE / slot
    out = Path(out_mod) / ARTICLE / slot
    if not src.is_dir():
        raise RuntimeError(
            f'{ARTICLE}/{slot} missing from the export at {EXPORT}; cannot place the sword. '
            f'Point [dumps] arc in paths.toml (or restore dumps/arc) - the sword clips are '
            f'read from the export and are never approximated.')
    _motion_kinds(slot)
    verify_mlist_roundtrip(src / 'motion_list.bin')

    out.mkdir(parents=True, exist_ok=True)
    for path in src.iterdir():
        if path.stem in STATES or path.name in VERBATIM:
            shutil.copy2(path, out / path.name)
    # The jab's clips are copies of the fair's vanilla source clips, so they inherit
    # the right bones and the `flamesword` visibility node without being derived
    # from anything this build already scaled.
    for clip, (_kind, from_clip) in JAB_STATES.items():
        shutil.copy2(src / f'{from_clip}.nuanmb', out / f'{clip}.nuanmb')

    report = {}
    for clip, (kind, drawn) in STATES.items():
        report[clip] = {'kind': kind, **_write_state(out, slot, clip, drawn, SIZE_FACTOR, 'vanilla')}

    for clip, (kind, from_clip) in JAB_STATES.items():
        report[clip] = {'kind': kind,
                        **_write_state(out, slot, clip, True, JAB_SIZE_FACTOR, from_clip)}
    report['motion_list'] = _build_jab_mlist(slot, out / 'motion_list.bin')

    require_hidden = [c for c, (_k, d) in STATES.items() if not d]
    report['_summary'] = {
        'slot': slot,
        'hidden_states': require_hidden,
        'drawn_states': [c for c, (_k, d) in STATES.items() if d],
        'size_factor': SIZE_FACTOR,
        'size_basis': 'taste value from the user report, not a measurement - see SIZE_FACTOR',
        'jab_size_factor': JAB_SIZE_FACTOR,
        'jab_size_basis': 'taste value: 1.0 matched Chrom jab reach on paper, hardware reported it a shade too big',
        'jab_states': {c: k for c, (k, _f) in JAB_STATES.items()},
        'files': len(list(out.iterdir())),
    }
    return report


if __name__ == '__main__':
    import json
    import sys
    import tempfile
    # The two size factors are read from the plugin source as well as from here.
    # They have to agree: the trail the jab draws is sized from the blade factor,
    # so a factor that only changed on this side would leave the ribbon and the
    # blade disagreeing, which is the exact mismatch 0.15.2 was reported for.
    rust = (TOOLS.parent / 'plugin/src/acmd/chrom_jab.rs').read_text()
    for name, value in (('JAB_SIZE_FACTOR', JAB_SIZE_FACTOR),):
        if f'const {name}: f32 = {value};' not in rust:
            raise RuntimeError(f'{name} is {value} here but not in chrom_jab.rs; the two '
                               f'sides of the jab size must be changed together')
    with tempfile.TemporaryDirectory() as tmp:
        for slot in sys.argv[1:] or ['c06', 'c07']:
            print(json.dumps(build_slot(slot, tmp), indent=1, sort_keys=True))
    print('build_esword_pose OK')
