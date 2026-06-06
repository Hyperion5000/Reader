param(
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Venv = Join-Path $Root "runtime\.venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$App = Join-Path $Root "src\reader\markdown_converter.py"
$Requirements = Join-Path $Root "config\requirements.txt"
$BuildRequirements = Join-Path $Root "config\build-requirements.txt"
$Tessdata = Join-Path $Root "runtime\tessdata"
$ReleaseDir = Join-Path $Root "release"
$OutputExe = Join-Path $ReleaseDir "Reader_Portable.exe"
$TesseractExe = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$TesseractDir = Split-Path $TesseractExe -Parent

Set-Location $Root

if (!(Test-Path $Python)) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "runtime") | Out-Null
    python -m venv $Venv
}

if (!$SkipDependencyInstall) {
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r $Requirements
    & $Python -m pip install -r $BuildRequirements
}

if (!(Test-Path $TesseractExe)) {
    throw "Tesseract was not found at $TesseractExe. Install it or update scripts/build_portable.ps1."
}

if (!(Test-Path $Tessdata)) {
    throw "OCR language data was not found at $Tessdata. Run the Tesseract installer helper script first."
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

Remove-Item -LiteralPath (Join-Path $Root "build") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $Root "dist") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $Root "Reader_Portable.spec") -Force -ErrorAction SilentlyContinue

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name Reader_Portable `
    --add-binary "$TesseractExe;." `
    --add-binary "$TesseractDir\*.dll;." `
    --add-data "$Tessdata;tessdata" `
    $App

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Move-Item -LiteralPath (Join-Path $Root "dist\Reader_Portable.exe") -Destination $OutputExe -Force

Remove-Item -LiteralPath (Join-Path $Root "build") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $Root "dist") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $Root "Reader_Portable.spec") -Force -ErrorAction SilentlyContinue

Write-Host "Built $OutputExe"
