# 0.12.2: up air is blocked, and it is not a bug in the port (Claude, 2026-09-29)

**Up air does not spawn the breath projectile. It is disabled deliberately, and
this is the evidence for why.** The card has a build that does not crash.

## The result, in one line

G&W's breath projectile cannot be constructed on a Pyra-owned agent. Its
construction is native game code that reads a pointer which is only ever set when
the owner is G&W, and it dereferences it without checking. It is the same wall the
project already documented for the props' removal rule, and it is not reachable by
any change to the move script.

## What the null pointer actually is (measured)

**It is the game's frame/time state object, and the field is not fighter-owned.**

One of the three engine-side readers names it. At `0x33fb934`:

```asm
033fb934: ldr x8, [manager, #0x690]
033fb940: ldr x9, [x8, #0x100]      ; a frame stamp
033fb944: str x9, [sp]
033fb948: ldr x8, [x8, #0x108]      ; another frame stamp
033fb94c: subs x8, x8, x9           ; delta
033fb950: mov x9, #0x6db7 ...       ; 0x6DB6DB6DB6DB6DB7
033fb964: mul x8, x8, x9            ; divide by 10 - frames to ticks
033fb96c: b.eq #0x33fb984
033fb970: ldr x8, [x0]; ldr x8, [x8, #0x78]; blr x8   ; push it into the object
```

Two frame stamps, their difference divided by ten: this is a **frame/timing
tracker**, and `+0x118` / `+0x11c` - the two floats the puff's setup reads - are
fields of *it*. So the breath's "default launch" is being read out of the match's
timing state, unconditionally.

### Why this reframes the problem

* The engine has **three** readers of this field and they are on the per-frame
  path, so during a live match the field is **not** null - if it were, the game
  would crash constantly with no mod involved.
* There are **five** known readers in total (the scan's strict 3-instruction
  pattern found four and missed the faulting one, which has an extra instruction
  between the two loads). **Two of the five are G&W article helpers** - `0xa80d70`
  and the faulting `0x33fc110` - and both dereference it with no check.

So the game has three always-executed readers that would fault on a null, and a
normal match never faults. The field is therefore populated in normal play. In
the crash it was not. Since the user confirms **real G&W's up air works on this
card** (in a different match, same NRO installed), our mod is not globally
breaking the timing object.

That leaves two live hypotheses, and they are now much narrower than before:

1. **The field is momentarily null when our eflame-owned weapon article is
   created** - i.e. the article is being built in a phase where the match timing
   state is not yet up. This is the good case and it is fixable in our own code,
   by spawning later or by finding what the phase requires.
2. **The second `clone_weapon` has a side effect** that perturbs the manager
   during boot. `get_static_fighter_data` (0x64b730) leaks a fresh allocation on
   every call, so a second registration means a second, differently sized table -
   worth ruling out, and it would also be a latent bug on its own.

**The test that separates them is one match, and it is now safe to run** because
up air spawning is disabled in 0.12.2 and cannot crash: put **real G&W and Pyra
c06 in the same match** and use G&W's up air there. If it works, hypothesis 1 (or
2) is about our article, not about a globally broken manager, and the next step
is to log the field's value at spawn time rather than guess.

## The faulting instruction, and the assets are already done

The faulting helper starts at `0x33fc110`:

```asm
033fc12c: adrp     x8, #0x52bb000
033fc130: ldr      x8, [x8, #0x3b0]     ; a core manager, alive
033fc13c: ldr      x24, [x8, #0x690]    ; <-- a SUB-POINTER of it, null
...
033fc180: add      x8, x24, #0x11c
033fc188: ld1      {v0.s}[1], [x8]      ; faults at 0x11c
```

So it is **not** a lookup keyed on the owner, and it is **not** a battle-object
id. `x24` is one global field: `*( *(0x52bb3b0) + 0x690 )`.

* `0x52bb3b0` is past `0x52A8C50`, which is where `.bss` starts, so it is a
  runtime-initialised global, not static data.
* The manager it points at is read **2747** times across `.text` (at offsets
  `0x50`, `0x188`, `0x428`, `0x690`, `0x770`, `0x7a8`, `0x7e0`, `0x968`, `0x980`,
  `0x1378`, `0x14c8`, ...), so the manager itself is definitely alive. Only the
  one sub-pointer at `0x690` is null.
* `0x690` has exactly **four** readers in the whole binary: `0xa80d90`,
  `0x33fb934`, `0x33fd554`, `0x33fe88c`. One of the four is **another G&W
  article helper** (`0xa80d70`), and it has the identical unchecked pattern:

  ```asm
  00a80d90: adrp     x8, #0x52bb000
  00a80d94: ldr      x8, [x8, #0x3b0]
  00a80d98: ldr      x8, [x8, #0x690]    ; same field
  00a80da4: ldr      x22, [x8, #0x1e0]   ; would fault identically
  ```

  So this is a shared dependency of G&W's *articles*, not of one move. Every
  G&W article that needs it will fail the same way, which is why forward air's
  `bomb` is very likely to fail identically and should not be attempted first.

The function uses the sub-object to fetch two default floats (`+0x118`,
`+0x11c`) and then applies a launch to the article through vtable calls
(`0x368`, `0x370`, `0x4f8`, and `0x428` three times). It is the article's
"default launch" setup, and it assumes the sub-object is always there.

## The evidence

Two console crashes, `atmosphere/crash_reports/01790701295` (0.12.0,
`use_original_code = false`) and `01790702259` (0.12.1, `= true`). They are the
same call chain, base addresses aside:

```text
Type: Data Abort, fault address 0x11c, faulting address +0x11c

pyra_gamewatch_reskin + 0x64a8     game_attackairhi -> generate_article
  cross2 + 0x3d41a8
  cross2 + 0x3d4114
  cross2 + 0x3a7000
  cross2 + 0xa80738                 G&W's breath init callback (0xa805a0)
  cross2 + 0x33a1208
  PC cross2 + 0x33fc188
```

`0xa80738` is the instruction after the call at `0xa80734`, inside the article
init callback at `0xa805a0` - which `scratch/maindesc.py 28` reports as G&W's
article [6]: `weapon 126, max 2, init 0xa805a0, fini 0xa807f0`.

The faulting instruction is

```text
033fc180: add      x8, x24, #0x11c
033fc184: add      x22, x24, #0x118
033fc188: ld1      {v0.s}[1], [x8]      <-- PC, faults
```

and the fault address is `0x11c`, so **`x24` is null**: it is dereferencing
`null + 0x11c`. `x24` is set up by the caller and is one of the objects the init
path looks up from the owner.

The same helper is called twice in this init, and the difference between the two
call sites is the whole story:

```text
00a805c8: bl  #0x3ac560      <- first call, result IS checked
00a805cc: cbz x0, #0xa805dc
...
00a80724: bl  #0x3ac560      <- second call, result used unchecked
00a80728: ldr x8, [x0]
```

`0x3ac560` is a battle-object-id resolver: it takes `id >> 28` as a category,
`(id >> 16) & 0xFFF` as a slot, compares the slot against a per-category count and
**returns null when the slot is out of range**. `normal_weapon`'s init handles the
null (it falls through to a global at `0x52b6000 + 0xf8`) and works fine on
eflame, which is why the stool and the fishbowl appear. `breath`'s init does not,
because on a G&W owner the lookup never fails and the author never had a reason to
check.

## Why `use_original_code` was not the fix, and what it did tell us

0.12.1 changed the flag to `true`, on correct reasoning: `breath` is one of the
articles with real donor status code (`lua2cpp_gamewatch/gamewatch_breath/
AttackAirHi.txt` - three shrinking hitboxes then a strong one, and that is the
damage up air does), so the article genuinely needs G&W's script module loaded.
That reasoning stands and the flag is left on.

It changed nothing because the crash is in **object creation**, which happens
before any script is looked up. The identical stack in both reports proves it.
The flag is still correct to have on, and it will be needed once creation works.

## The assets are finished, and proven loaded - do not redo them

The projectile is **already copied into Pyra's namespace**, byte for byte, and it
is on the card now. Verified in place:

```text
/f/ultimate/mods/pyra_gamewatch_reskin/fighter/eflame/
  model/breath/c00..c07    16 files each (c03,c04,c05,c07 have 15 - see build.py)
  motion/breath/c00..c07    3 files each: motion_list.bin, update.prc,
                                      c05attackairhi.nuanmb
```

`cmp` against the donor export: `model/breath/c06/model.numshb` and
`motion/breath/c06/c05attackairhi.nuanmb` are both **byte-identical** to G&W's.

**They are proven to load.** The engine loads every cloned article's model while
it initialises the fighter, which is why Space Bunny's missing-file crash was a
match-*start* crash. Vanilla Pyra c00, c05 and Mythra all loaded and played with
these files present, so the puff's model and skeleton load cleanly under an
eflame agent. The stool, fishbowl and turtle work through exactly this same
mechanism, and they were reported working on both crash runs.

So the asset half of this feature is done. The blocker is entirely in the game's
own construction code for the article, and no amount of copying files reaches it.

## What is in the build

* `clone_weapon` for `breath` is still registered, and `build.py` still ships its
  files for all eight slots. Nothing was rolled back.
* The two donor calls are emitted by R26 exactly as the donor has them, wrapped
  in `if crate::article::BREATH_SPAWN_ENABLED`. That is a `const false`, so the
  body is still type-checked and then compiled out. Re-enabling is one word, and
  it cannot fail to compile.

```rust
if crate::article::BREATH_SPAWN_ENABLED {
    ArticleModule::generate_article(agent.module_accessor, crate::article::breath(), false, -1);
    crate::article::note_breath(agent, "spawned");
}
```

* The other aerials, the props, the gait, Judge and the vanilla control are
  untouched and were reported working on the crash runs.

## Card (0.12.2)

- reskin NRO `2d193b5b8c86d36e3b0e8e4a7c614616309ca9adaf0e79ef24933928c9f5e46e`
- mod tree 1109 files, `libsmashline_plugin.nro` untouched (`5f4091ee...`)
- backups: `sd-backup-20260929-184753/`, `-190420/`, `-192046/`

---

# 0.12.3: the timing probe (Claude, 2026-09-29)

Installed. **This build still crashes, on purpose.** It exists to capture one
number at the moment of the crash. Do not treat it as a release, and do not
leave it on the card afterwards - put 0.12.2 back.

## Why no hook was needed

The question is "is the match's timing object present at the instant we spawn the
article?", and that is a *read*, not a call. Skyline resolves hook offsets as
`getRegionAddress(Region::Text) + offset` (skyline-rs 6b52d32,
`src/patching.rs:424`), and the console crash reports use the same
"module base + offset" convention that the decompressed `main.bin` uses as file
offset. So `Region::Text` is that base and `base + 0x52bb3b0` is the manager
slot, `*(manager + 0x690)` the timing object.

That is a belief, so the probe **verifies it before trusting it**: the first
instruction word at `base + 0x33fc110` must be `0xd10143ff`, the
`sub sp, sp, #0x50` prologue of the function that faults. If it does not match,
the probe logs `verified false` and the read is not to be believed. Nothing is
written and nothing is hooked, so a wrong base cannot break the game.

## What it writes

```text
PROBE boot: base 0x... verified true (word 0xd10143ff) manager 0x... timing 0x... present true|false
PROBE pre-spawn: base 0x... verified true (word 0xd10143ff) manager 0x... timing 0x... present true|false
```

`pre-spawn` is emitted **before** `generate_article`, not after. `note_breath`
never runs in this build - the game dies inside the spawn - so a probe after it
would record nothing. `log()` opens, writes and closes the file on every call,
so the line is on the card before the crash happens.

## The result (measured, 0.12.3)

```text
PROBE boot:      base 0x70c604000 verified true (word 0xd10143ff) manager 0x0            timing 0x0 present false
PROBE pre-spawn: base 0x70c604000 verified true (word 0xd10143ff) manager 0x3a189c2000   timing 0x0 present false
```

`verified true` means the addressing assumption is **confirmed**: the prologue
word the probe expected is the word it found. Every number below is trustworthy.

**What it rules out.** The "wrong phase" hypothesis is dead. The manager itself
is created during startup and is alive in the match (`0x3a189c2000`), so nothing
is torn down around the spawn. The timing object is null at boot *and* in the
middle of a live match, immediately before the spawn. It is not late, it is
never there.

**What it leaves.** Only five places in the whole game read that field, two of
them G&W article helpers, and it is never written on any path an eflame-owned
article takes. So it is an object G&W's own articles set up for themselves.

**The result that changes the plan.** Searching `main.bin` for writes to that
field - tracing the base register through `mov` copies, over a 600-instruction
window from every one of the 2747 references to the manager page - finds
**zero writers**:

```text
WRITES the manager slot 0x52bb3b0: 2 hits, both `str wzr` (teardown, at 0x6cab70)
WRITES manager->0x690:              0 hits
```

The manager slot itself is only ever *zeroed*. Nothing in the game's static code
stores into `manager->0x690` at all. So the object is not created by code we can
read; it is created on a path that only real G&W's articles take, and **it
cannot be supplied by copying it in from a dump**, because there is nothing in
the image to copy.

This is the honest consequence: the route of "work out what the missing pointer
should be and supply it" turns out to need the thing it was chosen to avoid.
Knowing *what* the object is does not tell us how to build one, and constructing
a valid frame/timing object by hand is a guess with a crash attached.

## The recommendation changed as a result

The guard option is now clearly the best of the three, and for a stronger reason
than before. A null-check at the faulting site is a **provable no-op for the real
Mr. Game & Watch**: his articles do have the object, so the guard's condition is
false and the instruction sequence is unchanged for him. It only changes
behaviour for an owner that would otherwise crash. That is a much stronger
safety argument than "we audited the other path through the function" - there is
no other path to audit, because the guard is inserted at the single faulting
site.

It still means a raw-offset patch of game code, which this project has been
deferring, so it is the user's call.

- reskin NRO `3ca04b0a58624b6a0921ad5b6c2ad9cc93a8ad88b2d2daaabd5fc0b3f4d16520` -
  **crashed on purpose. Superseded by 0.12.4**, NRO
  `4a1771882d88b3547be284c40db2c066dc5fec01a662f3358a50dccc988562f3`, which has
  `BREATH_SPAWN_ENABLED = false` so **the card is safe again**. The probe still
  runs - R26 emits it outside the gate - so this stays measurable for free.
- mod tree 1109 files, smashline untouched, backup `-194242/`

## The three ways forward, none cheap

1. **Bypass the native init.** Give the clone a descriptor whose `init` is null or
   a stub, so the engine builds the object without G&W's code, and drive the
   motion and hitbox from our own `Main` callback on the gated agent. Needs the
   article table to be writable per fighter, which means either a new raw-offset
   hook in the global plugin or writing the descriptor before the table is
   cached. This is the only route that does not patch shared game code.
2. **Patch the null check, conditionally on the owner.** One instruction at
   `0x33fc188`'s caller: if the owner is not `gamewatch`, branch past the
   dereference. Real G&W's up air is unaffected because the condition is false
   for him - but it is game code shared with the real fighter, so it needs an
   audit of the other path through the same function, and the project has
   deliberately not taken a raw-offset hook yet.
3. **Find what is missing rather than guard it.** `x24` comes from a lookup off
   the owner. If it is a param, a bone, or a per-fighter struct that eflame simply
   does not have, the honest fix is to supply it, and nothing in shared game code
   gets touched. Not yet identified; this is the route that would be worth trying
   first, because it is the only one that has no risk to real G&W.

Options 1 and 2 both need something the project currently reserves, so this is a
decision for the user rather than a next step.
