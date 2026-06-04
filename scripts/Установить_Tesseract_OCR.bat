@echo off
chcp 65001 > nul
setlocal

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

echo.
echo Установка Tesseract OCR для распознавания бумажных PDF-сканов.
echo Если Windows попросит подтверждение, разрешите установку.
echo.

where winget > nul 2> nul
if errorlevel 1 (
    echo winget не найден. Установите Tesseract вручную:
    echo https://github.com/UB-Mannheim/tesseract/wiki
    pause
    exit /b 1
)

winget install -e --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements

echo.
echo Скачиваю русские и английские языковые файлы OCR в локальную папку runtime\tessdata...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root = '%ROOT%'; $dir = Join-Path $root 'runtime\tessdata'; New-Item -ItemType Directory -Force -Path $dir | Out-Null; foreach ($lang in @('eng','rus','osd')) { $target = Join-Path $dir ($lang + '.traineddata'); if (!(Test-Path $target)) { Invoke-WebRequest -Uri ('https://github.com/tesseract-ocr/tessdata_fast/raw/main/' + $lang + '.traineddata') -OutFile $target } }"

echo.
echo После установки закройте это окно и снова запустите "Проверить_среду.bat".
echo В проверке должны появиться языки eng и rus.
pause
