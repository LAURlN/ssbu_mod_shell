$ErrorActionPreference = 'Stop'
$previousTarget = $env:CARGO_TARGET_DIR
$previousPath = $env:PATH
Push-Location (Join-Path $PSScriptRoot 'smashline_1304')
try {
    $env:CARGO_TARGET_DIR = Join-Path $PSScriptRoot 'target-smashline'
    if ($env:MSYS2_MINGW_BIN) { $env:PATH = $env:MSYS2_MINGW_BIN + [IO.Path]::PathSeparator + $env:PATH }
    $ErrorActionPreference = 'Continue'
    & cargo skyline build --release -- --offline *> (Join-Path $PSScriptRoot 'build-smashline.log')
    $buildExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($buildExit -ne 0) { throw 'Build failed; see build-smashline.log' }
    Get-FileHash -LiteralPath (Join-Path $env:CARGO_TARGET_DIR 'aarch64-skyline-switch/release/libsmashline_plugin.nro') -Algorithm SHA256
} finally {
    Pop-Location
    $env:CARGO_TARGET_DIR = $previousTarget
    $env:PATH = $previousPath
}
