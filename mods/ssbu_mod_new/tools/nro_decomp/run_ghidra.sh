#!/usr/bin/env bash
# Decompile functions of a lua2cpp_<fighter>.nro with headless Ghidra.
#   GHIDRA_HOME=<ghidra_11.1.2_PUBLIC> tools/nro_decomp/run_ghidra.sh <fighter.nro> <workdir> <out.c> [0xADDR ...]
# No addresses: decompiles every caller of sv_set_status_func. workdir (use scratch/<date>_<agent>/) receives the
# flattened image, labels and the Ghidra project; the first run imports+analyses (~3 min), later runs reuse it.
# GHIDRA_HOME: see paths.toml [toolchain].ghidra_home. Needs c++filt on PATH (paths.toml msys2_mingw).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../.." && pwd)
nro=$1; work=$2; out=$3; shift 3
py="$root/toolchains/py312/python.exe"; mkdir -p "$work/ghproj"
w=$(cygpath -w "$work" 2>/dev/null || echo "$work"); s=$(cygpath -w "$here/ghidra_scripts" 2>/dev/null || echo "$here/ghidra_scripts")
hl="$GHIDRA_HOME/support/analyzeHeadless"; [ -f "$hl.bat" ] && hl="$hl.bat"
if [ ! -f "$work/ghproj/nro.gpr" ]; then
  "$py" "$here/nro_flatten.py" "$nro" "$work/nro.bin" "$work/nro_labels.json"
  "$hl" "$w/ghproj" nro -import "$w/nro.bin" -processor AARCH64:LE:64:v8A -loader BinaryLoader -loader-baseAddr 0 \
    -scriptPath "$s" -preScript NroLabels.py "$w/nro_labels.json" -analysisTimeoutPerFile 1500 > "$work/ghidra_import.log" 2>&1
fi
"$hl" "$w/ghproj" nro -process nro.bin -noanalysis -scriptPath "$s" -postScript DecompStatus.py "$w/raw.c" "$@" > "$work/ghidra_post.log" 2>&1
"$py" "$here/annotate_c.py" "$work/nro.bin" "$work/nro_labels.json" "$work/raw.c" "$out"
echo "wrote $out"
