# ACMD Port Compile Fixes

This report records all syntactic and import-related compile fixes applied when porting dumped Smashline ACMD scripts to `pyra_mythra_clone/moveset`.
In accordance with `HANDOFF_WEAK_MODEL.md`, no numbers, frames, conditions, or call orders were changed. All fixes are purely syntactic, type annotation, float literal, or cast adjustments required by the Rust compiler and Skyline APIs.

| Agent | Function | Before | After | Reason |
|---|---|---|---|---|
| cflame | game_attackhi4 | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_attacklw4 | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_attacks4 | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialairhifall | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialairhijump | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialairhistart | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialairnhold | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialairnstart | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialairs | `ArticleModule::shoot(..., *ARTICLE_OPE_TARGET_ALL, false);` | `ArticleModule::shoot(..., smash::app::ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL), false);` | Wrap in ArticleOperationTarget newtype |
| cflame | game_specialairs | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialairsflick | `ArticleModule::shoot(..., *ARTICLE_OPE_TARGET_ALL, false);` | `ArticleModule::shoot(..., smash::app::ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL), false);` | Wrap in ArticleOperationTarget newtype |
| cflame | game_specialairsflick | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialhi | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialhistart | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialn1 | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialnhold | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialnstart | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specials | `ArticleModule::shoot(..., *ARTICLE_OPE_TARGET_ALL, false);` | `ArticleModule::shoot(..., smash::app::ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL), false);` | Wrap in ArticleOperationTarget newtype |
| cflame | game_specials | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame | game_specialsflick | `ArticleModule::shoot(..., *ARTICLE_OPE_TARGET_ALL, false);` | `ArticleModule::shoot(..., smash::app::ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL), false);` | Wrap in ArticleOperationTarget newtype |
| cflame | game_specialsflick | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| cflame_blazepillar | game_finalattack | `AttackModule::set_final_finish_cut_in(..., -1, ...)` | `AttackModule::set_final_finish_cut_in(..., -1.0, ...)` | Float literal required by type signature |
| cflame_esword | game_flyflickl | `MotionModule::set_rate(agent.module_accessor, 1);` | `MotionModule::set_rate(agent.module_accessor, 1.0);` | Float literal required by type signature |
| cflame_esword | game_flyflickr | `MotionModule::set_rate(agent.module_accessor, 1);` | `MotionModule::set_rate(agent.module_accessor, 1.0);` | Float literal required by type signature |
| cflame_esword | game_flyl | `MotionModule::set_rate(agent.module_accessor, 1);` | `MotionModule::set_rate(agent.module_accessor, 1.0);` | Float literal required by type signature |
| cflame_esword | game_flyr | `MotionModule::set_rate(agent.module_accessor, 1);` | `MotionModule::set_rate(agent.module_accessor, 1.0);` | Float literal required by type signature |
| cflame_esword | game_reflectedl | `MotionModule::set_rate(agent.module_accessor, 1);` | `MotionModule::set_rate(agent.module_accessor, 1.0);` | Float literal required by type signature |
| cflame_esword | game_reflectedr | `MotionModule::set_rate(agent.module_accessor, 1);` | `MotionModule::set_rate(agent.module_accessor, 1.0);` | Float literal required by type signature |
| cflame_esword | game_rotate | `MotionModule::set_rate(agent.module_accessor, 1);` | `MotionModule::set_rate(agent.module_accessor, 1.0);` | Float literal required by type signature |
| clight | game_attackhi4 | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| clight | game_attacklw4 | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| clight | game_attacks4 | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| clight | game_specialairhistart | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| clight | game_specialhistart | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| clight | game_specialnstart | `WorkModule::set_int64(agent.module_accessor, hash40(...) as i64, ...)` | `WorkModule::set_int64(agent.module_accessor, hash40(...) as u64, ...)` | WorkModule::set_int64 expects u64 in skyline-smash |
| clight_beam | game_finalattack | `AttackModule::set_final_finish_cut_in(..., -1, ...)` | `AttackModule::set_final_finish_cut_in(..., -1.0, ...)` | Float literal required by type signature |
