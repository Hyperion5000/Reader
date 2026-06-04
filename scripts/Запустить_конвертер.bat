@echo off
chcp 65001 > nul
setlocal

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

set "APP=src\reader\markdown_converter.py"
set "REQ=config\requirements.txt"
set "VENV=runtime\.venv"

echo.
echo Локальный конвертер PDF/DOCX в Markdown
echo Документы не отправляются в интернет.
echo.

if not exist "%VENV%\Scripts\python.exe" (
    echo Первая настройка. Создаю локальное окружение...
    if not exist "runtime" mkdir "runtime"
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo Не удалось создать окружение Python.
        pause
        exit /b 1
    )
)

if not exist "%VENV%\.ready" (
    echo Устанавливаю нужные компоненты. Это может занять несколько минут...
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 (
        echo Не удалось обновить pip.
        pause
        exit /b 1
    )
    "%VENV%\Scripts\python.exe" -m pip install -r "%REQ%"
    if errorlevel 1 (
        echo Не удалось установить компоненты из %REQ%.
        pause
        exit /b 1
    )
    echo ready > "%VENV%\.ready"
)

"%VENV%\Scripts\python.exe" "%APP%" --open-result %*

echo.
echo Работа завершена. Если выше указан путь к папке результата, откройте её.
pause
