"""Generate `generated/common.rs`: every remaining non-special ACMD script.

Why this exists
---------------
`gen_acmd.py` ported the moves somebody thought of (jab, tilts, smashes, aerials,
grabs, throws): 110 of Pyra's 948 game/effect/sound/expression scripts. Anything
else Pyra ships kept running on G&W's body. The clearest symptom was the old Aegis
sword on nair and bair: G&W's nair/bair have no `effect_*` script, so the generator
emitted none, and Pyra's own `effect_attackairn` / `effect_attackairb` (sword
trails) kept playing.

This tool works from the motion lists instead of from a hand-written list, so it
cannot miss a script that a move can actually run:

* the motion list decides which scripts a motion invokes, by the `game_script`
  name it carries; effect/sound/expression share that name's suffix;
* for every suffix of every G&W motion kind that is not a special / final / entry:
    - G&W's script is textually the same as Pyra's -> nothing to do (R14). Pyra's
                             already runs exactly what G&W's would; most are item
                             swings/shots that call engine-common helpers
                             (`game_SwordSwing1Common` ...) which the toolchain does
                             not expose, so they could not be ported anyway;
    - G&W has the script  -> port it (same rules as gen_acmd.py, R1-R13);
    - only Pyra has it    -> emit an empty override, because G&W runs nothing
                             there and Pyra's script must not run on his body.

Deliberately NOT done here, and recorded in the manifest so it stays visible:

* `sound_*` scripts. G&W's sounds live in a bank eflame does not load, so porting his
  script would only swap Pyra's footsteps and voice for silence. That needs the
  sound-bank work (handoff inventory item 4), not a script port.
* special / final / entry / visual-scene scripts. Specials are custom statuses,
  and the entry and swap scenes are what keep the Pyra<->Mythra swap vanilla.

Run:
    toolchains/py312/python.exe src/pgwr/tools/gen_common.py
    toolchains/py312/python.exe src/pgwr/tools/gen_common.py --check
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_acmd as g  # noqa: E402  (shares the transformation rules R1-R13)

ROOT = g.ROOT
PYRA_DUMP = ROOT / 'dumps' / 'scripts' / 'SSBU-Dumped-Scripts-main' / 'smashline' / 'lua2cpp_eflame' / 'eflame'
EXPORT = Path(os.environ.get('MGW_EXPORT', ROOT / 'dumps' / 'arc'))
PROJECT = Path(__file__).resolve().parents[1]
OUT = g.OUT_DIR / 'common.rs'
MANIFEST = PROJECT / 'generated-common-manifest.json'

# Ported here. `sound` is left alone on purpose (see the module docstring).
CATEGORIES = ('game', 'effect', 'expression')
# Scripts left as Pyra's because the dump lost information the port needs. Each entry
# is a decision not to guess; the reason is what a person needs to resolve it.
UNPORTABLE = {
    'expression_lose': 'mesh hide calls lost their arguments in the dump '
                       '(`as_hash()const(...)` then a no-argument set_mesh_visibility)',
    'expression_sleeploop': 'if/else nesting mangled by the decompiler; the branch '
                            'that picks the left or right zzz mesh cannot be trusted',
    'expression_itemspecialflaghoist': 'decompiler artifacts around a special-flag item check',
    'effect_scopeairrapidaerial': 'trailing argument of the common effect call unknown',
    **{n: 'ItemModule call whose trailing arguments the dump dropped (binding takes 4, dump has 3)'
       for n in ('game_clubswing1', 'game_clubswing3', 'game_clubswing4',
                 'game_swordswing1', 'game_swordswing3', 'game_swordswing4', 'game_swordswingdash')},
    **{n: 'ItemModule pickup/use call whose trailing arguments the dump dropped'
       for n in ('game_downeatd', 'game_downeatu', 'game_itemheavyget', 'game_itemlighteat',
                 'game_itemlightget', 'game_itemlightwalkeat', 'game_itemlightwalkget')},
}
# Suffixes this tool never touches.
EXCLUDED_PREFIXES = ('special', 'final', 'entry', 'visualscene')


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def list_scripts(path: Path) -> dict[int, int]:
    """{motion kind hash: game_script hash} for one motion_list.bin."""
    data = path.read_bytes()
    _, _, count = struct.unpack_from('<QQQ', data)
    offset, out = 24, {}
    for _ in range(count):
        kind, script, _flags, _blend, anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset = ((offset + 24 + anims * 9 + 3) & ~3) + size
        out[kind] = script
    return out


def dump_functions(directory: Path) -> dict[str, tuple[str, str]]:
    """{fn name: (file, text)} for a lua2cpp dump directory."""
    out = {}
    for path in sorted(directory.glob('*.txt')):
        text = path.read_text(encoding='utf-8', errors='replace')
        for name, body in g.split_functions(text).items():
            out[name] = (path.name, body)
    return out


def canon(body: str, name: str) -> str:
    """A script body with its own name and all whitespace removed, for R14."""
    body = body.replace(name, '@')
    return re.sub(r'\s+', '', body)


def already_registered() -> set[str]:
    """Script names gen_acmd.py's modules register, read from the checked-in files."""
    names = set()
    for group in g.GROUPS:
        path = g.OUT_DIR / f'{group}.rs'
        if path.is_file():
            names |= set(re.findall(r'_acmd\("(\w+)"', path.read_text(encoding='utf-8')))
    return names


def build():
    gw_dump = dump_functions(g.GW)
    pyra_dump = dump_functions(PYRA_DUMP)
    suffixes = {n.split('_', 1)[1] for n in list(gw_dump) + list(pyra_dump)
                if n.split('_', 1)[0] in ('game', 'effect', 'sound', 'expression')}
    by_hash = {hash40('game_' + s): s for s in suffixes}

    reach = {}
    for slot in ('c06', 'c07'):
        gw = list_scripts(EXPORT / 'fighter/gamewatch/motion/body' / slot / 'motion_list.bin')
        reach[slot] = {by_hash[h] for h in gw.values() if h in by_hash}
    require_same = reach['c06'] == reach['c07']
    if not require_same:
        raise SystemExit('error: c06 and c07 G&W motion lists reach different scripts')
    wanted = sorted(s for s in reach['c06'] if not s.startswith(EXCLUDED_PREFIXES))

    done = already_registered()
    drops: list[str] = []
    ported, blanked, identical, unported, parts = [], [], [], [], []
    for suffix in wanted:
        for cat in CATEGORIES:
            name = f'{cat}_{suffix}'
            if name in done:
                continue
            if name in UNPORTABLE:
                unported.append(name)
            elif (name in gw_dump and name in pyra_dump
                  and canon(gw_dump[name][1], name) == canon(pyra_dump[name][1], name)):
                identical.append(name)
            elif name in gw_dump:
                file, text = gw_dump[name]
                parts.append(g.strip_body(text, drops))
                ported.append((name, file))
            elif name in pyra_dump:
                parts.append(
                    f'unsafe extern "C" fn {name}(agent: &mut L2CAgentBase) {{\n'
                    f'    // eflame ships `{name}` ({pyra_dump[name][0]}); Mr. Game & Watch has\n'
                    f'    // no such script, so on c06/c07 it runs nothing.\n'
                    f'}}\n')
                blanked.append(name)

    notes = [f'// GEN-NOTES: {len(ported)} scripts ported from G&W, {len(blanked)} eflame '
             f'scripts emptied']
    for line in sorted(set(drops)):
        notes.append(f'//   {line}')
    header = g.HEADER.format(drops='\n'.join(notes))

    lines = ['pub fn install() {',
             '    let mut agent = Agent::new("eflame");',
             '    agent.set_costume(crate::TARGET_COSTUMES.to_vec());']
    for name, _ in ported:
        cat = name.split('_', 1)[0]
        lines.append(f'    agent.{cat}_acmd("{name}", {name}, Priority::Default);')
    for name in blanked:
        cat = name.split('_', 1)[0]
        lines.append(f'    agent.{cat}_acmd("{name}", {name}, Priority::Default);')
    lines += ['    agent.install();', '}', '']
    code = header + '\n' + '\n'.join(parts) + '\n' + '\n'.join(lines)

    left_sounds = sorted(f'sound_{s}' for s in wanted if f'sound_{s}' in pyra_dump)
    manifest = {
        'suffixes_covered': len(wanted),
        'ported': len(ported), 'blanked': len(blanked), 'identical_to_pyra_skipped': len(identical),
        'identical': identical,
        'unported': {n: UNPORTABLE[n] for n in unported},
        'ported_by_category': {c: sum(1 for n, _ in ported if n.startswith(c + '_')) for c in CATEGORIES},
        'blanked_by_category': {c: sum(1 for n in blanked if n.startswith(c + '_')) for c in CATEGORIES},
        'blanked': blanked,
        'sound_scripts_left_as_pyra': len(left_sounds),
        'excluded_prefixes': list(EXCLUDED_PREFIXES),
        'sha256': hashlib.sha256(code.encode()).hexdigest(),
    }
    return code, manifest


def main() -> int:
    check = '--check' in sys.argv
    code, manifest = build()
    if check:
        if not OUT.is_file() or OUT.read_text(encoding='utf-8') != code:
            print(f'  {OUT.name}: STALE or missing')
            return 1
        print(f'  {OUT.name}: up to date')
        return 0
    OUT.write_text(code, encoding='utf-8')
    MANIFEST.write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    print(f'  wrote {OUT.relative_to(ROOT)}  {len(code.splitlines())} lines')
    print(json.dumps({k: v for k, v in manifest.items() if k not in ('blanked', 'identical', 'unported')}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
