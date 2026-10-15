"""Embed Elight's native up-B game ACMD as safe non-c07 fallback scripts."""
from pathlib import Path
import hashlib
import re

root = Path(__file__).resolve().parents[3]
dump = root / 'SSBU-Dumped-Scripts-main/smashline/lua2cpp_elight/elight'
out = root / 'mod_files/mythra_gamewatch_swap/src/hero_spin3_vanilla_acmd.rs'
specs = (
    ('SpecialHiStart.txt', 'game_specialhistart', 'vanilla_game_specialhistart'),
    ('SpecialAirHi1.txt', 'game_specialairhi1', 'vanilla_game_specialairhi1'),
    ('SpecialAirHiJump.txt', 'game_specialairhijump', 'vanilla_game_specialairhijump'),
    ('SpecialAirHiEnd.txt', 'game_specialairhiend', 'vanilla_game_specialairhiend'),
)
pieces = ['// Generated from the local Elight ACMD dump for non-c07 vanilla fallback.\n']
for filename, source_name, fallback_name in specs:
    data = (dump / filename).read_bytes()
    body = data.decode('utf-8')
    pattern = rf'unsafe extern "C" fn {source_name}\(agent: &mut L2CAgentBase\) \{{'
    match = re.search(pattern, body)
    if not match:
        raise SystemExit(f'Missing {source_name} in {filename}')
    depth = 1
    end = match.end()
    while depth:
        if body[end] == '{':
            depth += 1
        elif body[end] == '}':
            depth -= 1
        end += 1
    extracted = body[match.start():end].replace(f'fn {source_name}(', f'fn {fallback_name}(', 1)
    # The dump uses a signed cast but skyline-smash exposes set_int64's value
    # parameter as u64; the Hash40 value is nonnegative and fits both forms.
    extracted = extracted.replace('hash40("special_air_hi_jump") as i64',
                                  'hash40("special_air_hi_jump") as u64')
    pieces.append(f'// {filename} SHA256 {hashlib.sha256(data).hexdigest()}\n{extracted}\n')
out.write_text('\n'.join(pieces), encoding='utf-8')
print(f'Generated {out} ({out.stat().st_size} bytes)')
