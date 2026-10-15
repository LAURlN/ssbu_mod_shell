$ErrorActionPreference = 'Stop'
$previousTarget = $env:CARGO_TARGET_DIR
$previousPath = $env:PATH
Push-Location $PSScriptRoot
try {
    # Skyline uses a Windows GNU host toolchain. Its build dependencies need
    # MinGW's dlltool/linker even though the final target is the Switch.
    $mingw = $env:MSYS2_MINGW_BIN
    if ($mingw -and (Test-Path -LiteralPath (Join-Path $mingw 'dlltool.exe'))) {
        $env:PATH = $mingw + [IO.Path]::PathSeparator + $env:PATH
    }
    $env:CARGO_TARGET_DIR = Join-Path $PSScriptRoot 'target'
    $ErrorActionPreference = 'Continue'
    & cargo skyline build --release -- --offline *> (Join-Path $PSScriptRoot 'build-probe.log')
    $buildExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($buildExit -ne 0) { throw "Build failed; see build-probe.log" }
    Get-FileHash -LiteralPath (Join-Path $env:CARGO_TARGET_DIR 'aarch64-skyline-switch/release/libmgw_clone_probe.nro') -Algorithm SHA256
} finally {
    Pop-Location
    $env:CARGO_TARGET_DIR = $previousTarget
    $env:PATH = $previousPath
}
