$ErrorActionPreference = 'Stop'
$previousTarget = $env:CARGO_TARGET_DIR
$previousPath = $env:PATH
Push-Location (Join-Path $PSScriptRoot 'vendor/ssbu_clone_engine')
try {
    $mingw = $env:MSYS2_MINGW_BIN
    if ($mingw -and (Test-Path -LiteralPath (Join-Path $mingw 'dlltool.exe'))) {
        $env:PATH = $mingw + [IO.Path]::PathSeparator + $env:PATH
    }
    $env:CARGO_TARGET_DIR = Join-Path $PSScriptRoot 'target-engine'
    $ErrorActionPreference = 'Continue'
    & cargo skyline build --release -- --offline *> (Join-Path $PSScriptRoot 'build-engine.log')
    $buildExit = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($buildExit -ne 0) { throw "Build failed; see build-engine.log" }
    Get-FileHash -LiteralPath (Join-Path $env:CARGO_TARGET_DIR 'aarch64-skyline-switch/release/libssbu_clone_engine.nro') -Algorithm SHA256
} finally {
    Pop-Location
    $env:CARGO_TARGET_DIR = $previousTarget
    $env:PATH = $previousPath
}
