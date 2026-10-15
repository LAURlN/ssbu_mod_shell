pub const AGENT_MAP: &[(&str, &str)] = &[
    ("eflame", "cflame"),
    ("eflame_blazepillar", "cflame_blazepillar"),
    ("eflame_esword", "cflame_esword"),
    ("eflame_firepillar", "cflame_firepillar"),
    ("eflame_windummy", "cflame_windummy"),
    ("elight", "clight"),
    ("elight_beam", "clight_beam"),
    ("elight_bunshin", "clight_bunshin"),
    ("elight_exprosiveshot", "clight_exprosiveshot"),
    ("elight_meteor", "clight_meteor"),
    ("elight_spreadbullet", "clight_spreadbullet"),
    ("elight_windummy", "clight_windummy"),
    ("element_diver", "clement_diver"),
];

pub fn get_clone_name(vanilla_name: &str) -> Option<&'static str> {
    AGENT_MAP.iter().find(|(v, _)| *v == vanilla_name).map(|(_, c)| *c)
}
