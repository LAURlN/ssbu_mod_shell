# P5-MSG-PROBE - can a mod add its own menu text labels?

Worker report. Task: `P5-MSG-PROBE`. Status: **DONE** (Parts 1-3 complete, nothing installed).
Date: 2026-10-05. Tiers used: **C** pinned third-party source, **B** offline measurement,
**D** hypothesis. No runtime behaviour is claimed anywhere in this report.

## Summary

- **A mod can add new message labels through ARCropolis, not only replace existing ones.**
  Pinned source: `MsbtHandler::apply` first rewrites labels that exist in the base file, then
  appends every label that did not match through `MsbtBuilder::add_label`
  (`src/modfs/handlers/msbt.rs:158-174`, tag v4.1.1). Label addition arrived in **v3.1.0**;
  message patching exists since **v3.0.0-beta.3.2**.
- The file goes at `<mod folder>/ui/message/msg_menu.xmsbt`. The path is turned into the base
  ARC path by replacing the extension with `msbt` and hashing the result
  (`msbt.rs:117-125`). The root XML element name is free; entries are `<entry label="...">`
  with the text as the character data of a `<text>` child. Text is written as UTF-16LE with a
  terminating `0x0000` (`msbt.rs:193-202`).
- **The card's ARCropolis version is not established, and the kb note is probably wrong for this
  card.** v4.1.1 refuses to install any hook unless the game is 13.0.5 (`src/lib.rs:516-522`),
  yet gate 1 (tier A) proved this 13.0.4 card loads mod files. v4.0.9/v4.0.10/v4.1.0/v4.1.1 all
  gate on 13.0.5; v4.0.7 and v4.0.8 gate on 13.0.4. D: the card runs v4.0.7 or v4.0.8. The kb
  note `kb/reference/ssbu-modding-stack.md` names v4.1.1 - I did not edit it (not my path).
- Locally (B): `ui/message/msg_menu.msbt` is 268096 bytes, sha256 `4b4f3d236400...` (matches the
  coordinator's copy), holds **3353** labels in 101 groups, and has **no** `mnu_mc_` label.
  `mnu_mmiif_setup_sp_move_title` = "Select Special Moves" and `..._width` = "Side Special"
  in `us_en`. The archive carries **one** path with per-region copies behind it; four were
  extracted and measured.
- Staged (not installed, not READY): `builds/0.2.1-msg-probe/mii_customizer_probe_msg/` adds one
  new label `mnu_mc_probe_title` = "MC probe 0.2.1" and asks the editor sub-title for it with a
  **different-length** Lua chunk (7788 bytes, was 7799). Its check script passes with 8/8
  negative controls caught.

---

## Part 1 - source facts (C)

### Pinned sources

| pin | what it is | commit |
|---|---|---|
| ARCropolis tag **v4.1.1** (2026-09-25) | primary reading | `fafcfea323f246b4b9eb2a557e5e921684e208fa` |
| ARCropolis tag **v4.0.8** (2026-04-14) | the 13.0.4-gated release; same feature, older layout | `d88dcd18004c05157eb1e53f459eeb3ae503c054` |
| commits `8f4afc52d8712f79040d3c7affb6afbc3d387db1` (2022-02-01), `250a9e30db6a1c307c18045336579f48c5b7cf87` (2022-03-14) | first message-patch support, first label addition | as listed |
| `serde-xml-rs` 0.6.0 (crate used by ARCropolis: `Cargo.toml:51`) | XML deserializer semantics | crates.io 0.6.0 tarball |
| `RoccoDev/msbt-rs` (the `msbt` dependency, `Cargo.toml:51`) | MSBT container layout cross-check | `9837597fe8e8349b6b079a0d17b9ac224df3984d` |

Cloned read-only into `scratch/2026-10-05_P5-MSG-PROBE/` (`arcropolis-src`, `msbt-rs`,
`serde-xml-rs-0.6.0`). No binaries were downloaded. Line numbers below are from those checkouts;
where a v4.0.8 path is cited it is named.

### a) Is there a message patch file, where, and what shape?

Yes.

| fact | where |
|---|---|
| handler advertises the extension | `src/modfs/handlers/msbt.rs:113-115` `extensions() -> &["xmsbt"]` |
| a mod file ending `xmsbt` is *collected* as a patch, not replaced into the arc | `src/fs/discover.rs:45-64` (`should_collect`), `src/fs.rs:409-421` (`is_handler_consumed`) |
| base path = mod-local path with the extension changed to `msbt`, then hashed | `msbt.rs:117-125` + `src/modfs/handlers/mod.rs:30-38` |
| mod roots | `sd:/ultimate/mods` (`src/utils.rs:61-62`), plus one extra root `sd:/ultimate/arcropolis/resources` (`src/utils.rs:71-72`) |
| same feature in v4.0.8 | `src/fs/loaders.rs:175-273`, path/hash rule `src/fs/utils.rs:151-181` |

So for this project the file is

```
ultimate/mods/<mod folder>/ui/message/msg_menu.xmsbt
```

The hash that decides which base file is patched is the hash of the *string*
`ui/message/msg_menu.msbt`; nothing else about the name matters except the region suffix (c).

**Shape.** The parser's data model (`msbt.rs:18-36`):

```rust
struct Xmsbt { #[serde(rename = "entry")] entries: Vec<Entry> }
struct Entry { label: String, base64: Option<bool>, #[serde(rename = "text")] text: Text }
struct Text  { #[serde(rename = "$value")] value: String }
```

- child element `entry` -> one label;
- attribute `label` -> the label name;
- attribute `base64` -> optional; when true the text is standard base64 and the decoded bytes
  are used raw (`msbt.rs:83-95`);
- child element `text` -> its character data is the string;
- the **root element name is ignored**: `serde_xml_rs::Deserializer::deserialize_struct`
  consumes the first `StartElement` and maps its children
  (`serde-xml-rs-0.6.0/src/de/mod.rs:256-272`), so `<xmsbt>`, `<messages>` and anything else all
  work. Comments, whitespace and processing instructions inside the root are skipped
  (`serde-xml-rs-0.6.0/src/de/buffer.rs:163-165`).

**Encoding of the text.** `to_text_data` (`msbt.rs:193-202`) encodes the Rust `String` as UTF-16
in host order (little endian on the Switch) and appends one `0x0000`. The `base64="true"` route
appends two zero bytes instead (`msbt.rs:84-88`). Practical consequence (D, from the code): a
string that needs the game's own escape units cannot be written literally, because units such as
`0x0004` are not legal XML 1.0 characters; the base64 route exists for those.

**A shipped example exists in the pinned tree**, which is why I trust the shape:
`resources/arcadia/ui/message/msg_menu.xmsbt` (4312 bytes) at tag v4.1.1, described in
`crates/arcadia/README.md:110-116`, with entries like
`<entry label="mnu_arcadia_hdr_mode"><text>ARCropolis</text></entry>`. Its header comment states
two things this probe follows: no region suffix on purpose (the arc holds one
`ui/message/msg_menu.msbt`), and every entry on one line because a newline inside `<text>` lands
in the text.

### b) Add or replace? Duplicates across mods?

**Both.** `MsbtHandler::apply` (`msbt.rs:143-182`):

1. all patches for the hash are flattened into one `HashMap<String, TextType>` in file order
  (`msbt.rs:148-153`);
2. every base label that is a key of that map gets `set_value_raw` (`msbt.rs:158-168`);
3. whatever is left in the map - labels that did **not** exist in the base file - goes through
   `MsbtBuilder::add_label` (`msbt.rs:170-174`).

Duplicate labels across mods: last writer wins, silently. The map is filled in discovery order;
mod roots are walked after `active_roots.sort()` (`src/fs/discover.rs:215`), so with two mods
shipping the same label the alphabetically later mod folder wins. There is **no warning**: the
`conflicts.json` dialog only covers ordinary staged files (`discover.rs:245-256`), while patch
files are collected separately (`discover.rs:257-266`). Two mods shipping different labels in
`msg_menu.xmsbt` merge cleanly; two shipping the same label do not merge, the later one replaces
it.

History of this behaviour (both commits verified with `git tag --contains`):

| tag | commit | change |
|---|---|---|
| v3.0.0-beta.3.2 (2022-03-01) | `8f4afc5` "add working, crashing xmsbt edit support" | xmsbt support, **override only** (the diff iterates base labels and has the add path commented out) |
| v3.1.0 | `250a9e3` "Label addition would work better with the actual code, however" | leftovers go through `MsbtBuilder::add_label` - label **addition** |

### c) Region / language handling

Yes, in the file name (`msbt.rs:119-123`, `handlers/mod.rs:14-28`, `discover.rs:24-41, 45-64`):

- `strip_regional` takes everything from a `+` up to five characters after it as the region id
  and removes them: `msg_menu+jp_ja.xmsbt` -> base `ui/message/msg_menu.msbt`, region `jp_ja`.
  A name with fewer than five characters after `+` is left alone.
- a patch whose region does not equal the console's region is neither collected nor used
  (`should_collect`/`should_ignore`).
- **no suffix means "use me in every region"** (`is_current_region = true` when there is no
  suffix).
- the 14 accepted ids are listed in `src/lib.rs:201-203`: `jp_ja us_en us_fr us_es eu_en eu_fr
  eu_es eu_de eu_nl eu_it eu_ru kr_ko zh_cn zh_tw`.

The patched base is whichever regional copy the console loads (`config::region()`), so one
unsuffixed patch applies to all of them; Part 2 shows those copies really are different files.

### d) Since which version, and enabled by default?

- Since **v3.0.0-beta.3.2** for patching existing labels, **v3.1.0** for adding new ones (table
  above). I checked the tags `v2.1.1` and earlier: `git grep xmsbt` finds nothing; the first tag
  with it is v3.0.0-beta.3.2.
- **Enabled by default.** The handler is registered unconditionally in `register_builtins`
  (`handlers/mod.rs:40-47`), `patches_load()` returns `true` (`msbt.rs:109-111`), the `xmsbt`
  extension is in the unconditional patch-extension list (`discover.rs:47-48`), and no config
  flag in the tree gates it. The only environment variable nearby,
  `ARCROP_PATCH_CACHE` (`src/modfs/patched.rs:24`), only controls a disk cache of already-merged
  files, not whether patching happens (`src/modfs/patched.rs:21`).

### Card version: not established, and the kb note looks wrong

Matching the card's `libarcropolis.nro` (2347008 bytes, sha256 `49b6f634039f...`) to a release
would require the release binaries, which this task may not download. **The card's version is
not established.**

What the source does establish (C): every ARCropolis release gates on the game version and
returns before installing any hook if it does not match.

| tag | required game version (`src/lib.rs`) |
|---|---|
| v4.0.6 | 13.0.3 |
| v4.0.7, v4.0.8 | **13.0.4** |
| v4.0.9, v4.0.10, v4.1.0, **v4.1.1** | 13.0.5 |

The user's game and dump are 13.0.4, and gate 1 (tier A,
`evidence/2026-10-04_gate1/RESULT_test2.md`) showed this card loading a changed `.lc` and a
changed `layout.arc` from a mod folder. Therefore the card is **not** running v4.0.9 or newer
(D): those builds show an error and hook nothing. The most likely candidates are **v4.0.7 or
v4.0.8**. The kb note `kb/reference/ssbu-modding-stack.md` names v4.1.1 "as the release checked
on 2026-09-25", which does not fit a 13.0.4 card that is demonstrably loading files; the
coordinator owns that note, so I only report it.

Because the card's version is unknown, I read the message handler at both plausible pins. The
feature is the same in v4.0.8 (`src/fs/loaders.rs:175-273`): same XML model, same
override-then-add order, same `+<region>` rule (`src/fs/utils.rs:151-181`).

**One open risk that only a console run can settle (D).** The merged file is *larger* than the
base. v4.1.1 answers a size query for a patched msbt with `base_size * 2`
(`msbt.rs:184-186`), which leaves room. In v4.0.8 the loader's own size hook returns `None` for
this patch type (`src/fs/loaders.rs:110-121`) and the FUSE layer asks the filesystem for it
(`src/fuse/mods.rs:21-30`). If the game sizes its buffer from the vanilla 268096 bytes and the
merge adds ~50 bytes, the appended label could fall outside the buffer. This is exactly the case
the staged probe exercises.

### Coordinator addendum (2026-10-05, after boot 1)

The card's version is narrowed (B): ASCII strings in the card's `libarcropolis.nro`
(`49b6f634...`) contain `arcropolis::fs::loaders`, the pre-refactor `XMSBT ... the following
syntax error` wording and `orbits-...` check-out paths; the v4.1.x markers (`modfs`, `patched
cache`) are absent. The card runs the old 4.0.x generation - consistent with the 13.0.4 gate
(v4.0.7/v4.0.8) and with the D-inference above; the earlier kb note naming v4.1.1 was wrong and
is corrected in place. Boot 1 result (tier A, `evidence/2026-10-05_session1/RESULT.md`): the
probe chunk loaded (sub-title showed the raw key `mnu_mc_probe_title`) but the new label did not
resolve; every other screen/frame was normal. No ARCropolis log file exists on the card after
that boot (`logging_level` was `Warn`, `ultimate/arcropolis/logs/` empty), so causes 1/3/4 of
the raw-key ladder are still not separated. Boot 2 will raise `logging_level` to `Debug`.

### Does the older mod already use this? (`mods/ssbu_mod_new`, read after its AGENTS.md)

Read `AGENTS.md`, `projects/pgwr/STATUS.md` and `handbook/00_INDEX.md` first, then searched
(`grep -rn --exclude-dir=.git --exclude-dir=target --exclude-dir=dumps -i xmsbt` over
`handbook projects src tools kb references refs state archive` plus the root docs).

- **The handbook never mentions msbt or message patches at all** (`grep -rn -i "msbt\|message
  patch" handbook/` returns nothing). Its index has a page for ARCropolis `config.json`
  (`10_arcropolis_config_json.md`) and one for params (`.prcx`/`.prcxml`) but none for messages.
  This is the canonical gap the task asked about. A second, broader search for `msbt` (not just
  `xmsbt`) over `handbook projects/pgwr/STATUS.md src/pgwr src/mgw_standalone/tools
  CURRENT_INSTALL.md` returned **no** additional text hit - every mention in that tree is an
  `.xmsbt` file.
- **The old mod's shipped tree does use it, for a different file**:
  `mods/ssbu_mod_new/src/pgwr/ui/message/msg_name.xmsbt`, 3323 bytes, 123 lines, root `<xmsbt>`,
  `<entry label="nam_chr0_06_eflame_first"><text>Ursula</text></entry>` and 39 more, generated by
  `src/pgwr/tools/build_custom_names.py` (per `projects/pgwr/STATUS.md:658,748`, staged in
  `builds/pgwr/staged_names/`, "not installed on card"). Those are **overrides** of labels that
  already exist in `msg_name.msbt`; nothing in that tree shows a new label being added.
  A second generator lives at `src/mgw_standalone/tools/package_probe.py:118-123`.
- One negative observation worth carrying: `projects/mgw_standalone/history/DIAGNOSIS.md:118`
  records a paste where "`msg_name.xmsbt` missing/invalid during file discovery", and
  `src/mgw_standalone/p5-validation.json:42` keeps it as an open packaging observation. A patch
  that the collector does not pick up is a failure mode that exists in the wild.

---

## Part 2 - local facts (B)

### Inputs

```
tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc \
    --out gamedata/mii_customizer/P5-MSG-PROBE ui/message/msg_menu.msbt
268096  4b4f3d23640032858334ab0b51939f3675271cad326131bcb5c70c1a4f25b26b  ui/message/msg_menu.msbt
1 extracted, 0 failed (exit 0)
```

268096 bytes, sha256 `4b4f3d23640032858334ab0b51939f3675271cad326131bcb5c70c1a4f25b26b` -
**identical to the coordinator's recorded copy** (4b4f3d236400, 268096). Transcript:
`evidence/P5-MSG-PROBE/extraction_and_regions.txt`.

### Reader

`evidence/P5-MSG-PROBE/read_msbt.py` (32-byte file header, 16-byte section headers, LBL1 group
table + inline label names, TXT2 offset table). Layout taken from the pinned `msbt-rs` sources
and then confirmed against this file. Self-checks that all held on this input:

- header file-size field 268096 equals the file length;
- 3 sections declared and found: `LBL1 ATR1 TXT2`;
- the 101 groups' label counts sum to exactly the number of names read (3353);
- every label's TXT2 index is in range, and every TXT2 slice stays inside the section;
- the section walk ends at byte 268086 and the remaining 10 bytes of the file are all `0xAB`
  padding, i.e. no unexplained bytes.

### Results for `ui/message/msg_menu.msbt` (us_en)

- **3353 labels** in **101 groups**, 3353 TXT2 strings, 11 labels whose text contains units that
  are not valid UTF-16 (the escape codes below).
- Both labels the task names exist:
  - `mnu_mmiif_setup_sp_move_title` = `Select Special Moves`
  - `mnu_mmiif_setup_sp_move_width` = `Side Special`
  (trailing `0x0000` omitted here; the reader prints it.)
- **No label starting with `mnu_mc_` exists** - `read_msbt.py <file> mnu_mc_` prints
  `matched 0 label(s)`. Full list of the 114 `mnu_mmiif_*` labels with texts:
  `evidence/P5-MSG-PROBE/msbt_mmiif_labels.txt`.
- Distinct raw non-ASCII unit sequences inside those 114 texts (13; bytes as stored, **not
  interpreted**):

  | units | bytes | labels | e.g. |
  |---|---|---|---|
  | `000e 0001 0000 0004 0000 cd00` | `0e 00 01 00 00 00 04 00 00 00 00 cd` | 9 | `mnu_mmiif_setup_sp_move_up_n` |
  | `000e 0001 0001 0002 cd00` | `0e 00 01 00 01 00 02 00 00 cd` | 5 | `mnu_mmiif_created_fighter_nam` |
  | `000e 0001 0002 0002 cd00` | `0e 00 01 00 02 00 02 00 00 cd` | 14 | `mnu_mmiif_sp_move_01` |
  | `000e 0001 0002 0002 cd01` | `0e 00 01 00 02 00 02 00 01 cd` | 8 | `mnu_mmiif_setup_sp_move_up_n` |
  | `000e 0001 0005 0002 0006` | `0e 00 01 00 05 00 02 00 06 00` | 1 | `mnu_mmiif_setup_voice_check_guide` |
  | `000e 0001 0005 0002 0008` | `0e 00 01 00 05 00 02 00 08 00` | 3 | `mnu_mmiif_sel_guide_create` |
  | `000e 0001 0005 0002 0009` | `0e 00 01 00 05 00 02 00 09 00` | 1 | `mnu_mmiif_sort_guide` |
  | `000e 0001 0005 0002 000c` | `0e 00 01 00 05 00 02 00 0c 00` | 2 | `mnu_mmiif_favorite_guide` |
  | `000e 0001 0005 0002 0013` | `0e 00 01 00 05 00 02 00 13 00` | 1 | `mnu_mmiif_setup_joycon_l` |
  | `000e 0001 0005 0002 0014` | `0e 00 01 00 05 00 02 00 14 00` | 1 | `mnu_mmiif_setup_stick_r` |
  | `e017` | `17 e0` | 1 | `mnu_mmiif_favorite_icon` |
  | `e12c` | `2c e1` | 1 | `mnu_mmiif_setup_btn_try_icon` |
  | `e08e` | `8e e0` | 1 | `mnu_mmiif_setup_btn_random_icom` |

  Every one of the 114 texts ends in a single `0x0000` terminator, which the reader drops from
  the run.

### Per-language variants

The archive index `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv` holds exactly **one** entry,
line 133 `ui/message/msg_menu.msbt` - the index is region-agnostic. The variants live behind the
region flag, so I extracted the same path four times:

| region | bytes | sha256 | labels | `mnu_mmiif_setup_sp_move_title` |
|---|---|---|---|---|
| us_en | 268096 | `4b4f3d2364003285...` | 3353 | Select Special Moves |
| eu_de | 279344 | `b2769d291669d62a...` | 3353 | Spezialtechniken |
| jp_ja | 270608 | `0ab366ea89aff02f...` | 3353 | 必殺ワザ選択 |
| zh_tw | 188400 | `0a05b56a5fbadda3...` | 3353 | 選擇必殺技 |

Limit: I read **4 of the 14** region ids. The other 10 copies are unverified here.

---

## Part 3 - the staged probe (B, not installed, not READY)

`builds/0.2.1-msg-probe/` - three files plus the checker.

| file | bytes | sha256 | role |
|---|---|---|---|
| `mii_customizer_probe_msg/info.toml` | 510 | `e50d337acd5ec166...` | mod folder metadata |
| `mii_customizer_probe_msg/ui/message/msg_menu.xmsbt` | 1068 | `9726ae8271b0f39...` | the message patch |
| `mii_customizer_probe_msg/ui/script/menu/chara_make/make_mii_special_actor.lc` | 7788 | `2ff0182ca70228a5...` | the chunk |

Originals recorded in `MANIFEST.json`: the chunk's original
`gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc`, 7799 bytes,
sha256 `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d` (unchanged since the
coordinator verified it on 2026-10-04); the patch's base
`gamedata/mii_customizer/P5-MSG-PROBE/ui/message/msg_menu.msbt`, 268096 bytes,
`4b4f3d23640032858334ab0b51939f3675271cad326131bcb5c70c1a4f25b26b`.

### The message patch

```xml
<xmsbt>
  <entry label="mnu_mc_probe_title"><text>MC probe 0.2.1</text></entry>
</xmsbt>
```

One entry, 18-character label, **no region suffix** (so it applies in every region), no newline
inside `<text>`, no `base64`. `mnu_mc_probe_title` is absent from the base `us_en` file, so this
is a label *addition*, not an override.

### The chunk (different length)

```
python mods/mii_customizer/tools/lua53-inspect/lua53_inspect.py setconst \
  gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc \
  builds/0.2.1-msg-probe/mii_customizer_probe_msg/ui/script/menu/chara_make/make_mii_special_actor.lc \
  main.p14 2 "mnu_mc_probe_title" --allow-used
```

- `--allow-used` was required: the tool names the one consumer,
  `LOADK [2] R[1] := K[2]` at `0x16e0`.
- **size before 7799, after 7788** (the key is 18 characters instead of 29, so 11 bytes shorter -
  a genuinely different-length chunk, which gate 1 never tested).
- `verify`: 11 PASS checks, exit 0, full consumption at `0x1e6c`.
- `compare`: **exactly 1 structural difference** -
  `main.p14.K[2]: value='mnu_mmiif_setup_sp_move_title' != value='mnu_mc_probe_title'`.
- `roundtrip`: byte-identical (same sha256 in and out), reparsed structural diff none.
- An independent replay of the same command produced a byte-identical file.

Transcript: `evidence/P5-MSG-PROBE/lua_probe.txt`.

### The checker

`builds/0.2.1-msg-probe/check_probe_msg.py` (new file; `builds/0.1.0-arc-probes/check_probes.py`
was read and left untouched). It re-derives `MANIFEST.json` from disk and compares, then checks
the payloads: `tomllib` on `info.toml`; XML well-formedness and the exact entry/label/text shape;
exactly one entry; the label is `mnu_mc_probe_title` with text `MC probe 0.2.1`; the label does
**not** exist in the base msbt (otherwise it would not test addition); the patch file name is
`msg_menu.xmsbt` with no region suffix; the chunk differs in length, contains the new key, not
the old one, and passes `verify`/`compare`/`roundtrip` through `lua53_inspect.py`.

Run: `python mods/mii_customizer/builds/0.2.1-msg-probe/check_probe_msg.py` -> exit 0,
**3 files checked, 0 manifest problems, 0 payload problems, 8/8 negative controls caught**
(`evidence/P5-MSG-PROBE/check_probe_msg_output.txt`). Controls, each caught by the payload layer
except the last:

| control | caught by |
|---|---|
| flipped byte in the chunk | payload: `lua53_inspect verify` parse error |
| two entries in the patch | payload: `2 entry elements, expected 1` |
| patch defines an existing vanilla label | payload: wrong label + "already exists in the base" |
| patch text changed | payload: text mismatch |
| patch renamed `msg_menu+jp_ja.xmsbt` | payload: missing at the expected path |
| chunk replaced by the unchanged original | payload: same length, key missing |
| `info.toml` left unterminated | payload: `tomllib` `Illegal character '\n'` |
| stray extra file in the probe folder | manifest: unexpected extra file (no payload rule covers this) |

### `info.toml`

Parses with Python 3.12 `tomllib`: keys `display_name`, `version` (`"0.2.1"`), `description`.
The description states the label, the chunk, that it is not installed and that it replaces the
earlier probe.

### This folder replaces the earlier Lua probe

`builds/0.1.0-arc-probes/mii_customizer_probe_lua/` ships the same ARC path
(`ui/script/menu/chara_make/make_mii_special_actor.lc`) as an **ordinary staged file**, and two
mods shipping one ordinary path hit the `conflicts.json` branch (`discover.rs:245-256`). So the
new folder must be installed **instead of** the old Lua probe, not beside it. The old layout
probe is a different path and is unaffected. `MANIFEST.json` says this in its `replaces` field.

### What a console session could conclude

| observation on the Mii special-move screen | what it settles |
|---|---|
| sub-title reads **"MC probe 0.2.1"** | a brand-new label resolves **and** a chunk whose length differs from the original loads |
| sub-title shows the raw key (`mnu_mc_probe_title`) or is empty | the chunk loaded (its old key is gone) but the label did not resolve |
| sub-title still reads "Select Special Moves" | the chunk did not load |

**What the probe cannot tell apart.**

- *New label visible* does not separate "the merge appended a label" from "the merged file was
  read whole": a truncated merge that still exposed the new label, or a region variant that
  already contained the label, would look the same. I checked 4 of 14 regional copies, not all.
- *Raw key / empty title* collapses four different causes: the patch file was not collected or
  failed to parse (ARCropolis warns in its log), the label was added but the game's lookup did
  not find it, the merge corrupted a neighbouring string, or the merged file was cut at the
  vanilla size and the appended label fell outside the buffer. The log line from boot is what
  separates them, not the screen.
- *Unchanged title* collapses "chunk rejected", "mod folder inactive", "preset disabled" and
  "ARCropolis not running on this card at all".
- A crash, hang or the ARCropolis error dialog is a fourth outcome not on this ladder, and is a
  real possibility given the version uncertainty above.
- Nothing here measures whether a merged file is *correct*, only whether one label became
  visible.

---

## Limits and unresolved questions

1. **The card's ARCropolis version is not established** (no binaries downloaded). v4.0.7/v4.0.8 is
   a D-tier inference from the version gate plus gate 1's tier-A result. The kb note naming
   v4.1.1 conflicts with that inference and should be corrected by whoever owns `kb/`.
2. **Whether a size query for a merged msbt is generous enough on the card's build is unresolved
   offline** (v4.1.1 says `base*2`; v4.0.8's loader declines to answer). The probe is built to
   hit this, but a negative result would not identify the cause without the log.
3. Ten of the fourteen regional copies of `msg_menu.msbt` were not read.
4. No runtime behaviour of the game is claimed. Everything above is C (pinned source) or B
   (bytes on disk).
5. Out of scope and not started: choosing real label names and texts for the mod's stat/option
   names, the base64 route for texts that need the game's escape units, and any hook into the
   message system beyond the ARCropolis file route.

## Next experiment

1. Install **only** `builds/0.2.1-msg-probe/mii_customizer_probe_msg/` (not the 0.1.0 Lua probe
   - see the conflict note), with a **vanilla control boot first** (no probe, same session).
2. Boot once and keep the whole log from boot. The ARCropolis log should show whether the
   `xmsbt` file was collected; any `XMSBT file ... skipping` warning is a decisive negative.
3. Open the Mii special-move screen and record the sub-title verbatim, plus whether the screen
   still works.
4. Decide by the table above. If the raw key or an empty title appears, read the log first: a
   parse warning points at the XML, silence points at the merge or the size query.
5. Only after that, stage the follow-ups that this probe cannot separate: an **override-only**
   variant (`mnu_mmiif_setup_sp_move_title` -> a mod-owned text, no new label) and a
   **region-suffixed** variant (`msg_menu+jp_ja.xmsbt`) to test per-region behaviour.

---

## Summary for the coordinator

**Task:** P5-MSG-PROBE. **Status: DONE** (Parts 1-3 complete; nothing installed; not READY).

Changed/added files (all inside `mods/mii_customizer/` unless noted):

- `research/P5-MSG-PROBE.md` (this report)
- `builds/0.2.1-msg-probe/MANIFEST.json`, `check_probe_msg.py`, `README.md` (install steps, the
  outcome ladder and the probe's limits, for whoever runs the console session),
  `mii_customizer_probe_msg/info.toml`,
  `mii_customizer_probe_msg/ui/message/msg_menu.xmsbt`,
  `mii_customizer_probe_msg/ui/script/menu/chara_make/make_mii_special_actor.lc`
- `evidence/P5-MSG-PROBE/read_msbt.py`, `msbt_mmiif_labels.txt`, `extraction_and_regions.txt`,
  `lua_probe.txt`, `check_probe_msg_output.txt`
- `scratch/2026-10-05_P5-MSG-PROBE/` (ARCropolis v4.1.1 clone + history, v4.0.8 files,
  `msbt-rs`, `serde-xml-rs-0.6.0`)
- workspace-relative `gamedata/mii_customizer/P5-MSG-PROBE/` (`ui/message/msg_menu.msbt` plus
  `region-{us_en,eu_de,jp_ja,zh_tw}/` copies)

Checks run, all exit 0: `check_probe_msg.py` (8/8 controls caught);
`lua53_inspect.py verify/compare/roundtrip` on the staged chunk; `arc-extract` five times;
`read_msbt.py` on five files. Nothing else was run: no emulator, no console, no SD, no git
commit, no other worker's files touched.

Coordinator decisions I did not make: whether to correct `kb/reference/ssbu-modding-stack.md`
(v4.1.1 vs the 13.0.4 gate), whether the next console session installs this probe, and whether
`STATUS.md`/`CURRENT_INSTALL.md` record the new package.