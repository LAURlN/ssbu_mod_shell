# Super Smash Bros. Ultimate — Pyra / Mythra Clone Test Scenarios

This document defines the complete gameplay verification test suite for the Pyra & Mythra clone fighter (`cflame` / `clight`).
Every `game_` script in `reports/acmd-inventory.json` is covered by at least one scenario.

## Table of Contents

- [SCEN-001: Pyra Ground Normals (Jab, Rapid Jab, Dash Attack)](#scen-001)
- [SCEN-002: Pyra Ground Tilts (F-Tilt angled Hi/Mid/Lw, U-Tilt, D-Tilt)](#scen-002)
- [SCEN-003: Pyra Smash Attacks (F-Smash angled Hi/Mid/Lw, U-Smash, D-Smash)](#scen-003)
- [SCEN-004: Pyra Aerial Attacks (N-Air, F-Air, B-Air, U-Air, D-Air)](#scen-004)
- [SCEN-005: Pyra Grab, Pummel, and Throws (F-Throw, B-Throw, U-Throw, D-Throw)](#scen-005)
- [SCEN-006: Pyra Neutral Special — Flame Nova (Ground & Air, Tap & Charge)](#scen-006)
- [SCEN-007: Pyra Side Special — Blazing End (Normal, Flick, Air, Sword Article)](#scen-007)
- [SCEN-008: Pyra Up Special — Prominence Revolt (Ground, Air, Fire Pillar Article)](#scen-008)
- [SCEN-009: Pyra Down Special — Swap to Mythra (Neutral Ground)](#scen-009)
- [SCEN-010: Mythra Ground Normals (Jab, Rapid Jab, Dash Attack)](#scen-010)
- [SCEN-011: Mythra Ground Tilts (F-Tilt angled Hi/Mid/Lw, U-Tilt, D-Tilt)](#scen-011)
- [SCEN-012: Mythra Smash Attacks (F-Smash angled Hi/Mid/Lw, U-Smash, D-Smash)](#scen-012)
- [SCEN-013: Mythra Aerial Attacks (N-Air, F-Air, B-Air, U-Air, D-Air)](#scen-013)
- [SCEN-014: Mythra Grab, Pummel, and Throws (F-Throw, B-Throw, U-Throw, D-Throw)](#scen-014)
- [SCEN-015: Mythra Neutral Special — Lightning Buster (Charge Levels 1-3, Ground & Air)](#scen-015)
- [SCEN-016: Mythra Side Special — Photon Edge (Ground, Air, Bunshin Afterimages)](#scen-016)
- [SCEN-017: Mythra Up Special — Ray of Punishment & Chroma Dust (Projectiles)](#scen-017)
- [SCEN-018: Mythra Down Special — Swap to Pyra (Neutral Ground)](#scen-018)
- [SCEN-019: Swap Stress Test — In Air & During Jump (Both Directions)](#scen-019)
- [SCEN-020: Swap Stress Test — On Ledge & Hanging (Both Directions)](#scen-020)
- [SCEN-021: Swap Stress Test — In Shield & Guard Buffer (Both Directions)](#scen-021)
- [SCEN-022: Swap Stress Test — During Hitstun & Damage (Both Directions)](#scen-022)
- [SCEN-023: Final Smash — Pyra Ground Hit (Burning Sword with Rex Diver)](#scen-023)
- [SCEN-024: Final Smash — Pyra Ground Whiff](#scen-024)
- [SCEN-025: Final Smash — Pyra Aerial Hit & Aerial Whiff](#scen-025)
- [SCEN-026: Final Smash — Mythra Ground Hit (Sacred Arrow with Rex Diver & Beam)](#scen-026)
- [SCEN-027: Final Smash — Mythra Ground Whiff](#scen-027)
- [SCEN-028: Final Smash — Mythra Aerial Hit & Aerial Whiff](#scen-028)
- [SCEN-029: Final Smash Matchup — Against Kirby](#scen-029)
- [SCEN-030: Final Smash Matchup — Mirror Match (Pyra/Mythra vs Pyra/Mythra)](#scen-030)
- [SCEN-031: Locomotion & Movement (Walk, Dash, Run, Turn, Brake)](#scen-031)
- [SCEN-032: Jump, Fall, Landing, Footstool, and Ceiling Collision](#scen-032)
- [SCEN-033: Shield, Spotdodge, Rolls, and Mythra Foresight](#scen-033)
- [SCEN-034: Ledge Hang and All Getup Options (Normal, Attack, Roll, Jump)](#scen-034)
- [SCEN-035: Damage Reactions, Hitstun, and Tumble](#scen-035)
- [SCEN-036: Teching and Missed Tech Ground Getups](#scen-036)
- [SCEN-037: Rebound, Trip, Dizzy, and Sleep States](#scen-037)
- [SCEN-038: Captured, Cargo Thrown, and Buried States](#scen-038)
- [SCEN-039: Freezing and Water Swimming States](#scen-039)
- [SCEN-040: Light Item Interactions (Pickup, Walk, Throw in All Directions)](#scen-040)
- [SCEN-041: Heavy Item Interactions (Crate, Barrel, Heavy Carry)](#scen-041)
- [SCEN-042: Batter Item Swings (Bat, Beam Sword, Star Rod, Lip's Stick, Fire Bar, Club)](#scen-042)
- [SCEN-043: Shooting Items & Fire Flower (Ray Gun, Super Scope, Drill, Steel Diver)](#scen-043)
- [SCEN-044: Special Items (Hammer, Screw Attack, Daybreak, Special Flag, Grass)](#scen-044)
- [SCEN-045: Taunts, Match Entry, and Victory Sequences](#scen-045)
- [SCEN-046: Kirby Copy Ability (Kirby Flame Nova & Kirby Lightning Buster)](#scen-046)

---

### SCEN-001: Pyra Ground Normals (Jab, Rapid Jab, Dash Attack)
<a id="scen-001"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. At neutral distance, press Attack (A) 3 times to execute Jab 1, 2, and 3.
2. Tap Attack rapidly after Jab 2 to enter Rapid Jab, hold for 60 frames, then release for Rapid End.
3. Dash forward across stage for 30 frames and press Attack (A) to execute Dash Attack.

**Expected Visible Outcome:**
- Pyra performs three consecutive horizontal flaming sword slashes, transitions smoothly into rapid thrusts with fire burst finisher, and performs a lunging diagonal dash slash.

**Expected Trace Markers / Covers:**
- `eflame::game_attack100`
- `eflame::game_attack100end`
- `eflame::game_attack100start`
- `eflame::game_attack100sub`
- `eflame::game_attack11`
- `eflame::game_attack12`
- `eflame::game_attack13`
- `eflame::game_attackdash`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-002: Pyra Ground Tilts (F-Tilt angled Hi/Mid/Lw, U-Tilt, D-Tilt)
<a id="scen-002"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Final Destination | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Tilt Left Stick forward + Attack (A) to execute F-Tilt (mid).
2. Tilt Left Stick up-forward + Attack (A) to execute F-Tilt (high angle).
3. Tilt Left Stick down-forward + Attack (A) to execute F-Tilt (low angle).
4. Tilt Left Stick up + Attack (A) to execute Up-Tilt.
5. Tilt Left Stick down + Attack (A) to execute Down-Tilt.

**Expected Visible Outcome:**
- Pyra executes heavy forward sword swipes angled high, middle, and low with distinct swing arcs; Up-Tilt performs an overhead flaming arc; Down-Tilt executes a low crouching sweep with flame trail.

**Expected Trace Markers / Covers:**
- `eflame::game_attackhi3`
- `eflame::game_attacklw3`
- `eflame::game_attacks3`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-003: Pyra Smash Attacks (F-Smash angled Hi/Mid/Lw, U-Smash, D-Smash)
<a id="scen-003"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Smash Left Stick forward + Attack (A), hold for 60 frames, release (F-Smash mid).
2. Smash Left Stick up-forward + Attack (A), hold 30f, release (F-Smash high).
3. Smash Left Stick down-forward + Attack (A), hold 30f, release (F-Smash low).
4. Smash Left Stick up + Attack (A), hold 60f, release (Up-Smash).
5. Smash Left Stick down + Attack (A), hold 60f, release (Down-Smash).

**Expected Visible Outcome:**
- Pyra charges flaming two-handed strikes; F-Smash swings sword overhead down with explosive flame pillar upon release; Up-Smash performs massive upward thrust; Down-Smash sweeps ground on front then back.

**Expected Trace Markers / Covers:**
- `eflame::game_attackhi4`
- `eflame::game_attacklw4`
- `eflame::game_attacks4`
- `eflame::game_attacks4charge`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-004: Pyra Aerial Attacks (N-Air, F-Air, B-Air, U-Air, D-Air)
<a id="scen-004"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Full hop, press Attack (A) with no direction for Neutral-Air.
2. Full hop, press forward + Attack (A) for Forward-Air.
3. Turn around, full hop, press backward + Attack (A) for Back-Air.
4. Full hop, press up + Attack (A) for Up-Air.
5. Full hop, press down + Attack (A) for Down-Air (meteor spike).

**Expected Visible Outcome:**
- Pyra performs 360-degree spinning aerial slash (N-Air), wide overhead forward swipe (F-Air), powerful backward slash (B-Air), upward horizontal sweeping cut (U-Air), and downward two-handed plunge with meteor hitbox (D-Air).

**Expected Trace Markers / Covers:**
- `eflame::game_attackairb`
- `eflame::game_attackairf`
- `eflame::game_attackairhi`
- `eflame::game_attackairlw`
- `eflame::game_attackairn`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-005: Pyra Grab, Pummel, and Throws (F-Throw, B-Throw, U-Throw, D-Throw)
<a id="scen-005"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Stand in front of opponent, press Grab (Z/L/R).
2. Dash across stage and press Grab for Dash Grab; run past and press back + Grab for Pivot Grab.
3. Hold grab, press Attack (A) twice for Pummel.
4. Throw Forward, Back, Up, and Down across four separate grabs.

**Expected Visible Outcome:**
- Pyra grabs opponent with left hand, pummels with fiery knee, throws forward with flame blast, throws backward spinning opponent behind, tosses upward with fire eruption, and slams downward onto stage.

**Expected Trace Markers / Covers:**
- `eflame::game_catch`
- `eflame::game_catchattack`
- `eflame::game_catchdash`
- `eflame::game_catchturn`
- `eflame::game_throwb`
- `eflame::game_throwf`
- `eflame::game_throwhi`
- `eflame::game_throwlw`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-006: Pyra Neutral Special — Flame Nova (Ground & Air, Tap & Charge)
<a id="scen-006"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. On ground, tap Special (B) for uncharged Flame Nova.
2. On ground, hold Special (B) for 60 frames, then release for full charge Flame Nova.
3. On ground, hold Special (B), press Shield (R) on frame 20 to cancel.
4. In mid-air, tap Special (B) for aerial Flame Nova.
5. In mid-air, hold Special (B) for 45 frames, then release.

**Expected Visible Outcome:**
- Pyra spins sword around herself creating expanding rings of flame. Shield cancel stops charge smoothly. Aerial versions maintain horizontal momentum while spinning.

**Expected Trace Markers / Covers:**
- `eflame::game_specialairn1`
- `eflame::game_specialairn2`
- `eflame::game_specialairn3`
- `eflame::game_specialairn4`
- `eflame::game_specialairnhold`
- `eflame::game_specialairnstart`
- `eflame::game_specialn1`
- `eflame::game_specialn1common`
- `eflame::game_specialn2`
- `eflame::game_specialn2common`
- `eflame::game_specialn3`
- `eflame::game_specialn3common`
- `eflame::game_specialn4`
- `eflame::game_specialn4common`
- `eflame::game_specialnhold`
- `eflame::game_specialnstart`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-007: Pyra Side Special — Blazing End (Normal, Flick, Air, Sword Article)
<a id="scen-007"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Tilt forward + Special (B) for standard Blazing End.
2. Smash forward + Special (B) for smash-flick Blazing End (extended range).
3. In air, tilt forward + Special (B) for aerial Blazing End.
4. In air, smash forward + Special (B) for aerial smash-flick Blazing End.
5. Observe sword article behavior while spinning and returning to Pyra's hand.

**Expected Visible Outcome:**
- Pyra throws her Aegis sword forward; sword article (`eflame_esword`) spins in place inflicting multi-hits and flame pillars (`eflame_blazepillar`), then flies back to Pyra. Pyra cannot use sword attacks while unarmed.

**Expected Trace Markers / Covers:**
- `eflame::game_specialairs`
- `eflame::game_specialairsflick`
- `eflame::game_specials`
- `eflame::game_specialsflick`
- `eflame_blazepillar::game_finalattack`
- `eflame_esword::game_flyflickl`
- `eflame_esword::game_flyflickr`
- `eflame_esword::game_flyl`
- `eflame_esword::game_flyr`
- `eflame_esword::game_hit`
- `eflame_esword::game_reflectedl`
- `eflame_esword::game_reflectedr`
- `eflame_esword::game_rotate`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-008: Pyra Up Special — Prominence Revolt (Ground, Air, Fire Pillar Article)
<a id="scen-008"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. On ground, press Up + Special (B) to execute Prominence Revolt.
2. In mid-air offstage, press Up + Special (B) to recover to ledge.
3. Execute Up-B directly hitting opponent on ground to confirm fire pillar eruption.

**Expected Visible Outcome:**
- Pyra leaps upward with rising flaming slash, then plunges downward sword-first into the ground, triggering an erupting flame pillar (`eflame_firepillar`) upon ground impact.

**Expected Trace Markers / Covers:**
- `eflame::game_specialairhifall`
- `eflame::game_specialairhijump`
- `eflame::game_specialairhistart`
- `eflame::game_specialhi`
- `eflame::game_specialhistart`
- `eflame_firepillar::game_specialhi`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-009: Pyra Down Special — Swap to Mythra (Neutral Ground)
<a id="scen-009"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. While standing neutral on ground, press Down + Special (B).
2. Observe transition frames, sheath/open sword sub-animations, and transformation flash.

**Expected Visible Outcome:**
- Pyra sheath/open sword animations trigger (`closesword*` / `opensword*`), a radiant light flash envelops fighter, and Mythra emerges in idle stance with zero lag or crash.

**Expected Trace Markers / Covers:**
- `eflame::game_closesword1f`
- `eflame::game_closesword2f`
- `eflame::game_closesword3f`
- `eflame::game_opensword1f`
- `eflame::game_opensword2f`
- `eflame::game_opensword3f`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-010: Mythra Ground Normals (Jab, Rapid Jab, Dash Attack)
<a id="scen-010"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Press Attack (A) 3 times for Jab 1, 2, 3.
2. Tap Attack rapidly after Jab 2 for Rapid Jab, hold 60f, release for Rapid End.
3. Dash forward and press Attack (A) for Dash Attack.

**Expected Visible Outcome:**
- Mythra executes lightning-fast horizontal slashes, transitions to flurry of light thrusts, and performs swift lunging horizontal dash cut.

**Expected Trace Markers / Covers:**
- `elight::game_attack100`
- `elight::game_attack100end`
- `elight::game_attack100start`
- `elight::game_attack100sub`
- `elight::game_attack11`
- `elight::game_attack12`
- `elight::game_attack13`
- `elight::game_attackdash`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-011: Mythra Ground Tilts (F-Tilt angled Hi/Mid/Lw, U-Tilt, D-Tilt)
<a id="scen-011"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Final Destination | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Tilt forward + Attack (A) for F-Tilt (mid).
2. Tilt up-forward + Attack (A) for F-Tilt (high angle).
3. Tilt down-forward + Attack (A) for F-Tilt (low angle).
4. Tilt up + Attack (A) for Up-Tilt.
5. Tilt down + Attack (A) for Down-Tilt.

**Expected Visible Outcome:**
- Rapid light-infused horizontal slashes angled across three trajectories, fast upward sweeping anti-air cut, and crouching slide kick/slash combo.

**Expected Trace Markers / Covers:**
- `elight::game_attackhi3`
- `elight::game_attacklw3`
- `elight::game_attacks3`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-012: Mythra Smash Attacks (F-Smash angled Hi/Mid/Lw, U-Smash, D-Smash)
<a id="scen-012"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Smash forward + Attack (A), hold 60f, release (F-Smash mid).
2. Smash up-forward + Attack (A), hold 30f, release (F-Smash high).
3. Smash down-forward + Attack (A), hold 30f, release (F-Smash low).
4. Smash up + Attack (A), hold 60f, release (Up-Smash).
5. Smash down + Attack (A), hold 60f, release (Down-Smash).

**Expected Visible Outcome:**
- Mythra charges light energy; F-Smash delivers horizontal forward burst cut; Up-Smash delivers multi-hit pillar of light above head; Down-Smash executes fast spinning ground sweep on both sides.

**Expected Trace Markers / Covers:**
- `elight::game_attackhi4`
- `elight::game_attacklw4`
- `elight::game_attacks4`
- `elight::game_attacks4charge`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-013: Mythra Aerial Attacks (N-Air, F-Air, B-Air, U-Air, D-Air)
<a id="scen-013"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Full hop, press Attack (A) with no direction for Neutral-Air.
2. Full hop, press forward + Attack (A) for Forward-Air.
3. Turn around, full hop, press backward + Attack (A) for Back-Air.
4. Full hop, press up + Attack (A) for Up-Air.
5. Full hop, press down + Attack (A) for Down-Air.

**Expected Visible Outcome:**
- Multi-hit spinning aerial ring (N-Air), quick forward swipe (F-Air), sharp backward slash (B-Air), horizontal upward juggling cut (U-Air), and downward spike/slash (D-Air).

**Expected Trace Markers / Covers:**
- `elight::game_attackairb`
- `elight::game_attackairf`
- `elight::game_attackairhi`
- `elight::game_attackairlw`
- `elight::game_attackairn`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-014: Mythra Grab, Pummel, and Throws (F-Throw, B-Throw, U-Throw, D-Throw)
<a id="scen-014"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Stand near opponent, press Grab (Z).
2. Dash across stage, press Grab (Dash Grab); run past, back + Grab (Pivot Grab).
3. Hold grab, press Attack (A) twice for Pummel.
4. Execute Forward Throw, Back Throw, Up Throw, Down Throw.

**Expected Visible Outcome:**
- Mythra grabs with one hand, knee strikes (Pummel), blasts forward with light energy, spins opponent backward, tosses upward with vertical light beam, and sweeps leg to pin opponent to floor.

**Expected Trace Markers / Covers:**
- `elight::game_catch`
- `elight::game_catchattack`
- `elight::game_catchdash`
- `elight::game_catchturn`
- `elight::game_throwb`
- `elight::game_throwf`
- `elight::game_throwhi`
- `elight::game_throwlw`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-015: Mythra Neutral Special — Lightning Buster (Charge Levels 1-3, Ground & Air)
<a id="scen-015"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Tap Special (B) on ground for Level 1 Lightning Buster.
2. Hold Special (B) for 30f on ground for Level 2 Lightning Buster.
3. Hold Special (B) for 60f on ground for Level 3 (max charge) Lightning Buster.
4. In air, execute uncharged and fully charged Lightning Buster.

**Expected Visible Outcome:**
- Mythra charges blade with electric light particles; upon release she slashes multiple times in front of her with invincible startup frames and finishing strike with extended range at max charge.

**Expected Trace Markers / Covers:**
- `elight::game_specialairn`
- `elight::game_specialairn2`
- `elight::game_specialairnhit`
- `elight::game_specialairnhold`
- `elight::game_specialn`
- `elight::game_specialn2`
- `elight::game_specialnhold`
- `elight::game_specialnstart`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-016: Mythra Side Special — Photon Edge (Ground, Air, Bunshin Afterimages)
<a id="scen-016"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. On ground, press Side + Special (B) across center stage.
2. In mid-air, press Side + Special (B) toward ledge.
3. Execute near ledge to trigger cliff-stop interaction (`specialcliffs*`).

**Expected Visible Outcome:**
- Mythra teleports forward into flurry of multi-directional slashes spawning bunshin article clones (`elight_bunshin` 0 through 5); halts at ledge edge safely if on ground.

**Expected Trace Markers / Covers:**
- `elight::game_specialairs`
- `elight::game_specialairsend`
- `elight::game_specialairsstart`
- `elight::game_specials`
- `elight::game_specialsend`
- `elight::game_specialsstart`
- `elight_bunshin::game_hit`
- `elight_bunshin::game_specialairs0`
- `elight_bunshin::game_specialairs1`
- `elight_bunshin::game_specialairs2`
- `elight_bunshin::game_specialairs3`
- `elight_bunshin::game_specialairs4`
- `elight_bunshin::game_specialairs5`
- `elight_bunshin::game_specialcliffs3`
- `elight_bunshin::game_specialcliffs4`
- `elight_bunshin::game_specialcliffs5`
- `elight_bunshin::game_specials0`
- `elight_bunshin::game_specials1`
- `elight_bunshin::game_specials2`
- `elight_bunshin::game_specials3`
- `elight_bunshin::game_specials4`
- `elight_bunshin::game_specials5`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-017: Mythra Up Special — Ray of Punishment & Chroma Dust (Projectiles)
<a id="scen-017"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. On ground, press Up + Special (B) and do not press B again (Ray of Punishment).
2. On ground, press Up + Special (B) and tap Special (B) repeatedly at peak of jump (Chroma Dust).
3. In mid-air offstage, execute Up-B to recover to ledge.

**Expected Visible Outcome:**
- Mythra leaps upward; Ray of Punishment fires single downward explosive light arrow (`elight_meteor`, `elight_exprosiveshot`); Chroma Dust fires spread volley of light projectiles (`elight_spreadbullet`).

**Expected Trace Markers / Covers:**
- `elight::game_specialairhi1`
- `elight::game_specialairhi2`
- `elight::game_specialairhiend`
- `elight::game_specialairhijump`
- `elight::game_specialairhistart`
- `elight::game_specialhistart`
- `elight_exprosiveshot::game_burst`
- `elight_exprosiveshot::game_fly`
- `elight_meteor::game_finalattack`
- `elight_spreadbullet::game_fly`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-018: Mythra Down Special — Swap to Pyra (Neutral Ground)
<a id="scen-018"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. While standing neutral on ground, press Down + Special (B).
2. Observe transition frames, sheath/open sword sub-animations, and transformation flash.

**Expected Visible Outcome:**
- Mythra sheath/open sword animations trigger (`closesword*` / `opensword*`), radiant light flash appears, and Pyra emerges in idle stance with zero lag or crash.

**Expected Trace Markers / Covers:**
- `elight::game_closesword1f`
- `elight::game_closesword2f`
- `elight::game_closesword3f`
- `elight::game_opensword1f`
- `elight::game_opensword2f`
- `elight::game_opensword3f`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-019: Swap Stress Test — In Air & During Jump (Both Directions)
<a id="scen-019"></a>

**Setup:**
- Fighter: Pyra / Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. As Pyra, full hop; at apex of jump press Down + Special (B) to swap to Mythra in air.
2. As Mythra, double jump; during rising jump momentum press Down + Special (B) to swap to Pyra in air.
3. Fast fall immediately after swapping to land on platform.

**Expected Visible Outcome:**
- Swap executes cleanly in mid-air (`specialairlw`) preserving momentum; fighter transitions seamlessly and lands with normal landing lag.

**Expected Trace Markers / Covers:**
- *(Behavioral state check; covers shared game mechanics)*

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-020: Swap Stress Test — On Ledge & Hanging (Both Directions)
<a id="scen-020"></a>

**Setup:**
- Fighter: Pyra / Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. As Pyra, drop off stage, grab ledge, and attempt Down-B input during ledge hang.
2. Buffer Down-B during ledge climb / jump getup.
3. Repeat with Mythra on ledge.

**Expected Visible Outcome:**
- Ledge grab state correctly handles swap input buffering without breaking ledge hang state or disconnecting fighter from ledge.

**Expected Trace Markers / Covers:**
- *(Behavioral state check; covers shared game mechanics)*

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-021: Swap Stress Test — In Shield & Guard Buffer (Both Directions)
<a id="scen-021"></a>

**Setup:**
- Fighter: Pyra / Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. As Pyra, hold Shield (R); while shielding, press Down + Special (B) with Special button.
2. Release shield during swap transition.
3. Repeat with Mythra.

**Expected Visible Outcome:**
- Fighter drops shield cleanly (`guardoff`) and executes swap without shield lockup or input rejection.

**Expected Trace Markers / Covers:**
- *(Behavioral state check; covers shared game mechanics)*

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-022: Swap Stress Test — During Hitstun & Damage (Both Directions)
<a id="scen-022"></a>

**Setup:**
- Fighter: Pyra / Mythra | Opponent: Mario (CPU Lv 9) | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. As Pyra, allow Mario to strike with F-Smash; mash Down + Special (B) during hitstun frames.
2. Confirm swap does not bypass hitstun, but buffers and executes on first actionable frame.
3. Repeat with Mythra.

**Expected Visible Outcome:**
- Hitstun rules enforced correctly; swap buffers cleanly and executes on frame 1 of actionability without state corruption.

**Expected Trace Markers / Covers:**
- *(Behavioral state check; covers shared game mechanics)*

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-023: Final Smash — Pyra Ground Hit (Burning Sword with Rex Diver)
<a id="scen-023"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, FS Meter On, Damage Ratio 1.0x

**Inputs:**
1. Fill FS Meter or acquire Smash Ball. Stand 2 character widths from Mario.
2. Press Special (B) with no direction to execute Burning Sword.
3. Connect initial slash to trigger cutscene.

**Expected Visible Outcome:**
- Pyra slashes forward; on hit, cinematic cutscene initiates (`game_visualscene01`-`02`), Rex (`element_diver`) appears with `ffinalstart`/`ffinalattack`, executing Burning Sword cinematic and high-knockback launch.

**Expected Trace Markers / Covers:**
- `eflame::game_final`
- `eflame::game_finalattack`
- `eflame::game_finalattackcommon`
- `eflame::game_visualscene01`
- `eflame::game_visualscene02`
- `element_diver::game_ffinalattack`
- `element_diver::game_ffinalstart`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-024: Final Smash — Pyra Ground Whiff
<a id="scen-024"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario (standing at opposite ledge) | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, FS Meter On, Damage Ratio 1.0x

**Inputs:**
1. Stand alone on center platform; activate Final Smash (B) with no opponent nearby.
2. Allow full whiff animation to complete without interruption.

**Expected Visible Outcome:**
- Pyra lunges forward with flaming sword slash (`game_finall`); on missing, she recovers into normal idle stance after whiff recovery frames.

**Expected Trace Markers / Covers:**
- `eflame::game_finall`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-025: Final Smash — Pyra Aerial Hit & Aerial Whiff
<a id="scen-025"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, FS Meter On, Damage Ratio 1.0x

**Inputs:**
1. Jump into air above Mario, activate Final Smash (B) to connect aerial Burning Sword.
2. In subsequent attempt, jump in mid-air offstage and activate Final Smash to whiff in air.

**Expected Visible Outcome:**
- Aerial hit transitions smoothly into Rex diver cinematic (`game_ffinalairstart`, `game_finalair`, `game_finalairattack`); aerial whiff (`game_finalairl`) completes slash and places Pyra into fall special state.

**Expected Trace Markers / Covers:**
- `eflame::game_finalair`
- `eflame::game_finalairattack`
- `eflame::game_finalairl`
- `element_diver::game_ffinalairstart`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-026: Final Smash — Mythra Ground Hit (Sacred Arrow with Rex Diver & Beam)
<a id="scen-026"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, FS Meter On, Damage Ratio 1.0x

**Inputs:**
1. With full FS Meter, stand 2 character widths from Mario.
2. Press Special (B) with no direction to execute Sacred Arrow.
3. Connect initial slash to trigger cutscene.

**Expected Visible Outcome:**
- Mythra slashes forward; cinematic initiates (`game_visualscene01`-`04`), Rex (`element_diver`) leaps in (`lfinalstart`/`lfinalattack`), summoning rain of light arrows and beam strikes (`elight_beam`).

**Expected Trace Markers / Covers:**
- `element_diver::game_lfinalattack`
- `element_diver::game_lfinalstart`
- `elight::game_final`
- `elight::game_finalattack`
- `elight::game_finalattackcommon`
- `elight::game_visualscene01`
- `elight::game_visualscene02`
- `elight::game_visualscene03`
- `elight::game_visualscene04`
- `elight_beam::game_finalattack`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-027: Final Smash — Mythra Ground Whiff
<a id="scen-027"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, FS Meter On, Damage Ratio 1.0x

**Inputs:**
1. Stand alone on platform, activate Final Smash (B) away from opponent.
2. Allow full whiff animation to complete.

**Expected Visible Outcome:**
- Mythra executes lunging horizontal light slash (`game_finall`); on missing, cutscene does not trigger and Mythra returns to idle stance.

**Expected Trace Markers / Covers:**
- `elight::game_finall`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-028: Final Smash — Mythra Aerial Hit & Aerial Whiff
<a id="scen-028"></a>

**Setup:**
- Fighter: Mythra (Costume 01) | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, FS Meter On, Damage Ratio 1.0x

**Inputs:**
1. Jump into air above Mario, activate Final Smash (B) to connect aerial Sacred Arrow.
2. Jump offstage and activate Final Smash to whiff in air.

**Expected Visible Outcome:**
- Aerial hit connects and starts aerial Rex diver cinematic (`game_lfinalairstart`, `game_finalair`, `game_finalairattack`); aerial whiff (`game_finalairl`) finishes with normal fall recovery.

**Expected Trace Markers / Covers:**
- `element_diver::game_lfinalairstart`
- `elight::game_finalair`
- `elight::game_finalairattack`
- `elight::game_finalairl`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-029: Final Smash Matchup — Against Kirby
<a id="scen-029"></a>

**Setup:**
- Fighter: Pyra / Mythra | Opponent: Kirby | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, FS Meter On, Damage Ratio 1.0x

**Inputs:**
1. As Pyra, activate Final Smash on Kirby.
2. As Mythra, activate Final Smash on Kirby.

**Expected Visible Outcome:**
- Cinematic cutscenes and knockback physics calculate correctly against Kirby's small hurtbox and lightweight parameters.

**Expected Trace Markers / Covers:**
- *(Behavioral state check; covers shared game mechanics)*

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-030: Final Smash Matchup — Mirror Match (Pyra/Mythra vs Pyra/Mythra)
<a id="scen-030"></a>

**Setup:**
- Fighter: Pyra (Costume 01) | Opponent: Mythra (Costume 02) | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, FS Meter On, Damage Ratio 1.0x

**Inputs:**
1. Connect Burning Sword on opponent Mythra.
2. Swap to Mythra, connect Sacred Arrow on opponent Pyra.

**Expected Visible Outcome:**
- Both cinematic sequences execute flawlessly with Rex assist appearing without duplicate entity ID or article conflict.

**Expected Trace Markers / Covers:**
- *(Behavioral state check; covers shared game mechanics)*

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-031: Locomotion & Movement (Walk, Dash, Run, Turn, Brake)
<a id="scen-031"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Final Destination | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Gently push Left Stick forward for Slow Walk, medium for Middle Walk, full for Fast Walk.
2. Flick stick for Dash; hold for Run.
3. While running, turn stick backward for TurnRun, or release for RunBrake / TurnRunBrake.
4. Repeat for both Pyra and Mythra.

**Expected Visible Outcome:**
- Clean transitions between walking speeds, dash startup, sustained run, turnaround skid, and braking animations with proper dust particles.

**Expected Trace Markers / Covers:**
- `eflame::game_dash`
- `eflame::game_runbrakel`
- `eflame::game_runbraker`
- `eflame::game_turndash`
- `eflame::game_turnrun`
- `elight::game_dash`
- `elight::game_runbrakel`
- `elight::game_runbraker`
- `elight::game_turndash`
- `elight::game_turnrun`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-032: Jump, Fall, Landing, Footstool, and Ceiling Collision
<a id="scen-032"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Hold Down on Left Stick to squat (crouch).
2. Tap Jump for short hop, hold Jump for full hop (forward and backward jumps).
3. Double jump in mid-air (forward and backward).
4. Jump and fall without attacking (Fall, FallAerial); fall after special move (FallSpecial).
5. Land with Light Landing, Heavy Landing (after high fall), and FallSpecial Landing.
6. Jump directly on Mario's head for footstool jump (`stepposeair`).
7. Jump up under Battlefield side platform to hit ceiling (`stopceil`).

**Expected Visible Outcome:**
- Fluid jump arcs, squat transitions, landing compression frames, footstool bounce, and ceiling bump reaction.

**Expected Trace Markers / Covers:**
- `eflame::game_squat`
- `eflame::game_stepposeair`
- `eflame::game_stopceil`
- `elight::game_landingairn`
- `elight::game_landingfallspecial`
- `elight::game_squat`
- `elight::game_stepposeair`
- `elight::game_stopceil`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-033: Shield, Spotdodge, Rolls, and Mythra Foresight
<a id="scen-033"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario (CPU Lv 9) | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Press and hold Shield (R) for GuardOn, Guard, and release for GuardOff.
2. Hold shield, allow opponent attack to hit for GuardDamage.
3. While shielding, push Left Stick down for Spotdodge (EscapeN).
4. While shielding, push Left Stick forward/backward for Roll (EscapeF / EscapeB).
5. In air, press Shield (R) with and without directional stick for Air Dodge (EscapeAir, EscapeAirSlide).
6. As Mythra, time spotdodge/roll right before Mario's attack connects to trigger Foresight (`escapenforesight`, `escapefforesight`, `escapebforesight`).

**Expected Visible Outcome:**
- Shield bubble renders properly, rolls and dodges grant standard invincibility frames. Mythra's Foresight activates slow-motion effect on attacker and reduces incoming damage.

**Expected Trace Markers / Covers:**
- `eflame::game_escapeair`
- `eflame::game_escapeairslide`
- `eflame::game_escapef`
- `elight::game_escapeair`
- `elight::game_escapeairslide`
- `elight::game_escapeairslideforesight`
- `elight::game_escapeb`
- `elight::game_escapef`
- `elight::game_escapefforesight`
- `elight::game_escapen`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-034: Ledge Hang and All Getup Options (Normal, Attack, Roll, Jump)
<a id="scen-034"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Drop from stage and grab ledge (CliffCatch / CliffWait).
2. Push Left Stick forward for Normal Climb (CliffClimb).
3. Press Attack (A) for Ledge Attack (CliffAttack).
4. Press Shield (R) for Ledge Roll (CliffEscape).
5. Push Left Stick up / press Jump for Ledge Jump 1, 2, 3 (CliffJump1, CliffJump2, CliffJump3).

**Expected Visible Outcome:**
- Clean ledge grab snap-to, correct intangible frames during hang, and responsive execution of all four recovery options.

**Expected Trace Markers / Covers:**
- `eflame::game_cliffattack`
- `eflame::game_cliffcatch`
- `eflame::game_cliffescape`
- `elight::game_cliffattack`
- `elight::game_cliffcatch`
- `elight::game_cliffescape`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-035: Damage Reactions, Hitstun, and Tumble
<a id="scen-035"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Receive Mario's Jab for light flinch damage (`damagelv1`, `damagen1`).
2. Receive Mario's F-Tilt and D-Tilt for medium damage (`damagelv2`, `damagehi1`, `damagelw1`).
3. Receive Mario's F-Smash for heavy launch damage (`damagelv3`, `damageflyn`, `damageflyhi`, `damageflylw`, `damageflytop`).
4. Receive electric attack (e.g. Pikachu Thunder / Item) for `damageelec`.
5. Enter tumble in mid-air (`damagefall`, `damageair1`-`3`).

**Expected Visible Outcome:**
- Accurate flinch and knockback animations matching vanilla knockback velocities and stun durations.

**Expected Trace Markers / Covers:**
- `elight::game_damageair1`
- `elight::game_damageair2`
- `elight::game_damageair3`
- `elight::game_damagehi1`
- `elight::game_damagehi2`
- `elight::game_damagehi3`
- `elight::game_damagelw1`
- `elight::game_damagelw2`
- `elight::game_damagelw3`
- `elight::game_damagen1`
- `elight::game_damagen2`
- `elight::game_damagen3`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-036: Teching and Missed Tech Ground Getups
<a id="scen-036"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Get launched in tumble; press Shield (R) right before hitting ground for Neutral Tech (`passive`).
2. Hold forward/backward + Shield before landing for Tech Roll (`passivestandf`, `passivestandb`).
3. Tech against wall (`passivewall`, `passivewalljump`) and ceiling (`passiveceiling`).
4. Miss tech on ground; observe bounce (`downboundu`, `downboundd`), ground lie (`downwaitu`, `downwaitd`), and getup options: Neutral Stand (`downstandu`, `downstandd`), Roll (`downstandfu`, `downstandbu`, `downstandfb`, `downstandbd`), and Getup Attack (`downattacku`, `downattackd`).

**Expected Visible Outcome:**
- All ground, wall, ceiling teching timings and missed tech getup animations function identically to vanilla.

**Expected Trace Markers / Covers:**
- `eflame::game_downattackd`
- `eflame::game_downattacku`
- `eflame::game_downboundu`
- `eflame::game_downeatd`
- `eflame::game_downeatu`
- `eflame::game_downwaitd`
- `eflame::game_passiveceil`
- `elight::game_downattackd`
- `elight::game_downattacku`
- `elight::game_downboundu`
- `elight::game_downeatd`
- `elight::game_downeatu`
- `elight::game_downwaitd`
- `elight::game_passiveceil`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-037: Rebound, Trip, Dizzy, and Sleep States
<a id="scen-037"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Hit clashing attack to trigger attack rebound (`rebound`).
2. Get tripped by Banana Peel or low sweep (`slip`, `slipwait`, `slipstand`, `slipattack`).
3. Have shield broken to enter shield-break dizzy (`furafura`, `furafurastartu`, `furafurastartd`, `furafuraend`).
4. Get put to sleep (Jigglypuff Sing) to enter sleep state (`sleep`, `sleeploop`, `sleepend`).

**Expected Visible Outcome:**
- Proper recoil animation on rebound, ground trip slide with recovery options, wobbling dizzy animation, and slumber loop animation.

**Expected Trace Markers / Covers:**
- `eflame::game_furafurastartd`
- `eflame::game_furafurastartu`
- `eflame::game_slip`
- `eflame::game_slipattack`
- `elight::game_furafurastartd`
- `elight::game_furafurastartu`
- `elight::game_slip`
- `elight::game_slipattack`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-038: Captured, Cargo Thrown, and Buried States
<a id="scen-038"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Donkey Kong / Inkling | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Get grabbed by opponent (`capturepulledlw`, `capturepulledhi`, `capturewaitlw`, `capturewaithi`).
2. Receive pummel while held (`capturedamagelw`, `capturedamagehi`).
3. Mash out of grab (`capturecut`, `capturejump`).
4. Get cargo grabbed by Donkey Kong and thrown.
5. Get buried by Inkling Roller or Pit Down-B (`downeatd`, `downeatu`).

**Expected Visible Outcome:**
- Fighter correctly exhibits struggle animation while grabbed, breaks free smoothly upon mashing, and pops out of buried ground state.

**Expected Trace Markers / Covers:**
- `eflame::game_downeatd`
- `eflame::game_downeatu`
- `elight::game_capturewaithi`
- `elight::game_capturewaitlw`
- `elight::game_downeatd`
- `elight::game_downeatu`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-039: Freezing and Water Swimming States
<a id="scen-039"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Great Bay / Delfino Plaza | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. Get hit by Freezie item or freezing attack (`icestart`, `ice`, `iceend`).
2. Jump into water on swimming stage (`swimin`, `swim`, `swimf`, `swimturn`, `swimend`).
3. Remain in deep water until stamina depletes (`swimdrown`, `drown`).

**Expected Visible Outcome:**
- Ice block encasement renders and breaks; swimming strokes animate smoothly with correct surface physics and drowning sequence.

**Expected Trace Markers / Covers:**
- *(Behavioral state check; covers shared game mechanics)*

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-040: Light Item Interactions (Pickup, Walk, Throw in All Directions)
<a id="scen-040"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items: Mr. Saturn, Bob-omb, Food | Damage Ratio 1.0x

**Inputs:**
1. Stand near light item, press Attack (A) to pick up (`itemlightget`, `itemlightpickup`, `itemlightwalkget`).
2. Walk while holding light item (`itemlightwalkeat` when picking up food).
3. Throw item forward, back, up, down on ground (`itemlightthrowf`, `itemlightthrowb`, `itemlightthrowhi`, `itemlightthrowlw`).
4. Throw item smash forward, back, up, down (`itemlightthrowf4`, `itemlightthrowb4`, `itemlightthrowhi4`, `itemlightthrowlw4`).
5. Dash throw and drop item (`itemlightthrowdash`, `itemlightthrowdrop`).
6. In air, throw item in 4 directions normal and smash (`itemlightthrowair*`).
7. Equip Super Leaf or Rocket Belt and walk (`itemlegswalkf`, `itemlegswalkb`).

**Expected Visible Outcome:**
- Clean item pickup and tossing animations across all 16 throw variants, food eating, and leg item walking animations.

**Expected Trace Markers / Covers:**
- `eflame::game_itemlighteat`
- `eflame::game_itemlightget`
- `eflame::game_itemlightthrowairb`
- `eflame::game_itemlightthrowairb4`
- `eflame::game_itemlightthrowairf`
- `eflame::game_itemlightthrowairf4`
- `eflame::game_itemlightthrowairhi`
- `eflame::game_itemlightthrowairhi4`
- `eflame::game_itemlightthrowairlw`
- `eflame::game_itemlightthrowairlw4`
- `eflame::game_itemlightthrowb`
- `eflame::game_itemlightthrowb4`
- `eflame::game_itemlightthrowdash`
- `eflame::game_itemlightthrowdrop`
- `eflame::game_itemlightthrowf`
- `eflame::game_itemlightthrowf4`
- `eflame::game_itemlightthrowhi`
- `eflame::game_itemlightthrowhi4`
- `eflame::game_itemlightthrowlw`
- `eflame::game_itemlightthrowlw4`
- `eflame::game_itemlightwalkeat`
- `eflame::game_itemlightwalkget`
- `elight::game_itemlighteat`
- `elight::game_itemlightget`
- `elight::game_itemlightthrowairb`
- `elight::game_itemlightthrowairb4`
- `elight::game_itemlightthrowairf`
- `elight::game_itemlightthrowairf4`
- `elight::game_itemlightthrowairhi`
- `elight::game_itemlightthrowairhi4`
- `elight::game_itemlightthrowairlw`
- `elight::game_itemlightthrowairlw4`
- `elight::game_itemlightthrowb`
- `elight::game_itemlightthrowb4`
- `elight::game_itemlightthrowdash`
- `elight::game_itemlightthrowdrop`
- `elight::game_itemlightthrowf`
- `elight::game_itemlightthrowf4`
- `elight::game_itemlightthrowhi`
- `elight::game_itemlightthrowhi4`
- `elight::game_itemlightthrowlw`
- `elight::game_itemlightthrowlw4`
- `elight::game_itemlightwalkeat`
- `elight::game_itemlightwalkget`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-041: Heavy Item Interactions (Crate, Barrel, Heavy Carry)
<a id="scen-041"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items: Crates & Barrels | Damage Ratio 1.0x

**Inputs:**
1. Approach heavy crate, press Attack (A) to lift (`itemheavyget`, `itemheavypickup`).
2. Walk across stage carrying crate (`itemheavywalk`).
3. Throw heavy item forward, back, up, down normal and smash (`itemheavythrow*`).

**Expected Visible Outcome:**
- Fighter lifts heavy item with two hands, walks with heavy burden animation, and hurls object with full physical follow-through.

**Expected Trace Markers / Covers:**
- `eflame::game_itemheavyget`
- `eflame::game_itemheavythrowb`
- `eflame::game_itemheavythrowb4`
- `eflame::game_itemheavythrowf`
- `eflame::game_itemheavythrowf4`
- `eflame::game_itemheavythrowhi`
- `eflame::game_itemheavythrowhi4`
- `eflame::game_itemheavythrowlw`
- `eflame::game_itemheavythrowlw4`
- `elight::game_itemheavyget`
- `elight::game_itemheavythrowb`
- `elight::game_itemheavythrowb4`
- `elight::game_itemheavythrowf`
- `elight::game_itemheavythrowf4`
- `elight::game_itemheavythrowhi`
- `elight::game_itemheavythrowhi4`
- `elight::game_itemheavythrowlw`
- `elight::game_itemheavythrowlw4`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-042: Batter Item Swings (Bat, Beam Sword, Star Rod, Lip's Stick, Fire Bar, Club)
<a id="scen-042"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items: Bat, Beam Sword, Star Rod, Lip's Stick, Fire Bar, Ore Club, Death's Scythe

**Inputs:**
1. Pick up Home-Run Bat; execute tilt swing 1, 3, dash swing, and smash swing 4 (`batswing*`).
2. Pick up Beam Sword; execute swings 1, 3, dash, and smash 4 (`swordswing*`).
3. Pick up Star Rod; execute swings 1, 3, dash, and smash 4 (`starrodswing*`).
4. Pick up Lip's Stick; execute swings 1, 3, dash, and smash 4 (`lipstickswing*`).
5. Pick up Fire Bar; execute swings 1, 3, dash, and smash 4 (`firebarswing*`).
6. Pick up Ore Club; execute swings 1, 3, dash, and smash 4 (`clubswing*`).
7. Pick up Death's Scythe; execute swings 3 and 4 (`deathscytheswing*`).

**Expected Visible Outcome:**
- All batter weapons swing with correct weapon range, hitboxes, and projectile generation (Star Rod stars, Ore Club tornadoes).

**Expected Trace Markers / Covers:**
- `eflame::game_batswing1`
- `eflame::game_batswing3`
- `eflame::game_batswing4`
- `eflame::game_batswingdash`
- `eflame::game_clubswing1`
- `eflame::game_clubswing3`
- `eflame::game_clubswing4`
- `eflame::game_clubswing4charge`
- `eflame::game_clubswingdash`
- `eflame::game_deathscytheswing3`
- `eflame::game_deathscytheswing4`
- `eflame::game_firebarswing1`
- `eflame::game_firebarswing3`
- `eflame::game_firebarswing4`
- `eflame::game_firebarswingdash`
- `eflame::game_lipstickswing1`
- `eflame::game_lipstickswing3`
- `eflame::game_lipstickswing4`
- `eflame::game_lipstickswingdash`
- `eflame::game_starrodswing1`
- `eflame::game_starrodswing3`
- `eflame::game_starrodswing4`
- `eflame::game_starrodswingdash`
- `eflame::game_swordswing1`
- `eflame::game_swordswing3`
- `eflame::game_swordswing4`
- `eflame::game_swordswingdash`
- `elight::game_batswing1`
- `elight::game_batswing3`
- `elight::game_batswing4`
- `elight::game_batswingdash`
- `elight::game_clubswing1`
- `elight::game_clubswing3`
- `elight::game_clubswing4`
- `elight::game_clubswing4charge`
- `elight::game_clubswingdash`
- `elight::game_deathscytheswing3`
- `elight::game_deathscytheswing4`
- `elight::game_firebarswing1`
- `elight::game_firebarswing3`
- `elight::game_firebarswing4`
- `elight::game_firebarswingdash`
- `elight::game_lipstickswing1`
- `elight::game_lipstickswing3`
- `elight::game_lipstickswing4`
- `elight::game_lipstickswingdash`
- `elight::game_starrodswing1`
- `elight::game_starrodswing3`
- `elight::game_starrodswing4`
- `elight::game_starrodswingdash`
- `elight::game_swordswing1`
- `elight::game_swordswing3`
- `elight::game_swordswing4`
- `elight::game_swordswingdash`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-043: Shooting Items & Fire Flower (Ray Gun, Super Scope, Drill, Steel Diver)
<a id="scen-043"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items: Ray Gun, Super Scope, Drill, Steel Diver, Fire Flower

**Inputs:**
1. Pick up Ray Gun; fire on ground and in air, empty and loaded (`lgunshoot*`).
2. Pick up Super Scope; test ground single shot, rapid fire, full charge, and aerial variants empty and loaded (`scope*`).
3. Pick up Fire Flower; hold Attack on ground and in air (`fflowershoot*`).
4. Pick up Drill; shoot on ground and in air (`drillshoot*`).
5. Pick up Steel Diver; shoot on ground and in air (`steeldivershoot*`).

**Expected Visible Outcome:**
- All shooting items fire appropriate bullets, lasers, and flames, animating correctly in standing and mid-air postures.

**Expected Trace Markers / Covers:**
- `eflame::game_drillshoot`
- `eflame::game_drillshootair`
- `eflame::game_fflowershoot`
- `eflame::game_fflowershootaerial`
- `eflame::game_fflowershootair`
- `eflame::game_fflowershootfly1`
- `eflame::game_fflowershootfly2`
- `eflame::game_fflowershootfly3`
- `eflame::game_fflowershootfly4`
- `eflame::game_fflowershootfly5`
- `eflame::game_lgunshoot`
- `eflame::game_lgunshootair`
- `eflame::game_lgunshootairempty`
- `eflame::game_lgunshootempty`
- `eflame::game_scopeairfire`
- `eflame::game_scopeairfireaerial`
- `eflame::game_scopeairfireempty`
- `eflame::game_scopeairfireemptyaerial`
- `eflame::game_scopeairfireemptyfly1`
- `eflame::game_scopeairfireemptyfly2`
- `eflame::game_scopeairfireemptyfly3`
- `eflame::game_scopeairfireemptyfly4`
- `eflame::game_scopeairfireemptyfly5`
- `eflame::game_scopeairfirefly1`
- `eflame::game_scopeairfirefly2`
- `eflame::game_scopeairfirefly3`
- `eflame::game_scopeairfirefly4`
- `eflame::game_scopeairfirefly5`
- `eflame::game_scopeairrapid`
- `eflame::game_scopeairrapidaerial`
- `eflame::game_scopeairrapidempty`
- `eflame::game_scopeairrapidemptyaerial`
- `eflame::game_scopeairrapidemptyfly1`
- `eflame::game_scopeairrapidemptyfly2`
- `eflame::game_scopeairrapidemptyfly3`
- `eflame::game_scopeairrapidemptyfly4`
- `eflame::game_scopeairrapidemptyfly5`
- `eflame::game_scopeairrapidfly1`
- `eflame::game_scopeairrapidfly2`
- `eflame::game_scopeairrapidfly3`
- `eflame::game_scopeairrapidfly4`
- `eflame::game_scopeairrapidfly5`
- `eflame::game_scopefire`
- `eflame::game_scopefireempty`
- `eflame::game_scoperapid`
- `eflame::game_scoperapidempty`
- `eflame::game_steeldivershoot`
- `eflame::game_steeldivershootair`
- `elight::game_drillshoot`
- `elight::game_drillshootair`
- `elight::game_fflowershoot`
- `elight::game_fflowershootaerial`
- `elight::game_fflowershootair`
- `elight::game_fflowershootfly1`
- `elight::game_fflowershootfly2`
- `elight::game_fflowershootfly3`
- `elight::game_fflowershootfly4`
- `elight::game_fflowershootfly5`
- `elight::game_lgunshoot`
- `elight::game_lgunshootair`
- `elight::game_lgunshootairempty`
- `elight::game_lgunshootempty`
- `elight::game_scopeairfire`
- `elight::game_scopeairfireaerial`
- `elight::game_scopeairfireempty`
- `elight::game_scopeairfireemptyaerial`
- `elight::game_scopeairfireemptyfly1`
- `elight::game_scopeairfireemptyfly2`
- `elight::game_scopeairfireemptyfly3`
- `elight::game_scopeairfireemptyfly4`
- `elight::game_scopeairfireemptyfly5`
- `elight::game_scopeairfirefly1`
- `elight::game_scopeairfirefly2`
- `elight::game_scopeairfirefly3`
- `elight::game_scopeairfirefly4`
- `elight::game_scopeairfirefly5`
- `elight::game_scopeairrapid`
- `elight::game_scopeairrapidaerial`
- `elight::game_scopeairrapidempty`
- `elight::game_scopeairrapidemptyaerial`
- `elight::game_scopeairrapidemptyfly1`
- `elight::game_scopeairrapidemptyfly2`
- `elight::game_scopeairrapidemptyfly3`
- `elight::game_scopeairrapidemptyfly4`
- `elight::game_scopeairrapidemptyfly5`
- `elight::game_scopeairrapidfly1`
- `elight::game_scopeairrapidfly2`
- `elight::game_scopeairrapidfly3`
- `elight::game_scopeairrapidfly4`
- `elight::game_scopeairrapidfly5`
- `elight::game_scopefire`
- `elight::game_scopefireempty`
- `elight::game_scoperapid`
- `elight::game_scoperapidempty`
- `elight::game_steeldivershoot`
- `elight::game_steeldivershootair`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-044: Special Items (Hammer, Screw Attack, Daybreak, Special Flag, Grass)
<a id="scen-044"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items: Hammer, Screw Attack, Daybreak, Special Flag, Grass

**Inputs:**
1. Pick up Hammer; test ground run, wait, and jumping (`hammer*`).
2. Pick up Screw Attack badge; jump in mid-air (`screw*`).
3. Assemble Daybreak; fire on ground and in air (`genesisfire`, `genesisairfire`).
4. Pick up Special Flag; hold and hoist flag (`itemspecialflaghoist`).
5. Pull buried grass item (`itemgrasspull`).

**Expected Visible Outcome:**
- Hammer swings rapidly with music override, Screw Attack creates multi-hit somersault, Daybreak fires mega beam, and Special Flag hoists cleanly.

**Expected Trace Markers / Covers:**
- `eflame::game_genesisairfire`
- `eflame::game_genesisfire`
- `eflame::game_itemgrasspull`
- `eflame::game_itemspecialflaghoist`
- `eflame::game_screw`
- `eflame::game_screwair`
- `elight::game_genesisairfire`
- `elight::game_genesisfire`
- `elight::game_itemgrasspull`
- `elight::game_itemspecialflaghoist`
- `elight::game_screw`
- `elight::game_screwair`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-045: Taunts, Match Entry, and Victory Sequences
<a id="scen-045"></a>

**Setup:**
- Fighter: Pyra & Mythra | Opponent: Mario | Stage: Battlefield | Rules: 1 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. At match start, observe spawn entrance animation facing Right and Left (`entryr`, `entryl`).
2. Execute Up Taunt (`appealhi`), Side Taunt (`appeals`), and Down Taunt (`appeallw`), testing both right-facing and left-facing variants.
3. Win match to view victory screens 1, 2, 3, 4 (`win1`-`win4`, including `windummy` Rex assist), and lose match to view clapping animation (`lose`).
4. Repeat for both Pyra and Mythra.

**Expected Visible Outcome:**
- All taunts, entry poses, victory podium animations with Rex assist (`windummy`), and clapping defeat poses execute with full audio and visual effects.

**Expected Trace Markers / Covers:**
- `eflame::game_appealhil`
- `eflame::game_appealhir`
- `eflame::game_entryl`
- `eflame::game_entryr`
- `eflame::game_lose`
- `eflame::game_win1`
- `eflame::game_win1wait`
- `eflame::game_win2`
- `eflame::game_win2wait`
- `eflame::game_win3`
- `eflame::game_win3wait`
- `eflame_windummy::game_win3`
- `elight::game_appealhil`
- `elight::game_appealhir`
- `elight::game_entryl`
- `elight::game_entryr`
- `elight::game_lose`
- `elight::game_win1`
- `elight::game_win1wait`
- `elight::game_win2`
- `elight::game_win2wait`
- `elight::game_win3`
- `elight::game_win3wait`
- `elight_windummy::game_win3`

**Verification:**
- [ ] Pass
- [ ] Fail

---

### SCEN-046: Kirby Copy Ability (Kirby Flame Nova & Kirby Lightning Buster)
<a id="scen-046"></a>

**Setup:**
- Fighter: Kirby | Opponent: Pyra / Mythra | Stage: Battlefield | Rules: 3 Stock, 8:00 Time, Items Off, Damage Ratio 1.0x

**Inputs:**
1. As Kirby, inhale Pyra to acquire Pyra's copy hat (Flame Nova).
2. Tap and hold Neutral-B as Kirby to execute Pyra's Flame Nova.
3. Discard hat (Taunt). Have opponent swap to Mythra.
4. As Kirby, inhale Mythra to acquire Mythra's copy hat (Lightning Buster).
5. Charge Neutral-B as Kirby to execute Mythra's Lightning Buster.

**Expected Visible Outcome:**
- Kirby correctly obtains Pyra and Mythra copy hats, charging and discharging Flame Nova and Lightning Buster with identical timing and particle effects.

**Expected Trace Markers / Covers:**
- *(Behavioral state check; covers shared game mechanics)*

**Verification:**
- [ ] Pass
- [ ] Fail

---
