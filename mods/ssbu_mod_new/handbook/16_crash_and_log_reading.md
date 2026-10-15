# Reading crash reports and logs

Tier legend: `AGENTS.md` rule 8. Worked examples live in `../evidence/`.

## Atmosphere crash report (`sd:/atmosphere/crash_reports/<id>_<title>.log`)
1. Note `Type` (Data Abort = bad memory access; Instruction Abort / Undefined Instruction = ran into data, e.g. `d4200020`; User Break = deliberate assert/`nnosBreak`), `Thread`, `Address`/`Fault Address`.
2. Frames show `module + offset`. For the game: `cross2_Release.nss + off` = offset into `dumps/exefs/13.0.4/main.bin` (VA == file offset for `.text`). Disassemble there (Capstone, `toolchains/python_tools`) and read the instructions before guessing a cause.
3. Fault address small (0x18, 0x20, 0x11c) = null pointer + field offset; the register holding the base is 0. Find who was supposed to set it.
4. Stack overflow looks like a fault at `stp x29,x30,[sp,#..]` with SP below the stack region floor and `Fault Address: 0x0` as a red herring; check for many identical return addresses.
5. A smashline frame on the stack is often just the hook wrapper around the original; read the frames above it.
6. A report older than the build (timestamps!) is not evidence about the build.
7. Data Abort at the *patch site* itself: plain stores into `.text` are not allowed; use `skyline::patching::Patch`.

## Skyline log (TCP stream) and file logs
- The TCP log loses its tail when the game kills the thread; write crash-adjacent lines to `sd:/ultimate/<name>_log.txt` (open/append/close per line). Ask for logs **from boot** (a head-truncated log removed the startup markers once).
- Log prefixes: `[PGWR]` `[PGWR-ART]` `[PGWR-HI3]` (reskin), `[MGW-SL]` `[MGW-CLONE]` `[MGW-MFLIP]` `[MGW-HI3]` `[MGW-SLOTS]` (older), `[copymodel]` `[motionbind]` `[articlescope]` (clone engine).
- Startup markers prove which build is installed: `[MGW-SL] p7: verified …`, `[PGWR-ART]/[PGWR] ARTICLE registered …`, plugin banner with version. A `REFUSED` marker = version/byte guard declined, hooks not installed (a failed gate, not a success).
- Silence is not a reading: a value printed only on change says nothing when it never changes; log the consequence (`is_catch`, victim status), not just setup.
- When the thing being measured can *crash the console at the moment it happens*, the lines leading into it have to be on the card before it happens. The one accepted exception to "never print per frame" is such a window: Monkey Flip's capture prints one line per frame inside the leap's box frames and every cling phase, capped at 90 lines per entry (`VICTIM`, plus a 12-line `VICTIMSTATUS` on victim status changes). Bounded and windows-scoped, not general per-frame printing.
- Log parsers must assert their own capture-group counts and have a fixture (`tools/summarise_mflip_log.py` + `fixture_mflip_i.log`).
- ARCropolis lines: `Cannot get file info range for 'Unknown' (0x…)` with pointers outside the healthy `0x31..-0x36..` range = a DirInfo that was never created (bad config.json). `File discovery collected path '.../config.json' but it does not exist` = benign.
- `Result code: 514` (0x202) creating a file on the SD: exclusive create is not supported; use non-exclusive open + length check.


## User-requested silent pgwr release — 2026-10-03

Verified B: 0.20.23 gates mod-owned log/console call expressions behind the existing `logging` feature, so disabled builds discard argument evaluation as well as output. Independent Hero mana/side-B, Snake, DK and Incineroar crash-tail writers are unreachable in this build. The user explicitly requested removing all logging; that instruction supersedes rule 25's file-output requirement for this release. Native safety checks/HUD logic remain active. Six mod log-file paths are absent from the built NRO; framework plugins are unchanged. Evidence: `../evidence/2026-10-03_pgwr_0.20.23_silent/BUILD.md`.

Unverified D: improvement in console frame pacing; judge by playing the same match/setup. This build emits no mod diagnostic pass/fail markers and supplies no new pgwr boot log. Identify it by NRO hash; use stock Atmosphere crash reports if the console crashes. Existing old log files are not deleted. At preparation time the SD card was disconnected; the subsequent user-requested 0.20.23 installation is verified in `../evidence/2026-10-03_pgwr_0.20.23_silent/INSTALL.md`.
