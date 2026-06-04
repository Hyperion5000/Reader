@echo off
chcp 65001 > nul
setlocal

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

set "APP=src\reader\markdown_converter.py"
set "VENV=runtime\.venv"

if exist "%VENV%\Scripts\python.exe" (
    "%VENV%\Scripts\python.exe" "%APP%" --check
) else (
    python "%APP%" --check
)

echo.
pause
