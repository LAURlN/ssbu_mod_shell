$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$modFilesRoot = $PSScriptRoot
$sdPluginDir = Join-Path $workspaceRoot 'mod_output/atmosphere/contents/01006A800016E000/romfs/skyline/plugins'
$previousTarget = $env:CARGO_TARGET_DIR

Push-Location $PSScriptRoot
try {
    $env:CARGO_TARGET_DIR = Join-Path $modFilesRoot 'target'
    $oldEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & cargo skyline build --release --features swap-diagnostics -- --offline *> (Join-Path $modFilesRoot 'build-diagnostic.log')
    $buildExit = $LASTEXITCODE
    $ErrorActionPreference = $oldEAP
    if ($buildExit -ne 0) { throw "Build failed; see $modFilesRoot/build-diagnostic.log" }
    $artifact = Join-Path $env:CARGO_TARGET_DIR 'aarch64-skyline-switch/release/libmythra_gamewatch_swap.nro'
    if (!(Test-Path -LiteralPath $artifact)) { throw "Missing NRO: $artifact" }
    
    New-Item -ItemType Directory -Force $sdPluginDir | Out-Null
    Copy-Item -LiteralPath $artifact -Destination (Join-Path $sdPluginDir 'libmythra_gamewatch_swap.nro') -Force
    Get-FileHash -LiteralPath (Join-Path $sdPluginDir 'libmythra_gamewatch_swap.nro') -Algorithm SHA256
} finally {
    Pop-Location
    $env:CARGO_TARGET_DIR = $previousTarget
}

