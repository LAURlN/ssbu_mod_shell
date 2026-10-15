"""Smoke-test the linked Snake QueryMemory C ABI (v1.0.0); offline evidence only."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_pgwr_svc_guard import functions
ROOT = Path(__file__).resolve().parents[1]
def main():
    path = ROOT / 'builds/.cache/pgwr-snake-target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.so'
    blob = path.read_bytes()
    address, code = functions(blob)['pgwr_snake_query_memory']
    assert code == bytes.fromhex('e10f1ff8c10000d4e20741f8410000b9c0035fd6')
    report = {'tool_version': '1.0.0', 'date': '2026-09-30', 'tier': 'B',
              'hardware_validated': False, 'input': str(path.relative_to(ROOT)).replace('\\', '/'),
              'sha256': hashlib.sha256(blob).hexdigest(), 'symbol': 'pgwr_snake_query_memory',
              'address': hex(address), 'instructions_hex': code.hex()}
    output = ROOT / 'refs/snake_grenade/compiled_guard_audit.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('PASS: compiled Snake QueryMemory has the pinned five-instruction C ABI')
if __name__ == '__main__': main()
