# Plan: Chrom's jab on the G&W costume (eflame c06/c07)

Status: **implemented, built and installed as 0.16.0 - and never run.** The user
authorized the build the same session, so this is no longer a plan: see
`builds/pgwr/0.16.0/MANIFEST.json` and `evidence/install-record-2026-09-30_0218.json`
for what shipped, and `projects/pgwr/STATUS.md` for the current card state. What is
below is kept as the reasoning, including the parts that turned out differently -
the retarget filter decision, the donor-directory-vs-article-name trap, and the
afterimage that is still pending.

All numbers are measured offline (tier B): from `dumps/`, or from the live read-only
extraction recorded in `refs/chrom_jab/` (`extraction.json`, per-file sha256) via the
new `tools/fetch_arc_files.py`. The console was up and answering on port 43022, so the
whole donor set was fetched rather than requested.

Goal: the neutral attack (jab) on the G&W-skinned Pyra becomes **Chrom's jab**.
Today it is G&W's own jab.

## What the jab is today (measured)

| Layer | Today | Source |
| --- | --- | --- |
| Script | G&W's `Attack11` ported by `gen_acmd.py` (`generated/ground.rs`) | dump |
| Prop | G&W's `normal_weapon` article, `KIND_SPRAY` — his bug-spray poke | `ground.rs` |
| Hitbox | 1 hitbox at frame 4, 3.0%, 361°, angle 22 BKB / 25 KBG, `ATTACK_REGION_OBJECT` | `ground.rs` |
| Clip | G&W's `c00attack11.nuanmb` = **1 frame**, 41 nodes | dump |
| Motion entry | G&W's `attack_11`: cancel **16**, flags `0x80` | G&W list |
| Chain | G&W's script sets `ENABLE_100` (frame 6) and `ENABLE_COMBO` (frame 8), so Pyra's status runs jab 1-2-3 with `attack_12`/`attack_13` standing in on G&W's clip, then the rapid | `ground.rs` + `FALLBACKS` |

So the jab the user sees now is essentially a **static one-frame pose** repeated up
to three times. Replacing it with Chrom's 42-frame slash fixes that on its own,
independent of the sword question.

## The donor: Chrom, and what he actually has

* Script: `dumps/scripts/.../lua2cpp_chrom/chrom/Attack11.txt`.
  Frames 5-8. Three hitboxes: **one on `top`** (radius 3.7, at `(0, 10, 7)`) and
  **two on `sword1`** (radius 3.8 at `(0, 0, 1.7)`; radius 3.5 at `(0, 0, 8.4)`).
  6.5%, angle 62, BKB 60, KBG 40, hitlag 1.4, `collision_attr_cutup`,
  `COLLISION_SOUND_ATTR_CHROM_HIT`, `ATTACK_REGION_SWORD`,
  `set_attack_reference_joint_id("sword1")`, `enable_fix_jostle_area(5.0, 5.0)`.
  **The script never touches an article** — no `generate_article`, no motion part.
* Clip: `dumps/arc/fighter/chrom/motion/body/c00/c00attack11.nuanmb`, 42872 bytes,
  **96 transform nodes, 42 frames**.
* Asset: the Falchion **article is now in hand**. `dumps/decoded/arc_files.tsv` lists 17 files per costume for
  `fighter/chrom/{model,motion}/sword/c00..c07`; both directories were empty in `dumps/arc`, so all 136 were
  extracted live into `refs/chrom_jab/arc/` (139 including the donor skeleton and params, 0 failures). Measured:

  | Fact | Value |
  | --- | --- |
  | Article skeleton | **2 bones**: `HaveR` (root) → `Sword`; no translation on either |
  | Sword mesh | one object `fal_RShape`, 444 verts, skinned to `Sword` |
  | Blade axis and reach | along **+z**, tip at **z = 10.908** (hilt back to −1.827); Pyra's Aegis tip is 11.39 — same axis, within half a unit |
  | Materials | `model`/`dark_model`/`light_model`/`metamon_model.numatb` reference `met_chrom_001_{col,nor,prm}` — all shipped |
  | Clips | 2 entries only (`entry_l`, `entry_r`), 916 B and 404 B |
  | Per-costume variation | **none** — every one of the 20 distinct file names is byte-identical across all eight costumes (unlike G&W's `normal_weapon`/`breath`) |
* **Decisive detail**: Chrom's sword article has **no pose animation at all** — its motion list holds only `entry_l`
  and `entry_r`, and the extracted clips confirm it (one `Transform` group, two nodes). Its transform is therefore
  whatever the body bone it hangs off does. That is the exact opposite of the Aegis article, which owns its pose in
  its own clips (R-20/R-21) — and it is why a body clip can aim Chrom's sword but cannot re-aim the Aegis one.
* **The two skeletons already agree.** Chrom's body skeleton (123 bones, now extracted) carries
  `Sword1 <- HaveR <- HandR <- ArmR <- ShoulderR <- ClavicleR <- ClavicleC <- Bust <- Waist <- Hip <- Rot <- Trans`,
  and the built recipient c06 carries the *same chain with the same names*, because Pyra's graft supplied it. So
  Chrom's jab hitboxes on `sword1` land on a bone that exists in the same place, and no bone work is needed.
* **`top` is engine-side, not a bone.** It is absent from Chrom's skeleton *and* from the recipient's, yet both use
  `Hash40::new("top")` in `ATTACK` calls and it works on hardware. That retires the fair's second open ship-blocker
  (`top` anchor resolution) rather than leaving it a standing assumption.
* Trail: already available. `dumps/arc/effect/fighter/chrom/` holds `ef_chrom.eff` and
  `trail/tex_chrom_sword1.nutexb` + `trail/tex_chrom_sword2.nutexb`, the exact pair his afterimage names.
* Motion list (`dumps/arc/fighter/chrom/motion/body/c00/motion_list.bin`, 753 entries):
  `attack_11` cancel **23**, flags `0x84`. **`attack_12`, `attack_13`, `attack_100`
  and `attack_100_start` are all absent.**

### Consequence: Chrom's jab is a single hit with no rapid

That is the whole shape of the port. It also means the follow-up statuses Pyra's
status machine can reach (`attack_12`, `attack_13`, `attack_100`) have no donor.

Note: hash40 verification of the kind names is sound (`attack_11` and
`attack_air_f` both resolve), but Chrom's motion list has **no `attack_s3`** while
he does have an `AttackS3.txt` script — so his kind naming is not uniformly the
Pyra/G&W convention. Confirm any kind before trusting it, the jab's included
(it is confirmed here).

## Retarget: what actually resolves

Recipient skeleton = G&W's **45** bones + **120** grafted Pyra bones = **165**
(`builds/pgwr/pyra_gamewatch_reskin/.../fighter/eflame/model/body/c06/model.nusktb`).

| Filter | Chrom's clip nodes kept |
| --- | --- |
| G&W's skeleton only (what `build_cloud_fair.py` does) | **36** |
| The built/grafted skeleton | **80** |

The 44 lost under the current filter are Chrom-only props (`Hilt`, `Scabbard`,
`S_MantleL/R/C1-4`, `S_FootL1/R1`) plus Pyra-grafted face/finger/sword bones
(`Sword1`, `Sword2`, `Face`, `Jaw`, `Tongue`, `*lip*`, `Finger*`).

**Only G&W's meshes are drawn**, so the grafted bones are invisible *except*
`Sword1`/`Sword2`, which are the sword's attach chain — and whether a body clip can
move the blade is exactly the question `handbook/graveyard.md` R-20/R-21 answered
*no* for the Aegis article. So the two filters should look identical on screen; the
wider one is a cheap experiment, not a requirement.

Chrom's clip also carries a **Visibility** group of 35 entries (his face/mouth/eye
mesh names, `SayaM`, `fal_L/R/e`) and **2 Material** groups. None of those names
exist in the recipient. The Cloud fair recipe — drop the donor's non-Transform
groups and replicate G&W's idle visibility — applies unchanged.

## Sword: measured reach, and the trap

| | Value |
| --- | --- |
| Chrom's jab reach along `sword1` | hitbox at z = 8.4, radius 3.5 → ~**11.9** |
| Pyra's Aegis blade tip, vanilla | z ≈ **11.39** |
| Pyra's blade as shipped in 0.15.2 | 1.4× → ~**15.9** |

Vanilla-scale Aegis and Chrom's jab happen to agree within a unit. But the 0.15.2
taste value (1.4×, chosen for the fair) is applied in the **article's own clips**,
so it applies to every drawn state including the jab. If the Aegis is reused for
the jab, the blade would overhang Chrom's hitboxes by ~4 units unless that factor is
revisited — that is the one place where the jab work collides with the fair work.
Chrom's own Falchion carries its own size and does not inherit the problem.

## Plan (when the tree is quiet and the card is back)

1. `src/pgwr/tools/build_chrom_jab.py`, sibling of `build_cloud_fair.py`:
   donor clip sha/bytes pinned, `get_chrom_motion_entry(hash40('attack_11'))`,
   retarget + `deploy_for_slot(slot, out, gw_slot)`. No sword track (R-21).
2. `build.py`: use Chrom's entry for `attack_11` (cancel 23) instead of G&W's, and
   deploy the clip over eflame's own `c00attack11.nuanmb` (name hash already
   matches, exactly as `c05attackairf.nuanmb` did — no alias needed).
3. `plugin/src/acmd/chrom_jab.rs` (High priority, same gated agent as
   `attack_air_f.rs`): Chrom's three hitboxes at frames 5-8 verbatim, `sword1`
   reference joint, sound/effect substitutions, and — if the sword ships — the
   `to_open` at the swing + `to_close`/hide after, copied from `attack_air_f.rs`.
4. Register in `acmd/mod.rs`; extend the `table` rows for ATTACK11/12/13.
5. Substitutions following the existing R2 convention: `se_chrom_swing_s` →
   `se_eflame_swing_s01`; verify `COLLISION_SOUND_ATTR_CHROM_HIT` compiles (the
   CLOUD equivalent does), else `CUTUP`. Chrom's afterimage uses
   `tex_chrom_sword1/2` + `EFFECT_OFF_KIND("chrom_sword")`, neither of which the
   mod ships.
6. Version bump, full build, dry run, install, verify hashes, records.

## Risks, ranked

1. **Chain flags.** Chrom's script sets no `ENABLE_COMBO`/`ENABLE_100`, and G&W's
   sets both explicitly, which suggests the script owns them and a verbatim port
   simply ends the jab. If Pyra's status self-chains, jab2/3 stay on G&W's 1-frame
   clip. Mitigation: give `attack_12`/`attack_13` Chrom's clip and entry too, so a
   surviving chain is still Chrom's jab rather than a spray poke.
2. **Sword visibility on a script that never mentions the article.** The jab must
   generate/open it itself, and must close and hide it again — the 0.15.1 finding
   is that a live article stays drawn for the rest of the match.
3. **Sounds.** `fighter/se_chrom` is in `sound-inventory.json`, but whether that
   bank is loaded in an eflame match is unverified. R2 substitution avoids the
   question.
4. **`Sword1` movement.** R-20/R-21 stay refuted and are not being re-litigated: they
   were about the *Aegis* article, which owns its pose. Chrom's sword is a different
   class of article (no pose clips), so a body-clip `Sword1` track is expected to
   move *it*. That expectation is untested and is the one claim here a build cannot
   confirm.
5. Single variable per hardware test (AGENTS 11): if the sword ships, the jab is
   *two* changes — motion+hitbox and sword. Consider shipping the motion first.

## Open decision

Whether the jab shows a sword, and which one. The evidence now favours (b):

* **(a) Reuse the Aegis esword.** Cheapest, reuses machinery already on the card. But
  the Aegis **owns its pose in its own clips**, so during a jab the blade would sit
  at whatever angle its `open` clip holds relative to the hand — the fair's angle,
  not a jab's horizontal arc. That is the mechanism behind the original "sword at the
  wrong angle" report, and no body animation can correct it.
* **(b) Ship Chrom's Falchion as a third cloned weapon.** Every blocking fact is now
  settled: the files are extracted; the constant exists (`WEAPON_KIND_CHROM_SWORD` =
  `0x1B6` in the locked `lua_const`, rev 315e4e8); the clone is one more
  `clone_weapon("chrom", *WEAPON_KIND_CHROM_SWORD, "eflame", "chrom_sword", false)`
  beside the other two, making it clone index **2** and local article id
  `ARTICLE_TERM(5) + 2 = 7`; and `dumps/scripts/.../lua2cpp_chrom/` has **no
  `chrom_sword` folder** (only `chrom`), so `use_original_code = false` for the same
  measured reason `normal_weapon` uses it. In exchange the blade is driven by the
  body bone, so the retargeted jab aims it for free and there is no article pose to
  fight — and its reach (10.91) is within half a unit of the Aegis blade's, so the
  move reads the same distance either way.
* **(c) No sword; G&W jabs bare.**

(b) also changes the retarget recommendation: keeping `Sword1`/`Sword2` — the 80-node,
built-skeleton filter instead of the 36-node G&W-only one — is precisely what drives a
body-owned article, so the filter choice belongs to this decision rather than being a
footnote.
