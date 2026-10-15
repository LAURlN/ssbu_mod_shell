# P2-SKILL-NATIVE - locate the native handlers behind the special-selector bridge names

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Keep game-derived files in your assigned
workspace-relative gamedata/mii_customizer/<task>/ folder, never source/evidence.
Report exact inputs/hashes, commands, observed checks, failures and limits. B is
offline observation, C pinned source, D hypothesis; no runtime behavior claims.
Coordinator owns STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report
and chat with task ID, DONE/PARTIAL/BLOCKED, changed files and next experiment.
Paths below are mod-relative unless marked workspace-relative.

One goal: for six bridge names, find WHERE each is registered in the executable and
WHICH function address is its handler. This is a locating task. Reading what the
handlers do is a later, separate task; do not attempt it here.

Names, exactly: get_skill_id, set_skill_id, replace_skill, replace_skill_subwindow,
get_skill_name_label, get_skill_help_label.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (rehash first; stop
BLOCKED on mismatch). Flat image, address == file offset. Pointer slots in .data are
zero in the file and filled by R_AARCH64_RELATIVE relocations; read the relocation
table when you need a pointer value, do not assume the file qword.

Read research/P1-ID-REVIEW.md section 2.3 first. It shows the one registration that
is already verified, for "post_fighter": a 0x28-byte delegate
{+0x00 vtable, +0x08 0, +0x10 owner object, +0x18 handler function, +0x20 adjust}
is built and registered under the name string through a call to 0x3376540, and the
delegate vtable's third slot is the invoke thunk that converts Lua arguments. Use
that as the pattern to look for, and re-verify it at each site instead of assuming
it. The names above take different argument counts (one, two or three Lua values,
see research/P2-UI-FLOW.md rows 12, 15, 19, 23, 30), so the delegate vtable and
thunk may differ per name. Report what is there.

You may copy scratch/2026-10-04_P1-ID-REVIEW/d.py into your own scratch folder and
extend the copy. It needs capstone, importable read-only with
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python (workspace-relative).
Do not edit the original script. Use `python`, not `python3`.

Steps, in order. Stop when all six names are done or a step fails for a name.
1. Find every byte occurrence of each name as a NUL-terminated string in the image.
   Report offset and count, including zero. A name that is a prefix of another
   (replace_skill / replace_skill_subwindow) must be matched with its terminator.
2. For each string address, find the adrp+add completions that reference it.
3. At each reference site, dump a window of at most 60 instructions before and 30
   after. From the window report: the allocation size, each store into the new
   object with its offset and value, the value's origin (immediate, adrp target or
   register with its provenance inside the window), and the call that receives the
   name. Mark any store whose value you cannot trace inside the window as
   "provenance not established". Do not fill it in by analogy with post_fighter.
4. For each handler address you find: report the candidate function start, and the
   first 40 instructions as a raw window. No commentary on what the function does
   beyond naming direct `bl` targets and any adrp-resolved string or global address
   that appears in those 40 instructions.
5. For each distinct delegate vtable: its three relocated slot values.
6. State whether all six registrations sit in one enclosing function, and that
   function's start address. Report the other names registered in the same function
   as a plain list (name, handler address) without analysing them.

Rules that matter here. Every claim needs the instruction addresses that show it.
A register value counts only if its definition is inside the window you dumped; if
it is not, say so. Do not match bare immediates across the binary, do not follow
more than the six names, do not interpret struct fields, do not guess what a
handler persists, and do not connect anything to saved-fighter records. An honest
"found the string, could not establish the handler" is a valid PARTIAL result.

Deliver research/P2-SKILL-NATIVE.md with one table: name, string address(es),
reference site, enclosing function, delegate size, vtable, thunk, handler address,
owner-object origin, confidence note. Put all raw windows in evidence, not in the
report. End with the smallest next question for a reader of the handlers.

Exclusive writes: research/P2-SKILL-NATIVE.md, evidence/P2-SKILL-NATIVE/,
scratch/2026-10-04_P2-SKILL-NATIVE/.
