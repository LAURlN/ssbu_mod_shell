"""v0.2.0: pin main-image throw parameter ABI and expression cursor commands.

Read-only main input; emits bounded inspection spans and instruction assertions.
Does not claim a complete CaptureModule audit or any runtime verification.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'builds/.cache/gaogaen_throw_b/python'), str(ROOT / 'tools')]
from main_image import MainImage

def main():
    out = ROOT / 'evidence/2026-10-02_pgwr_gaogaen_throw_b'
    routes = json.loads((out / 'ROUTES.json').read_text())
    by_name = {f['name']: f for f in routes['functions']}
    throw_init = by_name['_ZN7lua2cpp16L2CFighterCommon27sub_throw_uniq_process_initEv']
    victim_init = by_name['_ZN7lua2cpp16L2CFighterCommon28sub_thrown_uniq_process_initEv']
    assert any(c['target'] == '0xd436c' or c['site'] == '0xd436c'
               for c in throw_init['calls'])
    assert any('LinkModule__send_event_nodes_throw_impl' in c['name']
               for c in throw_init['calls'])
    assert any('CaptureModule__thrown_impl' in c['name'] for c in victim_init['calls'])
    image = MainImage(ROOT.parents[1] / 'gamedata/ssbu-13.0.4/main.bin')
    digest = hashlib.sha256(image.data).hexdigest()
    assert digest == json.loads((ROOT / 'refs/gaogaen_throw_b/SOURCE.json').read_text())['native_main']['sha256']
    def instructions(address, length):
        return [(i.mnemonic, i.op_str) for i in image.disasm(address, length)]
    assert instructions(0x20a8000, 4) == [('b', '#0x720f90')]
    assert instructions(0x61bf28, 12) == [('mov', 'w8, #0x39'),
        ('movk', 'w8, #0x2000, lsl #16'), ('sub', 'w19, w8, #9')]
    # The second flag setter constructs 0x20000039 then subtracts 8.
    assert instructions(0x61e4b8, 12) == [('mov', 'w9, #0x39'),
        ('movk', 'w9, #0x2000, lsl #16'), ('sub', 'w2, w9, #8')]
    spans = []
    for start, end in ((0x720f90, 0x7210e0), (0x61a8d4, 0x61a8f4),
                       (0x61b7d4, 0x61b7f4), (0x61bf20, 0x61bf90),
                       (0x61e4ac, 0x61e4f4), (0x1ff58e0, 0x1ff5920)):
        path = out / 'native' / f'engine_{start:x}.asm'
        path.write_text('\n'.join(f'{i.address:08x}: {i.mnemonic} {i.op_str}'
                                 for i in image.disasm(start, end-start)) + '\n')
        spans.append({'start': hex(start), 'end_exclusive': hex(end),
            'path': path.relative_to(ROOT).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'scope': 'inspection span; not inferred complete function except exported thunk'})
    report = {'tier': 'B: instruction bytes checked; interpretations bounded', 'main_sha256': digest,
        'thrown_offset': {'export': '0x20a8000', 'target': '0x720f90',
            'symbol': '_ZN3app8lua_bind41FighterParamAccessor2__thrown_offset_implEPNS_21FighterParamAccessor2Eiii',
            'interpretation': 'native returns SIMD q0; pinned binding phx::simd::Vector3 retained',
            'direction_b': 1, 'kind_alias': {'0x4c': '0x4b'}, 'kind_limit': 94,
            'runtime_abi': 'unverified; compiler emits improper_ctypes SIMD warning'},
        'cursor_commands': [{'command': '0x1f20a9d549', 'work_flag': '0x20000030',
            'binding': 'FIGHTER_INSTANCE_WORK_ID_FLAG_CURSOR', 'construction': '0x61a8d4',
            'receiver': '0x61bf20'}, {'command': '0x24772eddef', 'work_flag': '0x20000031',
            'binding': 'FIGHTER_INSTANCE_WORK_ID_FLAG_NAME_CURSOR', 'construction': '0x61b7d4',
            'setter_path': '0x61e4ac'}],
        'capture_module': {'exported_thrown_wrapper': '0x1ff58e0',
            'attacker_event': {'site': '0xd436c',
                'callee': 'LinkModule__send_event_nodes_throw_impl',
                'selected_from': 'CATCH_WAIT_WORK_INT_MOTION_KIND = throw_b; shared init retains target ids'},
            'victim_init': {'site': '0xb5b40', 'callee': 'CaptureModule__thrown_impl',
                'receiver': 'victim module accessor from generic thrown status init'},
            'conclusion': 'the measured common route selects victim thrown_b through its stock throw event and runs CaptureModule::thrown on the victim; the ordinary native call path takes no new shared custom status id as a parameter',
            'scope': 'CaptureModule implementation is virtual/native and gameplay acceptance is runtime-unverified'},
        'assembly': spans}
    (out / 'ENGINE.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS pinned main, parameter exported thunk, cursor and name-cursor instruction controls')

if __name__ == '__main__': main()
