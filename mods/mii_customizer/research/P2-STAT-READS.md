# P2-STAT-READS - where the executable uses the weight and walk_speed_max hashes

Task: `P2-STAT-READS`. Worker: Space Bunny Alpha. Date: 2026-10-04.
Prompt: `prompts/P2-STAT-READS.md`. Coordinator review: `research/COORDINATOR-2026-10-04.md`.

**One question.** Which code sites in the 13.0.4 executable compose the two
parameter hashes `weight` (`0x0607cd5541`) and `walk_speed_max`
(`0x0ee2ec2860`)?

**This report does not answer whether the values are fetched per use or copied
once.** It lists the sites. That reading is deliberately left to the next
person. Nothing here is named after what it "does", nothing is connected to
fighter kind or to Mii, and no runtime timing is claimed.

Evidence tiers: **B** offline measurement of a local file; **C** pinned external
source (used only for the `0x270` comparison); **D** hypothesis. **No tier A.**
No emulator, no console, no game run.

## Input

| item | value |
|---|---|
| file | `gamedata/ssbu-13.0.4/main.bin` (workspace-relative) |
| sha256 (rehashed at start of task) | `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` |
| expected sha256 (from prompt) | `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` |
| size | 86672752 bytes |
| layout | flat decompressed NSO, address == file offset |
| code range scanned | `0x100` .. `0x39C8000` |
| disassembler input | `scratch/2026-10-04_P1-ID-REVIEW/d.py`, copied to `scratch/2026-10-04_P2-STAT-READS/d.py` |
| capstone | 5.0.7, via `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python` |

**Hash matched, so the task was not BLOCKED.** The rehash is repeated by
`evidence/P2-STAT-READS/check_stat_reads.py`.

## Commands

```
sha256sum gamedata/ssbu-13.0.4/main.bin
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-04_P2-STAT-READS/stat_reads.py validate
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-04_P2-STAT-READS/stat_reads.py data
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-04_P2-STAT-READS/report.py
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/evidence/P2-STAT-READS/check_stat_reads.py
```

`python` (3.12.3) throughout, as instructed.

## 1. Scanner and its validation

A 40-bit constant is composed by `movz` (or `mov`) plus one or two `movk` on the
same register. Encodings accepted:

| form | word mask == |
|---|---|
| `MOVZ` 64-bit | `0xD2800000` |
| `MOVK` 64-bit | `0xF2800000` |
| `MOVZ` 32-bit | `0x52800000` |
| `MOVK` 32-bit | `0x72800000` |

A sequence is accepted when the composing instructions are adjacent or separated
by at most **4** instructions, none of which writes the carrying register. A
`bl`/`blr` counts as writing `x0`-`x18`, so no sequence is allowed to span a
call.

`stat_reads.py validate` runs **33 checks and passes all of them (exit 0)**:
the scanner finds both hashes planted in synthetic buffers (adjacent, gap 3,
gap exactly 4, and the shape seen at `0x595a8c` where four `movk` to other
registers sit between the composing instructions); and it reports nothing for
an intervening overwrite of the same register, a gap larger than 4, or a lone
`movz` of the low half only. A second, independently written scanner
(`scan_sequences_strict`) is used as a cross-check; on the real image both agree
exactly, 37 and 18 sites.

Two defects were found and fixed by these tests rather than by inspection:

* `regs_access()` needs `detail=True`. With it off, capstone raised
  `CsError`, the handler returned an empty writer set for **every** instruction,
  and the overwrite negative tests passed vacuously. `dest_regs` now enables
  detail and also adds the ABI-clobbered registers for `bl`/`blr`.
* The strict cross-check had an off-by-one gap limit and missed `0x595a8c`.

`validate` also asserts directly that `dest_regs` reports a writer for a known
`movz`, `add` and `bl`, so the negative tests cannot pass vacuously again.

## 2. Counts

| hash | name | code sites | data sites (raw 8-byte LE) | data sites (low 40 bits, 8-byte aligned) |
|---|---|---|---|---|
| `0x0607cd5541` | `weight` | **37** | **0** | **0** |
| `0x0ee2ec2860` | `walk_speed_max` | **18** | **1** | **1** |

Both hashes **do** appear in code, so the "zero code sites" stop condition in the
prompt does not apply.

### Data sites

The single hit is `0x453d0e0`, 8-byte aligned, file qword
`0x0000000ee2ec2860` - the hash with the top 24 bits zero, which is the same
value. Its neighbours are `0x3f800000` at `0x453d0c8` and `0x453d0f0` and zero
at `0x453d0e8` and `0x453d100`. **The table is not interpreted**, per the
prompt.

`weight` has no raw data occurrence anywhere in the image, at any alignment and
under both match rules.

## 3. Code sites

All 18 `walk_speed_max` sites are listed. For `weight` (37 sites) the **first 25
by address** are listed and **12 were left out** (`0x2dd7368`, `0x2ee5f94`,
`0x2f409d0`, `0x2f4933c`, `0x2ff7110`, `0x30ad990`, `0x30ae41c`, `0x30ae54c`,
`0x30c0f58`, `0x30c1520`, `0x36d8c98`, `0x36d8eac`). The complete address list
for both hashes is in `check_stat_reads.py` (`EXPECT`) and is re-derived from the
image on every run.

Raw 12-before / 20-after windows for every listed site are in
`evidence/P2-STAT-READS/win_<hash>_<site>.txt`.

### weight `0x0607cd5541`

| site | fstart cand. | reg | completes | first `bl`/`blr` after | other >=2^32 const in window | callers of fstart |
|---|---|---|---|---|---|---|
| `0x00595a8c` | `0x590a50` | x0 | `0x595aa4` | none within completing+0x400 | none | 0 |
| `0x0069d018` | `0x69cf90` | x1 | `0x69d024` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x69d010` | none | 1 |
| `0x006c6590` | `0x6c5df0` | x1 | `0x6c6598` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x6c65a0` | none | 0 |
| `0x006f5278` | `0x6f37b0` | x10 | `0x6f5280` | none within completing+0x400 | `0x607cd5540` @`0x6f5264`, `0x6a0d82dad` @`0x6f528c`, `0x6f54de50f` @`0x6f52a0` | 0 |
| `0x006f9778` | `0x6f7b20` | x24 | `0x6f9788` | none within completing+0x400 | none | 0 |
| `0x00ebeb98` | `0xebeadc` | x10 | `0xebeba0` | `bl` -> `0x39c0d80` | `0xe81be1d33`, `0xc8ef76c50`, `0x82d53e341`, `0xd62c374ed` | 0 |
| `0x01130030` | `0x112fef4` | x10 | `0x1130038` | none within completing+0x400 | `0x10abe75caf`, `0x13066f4b4e`, `0x82d53e341` | 0 |
| `0x023ddafc` | `0x23dab40` | x2 | `0x23ddb10` | `bl` -> `0x23d7250` | `0xa3d96e7b3` @`0x23ddaf4`, `0x120b0e70f9` @`0x23ddb34` | 0 |
| `0x023ddc24` | `0x23dab40` | x2 | `0x23ddc30` | `bl` -> `0x23d7250` | `0x1b259b918c` @`0x23ddbfc`, `0xa3d96e7b3` @`0x23ddc1c` | 0 |
| `0x023df9b8` | `0x23dab40` | x18 | `0x23df9c8` | `bl` -> `0x23d7250` | `0x120b0e70f9` @`0x23df9ec` | 0 |
| `0x023dfad4` | `0x23dab40` | x18 | `0x23dfadc` | `bl` -> `0x23d7250` | `0x1b259b918c` @`0x23dfab4` | 0 |
| `0x027085e4` | `0x2707b50` | x1 | `0x27085ec` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x27085e0` | none | 0 |
| `0x0299fc08` | `0x299f7b0` | x1 | `0x299fc10` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x299fc04` | none | 3 |
| `0x029a42b4` | `0x29a2f30` | x1 | `0x29a42bc` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x29a42b0` | none | 1 |
| `0x02b1b34c` | `0x2b1ab30` | x1 | `0x2b1b354` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2b1b348` | none | 2 |
| `0x02b88934` | `0x2b88200` | x1 | `0x2b8893c` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2b88930` | none | 3 |
| `0x02bcea58` | `0x2bce810` | x1 | `0x2bcea60` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2bcea54` | none | 0 |
| `0x02be5c10` | `0x2be5b50` | x1 | `0x2be5c18` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2be5c0c` | none | 0 |
| `0x02c16880` | `0x2c15f50` | x1 | `0x2c16888` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2c1687c` | none | 2 |
| `0x02d7b43c` | `0x2d7aee0` | x1 | `0x2d7b444` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2d7b438` | none | 0 |
| `0x02db4eec` | `0x2db4eb0` | x22 | `0x2db4efc` | `bl` -> `0x39c0100` | none | 0 |
| `0x02db55c8` | `0x2db4eb0` | x1 | `0x2db55d0` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2db55c4` | none | 0 |
| `0x02db5648` | `0x2db4eb0` | x1 | `0x2db5650` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2db5644` | none | 0 |
| `0x02db56c8` | `0x2db4eb0` | x1 | `0x2db56d0` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2db56c4` | none | 0 |
| `0x02db5748` | `0x2db4eb0` | x1 | `0x2db5750` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x2db5744` | none | 0 |

### walk_speed_max `0x0ee2ec2860`

| site | fstart cand. | reg | completes | first `bl`/`blr` after | other >=2^32 const in window | callers of fstart |
|---|---|---|---|---|---|---|
| `0x006d42c0` | `0x6d4060` | x1 | `0x6d42c8` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x6d42bc` | `0x6e5ec7051` @`0x6d42ec`, `0x12b00664bc` @`0x6d42f8` | 0 |
| `0x006d86d4` | `0x6d8560` | x1 | `0x6d86dc` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x6d86cc` | none | 0 |
| `0x006f3f14` | `0x6f37b0` | x10 | `0x6f3f1c` | none within completing+0x400 | `0xefbdfb1da`, `0xed1f9fdb8`, `0xef53a098c`, `0x1a0ac3b7ce` | 0 |
| `0x006f82f4` | `0x6f7b20` | x4 | `0x6f8300` | none within completing+0x400 | none | 0 |
| `0x006f830c` | `0x6f7b20` | x4 | `0x6f8314` | none within completing+0x400 | none | 0 |
| `0x0085b26c` | `0x85a9d0` | x10 | `0x85b274` | `bl` -> `0x75d8f0` | `0x120a302025` @`0x85b254`, `0xef53a098c` @`0x85b284` | 1 |
| `0x009132f8` | `0x9130b0` | x1 | `0x913300` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x9132f0` | `0x1ed6c19cc5` @`0x913334` | 0 |
| `0x009138e0` | `0x913710` | x1 | `0x9138e8` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x9138dc` | `0xef53a098c` @`0x913908` | 0 |
| `0x00993818` | `0x993750` | x8 | `0x993820` | `bl` -> `0x392e590` | `0xef53a098c` @`0x9937fc`, `0xea1225bca` @`0x993830` | 0 |
| `0x009deccc` | `0x9dea20` | x8 | `0x9decd4` | `bl` -> `0x392dce0` | `0xc8cc9db76`, `0xadec47ea3`, `0xd4d7c9e77`, `0xd1964cc31` | 3 |
| `0x00a8f070` | `0xa8e7ec` | x10 | `0xa8f078` | `bl` -> `0x39c0d80` | `0x11bd57461e`, **`0xee2ec285f`**, `0xef53a098c`, `0xf25ec86be`, `0x1648b9a5a1` | 0 |
| `0x00aa22cc` | none found | x15 | `0xaa22dc` | none within completing+0x400 | none | - |
| `0x00adade0` | `0xadac40` | x11 | `0xadade8` | `bl` -> `0x1c0` | `0xea1225bca`, `0xadec47ea3`, `0xd4d7c9e77`, `0xd1964cc31` | 0 |
| `0x00be3e8c` | `0xbe3d20` | x1 | `0xbe3e94` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0xbe3e84` | `0x226cf721de` @`0xbe3e64`, `0x17ab08d19c` @`0xbe3e9c`, `0x179705eec5` @`0xbe3ebc` | 0 |
| `0x0105fec8` | `0x105fc90` | x1 | `0x105fed0` | `blr x8`, producer `ldr x8, [x8, #0x270]` @`0x105fec4` | `0xea1225bca` @`0x105fea4`, `0xc8cc9db76` @`0x105feec` | 0 |
| `0x0116c814` | `0x116b880` | x10 | `0x116c81c` | `bl` -> `0x75d8f0` | `0xadec47ea3` @`0x116c824`, `0xd4d7c9e77` @`0x116c848`, `0xd5aaabf9b` @`0x116c858` | 2 |
| `0x0116cd34` | `0x116b880` | x10 | `0x116cd3c` | `bl` -> `0x75d8f0` | `0xba18057d9`, `0xef53a098c`, `0xadec47ea3` | 2 |
| `0x0131611c` | `0x1315e20` | x9 | `0x1316124` | `bl` -> `0x75d8f0` | `0xadec47ea3`, `0xd5aaabf9b`, `0x1357b18314` | 3 |

### Observations about the other hash-like argument

Step 3 asked what the same window shows about the other argument. Recorded as
plain equal/not-equal, with no naming:

* **No window builds the other of the two hashes.** At no `weight` site is
  `0x0ee2ec2860` built nearby, and at no `walk_speed_max` site is
  `0x0607cd5541` built nearby. The two hashes never appear in the same window.
* Two windows build a constant exactly **one** away from a target hash:
  `0x607cd5540` (= `weight` - 1) at `0x6f5264`, and `0xee2ec285f`
  (= `walk_speed_max` - 1) at `0xa8f05c`. These are **not equal** to either
  hash and are recorded only as an adjacent-constant observation.
* The many other >=2^32 constants in the table are unrelated values in the same
  register or nearby registers. They are listed per site with addresses so a
  later reader can judge them.

### Vtable offset comparison with the declared `0x270`

P2-STAT-API section 3 declares `WorkModule::get_param_float` at vtable offset
`0x270` (C). Comparing that **number only**, as the prompt allows:

* Every `blr` site's target register `x8` is produced by a literal
  `ldr x8, [x8, #0x270]` **at these addresses**, with no other offset observed
  in any window:
  `weight` - `0x69d010`, `0x6c65a0`, `0x27085e0`, `0x299fc04`, `0x29a42b0`,
  `0x2b1b348`, `0x2b88930`, `0x2bcea54`, `0x2be5c0c`, `0x2c1687c`, `0x2d7b438`,
  `0x2db55c4`, `0x2db5644`, `0x2db56c4`, `0x2db5744`;
  `walk_speed_max` - `0x6d42bc`, `0x6d86cc`, `0x9132f0`, `0x9138dc`,
  `0xbe3e84`, `0x105fec4`.
* **Equal** to `0x270` in all 21 of those cases. No site shows a different
  offset.

That is a numeric equality between an image operand and a number in a pinned
declaration. It is **not** evidence about which function is at that slot, and it
does not establish per-instance or per-use behaviour.

## 4. Enclosing functions and their direct `bl` callers

Function start candidates come from the same backward prologue scan as
`d.py fstart` and are **candidates, not confirmed boundaries**. 32 distinct
candidate values appear in the table below (18 for weight, 15 for walk, two of
them shared between the hashes, giving **31** distinct); one site
(`walk 0xaa22cc`) produced no candidate at all and is excluded from the caller
table. Distinct enclosing functions: **18** for
`weight`, **15** for `walk_speed_max`. Two function candidates each cover sites
for both hashes: `0x6f37b0` (weight `0x6f5278`, walk `0x6f3f14`) and `0x6f7b20`
(weight `0x6f9778`, walk `0x6f82f4`/`0x6f830c`).

Callers are direct `bl` instructions only. **No further up the call graph was
followed**, as instructed.

| hash | fstart | sites | direct `bl` callers | first 10 caller addresses |
|---|---|---|---|---|
| weight | `0x590a50` | `0x595a8c` | 0 | - |
| weight | `0x69cf90` | `0x69d018` | 1 | `0x20c9338` |
| weight | `0x6c5df0` | `0x6c6590` | 0 | - |
| weight | `0x6f37b0` | `0x6f5278` | 0 | - |
| weight | `0x6f7b20` | `0x6f9778` | 0 | - |
| weight | `0xebeadc` | `0xebeb98` | 0 | - |
| weight | `0x112fef4` | `0x1130030` | 0 | - |
| weight | `0x23dab40` | `0x23ddafc`, `0x23ddc24`, `0x23df9b8`, `0x23dfad4` | 0 | - |
| weight | `0x2707b50` | `0x27085e4` | 0 | - |
| weight | `0x299f7b0` | `0x299fc08` | 3 | `0x299c628`, `0x299c6d0`, `0x299c778` |
| weight | `0x29a2f30` | `0x29a42b4` | 1 | `0x299f608` |
| weight | `0x2b1ab30` | `0x2b1b34c` | 2 | `0x2b14580`, `0x2b14648` |
| weight | `0x2b88200` | `0x2b88934` | 3 | `0x2b7f004`, `0x2b7f214`, `0x2b7f6c8` |
| weight | `0x2bce810` | `0x2bcea58` | 0 | - |
| weight | `0x2be5b50` | `0x2be5c10` | 0 | - |
| weight | `0x2c15f50` | `0x2c16880` | 2 | `0x2c0a70c`, `0x2c0f9e4` |
| weight | `0x2d7aee0` | `0x2d7b43c` | 0 | - |
| weight | `0x2db4eb0` | `0x2db4eec`, `0x2db55c8`, `0x2db5648`, `0x2db56c8`, `0x2db5748` | 0 | - |
| walk | `0x6d4060` | `0x6d42c0` | 0 | - |
| walk | `0x6d8560` | `0x6d86d4` | 0 | - |
| walk | `0x6f37b0` | `0x6f3f14` | 0 | - |
| walk | `0x6f7b20` | `0x6f82f4`, `0x6f830c` | 0 | - |
| walk | `0x85a9d0` | `0x85b26c` | 1 | `0x21b6ce4` |
| walk | `0x9130b0` | `0x9132f8` | 0 | - |
| walk | `0x913710` | `0x9138e0` | 0 | - |
| walk | `0x993750` | `0x993818` | 0 | - |
| walk | `0x9dea20` | `0x9deccc` | 3 | `0x9dd4c0`, `0x9e02ac`, `0x21e12a0` |
| walk | `0xa8e7ec` | `0xa8f070` | 0 | - |
| walk | `0xadac40` | `0xadade0` | 0 | - |
| walk | `0xbe3d20` | `0xbe3e8c` | 0 | - |
| walk | `0x105fc90` | `0x105fec8` | 0 | - |
| walk | `0x116b880` | `0x116c814`, `0x116cd34` | 2 | `0x11681cc`, `0x1168384` |
| walk | `0x1315e20` | `0x131611c` | 3 | `0x131365c`, `0x13137a0`, `0x13137c4` |

Most candidate functions have **zero direct `bl` callers**, which for a
production image usually means they are reached indirectly (vtable dispatch) or
that the prologue heuristic picked a boundary that is not a real entry. That is
recorded, not resolved.

Of the **31** distinct candidate functions in the table above (18 weight + 15 walk,
two shared between the hashes), **21 have zero direct `bl` callers** and 10 have
one to three. Every caller count and every first-10 address is restated in
`check_stat_reads.py` `EXPECT_FNS` and is re-derived from the image on each run.

## 5. Limitations

1. **No runtime claim.** Nothing here says when any site executes, how often, or
   whether the result is cached. That is the question this task deliberately did
   not decide.
2. **Function boundaries are heuristic.** `fstart` is a backward scan for a
   prologue shape; it is not a validated boundary and it fails on at least one
   site. Zero-caller counts inherit that weakness.
3. **Only `movz`/`movk` builds are found.** A hash reached by `orr`/`add` of two
   immediates, or loaded from the one data occurrence at `0x453d0e0`, would not
   appear as a code site. The `weight` value has no data occurrence at all, so
   for that hash a non-`movz`/`movk` code path cannot be excluded by this
   method.
4. **Window limits.** "First call after" searches from the instruction after the
   completing `movk` through a fixed span of 0x400 bytes. "none within
   completing+0x400" means no `bl`/`blr` was found in that span, not that none
   exists later. The report generator and the check script use the identical
   definition.
5. **`0x270` is a number comparison.** It is compared with a pinned declaration
   (C) and with nothing in the image. No vtable layout was verified and no
   symbol was resolved.
6. **The `weight` site list is truncated** at 25 of 37 by the prompt's own cap;
   12 addresses are named above and all 37 are in the check script.
7. **Nothing is named.** No site is described as "walk", "weight use", "physics",
   "init" or any other function purpose; no site is connected to fighter kind or
   to Mii. Other constants are listed by value only.

## 6. Next experiment

Offline, and the smallest one that separates "fetched per use" from "copied
once" for a reader who now has the site list:

> Disassemble the three enclosing functions with the **highest** direct caller
> counts and the largest site clusters - `0x2db4eb0` (5 `weight` sites),
> `0x23dab40` (4 `weight` sites), `0x116b880` (2 `walk` sites) - and record, for
> each `ldr x8, [x8, #0x270]` / `blr x8` pair, **what register the float result
> lands in and whether that register is written again inside the same function**.
> A single read-and-discard near each site is consistent with per use; a result
> stored into an object field and read back later in the function is consistent
> with copy-once. This is still offline: it reads the image, it does not run it.

A second offline option, if the reader wants the truncation closed first: extend
the check script to emit the 12 omitted `weight` windows the same way as the 25
listed ones.

## Evidence index

| file | what |
|---|---|
| `evidence/P2-STAT-READS/check_stat_reads.py` | re-derives every site, count, caller and data hit from the image and re-checks the report tables; nonzero on mismatch (450/450 pass) |
| `evidence/P2-STAT-READS/sites.json` | machine-readable site list |
| `evidence/P2-STAT-READS/summary_weight.md` | generated summary table, weight |
| `evidence/P2-STAT-READS/summary_walk_speed_max.md` | generated summary table, walk |
| `evidence/P2-STAT-READS/win_<hash>_<site>.txt` | raw 12-before / 20-after window per listed site |
| `evidence/P2-STAT-READS/data_hits_raw.txt` | step 2 output |
| `evidence/P2-STAT-READS/code_sites_raw.txt` | first scan output |
| `scratch/2026-10-04_P2-STAT-READS/stat_reads.py` | scanner, data search, `validate` |
| `scratch/2026-10-04_P2-STAT-READS/report.py` | report generator |
| `scratch/2026-10-04_P2-STAT-READS/d.py` | copy of the P1-ID-REVIEW disassembler |

## Summary

Task `P2-STAT-READS` - **DONE**.

Changed files (all inside `mods/mii_customizer/`, no other worker's files, no
commits, no branches, no emulator, no SD access, no framework changes):

* `research/P2-STAT-READS.md` (this file, new)
* `evidence/P2-STAT-READS/` (new: check script, `sites.json`, two generated
  summary tables, 43 raw window files, two raw scan logs)
* `scratch/2026-10-04_P2-STAT-READS/` (new: `stat_reads.py`, `report.py`, copy
  of `d.py`)

Inputs were read-only. `gamedata/ssbu-13.0.4/main.bin` was rehashed and matched.

Observed checks:

* `stat_reads.py validate` - **33/33 pass, 0 fail, exit 0** (planted-hash
  positives and both negative classes).
* `report.py` - primary and strict scanners **agree exactly**: 37 and 18 sites.
* `evidence/P2-STAT-READS/check_stat_reads.py` - independent re-derivation,
  **450/450 pass, 0 fail, exit 0**. It re-reads the image, re-derives every site,
  count, data offset, caller count and first-call kind, replays each site's
  `movz`/`movk` value, and compares the report tables against the generated
  summary tables so the prose cannot drift.

Unresolved questions, left for the next reader: whether any of these 55 sites is
on a per-use read path or on an init-time copy; what the two `-1` adjacent
constants at `0x6f5264` and `0xa8f05c` are; why 12 `weight` sites build the hash
in `x10`/`x18`/`x2`/`x22`/`x24` rather than `x1`, which the argument-passing
sites mostly use; and whether the zero-caller functions are vtable-dispatched.