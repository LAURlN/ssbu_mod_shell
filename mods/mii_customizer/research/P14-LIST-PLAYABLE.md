# P14-LIST-PLAYABLE

> **Coordinator note, 2026-10-07: PARKED at the user's request, not reviewed, nothing of it
> shipped.** The user looked at the result and wants a different question answered later:
> not "is this fighter selectable", but, per character and per move, how hard the move is to
> give to a Gunner (skeleton match, weapons, special mechanics: e.g. Pyra/Mythra moves fine
> except down special, Steve hard throughout). "Once the foundation is working, we'll go
> through the characters one by one." The list on the console is unchanged (86 rows,
> `koopag` included). This task changed `tools/stat-presets/`; treat those edits as
> unreviewed.


Status: report complete with one host-linker limitation. Evidence tier B (game-data decode,
source inspection, and host-side checks); no runtime claim is intended.

## Scope and method

Determine which of the 94 fighter presets correspond to character-select entries using the
user's extracted game data, then make the generated `mc_list 1` exclude set reproducible.
Keep `presets_wide.txt` and all existing generated folders unchanged. New game-derived outputs
belong only in workspace `gamedata/mii_customizer/P14-LIST-PLAYABLE/`.

The archive file was extracted with the registered `tools/arc-extract` tool to
`gamedata/mii_customizer/P14-LIST-PLAYABLE/files/ui/param/database/ui_chara_db.prc`:
34,753 bytes, SHA-256
`c65a0da57a20fe790c2f0948d017a54c4885341885d9a30866c590ccf380f380`. The decoded PRC has 121
database entries; all 94 `fighter_param_table` presets were independently classified against
them. `mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv` is used only to resolve hashes to
field and fighter-kind names.

## Playability source and field

For ordinary CSS fighters, the source is the database row whose `name_id` or hash-resolved
`fighter_kind` matches the preset. `can_select` is a boolean describing whether the entry is
selectable; `disp_order` is the CSS order number. I classify a fighter as playable when the
matching entry has `can_select=true` and `disp_order >= 0`. Both values are checked so a
selectable flag without a CSS order cannot silently qualify. This marks echoes and each Mii
class playable, as well as both Aegis forms (they share `disp_order=80`).

Two structural cases are mapped to the selectable roster entry. `popo` and `nana` are the two
presets represented by the single selectable `ice_climber` CSS row. The three Pokemon rows
have `is_called_pokemon=true`; their playable parent is the `ptrainer` row, which is selectable
with `disp_order=37`. They remain playable for this list despite their own `can_select=false`
and `disp_order=-1` values.

The cross-check is presence of `nam_chr1_00_<preset>` in the extracted `msg_name.msbt`, matching
the current list generator. `popo`, `nana`, `eflame`, `elight`, and the three `miienemy*` rows
have no such label and therefore remain out of the list under the existing label rule. `koopag`
does have a label, but its database entry says `is_boss=true`, `can_select=false`,
`disp_order=-1`; it was the only currently listed non-playable row. `miigunner` is selectable
but intentionally excluded because it is the row-zero default on each page.

## Findings

The table below has one row per fighter preset in `fighter_param_table` order. “Current list”
means the input `COORD-session3/list.txt`; “Decision” describes the P14 list result. A blank
game display name is shown as `(no nam_chr1_00 label)`, rather than being guessed.

| Preset name | Display name | Current list | Playable per source | Decision | Reason |
|---|---|---:|---:|---|---|
| mario | Mario | yes | yes | keep | can_select=true and disp_order=0 |
| donkey | Donkey Kong | yes | yes | keep | can_select=true and disp_order=1 |
| link | Link | yes | yes | keep | can_select=true and disp_order=2 |
| samus | Samus | yes | yes | keep | can_select=true and disp_order=3 |
| yoshi | Yoshi | yes | yes | keep | can_select=true and disp_order=5 |
| kirby | Kirby | yes | yes | keep | can_select=true and disp_order=6 |
| fox | Fox | yes | yes | keep | can_select=true and disp_order=7 |
| pikachu | Pikachu | yes | yes | keep | can_select=true and disp_order=8 |
| luigi | Luigi | yes | yes | keep | can_select=true and disp_order=9 |
| ness | Ness | yes | yes | keep | can_select=true and disp_order=10 |
| captain | Captain Falcon | yes | yes | keep | can_select=true and disp_order=11 |
| purin | Jigglypuff | yes | yes | keep | can_select=true and disp_order=12 |
| peach | Peach | yes | yes | keep | can_select=true and disp_order=13 |
| koopa | Bowser | yes | yes | keep | can_select=true and disp_order=15 |
| popo | (no nam_chr1_00 label) | no | yes | already excluded; no nam_chr1_00 label | paired Ice Climbers presets; their shared CSS row is selectable |
| nana | (no nam_chr1_00 label) | no | yes | already excluded; no nam_chr1_00 label | paired Ice Climbers presets; their shared CSS row is selectable |
| sheik | Sheik | yes | yes | keep | can_select=true and disp_order=17 |
| zelda | Zelda | yes | yes | keep | can_select=true and disp_order=18 |
| mariod | Dr. Mario | yes | yes | keep | can_select=true and disp_order=19 |
| pichu | Pichu | yes | yes | keep | can_select=true and disp_order=20 |
| falco | Falco | yes | yes | keep | can_select=true and disp_order=21 |
| marth | Marth | yes | yes | keep | can_select=true and disp_order=22 |
| younglink | Young Link | yes | yes | keep | can_select=true and disp_order=24 |
| ganon | Ganondorf | yes | yes | keep | can_select=true and disp_order=25 |
| mewtwo | Mewtwo | yes | yes | keep | can_select=true and disp_order=26 |
| roy | Roy | yes | yes | keep | can_select=true and disp_order=27 |
| gamewatch | Mr. Game & Watch | yes | yes | keep | can_select=true and disp_order=29 |
| metaknight | Meta Knight | yes | yes | keep | can_select=true and disp_order=30 |
| pit | Pit | yes | yes | keep | can_select=true and disp_order=31 |
| szerosuit | Zero Suit Samus | yes | yes | keep | can_select=true and disp_order=33 |
| wario | Wario | yes | yes | keep | can_select=true and disp_order=34 |
| snake | Snake | yes | yes | keep | can_select=true and disp_order=35 |
| ike | Ike | yes | yes | keep | can_select=true and disp_order=36 |
| pzenigame | Squirtle | yes | yes | keep | is_called_pokemon=true; selected through selectable Pokemon Trainer |
| pfushigisou | Ivysaur | yes | yes | keep | is_called_pokemon=true; selected through selectable Pokemon Trainer |
| plizardon | Charizard | yes | yes | keep | is_called_pokemon=true; selected through selectable Pokemon Trainer |
| diddy | Diddy Kong | yes | yes | keep | can_select=true and disp_order=38 |
| lucas | Lucas | yes | yes | keep | can_select=true and disp_order=39 |
| sonic | Sonic | yes | yes | keep | can_select=true and disp_order=40 |
| dedede | King Dedede | yes | yes | keep | can_select=true and disp_order=41 |
| pikmin | Olimar | yes | yes | keep | can_select=true and disp_order=42 |
| lucario | Lucario | yes | yes | keep | can_select=true and disp_order=43 |
| robot | R.O.B. | yes | yes | keep | can_select=true and disp_order=44 |
| toonlink | Toon Link | yes | yes | keep | can_select=true and disp_order=45 |
| wolf | Wolf | yes | yes | keep | can_select=true and disp_order=46 |
| murabito | Villager | yes | yes | keep | can_select=true and disp_order=47 |
| rockman | Mega Man | yes | yes | keep | can_select=true and disp_order=48 |
| wiifit | Wii Fit Trainer | yes | yes | keep | can_select=true and disp_order=49 |
| rosetta | Rosalina & Luma | yes | yes | keep | can_select=true and disp_order=50 |
| littlemac | Little Mac | yes | yes | keep | can_select=true and disp_order=51 |
| gekkouga | Greninja | yes | yes | keep | can_select=true and disp_order=52 |
| palutena | Palutena | yes | yes | keep | can_select=true and disp_order=53 |
| pacman | PAC-MAN | yes | yes | keep | can_select=true and disp_order=54 |
| reflet | Robin | yes | yes | keep | can_select=true and disp_order=55 |
| shulk | Shulk | yes | yes | keep | can_select=true and disp_order=56 |
| koopajr | Bowser Jr. | yes | yes | keep | can_select=true and disp_order=57 |
| duckhunt | Duck Hunt | yes | yes | keep | can_select=true and disp_order=58 |
| ryu | Ryu | yes | yes | keep | can_select=true and disp_order=59 |
| cloud | Cloud | yes | yes | keep | can_select=true and disp_order=61 |
| kamui | Corrin | yes | yes | keep | can_select=true and disp_order=62 |
| bayonetta | Bayonetta | yes | yes | keep | can_select=true and disp_order=63 |
| inkling | Inkling | yes | yes | keep | can_select=true and disp_order=64 |
| ridley | Ridley | yes | yes | keep | can_select=true and disp_order=65 |
| simon | Simon | yes | yes | keep | can_select=true and disp_order=66 |
| krool | King K. Rool | yes | yes | keep | can_select=true and disp_order=68 |
| shizue | Isabelle | yes | yes | keep | can_select=true and disp_order=69 |
| gaogaen | Incineroar | yes | yes | keep | can_select=true and disp_order=70 |
| packun | Piranha Plant | yes | yes | keep | can_select=true and disp_order=71 |
| jack | Joker | yes | yes | keep | can_select=true and disp_order=72 |
| brave | Hero | yes | yes | keep | can_select=true and disp_order=73 |
| buddy | Banjo & Kazooie | yes | yes | keep | can_select=true and disp_order=74 |
| dolly | Terry | yes | yes | keep | can_select=true and disp_order=75 |
| master | Byleth | yes | yes | keep | can_select=true and disp_order=76 |
| tantan | Min Min | yes | yes | keep | can_select=true and disp_order=77 |
| pickel | Steve | yes | yes | keep | can_select=true and disp_order=78 |
| demon | Kazuya | yes | yes | keep | can_select=true and disp_order=81 |
| trail | Sora | yes | yes | keep | can_select=true and disp_order=82 |
| eflame | (no nam_chr1_00 label) | no | yes | already excluded; no nam_chr1_00 label | can_select=true and disp_order=80 |
| elight | (no nam_chr1_00 label) | no | yes | already excluded; no nam_chr1_00 label | can_select=true and disp_order=80 |
| edge | Sephiroth | yes | yes | keep | can_select=true and disp_order=79 |
| miifighter | Mii Brawler | yes | yes | keep | can_select=true and disp_order=84 |
| miiswordsman | Mii Swordfighter | yes | yes | keep | can_select=true and disp_order=85 |
| miigunner | Mii Gunner | no | yes | exclude; Mii Gunner is page row 0 default | can_select=true and disp_order=86 |
| samusd | Dark Samus | yes | yes | keep | can_select=true and disp_order=4 |
| daisy | Daisy | yes | yes | keep | can_select=true and disp_order=14 |
| lucina | Lucina | yes | yes | keep | can_select=true and disp_order=23 |
| chrom | Chrom | yes | yes | keep | can_select=true and disp_order=28 |
| pitb | Dark Pit | yes | yes | keep | can_select=true and disp_order=32 |
| ken | Ken | yes | yes | keep | can_select=true and disp_order=60 |
| richter | Richter | yes | yes | keep | can_select=true and disp_order=67 |
| koopag | Giga Bowser | yes | no | remove; explicit exclusion | boss row; can_select=false and disp_order=-1 |
| miienemyf | (no nam_chr1_00 label) | no | no | exclude; existing miienemy prefix rule | no selectable CSS entry; source row has can_select=false / disp_order=-1 |
| miienemys | (no nam_chr1_00 label) | no | no | exclude; existing miienemy prefix rule | no selectable CSS entry; source row has can_select=false / disp_order=-1 |
| miienemyg | (no nam_chr1_00 label) | no | no | exclude; existing miienemy prefix rule | no selectable CSS entry; source row has can_select=false / disp_order=-1 |

## Checks and changes

`tools/stat-presets/build_presets.py` now reads `tools/stat-presets/list_exclude.txt` when it
generates a list. It continues to skip the `miienemy` prefix. The explicit set is:

* `koopag` — boss, not CSS-selectable.
* `miigunner` — row-zero Mii Gunner default, not a selectable preset row.

Generated `gamedata/mii_customizer/P14-LIST-PLAYABLE/list.txt` has 85 entries; the current
86-entry list differs by exactly the removal of `koopag nam_chr1_00_koopag`. The matching
`names.txt` has 86 preset rows plus its version line: compared with the current names file it
removes only `koopag`; the existing `miigunner Mii Gunner` default line was already present and
is retained.

The generator was run into a temporary directory under this task's gamedata folder. These
other generated outputs were byte-identical to P10, with SHA-256:

| Output | SHA-256 |
|---|---|
| `presets_wide.txt` | `8c763e77ce8d8f6e4155243da3209e63cad8ff071f0e5208c06708326ef92e85` |
| `fields_wide.json` | `e7a8de0e28ad1a31f5126fbf85f4840d32f69459afbc09b7a238fa081142724d` |
| `fighters.json` | `53f37ee31cf744d26b433c081d4dddefff5dc4edb2d1fc874ce316d023208a01` |
| `fighter_param_full.json` | `c46dcd3e344b45f7c11a2b7a250405be9c56873f78a65a3335cea274c14415c3` |

New list SHA-256: `ca69481706944f4ab49edc5bc633d6e6ece79d874d2cc2a0562a18ff422637c4`.
New names SHA-256: `6dd06f14f034c5a18978e464b9f0ff6f8808770d8ef3616fcc1293f2c59ab2f0`.

`check_list.py` reports 20 checks passing, including the plugin `list.rs` parser (85 accepted,
0 rejected), preset cross-references, exact diffs, and a negative control that reintroduces
`koopag`. The host Rust modules type-check from unchanged plugin sources. Running a newly linked
host harness was unavailable because this host has the MSVC Rust target but no `link.exe`; the
existing compiled parser confirmed `list.rs`, while the `names.rs` input was validated against
its source rules by the checker. The prebuilt combined session wrapper prints the successful
list parse (`accepted=85`, `rejected=0`) and then exits 1 because its fixture still expects the
old 86-entry list; the P14 checker checks the parser result line rather than that stale wrapper
assertion. The parser execution for this new `names.txt` remains unverified.

## Plugin behavior for an unlisted saved preset

Source inspection only (verified by reading the current plugin code): `ui::current_row(None,
list)` returns row 0. For a saved preset, it returns that preset's list position plus one when
present, because row 0 is reserved for the Mii default. If the saved preset is absent from the
list, it returns `NO_ROW`. `menu::start` handles `NO_ROW` on a Stats page by starting the cursor
at row 0 and setting the tick to `NO_ROW`; it does not select or tick the row-zero default.
Therefore a loadout may still name `koopag`, but opening Stats will place the cursor on the
default row without marking it as the saved choice. This is a source reading, not a runtime
test.

## Verification and changed files

## Commands and checks

Extraction:

```text
tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/mii_customizer/P14-LIST-PLAYABLE/files ui/param/database/ui_chara_db.prc
```

Generation and checks:

```text
python -B mods/mii_customizer/scratch/2026-10-07_P14-LIST-PLAYABLE/make_outputs.py
python -B mods/mii_customizer/evidence/P14-LIST-PLAYABLE/check_list.py
python -B mods/mii_customizer/tools/stat-presets/check_presets.py
```

Observed: extraction succeeded (1 file); `check_list.py` reported 20 passed, 0 failed;
`check_presets.py` reported 31 passed, 0 failed. The check compared SHA-256 for the four
non-list outputs above and verified the `koopag` negative control. No emulator, console,
SD-card action, install, or commit was performed.

Changed files: `research/P14-LIST-PLAYABLE.md`; `evidence/P14-LIST-PLAYABLE/check_list.py` and
`host_check.rs`; `scratch/2026-10-07_P14-LIST-PLAYABLE/make_outputs.py`, `write_table.py`,
`check-output.txt`, and the type-check artifact `p14_host_check.rmeta`; `tools/stat-presets/`
(`build_presets.py`, `list_exclude.txt`, `README.md`, `check_presets.py`); and workspace
`gamedata/mii_customizer/P14-LIST-PLAYABLE/` (`list.txt`, `names.txt`, extracted
`ui_chara_db.prc`).

## Task summary

P14-LIST-PLAYABLE — PARTIAL. The filter, generated data, source-based table, and offline
checks are complete. Exact execution of the new `names.txt` through `plugin/src/names.rs` could
not be linked because `link.exe` is unavailable; this is the remaining verification question.
