"""Measure Hero lightning's recipient event dependency on pinned 13.0.4 main.

Version 1.0.0. Run with --check for a reproducible offline smoke test against
the saved JSON and disassembly. This measures dispatch, not console behaviour.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from main_image import MainImage

ROOT = Path(__file__).resolve().parents[1]
HASH = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'


def measure():
    image = MainImage()
    assert hashlib.sha256(image.data).hexdigest() == HASH
    assert image.ptr(0x4f931d8 + 0x170) == 0x8555a0
    assert image.ptr(0x4fb1fa0 + 0x170) == 0xa2a000
    assert image.ptr(0x51b1800) == 0x33caa70
    spans = [('lightning_callback', 0x33caa70, 0x33cabc4),
             ('hero_receiver', 0x8555a0, 0x855b00),
             ('mythra_receiver', 0xa2a000, 0xa2a270)]
    instructions = {i.address: (i.mnemonic, i.op_str)
                    for _, start, end in spans for i in image.disasm(start, end-start)}
    def expect(address, mnemonic, operands):
        assert instructions[address] == (mnemonic, operands), (hex(address), instructions[address])
    def constant(address):
        value = 0
        for offset in (0, 4, 8):
            mnemonic, operands = instructions[address+offset]
            assert mnemonic == ('mov' if offset == 0 else 'movk')
            args = operands.split(', ')
            shift = int(args[2].split('#')[1]) if len(args) == 3 else 0
            value |= int(args[1][1:], 0) << shift
        return value
    lightning = constant(0x33caad0)
    assert lightning == constant(0x855690) == 0x214e64eedd
    expect(0x33cab08, 'blr', 'x8')
    expect(0x8556a0, 'b.eq', '#0x85593c')
    expect(0x855944, 'mov', 'w1, #2')
    expect(0x8559a8, 'bl', '#0x851ac0')
    pivot = constant(0xa2a020)
    high = constant(0xa2a0cc)
    own = constant(0xa2a0d8)
    expect(0xa2a030, 'b.gt', '#0xa2a0cc')
    expect(0xa2a0e8, 'ccmp', 'x23, x22, #4, ne')
    expect(0xa2a0ec, 'b.ne', '#0xa2a214')
    expect(0xa2a218, 'mov', 'w0, #1')
    expect(0xa2a228, 'ret', '')
    # Execute the measured high dispatch comparisons: CCMP preserves EQ when
    # the first comparison matches, otherwise it compares against the own kind.
    def high_dispatch(kind):
        assert kind > pivot
        return kind == high or kind == own
    assert not high_dispatch(lightning)
    assert high_dispatch(own)
    assembly = '\n'.join(f'\n{name} {start:#x}..{end:#x}\n' + '\n'.join(
        f'{i.address:08x}: {i.mnemonic} {i.op_str}' for i in image.disasm(start, end-start))
        for name, start, end in spans) + '\n'
    report = {'tool': 'tools/audit_hero_side_b_link_events.py', 'version': '1.0.0',
              'tier': 'B', 'input_sha256': HASH,
              'hero_receiver_slot': '0x4f93348', 'hero_receiver': '0x8555a0',
              'mythra_receiver_slot': '0x4fb2110', 'mythra_receiver': '0xa2a000',
              'lightning_callback_slot': '0x51b1800', 'event_kind': hex(lightning),
              'hero_article_slot_operand': 2, 'hero_handler_call': '0x851ac0',
              'offline_controls': {'hero_event_matches_mythra_dispatch': False,
                                   'mythra_own_event_matches': True,
                                   'mythra_own_event': hex(own)},
              'required_review': 'Additional gated recipient +0x170 interception; not authorized or implemented.'}
    return json.dumps(report, indent=2) + '\n', assembly


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for suffix, content in zip(('json', 'asm.txt'), measure()):
        path = ROOT / 'refs/brave_special_s' / f'link_event_native_audit.{suffix}'
        if args.check:
            assert path.read_text() == content, path
        else:
            path.write_text(content)
    print('Hero lightning recipient event audit: PASS (offline)')
