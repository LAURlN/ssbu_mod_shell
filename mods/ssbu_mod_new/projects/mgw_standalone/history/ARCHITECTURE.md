# Standalone MGW implementation notes

## p2 correction

p1 reached character select on Switch but lacked portraits and crashed while
initializing Mythra's native sword article. p2 supplies the requested UI textures
and rebuilds Smashline with the late-code offsets verified against the user's
13.0.4 dump. This supersedes p1's choice of the official prebuilt Smashline
binary. Clone Engine itself is still unchanged. See `DIAGNOSIS.md`; the
independent-fighter hardware gate is still pending a successful retest.

## Target and current boundary

The target is one new selectable character with two owned fighter forms, native
Element-style switching, and later the existing custom moves and own costumes.
The vanilla Mythra/Pyra and G&W entries must remain usable alongside it.

p1 implements two independent clone definitions, asset namespaces, named
Smashline callbacks, and runtime identity diagnostics. It does not implement
pair construction or a transition between those forms. It uses the official
unmodified engine binary pinned below. The first required external evidence is
that both base clones load and work on hardware independently and together.

## Findings from pinned upstream source

Clone Engine commit `b420a90de60584e6fc18266a870570dc7fb0435b`:

- `docs/API.md` documents multiple `[[fighter]]` declarations in one manifest
  and clone-specific Smashline registration by name. Kinds are assigned at boot.
- `src/css_registration.rs` constructs normal selectable clone rows, sets
  `fighter_type_normal`, and copies base UI data. This is not a declaration of
  a transforming pair.
- `src/lib.rs`, `clone_kind_of_object`: gets the entry's single custom kind and
  requires that definition's base kind to match the native battle object's kind.
  Two different base forms under one entry cannot both pass that lookup.
- `fighter_clone_kind` and `param_override_kind` also derive identity from the
  entry. `ENTRY_FIGHTER_BOMA` holds one accessor per entry. Article-owner paths
  use these lookups too. Updating only script dispatch would leave inconsistent
  parameter and article routing.
- The 0.3 series provides clone-specific native vtable copies; the 0.2 release
  removed the separate Smashline fork requirement. These facilities do not, by
  themselves, establish Element-style ownership or state transfer.

The source observations above are confirmed by local inspection. Whether this
particular Mythra base can initialize independently, all its native articles
resolve, and callbacks dispatch correctly is still unverified on console.

## Planned engine extension after the p1 gate

Keep three separate identities:

1. **Roster identity:** one selected combo character, one player, stocks, damage
   and result entry. Never replace this with the currently active form's kind.
2. **Object identity:** each live fighter object maps to its own clone definition
   (`mgw_mythra` or `mgw_watch`) and base constructor. Include lifecycle tracking
   so destroyed/reused object IDs cannot inherit stale mappings.
3. **Active form:** owned by the pair's transition state. Only the active form
   receives input and contributes to camera tracking/collision as native Element
   specifies; switching must not repeatedly overwrite the roster identity.

This needs a maintained engine extension for fighter construction, clone lookup,
parameter routing, named ACMD/status dispatch, article ownership, resource load
and destruction. Retain entry-based behavior for ordinary single-form clones.
Do not create a second conflicting set of hooks at the same engine offsets.

## Swap implementation gate

Use the existing native Element traces under
`references/mythra_gamewatch_feasibility` and the original diagnosis as evidence.
Identify and account for all responsibilities before replacing native routines:

- Construct both forms and register ownership before either enters gameplay.
- Follow native capture -> outgoing standby -> activation -> restore ordering.
- Carry posture, ground/air state, facing and kinetic state through the correct
  native transition point. A pair of direct speed writes is not sufficient;
  enabled kinetic energies and native reset timing must be measured.
- Maintain native input/link/visibility/collision and camera ownership through
  the transition, rather than repairing them with per-frame writes.
- Handle damage/stock ownership, death, rebirth, capture, ledges, items, articles,
  match end and cleanup. The inactive fighter must not become a second player.
- Keep collision correction separate from world-coordinate restoration so a
  stale outgoing posture cannot teleport the incoming fighter.

Any copied native routine must have an evidence-backed address/version and an
audit of relocations, literal data, indirect calls, and side effects. Copying
machine-code bytes into a buffer does not make a relocatable clone of Element.
No speculative offsets or copied native machine code are introduced in p1.

## Subsequent gates

1. p1: two independent native clones coexist with each other and originals.
2. Pair construction and destruction with both form identities preserved.
3. Both swap directions: idle, run, jump, fall, hitstun/interrupts where legal,
   ledges, slopes, platforms, blast-zone vicinity, respawn, results and rematch.
   Compare frame-by-frame position, velocity and camera with native Element.
4. Migrate custom moves to named clone agents. Hero's Spin status indices,
   kinetic handling and reversals need their own regression checks. Keep the
   currently disabled grenade experiment disabled until independently fixed.
5. One final CSS entry, costume sets, names/portraits and packaged release.

The p8 to p11 gates are narrower. p8's console log proved the Mythra crash is
the state-5 skip at `0x49748c`: the motion bind at `main + 0x497350` asks
`[module+0x30]`'s vtable `+0x240` method for a state, an answer of 5 skips the
allocation at `0x49749c`, and the tail at `0x4983e4` then dereferences the
holder that was never stored at `0x497d10`. p9 guarded that one branch for the
calls that would otherwise fault, but its own write to `0x49748c` faulted: the
game's text is not writable from a plugin with a plain store. p10 writes
through `skyline::patching::Patch`, the same path Skyline's hooks use, and
reads the word back; the guard then engaged and native built the holder, which
moved the fault to `main + 0x4984d4`, where the object at `holder+0x10` answers
0 to its vtable `+0x38` method and the caller dereferences it. p11 keeps that
guard and mirrors every motion-probe line into
`sd:/ultimate/clone_engine/p11-breadcrumbs.txt`, because Skyline's log is a TCP
stream and the game kills the thread inside the hooked call, so the lines
written just before the fault never arrive. Passing p11 means the Mythra Probe
loads and finishes a match, the breadcrumb file ends on a `[bind]` or `[setup]`
entry with no matching exit (or on a `[force]` line that says why the guard
declined for it), no `CRASH PRECONDITION` line ends the log, and original
Mythra and Game & Watch behave exactly as before.

Do not present a successful build or resource lint as passing any hardware gate.
