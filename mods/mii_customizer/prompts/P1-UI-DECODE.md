# P1-UI-DECODE - decode the existing editor Lua chunks

Follow workspace AGENTS.md, kb/INDEX.md, mods/mii_customizer/AGENTS.md and STATUS.md.
Read your completed research/P1-UI.md and research/COORDINATOR-2026-10-04.md.
You are the finished UI worker's follow-up. P1-ID is still working: do not trace native
identifiers, saves or editor-to-battle bindings. No production UI modifications.

One goal: replace printable-string guesses with bounded Lua 5.3 chunk/instruction evidence
for the three already-extracted .lc files (base editor, patched editor, special editor).

1. Inspect the actual chunk header/endianness and correct the parser against official Lua
   5.3 source (lundump.c, lopcodes.h); cite exact version/URL. This is Lua 5.3, not LuaU.
   Existing scratch code's variable-integer/string assumptions must not be trusted.
2. Produce recursive prototype/constant/instruction dumps with exact byte offsets and
   full-file-consumption checks. Do not build a full source decompiler. Decode only the
   opcodes needed for counts, table fields, branches and calls of interest; unsupported
   interpretation stays unknown rather than becoming fabricated Lua source.
3. Locate SKILL_COMMAND_NUM, SPECIAL_SKILL_NUM, get_skill_id/set_skill_id and
   IS_SKILL_EDITABLE references. Show relevant instructions and distinguish constants,
   global/table reads and calls. Numeric counts are resolved only with actual definitions.
4. Compare base and patched editor at prototype/instruction level; summarize the actual
   observed differences, not just string differences. Recommend one minimal next UI task.

Write only research/P1-UI-DECODE.md, evidence/P1-UI-DECODE/,
scratch/2026-10-04_P1-UI-DECODE/ and tools/lua53-inspect/ under this mod.
Reuse extracted inputs read-only. Promote the useful parser to tools/lua53-inspect/ with
README, docstring and meaningful checks: truncated input rejection, header checks,
instruction/constant bounds where supported, recursive parsing and complete consumption
on all three chunks. No new runtime dependencies or tool installation.

If parsing stalls after two distinct corrective attempts, stop PARTIAL with exact offset,
bytes, error and hypotheses; no endless parser rewrite or full native RE. Don't edit P1-ID
outputs, other workers, shared STATUS/contracts, old mod, saves or framework plugins.
No emulator, console, SD access or commits. Paths relative to workspace/mod; no game upload.
End saved report and chat P1-UI-DECODE: DONE/PARTIAL/BLOCKED, changed files, observed
checks and unresolved boundaries. A decoded instruction is not runtime/native-target proof.
