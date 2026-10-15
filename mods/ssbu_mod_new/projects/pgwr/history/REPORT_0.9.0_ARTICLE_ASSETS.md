# 0.9.0 — the `normal_weapon` article's assets are staged; its registration is blocked

Status: **assets built and verified offline. The plugin half is not built, and the
reason is a reserved resource, not effort.**

The card is still on 0.7.0. The plugin NRO is unchanged from 0.8.0/0.8.1
(byte-identical, `ed2988e1…`); only the asset tree and `config.json` moved.

---

## 1. What this release does

`build.py` now copies G&W's `normal_weapon` article — the stool, the manhole cover,
the fishbowl, the turtle and the spray — into eflame's own namespace, verbatim:

| new directory | files | source |
| --- | --- | --- |
| `fighter/eflame/model/normal_weapon/c06`, `c07` | 16 each | `export/fighter/gamewatch/model/normal_weapon/<slot>` |
| `fighter/eflame/motion/normal_weapon/c06`, `c07` | 12 each | `export/fighter/gamewatch/motion/normal_weapon/<slot>` |

All four directories are declared in `mod_output/.../config.json` under
`new-dir-infos`, and every file is listed under `new-dir-files` in the same
directory. That is the shape the working clone pack in `mod_files/mgw_standalone/`
uses for whole new fighter trees, and whose Watch Probe loaded and ran on hardware.

Verified offline: all four trees are byte-identical to the G&W export (`diff -r`),
`build.py` is byte-deterministic across runs (`build-record.json` identical), and
`build.py` refuses to write if any file list drifts from what is on disk in the
export or if a declaration and the written tree disagree.

**The article's clips were not touched.** Their own mesh-visibility tracks are what
select the prop (`c01attacks3s` → `chairM`, `c02attacklw3` → `ManholeM`,
`c05attackairn`/`c05landingairn` → the fishbowl, `c05attackairb`/`c05landingairb` →
the turtle, the jab and down-taunt clips → `KiriM1..15`). They are deliberately not
passed to `complete_visibility()`, which fills *missing* meshes with `False` and
exists for the opposite purpose.

### The file-addition risk is now closed

`HANDOFF_ARTICLE_SEARCH.md` §6 called `new-dir-infos` "untested" and recommended
probing it in isolation before building the article. It no longer needs probing:
`mod_files/mgw_standalone/` ships a `config.json` driving `new-dir-infos`,
`new-dir-infos-base` and `new-dir-files` for new fighter trees, and its G&W clone
loaded and ran. Same ARCropolis build, same game version, same console.

Nine of the article's ten clips are names `eflame` already has — they are G&W's
*body* versions of the same moves. Only `j01appeallw` (the down taunt) is a file
name no `eflame` folder has, and the down taunt is not what the first test asks
for. Every model file is a standard name. So this tree is "standard file names in
new directories", the shape that is proven, rather than the "new file name" shape
0.8.0's probe tests.

---

## 2. Why the article is not spawned: a reserved resource

The handoff's hand-back condition, met:

> If `clone_weapon` cannot be made costume-safe, or it needs a raw-offset hook or a
> rebuilt global smashline plugin — hand back.

`clone_weapon` needs both. The mechanism, read from source:

1. `smashline_clone_weapon` (`src/api.rs:304` in both the locked crate and the
   installed `smashline_1304`) writes into two statics, `NEW_AGENTS` and
   `NEW_ARTICLES`.
2. `NEW_ARTICLES[eflame]` is read by exactly one thing: the
   `#[skyline::hook(offset = 0x64b730)] fn get_static_fighter_data` in
   `src/cloning/weapons.rs`, which appends G&W's `normal_weapon` descriptor to
   eflame's article table so that `generate_article(125)` is valid at all.
3. The owner and name lookups are redirected by further raw-offset inline hooks
   (`0x33b6628` params, `0x33acf78` game animcmd, `0x33ac040` status script,
   `0x17e0a4c` / `0x17e098c` name→file, and the param tables at `0x33b6830` /
   `0x33b69f0` / `0x33b6d14`).

**A mod NRO cannot reach the installed plugin's statics.** Each Skyline plugin
statically links its own copy of smashline; there is no cross-NRO symbol
resolution. The reskin's `clone_weapon` call would write to *its own* `NEW_ARTICLES`,
which nothing reads, unless the reskin also installed the hook that reads it — and
that hook is a raw-offset hook into `main`, which the global plugin has already
installed at the same address. Installing it twice from two NROs is the conflict
`mgw_standalone` p9/p10 spent three releases on.

### And the linked crate's addresses are wrong for this game anyway

The reskin pins `smashline` to git rev `be3ef30`. Measured against
`mod_files/mgw_standalone/offset-audit.json`, whose `resource_support_edits` record
the upstream and corrected values side by side:

| site | locked rev `be3ef30` | corrected (installed `smashline_1304`) |
| --- | --- | --- |
| `LOWERCASE_FIGHTER_NAMES` | `0x4f81e20` | `0x4f80e20` |
| `LOWERCASE_WEAPON_NAMES` | `0x5186bd0` | `0x5185bd0` |
| `LOWERCASE_WEAPON_OWNER_NAMES` | `0x5189240` | `0x5188240` |

plus **11 hook offsets carrying a `+ 0x5B0` shift** the 13.0.4 dump does not have
(`src/cloning/weapons.rs:247-266`, and the same class of site in `fighters.rs`),
and the `- 0x40` path-hook displacements that
`mgw_standalone/tools/prepare_smashline_1304.py` documents as landing "inside
prologues, hash loops and epilogues" instead of immediately after the native name
load.

So calling the linked `clone_weapon` would read the fighter-name and weapon-name
tables 0x1000 off and `.unwrap()` on the result — a hard crash, and the `+0x5B0`
hooks would write to the wrong addresses besides.

The script-installation half of the locked crate is unaffected — it uses none of
these — which is why 0.7.0 and 0.8.1 work today. The defect is confined to
`cloning/`, which is exactly the part this feature needs.

### The two ways forward, both reserved

| route | why it is reserved |
| --- | --- |
| Vendor a corrected smashline and `[patch]` the reskin onto it | Fixes the 14 addresses, but the article still does not exist until `get_static_fighter_data` is hooked, and that hook is a raw-offset write into `main` from a mod NRO, colliding with the global plugin. **Also dead on its own terms:** the global plugin's `main` is what installs every hook, including the `create_agent` ones the reskin's own installed moves depend on, so removing it breaks the reskin. |
| Rebuild and install a corrected global `libsmashline_plugin.nro` | NO SHORTCUTS item 4 names this explicitly. **This is the route taken** - see below. |

The second was chosen by the user on 2026-09-29.

### What was done about it

**The user authorised the one-line change on 2026-09-29, on the grounds that they
are not updating the game: upstream smashline releases only support 13.0.5+, so
"it will be overwritten by an update" was never a real cost for this card.**

`mod_files/mgw_standalone/smashline_1304/src/pgwr_article.rs` registers the
article at boot, ahead of every `install_*` in the plugin's `main`:

```rust
crate::api::smashline_clone_weapon(
    StringFFI::from_str("gamewatch"),
    125,                          // normal_weapon
    StringFFI::from_str("eflame"),
    StringFFI::from_str("normal_weapon"),
    false,                        // use_original_code
);
```

Built: 315392 bytes,
`b906669d4754bbf04f3d419bbd06f83a7b3ff1e0e505d0ac76c1531b74af7230`. Verified by
byte-diff against the 26 Sep build: every pre-existing diagnostic string survives
(`[MGW-SL] p7`, `[MGW-SL] REFUSED offset=`, `Failed to append article table`,
`smashline has panicked`) and the only new content is the three constants and the
two `[PGWR-ART]` format strings.

Notes that matter for reading the next run:

* **Ordering.** The call runs before any `install_*` because `FIGHTER_DATA_CACHE`
  memoises each fighter's article table; anything that built a fighter first would
  cache a table without the article and the entry would be invisible for the rest
  of the session. No fighter exists at boot, and this runs ahead of the hooks, so
  the cache is necessarily empty.
* **It is per fighter kind, not per costume.** eflame gains the *ability* to spawn
  the article on all eight Pyra colours. Nothing does so except this reskin's c06 /
  c07 scripts, so vanilla Pyra c00–c05 are unaffected in practice.
* **It is inert for every other fighter.** `try_get_new_agent` only matches when
  the current owner kind is the recipient, and the owner kind is only set during
  that fighter's own initialisation (`0x6079d0`).
* **`use_original_code = false`** means `get_weapon_code_dependency` returns `None`
  (`create_agent.rs:1079`), so the agent is built by the generic
  `weapon_common_ctor` and gamewatch's `lua2cpp` module is never loaded. That is
  the NO SHORTCUTS requirement and it is why the flag is false.
* **Failure is logged, not fatal.** `smashline_clone_weapon` `unwrap()`s its name
  lookups, and a panic in the plugin's `main` happens before the panic hook is
  installed, so the registration checks both names first and prints
  `[PGWR-ART] REFUSED` instead.
* **New risk to watch:** `get_static_fighter_data` `panic!`s
  `"Failed to append article table"` if the donor's fighter data has no descriptor
  for weapon 125. G&W does (article registry, global 125), but that panic is the
  one way this can fail at fighter creation rather than at boot.

**Still true and still open:** the NRO's dynsym is **not** recoverable. All
1,417,216 bytes were scanned for an `Elf64_Sym` table at the correct 0x18 stride
and there was exactly one false positive (`0x10fc1a`, `st_value 0x100000`,
`st_size 0`), so the decompile route must go through Ghidra function discovery,
not symbol lookup. That matters for porting the article's statuses, which is the
next step and is not done.

---

## 3. The manhole, resolved

Recorded here because two handoffs left it open and it is now settled by
measurement, not inference.

G&W's down tilt `c02attacklw3` carries a 45-value visibility track for
`manhole1M` (True, frames 0–4) and `manhole2M` (True, frames 5–44), and the built
c06 copy is identical to the export. **The hole is a body mesh and is already
animated in the build on the card.** The cover, `ManholeM`, is absent from every
body clip in both the export and the build; it is article geometry on a dedicated
`Manhole` bone of the article's own skeleton. So the manhole is not a separate bug
and never was: its hole works by the same clip-name-collision that makes the
hammer work, and its cover is the same `normal_weapon` blocker as the stool,
fishbowl and turtle.

**Stale docstring, now a trap.** `complete_visibility`'s docstring in `build.py`
still says `RHammerM` is one of four meshes G&W's clips never track, hidden by
native visibility groups. That is measurably false: G&W's `f03downattacku`,
`f04downattackd` and `g03slipattack` each carry a 50-value `RHammerM` track that
turns it on. It is the same wrong theory that produced the retracted rule R22, and
since this function writes `False` into every mesh a clip omits, someone who
believes it would "fix" the manhole by editing the pass. Do not.

---

## 4. Console test

In `reports/console-2026-09-29-article/RESULT.md`. Three files to install now, not
two: the reskin NRO, the mod folder, **and the rebuilt
`libsmashline_plugin.nro`**.

The line to look for is new:

```
[MGW-SL] p7: verified resource globals, name tables and path hooks
[PGWR-ART] registered gamewatch article 125 (normal_weapon) on eflame as local article 0; use_original_code=false
```

`[PGWR-ART] REFUSED` instead means one of the two fighter names was not found and
nothing was registered. No prop appearing plus a successful `[PGWR-ART]` line means
the registration worked and the remaining gap is the article's *behaviour*, which
is the port still to do.
