# Offline setup only. Never opens game containers, keys or emulator configuration.
[CmdletBinding()]
param(
    [string]$BackendPath = 'Ryujinx/build/LibHac.dll',
    [string]$CachePath = 'tools/data-arc-extract/.cache',
    [string]$BuildPath = 'tools/data-arc-extract/.cache/build',
    [string]$DotnetPath = 'dotnet',
    [switch]$Build
)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$pin = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'backend.lock.json') -Raw | ConvertFrom-Json
function WorkspacePath([string]$value) {
    if (($value -split '[/\\]') -contains '..') { throw 'Traversal components are unsupported.' }
    foreach ($component in ($value -split '[/\\]')) {
        if ($component -ne '.' -and ($component.EndsWith('.') -or $component.EndsWith(' '))) { throw 'Trailing-dot/space path aliases are unsupported.' }
    }
    if (![IO.Path]::IsPathRooted($value)) { $value = Join-Path $workspace $value }
    $full = [IO.Path]::GetFullPath($value)
    if ($full.Substring([IO.Path]::GetPathRoot($full).Length).Contains(':')) { throw 'Alternate data streams are unsupported.' }
    if (!$full.StartsWith($workspace + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path must be strictly inside workspace: $full"
    }
    # Reject existing junctions/symlinks, including ancestors of not-yet-created paths.
    $cursor = $full
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse-point path is unsupported: $cursor" }
        }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
    return $full
}
function WritablePath([string]$value) {
    $full = WorkspacePath $value
    # Keep all generated files in the ignored state tree or this tool's ignored cache.
    $allowed = @((Join-Path $workspace 'state'), (Join-Path $PSScriptRoot '.cache'))
    foreach ($root in $allowed) {
        if ($full.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or $full -eq $root) { return $full }
    }
    throw 'Cache/build destinations must be under state/ or tools/data-arc-extract/.cache/.'
}
$backend = WorkspacePath $BackendPath
$cache = WritablePath $CachePath
$buildDir = WritablePath $BuildPath
foreach ($generatedRoot in @($cache, $buildDir)) {
    if ($backend -eq $generatedRoot -or $backend.StartsWith($generatedRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Backend input overlaps generated cache/build destination.' }
}
if (!(Test-Path -LiteralPath $backend -PathType Leaf)) { throw 'Missing backend. Supply -BackendPath to the pinned LibHac 0.19.0 DLL inside this workspace; see README recovery.' }
if ((Get-FileHash -LiteralPath $backend -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pin.sha256) { throw 'Incompatible backend SHA-256. Do not substitute a Ryujinx.LibHac fork or edit the pin; see README recovery.' }
$version = [Reflection.AssemblyName]::GetAssemblyName($backend).Version.ToString()
if ($version -ne $pin.assemblyVersion) { throw "Incompatible backend assembly version: $version" }
$hostPath = if ($DotnetPath -eq 'dotnet') { 'dotnet' } else { WorkspacePath $DotnetPath }
$dotnet = Get-Command $hostPath -CommandType Application -ErrorAction SilentlyContinue
if (!$dotnet) { throw 'Missing dotnet SDK. Use -DotnetPath pointing to a workspace-local .NET SDK 8.0.201 dotnet.exe; see README.' }
$names = @('DOTNET_CLI_HOME','DOTNET_SKIP_FIRST_TIME_EXPERIENCE','DOTNET_CLI_TELEMETRY_OPTOUT','DOTNET_NOLOGO','DOTNET_MULTILEVEL_LOOKUP','DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE','NUGET_PACKAGES','NUGET_HTTP_CACHE_PATH','NUGET_PLUGINS_CACHE_PATH','NUGET_SCRATCH','TEMP','TMP','MSBuildEnableWorkloadResolver')
$saved = @{}
foreach ($name in $names) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
    foreach ($leaf in @('cli','packages','http','plugins','scratch','temp')) { $destination = WritablePath (Join-Path $cache $leaf); New-Item -ItemType Directory -Force -Path $destination | Out-Null }
    foreach ($leaf in @('obj','bin')) { $null = WritablePath (Join-Path $buildDir $leaf) }
    New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
    $values = @{
        DOTNET_CLI_HOME = (Join-Path $cache 'cli'); DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'; DOTNET_CLI_TELEMETRY_OPTOUT = '1'; DOTNET_NOLOGO = '1'; DOTNET_MULTILEVEL_LOOKUP = '0'; DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE = '1';
        NUGET_PACKAGES = (Join-Path $cache 'packages'); NUGET_HTTP_CACHE_PATH = (Join-Path $cache 'http'); NUGET_PLUGINS_CACHE_PATH = (Join-Path $cache 'plugins'); NUGET_SCRATCH = (Join-Path $cache 'scratch'); TEMP = (Join-Path $cache 'temp'); TMP = (Join-Path $cache 'temp'); MSBuildEnableWorkloadResolver = 'false'
    }
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $values[$name], 'Process') }
    Push-Location $PSScriptRoot
    try {
        $sdk = & $dotnet.Source --version
        if ($LASTEXITCODE -ne 0 -or "$sdk".Trim() -ne $pin.sdk) { throw 'SDK 8.0.201 is required by global.json. Supply a compatible -DotnetPath; no automatic SDK installation is performed.' }
        $runtimes = & $dotnet.Source --list-runtimes
        if ($LASTEXITCODE -ne 0 -or !($runtimes -match '^Microsoft.NETCore.App 8\.0\.')) { throw 'Missing Microsoft.NETCore.App 8.0 runtime. Use a complete workspace-local .NET 8 SDK distribution.' }
        $project = Join-Path $PSScriptRoot 'DataArcExtract.csproj'
        $properties = @("-p:LibHacPath=$backend", "-p:BaseIntermediateOutputPath=$buildDir/obj/", "-p:OutputPath=$buildDir/bin/", '-p:RestoreIgnoreFailedSources=false')
        & $dotnet.Source restore $project --configfile (Join-Path $PSScriptRoot 'NuGet.Config') --packages (Join-Path $cache 'packages') @properties
        if ($LASTEXITCODE -ne 0) { throw 'Offline restore failed. Check installed net8.0 reference packs and README recovery; no network fallback is enabled.' }
        if ($Build) {
            & $dotnet.Source build $project --no-restore --configuration Release @properties
            if ($LASTEXITCODE -ne 0) { throw 'Build failed; inspect compiler diagnostics. Do not treat this as extraction success.' }
        }
        Write-Output "Prepared LibHac $($pin.version), SHA-256 $($pin.sha256). Build requested: $Build. Outputs: $buildDir"
    } finally { Pop-Location }
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
}
