#!/usr/bin/env bash
# Build and run the host-side unit tests of plugin/src/loadout.rs + logic.rs.
# Output binary goes to builds/.cache/host-test/. Needs builds/0.2.0-override/example/loadouts.txt.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mod="$(cd "$here/../.." && pwd)"
export PATH="$HOME/.cargo/bin:$PATH"
mkdir -p "$mod/builds/.cache/host-test"
# kb/reference/local-machine.md: no MSVC link.exe here, host programs use the gnu toolchain.
# MC_MOD_DIR is only read by the test that parses the delivered example file.
export MC_MOD_DIR="$(cd "$mod" && pwd -W 2>/dev/null || pwd)"
rustc +stable-x86_64-pc-windows-gnu --edition 2021 --test -O "$here/host_test.rs" -o "$mod/builds/.cache/host-test/host_test_p4.exe"
"$mod/builds/.cache/host-test/host_test_p4.exe"
