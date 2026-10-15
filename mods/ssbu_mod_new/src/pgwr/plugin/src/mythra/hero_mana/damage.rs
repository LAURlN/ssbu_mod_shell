//! Reserved: the donor's hit / shield MP recovery. **Not built.**
//!
//! # What it would do
//!
//! Hero's meter also refills when Hero is hit or blocks. The donor does that in
//! its own event entry (`main+0x854610` -> `0x854a4c`): the event's bit selects
//! `sp_recover_damage_mul` (0.8) or `sp_recover_shield_mul` (0.8), the selected
//! multiplier scales the damage the fighter just took, and the product goes
//! through the same `add_sp` the passive recovery uses. The values are in
//! `super::params` and both are read from the pinned `vl.prc`
//! (`RECOVER_DAMAGE_MUL`, `RECOVER_SHIELD_MUL`).
//!
//! # Why it is not built
//!
//! The recipient cannot observe "this fighter was hit" or "this fighter blocked"
//! from anything it owns. Those are engine events delivered to arbitrary
//! opponents, not to our statuses, our articles or our scripts, and the only
//! sites that see them are `main+0x854610` / `0x854a4c` - Hero's own code. Rule
//! 17 reserves an interception there, and the contract is explicit that the
//! earlier projectile and article approvals do not extend to a damage callback.
//!
//! The tempting shortcuts are all wrong and none of them is implemented:
//!
//! * awarding from our own spark / bolt hit would recover MP for *hitting*
//!   someone, which is not the donor's rule;
//! * awarding every frame while a "was hit" flag is set would turn a single
//!   collision into a stream of awards;
//! * hooking the victim's `CheckDamage` line needs the same reserved
//!   interception.
//!
//! # What is done instead
//!
//! * the numbers and their keys are in `super::params` (tier B, pinned);
//! * the two target sites are byte-verified on the 13.0.4 image by
//!   `tools/audit_hero_mana_native.py` (both MATCH,
//!   `refs/brave_special_n/T-0057/reserved_sites.json`);
//! * the owned `add` in `super` already clamps exactly as the donor's `add_sp`
//!   does, so approving the hook adds one call, not new arithmetic;
//! * the whole module is behind `hero-mana-reserved`, which is **off by
//!   default**, so an ordinary build does not contain a line of it.
//!
//! # What approval would need to name
//!
//! Entry `main+0x854610`, the 16 bytes recorded in `reserved_sites.json`, the
//! event ABI to receive (which is `FighterSpecializer_Brave`'s and is not
//! recovered), how a mismatch disables this and nothing else, and the fact that
//! the damage value has to be the engine's own computed damage, not a
//! re-derivation from the hitbox.
