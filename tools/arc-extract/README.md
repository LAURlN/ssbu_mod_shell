---
purpose: Extract individual files from the local SSBU data.arc by ARC path, so agents do not need ArcExplorer or the running console
usage: tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/ssbu-13.0.4/files [--index <paths.txt>] <arc path | folder/ | pattern*> ...
status: working
lang: rust
updated: 2026-10-02
source: user request 2026-10-02 (Claude)
---

A small command-line program on top of the open-source `smash-arc` library (crates.io, pinned
`=0.6.0`, MIT, https://github.com/jam1garner/smash-arc) with its pure-Rust zstd backend. It opens
the archive read-only, decompresses the requested files and writes them to `<out>/<arc path>`.

## Build (once, or after changing the source)

```
cd tools/arc-extract
cargo build --release
```

`rust-toolchain.toml` pins `stable-x86_64-pc-windows-gnu`: this machine has no MSVC linker, so the
default `msvc` toolchain cannot link (`linker link.exe not found`; from Git Bash the error is
`link: extra operand`, because coreutils' `link` is found instead). `target/` is about 100 MB.

## Use (from the workspace root)

```
X=tools/arc-extract/target/release/arc-extract.exe
A=gamedata/ssbu-13.0.4/data.arc
O=gamedata/ssbu-13.0.4/files

# exact paths - no index needed
$X --arc $A --out $O effect/fighter/eflame/ef_eflame.eff fighter/brave/param/vl.prc

# a folder (trailing /) or a * pattern - needs an index: a text file with one ARC path per line
$X --arc $A --out $O --index mods/ssbu_mod_new/dumps/decoded/arc_files.tsv \
   fighter/brave/param/ "fighter/snake/motion/body/c00/*attackhi3*"

# only show what a folder/pattern expands to
$X --arc $A --out $O --index mods/ssbu_mod_new/dumps/decoded/arc_files.tsv --list fighter/brave/
```

- Output: one line per file on stdout, `<bytes>\t<sha256>\t<arc path>`; problems on stderr as
  `MISSING\t<path>\t<reason>`. Exit 0 if everything was extracted, 1 if any file failed, 2 for bad
  arguments.
- `--region` (default `us_en`; e.g. `eu_de`, `jp_ja`) selects the copy of regional files.
- `stream:/...` paths are written under `stream;/...`, as ArcExplorer does.
- The ARC stores hashes, not names, so the tool cannot list a folder by itself. The mod repo's
  `dumps/decoded/arc_files.tsv` (590,711 paths) is the index; `grep` it to find a path.
- Extract into `gamedata/`, never into `dump/`, `kb/`, `tools/` or a mod's source tree. Pin what a
  mod task uses into that mod's `refs/` with the printed sha256.

## Observed run (2026-10-02, data.arc sha256 `ef615e671e1d...`, 17,600,869,448 B)

```
$ arc-extract --arc ... --out ... effect/fighter/eflame/ef_eflame.eff fighter/brave/param/vl.prc fighter/nope/x.bin
11371400  24512f9a020f3a1b989bebb614314381a142d769570618fd71a786356c6682e3  effect/fighter/eflame/ef_eflame.eff
18685     dafa43c632c8562e8f6835f6162a5a04ecb817eb5dec7b3ed75755c5d9dd4d76  fighter/brave/param/vl.prc
MISSING   fighter/nope/x.bin   the requested resource could not be found
2 extracted, 1 failed            (exit 1, 2.3 s)

$ arc-extract ... --index mods/ssbu_mod_new/dumps/decoded/arc_files.tsv fighter/brave/param/ "fighter/snake/motion/body/c00/*attackhi3*" ui/message/msg_name.msbt
2375    350c10f18d30...  fighter/brave/param/expression_vl.prc
18685   dafa43c632c8...  fighter/brave/param/vl.prc
45760   f5151e106cbf...  fighter/snake/motion/body/c00/c02attackhi3.nuanmb
490336  9efc357db8ea...  ui/message/msg_name.msbt
4 extracted, 0 failed
```

Controls: `ef_eflame.eff` is byte-identical to the copy in the user's ArcExplorer export, and
`c02attackhi3.nuanmb` has the sha256 pinned in the mod repo's
`refs/snake_attack_hi3/extraction.json` (pulled from the console over arc-network on 2026-10-01).

## Limits

- Only those files were compared against an independent source; other files are unverified.
- Base-game files only: nothing a mod adds exists in the archive.
- No search and no directory listing without an index file.
