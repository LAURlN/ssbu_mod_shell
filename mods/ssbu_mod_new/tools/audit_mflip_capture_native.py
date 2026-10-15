"""Audit Monkey Flip's missing native capture receiver on the shipped 13.0.4 image.

Version 1.1.0. Read-only dump access through paths.toml; no runtime hooks.
Usage: toolchains/py312/python.exe tools/audit_mflip_capture_native.py [--smoke]
Writes pinned JSON and complete handler assembly to refs/diddy_monkey_flip/.
Smoke assertions verify the capture dispatch, status gates, acceptance writes,
recipient dispatch, and exported wrappers independently of status-script dumps.
Evidence tier B: instruction measurements, not console behavior or causation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main_image import MainImage, ROOT
from maindesc import descriptors, static_fighter_data

VERSION = '1.1.0'
SLOT = 0x170
CLASSES = {'diddy': (0x27, 0x4FA40F8, 0x956B70, 0x9570A0),
           'eflame': (0x5A, 0x4FAF9C8, 0xA0C8D0, 0xA0CC14)}


def symbols(img):
    tags = img.dynamic
    count = img.u32(tags[4] + 4)  # DT_HASH nchain
    for index in range(count):
        name, _, _, _, value, size = struct.unpack_from(
            '<IBBHQQ', img.data, tags[6] + index * 24)
        start = tags[5] + name
        end = img.data.index(b'\0', start)
        yield img.data[start:end].decode(), value, size


def asm(img, start, end):
    return '\n'.join(f'{i.address:#010x}: {i.mnemonic:8} {i.op_str}'
                     for i in img.disasm(start, end - start)) + '\n'


def check(img):
    capture_hash = (len('capture') << 32) | zlib.crc32(b'capture')
    assert capture_hash == 0x78BFEA6E5
    for name, (kind, vt, handler, _) in CLASSES.items():
        assert img.i32(static_fighter_data(img, kind)) == kind
        assert img.ptr(vt + 8) == 0x68D5B0
        assert img.ptr(vt + SLOT) == handler
        # Identity is supported by native article initializer locality.
        inits = [d['init'] for d in descriptors(img, kind) if d['init']]
        assert min(inits) - 0x4000 < handler < max(inits) + 0x4000, name
    expected = {
        0x956BAC: ('mov', 'x9, #0xa6e5'),
        0x956BB0: ('movk', 'x9, #0x8bfe, lsl #16'),
        0x956BB4: ('movk', 'x9, #7, lsl #32'),
        0x956BBC: ('b.eq', '#0x956c94'),
        0x956C94: ('ldr', 'w8, [x20, #0x38]'),
        0x956C98: ('cmp', 'w8, #0xf0'),
        0x956CB0: ('cmp', 'w0, #0x1e5'),
        0x956CC8: ('cmp', 'w0, #0x1ee'),
        0x956CE0: ('mov', 'w1, #0x1e8'),
        0x956CE4: ('mov', 'w2, wzr'),
        0x956CE8: ('blr', 'x8'),
        0x956CF0: ('strb', 'w8, [x20, #0x28]'),
        0x956CF4: ('strb', 'wzr, [x20, #0x4f]'),
        0x956D00: ('ldr', 'w1, [x20, #0x20]'),
        0x956D04: ('ldr', 'x8, [x8, #0x58]'),
        0x956DBC: ('mov', 'x0, x19'),
        0x956F5C: ('ldr', 'x8, [x20, #0x20]'),
        0x956FCC: ('ldr', 'x8, [x8, #0x4f8]'),
        0x816374: ('mov', 'x10, #0xa337'),
        0x816378: ('movk', 'x10, #0x85be, lsl #16'),
        0x81637C: ('movk', 'x10, #0xf, lsl #32'),
        0x816388: ('add', 'x1, x8, #0x110'),
        0x72126C: ('ldrsw', 'x8, [x8, #0x14f8]'),
        0x721278: ('ldp', 'x8, x10, [x10, #0x110]'),
    }
    for address, want in expected.items():
        instruction, = img.disasm(address, 4)
        assert (instruction.mnemonic, instruction.op_str) == want, hex(address)


def generate():
    img = MainImage()
    check(img)
    outputs = {}
    classes = {}
    for name, (kind, vt, handler, end) in CLASSES.items():
        outputs[f'{name}_capture_receiver.asm'] = asm(img, handler, end)
        classes[name] = {'fighter_kind': hex(kind), 'vtable': hex(vt),
                         'event_slot': hex(SLOT), 'handler': hex(handler),
                         'end_exclusive': hex(end),
                         'handler_sha256': hashlib.sha256(img.data[handler:end]).hexdigest()}
    wrappers = {}
    for name, value, _ in symbols(img):
        if any(f'{module}__' in name for module in ('CatchModule', 'LinkModule', 'StatusModule', 'MotionModule', 'PostureModule')):
            instructions = img.disasm(value, 24)
            if len(instructions) < 3:
                continue
            if instructions[0].mnemonic == 'ldr' and instructions[0].op_str.startswith('x0, [x0, #'):
                wrappers[name] = {'offset': hex(value), 'instructions': img.function_text(value, 8)}
    needed = ('set_catch', 'change_status_request_impl', 'set_model_constraint_flag',
              'get_model_constraint_flag', 'set_constraint_translate_offset',
              'LinkModule__is_link_impl', 'LinkModule__set_attribute_impl',
              'MotionModule__is_flip_impl', 'PostureModule__scale_impl')
    wrappers = {name: value for name, value in wrappers.items() if any(n in name for n in needed)}
    assert len(wrappers) == 9
    report = {
        'date': '2026-09-30', 'evidence_tier': 'B', 'tool_version': VERSION,
        'tool': 'tools/audit_mflip_capture_native.py',
        'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'input': img.path.relative_to(ROOT).as_posix(),
        'input_sha256': hashlib.sha256(img.data).hexdigest(), 'classes': classes,
        'capture_branch': {
            'event_hash': '0x78bfea6e5', 'event_dispatch': '0x956bac..0x956bbc',
            'victim_status_gate': {'event_offset': '0x38', 'value': '0xf0', 'at': '0x956c94'},
            'donor_attacker_status_gates': ['0x1e5', '0x1ee'],
            'donor_cling_request': {'status': '0x1e8', 'at': '0x956cd0..0x956ce8'},
            'acceptance_write': {'event_offset': '0x28', 'value': 1, 'at': '0x956cec..0x956cf0'},
            'constraint_write': {'event_offset': '0x4f', 'value': 0, 'at': '0x956cf4'},
            'catch_sender': {'event_offset': '0x20', 'at': '0x956cf8..0x956d08'},
            'remaining_setup': '0x956d0c..0x956fd4: conditional catch reset, link constraint setup and victim-dependent translated offset',
        },
        'exported_wrapper_controls': wrappers,
        'owned_offset_source': {
            'parameter': 'fighter_param_thrown.prc/diddy_special_s',
            'hash': '0xf85bea337',
            'decoder_dispatch': asm(img, 0x816374, 0x816390),
            'native_helper': asm(img, 0x721240, 0x7212cc),
            'measurement': 'Decoder selects vector at +0x110 for diddy_special_s; native helper reads that vector in triples via the per-kind index at +0x14f8.',
        },
        'limitations': [
            'No controlled hardware run: omitted handler is a fix hypothesis, not an established cause.',
            'Do not call Diddy class code on Pyra: donor status gates and class storage are fighter-specific.',
            'The full post-RET branch tail is included; first-RET-only extraction omits capture positioning.',
            'A gated plugin-owned receiver needs explicit approval under AGENTS.md rule 17.',
        ],
    }
    outputs['capture_native.json'] = json.dumps(report, indent=2) + '\n'
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    outputs = generate()
    if not args.smoke:
        for name, content in outputs.items():
            (ROOT / 'refs/diddy_monkey_flip' / name).write_text(content, encoding='utf-8')
    print(f'Monkey Flip native capture audit {VERSION}: {len(outputs)} artifacts; assertions passed')


if __name__ == '__main__':
    main()
