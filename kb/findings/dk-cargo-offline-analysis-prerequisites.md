---
title: DK cargo offline analysis uses task-local libraries and a prebuilt-path extraction fix
summary: A task-local Windows path sanitizer and explicit GNU build recover prebuilt NROs without changing the shared extractor.
status: verified
updated: 2026-10-02
tags: [extraction, windows, python, toolchain]
source: dk_cargo offline preparation, 2026-10-02
---

Verified 2026-10-02: the registered workspace ARC extractor reads the NRO path
`prebuilt:/nro/release/lua2cpp_donkey.nro`, but its output sanitizer handles only
`stream:/`; Windows output fails with error 123. The DK task's `extract.py`
builds an isolated copy with `:/` converted to `;/`, leaving the shared tool
unchanged. Explicit GNU toolchain is necessary when launching Cargo from the
workspace root: the initial default MSVC invocation failed with
`linker link.exe not found`; GNU offline release build passed.

Base Python lacked capstone. The analysis-only task cache contains capstone
5.0.9 and ssbh_data_py 0.9.1 installed through pip `--target`, with no system-wide
install. The sandbox network attempt failed with WinError 10013; a permitted
retry used cached wheels successfully. Reproduction:
`mods/ssbu_mod_new/src/pgwr/tools/dk_cargo/README.md`.

Game/mod findings are recorded only in the mod repo:
`mods/ssbu_mod_new/evidence/2026-10-02_pgwr_dk_cargo/RESULT.md`.
