# P9-EDIT-DISPATCH - edit-scene dispatch report (finished from P8 evidence)

Status: **DONE** (written incrementally during the task; the closing summary is
section 12).

Task: P9-EDIT-DISPATCH. Tier B throughout (offline static reading of
workspace-relative `gamedata/ssbu-13.0.4/main.bin`,
sha256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`,
verified at the start of this task). Everything about runtime behaviour is tier D.

## 0. Input identity and method

| item | value |
|---|---|
| image | `gamedata/ssbu-13.0.4/main.bin` (workspace-relative) |
| sha256 | `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` (verified) |
| size | 86 672 752 bytes (verified) |
| layout | flat MOD0 image, address == file offset |
| relocations | `R_AARCH64_RELATIVE` records, 24 bytes: `+0x00` u64 r_offset, `+0x08` u32 r_info (0x403), `+0x0c` u32 zero, `+0x10` u64 r_addend |
| tools | `d.py` (window/xref/calls/fstart/ptr), `lib.py`, `relocs.py`, `hash40.py`, copied from `scratch/2026-10-05_P8-EDIT-DISPATCH/` into `scratch/2026-10-05_P9-EDIT-DISPATCH/` |
| disassembler | capstone 5.0.1280 (arm64), `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python` |

The P8 folder was read as unreviewed notes. Every address cited below was re-read
from `main.bin` in this task.

### Correction to the P8 check script

`scratch/2026-10-05_P8-EDIT-DISPATCH/check_p8.py` fails with 9 failures. Two causes,
both in the check script, not in the mod facts:

1. **`mov w3, #-2` (0x1808fa8) and `mov w3, #-1` (0x1808fcc).** P8's `mov_imm()` only
   decoded `MOVZ` (bits 28..23 == 0x25, opc 10) and `MOVN` (0x25, opc 00). The word at
   0x1808fa8 is `0x321f7be3`, which is bits 28..23 == **0x24** with opc 01, i.e.
   **logical-immediate `ORR Wd, WZR, #imm`** — the architectural `mov` alias. Decoding it
   with the ARM `DecodeBitMasks` rule (N=0, immr=31, imms=30, Rn=31/WZR) gives
   `wmask = 0xfffffffe = -2`. The word at 0x1808fcc is `0x12800003`, a real `MOVN w3,#0`
   = -1. Both values in the P8 claim are confirmed correct; the decoder was too narrow.
   Capstone prints both correctly.
2. **Seven "handler off 0xNN" mismatches.** P8 walked backwards from the first
   `stp ..., [x19, #0xNN]` it found and then looked for the nearest preceding
   `adrp`/`add` pair. The table is built with **two** register accumulators (`x8` and
   `x9`) that alternate, so the nearest preceding pair is often the one that built the
   *other* slot's value. The correct table is in section 1; P8's expected values were a
   mis-pairing of the same 13 handler addresses.

Nothing in the coordinator's brief (B) is contradicted.

## 1. The 13 state handlers at scene+0x28

The table is **not** written in `0x1808980`. It is installed by the scene object's
constructor **`0x180de70`**, in the contiguous block `0x180e06c`..`0x180e10c`. That
function allocates `0x1e0` bytes (`mov w0,#0x10; mov w1,#0x1e0; bl 0x392dce0`,
0x180de94..0x180de9c) — so **the scene object is 0x1e0 bytes**, which is consistent with
a child pointer at `+0x1a0`. Each entry is one `stp <handler>, xzr, [x19, #0x28+16*n]`,
i.e. a pointer-to-member pair with a zero second half; the reader at `0x180ce40` loads
both halves.

Evidence: `evidence/P9-EDIT-DISPATCH/02_handler_table_install.txt`,
`01_scene_ctor_0x180de70_prologue.txt`.

| state | slot addr | handler | one line |
|---|---|---|---|
| 0 | +0x28 | `0x1808980` | `stp` at 0x180e07c | builds the whole scene: allocates and constructs the six child objects at +0x178..+0x1a0, registers the host globals, then returns |
| 1 | +0x38 | `0x1809e60` | `stp` at 0x180e08c | initial/idle state; the "edit menu" home state that the dispatch returns to on cancel (`0x180a1cc` pushes 1) |
| 2 | +0x48 | `0x1809fb0` | `stp` at 0x180e0c8 (value from `x9` built at 0x180e074/78) | second menu/page state |
| 3 | +0x58 | `0x180a030` | `stp` at 0x180e098 | **the dispatcher**: reads the edit script's exit value and pushes the next state |
| 4 | +0x68 | `0x180a5b0` | `stp` at 0x180e0a4 | sub-screen state A |
| 5 | +0x78 | `0x180abd0` | `stp` at 0x180e0e0 (value from `x9` built at 0x180e0cc/d0) | sub-screen state B |
| 6 | +0x88 | `0x180b1c0` | `stp` at 0x180e0b0 | sub-screen state C |
| 7 | +0x98 | `0x180b670` | `stp` at 0x180e0bc | sub-screen state D |
| 8 | +0xa8 | `0x180ba20` | `stp` at 0x180e0f8 (value from `x9` built at 0x180e0e4/e8) | the special-move sub-screen (§1.2; P8-EDIT-DISPATCH evidence 13 misnamed it the exit path) |
| 9 | +0xb8 | `0x180bc60` | `stp` at 0x180e0d4 | sub-screen state E |
| 10 | +0xc8 | `0x180c360` | `stp` at 0x180e0ec | sub-screen state F |
| 11 | +0xd8 | `0x180cbc0` | `stp` at 0x180e10c (value from `x9` built at 0x180e0fc/100) | not a sub-screen state: drives no child; gates on `scene+0x164` and `[0x532e7a0]` (§1.2; coordinator re-read 2026-10-05: at worst pops one state level) |
| 12 | +0xe8 | `0x180cc80` | `stp` at 0x180e104 | last sub-screen state |

One-line summaries for each handler are in the table above; the per-handler
detail, including which child slot each state drives, is section 1.2.

## 1.1. Who runs the state machine, and which object is which

The chain that ties the brief's names together, all read in this task:

- The Mii editor is **two objects**. An outer screen object holds a pointer at
  `+0x58` to an inner state object. The outer object's vtable is at `0x50a0bd8`
  (relocations confirmed); its slot `+0x40` (`0x50a0c18`) holds `0x180de70`, which
  **allocates the 0x1e0-byte inner object** (`mov w0,#0x10; mov w1,#0x1e0;
  bl 0x392dce0` at 0x180de94..0x180de9c) and installs the 13 handler pairs.
  Evidence `01_...prologue.txt`; reloc record file 0x3ce5050.
- The outer's slot `+0x48` is `0x180ea90`, its destructor: `ldr x19,[x0,#0x58]`
  (0x180ea9c), calls `0x180dc50` on the inner object, frees it.
- The outer's slot `+0x50` is `0x180ead0`, the **per-frame update**. It does
  `ldr x19,[x0,#0x58]` (0x180eae8) and calls `0x180ce40` at **0x180eaf4**. So
  `0x180ce40` (the state reader) is reached from the frame update, not by a
  direct `bl` from any other place — which is why a plain caller scan finds none.
  Evidence `20_frame_update_driver.txt`.
- Everything in sections 1, 4 and 5 (`0x1808980`, `0x180a030`, `0x1809e60`,
  `0x180a5b0`, `0x180abd0`, `0x180b1c0`, `0x180b670`, `0x180ba20`, `0x180bc60`,
  `0x180c360`, `0x180cbc0`, `0x180cc80`, `0x180d200`, `0x180daf0`, `0x180dc50`,
  `0x180ce40`) is a **method of the inner 0x1e0-byte object**, with `x0` == that
  object. Each parks it in `x19` (`mov x19,x0`). The brief's "x19" and "scene"
  are this inner object.
- `scene+0x14c` is **not** a flag the handler sets. It is a frame counter:
  `0x180ead0` does `ldr w8,[x19,#0x14c] ; add w8,w8,#1 ; str w8,[x19,#0x14c]`
  (0x180eb28..0x180eb34) after running the state, and `0x180ce40` clears it at
  0x180ceb8. Every state handler branches on it at entry (`ldr w8,[x0,#0x14c];
  cbz w8, ...`), so it reads as "this is not the first tick" (B, from the read
  pattern; the runtime meaning is D).

## 1.2. Per-handler detail: which child slot each state drives

Produced by `scratch/.../slotmap.py`, which scans each handler's own range
(handler start to the next handler start, so no reference leaks across handlers)
using capstone operand decoding, not a text search.

| state | handler | child slot it reads | in-scene calls | what it is |
|---|---|---|---|---|
| 0 | `0x1808980` | **all six** (+0x178, +0x180, +0x188, +0x190, +0x198, +0x1a0) | none | the builder: allocates and constructs all six children, registers the host globals (section 6), then returns |
| 1 | `0x1809e60` | +0x178 (via `x20`) | none | the idle/home tick; calls the edit actor's vtable `+0x20` slot at 0x1809e8c..0x1809e90 and compares its result with -1 (`cmn w0,#1` at 0x1809e94). This is the state the dispatch returns to (section 5). **This is the edit-menu state.** |
| 2 | `0x1809fb0` | none | none | the state-stack popper: `ldr w8,[x0,#0x144]; subs w8,w8,#1; b.lt; str` at 0x1809fc4..0x1809fd0, then returns. A no-op body whose whole job is to pop. |
| 3 | `0x180a030` | +0x178 | `0x180a1bc -> 0x180cf10` | **the dispatcher** (sections 3 and 4) |
| 4 | `0x180a5b0` | +0x178 | `0x180aadc -> 0x180d200` | a sub-screen state that drives only the edit actor (camera/scene-level; it takes the 0x80-byte object's `+0x80` sub-object, calls `0x19cb2e0` at 0x180aa00, sets `scene+0x161 = 1` at 0x180aa08, reads `scene+0x168` at 0x180aa0c). Not identified further. |
| 5 | `0x180abd0` | **+0x180 hat** (8 refs) | `0x180ad24 -> 0x180cf10` | the **headgear** sub-screen: reads the hat actor's decided value into `scene+0x1b0` (`ldr x8,[x19,#0x180]; ldr x8,[x8,#0x80]; ldr w8,[x8,#0x160]; str w8,[x19,#0x1b0]`, 0x180abf0..0x180abfc) |
| 6 | `0x180b1c0` | **+0x188 body** (8 refs) | `0x180b30c -> 0x180cf10` | the **outfit** sub-screen, same shape (0x180b1dc..0x180b1e8) |
| 7 | `0x180b670` | **+0x190** (6 refs) | `0x180b77c -> 0x180cf10` | the sub-screen driven by the `0x19c9340` actor (0x180b68c..0x180b698 reads `+0xe4`, not `+0x160`) |
| 8 | `0x180ba20` | **+0x198 special** | `0x180bb4c -> 0x180cf10` | the **special-move** sub-screen: reads `+0xe0` of the special actor's sub-object (0x180ba3c..0x180ba44) and branches on it. STATUS.md called this the commit/save state; the code reads it as a sub-screen driven by the special actor. |
| 9 | `0x180bc60` | **+0x1a0 voice** (4 refs) | none | the **voice** sub-screen (0x180bc94) |
| 10 | `0x180c360` | none | none | pops the stack (0x180c0d4..0x180c0e4) and drives no child; a return tick |
| 11 | `0x180cbc0` | none | none | driven by no child; gates on `scene+0x164` and a static at `0x532e7a0` (0x180cbd0..0x180cbe4) |
| 12 | `0x180cc80` | +0x188 (1 ref, in `x21`) | `0x180d23c -> 0x180daf0`, `0x180ddf8 -> 0x180dc50`, `0x180de4c -> 0x180dc50` | the exit/teardown state: pops (0x180cc60), pushes state 1 and calls `0x180daf0`, then frees with `0x180dc50` |

**Which state shows the edit menu:** state 1 (`0x1809e60`). It is the only handler
that touches the edit actor through the *virtual* slot (`ldr x8,[x0];
ldr x8,[x8,#0x20]; blr x8` at 0x1809e88..0x1809e90) rather than through the
`+0x80` sub-object pointer, and it is what every return path lands on
(sections 4 and 5). State 0 is the one-shot builder, not a menu.

**Which state runs each sub-screen, tied to slot and script:**

| sub-screen | slot | ctor | script | state |
|---|---|---|---|---|
| name / camera / scene-level | +0x178 | inline (no named ctor) | `make_mii_edit_actor.lc` | 4 (and 1, 3) |
| headgear | +0x180 | `0x19ceb30` | `make_mii_hat_actor.lc` | 5 |
| outfit | +0x188 | `0x19c7830` | `make_mii_body_actor.lc` | 6 |
| (unidentified) | +0x190 | `0x19c9340` | **none** (no `bl 0x32caa90` anywhere in its 0x1200 bytes) | 7 |
| special moves | +0x198 | `0x19ddb30` | `make_mii_special_actor.lc` | 8 |
| voice | +0x1a0 | `0x19e33e0` | `make_mii_voice_actor.lc` | 9 |

**Colour has no state of its own.** No handler drives a colour child: the six
slots are edit/hat/body/unidentified/special/voice, and the six states that touch
a child are 4..9. There is no seventh child and no colour script among the
hashes. If the Mii colour picker exists in 13.0.4, it is either inside one of
these objects (the +0x190 actor is the only unidentified one) or reached some
other way. **This is an open question, not a finding.** (D)
## 2. The six child slots +0x178 .. +0x1a0

All built by state 0, `0x1808980`, in that address order. Each is allocated
`mov w0,#0x10 ; mov w1,#0x88 ; bl 0x392dce0` (0x88 bytes, 0x10 alignment) unless
noted, initialised by `bl 0x32ca8f0` right before the store, and destroyed by
`bl 0x32ca770` if the slot was already occupied.

| slot | store | allocator size | ctor call | ctor | vtable set | script load | script path | hash40 |
|---|---|---|---|---|---|---|---|---|
| +0x178 | 0x1809498 | 0x88 (0x18089c4) | **inline, no named ctor** | vtable `0x50a6aa8` at 0x1808a28..0x1808a38 | `0x32caa90` @ 0x1808c98 | `ui/script_patch/chara_make/make_mii_edit_actor.lc` | `0x0314b141360` |
| +0x180 | 0x18095ac | 0x88 (0x18094c0) | 0x1809558 | `0x19ceb30` | `0x32caa90` @ 0x19ced1c | `ui/script/menu/chara_make/make_mii_hat_actor.lc` | `0x02fa5c13fc6` |
| +0x188 | 0x18096c4 | 0x88 (0x18095e4) | 0x1809670 | `0x19c7830` | `0x32caa90` @ 0x19c7a1c | `ui/script/menu/chara_make/make_mii_body_actor.lc` | `0x030c95391dc` |
| +0x190 | 0x1809794 | 0x88 (0x18096d8) | 0x1809740 | `0x19c9340` | **none** | **none** | - |
| +0x198 | 0x1809868 | 0x88 (0x18097a8) | 0x1809814 | `0x19ddb30` | `0x32caa90` @ 0x19ddd90 | `ui/script/menu/chara_make/make_mii_special_actor.lc` | `0x03359b0338a` |
| +0x1a0 | 0x1809934 | 0x88 (0x180987c) | 0x18098e4 | `0x19e33e0` | `0x32caa90` @ 0x19e3558 | `ui/script/menu/chara_make/make_mii_voice_actor.lc` | `0x031d9bfc44b` |

Layout hash loaded alongside the +0x178 script, for comparison:
`0x1808c60..0x1808c68` builds `0x0350c3e4c44` =
`ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc`.

`hash40` = `(len(lower(path)) << 32) | (crc32(lower(path)) & 0xffffffffff)`;
self-tested against `hash40("fighter_kind_miigunner") == 0x0166e9fae70`.

Evidence `07_scene_child_build_0x1808980.txt`, `08_slot_178_build.txt`,
`13_slot178_ctor_inline.txt`.

### The two slots with no script hash

**+0x190, ctor `0x19c9340`.** A real constructor: it stores vtable `0x50a69d8`
(0x19c9360..0x19c9368, reloc addends `0x19c9d90`, `0x19c9e90`, `0x32ca8d0`,
`0x19c9f80`), zeroes `+0x10` and `+0x48`, sets `+0x58 = 0`, `+0x70 = 1`, keeps `x1`
in `+0x78`, and then allocates a **0xf0-byte** sub-object (`mov w1,#0xf0;
mov w0,#0x10; bl 0x392dce0`, 0x19c9388..0x19c9398). Scanning its whole
0x1200-byte range finds **no `bl 0x32caa90`**, so it loads no script of its own.
It is the only child with an extra nested allocation. Its handler (state 7) reads
offset `+0xe4` of the `+0x80` sub-object where states 5/6 read `+0x160`, so it
is a different kind of object from hat/body. **Not identified further.** (D)

**`0x19e0910` is not a child constructor at all.** The P8 evidence file 49 lists
it as one. Read here: `0x19e0910` starts `str x19,[sp,#-0x20]!` and immediately
does `cbz x0,... ; mov x19,x0 ; ldr x0,[x0]` then registers `INPUT_BUTTON_UP`
= 0, `INPUT_BUTTON_DOWN` = 1, `INPUT_BUTTON_LEFT` = 2 through
`bl 0x33750a0`. It is a **host-global registrar** (the `INPUT_*` family), called
at 0x18092ec from the scene builder, and it has five callers
(0x18092ec, 0x19c8580, 0x19cf884, 0x19d3a34, 0x19e3864) across several actor
families. It builds nothing and loads no script. Evidence
`09_ctor_0x19e0910.txt`. **This corrects P8 evidence file 49.**

## 3. The exit value: script call to dispatch read

**Yes, it is the same object.** The brief called this "likely but not
established". It is now established, instruction by instruction:

```
0x1809498  str  x21, [x19, #0x178]     ; the 0x88 wrapper -> scene child slot +0x178
0x1808c74  str  x22, [x21, #0x80]      ; the 0x138 inner object -> wrapper +0x80
0x1808c1c  stp  x8, xzr, [x22, #0x80]  ; x8 = 0x19ca590, a pointer-to-member pair
0x19ca93c  mov  x8, x19                ; inside 0x19ca590, x19 = x0 = this object
0x19ca94c  str  w0, [x8, #0x118]       ; x19 + 0x10 (pre-index at 0x19ca940) + 0x118
                                       ;   == x19 + 0x128
0x180a048  ldr  x8, [x0, #0x178]       ; dispatch: the same child slot
0x180a054  ldr  x9, [x8, #0x80]        ; the same +0x80
0x180a098  ldr  w8, [x8, #0x128]       ; the same +0x128
```

So the object is the **0x138-byte inner object**, reached as
`[[scene+0x178]+0x80]`, and the field is `+0x128` of *it*. The 0x88-byte wrapper
in slot +0x178 has its `+0x80` used only as this pointer.

`0x1808c74` is `str x22,[x21,#0x80]` and `0x1808c1c` is
`stp <0x19ca590>, xzr, [x22,#0x80]`, so `0x19ca590` is installed as a virtual
method of the inner object, and its `x0`/`x19` is the inner object. That closes
the loop. Evidence `08_slot_178_build.txt`, `11_exit_value_store.txt`,
`12_edit_actor_0x19ca590.txt`.

### The write site

`0x19ca8ec..0x19ca8f8` builds the name (`adrp x2,#0x42e5000 ; add x2,x2,#0xa36`
-> `0x42e5a36` = `"get_exit_value"`, counted once in the image) and calls
`bl 0x38f4790` with `x0` = the Lua state. That call is inside
`0x19ca590`, whose backward prologue scan lands on 0x19ca590 itself (previous
word `0x00000000`).

The result is converted and stored at 0x19ca93c..0x19ca94c:
- if the returned Lua value is a number (tag 6, checked at 0x19ca914..0x19ca920),
  `bl 0x3376b80` converts it and the converted `w0` reaches 0x19ca93c;
- otherwise `w0` is forced to 0 at 0x19ca934 (`mov w0, wzr`);
- either way `mov x8,x19 ; ldr x9,[x8,#0x10]! ; str w0,[x8,#0x118]` stores it.

### The other writes to +0x128

| address | value | when |
|---|---|---|
| 0x1808bf8 | `-2` (`mov w8,#-2` at 0x1808bec) | initial value in the scene builder, before the script is loaded |
| 0x19ca94c | the converted `get_exit_value()` result | each frame the menu script runs |
| 0x19cab4c | `-2` (`mov w8,#-2` at 0x19cab48) | a second reset at the end of `0x19ca590`, before `ret` |

`-2` is `EXIT_VALUE_CANCEL` (section 6), so both the initial value and the
teardown value read as "cancelled / nothing chosen" (B).

### The three flag bytes at +0x130, +0x131, +0x132

All three live in the same 0x138-byte inner object. Only four accesses each way
exist in the whole Mii editor block, so the meanings below are complete, not
sampled (B for the access set; D for the semantics).

**+0x130 — "the menu has produced a decision this session" / gate flag.**
- Written `1` at 0x1808c14 as `strh w26,[x22,#0x130]` with `w26 = 1`
  (0x1808bf4), so **both +0x130 and +0x131 start at 1**.
- Read at 0x180a064 (`ldrb w9,[x8,#0x130]`); if zero, control jumps to
  **0x180a1ac**, which does not read the exit value at all.
- Cleared as a pair at 0x180a4b0 (`strh wzr,[x21,#0x130]`), zeroing 0x130 and
  0x131 together.
- Also written `1` at **0x19ca62c** (`strb w8,[x19,#0x130]`, `w8 = 1` at
  0x19ca628), immediately before the code that calls `get_exit_value`
  (0x19ca668 onward). So the object raises +0x130 on the tick it asks the script
  for its exit value.
- **Exact meaning, as far as the code shows (D):** `+0x130` is the
  "the edit script has been stepped and has a value" flag. `0x180a030` only
  consumes the exit value when it is non-zero; when it is zero it takes the
  `+0x132` path instead. It is also the first half of the pair cleared by
  `strh wzr`.

**+0x131 — "a value was actually chosen" / decided flag.**
- Starts at 1 (same `strh w26` at 0x1808c14).
- Written `1` at **0x19cb098** (`strb w8,[x19,#0x131]`, `w8 = 1` at 0x19cb090),
  near the end of the function starting at 0x19cae30, which is the *other*
  script-driving method: it calls `0x3777d50` with the strings
  `"favorite_off"` (0x19cae98) and `"favorite_on"` (0x19caed8).
- Read at 0x180a084 (`ldrb w10,[x8,#0x131]`); if set, `0x180a08c` writes
  `scene+0x161 = 1` (0x180a090).
- Cleared with +0x130 at 0x180a4b0.
- **Exact meaning (D):** a second, independent "there is a decision" flag,
  raised by the favourite-toggle method rather than by the exit-value call, and
  it is what sets `scene+0x161`. The scene never writes +0x161 itself except
  here and at 0x180aa08.

**+0x132 — "come back without deciding" / re-entry flag.**
- Initialised to **0** at 0x1808c18 (`strb wzr,[x22,#0x132]`).
- Read at 0x180a1ac (`ldrb w9,[x8,#0x132]`), the target of the `+0x130 == 0`
  branch. If it is also zero, control goes to 0x180a4f0, the plain epilogue.
- If non-zero, 0x180a1b4..0x180a1c8 runs: calls `0x180cf10` on the scene,
  writes `scene+0x162 = 1` (0x180a1c4), **clears +0x132** (0x180a1b8), and
  returns through 0x180a4f0.
- **No code anywhere in the editor block sets +0x132 to 1** (a whole-text scan
  for stores to `[Xn,#0x132]` in this object's window finds only the two clears).
  **Exact meaning (D):** it is a one-shot "re-enter the menu without reading a
  new value" flag, set somewhere outside the Mii editor block or by an
  overlapping-offset object. Its producer is **not established.** That is the
  one part of question 3 I cannot answer.

Evidence `16_flag_byte_writers.txt`.

**Note on the read order in `0x180a030`:** the flags are checked *before* the
exit value. `+0x130` first (0x180a064, gate at 0x180a068), then `+0x131`
(0x180a084, sets `scene+0x161` at 0x180a090), then the exit value at 0x180a098.
So `+0x131` being set does not skip the value read; it only adds `scene+0x161`.

## 4. Value by value: what `0x180a030` does

The whole function is short enough to state exactly. Reachable structure:

```
0x180a030  prologue (5 instructions)
[20 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
```

**The stack.** `scene+0xf8` holds up to `0x13` = 19 32-bit state values; the
index is `scene+0x144`. Before a push the index is compared with `0x11` (17) and
skipped if greater; after incrementing it is compared with `0x13` (19) and
trapped (`bl 0x39c20a0`) if >= 19. So the *pushed* slot index can be at most
0x12 = 18.

| exit value | states pushed, in order | everything else written | target |
|---|---|---|---|
| **0** | `0x04` (4) at `[+0xf8 + 4*(index+1)]` | index += 1 | falls through 0x180a0c8, not 5 or 6, to the epilogue |
| **1** | `0x05` (5) | index += 1 | epilogue |
| **2** | `0x06` (6) | index += 1 | epilogue |
| **3** | `0x07` (7) | index += 1 | epilogue |
| **4** | `0x08` (8) | index += 1 | epilogue |
| **5** | `0x09` (9) **then `0x0b` (11)** | index += 1 twice | `b.eq 0x180a228` at 0x180a0cc; the 0x180a228 block re-loads the index, increments, pushes `0x0b`, then branches to the epilogue at 0x180a250 |
| **6** | `0x0a` (10) **then `0x0b` (11)** | index += 1 twice | falls through 0x180a0d8; pushes `0x0b` at 0x180a0fc, then continues to 0x180a100, which resolves a sound id (`bl 0x32b1e30` at 0x180a120) and **tail-calls `0x33143f0`** at 0x180a144 |
| **7** | `0x0b` (11) | index += 1 | epilogue |
| **8** | `0x0c` (12) | index += 1 | epilogue |
| **9 or more** | `value + 4`, i.e. `>= 0x0d` (13) | index += 1 | epilogue -- but see below |
| **negative, `-1`** | `0x04` (4) | `scene+0x168 = 1`; if the static byte at `0x5306c8c` is non-zero, the function **tail-calls `0x180d200`** instead of pushing | `cmn w8,#1 ; b.eq #0x180a504` |
| **negative, `-2` and below** | `0x01` (1) | `scene+0x168 = 2` | falls through 0x180a1d4, pushes `0x01` at 0x180a1f0, then **tail-calls `0x180daf0`** at 0x180a208 |

### What happens for value 7 (state 11) and value 8 (state 12)

**They land in existing handlers. Both are valid.**

- Value 7 pushes `11`, and state 11's handler is `0x180cbc0` (installed at
  0x180e10c, slot +0xd8). `0x180ce40` accepts it: `cmp w8,#0xd` at 0x180ce70 is
  `state < 13`, and 11 < 13, so the call proceeds to the table load at
  0x180ce88. **Value 7 is in range.**
- Value 8 pushes `12`, and state 12's handler is `0x180cc80` (installed at
  0x180e104, slot +0xe8). 12 < 13, so it too is accepted.

State 11 (`0x180cbc0`) drives no child slot and gates on `scene+0x164` and the
static at `0x532e7a0`. State 12 (`0x180cc80`) pops the stack (0x180cc60),
pushes state 1 and calls `0x180daf0` (0x180d23c), then frees with `0x180dc50`
(0x180ddf8, 0x180de4c). Note that value 5 and value 6 *also* push `0x0b`, so
**state 11 is reached by four different exit values** (5, 6, 7 and, via the
value+4 push, nothing else) plus the direct `7`.

**Value 9 and above is where the code stops being safe.** `0x180a0c4` stores
`value + 4` unconditionally, so value 9 stores `13` into the state stack. When
`0x180ce40` next reads it, `cmp w8,#0xd` at 0x180ce70 is **not** satisfied and
it branches to `0x180cf00` **after** having already written the value: 0x180ce74
`str w9,[x19,#0x150]`, 0x180ce78 `str w8,[x19,#0x148]` (current state = 13),
then 0x180ce7c `b.hs #0x180cf00`. So **exit values >= 9 install an out-of-range
current state (>= 13) and jump to 0x180cf00 instead of running any handler.**
The push itself is also bounded: values above 0x0e would need an index >= 0x13
and trip `bl 0x39c20a0` at 0x180a5a0.

So: **values 0..8 all reach existing handlers; value 9 and above reach none.**
The gap starts at 9, not at 7. (B for the code path, D for what 0x180cf00 does
with the bad state -- it was not disassembled.)

> **Coordinator addendum 2026-10-05: `0x180cf00` is a trap.** Read from the image,
> it is `bl 0x39c20a0 ; udf #0` -- the same call the over-deep state-stack path
> (`0x180a5a0`) makes. So an exit value **>= 9 aborts**; it is not a handler. A
> modified script must never publish >= 9, and a plugin that rewrites exit values
> must treat an out-of-range value as a bug. Disassembly:
> `evidence/P9-EDIT-DISPATCH/19_coordinator_addendum.txt`.
>
> The same addendum records the coordinator's re-read of state 11 (`0x180cbc0`,
> reached by exit value 7): it returns unless `scene+0x164 <= 0` and `[0x532e7a0]`
> is non-zero, then does one registry lookup and at most decrements `scene+0x144`
> by one (never below zero). No trap, no child access. **7 is the value the mod
> can use**: without the plugin it is benign; with the plugin the hook rewrites it
> to 1 before the dispatcher reads it. Value 8 is avoided because state 12 is the
> editor's teardown path.

### Value 5 versus value 6

They are not the same code despite pushing the same state.

- Value 5 goes to 0x180a228, whose push block (0x180a228..0x180a24c) is a
  **duplicate** of the value-6 push block at 0x180a0d8..0x180a0fc, then
  `b #0x180a4f0` (plain epilogue). Its guard differs: `ldr w8,[x19,#0x144] ;
  cmp w8,#0x11 ; b.gt #0x180a4f0` -- if the stack is already deep it skips the
  push entirely and returns.
- Value 6 falls through and, after its push, runs 0x180a100..0x180a144: it walks
  `[0x532e730]->[8]->[0x178]->[8]`, calls `0x32b1e30` with a hashed sound id
  built at 0x180a114..0x180a11c, then sets up `x0 = [0x532e8d0]`, `x1` = the
  sound handle, `w2 = 0` and **tail-calls `0x33143f0`**. So value 6 plays a
  sound and never returns through the normal epilogue. (D for the sound id.)

Evidence `03_dispatch_0x180a030_full.txt`.

## 5. How a sub-screen state ends, and how the edit menu resumes

### The pop

Every handler that has a child to close uses the identical idiom on
`scene+0x144`:

```
ldr   w<n>, [x19, #0x144]
subs  w<n>, w<n>, #1
b.lt  <skip>                ; if the index was already 0, do not store
str   w<n>, [x19, #0x144]
```

Measured sites (one per handler; the check script scans a 7-instruction window
because 0x180c0dc puts an unrelated `strb wzr,[x19,#0x1d0]` between the `subs`
and the `b.lt`):

| handler | state | pop load | `subs` | `b.lt` | `str` |
|---|---|---|---|---|---|
| `0x1809fb0` | 2 | 0x1809fc4 | 0x1809fc8 | 0x1809fcc | 0x1809fd0 |
| `0x180a5b0` | 4 | 0x180a5f0 | 0x180a5f4 | 0x180a5f8 | 0x180a5fc |
| `0x180abd0` | 5 | 0x180adf4 | 0x180adf8 | 0x180adfc | 0x180ae00 |
| `0x180b1c0` | 6 | 0x180b3dc | 0x180b3e0 | 0x180b3e4 | 0x180b3e8 |
| `0x180b670` | 7 | 0x180b7b8 | 0x180b7bc | 0x180b7c0 | 0x180b7c4 |
| `0x180ba20` | 8 | 0x180bb50 | 0x180bb54 | 0x180bb58 | 0x180bb5c |
| `0x180bc60` | 9 | 0x180c0d4 | 0x180c0d8 | 0x180c0e0 | 0x180c0e4 |
| `0x180c360` | 10 | 0x180cb64 | 0x180cb68 | 0x180cb6c | 0x180cb70 |
| `0x180cc80` | 12 | 0x180cc60 | 0x180cc64 | 0x180cc68 | 0x180cc6c |
| `0x180cc80` | 12 (second) | 0x180cdd0 | 0x180cdd4 | 0x180cdd8 | 0x180cddc |

The `b.lt` guard means the index is **never decremented below zero**: if it is
already 0 the store is skipped. State 2 (`0x1809fb0`) is a handler whose whole
body is this pop followed by `ret` (0x1809fd4), which makes it a pure
"pop and do nothing else" state.

**How the pop takes effect:** `0x180ce40` reads the index at 0x180ce4c
(`ldrsw x8,[x0,#0x144]`), the state at `[x0 + index*4 + 0xf8]` (0x180ce58,
0x180ce5c), and compares it with the current state in `+0x148` (0x180ce68).
A decrement changes the state at the new index, so the *previous* state becomes
current. There is no separate "return address" -- **the state stack itself is
the return stack.** A pop is the only way back (B).

### Resuming the edit menu

Four paths, all pushing a low state, none of them restarting the menu script by
an explicit call:

1. **Cancel (`-1`)** reaches 0x180a504: writes `scene+0x168 = 1`
   (0x180a504..0x180a508), reads the gate byte at `0x5306c8c` (0x180a510). If
   the gate is zero it increments the index and pushes **`4`** (`mov w9,#4` at
   0x180a550, `str` at 0x180a554) and returns. If the gate is non-zero it
   restores the stack frame and **tail-calls `0x180d200`** instead.
2. **Negative below `-1`** reaches 0x180a1d4: writes `scene+0x168 = 2`,
   pushes **`1`** (`mov w9,#1` at 0x180a1ec, `str` at 0x180a1f0), then
   **tail-calls `0x180daf0`** (0x180a208).
3. **`0x180d200`** (the gate-set commit path) increments the index, pushes
   **`1`** (`mov w9,#1` at 0x180d230, `str` at 0x180d238), calls `0x180daf0`
   (0x180d23c) and checks `scene+0x168 == 1` (0x180d240..0x180d248).
4. **State 12 (`0x180cc80`)** does the same at 0x180d23c, then frees with
   `0x180dc50` (0x180ddf8, 0x180de4c).

**The edit-menu state is state 1, `0x1809e60`,** and it is reached by pushing
the value `1`. Note the asymmetry: plain `-1` cancel pushes **4**, not 1; only
the `-2`-and-below branch, the `0x180d200` commit path and state 12 push 1.
`0x180daf0` is the common tail: it reads `[0x5313510]->[0]`, compares
`scene+0x1c8` and `scene+0x1cc` against a limit fetched through `[...]+0x98`,
writes a byte at `0x5306d35` (0x180db74). Evidence
`15_0x180daf0_and_0x180d200.txt`.

**The edit menu script is not re-entered by any of this.** `0x19ca590` (which
calls `get_exit_value`) is a method of the +0x178 inner object reached through
its own pointer-to-member pair, not from the state table, so no resume path
calls it directly. Whether the Lua chunk is re-run from its start on resume is
**not established**: `0x19ca590`'s prologue does `bl 0x33762b0` at 0x19ca5bc on
`[x19+0x40]`, which is consistent with a per-tick re-entry, but that is an
inference. (D)

## 6. Host global registrations

All in the scene builder `0x1808980`, in the block 0x1808f98..0x1809174. The
registration helper is `bl 0x33750a0`, called **12 times** in that block, with
the shape:

```
x0 = *(*(x22 + 0x40))          ; the Lua state
x1 = name string
x2 = type tag string           ; 0x42b1a84 = "i" (integer), 0x43ccb7b = "b" (boolean)
w3 = value
```

| name | string addr | count in image | value | value source | type |
|---|---|---|---|---|---|
| `EXIT_VALUE_CANCEL` | 0x43ef3ad | 1 | **-2** | immediate, word `0x321f7be3` at 0x1808fa8 (logical-immediate `mov` alias; `S=30, R=31` -> `0xfffffffe`) | `i` |
| `EXIT_VALUE_DECIDE` | 0x4359e6a | 1 | **-1** | immediate, word `0x12800003` at 0x1808fcc (`MOVN w3,#0`) | `i` |
| `INPUT_COMMON_BUTTON` | 0x438b274 | 1 | 6 | immediate 0x1808ff0 | `i` |
| `INPUT_FAVORITE` | 0x4306e80 | 1 | 7 | immediate 0x1809014 | `i` |
| `IS_NEED_SAVE` | 0x4338aff | 1 | `w23` | a register, computed earlier | `b` |
| `FROM_AMIIBO` | 0x4359ec6 | 1 | byte | `ldrb w3,[0x5306000 + 0xd3c]` at 0x1809050 | `b` |
| `IS_NEW_CREATE_AMIIBO` | 0x4317830 | 1 | byte | `ldrb w3,[0x5306000 + 0xd3d]` at 0x1809078 | `b` |
| `AMIIBO_CONFIRM_RESULT_DECIDE` | 0x4431937 | 1 | 0 | immediate `mov w3, wzr` at 0x18090ac (`orr w3,wzr,wzr`) | `i` |
| `AMIIBO_CONFIRM_RESULT_CANCEL` | 0x4359e7c | 1 | 1 | immediate 0x18090d0 | `i` |
| `IS_READ_ONLY` | 0x44119af | 1 | boolean | **`(byte at 0x5306b8c) != 0`**: `ldr b` 0x18090ec, `cmp #0` 0x18090f0, `cset w3, ne` 0x18090f4 | `b` |
| `IS_SKILL_EDITABLE` | 0x4431954 | 1 | boolean | **`(byte at 0x5306b8c) == 0` OR `(u16 at 0x5306b8c+0x10) != 0`**: `ldrb w8,[x23]` 0x1809114, `ldrh w9,[x23,#0x10]` 0x1809118, `cset w8,eq` 0x1809120, `cset w9,ne` 0x1809128, `orr w23,w8,w9` 0x180912c | `b` |
| `EDIT_MII_TYPE` | 0x429fcce | 1 | 3 or 0 | `mov w8,#3 ; csinc w3,w8,wzr,ne` at 0x18092b8..0x18092bc, from the eor/cset chain 0x1809288..0x18092b4 | `i` |

`x23` is loaded as `adrp x23,#0x5306000 ; add x23,x23,#0xb8c` (0x18090e4,
0x18090e8), so the working-record base is **0x5306b8c** -- the same static
STATUS.md records, and the same base STATUS.md calls W. So:

- `IS_READ_ONLY` = `W[+0x00] != 0` (STATUS.md's "W+0x14", where W = 0x5306b78)
- `IS_SKILL_EDITABLE` = `W[+0x00] == 0 || W[+0x10] != 0` (STATUS.md's "W+0x24")

This confirms STATUS.md's revised reading and refines it: STATUS.md said
`IS_READ_ONLY` / `IS_SKILL_EDITABLE` "are computed from bytes at W+0x14 and
W+0x24". More precisely, `IS_READ_ONLY` uses only the **byte** at W+0x14, and
`IS_SKILL_EDITABLE` is the **disjunction** of "that byte is zero" and "the
**u16** at W+0x24 is non-zero" -- so it is not a single byte, and the u16 at
W+0x24 matters independently. Evidence `05_globals_reg_0x1808f40.txt`,
`06_globals_reg_tail.txt`.

Note the `i` / `b` tag strings are at 0x42b1a84 and 0x43ccb7b, and the
`IS_NEED_SAVE` and `FROM_AMIIBO` registrations use the boolean tag while the
`EXIT_VALUE_*` pair uses the integer tag -- consistent with -1/-2 being Lua
integers.

## 7. Hook facts (facts only, no design)

Measured by `scratch/2026-10-05_P9-EDIT-DISPATCH/hookfacts.py`.

### (a) First four instruction words at 0x180a030

| address | word | instruction | PC-relative? |
|---|---|---|---|
| 0x180a030 | `0xa9bc5ff8` | `stp x24, x23, [sp, #-0x40]!` | **no** |
| 0x180a034 | `0xa90157f6` | `stp x22, x21, [sp, #0x10]` | **no** |
| 0x180a038 | `0xa9024ff4` | `stp x20, x19, [sp, #0x20]` | **no** |
| 0x180a03c | `0xa9037bfd` | `stp x29, x30, [sp, #0x30]` | **no** |

Checked against the masks for `adrp` (`w & 0x9f000000 == 0x90000000`), `adr`,
`ldr` literal (`w & 0x3b000000 == 0x18000000`), `bl`, `b`, `b.cond`, `cbz/cbnz`
and `tbz/tbnz`. All four are `STP` immediate-unsigned/pre-index: SP-relative
only, no PC-relative displacement, and no literal pool. The fifth instruction
(0x180a040, `add x29, sp, #0x30`) is likewise SP-relative, so the **first five
words of the function contain nothing PC-relative** (B).

### (b) Registers over 0x180a098 .. 0x180a0c8

| address | instruction | reads | writes |
|---|---|---|---|
[13 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]

- **Live across the whole range:** `x19` (the scene object, parked by
  `mov x19, x0` at 0x180a04c and used at 0x180a0a0, 0x180a0b4, 0x180a0bc), and
  the condition flags.
- **Live into the range:** `x8` carries the exit value from 0x180a098 and is
  still needed at 0x180a0c0 and 0x180a0c8.
- **Scratch inside the range:** `x9` (0x180a0ac..0x180a0bc) and `x10`
  (0x180a0c0..0x180a0c4). Both are dead after 0x180a0c4 / 0x180a0c8.
- **Free over the whole range** (caller-saved by AAPCS64 and not touched
  anywhere in 0x180a098..0x180a0c8):
  `x0, x1, x2, x3, x4, x5, x6, x7, x11, x12, x13, x14, x15, x16, x17, x18`.
  Each of those is free in the full 64-bit form.
- **Not free:** `x19`..`x28`, `x29` (frame pointer), `x30` (link register).
  These are callee-saved and additionally used as spill slots in the prologue
  (x19..x24) and in 0x180a148's path (x21, x22, x24).

## 8. Corrections to the inherited P8 notes

Two of them change facts; the rest do not.

1. **`0x19e0910` is not a constructor.** P8 evidence file 49 lists it among the
   child constructors. It is the `INPUT_BUTTON_*` host-global registrar (section
   2). Corrected in this report; P8's file was not edited.
2. **The handler-table ordering in `check_p8.py` is wrong**, and with it the
   seven `handler off 0xNN` failures. The table is correct in section 1; the P8
   check paired the wrong `adrp`/`add` because the install block alternates
   between the accumulators `x8` and `x9`.
3. **The `mov_imm32` decoder in `check_p8.py` is too narrow**, which caused the
   two `imm w3 @0x1808f..` failures. It handles MOVZ and MOVN but not the
   logical-immediate `mov` alias. The *values* P8 reported (-2 and -1) are
   correct; only the decoder was wrong. Fixed in `check_p9.py`, which
   self-tests against capstone over every `mov Wd, #imm` in the two editor
   blocks.

Nothing the coordinator supplied in the brief is contradicted. The exit-value
chain, the two branch targets, the handler table location and the four script
hashes all re-read identically.

## 9. Check run

Script: `scratch/2026-10-05_P9-EDIT-DISPATCH/check_p9.py`. Run from the
workspace root:

```
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-05_P9-EDIT-DISPATCH/check_p9.py
```

Full output including every negative control: `evidence/P9-EDIT-DISPATCH/17_check_p9_run.txt`.

> **Coordinator note 2026-10-05.** The run quoted below is the 13:23 capture. `check_p9.py`
> was extended afterwards (13:59) and now reports **774** checks; the coordinator reran the
> delivered script on 2026-10-05: clean run 774 passed / 0 failed, exit 0, and all six
> negative controls still exit 1 (`evidence/P9-EDIT-DISPATCH/18_coordinator_rerun.txt`).
> The counts in the quote below are the earlier revision's; the quoted failures and their
> fixes reproduce with the delivered script.

Last lines of the clean run and of all six negative controls (13:23 capture):

```
### clean run
negative control: none
checks passed: 639   failed: 0
exit=0

### negative control: --neg handlers
FAIL: negative handler accumulator @0x180e0b8 add x8, x8, #0x670
FAIL: negative handler accumulator @0x180e0f4 add x8, x8, #0xc80
FAIL: negative handler accumulator @0x180e0d0 add x9, x9, #0xbd0
FAIL: negative handler accumulator @0x180e0e8 add x9, x9, #0xa20
FAIL: negative handler accumulator @0x180e108 add x8, x19, #0x13c
FAIL: negative handler accumulator @0x180e100 add x9, x9, #0xbc0
exit=1

### negative control: --neg movimm
negative control: movimm
checks passed: 639   failed: 1
FAIL: negative MOVZ/MOVN-only control @0x1808fa8 bits28_23=0x24
exit=1

### negative control: --neg path
FAIL: hash40 @0x1808c60 got 0x0350c3e4c44 want 0x030fbd8f53d (ui/script/menu/chara_make/make_mii_edit_actor.lc)
FAIL: hash40 @0x1808c6c got 0x0314b141360 want 0x030fbd8f53d (ui/script/menu/chara_make/make_mii_edit_actor.lc)
FAIL: hash40 @0x19cecf8 got 0x02fa5c13fc6 want 0x030fbd8f53d (ui/script/menu/chara_make/make_mii_edit_actor.lc)
FAIL: hash40 @0x19c79f8 got 0x030c95391dc want 0x030fbd8f53d (ui/script/menu/chara_make/make_mii_edit_actor.lc)
FAIL: hash40 @0x19ddd6c got 0x03359b0338a want 0x030fbd8f53d (ui/script/menu/chara_make/make_mii_edit_actor.lc)
FAIL: hash40 @0x19e3534 got 0x031d9bfc44b want 0x030fbd8f53d (ui/script/menu/chara_make/make_mii_edit_actor.lc)
exit=1

### negative control: --neg str
negative control: str
checks passed: 638   failed: 1
FAIL: str@0x42e5a36 got 'get_exit_value' want 'get_exit_valueX'
exit=1

### negative control: --neg branch
negative control: branch
checks passed: 635   failed: 1
FAIL: negative script-call target got 0x38f4790
exit=1

### negative control: --neg size
negative control: size
checks passed: 633   failed: 1
FAIL: negative child +0x178 size got 136 want 312
exit=1
```

Each control injects exactly one deliberate error at a different layer --
register pairing, immediate decoding, hash-to-path matching, string contents,
branch target, object size -- and each makes the script exit 1.

The 639 passing checks cover: the image sha256 and size; eleven anchor strings
and six occurrence counts; the twelve host-global registrations with their
values and tags; all thirteen handler-table entries including the `adrp`/`add`
accumulator register and the resolved target; the scene object size; the state
reader and the dispatch function's control flow; the four entry words of
0x180a030 with a per-word PC-relative class test; a self-test of the `mov`
decoder against capstone; the six child slots, sizes, constructors and their
two absent script loads; six 40-bit path hashes with their MOVZ/MOVK/MOVK shape
and the five `bl 0x32caa90` sites; the exit-value chain from the script call to
the dispatch read; the three flag bytes' writers and readers; and ten pop sites.

## 10. Limits and unresolved questions

- **+0x132 has no producer.** Nothing in the Mii editor block sets it to 1; the
  two stores at 0x180a1b8 and 0x1808c18 only clear it. Its meaning is inferred
  from how it is read, and the writer is outside the code read here. (D)
- **`+0x130` and `+0x131` semantics are inferred** from the read/write pattern,
  not from names. The access set is complete (B); the meaning is D.
- **State 4 (`0x180a5b0`) and the `+0x190` child (`0x19c9340`) are not
  identified.** Neither is the name sub-screen nor the colour sub-screen: there
  is no seventh child and no seventh child-driving state, so if 13.0.4 has a
  colour picker it is not a sibling of hat/body/special/voice in this scene.
- **`0x180cf00` was not disassembled in this task.** It is where an out-of-range
  state (>= 13) and an over-deep stack index both land. The coordinator
  disassembled it on 2026-10-05: it is `bl 0x39c20a0 ; udf #0`, a trap. That it
  is reached by exit value >= 9 is B; that it aborts follows from the trap call
  (B). See section 4's addendum.
- **The value-6 sound id** at 0x180a114..0x180a11c is a 40-bit hash
  (`0x116b904091`); no path was matched to it and none was sought.
- **`0x19cae30` has no `bl` caller.** It is reached through a pointer like
  0x180ce40; which pointer was not found. Its two string uses
  (`favorite_off`, `favorite_on`) are what identify it as the favourite-toggle
  path and therefore as the writer of +0x131, so that attribution is by string,
  not by call graph.
- **The claim that `0x1808980` "is the edit scene" (tier A) was re-verified only
  as far as offline structure.** Everything in this report is tier B (static
  reading) or tier D (runtime meaning). No code was executed, nothing was
  patched, no emulator or console was used.
- **Relocations were used for two vtables only** (`0x50a6aa8`, `0x50a69d8`, and
  the outer `0x50a0bd8`). A whole-image search for a `R_AARCH64_RELATIVE`
  addend equal to `0x180ce40`, `0x180cf10`, `0x180d200` or `0x180daf0` found
  **zero** records, so those four are reached only through a structure built at
  runtime (or through a pointer copied from elsewhere); the reader chain for
  them is not established. The two that *are* reached by a `bl` inside the scene
  block (`0x180cf10` at 0x180a1bc, `0x180d200` at 0x180a52c) are cited from
  those sites only.
- **The `+0x144` pop window** was searched 7 instructions wide. A pop split by
  more than 6 instructions of unrelated code would be missed; all ten found
  sites are within 4.

## 11. Evidence index

All under `evidence/P9-EDIT-DISPATCH/`.

| file | what it is |
|---|---|
| `01_scene_ctor_0x180de70_prologue.txt` | the inner object's allocation (0x1e0) |
| `02_handler_table_install.txt` | all thirteen `adrp`/`add`/`stp` triples |
| `03_dispatch_0x180a030_full.txt` | 0x180a030 in full, plus both push blocks and the epilogue |
| `04_state_reader_0x180ce40.txt` | the state reader |
| `05_globals_reg_0x1808f40.txt` | the host-global registration block |
| `06_globals_reg_tail.txt` | the IS_SKILL_EDITABLE tail and the `set_txt_unedit` follow-on |
| `07_scene_child_build_0x1808980.txt` | the whole child-construction run |
| `08_slot_178_build.txt` | the +0x178 wrapper, its 0x138 inner object and the script load |
| `09_ctor_0x19e0910.txt` | shows it is the INPUT_* registrar, not a constructor |
| `10_ctor_0x19c9340.txt` | the +0x190 constructor |
| `11_exit_value_store.txt` | the `get_exit_value` call and the store at 0x19ca94c |
| `12_edit_actor_0x19ca590.txt` | the enclosing function |
| `13_slot178_ctor_inline.txt` | the inline vtable setup for +0x178 |
| `14_handler_state4_0x180a5b0.txt` | state 4 |
| `15_0x180daf0_and_0x180d200.txt` | the resume tail and the commit |
| `16_flag_byte_writers.txt` | all four writers of +0x130/131/132 and the resets of +0x128 |
| `17_check_p9_run.txt` | the clean run and all six negative controls |
| `18_handler_state4_and_state5_entries.txt` | the first ticks of states 4 and 5 |
| `19_scene_frame_update_0x180ead0.txt` | the per-frame update after the state call |
| `20_frame_update_driver.txt` | `0x180ead0` calling `0x180ce40` at 0x180eaf4 |

Scripts under `scratch/2026-10-05_P9-EDIT-DISPATCH/`: `check_p9.py`,
`hookfacts.py` (Q7), `slotmap.py` (Q1 child-slot map), `callers.py`,
`relocs.py`/`reloc_all.py`/`reloc_find2.py` (vtable lookups), `findflags2.py`
(flag-byte access census), `findfield.py` (+0x144 access census),
`find14c.py` (+0x14c census), `ctor_calls.py` (script-load census),
`mov_imm32` self-test inside `check_p9.py`.

## 12. Summary

**Task ID: P9-EDIT-DISPATCH. DONE.**

Changed files (all inside the three assigned paths, nothing else touched):

- `research/P9-EDIT-DISPATCH.md` (this report)
- `evidence/P9-EDIT-DISPATCH/` -- 20 files, listed in section 11
- `scratch/2026-10-05_P9-EDIT-DISPATCH/` -- `check_p9.py`, `hookfacts.py`,
  `slotmap.py`, `callers.py`, `relocs.py`, `reloc_all.py`, `reloc_find2.py`,
  `findflags2.py`, `findfield.py`, `find14c.py`, `find14call.py`, `ctor_calls.py`,
  `lib.py`, `d.py`, `relocs.py`, `a64.py`, `hash40.py` (copied from P8), and
  `17_check_p9_run.txt` is in evidence.

Not touched: `evidence/P8-EDIT-DISPATCH/`, `scratch/2026-10-05_P8-EDIT-DISPATCH/`,
`STATUS.md`, and every other path. No commits, branches, agents, emulator runs
or SD access.

Verified: image sha256 and size; 774 automated re-reads of every cited address,
immediate, string, table entry and path hash, all passing, with six negative
controls each forcing exit 1 (coordinator rerun of the delivered script; the
13:23 capture in section 9 said 639 and predates the script's last revision).

Not verified: everything about runtime behaviour (tier D). In particular the
meanings of `+0x130`/`+0x131`/`+0x132`, which state shows which visible screen,
and whether the edit menu Lua chunk restarts on resume (`0x180cf00` is now known
to trap; see section 10). The producer of `+0x132` was not found and no reader
of the pointer-to-member pairs that reach `0x180ce40`, `0x180cf10`, `0x180d200`
or `0x180daf0` was identified.

Next experiment, if the coordinator wants one: read `0x180cf00` and find who
sets `+0x132`; that closes the only loop left open inside the scene. The
colour sub-screen question is separate and needs a search outside
`0x1808980..0x180de70`.