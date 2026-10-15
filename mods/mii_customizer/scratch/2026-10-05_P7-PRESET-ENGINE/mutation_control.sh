#!/usr/bin/env bash
# Negative control for the host tests: each mutation of a copy of the three pure source files
# must make at least one test fail (or stop the test from compiling). Works on copies under
# builds/.cache/host-test/mut7/; plugin/src is not touched.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mod="$(cd "$here/../.." && pwd)"
export PATH="$HOME/.cargo/bin:$PATH"
export MC_MOD_DIR="$(cd "$mod" && pwd -W 2>/dev/null || pwd)"
work="$mod/builds/.cache/host-test/mut7"
caught=0; missed=0
only="${1:-}"   # optional: run only the mutations whose name contains this text
run() { # name, file, sed expression
  case "$1" in *"$only"*) ;; *) return ;; esac
  rm -rf "$work"; mkdir -p "$work/plugin/src" "$work/scratch/x"
  cp "$mod/plugin/src/loadout.rs" "$mod/plugin/src/logic.rs" "$mod/plugin/src/preset.rs" "$work/plugin/src/"
  cp "$here/host_test.rs" "$work/scratch/x/"
  before="$(sha256sum "$work/plugin/src/$2" | cut -d' ' -f1)"
  sed -i "$3" "$work/plugin/src/$2"
  after="$(sha256sum "$work/plugin/src/$2" | cut -d' ' -f1)"
  if [ "$before" = "$after" ]; then echo "NOT APPLIED  $1"; missed=$((missed+1)); return; fi
  if ! rustc +stable-x86_64-pc-windows-gnu --edition 2021 --test -C opt-level=1 "$work/scratch/x/host_test.rs" -o "$work/t.exe" 2> "$work/rustc.log"; then
    echo "CAUGHT (does not compile)  $1"; caught=$((caught+1)); return; fi
  if "$work/t.exe" > "$work/out.txt" 2>&1; then echo "MISSED  $1"; missed=$((missed+1));
  else echo "CAUGHT ($(grep -c 'FAILED$' "$work/out.txt") tests fail)  $1"; caught=$((caught+1)); fi
}
# --- preset file (contract A)
run 'preset file limit 512 KiB + 1'              preset.rs  's/pub const MAX_FILE: usize = 512 \* 1024;/pub const MAX_FILE: usize = 512 * 1024 + 1;/'
run '129 presets accepted'                       preset.rs  's/pub const MAX_PRESETS: usize = 128;/pub const MAX_PRESETS: usize = 129;/'
run '49 fields per preset accepted'              preset.rs  's/pub const MAX_PRESET_FIELDS: usize = 48;/pub const MAX_PRESET_FIELDS: usize = 49;/'
run '49 distinct field hashes accepted'          preset.rs  's/pub const MAX_FILE_HASHES: usize = 48;/pub const MAX_FILE_HASHES: usize = 49;/'
run '32-character preset names accepted'         preset.rs  's/pub const NAME_MAX: usize = 31;/pub const NAME_MAX: usize = 32;/'
run 'preset version line 2 accepted'             preset.rs  's/"mc_presets 1"/"mc_presets 2"/'
run 'preset reject log 33 lines'                 preset.rs  's/pub const REJECT_LOG_LIMIT: usize = 32;/pub const REJECT_LOG_LIMIT: usize = 33;/'
run 'duplicate preset name accepted'             preset.rs  's/if self.find_name(name).is_some() {/if false {/'
run 'repeated field replaces the first value'    preset.rs  's/if have \& (1u64 << field) != 0 {/if false {/'
run 'field hash zero accepted'                   preset.rs  's/Some(0) | None => Err(Reject::BadHash),/None => Err(Reject::BadHash),/'
run 'upper-case preset names accepted'           preset.rs  "s/matches!(\*b, b'a'..=b'z' | /matches!(*b, b'A'..=b'Z' | b'a'..=b'z' | /"
run '9-digit hashes accepted'                    preset.rs  's/if rest.len() == 10 => rest,/if rest.len() >= 9 \&\& rest.len() <= 10 => rest,/'
run 'fields after a rejected fighter line join the previous preset' preset.rs 's/^            current = Current::Skipping;$//'
run 'field line before any fighter line not reported' preset.rs 's/Current::Start => Err(Reject::NoPreset),/Current::Start => continue,/'
run 'preset value read without its presence bit' preset.rs  's/if self.masks.get(preset)?.load(Ordering::Relaxed) \& (1u64 << field) == 0 {/if false {/'
# --- field hash table (contract D)
run 'lookup does not stop at an empty slot'      preset.rs  's/            if key == 0 {$/            if key == 1 {/'
run 'probe bound not maintained'                 preset.rs  's/if examined > self.probe_max.load(Ordering::Relaxed) {/if false {/'
run 'lookup compares only the low 32 bits'       preset.rs  's/            if key == hash {$/            if key as u32 == hash as u32 {/'
# --- loadout file (contract B)
run 'weight upper bound 140 -> 141'              loadout.rs 's/(60.0, 140.0)/(60.0, 141.0)/'
run 'walk_speed_max lower bound 0.5 -> 0.4'      loadout.rs 's/(0.5, 2.0)/(0.4, 2.0)/'
run 'ID 00000000 accepted'                       loadout.rs 's/if id == 0 {$/if false {/'
run 'version line 3 accepted instead of 2'       loadout.rs 's/"mc_loadouts 2"/"mc_loadouts 3"/'
run 'version line 1 no longer accepted'          loadout.rs 's/"mc_loadouts 1"/"mc_loadouts 0"/'
run 'preset key accepted in a version 1 file'    loadout.rs 's/if report.version >= 2 \&\& key_field == PRESET_KEY {/if key_field == PRESET_KEY {/'
run '33 ids accepted'                            loadout.rs 's/pub const MAX_IDS: usize = 32;/pub const MAX_IDS: usize = 33;/'
run 'loadout file limit 16 KiB + 1'              loadout.rs 's/pub const MAX_FILE: usize = 16 \* 1024;/pub const MAX_FILE: usize = 16 * 1024 + 1;/'
run 'loadout reject log 64 lines'                loadout.rs 's/pub const REJECT_LOG_LIMIT: usize = 32;/pub const REJECT_LOG_LIMIT: usize = 64;/'
run 'exponent accepted as digit'                 loadout.rs "s/b'\.' if !seen_point => seen_point = true,/b'.' if !seen_point => seen_point = true, b'e' => {}/"
run 'range check of explicit values skipped'     loadout.rs 's/Some(value) if !in_range(key, value) => Err(Reject::OutOfRange),/Some(value) if false => Err(Reject::OutOfRange),/'
run 'unknown preset becomes preset 0'            loadout.rs 's/presets.find_name(name).ok_or(Reject::UnknownPreset)/Ok(presets.find_name(name).unwrap_or(0))/'
run 'preset name syntax not checked'             loadout.rs 's/let found = if !crate::preset::valid_name(name) {/let found = if false {/'
run 'rejected preset line keeps the earlier preset' loadout.rs 's/report.cleared += table.clear_preset(id) as u32;//'
run 'entry without content stays in the table'   loadout.rs 's/^        if empty {$/        if false {/'
# --- resolution order
run 'explicit value ignored (preset wins)'       loadout.rs 's/if field < KEYS \&\& self.has.get(entry)?.get(field)?.load(Ordering::Relaxed) {/if false {/'
run 'explicit key index not limited to its two fields' loadout.rs 's/if field < KEYS \&\& self.has.get(entry)?/if self.has.get(entry)?/'
run 'preset index off by one'                    loadout.rs 's/let value = presets.value(preset as usize - 1, field)?;/let value = presets.value(preset as usize, field)?;/'
run 'ID 0 can have a loadout'                    loadout.rs 's/^        if id == 0 {$/        if false {/'
run 'OV mark not kept per field'                 loadout.rs 's/Some(mask) => mask.fetch_or(1u64 << field, Ordering::Relaxed) \& (1u64 << field) == 0,/Some(_) => true,/'
# --- serialisation
run 'explicit lines not written'                 loadout.rs 's/if entry.has.get(key) != Some(\&true) {/if true {/'
run 'preset line not written'                    loadout.rs 's/if let Some(preset) = entry.preset {/if let (Some(preset), false) = (entry.preset, true) {/'
run 'value text not verified by re-parsing'      loadout.rs 's/if parse_decimal_bytes(text).map(f32::to_bits) == Some(value.to_bits()) {/if true {/'
run 'serialise ignores the 16 KiB limit and overflow' loadout.rs 's/if w.overflow || w.len > MAX_FILE {/if false {/'
run 'table equality ignores values'              loadout.rs 's/\.all(|(has, (a, b))| !\*has || a.to_bits() == b.to_bits())/.all(|_| true)/'
run 'table equality ignores the preset'          loadout.rs 's/            \&\& self.preset == other.preset$//'
run 'snapshot drops presets'                     loadout.rs 's/let _ = table.set_preset(id, preset as usize - 1);//'
# --- decision (contract C) and identity
run 'kind test removed from decide'              logic.rs   's/if !kinds.contains(\&ident.kind) {/if false {/'
run 'accepted kind 74 -> 75'                     logic.rs   's/pub const KIND_MIIGUNNER: i32 = 0x4a;/pub const KIND_MIIGUNNER: i32 = 0x4b;/'
run 'slot id 0 allowed'                          logic.rs   's/if slot_id == 0 {/if false {/'
run 'round trip not required'                    logic.rs   's/if !f.round_trip {/if false {/'
run 'category by id not required'                logic.rs   's/if f.cat_object != f.fighter_cat {/if false {/'
run 'entry mismatch tolerated'                   logic.rs   's/if f.entry_accessor != f.entry_object {/if false {/'
run 'entry id 8 allowed'                         logic.rs   's/f.entry_accessor >= PLAYERS as i32/f.entry_accessor > PLAYERS as i32/'
run 'other vtable accepted'                      logic.rs   's/if x0 == 0 || vt_class != 1 {/if x0 == 0 || vt_class == 0 {/'
run 'back-pointer not required'                  logic.rs   's/} else if back != x0 {/} else if false {/'
run 're-entry not detected'                      logic.rs   's/return Enter::Reentry;/{}/'
run 'hook site offset changed'                   logic.rs   's/offset: 0x4e_53e0,/offset: 0x4e_53f0,/'
# --- logging bounds
run '17 L3 lines per fighter'                    logic.rs   's/pub const L3_HASHES_PER_PARENT: u32 = 16;/pub const L3_HASHES_PER_PARENT: u32 = 17;/'
run 'every request of a field logged'            logic.rs   's/let first = fields.load(Ordering::Relaxed) \& bit == 0 \&\& fields.fetch_or(bit, Ordering::AcqRel) \& bit == 0;/let first = true;/'
run 'seen key ignores the identity'              logic.rs   's/ ^ who.wrapping_mul(0xc2b2_ae3d_27d4_eb4f)//'
run 'L5 every 600 requests instead of doubling'  logic.rs   's/ \&\& (n \/ L5_FIRST).is_power_of_two()//'
run 'field flag fires every time'                logic.rs   's/self.0.load(Ordering::Relaxed) \& bit == 0 \&\& self.0.fetch_or(bit, Ordering::Relaxed) \& bit == 0$/{ self.0.fetch_or(bit, Ordering::Relaxed); true }/'
rm -rf "$work"
echo "$caught caught, $missed missed"
[ "$missed" -eq 0 ]
