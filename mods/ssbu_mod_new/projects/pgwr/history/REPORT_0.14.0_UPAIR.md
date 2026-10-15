# 0.14.0: breath parameter bridge + Mythra c06/c07

Built 2026-09-29 for Smash 13.0.4. **Console behavior is not yet verified.**

The combined release includes the existing Mythra changes: Corrin up air,
Mii Swordfighter Hero's Spin up B (including eight retargeted clips), and Luigi
down throw, all restricted to c06/c07. Their move logic is preserved. The Mythra
gate diagnostic now uses the entry ID instead of the battle-object ID, and writes
to `sd:/ultimate/pgwr_log.txt`, so it can be inspected after transforming.

## Correction to the earlier up-air diagnosis

`*( *(main + 0x52bb3b0) + 0x690 )` is Game & Watch's decoded fighter parameter
object, not a match timing tracker. The old interpretation of two pointers as
frame stamps was incorrect: pointer differences divided by element size are
container lengths. Other readers found by a broader scan also contradict the
old report's count of five readers.

The decisive evidence is the game's PRC decoder:

| Key in donor `fighter/gamewatch/param/vl.prc` | Field offset | Value | Decoder store |
| --- | --- | --- | --- |
| `pos_offset_x` | 0x118 | 0.5 | 0xa9829c |
| `pos_offset_y` | 0x11c | 21.5 | 0xa98350 |
| `life` | 0x120 | 34 | 0xa98438 |
| `move_interval` | 0x124 | 7 | 0xa98520 |
| `speed_y` | 0x128 | 8.5 | 0xa985d0 |
| `scale_mul` | 0x12c | 1.9 | 0xa98684 |

The native parameter lookup at 0xa91ed4 also returns `object + 0x118` for
`param_breath`. `tools/verify_breath_bridge.py` independently checks each key's
hash construction, destination register, field offset, donor value, and the
constructor signature. It passed for all six fields.

## Implementation

`plugin/src/breath.rs` provides a static parameter view to the breath constructor
at `main+0x33fc140`, after its load of the missing G&W parameter object. Only x24
is redirected, only during this mod's synchronous `generate_article` call, and
only for the breath weapon kind. The native constructor continues normally,
reading spawn position at +0x118/+0x11c and scale at +0x12c. No pointer is written
into the global parameter manager. The entire 388-byte constructor is compared
against the audited image before installing hooks; a mismatch disables spawning.

Two symbol-based WorkModule parameter hooks supply `param_breath` to the original
donor status scripts for a breath whose founder is Pyra c06/c07. Real G&W and all
other queries call the original functions. Founder identity is used instead of
current link owner so reflection does not switch off the parameter bridge.

The donor status NRO uses `get_param_int` for life and movement interval and
`get_param_float` for upward speed (calls at NRO+0x32348, 0x323b0, 0x32418,
and 0x32a30). The donor movement logic and projectile attack script are retained.
The original attack-air script generates on frame 8 and shoots on frame 9.

The old unconditional timing probe and compile-time false switch are removed.
The generator emits calls through the version-checked bridge, so regeneration
preserves the fix. The global smashline plugin is not rebuilt or replaced.

## Build and validation

- `cargo skyline build --release`: passed; only existing unused-function warning.
- `tools/gen_acmd.py --check`: passed for all four generated script groups.
- `tools/verify_breath_bridge.py`: six fields and constructor signature passed.
- `build.py`: 1,117 files, including Mythra's eight Hero's Spin clips.
- NRO SHA-256: `0372cf5be5855e4cb5e1c8c3e36dd4636c82cd64693dc713c6ff2a214f2cfa90`.

## Console test

1. Pyra c06 and c07: use up air repeatedly; confirm a puff appears, travels upward,
   hits, finishes, and disappears. Test landing and down-B while a puff is alive.
2. Transform into Mythra: test up air, ground tap/charged up B, aerial up B, and
   down throw. Repeat for c07.
3. Check vanilla Pyra/Mythra c00-c05 and real G&W's up air. Check the fishbowl,
   turtle and Judge for regressions; optionally reflect a puff.

Expected file-log lines include `BREATH parameter bridge ready`,
`BREATH native spawn parameters supplied`, `BREATH donor status parameters
supplied: life 34`, `BREATH spawned`, `BREATH shot`, and `MYTHRA GATE ACTIVE`.
If the game crashes, retain the SD log and Atmosphere crash report. Compilation
and offline inspection do not establish successful projectile behavior on hardware.

## Installation result

Installed and byte-for-byte verified on F: with 1,117 mod files. Previous NRO and
mod folder backed up in sd-backup-20260929-202833. Existing smashline hash stayed
5f4091eed89c5854c2bfccb9f25b6e8da8c03ebedcaa5ab36eadebfc078bc8f7.
The previous SD log is backed up there; the live log is ready for this test.

