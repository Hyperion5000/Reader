@echo off
chcp 65001 > nul
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" markdown_converter.py --check
) else (
    python markdown_converter.py --check
)

echo.
pause
