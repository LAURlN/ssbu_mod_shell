"""Read and edit `param_visibility_data_body` in a fighter's `param/expression_vl.prc`.

`VisibilityModule::set_int64(hash40("rhand"), hash40("rhand_hammer"))` looks the
pair up in this table: the first hash names a *group*, the second names a *state*
inside it, and the state is the list of meshes that state shows. A fighter whose
file lacks the group does nothing at all, which is why G&W's props were invisible
on `eflame` before 0.7.0 merged his tables in.

Layout, read from G&W's own file rather than guessed:

    param_visibility_data_body        ('struct', [ (key, ('list', [group, ...])), ... ])
    group                             ('struct', [
        (k_name,    ('hash', <group name>)),
        (k_default, ('hash', <default state>)),
        (k_states,  ('list', [state, ...])),
    ])
    state                             ('struct', [
        (k_state,  ('hash', <state name>)),
        (k_meshes, ('list', [('hash', <mesh>), ...])),
    ])

The struct key hashes are the *same* in every group (`k_name`/`k_default`/
`k_states`/`k_state`/`k_meshes`); only the values differ, so this addresses
children by key hash and never by position. That is deliberate: the ordering in
the file is sorted by key hash, and a positional writer breaks the moment a key's
value changes that sort order.

`set_state` clones an existing state's node so the new entry is structurally
identical to the ones already there, and re-sorts each struct's children by key
hash, which `prc.write` requires.
"""
from __future__ import annotations

from pathlib import Path

import prc

K_NAME = 0x267AA281F
K_DEFAULT = 0x5509DBF4D
K_STATES = 0xBD5CFE3F8
K_STATE = 0x56DC044C5
K_MESHES = 0xA377DDA72

# The second key of param_visibility_data_body, the list that follows the groups.
# It is not a visibility group; nothing reads it and nothing writes it.
K_GROUPS = 0x9592D3A65


def _field(struct, key):
    """The value node for `key` in a ('struct', [(k, node), ...]) node."""
    for k, node in struct[1]:
        if k == key:
            return node
    raise KeyError(f'no child {key:#x} in a {len(struct[1])}-field struct')


def _set_field(struct, key, node):
    """Replace one child in place, keeping the list sorted by key hash."""
    rows = [r for r in struct[1] if r[0] != key]
    rows.append((key, node))
    rows.sort(key=lambda r: r[0])
    return ('struct', rows)


def _groups_node(tree):
    return _field(tree, K_GROUPS)


def group_names(tree):
    """Every group name hash in the table, in file order."""
    return [_field(g, K_NAME)[1] for g in _groups_node(tree)[1]]


def find_group(tree, name_hash):
    """The ('struct', ...) node for one group, or None."""
    for g in _groups_node(tree)[1]:
        if _field(g, K_NAME)[1] == name_hash:
            return g
    return None


def state_names(group):
    """State name hashes in one group, in file order."""
    return [_field(s, K_STATE)[1] for s in _field(group, K_STATES)[1]]


def state_meshes(group, state_hash):
    node = _field(group, K_STATES)
    for s in node[1]:
        if _field(s, K_STATE)[1] == state_hash:
            meshes = _field(s, K_MESHES)
            return [m[1] for m in meshes[1]] if meshes[0] == 'list' else []
    return None


def set_state(group, state_hash, mesh_hashes, template_state_hash):
    """Add (or replace) one state in `group`, cloned from an existing state.

    Cloning rather than building a node from scratch is what keeps the new entry
    byte-shaped like its neighbours: the key hashes, the list tag and the child
    order all come from a state that is already in the file. Replacing a state
    that already exists is a no-op on file order, so it is safe to call twice.
    """
    states = _field(group, K_STATES)
    template = next((s for s in states[1]
                     if _field(s, K_STATE)[1] == template_state_hash), None)
    if template is None:
        raise KeyError(f'no template state {template_state_hash:#x} to clone')

    entry = _set_field(
        template,
        K_STATE,
        ('hash', state_hash),
    )
    entry = _set_field(entry, K_MESHES, ('list', [('hash', h) for h in mesh_hashes]))

    if any(_field(s, K_STATE)[1] == state_hash for s in states[1]):
        rows = [entry if _field(s, K_STATE)[1] == state_hash else s for s in states[1]]
    else:
        rows = list(states[1]) + [entry]
    return _set_field(group, K_STATES, ('list', rows))


def read_body(path):
    """The `param_visibility_data_body` node of a file, as a mutable tree.

    `prc.read` returns the root *node* (`('struct', [(key, node), ...])`), not a
    pair, so the root is the thing `_field` is applied to.
    """
    return _field(prc.read(path), prc.hash40('param_visibility_data_body'))


def write_body(path, body):
    """Write a modified body node back into the file, keeping every other key."""
    root = _set_field(prc.read(path), prc.hash40('param_visibility_data_body'), body)
    Path(path).write_bytes(prc.write(root))


def describe(path, labels=None):
    """Human-readable dump: group -> state -> meshes, with names where known."""
    labels = labels or {}
    body = read_body(path)
    out = []
    for g in _groups_node(body)[1]:
        gname = labels.get(_field(g, K_NAME)[1], f'#{_field(g, K_NAME)[1]:#x}')
        default = labels.get(_field(g, K_DEFAULT)[1], f'#{_field(g, K_DEFAULT)[1]:#x}')
        out.append((gname, default))
        for s in _field(g, K_STATES)[1]:
            sh = _field(s, K_STATE)[1]
            meshes = _field(s, K_MESHES)
            names = [labels.get(m[1], f'#{m[1]:#x}') for m in meshes[1]]
            out.append((f'  {labels.get(sh, f"#{sh:#x}")}', names))
    return out


# --- mesh-name resolution -------------------------------------------------
#
# Group and state names are ordinary `hash40` of the exact-case name
# (`hash40("head")` = 0x4a7f3f69c, `hash40("lhand_alarm")` = 0xb4d9cb5ed), but the
# per-state *mesh* hashes are `hash40` of the **lowercased** mesh name. G&W's model
# stores `AlarmM`; the table stores hash40("alarmm") = 0x61917c347. Getting this
# wrong is why 134/134 hashes looked unresolvable and `lhand_alarm` sat unidentified
# for a long time - the lookup has to lowercase, and nothing in the file says so.
#
# Proof, not inference: brute-forcing every 4-character name over
# [A-Za-z0-9_] against the ten 4-char hashes in G&W's table returns exactly
# `no1m`..`no9m` and `keym`, which are the lowercased forms of the model's `No1M`..
# `No9M` and `KeyM`. With that key, 124 of 134 resolve; the other 10 are all
# SENTINEL, the "shows nothing" entry every group carries as its empty state.
SENTINEL_MESH = 0x7FB997A80


def mesh_names(model_mesh_path):
    """Lowercased mesh-name -> hash, from a fighter's `model.numshb`."""
    import ssbh_data_py
    mesh = ssbh_data_py.mesh_data.read_mesh(str(model_mesh_path))
    return {prc.hash40(o.name.split('_VIS_')[0].lower()): o.name.split('_VIS_')[0]
            for o in mesh.objects}


def resolve_state_meshes(state_hash, meshes, index):
    """Turn one state's mesh-hash list into names, via a `mesh_names` index."""
    out = []
    for h in meshes:
        if h == SENTINEL_MESH:
            out.append(None)          # "this state shows nothing"
        elif h in index:
            out.append(index[h])
        else:
            out.append(f'#{h:#x}')
    return out


def summarise_groups(prc_path, index):
    """group -> {state: [mesh names]} for one `expression_vl.prc`, for build records.

    Records the table's actual content in the build record so a change in a future
    dump shows up as a diff in review rather than as a silent behaviour change on
    hardware. `None` in a mesh list is the empty/sentinel state.
    """
    body = read_body(prc_path)
    out = {}
    for g in _groups_node(body)[1]:
        gname = _field(g, K_NAME)[1]
        states = {}
        for s in _field(g, K_STATES)[1]:
            sh = _field(s, K_STATE)[1]
            meshes = _field(s, K_MESHES)
            lst = [m[1] for m in meshes[1]] if meshes[0] == 'list' else []
            states[f'#{sh:#x}'] = resolve_state_meshes(sh, lst, index)
        out[f'#{gname:#x}'] = states
    return out
