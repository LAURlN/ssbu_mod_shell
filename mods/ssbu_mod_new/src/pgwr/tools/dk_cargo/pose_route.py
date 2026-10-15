"""Capture native motion lookup/delegate candidates; offline, no hooks.

Raw immediate matches are candidates, never proof of a capture dependency.
Run after victims.py. A complete resolver must identify the delegate object,
its constructors and its capture-specific lookup before runtime implementation.
"""
import struct
import audit
from audit import OUT, WS, cfg, sha, write
from main_image import MainImage
from audit_mflip_capture_native import symbols


def run():
    img = MainImage(WS / 'gamedata/ssbu-13.0.4/main.bin')
    labels = {a: n for n, a, size in symbols(img) if a}
    functions = {}
    for a in (0x3cb840, 0x496a30, 0x495690, 0x6debf0, 0x6deca0,
              0x6ded80, 0x6defa0, 0x49f300, 0x4a0fb0, 0x49f9e0,
              0x483020, 0x483060, 0x47fba0, 0x4a1b70):
        row, text = cfg(img.data, a, labels)
        path = OUT / 'semantic_asm' / f'pose_route_{a:x}.asm'
        path.write_text(text)
        functions[hex(a)] = {**row, 'asm_sha256': sha(path.read_bytes())}
    stores = []
    # STR Xt,[Xn,#0x190], unsigned immediate, excluding SIMD/pre/post forms.
    # Register identity alone cannot establish which module Xn denotes.
    for a in range(0x100, 0x39c8000, 4):
        w = struct.unpack_from('<I', img.data, a)[0]
        if w & 0xffc00000 != 0xf9000000 or ((w >> 10) & 0xfff) * 8 != 0x190:
            continue
        stores.append({'at': hex(a), 'source_register': w & 31,
                       'base_register': (w >> 5) & 31})
        # Keep the complete address inventory but only disassemble stores in
        # the recovered base MotionModule setter. Other modules use +0x190 too.
        if 0x49f9e0 <= a <= 0x49fb94:
            path = OUT / 'semantic_asm' / f'pose_delegate_store_{a:x}.asm'
            path.write_text('\n'.join(f'{i.address:#010x}: {i.mnemonic:8} {i.op_str}'
                for i in img.disasm(a - 96, 196)) + '\n')
    # Recover the LinkModule table independently from its native shoulder_throw
    # constructor and exported send_event_nodes_throw wrapper's virtual slot.
    throw_slots = [a for a,v in img.relocs.items() if v == 0x47fba0]
    assert throw_slots == [0x4f6e7a0]
    link_vt = throw_slots[0] - 0xc8
    assert img.ptr(link_vt + 0x240) == 0x483020
    assert img.ptr(link_vt + 0x248) == 0x483060
    assert img.ptr(0x4f88198 + 0x458) == 0x49f300
    assert img.ptr(0x4f88198 + 0x680) == 0x4a0fb0
    route = {'native_chain': ['MotionModule change 0x49a4a0; motion flag bit 3',
        'BOMA +0xd0 is LinkModule, independently exported wrappers',
        'Link virtual +0x248 -> 0x483060: follow parent link',
        'parent Link virtual +0x240 -> 0x483020: follow transactor or own motion',
        'parent Motion virtual +0x458 -> 0x49f300',
        'Motion virtual +0x680 -> 0x4a0fb0 -> hash lookup 0x495690'],
        'link_vtable': hex(link_vt), 'motion_vtable': '0x4f88198',
        'owned_alias_contract': 'Victim empty owned entry keeps donor sharing flag; captor motion list supplies matching owned motion kind and donor pose template. No new link is constructed.',
        'pickel_overlay_contract': 'Fighter motion 0x6df820 calls 0x4a1b70 for multi-animation metadata. Flags & 0x1008 select parent lookup/resource for the first animation; bit 0x1000 retains the victim animation list and switches subsequent animations to victim-local resources. Keep Pickel overlay entries/flags; rename only the shared first clip.',
        'runtime_verified': False}
    write('native_pose_route.json', {'tier': 'B', 'runtime_verified': False,
        'complete': False, 'main_sha256': sha(img.data),
        'functions': functions, 'delegate_store_candidates': stores,
        'shared_pose_route': route,
        'missing': 'Runtime lookup/retarget must be checked on hardware; +0x190 optional hash delegate is separate from the measured parent-sharing branch.'})
    print('PASS: pinned native pose lookup graphs and', len(stores), 'unclassified store candidates')


if __name__ == '__main__':
    run()
