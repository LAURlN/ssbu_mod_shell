#!/usr/bin/env bash
# P2-SKILL-NATIVE: regenerate every raw window cited in research/P2-SKILL-NATIVE.md.
# Run from the workspace root.
set -euo pipefail
S=mods/mii_customizer/scratch/2026-10-04_P2-SKILL-NATIVE
E=mods/mii_customizer/evidence/P2-SKILL-NATIVE
export PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python
mkdir -p "$E"

{
  echo "# P2-SKILL-NATIVE raw windows (tier B, offline static read of gamedata/ssbu-13.0.4/main.bin)"
  echo "# sha256 f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613"
  echo "# flat MOD0 image, address == file offset"
  echo
  echo "## step 1: string search  (scratch/.../strfind.py)"
  cat "$S/step1_strings.txt"
  echo
  echo "## step 2: adrp+add reference sites  (scratch/.../refscan.py)"
  cat "$S/step2_refs.txt"
  echo
  echo "## step 5: delegate vtable relocation records  (scratch/.../relocs.py)"
  echo "# control first: vtable 0x50a6d28 is the one P1-ID-REVIEW already decoded"
  python "$S/relocs.py" 0x50a6d28 3
  echo
  sed -n '/vtable 0x50a6e78/,$p' "$S/step5_vtables.txt"
} > "$E/00_search_and_vtables.txt"

# ---- step 3: per-site windows, 60 instructions before and 30 after the adrp+add ----
# site = the adrp+add completion address that yields the name string address.
: > "$E/01_reference_sites.txt"
while read -r label site; do
  start=$(( site - 60 * 4 ))
  stop=$(( site + 30 * 4 ))
  {
    echo "==============================================================="
    echo "# name        : $label"
    echo "# site        : $site   (adrp+add completion producing the name pointer)"
    echo "# window      : $start .. $stop   ($(( (stop-start)/4 + 1 )) instructions, 60 before / 30 after)"
    echo "==============================================================="
    python "$S/w.py" "$start" $(( (stop - start) / 4 + 1 ))
    echo
  } >> "$E/01_reference_sites.txt"
done <<'EOF'
set_skill_id 0x19de10c
get_skill_id 0x19de1bc
get_skill_name_label 0x19de268
get_skill_help_label 0x19de310
replace_skill 0x19de3b0
replace_skill_subwindow 0x19de45c
EOF

# ---- step 3b: enclosing function 0x19ddb30 (prologue through ret) ----
cp "$S/enclosing_fn_only.txt" "$E/02_enclosing_function_0x19ddb30.txt"

# ---- step 4: first 40 instructions of each handler ----
: > "$E/03_handler_windows.txt"
for h in 0x19dcf20 0x19dcf40 0x19dcf60 0x19dd080 0x19dd1a0 0x19dd250; do
  {
    echo "==============================================================="
    echo "# handler address: $h   (first 40 instructions, raw window)"
    echo "# candidate function start: see '00_candidates' line below"
    echo "==============================================================="
    python "$S/w.py" "$h" 40
    echo
  } >> "$E/03_handler_windows.txt"
done

# ---- step 5b: invoke thunks, full bodies ----
{
  echo "# invoke thunks. slot0 of every vtable is 0x19c2210; slot2 (the third relocated"
  echo "# slot, per P1-ID-REVIEW 2.3) is the invoke thunk that converts Lua arguments."
  echo "# The post_fighter control thunk 0x19dc650 is dumped first and reproduces"
  echo "# P1-ID-REVIEW 2.3 exactly; the four new thunks follow."
  echo
  python "$S/w.py" 0x19dc650 62
  echo
  cat "$S/step5_thunks.txt"
} > "$E/04_invoke_thunks.txt"

# ---- step 4b: why each handler address is a function start ----
# The report claims four handlers are preceded by `udf #0` padding and two follow a cold
# assert block. Dump the words immediately before every handler so each claim is visible
# here, not only in the prologue scan.
{
  echo "# handler function-start evidence: the words immediately preceding each handler."
  echo "# Four are preceded by udf #0 padding; 0x19dcf40 and 0x19dcf60 follow the cold"
  echo "# assert blocks at 0x19dcf34/0x19dcf54, whose last call targets 0x39c20a0."
  echo
  echo "## backwards prologue scan (scratch/.../fstart.py)"
  for h in 0x19dcf20 0x19dcf40 0x19dcf60 0x19dd080 0x19dd1a0 0x19dd250; do
    echo "--- $h ---"
    python "$S/fstart.py" "$h" | head -4
  done
  echo
  echo "## the words at each handler address and the two before it"
  for h in 0x19dcf20 0x19dcf40 0x19dcf60 0x19dd080 0x19dd1a0 0x19dd250; do
    echo "--- 3 words ending at $h ---"
    python "$S/w.py" $(( h - 8 )) 3
  done
  echo
  echo "## 0x19dcf20 in full, with its assert tail and the 0x19dcf34 cold block"
  python "$S/w.py" 0x19dcf1c 18
  echo
  echo "## 0x19dcf40 with its assert tail"
  python "$S/w.py" 0x19dcf3c 8
} > "$E/05_function_start_candidates.txt"

echo "wrote:"
ls -l "$E"
