#!/usr/bin/env bash
# Install the reskin onto the SD card.
#
# STANDING RULE (user, 2026-09-29): installing to the card is the agent's job, not
# the user's. It is part of finishing a build, and it stays part of the job for
# whoever this work is handed to. Do not print copy instructions and stop. Do not
# ask the user to do the copying. Run this.
#
# It used to be the opposite: this project deliberately never wrote to the card,
# on the theory that only the user should touch it. That was wrong in practice.
# Hand-copying three artefacts, one of them 793 files, is exactly how the card
# ended up running a 0.8.x build against an unpatched smashline plugin for an
# entire test cycle (2026-09-29). The "the agent cannot install" constraint was
# self-imposed and produced a silent, expensive failure. The user is still the
# only person who can *test* on the console, but installation is ours.
#
# Safety is kept, it is just not used as an excuse to not install:
#   - every overwrite is backed up first, into evidence/sd-backups/ (never into a
#     source tree; AGENTS rule 5) and the last five backups are kept
#   - directory installs are staged and swapped, never copied in place, so the
#     card is never left half-written
#   - everything is verified after the copy by hash and file count
#   - a failed verification rolls back automatically
#   - the card is identified by its own contents, and the script refuses to
#     write to a volume that does not look like the Switch card
#
# Usage:  ./install-to-card.sh [--no-smashline] [--dry-run]
#
#   --no-smashline  leave libsmashline_plugin.nro alone. It is a *patched local
#                   build* (it registers G&W's article on eflame) and it is
#                   version-locked to this card's 13.0.4. Do not "update" it from
#                   upstream: upstream releases target 13.0.5+ and will refuse to
#                   install their hooks here.
#   --dry-run       report what would be installed, touch nothing.
#   --reused-nro    the package reuses an already-built NRO verbatim (an
#                   asset-only variant of an installed release, whose cargo
#                   cache has since been pruned). Skips the "built NRO exists
#                   and equals the staged one" check, which cannot run without
#                   that cache, and instead requires the staged NRO to equal the
#                   NRO already on the card. That is the stronger statement for
#                   this case: the binary is not merely rebuilt, it is unchanged.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"

PLUG_REL="atmosphere/contents/01006A800016E000/romfs/skyline/plugins"
NRO="libpyra_gamewatch_reskin.nro"
SMASH_NRO="libsmashline_plugin.nro"
EFF_NRO="libone_slot_eff.nro"
MOD_NAME="pyra_gamewatch_reskin"

version="$(awk -F '"' '/^version =/ {print $2; exit}' "$here/plugin/Cargo.toml")"
package="${MGW_PACKAGE:-$root/builds/pgwr/$version}"
# Which cargo target dir holds this package's NRO.
#
# Precedence:
#   1. PGWR_CARGO_TARGET (absolute path, or a name under builds/.cache)
#   2. "cargo_target" recorded in the package's own MANIFEST.json - this is the
#      important one: a package built by one agent in an isolated cache must be
#      installed from that same cache, never from a shared one another agent is
#      also writing. On 2026-10-01 two agents sharing builds/.cache/pgwr-snake-target
#      caused a package to be installed with the *other* build's NRO.
#   3. the feature-derived default (kept for older packages with no such field)
cache_name=""
if [ -n "${PGWR_CARGO_TARGET:-}" ]; then
  case "$PGWR_CARGO_TARGET" in
    /*|[A-Za-z]:*) built_nro="$PGWR_CARGO_TARGET/aarch64-skyline-switch/release/$NRO" ;;
    *)             built_nro="$root/builds/.cache/$PGWR_CARGO_TARGET/aarch64-skyline-switch/release/$NRO" ;;
  esac
else
  if [ -f "$package/MANIFEST.json" ]; then
    cache_name="$(sed -n 's/.*"cargo_target":[[:space:]]*"\([^"]*\)".*/\1/p' "$package/MANIFEST.json" | head -1)"
  fi
  [ -n "$cache_name" ] || cache_name=pgwr-target
  if [ -f "$package/MANIFEST.json" ] && grep -q '"snake-neutral-b"' "$package/MANIFEST.json"; then
    [ "$cache_name" = pgwr-target ] && cache_name=pgwr-snake-target
  fi
  built_nro="$root/builds/.cache/$cache_name/aarch64-skyline-switch/release/$NRO"
fi
echo "cargo cache: $built_nro"
staged_nro="$package/$PLUG_REL/$NRO"
smash_src="$root/src/mgw_standalone/target-smashline/aarch64-skyline-switch/release/$SMASH_NRO"
eff_src="$package/$PLUG_REL/$EFF_NRO"
mod_src="$package/ultimate/mods/$MOD_NAME"

install_smashline=0   # default OFF: the card's smashline (5f4091ee...) is the good one; see AGENTS.md rule 22
dry_run=0
reused_nro=0
for arg in "$@"; do
  case "$arg" in
    --no-smashline) install_smashline=0 ;;
    --with-smashline) install_smashline=1 ;;
    --dry-run) dry_run=1 ;;
    --reused-nro) reused_nro=1 ;;
    -h|--help) sed -n '2,40p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "error: unknown argument $arg" >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'install-to-card: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- locate card
# Do not trust a remembered drive letter. Identify the volume by the files that
# make a Switch card a Switch card, and refuse anything else.
card=""
# Enumerate every mounted volume instead of guessing letters. The previous
# version used `ls -d /[a-z]`, which returns nothing in Git Bash on Windows
# (no single-character root entries), so autodetect found no card at all on this
# machine and the script refused to run. `mount` sees the real volumes; the
# identity test below is what actually decides which one is the card.
volumes() {
  {
    mount 2>/dev/null | sed -n 's,^\([^ ]*\) on /.*type[ ]\([^ ]*\).*,\1 \2,p'
    mount 2>/dev/null | sed -n 's,^\([^ ]*\) on \([^ ]*\) .*,\1 \2,p'
    df -P 2>/dev/null | awk 'NR>1 && $1 ~ /^\/|^[A-Za-z]:/ {print $1, $6}'
  } | awk '{print $1}' | sort -u
}
while read -r cand fstype; do
  [ -n "$cand" ] || continue
  [ -d "$cand" ] || continue
  if [ -d "$cand/$PLUG_REL" ] && [ -d "$cand/ultimate/mods" ] && [ -d "$cand/atmosphere" ]; then
    card="$cand"; break
  fi
done <<EOF
$(volumes)
EOF
# Last resort: every single-letter path that exists, in case mount/df are absent.
if [ -z "$card" ]; then
  for letter in a b c d e f g h i j k l m n o p q r s t u v w x y z; do
    cand="/$letter"
    [ -d "$cand" ] || continue
    if [ -d "$cand/$PLUG_REL" ] && [ -d "$cand/ultimate/mods" ] && [ -d "$cand/atmosphere" ]; then
      card="$cand"; break
    fi
  done
fi
[ -n "$card" ] || die "no volume found holding $PLUG_REL + ultimate/mods + atmosphere.
Mount the Switch's SD card, or run with the card already inserted. Not writing
to any volume that does not look like the card.
Volumes seen: $(volumes | tr '\n' ' ')"

# Sanity: never let a stray root or home directory satisfy the check.
case "$card" in /|/c|/c/Users|"$HOME") die "refusing to install to $card" ;; esac

# Resolve every recursive deletion inside its explicitly named scope.
safe_remove() {
  local resolved
  resolved="$(realpath -m -- "$1")"
  case "$resolved" in
    "$card/ultimate/mods/$MOD_NAME"|"$card/ultimate/mods/$MOD_NAME.new"|"$root/evidence/sd-backups/"sd-backup-[0-9]*)
      rm -rf -- "$resolved" ;;
    *) die "refusing recursive removal outside install/backup scope: $resolved" ;;
  esac
}

say "card: $card"

# ------------------------------------------------------------------- check src
if [ "$reused_nro" -eq 1 ]; then
  [ -f "$staged_nro" ] || die "no staged reskin NRO at $staged_nro"
  [ -f "$card/$PLUG_REL/$NRO" ] || die "--reused-nro given but the card has no $NRO to compare against"
  cmp -s "$staged_nro" "$card/$PLUG_REL/$NRO" \
    || die "--reused-nro: the staged NRO is NOT the one already on the card.
This flag asserts the package reuses the installed binary unchanged. If the
package really carries a new build, drop the flag and rebuild into the cache
named by the package MANIFEST (cargo_target), so the built-vs-staged check runs."
  say "reused NRO: staged == card, byte for byte (no rebuild, no new binary)"
else
  [ -f "$built_nro" ] || die "no built reskin NRO at $built_nro (run ./build-plugin.sh first)"
  [ -f "$staged_nro" ] || die "no staged reskin NRO at $staged_nro (run ./build-plugin.sh first)"
  cmp -s "$built_nro" "$staged_nro" || die "staged NRO differs from the freshly built one; re-run ./build-plugin.sh"
fi
[ -f "$eff_src" ] || die "no one_slot_eff NRO at $eff_src (run build.py first)"
[ -d "$mod_src" ] || die "no built mod tree at $mod_src (run build.py first)"

want_files="$(find "$mod_src" -type f | wc -l | tr -d ' ')"
[ "$want_files" -gt 0 ] || die "built mod tree at $mod_src is empty"

if [ "$install_smashline" -eq 1 ]; then
  [ -f "$smash_src" ] || die "no patched smashline build at $smash_src
Build it with:
  cd src/mgw_standalone/smashline_1304
  PATH=\"${MSYS2_MINGW_BIN}:\$PATH\" CARGO_TARGET_DIR=../target-smashline \\
    cargo skyline build --release -- --offline
or re-run with --no-smashline to leave the card's existing plugin untouched."
fi

if [ "$reused_nro" -eq 1 ]; then
  say "reskin NRO : $(sha256sum "$staged_nro" | cut -d' ' -f1)  ($want_files mod files)"
else
  say "reskin NRO : $(sha256sum "$built_nro" | cut -d' ' -f1)  ($want_files mod files)"
fi
say "one_slot_eff: $(sha256sum "$eff_src" | cut -d' ' -f1)"
[ "$install_smashline" -eq 1 ] && say "smashline  : $(sha256sum "$smash_src" | cut -d' ' -f1)  (patched, 13.0.4)"

if [ "$dry_run" -eq 1 ]; then
  say ""
  say "dry run: nothing written."
  exit 0
fi

# --------------------------------------------------------------------- backup
stamp="$(date +%Y%m%d-%H%M%S)"
backup_root="$root/evidence/sd-backups"
backup="$backup_root/sd-backup-$stamp"
mkdir -p "$backup/plugins"
for f in "$NRO" "$SMASH_NRO" "$EFF_NRO"; do
  [ -f "$card/$PLUG_REL/$f" ] && cp -a "$card/$PLUG_REL/$f" "$backup/plugins/$f"
done
if [ -d "$card/ultimate/mods/$MOD_NAME" ]; then
  say "backing up current mod folder ($(find "$card/ultimate/mods/$MOD_NAME" -type f | wc -l | tr -d ' ') files)..."
  tar -cf "$backup/card-mod-folder.tar" -C "$card/ultimate/mods" "$MOD_NAME"
fi
echo "$stamp" > "$here/.last-sd-backup"
say "backup: $backup"
# AGENTS rule 5: prune to the last five backups.
ls -1dt "$backup_root"/sd-backup-* 2>/dev/null | tail -n +6 | while IFS= read -r old; do
  safe_remove "$old"
done

rollback() {
  trap - ERR
  say ""
  say "VERIFY FAILED - rolling back to the backup."
  rollback_plugins=("$NRO" "$EFF_NRO")
  [ "$install_smashline" -eq 0 ] || rollback_plugins+=("$SMASH_NRO")
  for f in "${rollback_plugins[@]}"; do
    if [ -f "$backup/plugins/$f" ]; then
      cp -a "$backup/plugins/$f" "$card/$PLUG_REL/$f"
    else
      rm -f "$card/$PLUG_REL/$f"
    fi
  done
  if [ -f "$backup/card-mod-folder.tar" ]; then
    safe_remove "$card/ultimate/mods/$MOD_NAME"
    tar -xf "$backup/card-mod-folder.tar" -C "$card/ultimate/mods"
  fi
  sync
  say "rolled back. Card is back to the state in $backup."
}

# ------------------------------------------------------------------- install
trap 'rollback; exit 1' ERR
# Verify staged files before replacing the current plugins.
if [ "$reused_nro" -eq 1 ]; then src_nro="$staged_nro"; else src_nro="$built_nro"; fi
cp "$src_nro" "$card/$PLUG_REL/$NRO.new"
cmp "$src_nro" "$card/$PLUG_REL/$NRO.new"
mv -f "$card/$PLUG_REL/$NRO.new" "$card/$PLUG_REL/$NRO"
cp "$eff_src" "$card/$PLUG_REL/$EFF_NRO.new"
cmp "$eff_src" "$card/$PLUG_REL/$EFF_NRO.new"
mv -f "$card/$PLUG_REL/$EFF_NRO.new" "$card/$PLUG_REL/$EFF_NRO"
if [ "$install_smashline" -eq 1 ]; then
  cp "$smash_src" "$card/$PLUG_REL/$SMASH_NRO"
fi

# Mod tree: stage, verify, then swap. Copying files straight onto the card
# leaves it inconsistent for as long as the copy takes, and a failure halfway
# through would brick the next launch.
stage="$card/ultimate/mods/$MOD_NAME.new"
safe_remove "$stage"
say "staging $want_files mod files..."
cp -a "$mod_src" "$stage"
got_files="$(find "$stage" -type f | wc -l | tr -d ' ')"
if [ "$got_files" != "$want_files" ]; then
  safe_remove "$stage"
  rollback
  die "staged file count $got_files != built $want_files"
fi
diff -r -q "$mod_src" "$stage"
safe_remove "$card/ultimate/mods/$MOD_NAME"
mv "$stage" "$card/ultimate/mods/$MOD_NAME"
sync

# -------------------------------------------------------------------- verify
fail=0
cmp -s "$src_nro" "$card/$PLUG_REL/$NRO" || { say "MISMATCH: $NRO"; fail=1; }
cmp -s "$eff_src" "$card/$PLUG_REL/$EFF_NRO" || { say "MISMATCH: $EFF_NRO"; fail=1; }
if [ "$install_smashline" -eq 1 ]; then
  cmp -s "$smash_src" "$card/$PLUG_REL/$SMASH_NRO" || { say "MISMATCH: $SMASH_NRO"; fail=1; }
fi
card_files="$(find "$card/ultimate/mods/$MOD_NAME" -type f | wc -l | tr -d ' ')"
[ "$card_files" = "$want_files" ] || { say "MISMATCH: mod tree has $card_files files, expected $want_files"; fail=1; }
diff -r -q "$mod_src" "$card/ultimate/mods/$MOD_NAME" >/dev/null || { say "MISMATCH: mod tree differs from build"; fail=1; }

if [ "$fail" -ne 0 ]; then
  rollback
  die "install did not verify; card restored from $backup"
fi

say ""
say "installed and verified:"
say "  $card/$PLUG_REL/$NRO"
say "  $card/$PLUG_REL/$EFF_NRO"
[ "$install_smashline" -eq 1 ] && say "  $card/$PLUG_REL/$SMASH_NRO"
say "  $card/ultimate/mods/$MOD_NAME/  ($card_files files)"
say ""
say "Next: boot the game and do the console test. The user is the only one who"
say "can test; do not report the build as working until they have run it."
