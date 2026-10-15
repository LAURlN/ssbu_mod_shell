# Console run 1 - 2026-09-29 - 0.2.0 phase 1 (gating + jab)

## What was installed
- sd:/atmosphere/.../skyline/plugins/libpyra_gamewatch_reskin.nro
  sha256 7fdcfadd5dd3bb02d879a64db32df5e88c0db9fb8b3507ff1fc1bd6ecb849b01
- sd:/ultimate/mods/pyra_gamewatch_reskin/info.toml -> 0.2.0

## Expected vs seen
| Expected | Seen |
| --- | --- |
| `[PGWR] ... v0.2.0 (phase 1: gating + jab) loaded` at boot | not reported |
| `[PGWR] gated fighter=eflame costumes=[6, 7]` | not reported |
| c06/c07 jab = G&W hitbox (short poke at top, 3%) | "i think the jab is working" |
| c00-c05 jab = Pyra's sword jab, unchanged | NOT explicitly confirmed |
| Mythra + real G&W unchanged | NOT explicitly confirmed |
| no crash | not reported as a problem |

## Verdict
INCONCLUSIVE on gating. The user judged the jab "kinda hard to tell", which is
not a positive identification of G&W's hitbox, and the negative control (vanilla
c00-c05 / Mythra / real G&W unchanged) was never explicitly confirmed.

Gating is still treated as UNPROVEN. Phase 2 proceeds because the user asked to
continue, not because the gate was verified. Two mitigations added in 0.3.0:
  1. a runtime log line naming the costume whenever an overridden script fires,
     so gating can be read from the log instead of judged by eye;
  2. a deliberately conspicuous marker move so a positive result is unambiguous.
