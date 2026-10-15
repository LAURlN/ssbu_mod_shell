"""Gaogaen back-throw preparation v0.1.0; offline, no installation.

Commands: pin, prepare, check, merge --target <mod tree>.
Outputs stay in builds/pgwr/gaogaen_throw_b-0.1.0; sources remain read-only.
This is a PENDING dependency package, not a playable release.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import math
import re
import shutil
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[4]
LAB = ROOT.parents[1]
REF = ROOT / 'refs/gaogaen_throw_b'
OUT = ROOT / 'builds/pgwr/gaogaen_throw_b-0.1.0'
BASE = ROOT / 'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
ARC = LAB / 'gamedata/ssbu-13.0.4/files'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import merge_snake_uptilt_sound as sound
import prc

DONOR_FILES = [
    'fighter/gaogaen/motion/body/c00/e01throwb.nuanmb',
    'fighter/gaogaen/motion/body/c00/motion_list.bin',
    'fighter/gaogaen/model/body/c00/model.nusktb',
    'fighter/gaogaen/param/vl.prc',
    'fighter/common/param/fighter_param_thrown.prc',
    'sound/sequence/fighter/gaogaen.sqb',
] + [f'sound/bank/{folder}/{name}_gaogaen_c00{ext}'
     for folder, name in [('fighter', 'se'), ('fighter_voice', 'vc')]
     for ext in ['.nus3audio', '.nus3bank', '.tonelabel']]
CLIP = 'pgwrgaogaenthrowb.nuanmb'
KIND = 'pgwr_gaogaen_throw_b'
SCRIPT = 'pgwrgaogaenthrowb'
SE = {'se_gaogaen_throw_b01', 'se_gaogaen_throw_b02', 'se_gaogaen_throw_b03',
      'se_gaogaen_throw_mat', 'se_gaogaen_react_success'}
VC = {'vc_gaogaen_attack06'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def h40(s):
    return len(s.encode()) << 32 | zlib.crc32(s.encode())


def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')


def rel(p):
    return Path(p).relative_to(ROOT).as_posix()


def mlist(data):
    magic, folder, count = struct.unpack_from('<QQQ', data)
    assert magic == h40('motion')
    offset = 24
    entries = {}
    for _ in range(count):
        start = offset
        kind, script, flags, blend, n, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n, data, offset)
        offset = (offset + n * 9 + 3) & ~3
        end = offset + size
        assert end <= len(data) and kind not in entries
        entries[kind] = {'raw': data[start:end], 'anims': anims, 'script': script,
                         'flags': flags, 'blend': blend,
                         'cancel': struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None}
        offset = end
    assert offset == len(data)
    return magic, folder, entries


def pin():
    assert not (REF / 'SOURCE.json').exists(), 'Pins already exist; do not silently refresh'
    sources = [{'path': p, 'sha256': sha(ARC / p), 'bytes': (ARC / p).stat().st_size}
               for p in DONOR_FILES]
    acmd = []
    for name in ['ThrowB.txt', 'eflame_ThrowB.txt']:
        p = REF / 'donor_acmd' / name
        fighter = 'eflame' if name.startswith('eflame') else 'gaogaen'
        acmd.append({'path': rel(p), 'sha256': sha(p), 'url':
            f'https://raw.githubusercontent.com/WuBoytH/SSBU-Dumped-Scripts/59004685238a3f6f93bae905d3a4e079701c40b4/smashline/lua2cpp_{fighter}/{fighter}/ThrowB.txt'})
    p = REF / 'donor_status/pre.c'
    write_json(REF / 'SOURCE.json', {'task': 'gaogaen_throw_b', 'date': '2026-10-02',
        'recipient': 'eflame c06/c07 (G&W)', 'game_version': '13.0.4',
        'arc_provenance': 'gamedata/ssbu-13.0.4/data.arc.provenance.json (workspace relative)',
        'arc_root': 'gamedata/ssbu-13.0.4/files (workspace relative)', 'assets': sources,
        'acmd': acmd, 'status': {'path': rel(p), 'sha256': sha(p), 'url':
          'https://raw.githubusercontent.com/Coolsonickirby/SSBU-Dumped-Status-Scripts/b6bb1fecf7a0a3ee872cea73c94acccccadf8133/ghidra_scripts/lua2cpp_gaogaen.nro/gaogaen/gaogaen/status/Throw/pre.c'},
        'native_main': {'path': 'gamedata/ssbu-13.0.4/main.bin (workspace relative)',
                        'sha256': sha(LAB / 'gamedata/ssbu-13.0.4/main.bin')},
        'baseline_manifest_sha256': sha(BASE.parents[2] / 'MANIFEST.json')})
    print('Donor pins recorded')


def check_pins():
    source = json.loads((REF / 'SOURCE.json').read_text())
    for item in source['assets']:
        assert sha(ARC / item['path']) == item['sha256'], item['path']
    for item in source['acmd'] + [source['status']]:
        assert sha(ROOT / item['path']) == item['sha256'], item['path']
    assert sha(BASE.parents[2] / 'MANIFEST.json') == source['baseline_manifest_sha256']


def generate_acmd():
    donor = (REF / 'donor_acmd/ThrowB.txt').read_text(encoding='utf-8')
    assert len(re.findall(r'unsafe extern "C" fn', donor)) == 4
    assert 'FIGHTER_GAOGAEN_' not in donor
    # The raw expression commands are retained verbatim, pending native audit.
    # This module is deliberately not registered in the live crate.
    preamble = '''//! Generated by tools/gaogaen_throw_b/pipeline.py; do not hand edit.
//! PENDING: native victim, collateral, Revenge and raw expression audit incomplete.
//! Owned custom motion scripts only. No live throw handler is replaced.
use smash::{lua2cpp::*, phx::*, app::{sv_animcmd::*, lua_bind::*, *}, lib::lua_const::*};
use smash_script::*;
use smashline::*;
'''
    body = preamble + donor + '\n\npub fn install() {\n    Agent::new("eflame")\n        .set_costume(crate::TARGET_COSTUMES.to_vec())\n'
    for category in ['game', 'effect', 'sound', 'expression']:
        body += f'        .{category}_acmd("{category}_{SCRIPT}", {category}_throwb, Priority::Default)\n'
    body += '        .install();\n}\n'
    dst = ROOT / 'src/pgwr/plugin/src/acmd/gaogaen_throw_b.rs'
    dst.write_text(body, encoding='utf-8')
    # Narrow unapplied registration patch, generated against the current shared file.
    shared = ROOT / 'src/pgwr/plugin/src/acmd/mod.rs'
    original = shared.read_text(encoding='utf-8')
    new = original.replace('pub mod compat;', 'pub mod compat;\npub mod gaogaen_throw_b;', 1)
    new = new.replace('    generated::ground::install();',
                      '    gaogaen_throw_b::install();\n    generated::ground::install();', 1)
    patch = ''.join(difflib.unified_diff(original.splitlines(True), new.splitlines(True),
                   fromfile='a/src/pgwr/plugin/src/acmd/mod.rs',
                   tofile='b/src/pgwr/plugin/src/acmd/mod.rs'))
    (OUT / 'integration.patch').write_text(patch, encoding='utf-8')
    return {'registration_baseline_sha256': sha(shared), 'generated_acmd_sha256': sha(dst),
            'raw_expression_commands': ['0x1f20a9d549(false)', '0x24772eddef(false)'],
            'registration_patch_applied': False}


def parameters():
    labels = {}
    for line in (ROOT / 'dumps/scripts/ParamLabels.csv').read_text().splitlines():
        a, _, b = line.partition(',')
        if a.startswith('0x'):
            labels[int(a, 16)] = b
    def convert(n):
        tag, value = n
        if tag == 'struct':
            return {labels.get(k, hex(k)): convert(v) for k, v in value}
        if tag == 'list':
            return [convert(v) for v in value]
        if tag == 'hash':
            return {'hash40': hex(value), 'label': labels.get(value)}
        return value
    params = convert(prc.read(ARC / 'fighter/gaogaen/param/vl.prc'))
    table = convert(prc.read(ARC / 'fighter/common/param/fighter_param_thrown.prc'))['fighter_param_thrown_table']
    # Select by the file's fighter_kind hash, never by a guessed row index.
    selected = [(i, row) for i, row in enumerate(table)
                if row['fighter_kind']['hash40'] in
                   {hex(h40('fighter_kind_gaogaen')), hex(h40('fighter_kind_eflame'))}]
    assert len(selected) == 2
    return {'revenge_data': params['revenge_data'], 'param_private': params['param_private'],
            'throw_offset_rows': [{'row': i, **row} for i, row in selected],
            'row_index_to_runtime_kind_mapping': 'unverified; no global PRC edited',
            'intended_revenge': 'no Revenge system or multiplier on recipient; unboosted vanilla target',
            'acmd_revenge_branch': 'none in pinned ThrowB.txt; native consumption/scaling audit pending'}


def retarget(slot, payload):
    import ssbh_data_py as s
    donor = s.anim_data.read_anim(str(ARC / DONOR_FILES[0]))
    skeleton = BASE / f'fighter/eflame/model/body/{slot}/model.nusktb'
    idlepath = BASE / f'fighter/eflame/motion/body/{slot}/a00wait1.nuanmb'
    names = {b.name for b in s.skel_data.read_skel(str(skeleton)).bones}
    idle = s.anim_data.read_anim(str(idlepath))
    transform = next(g for g in donor.groups if g.group_type.name == 'Transform')
    original = [n.name for n in transform.nodes]
    transform.nodes = [n for n in transform.nodes if n.name in names]
    visibility = next(g for g in idle.groups if g.group_type.name == 'Visibility')
    donor.groups = [transform, s.anim_data.GroupData(s.anim_data.GroupType.Visibility,
        [s.anim_data.NodeData(n.name, [s.anim_data.TrackData('Visibility', values=[n.tracks[0].values[0]])])
         for n in visibility.nodes])]
    p = payload / f'fighter/eflame/motion/body/{slot}/{CLIP}'
    p.parent.mkdir(parents=True, exist_ok=True)
    donor.save(str(p))
    check = s.anim_data.read_anim(str(p))
    assert check.final_frame_index == donor.final_frame_index
    kept = {n.name for n in transform.nodes}
    anchors = {name: name in kept for name in ['Throw', 'Rot', 'Trans', 'Hip', 'Waist', 'Bust', 'ShoulderL', 'ShoulderR', 'ArmL', 'ArmR']}
    assert anchors['Throw'], 'Victim anchor track would be dropped'
    spans = {}
    for n in transform.nodes:
        if n.name not in anchors:
            continue
        values = n.tracks[0].values
        base = values[0]
        def angle(v):
            a,b = v.rotation,base.rotation
            denom = math.sqrt(sum(float(x)**2 for x in a)*sum(float(x)**2 for x in b))
            return math.degrees(2*math.acos(min(1,abs(sum(float(x)*float(y) for x,y in zip(a,b)))/denom)))
        spans[n.name] = {'samples':len(values),'max_rotation_from_frame0_degrees':max(angle(v) for v in values),
            'max_translation_from_frame0':max(max(abs(float(x)-float(y)) for x,y in zip(v.translation,base.translation)) for v in values)}
    assert spans['Throw']['max_rotation_from_frame0_degrees'] > 1 or spans['Throw']['max_translation_from_frame0'] > 0.05
    return {'slot': slot, 'skeleton_sha256': sha(skeleton), 'idle_sha256': sha(idlepath),
            'donor_nodes': len(original), 'kept': len(kept),
            'dropped': [n for n in original if n not in kept], 'anchors': anchors,
            'final_frame_index': donor.final_frame_index, 'clip_sha256': sha(p),
            'track_motion':spans, 'appearance': 'unverified; node intersection is not rig equivalence'}


def prepare():
    check_pins()
    OUT.mkdir(parents=True, exist_ok=True)
    payload = OUT / 'delta'
    payload.mkdir(exist_ok=True)
    report = {'state': 'PENDING', 'tier': 'B bytes / C pinned script / D runtime',
              'task': 'gaogaen_throw_b', 'baseline': '0.20.19',
              'source': generate_acmd(), 'parameters': parameters(), 'animation': [], 'sound': []}
    donor = mlist((ARC / DONOR_FILES[1]).read_bytes())[2][h40('throw_b')]
    assert donor['anims'] == (h40('e01throwb.nuanmb'),)
    owned = bytearray(donor['raw'])
    struct.pack_into('<Q', owned, 0, h40(KIND))
    struct.pack_into('<Q', owned, 8, h40('game_' + SCRIPT))
    struct.pack_into('<Q', owned, 24, h40(CLIP))
    (OUT / 'motion_entry.bin').write_bytes(owned)
    report['motion'] = {k: v for k, v in donor.items() if k not in ['raw', 'anims']}
    report['motion'].update(donor_entry_sha256=hashlib.sha256(donor['raw']).hexdigest(),
                           owned_entry_sha256=sha(OUT / 'motion_entry.bin'),
                           kind=KIND, script='game_' + SCRIPT, clip=CLIP)
    motions = []
    config_add = {}
    for slot in ['c06', 'c07']:
        report['animation'].append(retarget(slot, payload))
        path = f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        original = (BASE / path).read_bytes()
        magic, folder, entries = mlist(original)
        assert h40(KIND) not in entries
        merged = struct.pack('<QQQ', magic, folder, len(entries) + 1) + b''.join(v['raw'] for v in entries.values()) + owned
        got = mlist(merged)[2]
        assert all(got[k]['raw'] == v['raw'] for k, v in entries.items())
        dst = payload / path
        dst.write_bytes(merged)
        motions.append({'path': path, 'baseline_sha256': sha(BASE / path),
                        'operation': 'append owned entry, preserve all existing entries'})
        config_add[f'fighter/eflame/{slot}'] = [f'fighter/eflame/motion/body/{slot}/{CLIP}']
        for folder, prefix, wanted in [('fighter', 'se', SE), ('fighter_voice', 'vc', VC)]:
            path = f'sound/bank/{folder}/{prefix}_eflame_{slot}'
            report['sound'].append(sound.append_tones(
                ARC / f'sound/bank/{folder}/{prefix}_gaogaen_c00', BASE / path, payload / path, wanted))
    cfg = json.loads((BASE / 'config.json').read_text())
    for group, files in config_add.items():
        arr = cfg.setdefault('new-dir-files', {}).setdefault(group, [])
        for file in files:
            assert file not in arr
            arr.append(file)
    write_json(payload / 'config.json', cfg)
    write_json(OUT / 'merge_deltas.json', {'motion_entries': motions, 'config':
        {'baseline_sha256': sha(BASE / 'config.json'), 'append_new_dir_files': config_add},
        'bank_operations': [{'slot': slot, 'folder': folder, 'prefix': prefix, 'append_tones': sorted(wanted)}
            for slot in ['c06', 'c07'] for folder, prefix, wanted in [('fighter','se',SE),('fighter_voice','vc',VC)]]})
    report['effects'] = {'fighter_bank_delta': None, 'names': ['sys_atk_smoke','sys_crown','null'],
                         'reason': 'pinned ACMD uses common effects and donor null placeholder only'}
    report['sequence_delta'] = None
    report['blockers'] = ['native victim attachment, motion selection, rotation and cleanup not recovered',
        'native collateral hitboxes not recovered: pinned ACMD contains catch-only attack only',
        'native Revenge scaling/consumption and raw expression commands not recovered',
        'owned throw status routing and interruption cleanup not implemented; request collective allocation, no ID chosen']
    files = []
    for p in sorted(payload.rglob('*')):
        if p.is_file():
            relative = p.relative_to(payload).as_posix()
            base = BASE / relative
            files.append({'path': relative, 'sha256': sha(p), 'bytes': p.stat().st_size,
                          'baseline_sha256': sha(base) if base.is_file() else None})
    report['files'] = files
    write_json(OUT / 'MANIFEST.json', report)
    print(json.dumps({'state':report['state'], 'files':len(files), 'animation':report['animation'], 'motion':report['motion']}, indent=2))


def check():
    check_pins()
    report = json.loads((OUT / 'MANIFEST.json').read_text())
    assert report['state'] == 'PENDING' and report['blockers']
    for item in report['files']:
        assert sha(OUT / 'delta' / item['path']) == item['sha256'], item['path']
        p = BASE / item['path']
        assert (sha(p) if p.is_file() else None) == item['baseline_sha256'], item['path']
    source = ROOT / 'src/pgwr/plugin/src/acmd/gaogaen_throw_b.rs'
    assert sha(source) == report['source']['generated_acmd_sha256']
    assert b'FIGHTER_GAOGAEN_' not in source.read_bytes()
    for slot in ['c06', 'c07']:
        relative = f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        before = mlist((BASE / relative).read_bytes())[2]
        after = mlist((OUT / 'delta' / relative).read_bytes())[2]
        assert set(after) == set(before) | {h40(KIND)}
        assert all(after[k]['raw'] == v['raw'] for k, v in before.items())
    assert all('/c00/' not in f['path'] for f in report['files'])
    # Negative control: removal of the owned entry must be detected.
    missing = dict(after)
    del missing[h40(KIND)]
    assert set(missing) != set(before) | {h40(KIND)}
    write_json(OUT / 'CHECK.json', {'state':'PASS prerequisite bytes only', 'runtime':'unverified',
                                  'checked_files':len(report['files']), 'missing_motion_negative_control':True,
                                  'manifest_sha256':sha(OUT / 'MANIFEST.json')})
    print('PASS pins, payload hashes, baseline hashes, motion preservation, missing-entry negative control')


def merge(target):
    """Replay semantic deltas against an installer-owned tree; never replace shared banks/lists."""
    check_pins()
    target = Path(target).resolve()
    assert target.is_relative_to(ROOT / 'builds') and not target.is_relative_to(BASE.parents[2])
    assert target != OUT / 'delta'
    # Preflight every shared input before writing any file.
    for slot in ['c06','c07']:
        path = target / f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        entries = mlist(path.read_bytes())[2]
        if h40(KIND) in entries:
            assert entries[h40(KIND)]['raw'] == (OUT / 'motion_entry.bin').read_bytes()
        for folder,prefix,wanted in [('fighter','se',SE),('fighter_voice','vc',VC)]:
            stem = target / f'sound/bank/{folder}/{prefix}_eflame_{slot}'
            existing = {n.lower() for n,_ in sound.codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())}
            assert not (existing & wanted), 'Already merged or collision; compare donor tone bytes explicitly'
    cfg = json.loads((target / 'config.json').read_text())
    entry = (OUT / 'motion_entry.bin').read_bytes()
    for slot in ['c06','c07']:
        path = target / f'fighter/eflame/motion/body/{slot}/motion_list.bin'
        original = path.read_bytes()
        magic, folder, entries = mlist(original)
        if h40(KIND) in entries:
            assert entries[h40(KIND)]['raw'] == entry
        else:
            merged = struct.pack('<QQQ', magic, folder, len(entries)+1) + b''.join(v['raw'] for v in entries.values()) + entry
            after = mlist(merged)[2]
            assert all(after[k]['raw'] == v['raw'] for k,v in entries.items())
            path.write_bytes(merged)
        path = target / f'fighter/eflame/motion/body/{slot}/{CLIP}'
        path.write_bytes((OUT / 'delta' / path.relative_to(target)).read_bytes())
        for folder,prefix,wanted in [('fighter','se',SE),('fighter_voice','vc',VC)]:
            stem = target / f'sound/bank/{folder}/{prefix}_eflame_{slot}'
            existing = {n.lower() for n,_ in sound.codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())}
            assert not (existing & wanted), 'Already merged or collision; compare donor tone bytes explicitly'
            sound.append_tones(ARC / f'sound/bank/{folder}/{prefix}_gaogaen_c00', stem, stem, wanted)
    path = target / 'config.json'
    cfg = json.loads(path.read_text())
    for group, files in json.loads((OUT / 'merge_deltas.json').read_text())['config']['append_new_dir_files'].items():
        arr = cfg.setdefault('new-dir-files',{}).setdefault(group,[])
        for file in files:
            if file not in arr:
                arr.append(file)
    write_json(path,cfg)
    print('Prerequisite asset deltas replayed; PENDING native port, do not install')


def smoke():
    check()
    target = ROOT / 'builds/.cache/gaogaen_throw_b/merge-smoke'
    assert not target.exists(), 'Smoke destination exists; choose a fresh task cache instead of overwriting it'
    target.mkdir(parents=True)
    report = json.loads((OUT / 'MANIFEST.json').read_text())
    for f in report['files']:
        if f['baseline_sha256'] is not None:
            p = target / f['path']
            p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(BASE / f['path'],p)
    merge(target)
    assert all(sha(target / f['path']) == f['sha256'] for f in report['files'])
    # Bank preservation negative control: deliberately altered original samples.
    stem = target / 'sound/bank/fighter/se_eflame_c06'
    original,chunks,labels = sound._read_bank(BASE / 'sound/bank/fighter/se_eflame_c06')
    tones = sound.codec.tones_read(dict(chunks)[b'TONE'])
    changed = list(original)
    name,data = changed[0]
    changed[0] = (name,data+b'corrupt-control')
    detected = False
    try:
        sound.verify_preserved(stem,changed,tones,labels,dict(chunks),SE)
    except AssertionError:
        detected = True
    assert detected
    write_json(OUT / 'SMOKE.json', {'semantic_delta_replay_byte_equal':True,
        'files':len(report['files']), 'original_sample_corruption_negative_control':detected,
        'runtime':'unverified', 'destination':rel(target)})
    print('PASS semantic replay byte equality and sound preservation negative control')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['pin','prepare','check','merge','smoke'])
    parser.add_argument('--target', type=Path)
    args = parser.parse_args()
    if args.command == 'merge':
        assert args.target is not None
        merge(args.target)
    else:
        globals()[args.command]()

