<#
Captures the Skyline log from the Switch over TCP straight into this workspace.

Based on the snippet that already works:

    while ($true) { try { $client = New-Object System.Net.Sockets.TcpClient($ip, $port)
        $reader = New-Object System.IO.StreamReader($client.GetStream())
        while ($line = $reader.ReadLine()) { Write-Output $line }; break
    } catch { Start-Sleep -Seconds 1 } }

Three deliberate differences:

 - It writes to a file. The MFLIP lines are a small fraction of a Skyline log, and a
   pasted excerpt is lossy: searching a file finds every attempt, including the ones
   where something is missing entirely (for example a leap with no CATCH ACMD line at
   all, which a hand-picked excerpt would not reveal).
 - It reconnects rather than breaking out when the stream ends. Restarting the game
   drops the socket, and what happens after a restart is usually the interesting part.
 - It appends each line immediately, so a crash or a Ctrl+C still leaves a full log.

Run it in its own terminal before starting the game, then play the move, then Ctrl+C.

    powershell -NoProfile -ExecutionPolicy Bypass -File scratch/capture_switch_log.ps1

Skyline uses more than one port; 6969 carries what the earlier logs contained. If a
kind of line is missing, run a second instance with -Port 6970 -Path logs\other.log.
#>
param(
    [string]$Ip = '10.241.230.26',
    [int]$Port = 6969,
    [string]$Path
)

if (-not $Path) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
    $Path = Join-Path $root "logs\switch-$stamp.log"
}
$dir = Split-Path -Parent $Path
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
if (-not (Test-Path $Path)) { Set-Content -Path $Path -Value '' }

[System.IO.File]::AppendAllText($Path, "# capture opened $(Get-Date -Format s) target ${Ip}:${Port}$([Environment]::NewLine)")
Write-Host "capturing ${Ip}:${Port} into $Path"
Write-Host 'play the move, then press Ctrl+C here'

while ($true) {
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect($Ip, $Port)
        $client.NoDelay = $true
        $reader = New-Object System.IO.StreamReader($client.GetStream())
        [System.IO.File]::AppendAllText($Path, "# connected $(Get-Date -Format s)$([Environment]::NewLine)")
        Write-Host "connected $(Get-Date -Format HH:mm:ss)"

        while ($true) {
            $line = $reader.ReadLine()
            if ($null -eq $line) { break }
            [System.IO.File]::AppendAllText($Path, $line + [Environment]::NewLine)
            Write-Host $line
        }
        Write-Host "stream ended $(Get-Date -Format HH:mm:ss) - reconnecting"
    } catch {
        # Nothing listening yet, or the game restarted. Retry quietly.
    } finally {
        if ($client) { $client.Close() }
    }
    Start-Sleep -Seconds 1
}
