#!/usr/bin/env bash
# Build and run the host-side unit tests of the pure part of plugin 0.5.0:
#   1. the 0.3.0 tests (scratch/2026-10-05_P7-PRESET-ENGINE/host_test.rs: preset.rs, loadout.rs,
#      logic.rs), unchanged, against the current sources;
#   2. this task's tests (host_test.rs next to this script: list.rs, ui.rs, menu.rs,
#      Store::set_preset, loadout::load).
# Binaries go to builds/.cache/host-test/. No skyline toolchain involved.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mod="$(cd "$here/../.." && pwd)"
export PATH="$HOME/.cargo/bin:$PATH"
out="$mod/builds/.cache/host-test"
mkdir -p "$out"
# kb/reference/local-machine.md: no MSVC link.exe here, host programs use the gnu toolchain.
# MC_MOD_DIR is only read by the tests that parse delivered files.
export MC_MOD_DIR="$(cd "$mod" && pwd -W 2>/dev/null || pwd)"
echo "== 0.3.0 tests (P7) on the current sources"
rustc +stable-x86_64-pc-windows-gnu --edition 2021 --test -O \
  "$mod/scratch/2026-10-05_P7-PRESET-ENGINE/host_test.rs" -o "$out/host_test_p7.exe"
"$out/host_test_p7.exe"
echo "== 0.5.0 tests (P11)"
rustc +stable-x86_64-pc-windows-gnu --edition 2021 --test -O "$here/host_test.rs" -o "$out/host_test_p11.exe"
"$out/host_test_p11.exe"
