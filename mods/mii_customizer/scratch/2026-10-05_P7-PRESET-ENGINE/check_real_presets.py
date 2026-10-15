"""P7-PRESET-ENGINE: run the plugin's preset parser (host build of plugin/src/preset.rs) over the
generated preset file of P6-PRESET-DATA and compare every stored value, bit for bit, with an
independent reading of the same text (Python's correctly rounded float -> IEEE single).

usage: python check_real_presets.py        exit 0 = file present and everything agrees
                                            exit 2 = the file does not exist
Reads workspace gamedata/mii_customizer/P6-PRESET-DATA/presets.txt. Copies nothing: it prints
counts, hashes and the size only, and the compiled helper goes to builds/.cache/host-test/."""
import hashlib, os, struct, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
WS = MOD.parents[1]
SRC = WS / 'gamedata/mii_customizer/P6-PRESET-DATA/presets.txt'
EXE = MOD / 'builds/.cache/host-test/preset_report_p7.exe'
ok = bad = 0


def check(name, cond, detail=''):
    global ok, bad
    ok += bool(cond)
    bad += not cond
    print(('PASS ' if cond else 'FAIL ') + name + (' | ' + str(detail) if detail != '' else ''))


if not SRC.is_file():
    print('ABSENT gamedata/mii_customizer/P6-PRESET-DATA/presets.txt (workspace-relative)')
    sys.exit(2)
raw = SRC.read_bytes()
print(f'input gamedata/mii_customizer/P6-PRESET-DATA/presets.txt size={len(raw)} sha256={hashlib.sha256(raw).hexdigest()}')

EXE.parent.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, PATH=str(Path.home() / '.cargo/bin') + os.pathsep + os.environ['PATH'])
subprocess.run(['rustc', '+stable-x86_64-pc-windows-gnu', '--edition', '2021', '-O', str(HERE / 'preset_report.rs'), '-o', str(EXE)],
               check=True, env=env)
out = subprocess.run([str(EXE), str(SRC), '--dump'], check=True, capture_output=True, text=True).stdout.splitlines()
head = dict(kv.split('=') for kv in out[0].split())
print('plugin parser:', out[0])
print('plugin parser:', out[1])
for line in out:
    if line.startswith(('field ', 'reject ', 'fields_per_preset')):
        print('plugin parser:', line)

# Independent reading of the text: no code shared with the plugin.
want = {}
cur = None
names = []
for n, line in enumerate(raw.decode('ascii').split('\n')[1:], start=2):
    f = line.split('#')[0].split()
    if not f:
        continue
    if f[0] == 'fighter':
        cur = (f[1], int(f[2], 16))
        names.append(f[1])
        continue
    bits = struct.unpack('<I', struct.pack('<f', float(f[1])))[0]
    want[(cur[0], cur[1], int(f[0], 16))] = bits
got = {}
for line in out:
    if line.startswith('value '):
        _, name, kind, field, bits = line.split()
        got[(name, int(kind, 16), int(field, 16))] = int(bits, 16)

check('first line is `mc_presets 1`', raw.split(b'\n')[0] == b'mc_presets 1')
check('state ok, no rejected and no skipped line', (head['state'], head['rejected'], head['skipped']) == ('ok', '0', '0'), out[0])
check('size is under the 512 KiB limit of contract A', len(raw) <= 512 * 1024, len(raw))
check('preset count equals the number of `fighter` lines and is at most 128', int(head['presets']) == len(names) <= 128, len(names))
check('preset names are unique', len(set(names)) == len(names))
check('distinct field hashes at most 48', int(head['hashes']) <= 48, head['hashes'])
check('field lines stored equal the value lines of the file', int(head['field_lines']) == len(want), (head['field_lines'], len(want)))
check('every value the plugin parser stored has the bits of the correctly rounded decimal', got == want,
      f'{len(got)} stored, {len(want)} in the text, {sum(1 for k in want if got.get(k) != want[k])} differ')
print(f'\n{ok} passed, {bad} failed')
sys.exit(1 if bad else 0)
