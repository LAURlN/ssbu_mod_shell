# User hardware verdict and next development batch — 2026-10-03

Provenance: user message in this chat: "okay, the latest version of the mod works great."
Scope clarification: "i mean the modded character over pyra mythra c06 and c07 for all of these".

Tier A / verified by user report: overall latest mod is satisfactory on console. No boot log, new hash check, individual move checklist, or crash report was supplied in this turn. Latest recorded card package is `builds/pgwr/dk_cargo-0.1.1-test`, containing prior Incineroar and Snake/Lucas/Ness changes; association with that exact package is inferred from CURRENT_INSTALL.md, not independently hardware-hash verified here. Do not convert the broad verdict into individual control-test passes.

User-reported remaining issues: level-2 Hero side-B visually points somewhat too high (about 5%, explicitly a rough estimate); mana bar is not visibly available on either body; Chrom jab sword is not visible on G&W; dash grabbing an opponent slides G&W; opponents still fall out of Mythra up-B too often; selected G&W starting form is not visible as intended on battle loading screen. These observations are user reports, not isolated causes.

Requested six parallel manual handoffs: Opus effects customization (Lucas down smash and Ness back throw; c07 light, c06 scarlet/dark matching existing themes); Opus Zapple angle plus real shared mana HUD; Freebuff jab sword visibility; Freebuff dash-grab slide; Freebuff further up-B gravity reduction; Freebuff battle-loading-screen G&W appearance. Workers should decide implementation details autonomously, ask no intermediate questions, preserve current installed functionality, and prepare checked mergeable deltas without installation. Unresolvable technical blockers must be reported honestly at completion rather than guessed around.

The mana HUD request authorizes implementing the necessary project-owned, 13.0.4-signature-checked HUD integration. It does not request recovery-on-hit or changes to framework plugins. Installation waits until the user reports completion of the workers.
