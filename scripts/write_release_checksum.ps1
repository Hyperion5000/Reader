param(
    [string]$ExePath = "release\Reader_Portable.exe"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ResolvedExe = Join-Path $Root $ExePath

if (!(Test-Path -LiteralPath $ResolvedExe)) {
    throw "Release exe not found: $ResolvedExe"
}

$hash = Get-FileHash -LiteralPath $ResolvedExe -Algorithm SHA256
$outputPath = "$ResolvedExe.sha256.txt"
$fileName = Split-Path $ResolvedExe -Leaf

"SHA256 $fileName" | Set-Content -LiteralPath $outputPath -Encoding UTF8
$hash.Hash.ToLowerInvariant() | Add-Content -LiteralPath $outputPath -Encoding UTF8

Write-Host "Wrote $outputPath"
Write-Host $hash.Hash.ToLowerInvariant()
