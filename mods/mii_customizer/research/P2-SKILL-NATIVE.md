# P2-SKILL-NATIVE - where the six special-selector bridge names are registered

Task: `prompts/P2-SKILL-NATIVE.md`. Date 2026-10-04. Status: **DONE** (locating only).

This is a locating task. It answers *where each name is registered* and *which function
address is its handler*. It deliberately does **not** read what the handlers do. Nothing
here is a runtime claim.

## Input

`gamedata/ssbu-13.0.4/main.bin` (workspace-relative), sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`, 86672752 bytes,
rehashed at the start of this task - **matches** (`evidence/P2-SKILL-NATIVE/06_input_identity.txt`).
Flat `MOD0` image, address == file offset. No ELF header and no program headers.

Pointer slots in `.data` are zero in the file and filled at load by `R_AARCH64_RELATIVE`.
Because the image has no relocation header, the records are a bare 24-byte array; this task
located it at file `0x39c8070..0x40c9fc7` (306169 records) and read addends from it. The
record layout was validated against the one vtable P1-ID-REVIEW already decoded:
`0x50a6d28` resolves here to `{0x19c2210, 0x19dc640, 0x19dc650}`, identical to that report.
**The post_fighter pattern was re-verified, not assumed.**

Tiers: **B** = read from the image in this task (offline, static only). **C** = pinned prior
report. **D** = hypothesis, flagged as such. No emulator, no console, no runtime behaviour.

## Result table

All six registrations sit in **one enclosing function, `0x19ddb30`** (prologue
`sub sp, sp, #0xa0` at `0x19ddb30`, `add sp, sp, #0xa0` at `0x19de6ac`, `ret` at
`0x19de6b0`). Owner object is `x19` for all six, stored at delegate `+0x10`.

| name | string address | reference site | enclosing function | delegate size | vtable | thunk | handler address | owner-object origin | confidence note |
|---|---|---|---|---|---|---|---|---|---|
| `set_skill_id` | `0x04348c5a` | `0x19de10c` | `0x19ddb30` | `0x28` | `0x50a6e78` | `0x19dd950` | **`0x19dcf20`** | `x19` (19) | high. All fields traced inside the dumped window. Handler pointer in `x8` built at `0x19de0f8`, stored `+0x18` by `stp x19, x8, [x0,#0x10]` at `0x19de104`. |
| `get_skill_id` | `0x042905bf` | `0x19de1bc` | `0x19ddb30` | `0x38` | `0x50a6ea0` | `0x19dd7d0` | **`0x19dcf40`** | `x19` (19) | high for the address; **layout differs from post_fighter**. Handler in `x9` built at `0x19de1a0`, stored at **`+0x28`** by `stp xzr, x9, [x0,#0x20]` at `0x19de1b4`, while `+0x18` is explicitly zeroed at `0x19de1ac`. The thunk confirms this: it reads `+0x28` first (`0x19dd89c`) and falls back to `+0x18` (`0x19dd8f8`). |
| `get_skill_name_label` | `0x0427f3d5` | `0x19de268` | `0x19ddb30` | `0x38` | `0x50a6ec8` | `0x19dd5c0` | **`0x19dcf60`** | `x19` (19) | high. Handler in `x8` built at `0x19de248`, stored `+0x18` by `stp x8, xzr, [x0,#0x18]` at `0x19de254`; owner at `+0x10` by `str x19, [x0,#0x10]` at `0x19de26c`. |
| `get_skill_help_label` | `0x0441127e` | `0x19de310` | `0x19ddb30` | `0x38` | `0x50a6ec8` (shared) | `0x19dd5c0` (shared) | **`0x19dd080`** | `x19` (19) | high. Same vtable/thunk as `get_skill_name_label`, different handler: `x8` built at `0x19de2f8` = `0x19dd080`, stored `+0x18` at `0x19de300`. The vtable comes from `x22`, last defined at `0x19de24c`/`0x19de250` - i.e. **outside** this site's own 60-instruction window, established from the enclosing-function dump. |
| `replace_skill` | `0x0439bd6c` | `0x19de3b0` | `0x19ddb30` | `0x28` | `0x50a6e78` (shared with `set_skill_id`) | `0x19dd950` (shared) | **`0x19dd1a0`** | `x19` (19) | high. Handler in `x8` built at `0x19de3a0`, stored `+0x18` by `stp x19, x8, [x0,#0x10]` at `0x19de3a8`. The vtable register `x21` is reused from `0x19de0f0`, outside this window (D for this row alone, B via the enclosing-function dump). |
| `replace_skill_subwindow` | `0x0437af9d` | `0x19de45c` | `0x19ddb30` | `0x28` | `0x50a6ef0` | `0x19dd480` | **`0x19dd250`** | `x19` (19) | high. Handler in `x9` built at `0x19de448`, stored `+0x18` by `stp x19, x9, [x0,#0x10]` at `0x19de454`. Its thunk `0x19dd480` reads `+0x10`/`+0x18` and tail-branches, the same shape as the post_fighter control. |

### Delegate vtables (step 5)

Slot 0 is `0x19c2210` on all five vtables; slot 2 is the invoke thunk.

| vtable | slot 0 | slot 1 | slot 2 (invoke thunk) | used by |
|---|---|---|---|---|
| `0x50a6e78` | `0x19c2210` | `0x19dd940` | `0x19dd950` | `set_skill_id`, `replace_skill` |
| `0x50a6ea0` | `0x19c2210` | `0x19dd7c0` | `0x19dd7d0` | `get_skill_id` |
| `0x50a6ec8` | `0x19c2210` | `0x19dd5b0` | `0x19dd5c0` | `get_skill_name_label`, `get_skill_help_label` |
| `0x50a6ef0` | `0x19c2210` | `0x19dd470` | `0x19dd480` | `replace_skill_subwindow` |

The prompt anticipated that the vtable and thunk might differ per argument count. They do
differ, but not in the way the argument counts alone predict: the four thunk shapes are

- `0x19dd950` / `0x19dd480`: `ldp` the `+0x10`/`+0x18` pair, tail-`br` - identical in shape to
  the verified post_fighter thunk `0x19dc650`.
- `0x19dd5c0` / `0x19dd7d0`: read `+0x28`/`+0x30` first (`0x19dd708` / `0x19dd89c`) and fall
  back to `+0x18`/`+0x20` (`0x19dd750` / `0x19dd8f8`). `0x19dd5c0` returns the handler result
  to Lua (`b #0x38f4570` at `0x19dd74c`); `0x19dd7d0` branches to the handler and stores the
  result into the Lua stack slot (`blr x8` at `0x19dd8c0`).

Per-name argument counts were **not** used to infer any of this; each thunk was read.

### Handler candidate function starts (step 4)

Each handler address is itself a function start: four are immediately preceded by `udf #0`
padding (`0x19dcf1c`, `0x19dd07c`, `0x19dd19c`, `0x19dd24c`); `0x19dcf40` and `0x19dcf60`
follow the cold assert blocks at `0x19dcf34`/`0x19dcf54` whose last call is `bl 0x39c20a0`.
Raw 40-instruction windows are in `evidence/P2-SKILL-NATIVE/03_handler_windows.txt`; no
commentary on behaviour is offered beyond the direct `bl` targets and the adrp-resolved
string/global addresses visible in those windows.

### Other names registered or referenced in the same function (step 6, no analysis)

Plain list, `(name, handler address)` where a handler address exists:

- `set_btn_ok` (`0x43cdd95`, ref `0x19de04c`) - passed to `bl 0x3776090`, **no delegate built,
  no handler address**.
- `SPECIAL_SKILL_NUM` (`0x424de53`) / `SKILL_COMMAND_NORMAL` (`0x4348c67`) /
  `SKILL_COMMAND_SIDE` (`0x424de65`) / `SKILL_COMMAND_UPPER` (`0x43bd0b4`) /
  `SKILL_COMMAND_LOWER` (`0x432898f`) / `SKILL_COMMAND_NUM` (`0x4338b2f`) /
  `INPUT_OK` (`0x4306e9b`) - all passed to `bl 0x33750a0`, a different registration
  function from `0x3376540`. **No handler addresses.**
- `initialize` (`0x42b0d8c`) - passed to `bl 0x38f4570` and `bl 0x38f4790`. **No handler
  address.**

`0x3376540` is called exactly **6** times in `0x19ddb30`, and all six are these six names.

## Method and commands

```
sha256sum gamedata/ssbu-13.0.4/main.bin
export PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python
python mods/mii_customizer/scratch/2026-10-04_P2-SKILL-NATIVE/strfind.py      # step 1
python mods/mii_customizer/scratch/2026-10-04_P2-SKILL-NATIVE/refscan.py      # step 2
python mods/mii_customizer/scratch/2026-10-04_P2-SKILL-NATIVE/w.py <addr> <n>  # steps 3-4
python mods/mii_customizer/scratch/2026-10-04_P2-SKILL-NATIVE/relocs.py 0x… 4 # step 5
python mods/mii_customizer/scratch/2026-10-04_P2-SKILL-NATIVE/fstart.py <addr># step 4
bash   mods/mii_customizer/scratch/2026-10-04_P2-SKILL-NATIVE/windows.sh     # all evidence
python mods/mii_customizer/scratch/2026-10-04_P2-SKILL-NATIVE/check_claims.py # 174 checks
```

`check_claims.py` re-derives every address in this report directly from the image
(disassembly text plus relocation addends, never the window scripts): **174 checks,
0 failures, exit 0** (`evidence/P2-SKILL-NATIVE/07_claim_check.txt`).

Note: capstone here reports **5.0.7**, where P1-ID-REVIEW recorded 5.0.9. Disassembly of the
cited sites was cross-read against the raw words; no discrepancy was found, but the version
difference is recorded rather than glossed.

## Observed checks, failures and limits

- All six names: exactly one NUL-terminated occurrence each; counts reported including zero.
  The terminator rule matters for `replace_skill`: it appears once bare, inside
  `replace_skill_subwindow` at `0x437af9d`, and that occurrence does **not** satisfy a
  `replace_skill\0` match.
- Reference-site scan: exactly one `adrp+add` completion per name, all six inside
  `0x19ddb30..0x19de6b0`.
- Provenance: every store into each new delegate was traced to an immediate or to an `adrp`
  target **inside the dumped window**, with two exceptions marked in the table
  (`get_skill_help_label` vtable from `x22`, `replace_skill` vtable from `x21`), both
  established from the enclosing-function dump rather than the 60-instruction window. The
  owner register `x19` is defined at `0x19ddb94` (`mov x19, x0`, from a 0x150-byte
  allocation) inside the enclosing function, so it is in scope for step 6 but outside each
  per-site window.
- No store was left as "provenance not established". The one genuinely non-obvious case,
  `get_skill_id`'s `+0x28` slot, was resolved by reading the thunk rather than by analogy
  with `post_fighter`, and the thunk reads `+0x28` first.
- Limits: no runtime behaviour claimed; nothing executed. Struct fields are named by offset
  only. No saved-fighter record is connected to any of this. Handler bodies are located but
  not interpreted. Whether `0x19ddb30` is the only place these names are ever registered
  was not checked beyond the TEXT-wide reference scan, which found no second reference to any
  of the six strings.

## Smallest next question

For `0x19dcf20` (`set_skill_id`) and `0x19dcf40` (`get_skill_id`): the two handlers at
`0x19dcf20`/`0x19dcf40` are three instructions each - `cmp w1, #4`, `add x8, x0, w1, sxtw`,
then `strb w2, [x8, #0x100]` / `ldrb w0, [x8, #0x100]`. So they read and write a **u8 array
at `owner + 0x100 + row`, four rows wide**. The smallest next question is therefore not about
these two but about the writer: *which code path puts non-zero bytes into that `+0x100`
array, and is `0x19dd1a0` (`replace_skill`) or `0x19dd250` (`replace_skill_subwindow`) the
only writer?* That single question decides whether the selection survives leaving the
screen, and it is answerable offline by tracing stores to `owner+0x100..0x103`.

---

## Closing summary

- **Task ID:** P2-SKILL-NATIVE
- **Status:** DONE
- **Changed files:**
  - `research/P2-SKILL-NATIVE.md` (new, this file)
  - `evidence/P2-SKILL-NATIVE/` (new): `00_search_and_vtables.txt`,
    `01_reference_sites.txt`, `02_enclosing_function_0x19ddb30.txt`,
    `03_handler_windows.txt`, `04_invoke_thunks.txt`,
    `05_function_start_candidates.txt`, `06_input_identity.txt`, `07_claim_check.txt`
  - `scratch/2026-10-04_P2-SKILL-NATIVE/` (new): `d.py` (unmodified copy),
    `strfind.py`, `refscan.py`, `w.py`, `fstart.py`, `relocs.py`, `check_claims.py`,
    `windows.sh`, plus raw outputs
- **Verified checks:** input sha256 rehash matched; 174/174 address claims re-derived from
  the image with exit 0; the `post_fighter` control vtable reproduced exactly.
- **Unresolved / out of scope:** what the handlers do with their arguments; the flat image
  has no relocation header, so relocation lookup relies on a validated bare-record scan;
  no second registration site for any of the six names was sought or found within TEXT.
- **Next experiment:** trace stores into `owner + 0x100..0x103` to find the writer that
  outlives the screen (see above).
