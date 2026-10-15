"""Read missing resources using Arc Explorer's installed smash_arc.dll.

ABI source: ScanMountGoat/SmashArcNet, SmashArcNet/RustBindings.cs and
RustTypes/RustEnums.cs. This performs archive reads only; no Switch writes.
The server may serialize clients: close Arc Explorer while this runs.
"""
import argparse
import ctypes as c
import hashlib
import json
from pathlib import Path
import shutil
import time
from prepare import ROOT, h40, safe_relative, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ip', default='192.168.2.166')
    parser.add_argument('--dll', type=Path, default=Path.home() / 'Downloads/ArcExplorer_win_x64/smash_arc.dll')
    parser.add_argument('--export', type=Path, default=ROOT.parent / 'export')
    parser.add_argument('--region', type=int, choices=range(15), default=2,
                        help='Arc region: 2=US English (Arc Explorer default), 5=EU English, 8=German')
    parser.add_argument('--paths', type=Path, default=ROOT / 'reports/missing.json')
    args = parser.parse_args()
    paths = json.loads(args.paths.read_text(encoding='utf8'))
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise ValueError('Expected a JSON array of archive paths')
    for p in paths:
        safe_relative(p)
    lib = c.CDLL(str(args.dll.resolve()))
    lib.arc_open_networked.argtypes = [c.c_char_p]
    lib.arc_open_networked.restype = c.c_void_p
    lib.arc_free.argtypes = [c.c_void_p]
    lib.arc_free.restype = None
    lib.arc_extract_file_regional.argtypes = [c.c_void_p, c.c_uint64, c.c_char_p, c.c_uint32]
    lib.arc_extract_file_regional.restype = c.c_uint8
    lib.arc_get_file_count.argtypes = [c.c_void_p]
    lib.arc_get_file_count.restype = c.c_uint64
    lib.arc_get_version.argtypes = [c.c_void_p]
    lib.arc_get_version.restype = c.c_uint32
    print('Opening ARC server at {}:43022 ...'.format(args.ip), flush=True)
    handle = lib.arc_open_networked(args.ip.encode('ascii'))
    if not handle:
        raise RuntimeError('Archive server did not return a handle')
    report = {'ip': args.ip, 'region': args.region,
              'arc_version': lib.arc_get_version(handle),
              'archive_file_count': lib.arc_get_file_count(handle), 'files': []}
    print('Archive opened:', report['archive_file_count'], 'files', flush=True)
    report_path = ROOT / 'reports/extraction.json'
    if report_path.exists():
        previous = json.loads(report_path.read_text(encoding='utf8'))
        if all(previous.get(k) == report[k] for k in ('ip', 'region', 'arc_version', 'archive_file_count')):
            report['files'] = previous.get('files', [])
    try:
        for index, relative in enumerate(paths):
            destination = args.export.resolve() / safe_relative(relative)
            if destination.exists():
                continue
            if shutil.disk_usage(args.export).free < 128 * 1024**2:
                raise RuntimeError('Less than 128 MiB free; extraction stopped before the next file')
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + '.pmclone-part')
            if temporary.exists():
                raise FileExistsError('Inspect incomplete extraction before retrying: ' + str(temporary))
            archive_path = relative.replace('prebuilt/', 'prebuilt:/', 1) if relative.startswith('prebuilt/') else relative
            result = lib.arc_extract_file_regional(handle, h40(archive_path),
                                                   str(temporary).encode('utf8'), args.region)
            row = {'path': relative, 'result': int(result)}
            if result == 0 and temporary.is_file() and temporary.stat().st_size > 0:
                row['bytes'] = temporary.stat().st_size
                row['sha256'] = hashlib.sha256(temporary.read_bytes()).hexdigest()
                # rename refuses to replace an existing destination on Windows.
                temporary.rename(destination)
            else:
                row['error'] = 'Extraction failed or empty; any partial file is preserved'
            report['files'].append(row)
            write_json('extraction.json', report)
            print('{}/{} result={} {}'.format(index + 1, len(paths), result, relative), flush=True)
    finally:
        lib.arc_free(handle)
        report['finished_at_unix'] = time.time()
        write_json('extraction.json', report)


if __name__ == '__main__':
    main()
