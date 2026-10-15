# P1-LUA-WRITE - checked reserialization of the editor Lua chunks

Worker: Space Bunny Alpha, finished Lua worker's follow-up. Follow root AGENTS.md,
kb/INDEX.md, this mod's AGENTS.md and STATUS.md. Read tools/lua53-inspect/README.md,
research/P1-UI-DECODE.md and research/P1-UI-GLOBALS.md. Layout/native identity workers
are independent; don't edit their files. Stop further global-definition searches.

Goal: create the smallest reliable offline write path for the THREE already extracted
Lua editor chunks. No source decompiler, compiler installation or production UI change.

1. Extend the existing lua53-inspect tool with an encoder preserving header widths,
   floats, strings, nested prototypes, instructions, upvalues and debug sections.
   Work from official Lua 5.3 dump format already pinned by the tool; do not invent
   unknown sections or fix their values. Keep existing commands compatible.
2. For the base editor, patched editor and special selector chunks, parse -> encode
   must reproduce every byte and SHA256 exactly. Report actual comparisons; serializing
   the original raw blob unchanged is not an encoder verification.
3. On a DISPOSABLE test variant, change one existing display-name string or another
   nonexecuted test constant to a longer string (do not change bridge names, selectors,
   flags, loop bounds or native arguments). Reparse it and demonstrate only the intended
   constant changed semantically; all instructions and other prototype fields are equal.
   If no clearly suitable display literal exists, use a purely synthetic valid chunk
   for the length-changing mutation and leave all real chunks unmodified.
4. Check malformed/truncated input rejection still passes. Document supported fields,
   limits, commands and why reserialization is not proof the game loads modified scripts.

Exclusive writes under this mod: tools/lua53-inspect/, research/P1-LUA-WRITE.md,
evidence/P1-LUA-WRITE/ and scratch/2026-10-04_P1-LUA-WRITE/.
Game-derived/repacked chunks belong ONLY in workspace gamedata/mii_customizer/P1-LUA-WRITE/;
keep originals read-only, no game data in tools/source/evidence. No install candidate.
This prompt authorizes changes to this one tool; no concurrent worker owns it.

Use stdlib and existing tools only; no dependency/tool installation, other-project edits,
native RE, saves, SD, emulator, console, commits or shared status/schema edits.
Stop after three round trips and the mutation checks. If format preservation stalls after
two distinct fixes, return PARTIAL with exact field/offset and error; do not rewrite the
entire inspector. Correct P1-UI-GLOBALS overclaims only in your new report: absence of an
assignment does not prove a global is immutable or that an enum is necessarily host-owned.
End saved report/chat P1-LUA-WRITE: DONE/PARTIAL/BLOCKED, changed files, commands/results.
