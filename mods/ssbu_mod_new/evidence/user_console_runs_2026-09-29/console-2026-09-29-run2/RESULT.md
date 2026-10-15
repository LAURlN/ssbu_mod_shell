# Console run 2 - 2026-09-29 - 0.3.0 (phase 2)

## Expected vs seen
| Expected | Seen |
| --- | --- |
| c06/c07 normals, aerials, grabs, throws behave as G&W | "mostly right" |
| GATE ACTIVE line for c06/c07 | not reported |
| vanilla c00-c05 / Mythra / real G&W unchanged | NOT TESTED (user: "I didn't test the vanilla slots") |
| no crash | "but no crash" |
| no leftover Pyra animations | "animations are a bit weird here and there" |
| - | "still some leftover animations from Pyra, especially the sword" |
| - | "usually I find a second or even more G&W on top of each other" |

Follow-up clarification from the user on the duplicate:
"from the very beginning, during movement and most animations. only disappears
during some animations and comes back afterwards"

## Findings
1. Gating: STILL UNVERIFIED. Never tested. This remains the one thing that
   blocks confidence in everything else.
2. Leftover Pyra animations: ROOT CAUSED. The rapid-fire chain
   (Attack100 / Attack100Sub / Attack100End) was never ported - G&W's Attack11
   sets ENABLE_100 which hands over to Attack100, so Pyra's 0.6% magic pokes and
   her `eflame_attack100` effects kept playing. Fixed in 0.4.0.
3. Duplicate G&W: NOT YET DIAGNOSED. Working hypothesis, not confirmed: the
   dormant Aegis partner is drawn as a G&W. Supporting evidence is that
   `EntryL`/`EntryR` (the spawn scripts) generate `FIGHTER_EFLAME_GENERATE_ARTICLE_DIVER`,
   which is the partner body, and eflame has no model folder of its own for it,
   so it resolves through eflame's body model - the folder this mod overwrites.
   "From the very beginning" matches EntryL. A decisive test is below.

## Decisive test for the duplicate
Spawn as Pyra c06 and press nothing.
  a) If a second figure is present at frame 1, it is the partner (EntryL), not
     an article you summoned.
  b) Press down-B. If the second figure turns into Mythra while the first stays
     G&W, the dormant partner is being rendered with eflame's model, and the
     hypothesis is confirmed.
  c) If the second figure does not change on down-B, it is an article/afterimage
     and the hypothesis is wrong.
