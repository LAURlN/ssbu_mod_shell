@echo off
rem Shell-agnostic plugin build.
rem
rem Why this exists: the task runner has handed this project both
rem powershell.exe and cmd.exe. Under powershell.exe, cargo's stderr output is
rem wrapped as a NativeCommandError (a RemoteException), the exit code reported
rem back is 255, and the run reads as a build failure even though cargo itself
rem printed "Finished". The first attempt at build 2026-09-17.e went exactly that
rem way: cargo printed "Finished `release` profile [optimized] target(s) in
rem 3.25s", the reported exit code was 255, and
rem target\aarch64-skyline-switch\release\libmythra_gamewatch_swap.nro was left as
rem the previous build -- which deploy.py then copied, so the deploy printed the
rem .d hash 4de85a47... for what was supposed to be the .e binary. The NRO
rem packaging in cargo-skyline runs after cargo's own "Finished" line, so a
rem masked failure there is invisible in the cargo log.
rem
rem Running through a batch file removes the shell from the equation: the output
rem is plain text in build_e.log and %ERRORLEVEL% is cargo's real exit code.
rem The mingw binutils must come first: rustup's bundled dlltool cannot build
rem import libraries (rust-mingw ships no as.exe), and getrandom/windows-sys need
rem dlltool even though the plugin itself targets aarch64.
rem
rem Usage:  cmd /c tools\build_plugin.cmd
setlocal
set "PATH=%MSYS2_MINGW_BIN%;%USERPROFILE%\.cargo\bin;%PATH%"
set "ROOT=%~dp0.."
if not exist "%ROOT%\builds\.cache" mkdir "%ROOT%\builds\.cache"
cd /d "%ROOT%\src\mgw_swap"
cargo skyline build --release --features swap-diagnostics > "%ROOT%\builds\.cache\mgw_swap_build.log" 2>&1
echo EXIT=%ERRORLEVEL%
endlocal
