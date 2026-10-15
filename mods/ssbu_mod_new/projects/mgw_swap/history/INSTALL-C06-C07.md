# c06 + c07 package — 2026-09-26.c06c07

Both costume 7 (c06) and costume 8 (c07) now receive the current replacements:
Mythra's Hero's Spin, Corrin up-air and Luigi down-throw; G&W's Monkey Flip
and sword forward-air; and the bidirectional Mythra/G&W swap for paired entries.
Ordinary G&W selections get the move replacements but do not create an Aegis pair.
The current grenade experiment remains disabled, as in the incoming .p4 build.
G&W neutral-B therefore remains Chef. c00–c05 retain their existing vanilla paths.

## Install

Merge both folders from `<workspace root>\mod_output`
into the matching SD-card locations:

- `atmosphere` → `sd:/atmosphere`
- `ultimate/mods/mythra_gamewatch_swap` → `sd:/ultimate/mods/mythra_gamewatch_swap`

The plugin is `libmythra_gamewatch_swap.nro`, 143360 bytes, at
`sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/`.
Keep only one version of this plugin installed; overwrite its existing file.
Also install the assets: the package contains new c06 folders under
`fighter/elight/motion/body`, `fighter/gamewatch/motion/body`, and
`fighter/gamewatch/model/body`.

SHA-256: `aadadfbfce1abce1f59aedc9182e76d9c3071bf5b713450deb7cb3f6b4542a29`

## Switch test (pending)

1. Start a match as c06 Mythra. Test ground/air Hero's Spin, startup reversal,
   up-air and down-throw. Swap to G&W and back on the ground and in the air.
   Check position, damage, camera and costume stay correct.
2. As the c06 G&W partner, test forward-air and Monkey Flip including a grab
   and interruption. Check the sword appears during fair and hides afterward.
   Repeat the moves with an ordinary c06 G&W selected directly.
3. Put c06 and c07 Aegis in the same match, swap each repeatedly, lose a stock
   and finish the match on each form. Neither player's state should move to the
   other. Also confirm c07's existing moves still work.
4. Check ground/air up-B on c00–c05 Mythra, normal Pyra/Mythra swapping on those
   slots, and vanilla G&W moves on an untouched costume. Neutral-B should be
   Chef on every G&W slot while the grenade experiment is disabled.

Startup marker: `[MGW-SLOTS] build 2026-09-26.c06c07 costumes=[6, 7] grenade=false`.
Hero's Spin entry diagnostics now say `entry c06` or `entry c07`; either should
reach its motion/phase lines. Other costumes should not enter a custom Hi3 phase.
Preload and FighterEntry Init lines include the actual entry id and costume.
These logs establish dispatch; visible movement, hits and swap behavior still
need the on-console checks above.

## Offline verification and rollback

The release build and complete deploy pipeline passed. Built/package NROs match,
NRO0 header/size are valid, 37 c06 files verify, c06 body geometry/materials are
preserved, and all pre-existing c07 files are byte-identical. The grenade module's
markers are absent. This does not establish Switch runtime behavior.

To undo this extension, restore the NRO from
`mod_files/mythra_gamewatch_swap/backups/before-c06-extension/` to the same SD
plugin path and remove only the three newly added c06 asset folders named above
from this mod's SD folder. Leave its c07 files installed. That backup is the
incoming .p4 grenade-disabled build, not a claim that .p4 is console-verified.
