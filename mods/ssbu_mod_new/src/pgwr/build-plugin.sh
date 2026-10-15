#!/usr/bin/env bash
# Build and stage the versioned pgwr plugin; install unless --stage-only.
# Assets must already be built with build.py. Framework installation defaults OFF.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
version="$(awk -F '"' '/^version =/ {print $2; exit}' "$here/plugin/Cargo.toml")"
export MGW_PACKAGE="${MGW_PACKAGE:-$root/builds/pgwr/$version}"
export CARGO_TARGET_DIR="$root/builds/.cache/pgwr-target"
stage_only=0
snake_neutral_b=0
with_logging=0
install_args=()
for arg in "$@"; do
  case "$arg" in
    --stage-only) stage_only=1 ;;
    --snake-neutral-b) snake_neutral_b=1 ;;
    --with-logging) with_logging=1 ;;
    --no-smashline) install_args+=(--no-smashline) ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done
if [ "$snake_neutral_b" -eq 1 ]; then
  # Keep other agents' ready default builds in their original cache.
  export CARGO_TARGET_DIR="$root/builds/.cache/pgwr-snake-target"
  test -f "$MGW_PACKAGE/snake_neutral_b_assets.json"
  test -f "$MGW_PACKAGE/snake_neutral_b_sound.json"
fi
# Avoid the devkitPro cmd stub when cargo-skyline launches Windows commands.
winroot="${SYSTEMROOT:-${WINDIR:-}}"
[ -z "$winroot" ] || export PATH="$(cygpath -u "$winroot")/System32:$PATH"
mingw="$(awk -F '"' '/^msys2_mingw =/ {print $2; exit}' "$root/paths.toml")"
export PATH="$(cygpath -u "$mingw"):$PATH"
cd "$here/plugin"
features=()
[ "$snake_neutral_b" -eq 1 ] && features+=(snake-neutral-b)
[ "$with_logging" -eq 1 ] && features+=(logging)

if [ "${#features[@]}" -gt 0 ]; then
  feature_list="$(IFS=,; echo "${features[*]}")"
  cargo skyline build --release --features "$feature_list" -- --offline
else
  cargo skyline build --release -- --offline
fi
nro="libpyra_gamewatch_reskin.nro"
built="$CARGO_TARGET_DIR/aarch64-skyline-switch/release/$nro"
staged="$MGW_PACKAGE/atmosphere/contents/01006A800016E000/romfs/skyline/plugins"
mkdir -p "$staged"
cp "$built" "$staged/$nro"
cmp "$built" "$staged/$nro"
sha256sum "$staged/$nro"
[ "$stage_only" -eq 0 ] || exit 0
exec "$here/install-to-card.sh" "${install_args[@]}"
