#!/usr/bin/env python3
"""Compare a donor clip's animated nodes with a skeleton (model.nusktb). Read-only.

Usage (workspace root, PYTHONDONTWRITEBYTECODE=1):
  python compat2.py <clip.nuanmb> <skel.nusktb> [--bones kneer,KneeR,...]
Group type is matched by substring because str(GroupType) prints as '<GroupType.Transform: 1>'.
"""
import sys
import ssbh_data_py as s


def kind(g):
    t = str(g.group_type)
    for k in ('Transform', 'Visibility', 'Material', 'Camera'):
        if k in t:
            return k
    return t


def main():
    clip_path, skel_path = sys.argv[1], sys.argv[2]
    bones_arg = sys.argv[sys.argv.index('--bones') + 1].split(',') if '--bones' in sys.argv else []
    anim = s.anim_data.read_anim(clip_path)
    skel = s.skel_data.read_skel(skel_path)
    by_kind = {}
    for g in anim.groups:
        by_kind.setdefault(kind(g), []).extend(n.name for n in g.nodes)
    tr = set(by_kind.get('Transform', []))
    vis = set(by_kind.get('Visibility', []))
    mat = set(by_kind.get('Material', []))
    sk = [b.name for b in skel.bones]
    sks = set(sk)
    print(f"clip={clip_path} final_frame_index={anim.final_frame_index}")
    print(f"skel={skel_path} bones={len(sk)} unique={len(sks)}")
    print(f"transform nodes={len(tr)} visibility nodes={len(vis)} material nodes={len(mat)}")
    print("transform nodes NOT in skeleton:", sorted(tr - sks))
    print("skeleton bones NOT in transform track:", sorted(sks - tr))
    print("visibility nodes:", sorted(vis))
    for b in bones_arg:
        print(f"name {b!r}: in_skeleton={b in sks} in_transform_track={b in tr}")


if __name__ == '__main__':
    main()
