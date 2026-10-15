# dumps/ - read-only game data (Smash Ultimate 13.0.4)

Never edit. Need something that is not here? Add it to `dumps/MISSING.md` (exact ARC path + why) and ask the user; never approximate.

## arc/ - ArcExplorer / arc-network export (25,404 files, 4.25 GB), mirrors ARC paths
Copied 1:1 from `modpack_test_1/export` (robocopy, 0 failures). It is **partial by design**.

| Path | Content |
| --- | --- |
| `fighter/<id>/{model,motion,param,...}` | 98 fighters: bayonetta brave buddy captain chrom cloud common daisy dedede demon diddy dolly donkey duckhunt edge eflame element elight falco fox gamewatch ganon gaogaen gekkouga ike inkling jack kamui ken kirby koopa koopag koopajr krool link littlemac lucario lucas lucina luigi mario mariod marth master metaknight mewtwo miienemy{f,g,s} miifighter miigunner miiswordsman murabito nana ness packun pacman palutena peach pfushigisou pichu pickel pikachu pikmin pit pitb plizardon popo ptrainer ptrainer_low purin pzenigame reflet richter ridley robot rockman rosetta roy ryu samus samusd sheik shizue shulk simon snake sonic szerosuit tantan toonlink trail wario wiifit wolf yoshi younglink zelda |
| `prebuilt/nro/release/` | `lua2cpp_<fighter>.nro` (98) - status/ACMD native code (Ghidra input); `prebuilt/movie`, `prebuilt/ui/font` |
| `effect/`, `sound/`, `ui/`, `camera/`, `common/`, `finalsmash/`, `item/`, `standard/` | effects (.eff/trail), sound banks (`nus3audio`/`tonelabel`), portraits (bntx), etc. |

Fighters that matter for current work: `gamewatch` `eflame` `elight` `element` `diddy` `kamui` `luigi` `shulk` `miiswordsman` `snake` `younglink` `chrom`, plus `common` and `mario` (template file for ARCropolis add).
Region 2 (US English) only. Live dumping: `handbook/03_dumps.md`.

## exefs/13.0.4/
`main` (NSO0, 42,910,639 B, sha256 `77936fe2…d92e`, build id `3eae0063…`), `main.npdm`, `rtld`, `sdk`, `subsdk0`, and **`main.bin`**
(decompressed flat image, 86,672,752 B, sha256 `f70c97d2…7613`; VA == file offset for `.text`; `.bss` absent). All disassembly / xref tools read `main.bin`.

## scripts/
- `SSBU-Dumped-Scripts-main/` - WuBoytH ACMD text dumps (77,532 files). `smashline/lua2cpp_<fighter>/<fighter>/<Script>.txt`. Conversion errors exist. G&W has **no status functions** here.
- `ParamLabels.csv` - hash -> param name. `gamewatch_motion_list.yml` - motion-list dump.
- Not present (were only GitHub tree listings): status-script repo, motion-list repo.

## decoded/ - derived from the above
`main_symbols.json` (dynamic symbols; not address-ordered), `transformation_symbols.json`, `nro_inventory.json`, `main_inventory.json`, `initial_disassembly.txt`,
`native-swap-trace.txt`, `ASSESSMENT.md` (Gemini-era feasibility, historical), `sources.json`, `ghidra_scripts__*.c` (Mythra `SpecialLw*`, Element changer),
`ghidra_scripts/`, `main-functions/*.asm.txt` (22 character-specific imports), `pmclone_*` (class/native inventories, ACMD inventory), `acmd_snapshot_pmclone/` (924 vanilla ACMD references),
`arc_files.tsv` (vanilla ARC file index, from clone_pack_workbench).
Regenerate with `tools/inspect_main.py` (needs `toolchains/python_tools`) and `src/pgwr/tools/{article_table,nro_syms,visibility_table}.py`.

## Not included (still in modpack_test_1 only)
`pyra_mythra_clone/editable` (regenerable copies), duplicate ExeFS images, `mgw_standalone/staging` and `downloads`, `scratch/ghidra` (Ghidra install).
