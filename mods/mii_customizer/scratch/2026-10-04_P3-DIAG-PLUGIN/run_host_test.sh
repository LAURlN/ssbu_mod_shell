#!/usr/bin/env bash
# Build and run the host-side unit tests of plugin/src/logic.rs. Output binary goes to builds/.cache/.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mod="$(cd "$here/../.." && pwd)"
export PATH="$HOME/.cargo/bin:$PATH"
mkdir -p "$mod/builds/.cache/host-test"
# kb/reference/local-machine.md: no MSVC link.exe here, host programs use the gnu toolchain.
rustc +stable-x86_64-pc-windows-gnu --edition 2018 --test -O "$here/host_test.rs" -o "$mod/builds/.cache/host-test/host_test.exe"
"$mod/builds/.cache/host-test/host_test.exe"
