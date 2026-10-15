# Console run 3 - 2026-09-29 - 0.4.0

## CONFIRMED: the costume gate holds
The user tested the vanilla slots and reported they work fine. This is the
negative control that had been missing since run 1, and it is the foundation of
the whole approach: `Agent::new("eflame").set_costume([6, 7])` really does restrict
the overrides to c06/c07, and vanilla Pyra c00-c05, Mythra and real G&W are
untouched.

Gating is no longer an assumption. Phase 1's design risk is retired.

## Still open
1. "the weird model stuff and the sword are still there" - unchanged by 0.4.0.
2. "anything where I'd spawn a projectile like gnw fair and uair don't work" -
   forward air (bomb) and up air (breath). This is the known R1 article omission,
   now confirmed as the top functional gap.
3. Screenshots of the weird models were made on the Switch but did not reach the
   workspace and no attachment arrived. Not yet diagnosed.

## On the sword
The Aegis sword still generates because every unported Pyra script that calls
`generate_article(ESWORD)` is a special, the Final, a ledge move, the
transformation scene or a victory pose. The specials are Pyra's by design until
phase 4, so the sword appearing during side-B / up-B is expected, not a bug.
What is NOT yet established is whether it also appears during ordinary normals.
