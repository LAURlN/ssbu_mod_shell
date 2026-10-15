# P3-DIAG-PLUGIN - log-only diagnostic plugin 0.1.0 for the first console gate

Task: `prompts/P3-DIAG-PLUGIN.md`. Date 2026-10-04. Worker: Claude Opus 5.5.
Status: **DONE** (the optional `0.1.0-override` variant was not built; its condition is not met, 1.6).

Nothing here is runtime evidence. The plugin has never been loaded by Skyline, never run on a
console or emulator, and is installed nowhere. **B** = measured offline in this task,
**C** = read from pinned source, **D** = hypothesis. Not READY; packaging and the test plan
are the coordinator's.

Paths are relative to `mods/mii_customizer/` unless marked workspace-relative.

## Result in short

- `builds/0.1.0-diag/libmii_customizer.nro`, sha256
  `ae49c1c84da39cf454f41811c75ed5e22cde21cfd63a9b530b592b15ee8c96af`, 45056 bytes, with
  `MANIFEST.json`. Two consecutive recompiles give the same hash.
- Three replace hooks (`0x179e440`, `0x17c8210`, `0x4e53e0`), each installed only if the four
  instruction words at the site equal the audited ones. Each calls the original with the
  caller's x0-x7 / v0-v7 and returns its result; the only added effect is `mc|` log lines.
- Step 0: 36/36 offline checks pass. A tier-A raw-offset precedent exists (0a). Hooking the
  4-instruction thunk itself with a replace hook is safe on the Skyline runtime copy that is
  in the lab (0c); the copy on the user's card was not hashed.
- One real defect was found and removed before this build: reading x30 inside the Rust hook
  was broken by the size optimiser (2.3). The hooks now enter through assembly stubs.
- Two deliberate deviations from the prompt, both bounded, listed in section 5.

## 0. Prerequisites (offline, B)

Script: `scratch/2026-10-04_P3-DIAG-PLUGIN/step0.py`, output `evidence/P3-DIAG-PLUGIN/01_step0.txt`,
**36 passed, 0 failed, exit 0**. Image: workspace-relative `gamedata/ssbu-13.0.4/main.bin`,
sha256 `f70c97d2...7613` re-hashed, matches.

### 0a. Offset convention

Precedent: `mods/ssbu_mod_new/handbook/12_native_offsets_13_0_4_only.md` **line 9**: pgwr
replaces Pyra's event slots `+0x210` / `+0x220` of vtable `0x4faf9c8`, and "`+0x220` fires when
hit (A, 0.19.0 log)". The source of that patch,
`mods/ssbu_mod_new/src/pgwr/plugin/src/status/special_hi.rs:534-541, 577-595`, only patches
after a load-time check with `base = getRegionAddress(Region::Text)`
(`src/pgwr/plugin/src/article.rs:107-109`):
`[base+0x4faf9c8+0x210] == base+0x68d9c0`, `[base+0x4faf9c8+0x220] == base+0x68d9e0`, and the
code bytes at `base+0x68d9c0` / `base+0x68d9e0` equal `e0 03 00 32 c0 03 5f d6` / `c0 03 5f d6`.
The patch itself goes through `Patch::in_text(off)`, which is `getRegionAddress(Text) + off`
(`skyline-rs@6b52d32/src/patching.rs:89-91`), the same expression the hook macro uses for
`offset = ...` (`skyline_macro/src/install_fn.rs:20-24`).

Checked on the flat image: relocated slot `0x4faf9c8+0x210` -> `0x68d9c0`, `+0x220` ->
`0x68d9e0`; bytes at file offset `0x68d9c0` = `mov w0,#1; ret`, at `0x68d9e0` = `ret`. All
four match what that plugin requires. So a check of the form "bytes at
`getRegionAddress(Text) + file offset`" passed on the console for these file offsets, which is
the convention this plugin uses for hooks, word checks and the static tables.

Limits: I did not read the 0.19.0 console log myself (the handbook line is the citation), and I
did not verify that the 0.19.0 build already contained the byte check in its present form.
Pointer slots are zero in the file and filled by relocation, so they are compared through the
`R_AARCH64_RELATIVE` table (my first version of the check compared file bytes and failed for
that reason). L0 makes the convention checkable on the console independently of all this.

### 0b. Hook sites: function entries and their first four words

| site | words (expected by the plugin) | instructions | entry evidence |
|---|---|---|---|
| `0x4e53e0` | `f9401c00 f9400008 f9401903 d61f0060` | `ldr x0,[x0,#0x38]; ldr x8,[x0]; ldr x3,[x8,#0x30]; br x3` | previous word `udf #0`; no direct branch to it; exactly two relocated pointers, slots `0x4f89490+0x270` and `0x4f73738+0x270` |
| `0x179e440` | `f81e0ff3 a9017bfd 910043fd 7100203f` | `str x19,[sp,#-0x20]!; stp x29,x30,[sp,#0x10]; add x29,sp,#0x10; cmp w1,#8` | previous word `ret`; 72 `bl` callers |
| `0x17c8210` | `a9bd57f6 a9014ff4 a9027bfd 910083fd` | `stp x22,x21,[sp,#-0x30]!; stp x20,x19,[sp,#0x10]; stp x29,x30,[sp,#0x20]; add x29,sp,#0x20` | previous word `udf #0`; 139 `bl` callers (same count as P2-MATCH-READER) |

For all three: 8-aligned; none of the four words is PC-relative; no direct branch and no
relocated pointer targets `site+4 .. site+0xc`. `0x179e440` range-checks `w1 < 8` itself
(`cmp w1,#8; b.hs`), and the `b.hs` is word 4, outside the overwritten range. x8 is not an input
of any site (each overwrites x8 before reading it), nor is x3 of the thunk.

Statics: MOD0 gives bss `0x52a9000..0x7446100`; the 16 table reads span
`0x5307802..0x530957c`, inside bss. `T+0xe58 = 0x53085b8`, `T+0xa2 = 0x5307802`.

New fact for the coordinator: `0x179e440` has **72** direct callers, not only the writers named
in P2-MATCH-READER. See deviation 5.1.

### 0c. Inline versus replace hook

The pinned crate (`skyline-rs@6b52d32`) only declares `A64HookFunction` and `A64InlineHook`;
the code that patches lives in the Skyline runtime (`exefs/subsdk9`). The lab has one copy,
workspace-relative `testenv/ryujinx/data/sdcard/atmosphere/contents/01006A800016E000/exefs/subsdk9`,
sha256 `9959ecb1...9280`, 47841 bytes. I decompressed it (`scratch/.../nso.py`) and read
`A64HookFunction` (`0x43d8`) and `A64HookFunctionV` (`0x40f4`)
(`evidence/P3-DIAG-PLUGIN/02_...txt`, `03_...txt`), B for that copy:

- far target (|distance| >= 2^25 instructions): overwrites **4** words when the site is
  8-aligned, else 5 (`nop` first); writes `ldr x17,#8; br x17; .quad replace`.
- near target: overwrites 1 word with `b`.
- the trampoline pointer is stored to `*result` (`0x4454`) **before** the site is patched
  (`0x448c`); on failure `*result` is 0 and the site is left unpatched.

Decision: **replace hook on all three sites, on the thunk itself.** The thunk is exactly 4
words and 8-aligned, so at most its own 16 bytes are overwritten and `0x4e53f0` is untouched;
the relocated copy is position-independent and ends in `br x3`, so the trampoline's jump back is
never reached. An inline hook was rejected for the thunk because it cannot see the returned f32
(L3 requires it) and for the other two because L1 needs "after the original returns". The entry
jump clobbers x17 only, which is not an argument register. No alternative point was needed.

Unverified: that the card's `subsdk9` is this build. If it differs, the 4-word bound for the
thunk is an assumption (D). L0's `after=` words show which form was written.

The `skyline::hook` macro is not used: its expansion contains `unwrap()` and `panic!`
(`skyline_macro/src/lib.rs:177`, `install_fn.rs:48,64,76`). `A64HookFunction` is called
directly with the address of a static `AtomicUsize` as `result`.

## 1. The plugin

`plugin/src/logic.rs` (pure: constants, formatter, counters, parent table) and
`plugin/src/lib.rs` (stubs, hooks, logging, install). Crate version `0.1.0`, variant string
`diag`. Dependency unchanged: `skyline 0.6.0` rev `6b52d32...`, nothing added.

### 1.1 Log lines

File `sd:/ultimate/mii_customizer_log.txt`, append, one open/write/flush/close per event, every
error ignored. Every line starts `mc|<event>|seq=<n>`; `seq` is a global counter, so a gap means
a dropped line. `ra` values are module-relative (`lr - base`). L0 also goes to the TCP log.

```
mc|L0|seq=0|mii_customizer 0.1.0-diag loaded|base=0x..|T=0x..|id_p0=0x..|special_p0=0x..|hook_param=0x..
mc|L0|seq=1|site=0x179e440|name=store|expected=f81e0ff3,a9017bfd,910043fd,7100203f|found=<4 words>|match=1
mc|L0|seq=2|site=0x179e440|name=store|installed=1|trampoline=0x..|after=<4 words>
        (same pair for 0x17c8210 "load", then 0x4e53e0 "param"; on mismatch: installed=0|reason=words_differ)
mc|L0|seq=7|load_done|base_ok=1
mc|L1|seq=..|n=3|late=0|player=1|ra=0x1791910|x0=0x5307760|p1=<id 8 hex>:<4 special bytes hex>
mc|L2|seq=..|n=2|late=0|all=5|id=0x<8 hex>|ra=0x25cd0e8|ret=0x1
mc|L3|seq=..|h=weight|n=1|slot=0|x0=0x..|parent=0x..|x2=0x0|ra=0x2db55dc|bits=0x42d00000|v=104.0000
mc|L4|seq=..|parent=0x..|slot=0|p0=<id>:<bytes>|p1=..|...|p7=..
mc|L5|seq=..|weight=..|walk_speed_max=..|parents=..|parent_overflow=..|l1=..|l2=..|l2_editor=..|dropped=..|orig_null=..
```

- **L0** the first site line is written before `A64HookFunction` is called and the second
  after, so a crash inside an install leaves the first one. Install order: store, load, param.
  `x0` in L1 is `x0 - base`; `0x5307760` means the call used table `T`.
- **L1** values are read after the original returned. `p >= 8` logs `|noread`.
- **L2** is written after the original returned (so nothing runs before it); `id` and `ra` are
  the entry values, `ret` is the returned w0. Return addresses in `0x19d0950..0x19dc304`
  (inclusive) are counted in `l2_editor` only.
- **L3** only for the two hashes; per parent the first 4 events per hash; 32 parents; events of
  further parents are counted in `parent_overflow`. `bits` is the raw f32, `v` a 4-decimal rendering.
- **L4** once per new parent, all eight players. **L5** with every L4 and on every 600th L3 hit.

### 1.2 Pass-through path

`mc_param_impl` for any other hash: load the stack argument, two compares, tail `br` to the
trampoline (`evidence/P3-DIAG-PLUGIN/04_nro_hooks_disasm.txt`). No heap, lock or IO. Counting
the assembly stub, a non-matching call costs about 35 instructions plus the trampoline.

### 1.3 Reads

`[x0+8]` (L3, after the original returned, which itself dereferenced x0); the 8+8 static table
cells; the 12 instruction words at load (twice). Nothing else is dereferenced. `[x0]` (which
of the two vtables the object has) would be a useful extra field but is not on the allowed
list, so it is not read. For objects of vtable `0x4f73738` it is not shown that `[x0+8]` is a
parent pointer; the value is only printed.

### 1.4 State and concurrency

Fixed statics and atomics only. Parent table: 32 `AtomicU64` keys claimed by compare-exchange,
two `AtomicU32` counts each. Log gate: `AtomicBool` try-lock taken only after the original has
returned and never waited on; when busy the lines are dropped and counted (`dropped=`).
No thread, no mutex in the crate's own code. (`std::fs` itself allocates for the path; that
happens only on logged events.)

### 1.5 Never-panic rules

No `unwrap`, `expect`, `panic!`, assert, indexing expression, `format!` in hook paths
(checked mechanically, section 2.2). `skyline::println!` is used at load only.

If a trampoline pointer is missing while the hook is live (not expected, 0c): the param hook
performs the thunk's own three loads and calls the target; the other two wait up to 10^6 spins
and then return 0 **without calling the original**. That would change behaviour and is counted
as `orig_null`; it is the only such path and should read 0 in every L5 line.

### 1.6 Entry id and the override variant: not built

The only pinned binding is `skyline`; it declares no game function. Getting a parent's entry id
through an exported function would need `skyline_smash` (a new dependency) or a hand-written
symbol declaration (a guess about its ABI). Per the prompt both are excluded, so L3 has no
entry id and `0.1.0-override` was not built. No `builds/0.1.0-override/` exists.

## 2. Build and offline checks

### 2.1 Build

`bash build-plugin.sh` (now stages to `builds/<version>-diag/`; `0.0.1` would still map to
`-scaffold`). Target dir unchanged, `builds/.cache/plugin-target/`. All builds exit 0, 0
warnings in the final one. Final hash `ae49c1c8...96af` reproduced after `touch` + rebuild
(`evidence/P3-DIAG-PLUGIN/06_*`). Not repeated from a cold target tree.
`builds/0.0.1-scaffold/` is untouched (`3ee95be2...`).

### 2.2 Binary and source checks

`python scratch/2026-10-04_P3-DIAG-PLUGIN/check_build.py --write-manifest` -> **37 passed, 0
failed, exit 0** (`evidence/P3-DIAG-PLUGIN/07_check_build.txt`). It checks: NRO0/MOD0 magic and
size; the three `{offset, 4 words}` records contiguous in the binary (at `0x6078`); three entry
stubs with the exact 8-instruction shape and direct `bl` to three distinct functions; one of
them builds both hashes, compares before any call, reads the ninth argument, has a tail `br`
and a `blr`; strings; imports (only skyline, libc, pthread, `nn::fs`; no `A64InlineHook`, no
game symbol); source rules of 1.5; version and the pinned revision.

### 2.3 Defect found by reading the binary

The first build read the return address with `asm!("mov {}, x30")` at the top of each Rust
hook. With `opt-level = "z"` the outliner placed a `bl` to an outlined fragment **before** that
`mov` in the loader hook, so the logged value would have been an address inside the plugin.
Fix: the hook targets are assembly stubs (`stp x29,x30; mov x29,sp; sub sp,#16; str x30,[sp];
bl impl; add sp,#16; ldp; ret`) that pass the return address as a ninth, stack-passed argument.
They leave x0-x7 / v0-v7 untouched both ways. A second iteration removed a PLT indirection by
referencing the implementations with `sym`. `plugin/README.md` warns against undoing this.

### 2.4 Host-side unit test

`bash scratch/2026-10-04_P3-DIAG-PLUGIN/run_host_test.sh` compiles `plugin/src/logic.rs`
unchanged into a host test (gnu toolchain; this machine has no MSVC linker):
**12 passed, 0 failed** (`evidence/P3-DIAG-PLUGIN/05_host_test.txt`). Covers table addresses
for players 0, 1, 7 and out of range; hash filter; word compare; inclusive editor range; first
64 then count only; the 600 cadence; 4 events per hash per parent; 32 parents then overflow; null
parent; 8 threads racing on one table (each parent new exactly once); hex/decimal/float
formatting; truncation that never overruns and keeps the newline.

Not covered by any offline check: the hooks themselves, the stubs at runtime, SD writes.

## 3. For the coordinator's test plan

### 3.1 What the user does (10 steps)

1. Delete an old `sd:/ultimate/mii_customizer_log.txt` if present. Boot the game to the main menu.
2. Vanilla control: Smash, 2 players, P1 Mario, P2 Kirby (any two non-Mii fighters with clearly
   different weights). Start the match.
3. Walk both fighters left and right for about 10 seconds, let one hit the other once, then
   quit the match back to character select.
4. Select P1 = saved Mii Gunner A, P2 = saved Mii Gunner B. They must have different specials;
   easiest to read later: A with the first option in all four slots, B with the third in all four.
5. Start the match, walk both, one hit, about 20 seconds, quit the match.
6. Leave Smash. Open Games & More -> Mii Fighters, open Gunner A's edit screen, enter the
   specials screen, leave it without changing anything, back out to the main menu.
7. Repeat steps 4 and 5 with the same two Gunners.
8. Close the game normally (HOME -> close).
9. Copy `sd:/ultimate/mii_customizer_log.txt` from the card, whole file from boot.
10. If the game crashed or froze anywhere: note the step, and also copy the newest file in
    `atmosphere/crash_reports/`.

Useful to write down during the test: which Gunner was P1 in each match.

### 3.2 Which lines decide which question

**(3) Offset convention - L0.** Right if all three `found` equal `expected` and
`installed=1`. `after=58000051,d61f0220,<lo>,<hi>` is the far form, `14xxxxxx` plus three
unchanged words the near form.

| outcome | meaning |
|---|---|
| all three match, installed | file offset == hook offset on the console (A) |
| all three differ | wrong convention or not 13.0.4; nothing was hooked, rest of the log is empty by design |
| one differs | that site was already hooked by an earlier plugin, or the audit is wrong for it; the other two still log |
| match=1 but installed=0 | the runtime refused the hook (trampoline pool) |

**(1) ID slots at match start - L1, L2, L4.** Between confirming character select and the
first L3 of the Gunner match:

- L2 `id=` values and `ra` name the loader call. Known return addresses (call + 4, from
  P2-MATCH-READER): `0x179177c` (fn `0x17914d0`), `0x230f2a8` (`0x230d4c0`, reads the ID back
  from the table), `0x25cd0e8` (`0x25cc840`), `0x23a1028`, `0x14ebba8 / 0x14ebd2c / 0x14ebed4`.
- L1 `player=` and `ra` name the writer: `0x1791910` (`0x17914d0`), `0x25cd3d4` (`0x25cc840`),
  `0x25cb424` (`0x25cb100`), `0x1961834` (`0x1961590`); anything else is one of the other 68 callers.
- L4 written at the first param request of each new parent shows the slots at fighter creation.

| outcome | meaning |
|---|---|
| L4 during match 2 shows `p0` and `p1` with two different non-zero IDs, special bytes `00000000` and `02020202` on the sides the user chose | slots are correct and current at fighter creation; a plain static read by player index is enough. The L1 lines just before, `ra` included, name the writer |
| IDs present but swapped relative to P1/P2 | `p` is not the match player index; mapping needs another source |
| IDs zero, equal, or the same as in the vanilla match | slots are not filled for the match; L2 `ra` shows where the ID was loaded from instead |
| no L1 between character select and match | this store is not on the match path |
| vanilla match L4: slots zero vs stale | tells whether a non-Mii player clears its slot (needed for the "unknown identity" default) |
| step 7 differs from step 5 | the editor visit rewrites the slots (compare `l2_editor`, late L1 lines) |

The user cannot see IDs; the special bytes are what ties a slot to Gunner A or B. The ID is
then the L2/L4 value next to those bytes.

**(2) Param requests - L3, L5.**

| outcome | meaning |
|---|---|
| vanilla match: L3 `h=weight` with `v=` equal to the two fighters' weights, on different `parent` values | `0x4e53e0` is the float-param getter and the parent is per fighter (turns the naming from D to A) |
| Gunner match: two parents, both `v` = the Gunner weight | the parent pointer separates the two Gunners. Which one is P1 is **not** decided by this log (no entry id); creation order in the vanilla match (which weight appears first) is a hint only |
| `x2` not 0, or `ra` not next to a site listed in P2-STAT-READS section 3 | another caller shape exists; `ra` gives the address to read |
| L5 `weight=` / `walk_speed_max=` keep growing during the match | read repeatedly; an override applies whenever it is active. A small fixed count per match means read at set-up and cached |
| more parents than fighters | other objects use the getter too (items, sub-fighters); `v` and `ra` tell them apart |
| `installed=1` for param and no L3 in any match | requests for these hashes do not pass through `0x4e53e0` |
| `parent_overflow` > 0 | more than 32 parents; later ones unlogged |

Expected weights (Mario 98, Kirby 79, Mii Gunner 104) are from memory, unverified; the
coordinator can read them from the extracted `fighter_param.prc`.

Health fields in every L5: `dropped` (lines lost to concurrent logging), `orig_null` (must be 0).

### 3.3 What a crash or hang would implicate

| where it stops | last log line | implicates |
|---|---|---|
| boot, no log file or no `mc|` line | - | plugin not loaded / import resolution, or SD write at load; unrelated to hooks |
| boot | `L0 ... match=1` for a site without its `installed=` line | `A64HookFunction` on that site |
| boot or first menus, after `load_done` | L0 only | store/load hooks (`0x179e440`, `0x17c8210`) on their first call: stub or trampoline |
| entering character select / Mii screens | an L1 or L2 line | the store/load hook or its table read; `player=` and `ra` identify the call |
| match loading, no L3 yet | L0/L1/L2 | param hook pass-through (`0x4e53e0`), i.e. stub, trampoline or the 4-word assumption of 0c |
| match loading or first frames | an L3 line without its L4/L5 | logging inside the getter (file IO on that thread) |
| freeze instead of crash, log ends cleanly | any | file IO from the calling thread; a gap in `seq` or `dropped>0` in the last L5 supports that |
| only short hitches at match start | - | expected: up to 8 SD writes per new fighter object |

A crash report whose PC is inside the plugin NRO points at the plugin's own code; a PC at
`main+0x4e53e0..0x4e53ec`, `+0x179e440..` or `+0x17c8210..` points at the patch form.
Rollback is removing the one NRO; the plugin writes nothing but its log file.

## 4. Not verified

- Anything at runtime: loading, hook installation, SD append from these call sites, timing cost.
- That the card's Skyline runtime equals the lab copy analysed in 0c.
- That the 0.19.0 console log cited in 0a exists as described (handbook citation only).
- Whether `std::fs` on this target takes a lock internally (it imports `pthread_mutex_lock`);
  the same open/append/close pattern is recorded as working from fighter callbacks in the old
  mod (handbook `11_smashline_skyline.md` line 9).
- Whether another installed plugin hooks one of the three sites (L0 would show `words_differ`).
- The real signatures of the three originals. The hooks forward x0-x7 and v0-v7 and return
  x0 (u64) or s0 (f32); a result returned in x1 or in the upper part of v0 would be lost for
  the two logged-path cases.
- Cold-tree rebuild of 0.1.0.

## 5. Deviations and notes for review

1. **L1/L2 budget extended (bounded).** The prompt says "first 64 events, then count only".
   `0x179e440` has 72 callers and `0x17c8210` 139, so menus could use up 64 events before the
   match. In addition to the first 64, a line is still written when its return address (L1:
   return address + player) has been logged fewer than 4 times, for at most 32 such keys; such
   lines carry `late=1`. At most 128 extra lines per event type. To restore the literal rule,
   delete the two `fresh` conditions in `store_event` / `load_event`.
2. **L2 is written after the original returns**, not at entry, so that no code runs before the
   original; it adds the returned w0. Entry values are what is logged.
3. `build-plugin.sh` and `plugin/Cargo.toml` now describe 0.1.0, so
   `scratch/2026-10-04_P2-PLUGIN-SCAFFOLD/check_scaffold.py` (another worker's file, not run,
   not edited) will no longer match the crate.
4. `builds/.cache/skyline_subsdk9_flat.bin` (97 KB) is the decompressed runtime copy used in 0c;
   `builds/.cache/host-test/` holds the host test binary. Both are disposable.
5. Out of scope, suggested: a kb line that `asm!` reads of x30 are unsafe under `opt-level = "z"`
   (2.3); and hashing the card's `subsdk9` when the package is assembled, to close 0c.

## Closing summary

- **Task ID:** P3-DIAG-PLUGIN
- **Status:** DONE (optional override variant not built, condition not met)
- **Changed files:**
  - `plugin/Cargo.toml` (version 0.1.0, authors), `plugin/Cargo.lock` (version field),
    `plugin/src/lib.rs` (rewritten), `plugin/src/logic.rs` (new), `plugin/README.md` (rewritten)
  - `build-plugin.sh` (variant suffix)
  - `builds/0.1.0-diag/libmii_customizer.nro`, `builds/0.1.0-diag/MANIFEST.json` (new)
  - `builds/.cache/`: `build-0.1.0.log`, `build-0.1.0.stdout`, `skyline_subsdk9_flat.bin`,
    `host-test/`, `plugin-target/` (updated)
  - `research/P3-DIAG-PLUGIN.md` (this file)
  - `evidence/P3-DIAG-PLUGIN/01_step0.txt` .. `07_check_build.txt` (8 files)
  - `scratch/2026-10-04_P3-DIAG-PLUGIN/`: `d.py`, `rel.py`, `chain.py` (unmodified copies),
    `step0.py`, `nso.py`, `dynsym.py`, `flatdis.py`, `check_build.py`, `host_test.rs`,
    `run_host_test.sh`
- **Observed checks:** step 0 36/36; build exit 0 with a reproduced hash; binary/source check
  37/37; host unit tests 12/12.
- **Not touched:** `mods/ssbu_mod_new` (read only), `testenv/` (read only), `kb/`, `STATUS.md`,
  other workers' files, SD card, emulator. No commits, branches, agents or installs.
- **Could not verify:** section 4.
