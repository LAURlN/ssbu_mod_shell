# FLAG_SUCCESS_SP - who sets it

Measured 2026-09-30 by Buffy on `dumps/arc/prebuilt/nro/release/lua2cpp_brave.nro`
(sha256 `dc5edcde314f0c461ba0ab08d9e9deef5ede9d5b4ed324141678b9966d43b7a2`, 13.0.4, region 2).
Everything below is **tier B** - measured offline - except where marked. Bodies:
`flag_success_sp.c` in this directory. Read that file's header first; it lists three Ghidra
rendering artefacts, one of which changes how the setter must be described.

## The three addresses named in the brief

None of the three is the setter, and the third is not a `FLAG_SUCCESS_SP` reference at all.

| brief address | containing function | verdict |
| --- | --- | --- |
| `0x28d00` | `FUN_00028ce0` (`0x28ce0..0x294a0`) | **reads** the flag; does not set or clear it |
| `0x29820` | `FUN_00029760` (`0x29760..0x29f18`) | **reads** the flag; does not set or clear it |
| `0x2ad40` | `FUN_0002ac80` (`0x2ac80..0x2b0a0`) | **no `FLAG_SUCCESS_SP` reference**; references `WORK_INT_HOLD_FRAME` (`0xc958`) |

The `0x2ad40` premise in the brief is wrong, and it matches what
`SOURCE_STATUS.md` §5 already said ("one near `0x2ad40` references `WORK_INT_HOLD_FRAME`")
- §3 of the addendum, which lists `0x2ad40` among the `FLAG_SUCCESS_SP` references, is the
outlier. The instruction word at `0x2ad40` is `mov w8, #0xc958`, confirmed from the raw image and
from `nro_util.const_name`; it is not the `0xc914` that a `FLAG_SUCCESS_SP` site would carry.
This needs a retraction in the addendum, which is out of scope for this read-only task.

Per function, the rest:

- **`FUN_00028ce0` - spark spawner.** Caller: three `bl` sites, `0x285d0`, `0x2a240`, `0x2a760`
  (tier B). Those three are anonymous MAIN bodies that change motion by situation, call
  `FUN_00028af0`, then call this with `param_special_s/0x74a38abf` (spark wait count).
  It reads `FLAG_SUCCESS_SP` and **returns immediately when it is false**. When true it runs the
  `STORE_TARGET_RIGHT/LEFT` -> `DECIDE_SPARK_*` -> `FINISH_SPARK_*` -> `generate_article SPARK`
  sequence and compares the wait count against `WORK_INT_SPARK_WAIT_COUNT_RIGHT/LEFT`. Its
  `on_flag_impl` calls belong to the four `DECIDE`/`FINISH_SPARK_*` flags, never to
  `FLAG_SUCCESS_SP`.
- **`FUN_00029760` - ATTACK3's continuation MAIN.** Caller: **no `bl` caller**; it is
  address-taken at `0xef10`, inside `0xec80` =
  `FIGHTER_BRAVE_STATUS_KIND_SPECIAL_S_ATTACK3 ..._STATUS_MAIN`. That is the
  `sub_shift_status_main` idiom, so ATTACK3 hands the run to this function and it finishes by
  `change_status` to `SPECIAL_S_ATTACK3_APPEND`. It reads `FLAG_SUCCESS_SP` **and**
  `FLAG_ACTIVATE_LIGHTNING`; with both set it drives the lightning spawner
  (`WORK_INT_LIGHTNING_INTERVAL_COUNT`, `alloc_log_group`, `generate_article LIGHTNING`, capped
  by `WORK_INT_LIGHTNING_ACTIVE_COUNT < 2`). Neither flag is written.
- **`FUN_0002ac80` - HOLD's shifted-in MAIN.** Caller: address-taken at `0xe6cc`, inside
  `0xe530` = `..._SPECIAL_S_HOLD ..._STATUS_MAIN`. This is the real reason
  `SPECIAL_S_HOLD`'s own registered bodies never mention `FLAG_SUCCESS_SP`: the logic sits in
  this helper. It reads `WORK_INT_HOLD_FRAME` and compares it against `param_special_s`
  `hold_frame_m` / `hold_frame_l` / `0x3adad701`, then reads `CONTROL_PAD_BUTTON_SPECIAL`.

## The setter

**`FUN_00016db0`, via `FUN_0001a230`.** Tier B.

All three ATTACK MAIN bodies contain `FLAG_SUCCESS_SP` **neither as a read nor as a write**. They
build the id as an `L2CValue` and pass it *into* a helper:

```c
lib::L2CValue::L2CValue(aLStack_50, get_param_float(...));   // the amount
lib::L2CValue::L2CValue(aLStack_60, _FIGHTER_BRAVE_STATUS_SPECIAL_S_FLAG_SUCCESS_SP);
FUN_00016db0(param_2, aLStack_50, aLStack_60);
```

That is the same helper, and the same calling shape, that neutral-B uses - it is already pinned
in `refs/brave_special_n/neutral_b_status.c` as the setter called from
`FIGHTER_BRAVE_STATUS_KIND_SPECIAL_N_SHOOT` MAIN. Side-B reuses the neutral-B helper rather than
having its own, which is why nothing in the `0x20000-0x30000` anonymous block sets the flag.

`FUN_00016db0` callers, word-decoded over `.text` (tier B): `0xce38` (in `0xcc20`
`SPECIAL_N_SHOOT` MAIN - the existing neutral-B pin, which is the control), `0xe830`
(`ATTACK1` MAIN), `0xeab0` (`ATTACK2` MAIN), `0xed80` (`ATTACK3` MAIN), `0x13988` (in `0x136c0`
`SPECIAL_HI_JUMP` MAIN), `0x1c3f8` (in `0x1bec0`, unregistered).

`FUN_00016db0` reads `FIGHTER_BRAVE_INSTANCE_WORK_ID_FLOAT_SP` and
`..._FLOAT_MAX_SP`, calls `FUN_0001a230`, and on a true result calls
`FighterSpecializer_Brave::add_sp`. `FUN_0001a230` is the actual mutation site:

```
sp = get_float(WORK_ID_FLOAT_SP);  max_sp = get_float(WORK_ID_FLOAT_MAX_SP);
amount <= sp  ->  WorkModule__on_flag_impl(module, flag_id)   // SET
else          ->  WorkModule__off_flag_impl(module, flag_id)  // CLEAR
```

So it is **both** setter and clearer in one place, and the direction is decided by a comparison
against the live SP work float. That is the whole gate.

## Correction this forces on the addendum

`SOURCE_STATUS.md` §4 concludes, from three absences, that "the gauge check is engine-side, in
`main.bin`, outside `lua2cpp_brave.nro`", and that therefore a status/ACMD port "has no gauge to
consult". **Tier B measurement contradicts the second half of that.** There *is* an SP
comparison inside `lua2cpp_brave.nro`: `FUN_0001a230` reads `WORK_ID_FLOAT_SP` and
`..._FLOAT_MAX_SP` and gates `FLAG_SUCCESS_SP` on it.

Where those floats are filled and where the SP UI lives were not traced here.
The settled recipient design replaces the helper's decision with owned unconditional
success. It must not read Hero SP work floats on Mythra or call Hero's SP specializer.
Gauge reachability remains outside scope. The hardware control is real Hero's
side-B at sufficient/insufficient SP against the recipient's unconditional outcome.
The measured comparison is against the requested amount, not necessarily a full meter.

2026-09-30 recheck: `tools/audit_hero_side_b.py` 1.0.0 reproduces the setter,
neutral-B control call, and spark guard from fresh flattened bytes. Full inputs/hashes:
`native_dependency_audit.json`. The earlier inverted guard is retracted in
`handbook/graveyard.md` R-HERO-S-2. The C below was the control that exposed it.

## Not established

- Whether the code above `0x70000` that also materialises `0xc914` (`0x7998c`, `0x79cb0`,
  `0x7b6c0`, `0x7fcc0`, `0x81bb0`, `0xd69a4`, `0xd6d64`, `0xd72c4`, `0x115608`, `0x115828`,
  `0x116260`, `0x159728`, `0x15a058`, `0x15a538`, `0x15b098`, `0x15b5e8`) is hero-side or
  weapon-side. `lua2cpp_brave.nro` carries the `WEAPON_BRAVE_*` statuses as well. Those bodies all
  decompile to `is_flag_impl` reads and none writes the flag, so they do not change the verdict,
  but their module is unattributed.
- The enclosing function of `0x26498`, the second caller of `FUN_0001a230`. It has no matching
  frame-pointer prologue and lies outside the ranges scanned. Recorded as unresolved rather than
  guessed.
- The exact amount and sign passed to `FighterSpecializer_Brave::add_sp`. Ghidra's rendering of
  that call's argument marshalling is inconsistent with a four-argument C++ signature, so only the
  control flow around it is treated as measured.
- Nothing here is hardware evidence. No claim in this file is tier A.

## Reproduction

The scripts that produced this are in `scratch/2026-09-30_flag_success_sp/`
(`entries2.py` for function boundaries, `callers.py` for callers, `scan_consts.py` for the const
sites, `build_ref_c.py` to assemble the C). **AGENTS.md rule 3 says scratch is deleted after 30
days and anything useful must be promoted to `tools/` first. This task's brief forbade writing
anywhere except the two output files, so the promotion was deliberately not done.** Re-deriving
these results after 2026-10-30 means rewriting the boundary detector in particular: this binary's
prologue is `sub sp,sp,#N` / `stp x29,x30,[sp,#N-0x10]` / `add x29,sp,#N-0x10`, *not* the
pre-index `stp ... [sp,#-N]!` form, and detecting the wrong one yields zero entries with no error.
