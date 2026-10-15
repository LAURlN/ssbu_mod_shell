# Hero MP gauge on the fighter HUD - the route, read out of the 13.0.4 image

2026-10-03, Claude (Opus). Tier **B** for every statement about bytes, offsets and control
flow (read from `gamedata/ssbu-13.0.4/main.bin`, sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`, by the tools named
below). Tier **D** for everything about what the console draws: **no console, emulator or
test run exists for any of this.**

Files here: `hud_route.asm.txt` (disassembly of all 25 spans), `hud_route_audit.json`
(span sha256 + vtable slots, `tools/audit_hero_mana_native.py --hud-only`),
`hud_constants_audit.json` (every plugin constant against its instruction,
`tools/audit_hero_mana_hud.py`).

## 1. What the earlier work had right and what it had wrong

T-0049/T-0057 found the SP events (0x5c set, 0x5d add), the layout names and three
candidate hook sites, and concluded the gauge "needs an interception of the HUD update or
of the SP event dispatch". The first part stands. The conclusion does not: **no
interception is needed**, because the game already has a non-Hero fighter show this gauge
(Kirby copying Hero) and the function that does it is callable. See graveyard R-HERO-MANA-5 (added during Codex recovery).

## 2. The chain, from Hero's fighter code to the pixels

1. `FighterSpecializer_Brave::set_sp` (`0x8529f0`) writes Hero's work floats and then raises a
   **FighterManager event**: `{vtable 0x4f83168, id 0x5c | 0x5d, player, sp}`.
   FighterManager = `*(*(main+0x52b84f8))`; the entry object is `[FM + 0x20 + 8*entry]`; the
   HUD player id is the int at entry `+0x41e4`, used only if the byte at `+0x41e8` is set.
   `0x85bbfc` raises id 0x5e (player only) when SP is short.
2. Listeners are per event id: list head `[FM+8] + id*0x18 + 8`, node `+0x10` = delegate,
   delegate `{+0x10 owner, +0x18 callback, +0x20 adjustment}`. The HUD's delegates call
   `0x1378650` (0x5c), `0x1378680` (0x5d), `0x13786b0` (0x5e), each of which does
   `H = [owner+0x20]; H->vt[0x2e0 | 0x2e8 | 0x2f0](H, player, sp)`.
3. `H` is one of three classes. Two (`vtable 0x5061780`, `0x5061ba0`) share the handlers
   `0x13689c0` / `0x1368ae0` / `0x1368bb0`; the third (`0x5061f60`) has its own and a different
   panel class, and **is not supported by the plugin** (it refuses).
4. The handler maps the player to a panel: `G = *(main+0x52c2420)`, `M = *[G+8]`,
   `i = [[H+0x18] + player*0x260 + 0xc]`, view handle `= M+0xc50` if `i == -1` else
   `[M + 0xc68 + 8*i]`; valid if `[h+8] != 0`, `byte [[h+8]]+0x70 != 0`, `[h+0x14] != -1`
   (`0x138b1c0`); panel index `[h+0x14]` **bounded by 8, not 4**; panel
   `= [[view+0xb0]+0x1910] + index*0x3e0`. A mode check (`*(main+0x532e8b0)`, `+0x138`,
   `+0x2b8 == 0xb`) skips the panel.
5. `[panel+0x318]` is the panel's 0x40-byte **brave UI**, built by the panel constructor for
   every fighter (`0x1405be0` called from `0x1426644`): `+0x28` SP state, `+0x30` command
   window, `+0x38` shortage byte. The SP state (`0x1407360`, 0x280 bytes) is a small state
   machine with a 12-entry queue of `{u32 command, f32 value, u8 used}`: command 0 sets,
   1 animates to a new total, 2 previews a cost. `+0x258` is the target value.
6. The gauge is only *drawn* when the panel's current part is the brave part. The panel's
   gauge object is `panel + 8`; its current part pointer is `[gauge+8]`; the brave part is
   the embedded object at `gauge+0x300` (vtable `0x5065d58`: `+0x10` init, `+0x18` reset,
   `+0x20` update). `0x1426fb0` - **`select(gauge, chara, copy)`** - picks the part from the
   fighter kind of `chara`: kind **0x53 (Hero) -> `gauge+0x300`, part 8**, and for kind 6
   (Kirby) from the kind of `copy`, where 0x53 again gives `gauge+0x300`. It then runs the
   old part's reset, the new part's init (which binds the brave UI to layout row
   `[layout+0x80] + index*0xd90 + 0xf78`) and the layout part switch `0x1b7d460`.
   The game calls it as `select(panel + 8, [panel+0x3c8], [panel+0x3d0])` (`0x1367690`).
7. eflame (0x5a) and elight (0x5b) own no part, so a c06/c07 panel's part is empty, and a
   form swap - which makes the game call `select` again for the new kind - empties it again.

## 3. The route the plugin takes

`src/pgwr/plugin/src/mythra/hero_mana/hud.rs`, feature `hero-mana-hud`:

* find `H` through the delegate on event 0x5c (step 2), refuse unless its vtable is one of
  the two known classes;
* find the entry's player id (step 1) and its panel (step 4), and check the gauge is the
  13.0.4 object (brave part vtable at `+0x300`, owner pointer, panel index, SP state
  descriptor/capacity/buffer);
* if the part is empty: `select(gauge, 0xc1ffff00_00000000 | hash40("ui_chara_brave"),
  0xc1ffff00_00000000)`. The chara id format is the game's (`0x3262130`): tag 0xc1, a 16-bit
  index hint, a hash40; a hint that is out of range makes it search by hash, and an unknown
  hash yields no part - so a wrong id is "no gauge", not a crash;
* push the value with `H->vt[0x2e0]` (instant, the first frames after a selection) or
  `H->vt[0x2e8]` (animated), only while the state's target differs from the meter;
* a refused cast calls `H->vt[0x2f0]` (the donor's shortage flash).

Nothing is hooked, no slot is patched, no game memory is written by the plugin. No pointer
is kept across frames; every dereference is preceded by `svcQueryMemory`.

## 4. What is not established (tier D)

* that the brave part initialises correctly on a panel whose fighter is neither Hero nor
  Kirby - in particular that the row's MP gauge binding (`row+0xf78`) is populated for every
  player (the plugin refuses when it is null) and that `0x14249c0`'s owner calls behave;
* that the lookup `ui_chara_brave` -> kind 0x53 succeeds at run time (the key is in the
  package's `ui_chara_db.prc`; a failure is logged as `HUD SELECT-FAILED`);
* where the gauge sits on a Pyra/Mythra panel, and how it looks in the condensed 5-8 player
  layout;
* that nothing else re-selects the part between swaps (the plugin rate-limits and gives up
  with `HUD OFF` rather than fight);
* thread context: the calls are made from the fighter's `Main` line, which is where Hero's
  own `set_sp` raises the same events - measured for the events, assumed for `select`
  (the game's own callers are event handlers raised from the same context).

## 5. Recovery completion — 2026-10-03 (Codex)

User explicitly authorized project-owned native integration; framework plugins remain off limits.
Checked READY candidate `builds/pgwr/zapple-mana-hud-0.1.1/` has combined/angle-only/HUD-only/baseline
controls, latest installed assets and narrow patches. Hardware behavior remains unverified (D).

Source corrections: reset dead/refusal/cooldown/set bookkeeping once at the owned stock/entry boundary,
not a swap; count the eight-frame instant-set window even if target MP already matches. No game pointer
is reused across frames; native teardown/selection still owns removal for vanilla/CSS. The guard does
not prove concurrency safety; serial fighter/event context and native part selection from Main remain
runtime assumptions. Existing active-Main callback regen dedupe limits remain unchanged.

Verified B: fresh isolated builds, 25 native spans/nine slots, generated table identical; 161 checks for
each HUD-enabled build, signature/constant/selector negative controls; 5099-file asset retention (info
version only), six-file source delta and clean patch reproduction. Evidence and complete manual controls:
`evidence/2026-10-03_pgwr_zapple_mana_hud/RESULT.md`. Logs BIND/READY establish internal prerequisites,
not rendered pixels. Old cached 0.1.0 manifest is superseded and must not supply an asset tree.
