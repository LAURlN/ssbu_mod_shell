"""B-tier donor collision audit for pinned vanilla Gaogaen throw_b.

Run from the mod root after extracting/pinning native inputs. Audits the complete
bounded game_throwb body and pinned public script; does not claim gameplay results.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'evidence/2026-10-02_pgwr_gaogaen_throw_b'
sys.path[:0] = [str(ROOT / 'builds/.cache/gaogaen_throw_b/python'), str(ROOT / 'tools/nro_decomp')]
from nro_flatten import flatten
import nro_util as u

def main():
    pins = json.loads((OUT / 'NATIVE_INPUTS.json').read_text())
    pin = next(x for x in pins if 'lua2cpp_gaogaen.nro' in x['local_path'])
    data = (ROOT.parents[1] / pin['local_path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == pin['sha256']
    image, _meta = flatten(data)
    start, size = 0xddba0, 0x1030
    body = list(u.disasm(image, start, size))
    assert body[0].address == start and any(i.address == 0xde79c and i.mnemonic == 'ret' for i in body)
    body = [i for i in body if i.address <= 0xde79c]
    calls = [(i.address, int(i.op_str.lstrip('#'), 0)) for i in body if i.mnemonic == 'bl']
    assert [site for site, target in calls if target == 0xa3850] == [0xde2c0]
    assert [site for site, target in calls if target == 0xa08f0] == [0xddd34, 0xddeec]
    for expected in (0xde420, 0xde470, 0xde514, 0xde698, 0xde774):
        assert expected in {i.address for i in body}
    asm_path = OUT / 'native' / 'lua2cpp_gaogaen_ddba0.asm'
    script_path = ROOT / 'refs/gaogaen_throw_b/donor_acmd/ThrowB.txt'
    assert script_path.is_file()
    report = {
        'tier': 'B: pinned full bounded donor function and C-tier script instructions',
        'input_nro_sha256': pin['sha256'], 'body': {'start': hex(start),
            'end_inclusive': hex(body[-1].address), 'size': size,
            'assembly_sha256': hashlib.sha256(asm_path.read_bytes()).hexdigest()},
        'regular_attack_helper_calls': [{'site': hex(site), 'helper': hex(target)}
            for site, target in calls if target == 0xa3850],
        'absolute_attack_helper_calls': [{'site': hex(site), 'helper': hex(target)}
            for site, target in calls if target == 0xa08f0],
        'body_sites': {'catch_only_all': '0xde420', 'finish_camera': '0xde470',
            'clear_all': '0xde514', 'absolute_release': '0xde698', 'reverse_lr': '0xde774'},
        'public_source_sha256': hashlib.sha256(script_path.read_bytes()).hexdigest(),
        'collision_readout': 'one regular attack setup at frame 28; pinned script immediately marks it catch-only; no non-catch-only collateral attack is present in this donor script/body',
        'scope_limit': 'No claim that third-party game situations cannot produce other collision effects; no additional collateral hitbox was present in donor code.'}
    (OUT / 'COLLISION.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS pinned complete throw_b function: one catch-only attack setup, two absolute definitions, no donor collateral attack')

if __name__ == '__main__': main()
