# T-0057 - Hero mana inputs, recovered and pinned

Freebuff dispatch slot `3-mythra-mana`, 2026-10-02. Tiers: **B** for everything
here (bytes read out of a pinned file). No console, no emulator, no tests, no
card access, no install.

## 1. The answer to "why was the mana not working"

The Hero moves in this mod were **written with mana switched off**. It is not a
broken mana system, a missing gauge, a wrong parameter or a failed feature: the
gate that decides whether a spell is affordable was hard-wired to "yes" and no MP
value was ever kept.

Evidence, in the tree this task started from:

* `src/pgwr/plugin/src/mythra/hero_neutral_b/fighter.rs` - `redirect` logged
  `mana=off`;
* `src/pgwr/plugin/src/mythra/hero_side_b/fighter.rs` - module docstring:
  "Mana is excluded by the user's instruction: SUCCESS_SP is always true";
* `src/pgwr/plugin/src/mythra/hero_neutral_b/donor_params.rs` - header:
  "Mana prices excluded";
* `src/pgwr/plugin/src/mythra/hero_side_b/params.rs` - header: "no mana fields";
* `src/pgwr/plugin/src/mythra/hero_side_b/state.rs` - header: "contain no mana
  state";
* `src/pgwr/plugin/src/lib.rs` - the boot banner said "Hero neutral-B without
  mana".

The cause of *that* is recorded, not guessed: T-0046/T-0049 changed the
specification (one shared pair meter, real HUD) but the work stopped at BLOCKED,
waiting for the numeric PRC values. Those values are the only input the
implementation needed, and §2 below is where they came from.

## 2. The donor parameter file, recovered

T-0049 could not reach the donor parameter file and recorded that as its blocker.
It is reachable, and the reason it looked unreachable is a dead end worth
writing down: **the user's ArcExplorer export has an empty
`fighter/brave/param/` directory**, so a file missing there is not missing from
the game. The file is in the base game and `tools/arc-extract` pulls it out of
the local `data.arc`.

```
tools/arc-extract/target/release/arc-extract.exe \
  --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/ssbu-13.0.4/files \
  fighter/brave/param/vl.prc
```

| item | value |
| --- | --- |
| container | `gamedata/ssbu-13.0.4/data.arc`, sha256 `ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995` |
| ARC path | `fighter/brave/param/vl.prc` |
| extracted | 18,685 B, sha256 **`dafa43c632c8562e8f6835f6162a5a04ecb817eb5dec7b3ed75755c5d9dd4d76`** |

The same `dafa43c6...` hash is already recorded in
`hero_neutral_b::donor_params`, which was generated from this same file. So the
fireball numbers and the SP numbers below now come out of one pinned donor file.

Decoded with `tools/dump_hero_mana_params.py` v1.0.0 (promoted); report
`hero_mana_params.json` in this directory.

## 3. The six prices, the ceiling and the recovery - measured

| name | Hash40 | value | where |
| --- | --- | --- | --- |
| `sp_max` | `0x0634ffda6c` | 100.0 | `param_private` |
| `recover_sp` | `0x0a5a302e1e` | 1.0 | `param_private` |
| `sp_recover_frame` | `0x100012301a` | 60 | `param_private` |
| `sp_recover_damage_mul` | `0x15db7b9842` | 0.8 | `param_private` |
| `sp_recover_shield_mul` | `0x1595084712` | 0.8 | `param_private` |
| `sp_special_n1` | `0x0d3fd79c7d` | **6.0** (Frizz) | `param_private`, cross-checked in `param_special_n[0]` |
| `sp_special_n2` | `0x0da6decdc7` | **16.0** (Frizzle) | same |
| `sp_special_n3` | `0x0dd1d9fd51` | **36.0** (Kafrizz) | same |
| `sp_special_s1` | `0x0dc0bbf061` | **8.0** (Zap) | `param_private` |
| `sp_special_s2` | `0x0d59b2a1db` | **18.0** (Zapple) | `param_private` |
| `sp_special_s3` | `0x0d2eb5914d` | **42.0** (Kazap) | `param_private` |

Every one of those eleven Hash40 keys is the key the T-0033/T-0049 contract had
already written down from `ParamLabels.csv`, so the label-derived table and the
decoded file agree key for key. That is a check on both, not just on the numbers.

`param_special_n[0]` repeats the three neutral prices (6 / 16 / 36) and entries
1-3 are all zero, which is why the neutral-B donor reads them out of the
`param_special_n` parent while the side-B prices live only in `param_private`.

## 4. The gate, the debit and the failure - pinned donor code, re-read here

From `refs/brave_special_n/neutral_b_status.c` (`FUN_0000cc20`, the SHOOT MAIN)
and `refs/brave_special_s/flag_success_sp.c` (`FUN_00016db0`, `FUN_0001a230`):

* the SHOOT MAIN compares the level name to the donor's S / M / L constants and
  reads the matching price with `get_param_float(boma, 0x899192aa, price_hash)` -
  the same parent and the same keys as §3;
* `FUN_0001a230`: `if (amount <= sp) { on_flag(SUCCESS_SP); true } else
  { off_flag(SUCCESS_SP); false }` - the comparison is a plain `<=`, no epsilon;
* `FUN_00016db0`: **only on true** does it call `add_sp(fighter, -price)`;
* `flag_success_sp.c` names the callers of that one function: `0xce38` (neutral
  SHOOT MAIN), `0xe830` (ATTACK1), `0xeab0` (ATTACK2), `0xed80` (ATTACK3),
  `0x13988` (up-B, out of scope) and one unregistered site. The side-B finisher
  is **not** a caller, so Kazap's finisher does not spend a second time;
* the neutral article setup (`0x2b420`) is gated on `SUCCESS_SP`, so a refused
  cast creates no projectile; `0x28ce0` (sparks) returns while the flag is clear;
  `0x29760` needs the flag as well as the lightning activation.

This is why the out-of-MP behaviour implemented here is "the motion plays, no
article is created, nothing is spent" and not a silent no-op.

## 5. Reserved targets, byte-verified on the 13.0.4 image

`tools/audit_hero_mana_native.py` v1.0.0; report `reserved_sites.json`.
All nine sites **MATCH**.

| site | image | offset | bytes |
| --- | --- | --- | --- |
| HUD update task registration | main | `0x13540e4` | `a80100d008411c9179e8019039c33a91` |
| HUD task adapter | main | `0x138a710` | `080440f9000140f9bab70014` |
| HUD update target | main | `0x13b8600` | `ff8302d1ea1300fde923036dfc6f04a9` |
| match-start adapter | main | `0x2256b00` | `fd7bbfa9fd030091e2efcf97e0031f2a` |
| SP start/max assignment | main | `0x852840` | `ff4301d1e81300fdf51700f9f44f03a9` |
| SP passive recovery | main | `0x853500` | `ffc302d1e82b00fdfa6706a9f85f07a9` |
| SP add positive guard | main | `0x853890` | `ff8301d1ea1300fde9a3026df51f00f9` |
| damage event entry | main | `0x854610` | `a02040bde00301aae103032ae3031f2a` |
| damage event scaling | main | `0x854a4c` | `9f02007289178052ea071a324911899a` |

Images: `gamedata/ssbu-13.0.4/main.bin` sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` (matches the
flat hash the contract recorded for it), and the donor NRO
`prebuilt/nro/release/lua2cpp_brave.nro` sha256
`dc5edcde314f0c461ba0ab08d9e9deef5ede9d5b4ed324141678b9966d43b7a2` (matches the
pinned donor hash).

The first four were carried over from T-0049's own measurement and are the ones
that make an approved HUD hook safe to attempt. The other five are new
measurements taken by this task.

**A correction worth keeping:** Hero's SP code is in `main`, not in
`lua2cpp_brave.nro`. `0x852840` / `0x853500` / `0x854610` read past the end of a
2.9 MB NRO, which is how the mistake is visible; an earlier reading of this task
put the damage sites in the donor NRO. The NRO is still pinned above because the
contract's donor NRO hash is what makes the `flag_success_sp.c` pin meaningful.

## 6. The real fighter HUD already has an MP gauge

Extracted from the same `data.arc`:

| item | value |
| --- | --- |
| ARC path | `ui/layout/info/info_melee/info_melee/layout.arc` |
| size / sha256 | 2,166,040 B, `c382a6e575e48102aff492fdc2bfd9c8a9cab6d9a0843b61224e4ab15e9c25c3` |

Byte-identical to the user's ArcExplorer copy of the same path, so the two
sources agree. Named entries inside it (tier B, plain strings read out of the
file):

* `blyt/info_melee_lct_player_sp.bflyt`, layout instance
  `info_melee_lct_player_sp`;
* panes `sp_00`, `sp_01`, `sp_02`, `sp_03` (four player slots) and `sp_bg`,
  `sp_bgC`, `sp_bgLT`, `sp_bgRT`;
* `anim/info_melee_lct_player_00_sp.bflan`, `..._01_sp.bflan`, and
  `anim/info_melee_lct_player_sp_sp.bflan` with `_anim_in` / `_anim_loop` /
  `_anim_out`;
* HUD event names `MELEE_GAUGE_SP_GET`, `MELEE_GAUGE_SP_USE`; setters
  `set_fxui_sp_get`, `set_fxui_sp_use`, `set_sp`, `set_sp_flash`.

So the contract's line "Hero wind-command textures found in the index are not
established MP resources" is superseded: the MP gauge resources are established
and named. An approved HUD implementation would author **no** assets; it would
drive panes that already exist. What is still unknown is what makes the game draw
them for a c06/c07 entry - the SP event the HUD consumes - which is the reserved
part.

## 7. What is still not established

* whether the engine calls the `on_line(Main)` line exactly once per fighter per
  frame, which is what the per-frame recovery advance assumes (tier D; the log
  prints a `TICK` rate line per 60 frames so it is measurable on hardware);
* the out-of-MP failure effect and sound. The pinned status dumps carry no effect
  names, so nothing was invented in their place;
* hit and shield recovery, and the HUD gauge: both reserved, see
  `../../../../src/pgwr/plugin/src/mythra/hero_mana/{damage,hud}.rs`.
