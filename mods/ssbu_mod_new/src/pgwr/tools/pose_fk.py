"""Forward kinematics over SSBH skeletons and clips, for checking a retarget (v1.0.0).

Shared by `build_pikachu_airb.py` (which builds a clip) and
`tools/audit_pikachu_airb_pose.py` (which re-reads the written file and measures
it independently). It exists because a retarget that keeps node *names* cannot
be judged from node counts: the name-intersection retarget the Pikachu back air
shipped with in 1.0.0 kept 45 of 55 nodes and 0 parent-chain mismatches and was
still wrong, because every kept node also carried the donor's own bone
*offsets* (translation), which turned the recipient's skeleton into Pikachu's.
Only a world-space measurement shows that.

Conventions, all verified by the identity controls in the audit:

* `nusktb` bone transforms are row-vector 4x4 (translation in the last row);
  they are transposed here to column-vector form, so `world = parent @ local`.
* An animation `Transform` value is `T * R * S` in column-vector form, rotation
  as an xyzw quaternion - the same convention `build_robot_dtilt.py` uses.
* Bones need not be stored parent-first, so world matrices are resolved
  recursively.

Tier B tooling: nothing here proves how a move looks in game.
"""
from __future__ import annotations

import numpy as np
import ssbh_data_py as s


def quat_to_matrix(q) -> np.ndarray:
    x, y, z, w = (float(v) for v in q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def transform_matrix(value) -> np.ndarray:
    """Column-vector 4x4 of one animation `Transform` value."""
    m = np.eye(4)
    m[:3, :3] = quat_to_matrix(value.rotation) @ np.diag([float(v) for v in value.scale])
    m[:3, 3] = [float(v) for v in value.translation]
    return m


def rotation_of(m: np.ndarray) -> np.ndarray:
    """The orthonormal rotation of a 4x4 that may carry scale."""
    r = m[:3, :3]
    return r / np.linalg.norm(r, axis=0)


def angle_between(a: np.ndarray, b: np.ndarray) -> float:
    """Degrees between two rotation matrices."""
    c = (np.trace(a.T @ b) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


class Skeleton:
    def __init__(self, path):
        skel = s.skel_data.read_skel(str(path))
        self.names = [b.name for b in skel.bones]
        self.parent = [b.parent_index for b in skel.bones]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.lower = {n.lower(): n for n in self.names}
        self.rest = [np.array(b.transform).T for b in skel.bones]

    def worlds(self, local) -> list:
        out = [None] * len(local)

        def get(i):
            if out[i] is None:
                p = self.parent[i]
                out[i] = local[i] if p is None else get(p) @ local[i]
            return out[i]

        for i in range(len(local)):
            get(i)
        return out

    def rest_worlds(self) -> list:
        return self.worlds(self.rest)


def read_transform_tracks(path) -> tuple:
    """(anim, {node: [Transform per frame]}) for the Transform group."""
    anim = s.anim_data.read_anim(str(path))
    group = next(g for g in anim.groups if g.group_type.name == 'Transform')
    return anim, {n.name: list(n.tracks[0].values) for n in group.nodes}


def value_at(values, frame: int):
    """A 1-value track is constant; otherwise index by frame (clamped)."""
    return values[min(frame, len(values) - 1)]


def locals_at(skel: Skeleton, tracks: dict, frame: int) -> list:
    """Local matrices at `frame`; a bone without a track sits at the skeleton rest."""
    out = []
    for i, name in enumerate(skel.names):
        out.append(transform_matrix(value_at(tracks[name], frame))
                   if name in tracks else skel.rest[i])
    return out


def frame_count(tracks: dict) -> int:
    return max(len(v) for v in tracks.values())


def world_position(skel: Skeleton, worlds: list, name: str) -> np.ndarray:
    return worlds[skel.index[name]][:3, 3]


def lowest_toe(skel: Skeleton, worlds: list) -> float:
    """Height of the lower of the two toe joints - the ground-contact proxy."""
    return float(min(world_position(skel, worlds, 'ToeL')[1],
                     world_position(skel, worlds, 'ToeR')[1]))
