#!/usr/bin/env bash
# Build the mii_customizer Skyline plugin to an NRO and stage it in builds/<version>-<variant>/.
#
# Build-only. Installs nothing, talks to no console and no network device, and
# never runs `cargo skyline install` / `run` / `listen`. Fetching the pinned
# crates through cargo is the only network use (project-local dependency).
#
# Usage, from anywhere inside the workspace:
#   mods/mii_customizer/build-plugin.sh              # offline build (default)
#   mods/mii_customizer/build-plugin.sh --online     # allow cargo to fetch
#
# Variant: 0.0.1 staged as "scaffold", 0.1.x as "diag" (log-only), 0.2.x as "override"
# (research/P4-OVERRIDE-SLICE.md), 0.3.x as "presets" (research/P7-PRESET-ENGINE.md), 0.4.x
# as "ui" (research/P10-UI-SLICE.md), from 0.5.0 as "menu" (research/P11-MENU.md).
#
# Follows kb/reference/cargo-skyline.md:
#   * cargo/cargo-skyline live in $HOME/.cargo/bin (Git Bash path).
#   * Invoke cargo directly from Git Bash; a cmd batch wrapper is not used,
#     because `cmd //c build.cmd` mis-resolves the path here.
#   * System32 goes first on PATH so cargo-skyline does not pick the devkitPro
#     `cmd` stub when it launches Windows commands.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
crate="$here/plugin"
version="$(awk -F '"' '/^version =/ {print $2; exit}' "$crate/Cargo.toml")"
case "$version" in
  0.0.1) variant="scaffold" ;;
  0.1.*) variant="diag" ;;
  0.2.*) variant="override" ;;
  0.3.*) variant="presets" ;;
  0.4.*) variant="ui" ;;
  0.8.*|0.9.*) variant="moves" ;;
  *)     variant="menu" ;;
esac
pkg="$here/builds/$version-$variant"
target_dir="$here/builds/.cache/plugin-target"

export PATH="$HOME/.cargo/bin:$PATH"
export CARGO_TARGET_DIR="$target_dir"

winroot="${SYSTEMROOT:-${WINDIR:-}}"
if [ -n "$winroot" ]; then
  export PATH="$(cygpath -u "$winroot")/System32:$PATH"
fi

mkdir -p "$target_dir" "$here/builds/.cache"
log="$here/builds/.cache/build-$version.log"

# `--offline` is the default: every pinned crate is already in this machine's
# cargo cache (verified below). Drop it when a new pin needs fetching once.
cargo_args=(skyline build --release)
[ "${1:-}" = "--online" ] || cargo_args+=(-- --offline)

echo "command: cargo ${cargo_args[*]}"
echo "crate:   $crate"
echo "version: $version ($variant)"
echo "target:  $CARGO_TARGET_DIR"
set +e
( cd "$crate" && cargo "${cargo_args[@]}" ) > "$log" 2>&1
status=$?
set -e
echo "exit:    $status"
echo "log:     $log"
[ "$status" -eq 0 ] || { tail -40 "$log"; exit "$status"; }

built="$CARGO_TARGET_DIR/aarch64-skyline-switch/release/libmii_customizer.nro"
[ -f "$built" ] || { echo "NRO missing: $built"; exit 1; }

mkdir -p "$pkg"
cp "$built" "$pkg/libmii_customizer.nro"
cmp "$built" "$pkg/libmii_customizer.nro"
sha256sum "$built" "$pkg/libmii_customizer.nro"
stat -c '%n %s bytes' "$pkg/libmii_customizer.nro"
echo "staged:  $pkg/libmii_customizer.nro"