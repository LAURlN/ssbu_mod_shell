//! Recording/playback session state, file formats and the D-pad commands.
//!
//! Commands (Training mode only; taunts are disabled while this plugin is loaded):
//!   D-pad up          start a recording (inputs + trace)
//!   D-pad left        play back the selected recording exactly
//!   D-pad right       play it back with one neutral input at frame 60 (self-test)
//!   D-pad down        stop
//!
//! Both start the same way: ARM_FRAMES frames in which every *active* fighter is
//! held at its start position with speed cleared and sent to WAIT, then forced
//! into WAIT once more so the idle animation starts at frame 0. Recording
//! captures the start positions/percent; playback restores them from the file.
//! This restores a small subset of start state, not RNG or a full save state.
//! Equal replay traces remain a hardware acceptance gate.
//!
//! Lock discipline (learned the hard way on 2026-09-28): SESSION is a
//! non-reentrant Mutex, and the game calls used to arm a fighter (heal, speed
//! reset, status change) re-enter the Smashline Main lines this plugin hooks, on
//! the same thread. Calling them with SESSION held self-deadlocks the game and
//! freezes it on D-pad up, with no crash report. So the arm path is split:
//! `plan_arm` runs with SESSION held and may only *read*, and every write
//! happens in `apply_arm` with SESSION released. `enter` additionally drops
//! any re-entrant callback instead of risking the same hang.
//!
//! Files (all under sd:/ultimate/pmclone_trace/):
//!   pmclone_trace.log          boot + session log, appended
//!   counter.txt                next session number
//!   traces/NNNN_rec.trace.csv  trace of a recording
//!   traces/NNNN_play_<src>.trace.csv  trace of a playback
//!   inputs/NNNN.inputs         a recording's inputs; also copied to last.inputs
//!   play.txt                   optional: name of the inputs file to play (default last.inputs)
//!   perturb.txt                optional: "frame N" changes the frame D-pad right
//!                              replaces with a neutral input (default 60)
use core::cell::Cell;

use std::fs::{self, File, OpenOptions};
use std::io::{BufWriter, Write};
use std::sync::Mutex;

use smash::app::{lua_bind::*, BattleObjectModuleAccessor};
use smash::lib::lua_const::*;
use smash::phx::Vector3f;

use crate::input::MappedInputs;
use crate::sample;

pub const DIR: &str = "sd:/ultimate/pmclone_trace";
const ARM_FRAMES: u32 = 30;
const MAX_FRAMES: usize = 3600;
/// Frame whose input D-pad-right playback replaces with neutral (perturb.txt overrides).
const DEFAULT_PERTURB_FRAME: i64 = 60;

const APPEAL_HI: u32 = 0x400;
const APPEAL_LW: u32 = 0x1000;
const APPEAL_SL: u32 = 0x2000;
const APPEAL_SR: u32 = 0x4000;
const APPEAL_ALL: u32 = APPEAL_HI | APPEAL_LW | APPEAL_SL | APPEAL_SR;

pub const HEADER: &str = "frame,slot,object,kind,status,situation,motion,motion_frame,motion_rate,pos_x,pos_y,lr,speed,damage,hitstop,hitboxes,work";

#[derive(Clone, Copy, PartialEq, Debug)]
enum Goal {
    Record,
    Play,
}

#[derive(Clone, Copy, PartialEq, Debug)]
enum Mode {
    Idle,
    Arming { goal: Goal, left: u32 },
    Running { goal: Goal },
}

thread_local! {
    /// True while this thread is inside a session callback. Any re-entry
    /// returns immediately rather than re-entering SESSION or recursing.
    static IN_HOOK: Cell<bool> = const { Cell::new(false) };
}

/// Held for the length of a callback; clears `IN_HOOK` on drop.
struct HookGuard;

impl Drop for HookGuard {
    fn drop(&mut self) {
        IN_HOOK.with(|f| f.set(false));
    }
}

/// Returns a guard, or None if this thread is already inside a session callback.
fn enter() -> Option<HookGuard> {
    IN_HOOK.with(|f| {
        if f.get() {
            None
        } else {
            f.set(true);
            Some(HookGuard)
        }
    })
}

#[derive(Clone, Copy, Default)]
struct Start {
    present: bool,
    applied_damage: bool,
    x: f32,
    y: f32,
    lr: f32,
    damage: f32,
    /// Base fighter kind active in this slot at the start. Pyra/Mythra must start
    /// a playback in the same form as the recording.
    kind: i32,
}

/// One trace row before the per-frame sort. `object` has no instance suffix yet.
pub struct Row {
    pub slot: i32,
    pub object: String,
    pub order: u32,
    pub article: bool,
    pub fields: String,
}

struct Session {
    mode: Mode,
    owner: i32,
    prev_buttons: [u32; 16],
    number: u32,
    frame: i64,
    inputs: Vec<MappedInputs>,
    source: String,
    perturb_frame: Option<i64>,
    starts: [Start; 8],
    seen_starts: [bool; 8],
    abort: Option<String>,
    error: Option<String>,
    writer: Option<BufWriter<File>>,
    trace_path: String,
    rows: Vec<Row>,
    rows_written: u64,
    extra_callbacks: u64,
}

static SESSION: Mutex<Session> = Mutex::new(Session {
    mode: Mode::Idle,
    owner: -1,
    prev_buttons: [0; 16],
    number: 0,
    frame: -1,
    inputs: Vec::new(),
    source: String::new(),
    perturb_frame: None,
    starts: [Start { present: false, applied_damage: false, x: 0.0, y: 0.0, lr: 0.0, damage: 0.0, kind: -1 }; 8],
    seen_starts: [false; 8],
    abort: None,
    error: None,
    writer: None,
    trace_path: String::new(),
    rows: Vec::new(),
    rows_written: 0,
    extra_callbacks: 0,
});

/// Creates the output directories as early as possible and reports each result.
///
/// A directory created *after* the SD mount is opened can appear on the card
/// while still being unresolvable through FSS, so a file created inside it
/// fails with "Result code: 514" (PathNotFound) even though the folder is
/// there. Files written straight into DIR always resolve. Creating the tree at
/// init, and never discarding the result, is what makes this diagnosable
/// instead of a silent failure on the first session.
pub fn prepare_dirs() {
    for sub in ["", "/traces", "/inputs"] {
        let path = format!("{}{}", DIR, sub);
        match fs::create_dir_all(&path) {
            Ok(()) => boot_log(&format!("dir ready: {}", path)),
            Err(e) => boot_log(&format!("dir FAILED: {}: {}", path, e)),
        }
    }
}

/// Re-checks a session directory and logs the real error, which used to be
/// discarded and cost us the only clue about the 514.
fn ensure_dir(path: &str, number: u32) {
    if let Err(e) = fs::create_dir_all(path) {
        boot_log(&format!("session {}: create_dir_all({}) failed: {}", number, path, e));
    }
}

pub fn boot_log(text: &str) {
    let _ = fs::create_dir_all(DIR);
    if let Ok(mut file) = OpenOptions::new()
        .append(true)
        .create(true)
        .open(format!("{}/pmclone_trace.log", DIR))
    {
        let _ = writeln!(file, "{}", text);
    }
    println!("[pmclone_trace] {}", text);
}

fn next_number() -> Result<u32, String> {
    let path = format!("{}/counter.txt", DIR);
    let n = fs::read_to_string(&path)
        .ok()
        .and_then(|s| s.trim().parse::<u32>().ok())
        .unwrap_or(1);
    fs::write(&path, format!("{}\n", n.checked_add(1).ok_or("counter overflow")?))
        .map_err(|e| format!("cannot save counter: {}", e))?;
    Ok(n)
}

fn load_inputs(s: &mut Session, perturbed: bool) -> Result<(), String> {
    let name = fs::read_to_string(format!("{}/play.txt", DIR))
        .ok()
        .and_then(|t| t.lines().next().map(|l| l.trim().to_string()))
        .filter(|l| !l.is_empty())
        .unwrap_or_else(|| "last.inputs".to_string());
    if !name.ends_with(".inputs") || name.contains("..")
        || name.chars().any(|c| !(c.is_ascii_alphanumeric() || c == '_' || c == '-' || c == '.')) {
        return Err("play.txt must contain a plain .inputs filename".into());
    }
    let text = fs::read_to_string(format!("{}/inputs/{}", DIR, name))
        .map_err(|e| format!("cannot read inputs/{}: {}", name, e))?;
    s.inputs.clear();
    s.starts = [Start::default(); 8];
    for (n, line) in text.lines().enumerate() {
        let p: Vec<&str> = line.split_whitespace().collect();
        let bad = || format!("inputs/{} line {}: malformed", name, n + 1);
        match p.first() {
            Some(&"start") if p.len() == 7 => {
                let slot: usize = p[1].parse().map_err(|_| bad())?;
                if slot >= 8 || s.starts[slot].present {
                    return Err(bad());
                }
                s.starts[slot] = Start {
                    present: true,
                    applied_damage: false,
                    x: p[2].parse().map_err(|_| bad())?,
                    y: p[3].parse().map_err(|_| bad())?,
                    lr: p[4].parse().map_err(|_| bad())?,
                    damage: p[5].parse().map_err(|_| bad())?,
                    kind: p[6].parse().map_err(|_| bad())?,
                };
                let st = s.starts[slot];
                if !st.x.is_finite() || !st.y.is_finite() || !st.damage.is_finite()
                    || st.damage < 0.0 || (st.lr != 1.0 && st.lr != -1.0) {
                    return Err(bad());
                }
            }
            Some(&"i") if p.len() == 6 => s.inputs.push(MappedInputs {
                buttons: u32::from_str_radix(p[1], 16).map_err(|_| bad())?,
                lstick_x: p[2].parse().map_err(|_| bad())?,
                lstick_y: p[3].parse().map_err(|_| bad())?,
                rstick_x: p[4].parse().map_err(|_| bad())?,
                rstick_y: p[5].parse().map_err(|_| bad())?,
            }),
            Some(t) if t.starts_with('#') => {}
            None => {}
            _ => return Err(bad()),
        }
    }
    if s.inputs.is_empty() || s.inputs.len() > MAX_FRAMES
        || !s.starts.iter().any(|st| st.present) {
        return Err(format!("inputs/{} needs starts and 1..={} input lines", name, MAX_FRAMES));
    }
    s.source = name;
    s.perturb_frame = if perturbed {
        Some(
            fs::read_to_string(format!("{}/perturb.txt", DIR))
                .ok()
                .and_then(|t| t.split_whitespace().nth(1).and_then(|n| n.parse().ok()))
                .unwrap_or(DEFAULT_PERTURB_FRAME),
        )
    } else {
        None
    };
    if let Some(frame) = s.perturb_frame {
        if frame < 0 || frame as usize >= s.inputs.len()
            || s.inputs[frame as usize] == MappedInputs::default() {
            return Err("perturb frame must be in range and contain non-neutral input".into());
        }
    }
    Ok(())
}

fn save_inputs(s: &Session) -> std::io::Result<()> {
    let mut text = String::from("# pmclone_trace inputs v1\n");
    for (slot, st) in s.starts.iter().enumerate() {
        if st.present {
            text.push_str(&format!(
                "start {} {} {} {} {} {}\n",
                slot, st.x, st.y, st.lr, st.damage, st.kind
            ));
        }
    }
    for i in &s.inputs {
        text.push_str(&format!(
            "i {:x} {} {} {} {}\n",
            i.buttons, i.lstick_x, i.lstick_y, i.rstick_x, i.rstick_y
        ));
    }
    fs::create_dir_all(format!("{}/inputs", DIR))?;
    fs::write(format!("{}/inputs/{:04}.inputs", DIR, s.number), &text)?;
    fs::write(format!("{}/inputs/last.inputs", DIR), &text)
}

fn begin(s: &mut Session, goal: Goal) {
    if !s.starts.iter().any(|st| st.present)
        || s.starts.iter().zip(s.seen_starts.iter()).any(|(st, seen)| st.present != *seen) {
        finish(s, "recording roster does not match active fighters observed while arming");
        return;
    }
    s.error = None;
    s.number = match next_number() {
        Ok(n) => n,
        Err(e) => { finish(s, &e); return; }
    };
    ensure_dir(&format!("{}/traces", DIR), s.number);
    s.trace_path = match goal {
        Goal::Record => format!("{}/traces/{:04}_rec.trace.csv", DIR, s.number),
        Goal::Play => format!(
            "{}/traces/{:04}_play_{}{}.trace.csv",
            DIR,
            s.number,
            s.source.trim_end_matches(".inputs"),
            if s.perturb_frame.is_some() { "_perturbed" } else { "" }
        ),
    };
    // Exclusive create (create_new) is the one open mode that fails on the
    // Horizon SD path: it returns "Result code: 514" (PathNotFound) for a file
    // whose parent directory resolves fine, while plain create/append/truncate
    // all work. So create without O_EXCL and keep the no-overwrite guarantee
    // by refusing a path that already holds data. That check is not atomic
    // against another writer, which is acceptable here: names are session
    // numbered and only one human controller can record at a time.
    let mut w = match OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(false)
        .open(&s.trace_path)
    {
        Ok(f) => {
            let occupied = f.metadata().map(|m| m.len() != 0).unwrap_or(false);
            if occupied {
                boot_log(&format!(
                    "session {}: refusing to overwrite existing {}",
                    s.number, s.trace_path
                ));
                s.mode = Mode::Idle;
                return;
            }
            BufWriter::with_capacity(1 << 16, f)
        }
        Err(e) => {
            boot_log(&format!("session {}: cannot create {}: {}", s.number, s.trace_path, e));
            s.mode = Mode::Idle;
            return;
        }
    };
    let _ = writeln!(w, "# pmclone_trace v{}", crate::VERSION);
    let _ = writeln!(w, "# session={} mode={:?} controller={}", s.number, goal, s.owner);
    if goal == Goal::Play {
        let _ = writeln!(w, "# inputs={} frames={} perturb={:?}", s.source, s.inputs.len(), s.perturb_frame);
    }
    for (slot, st) in s.starts.iter().enumerate() {
        if st.present {
            let _ = writeln!(
                w,
                "# start slot={} x={} y={} lr={} damage={} kind={}",
                slot, st.x, st.y, st.lr, st.damage, st.kind
            );
        }
    }
    if let Err(e) = writeln!(w, "{}", HEADER).and_then(|_| w.flush()) {
        finish(s, &format!("cannot write trace header: {}", e));
        return;
    }
    s.writer = Some(w);
    s.frame = -1;
    s.rows.clear();
    s.rows_written = 0;
    s.mode = Mode::Running { goal };
    boot_log(&format!("session {} started: {:?} -> {}", s.number, goal, s.trace_path));
}

/// Writes the rows collected for the frame that just ended, sorted so that the
/// file does not depend on callback order. Articles of the same name in the same
/// slot are numbered by creation order (battle object id).
fn flush_rows(s: &mut Session) {
    if s.rows.is_empty() {
        if s.frame >= 0 {
            s.error = Some(format!("frame {} has no callbacks; pause, missing Smashline, or timing mismatch", s.frame));
        }
        return;
    }
    let mut rows = core::mem::take(&mut s.rows);
    rows.sort_by(|a, b| (a.slot, &a.object, a.order).cmp(&(b.slot, &b.object, b.order)));
    // First-wins. The Main line can fire twice for one object in a single
    // frame: the regular per-frame update, then a mid-frame status transition
    // (seen on hardware: fighter:elight sampled at status 0 and again at
    // status 39 on frame 212 of session 4). The sort is stable, so the regular
    // sample is the one kept. Dropping the extra instead of invalidating the
    // capture matters because every recording with an attack in it trips this.
    // `order` is part of the key: several articles of one name legitimately
    // share a slot and object and are told apart by battle object id.
    let mut extra = 0u64;
    let mut w = 0usize;
    for i in 0..rows.len() {
        if w > 0
            && rows[w - 1].slot == rows[i].slot
            && rows[w - 1].object == rows[i].object
            && rows[w - 1].order == rows[i].order
        {
            extra += 1;
            continue;
        }
        rows.swap(w, i);
        w += 1;
    }
    rows.truncate(w);
    if extra > 0 {
        s.extra_callbacks += extra;
    }
    for (slot, st) in s.starts.iter().enumerate() {
        if st.present && !rows.iter().any(|r| !r.article && r.slot == slot as i32) {
            s.error = Some(format!("frame {} missing fighter slot {}", s.frame, slot));
        }
    }
    let frame = s.frame;
    if let Some(w) = s.writer.as_mut() {
        let mut instance = 0;
        for i in 0..rows.len() {
            let r = &rows[i];
            if i > 0 && rows[i - 1].slot == r.slot && rows[i - 1].object == r.object {
                instance += 1;
            } else {
                instance = 0;
            }
            let result = if r.article {
                writeln!(w, "{},{},{}#{},{}", frame, r.slot, r.object, instance, r.fields)
            } else {
                writeln!(w, "{},{},{},{}", frame, r.slot, r.object, r.fields)
            };
            if let Err(e) = result {
                s.error = Some(format!("trace write failed: {}", e));
            }
        }
        if frame % 60 == 0 {
            if let Err(e) = w.flush() {
                s.error = Some(format!("trace flush failed: {}", e));
            }
        }
    }
    s.rows_written += rows.len() as u64;
    rows.clear();
    s.rows = rows;
}

fn finish(s: &mut Session, reason: &str) {
    let goal = match s.mode {
        Mode::Running { goal } => goal,
        Mode::Arming { goal, .. } => {
            boot_log(&format!("{:?} cancelled while arming: {}", goal, reason));
            s.mode = Mode::Idle;
            s.owner = -1;
            return;
        }
        Mode::Idle => return,
    };
    if !s.rows.is_empty() { flush_rows(s); }
    if s.rows_written == 0 {
        s.error = Some("no state rows recorded".into());
    }
    if reason != "stopped by user" && reason != "end of inputs" && reason != "frame limit" {
        s.error = Some(reason.to_string());
    }
    // Inputs are saved even when the trace is invalid. They are the only record
    // of what the player actually pressed, and playback cannot be exercised at
    // all without them, so discarding them alongside a bad trace leaves us
    // unable to tell a failed capture from inputs that never reached the game.
    if goal == Goal::Record && !s.inputs.is_empty() {
        if let Err(e) = save_inputs(s) {
            let msg = format!("saving inputs failed: {}", e);
            boot_log(&format!("session {}: {}", s.number, msg));
            if s.error.is_none() {
                s.error = Some(msg);
            }
        }
    }
    if let Some(mut w) = s.writer.take() {
        let result = if let Some(e) = &s.error {
            writeln!(w, "# invalid {}", e)
        } else {
            writeln!(w, "# complete frames={} rows={}", s.frame + 1, s.rows_written)
        };
        if let Err(e) = result.and_then(|_| w.flush()) {
            s.error = Some(format!("final trace write failed: {}", e));
        }
    }
    if let Some(e) = &s.error { boot_log(&format!("session {} INVALID: {}", s.number, e)); }
    if s.extra_callbacks > 0 {
        boot_log(&format!(
            "session {}: {} extra Main callbacks dropped (first-wins)",
            s.number, s.extra_callbacks
        ));
    }
    boot_log(&format!(
        "session {} finished ({}): {:?}, {} frames, {} rows, {}",
        s.number,
        reason,
        goal,
        s.frame + 1,
        s.rows_written,
        s.trace_path
    ));
    s.mode = Mode::Idle;
    s.owner = -1;
}

/// Called once per frame per human player from the input hook.
pub fn on_input(idx: i32, out: &mut MappedInputs) {
    if !(0..16).contains(&idx) { return; }
    let _hook = match enter() { Some(g) => g, None => return };
    let mut guard = match SESSION.lock() {
        Ok(g) => g,
        Err(_) => return,
    };
    let s = &mut *guard;
    let slot = (idx as usize) & 15;
    let pressed = out.buttons & !s.prev_buttons[slot];
    s.prev_buttons[slot] = out.buttons;
    // Taunts are commands while this plugin is loaded; never pass them to the game.
    out.buttons &= !APPEAL_ALL;

    if let Some(reason) = s.abort.take() {
        finish(s, &reason);
    }

    match s.mode {
        Mode::Idle => {
            if pressed & APPEAL_HI != 0 {
                s.owner = idx;
                s.inputs.clear();
                s.perturb_frame = None;
                s.starts = [Start::default(); 8];
                s.seen_starts = [false; 8];
                s.mode = Mode::Arming { goal: Goal::Record, left: ARM_FRAMES };
                boot_log("record requested; arming");
            } else if pressed & (APPEAL_SL | APPEAL_SR) != 0 {
                // Left: exact playback. Right: playback with one neutral input
                // (self-test that a difference shows up in the comparison).
                let perturbed = pressed & APPEAL_SL == 0;
                match load_inputs(s, perturbed) {
                    Ok(()) => {
                        s.owner = idx;
                        s.seen_starts = [false; 8];
                        s.mode = Mode::Arming { goal: Goal::Play, left: ARM_FRAMES };
                        boot_log(&format!(
                            "play requested: {} ({} frames, perturb={:?}); arming",
                            s.source,
                            s.inputs.len(),
                            s.perturb_frame
                        ));
                    }
                    Err(e) => boot_log(&format!("play refused: {}", e)),
                }
            }
        }
        _ if idx != s.owner => {}
        Mode::Arming { goal, left } => {
            if pressed & APPEAL_LW != 0 {
                finish(s, "stopped by user");
                return;
            }
            *out = MappedInputs::default();
            if left > 1 {
                s.mode = Mode::Arming { goal, left: left - 1 };
            } else {
                begin(s, goal);
                // This same frame is input 0 of the session (unless begin failed).
                if let Mode::Running { .. } = s.mode {
                    running_input(s, goal, pressed, out);
                }
            }
        }
        Mode::Running { goal } => running_input(s, goal, pressed, out),
    }
}

fn running_input(s: &mut Session, goal: Goal, pressed: u32, out: &mut MappedInputs) {
    flush_rows(s);
    if let Some(e) = s.error.clone() {
        finish(s, &e);
        return;
    }
    if pressed & APPEAL_LW != 0 {
        finish(s, "stopped by user");
        return;
    }
    if goal == Goal::Record && s.inputs.len() >= MAX_FRAMES {
        finish(s, "frame limit");
        return;
    }
    s.frame += 1;
    match goal {
        Goal::Record => s.inputs.push(*out),
        Goal::Play => {
            let n = s.frame as usize;
            if n >= s.inputs.len() {
                // Undo the increment: the last traced frame was n - 1.
                s.frame -= 1;
                finish(s, "end of inputs");
                return;
            }
            *out = if Some(s.frame) == s.perturb_frame {
                MappedInputs::default()
            } else {
                s.inputs[n]
            };
        }
    }
}

unsafe fn is_active_fighter(boma: *mut BattleObjectModuleAccessor, entry: i32) -> bool {
    sample::current_fighter_id(entry).map_or(false, |id| id == (*boma).battle_object_id)
}

pub fn leave_training() {
    let _hook = match enter() { Some(g) => g, None => return };
    if let Ok(mut s) = SESSION.lock() {
        finish(&mut s, "left Training mode");
        s.prev_buttons = [0; 16];
    }
}

/// Called from every fighter's per-frame line.
pub unsafe fn on_fighter(boma: *mut BattleObjectModuleAccessor) {
    if !smash::app::smashball::is_training_mode() { leave_training(); return; }
    let _hook = match enter() { Some(g) => g, None => return };
    // The arm plan is decided under the lock and applied after it is dropped,
    // because applying it re-enters this very callback.
    let action = {
        let mut guard = match SESSION.lock() {
            Ok(g) => g,
            Err(_) => return,
        };
        let s = &mut *guard;
        let entry = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
        if !(0..8).contains(&entry) {
            return;
        }
        match s.mode {
            Mode::Idle => None,
            Mode::Arming { goal, left } => {
                if !is_active_fighter(boma, entry) {
                    return;
                }
                plan_arm(s, boma, entry as usize, goal, left)
            }
            Mode::Running { .. } => {
                let active = is_active_fighter(boma, entry);
                let row = sample::fighter_row(boma, entry, active);
                s.rows.push(row);
                None
            }
        }
    };
    if let Some(a) = action {
        apply_arm(boma, a);
    }
}

/// How an armed fighter should be brought back to WAIT.
#[derive(Clone, Copy, PartialEq, Debug)]
enum Wait {
    /// Already in WAIT; leave it alone.
    Keep,
    /// Ask for WAIT this frame.
    Request,
    /// Restart WAIT so its animation begins at frame 0 in every session.
    Force,
}

/// The game-state writes one armed fighter needs, decided under SESSION and
/// applied with SESSION released.
#[derive(Clone, Copy)]
struct ArmAction {
    pos: Vector3f,
    lr: f32,
    /// When set, heal to 0% and then add this much damage.
    damage: Option<f32>,
    wait: Wait,
}

/// Decides what an armed fighter needs and records its start state.
///
/// Runs with SESSION held, so it may only *read* fighter state: the writes are
/// deferred to `apply_arm` because heal, speed resets and status changes
/// re-enter the Main lines that call back into this module on this same thread.
unsafe fn plan_arm(
    s: &mut Session,
    boma: *mut BattleObjectModuleAccessor,
    slot: usize,
    goal: Goal,
    left: u32,
) -> Option<ArmAction> {
    s.seen_starts[slot] = true;
    let kind = crate::names::base_fighter_kind(smash::app::utility::get_kind(&mut *boma));
    let st = &mut s.starts[slot];
    if st.present && goal == Goal::Play && st.kind != kind {
        s.abort = Some(format!(
            "slot {} was {} when recorded but is {} now; switch form first",
            slot,
            crate::names::fighter_name(st.kind),
            crate::names::fighter_name(kind)
        ));
        return None;
    }
    let mut damage = None;
    if !st.present {
        if goal == Goal::Play {
            s.abort = Some(format!("slot {} is in the match but not in the recording", slot));
            return None;
        }
        if StatusModule::situation_kind(boma) != *SITUATION_KIND_GROUND {
            s.abort = Some(format!("slot {} must be standing on the ground to start", slot));
            return None;
        }
        let pos = &*PostureModule::pos(boma);
        *st = Start {
            present: true,
            applied_damage: true, // recording keeps the current percent
            x: pos.x,
            y: pos.y,
            lr: PostureModule::lr(boma),
            damage: DamageModule::damage(boma, 0),
            kind,
        };
    } else if !st.applied_damage {
        damage = Some(st.damage);
        st.applied_damage = true;
    }
    let wait = if left <= 1 {
        Wait::Force
    } else if StatusModule::status_kind(boma) != *FIGHTER_STATUS_KIND_WAIT {
        Wait::Request
    } else {
        Wait::Keep
    };
    Some(ArmAction {
        pos: Vector3f { x: st.x, y: st.y, z: 0.0 },
        lr: st.lr,
        damage,
        wait,
    })
}

/// Applies an armed fighter's start state. Called with SESSION released and
/// while the re-entrancy guard is still held, so the Main lines these calls
/// re-enter are skipped rather than allowed to recurse.
unsafe fn apply_arm(boma: *mut BattleObjectModuleAccessor, a: ArmAction) {
    if let Some(d) = a.damage {
        DamageModule::heal(boma, -DamageModule::damage(boma, 0), 0);
        DamageModule::add_damage(boma, d, 0);
    }
    KineticModule::clear_speed_all(boma);
    PostureModule::set_pos(boma, &a.pos);
    PostureModule::set_lr(boma, a.lr);
    match a.wait {
        Wait::Force => {
            StatusModule::change_status_force(boma, *FIGHTER_STATUS_KIND_WAIT, false);
        }
        Wait::Request => {
            StatusModule::change_status_request(boma, *FIGHTER_STATUS_KIND_WAIT, false);
        }
        Wait::Keep => {}
    }
}

/// Called from every weapon's per-frame line.
pub unsafe fn on_weapon(boma: *mut BattleObjectModuleAccessor) {
    if !smash::app::smashball::is_training_mode() { return; }
    let _hook = match enter() { Some(g) => g, None => return };
    // Articles outlive a session, so their animation phase keeps advancing
    // between two playbacks of identical inputs; on hardware that alone put
    // 334 differences into the control comparison. Resetting it is the known
    // open item, but the obvious approach is not safe: see below.
    let arming = match SESSION.lock() {
        Ok(g) => matches!(g.mode, Mode::Arming { .. }),
        Err(_) => return,
    };
    if arming {
        // REVERTED 2026-09-28. MotionModule::set_frame(boma, 0.0, false) was
        // tried here to reset that phase. It is not safe on a weapon: the run
        // that added it recorded "frame 0 has no callbacks", so the weapon Main
        // line stopped firing entirely, and the next attack raised a User Break
        // in status_Attack_Main_button. MotionModule is the fighter motion API;
        // articles need their own path, which has not been identified yet. Do
        // not retry this blindly. The identical experiment zeroing
        // INT_ATTACK_SERIAL via WorkModule::set_int was reverted at the same
        // time and is the other suspect for the same assert.
        let _ = arming;
    }
    let mut guard = match SESSION.lock() {
        Ok(g) => g,
        Err(_) => return,
    };
    let s = &mut *guard;
    if let Mode::Running { .. } = s.mode {
        if let Some(row) = sample::weapon_row(boma) {
            s.rows.push(row);
        }
    }
}
