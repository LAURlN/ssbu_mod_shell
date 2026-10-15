"""Build-independent local packaging and static checks for the recorder diagnostic.

Never writes to the SD. Run after cargo skyline build --release in trace/.
"""
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    source = (ROOT / 'trace/src/input.rs').read_text()
    declaration = source.split('const NEEDLE_FIM:', 1)[1].split('= [', 1)[1].split('];', 1)[0]
    needle = bytes(int(x, 16) for x in re.findall(r'0x[0-9a-f]+', declaration))
    main_image = (ROOT / 'reference/dumps/images/main.bin').read_bytes()
    first = main_image.find(needle)
    if first != 0x1750f70 or main_image.find(needle, first + 1) != -1:
        raise SystemExit('Input signature must occur exactly once at main+0x1750f70')
    required = [
        b'_ZN3app8lua_bind38FighterManager__get_fighter_entry_implEPNS_14FighterManagerENS_14FighterEntryIDE',
        b'_ZN3app8lua_bind37FighterEntry__current_fighter_id_implEPNS_12FighterEntryE',
    ]
    for symbol in required:
        if symbol + b'\0' not in main_image:
            raise SystemExit('Missing native symbol: ' + symbol.decode())
    nro = ROOT / 'trace/target/aarch64-skyline-switch/release/libpmclone_trace.nro'
    data = nro.read_bytes()
    if data[0x10:0x14] != b'NRO0':
        raise SystemExit('Invalid NRO magic')
    sources = list((ROOT / 'trace/src').glob('*.rs')) + [ROOT / 'trace/Cargo.toml', ROOT / 'trace/Cargo.lock']
    if any(p.stat().st_mtime > nro.stat().st_mtime for p in sources):
        raise SystemExit('Recorder source is newer than NRO; rebuild before packaging')
    relative = Path('atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpmclone_trace.nro')
    local_tree = ROOT.parent / 'mod_output/new_standalone'
    target = local_tree / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    instructions = ROOT / 'trace/README.md'
    shutil.copyfile(str(instructions), str(local_tree / 'TRACE_START_HERE.md'))
    report = {
        'version': '0.1.1', 'console_tested': False, 'm0_complete': False,
        'main_sha256': sha(main_image), 'input_signature_offset': hex(first),
        'input_signature_matches': 1, 'native_symbol_names_present': True,
        'nro_sha256': sha(data), 'nro_bytes': len(data),
        'sources': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sources},
    }
    report_data = json.dumps(report, indent=2) + '\n'
    (ROOT / 'reports/trace-build.json').write_text(report_data, encoding='utf8')
    archive = ROOT / 'test_output/PyraMythra_trace_check.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(archive), 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(relative.as_posix(), data)
        z.write(str(instructions), 'START_HERE.md')
        z.writestr('trace-build.json', report_data)
    with zipfile.ZipFile(str(archive)) as z:
        assert z.read(relative.as_posix()) == target.read_bytes() == data
        assert z.testzip() is None
    print('Signature unique at', hex(first), '; native symbol names present')
    print('NRO:', len(data), 'bytes; SHA256:', sha(data))
    print('Package verified:', archive)
    print('No SD writes. Hardware acceptance remains pending.')


if __name__ == '__main__':
    main()
