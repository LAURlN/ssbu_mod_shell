"""Copy vanilla script text and shared database inputs; do not install them."""
from pathlib import Path
from prepare import ROOT, materialize, digest, write_json


def main():
    rows = []
    for name in ('eflame', 'elight', 'element'):
        source = ROOT.parent / 'SSBU-Dumped-Scripts-main/smashline' / ('lua2cpp_' + name)
        for path in source.rglob('*.txt'):
            dest = ROOT / 'reference/acmd' / ('lua2cpp_' + name) / path.relative_to(source)
            data = path.read_bytes()
            rows.append(dict(source=str(path), copy=dest.relative_to(ROOT).as_posix(),
                             sha256=digest(data), status=materialize(path, dest, data)))
    write_json('acmd-sources.json', dict(compiled=False, vanilla_parity_verified=False, files=rows))
    paths = ['fighter/common/param/' + name + '.prc' for name in
             ('common', 'battle_object', 'fighter_param', 'fighter_param_motion', 'fighter_param_thrown', 'effect', 'sound')]
    paths.append('ui/param/database/ui_chara_db.prc')
    shared = []
    for relative in paths:
        source = ROOT.parent / 'export' / relative
        if not source.is_file():
            shared.append(dict(path=relative, status='missing'))
            continue
        data = source.read_bytes()
        shared.append(dict(path=relative, sha256=digest(data),
                           status=materialize(source, ROOT / 'reference/shared' / relative, data)))
    write_json('shared-databases.json', shared)
    print('Verified script references:', len(rows), 'shared databases:', sum(s['status'] == 'verified' for s in shared), '/', len(shared))


if __name__ == '__main__':
    main()
