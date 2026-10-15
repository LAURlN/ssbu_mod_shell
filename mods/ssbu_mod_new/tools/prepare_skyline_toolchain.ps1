<#
Prepares the skyline-v3 toolchain without downloading gigabytes of submodules.

What cargo-skyline's update-std actually does (read from
cargo-skyline 3.5.0, src/update_std.rs):

  1. finds the base nightly from the skyline rust-src fork's last bors commit date
  2. copies that nightly into %CARGO_HOME%\skyline\toolchain\skyline
  3. wipes lib/rustlib/src and runs
        git clone --recurse-submodules --shallow-submodules --depth 1 --branch skyline
  4. runs `rustup toolchain link skyline-v3 <toolchain>`

and that is all. It does NOT build the standard library: `cargo skyline build`
compiles it itself with -Z build-std=core,alloc,std,panic_abort, and
check_std_installed() only checks that the linked `skyline-v3` toolchain exists.

The expensive part is step 3's submodules. -Z build-std reads
lib/rustlib/src/rust/library and nothing else, so the LLVM and gcc submodules are
dead weight - well over a gigabyte of it. This script does step 3 without
--recurse-submodules and then performs step 4.

Usage:
    powershell -NoProfile -ExecutionPolicy Bypass -File scratch/prepare_skyline_toolchain.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File scratch/prepare_skyline_toolchain.ps1 -Status

-Status only reports, so it can be polled cheaply while the clone runs.
#>
param(
    [switch]$Status,
    [string]$Branch = 'skyline',
    [string]$Repo = 'https://github.com/skyline-rs/rust-src'
)

$cargoHome = if ($env:CARGO_HOME) { $env:CARGO_HOME } else { Join-Path $HOME '.cargo' }
$toolchain = Join-Path $cargoHome 'skyline\toolchain\skyline'
$srcRoot = Join-Path $toolchain 'lib\rustlib\src\rust'
$library = Join-Path $srcRoot 'library'
$linkPath = Join-Path $HOME '.rustup\toolchains\skyline-v3'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $here 'skyline-clone.log'
$logErr = Join-Path $here 'skyline-clone.err.log'

$cargoBin = Join-Path $cargoHome 'bin'
$env:PATH = $cargoBin + [IO.Path]::PathSeparator + $env:PATH

function Show-Status {
    $clone = Get-Process git -ErrorAction SilentlyContinue
    $size = if (Test-Path $srcRoot) {
        [math]::Round(((Get-ChildItem $srcRoot -Recurse -File -ErrorAction SilentlyContinue |
            Measure-Object Length -Sum).Sum / 1MB), 1)
    } else { 0 }
    Write-Output "clone running : $([bool]$clone)"
    Write-Output "src size MB   : $size"
    Write-Output "library/ here : $(Test-Path $library)"
    Write-Output "skyline-v3    : $(Test-Path $linkPath)"
    if (Test-Path $log) {
        Write-Output 'last log lines:'
        Get-Content $log -Tail 6 -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "  $_" }
    }
}

if ($Status) { Show-Status; exit 0 }

if (-not (Test-Path $toolchain)) {
    Write-Output "toolchain copy missing at $toolchain - run 'cargo skyline update-std' once to create it,"
    Write-Output 'or let it get as far as copying the nightly, then stop it.'
    exit 1
}

Write-Output 'stopping any in-flight clone...'
Stop-Process -Name cargo-skyline -Force -ErrorAction SilentlyContinue
Stop-Process -Name git -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

if (Test-Path $srcRoot) {
    Write-Output 'removing the partial clone...'
    Remove-Item $srcRoot -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path (Split-Path -Parent $srcRoot) -Force | Out-Null

$git = (Get-Command git.exe -ErrorAction SilentlyContinue).Source
if (-not $git) { Write-Output 'git not found on PATH'; exit 1 }
Write-Output "cloning $Repo branch $Branch without submodules..."

Start-Process -FilePath $git `
    -ArgumentList 'clone', '--depth', '1', '--branch', $Branch, '--single-branch', $Repo, $srcRoot `
    -NoNewWindow -RedirectStandardOutput $log -RedirectStandardError $logErr

Start-Sleep -Seconds 20
Show-Status
