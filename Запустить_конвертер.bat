@echo off
chcp 65001 > nul
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo Локальный конвертер PDF/DOCX в Markdown
echo Документы не отправляются в интернет.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Первая настройка. Создаю локальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo Не удалось создать окружение Python.
        pause
        exit /b 1
    )
)

if not exist ".venv\.ready" (
    echo Устанавливаю нужные компоненты. Это может занять несколько минут...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 (
        echo Не удалось обновить pip.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Не удалось установить компоненты из requirements.txt.
        pause
        exit /b 1
    )
    echo ready > ".venv\.ready"
)

".venv\Scripts\python.exe" markdown_converter.py --open-result %*

echo.
echo Работа завершена. Если выше указан путь к папке результата, откройте её.
pause
