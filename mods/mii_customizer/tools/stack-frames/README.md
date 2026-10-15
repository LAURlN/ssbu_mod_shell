# stack-frames

Purpose: find oversized stack frames in a plugin NRO before it goes on the card. The plugin's
`main` runs on a 64 KiB Skyline thread stack; a 324 KiB frame crashed the boot on 2026-10-07
(`evidence/2026-10-07_session4/RESULT_boot1.md`).

Usage (from the mod folder): `python tools/stack-frames/stack_frames.py <file.nro> [--limit BYTES] [--top N]`.
Exit 0 when every frame is within the limit (default 24 KiB), 1 otherwise.

Smoke check: `builds/0.6.0-menu/libmii_customizer.nro` -> largest 19584, exit 0;
`builds/0.7.0-menu/libmii_customizer.nro` -> largest 283552, exit 1.

Status: working. It reads `sub sp, sp, #imm` instructions only (adjacent ones are added); it
does not follow call chains, so nested frames still have to fit together, and it would not
see a frame allocated with a register operand.
