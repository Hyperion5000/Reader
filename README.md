# Reader

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)](README.md)
[![Privacy](https://img.shields.io/badge/privacy-local%20processing-brightgreen.svg)](SECURITY.md)
[![OCR](https://img.shields.io/badge/OCR-rus%20%7C%20eng%20%7C%20osd-orange.svg)](README.md)

Локальный Windows-конвертер PDF/DOCX в Markdown с русским OCR.

**English summary:** Reader is a local Windows tool that converts PDF and DOCX documents to Markdown. It supports Russian OCR, scanned PDFs, mixed text/OCR PDFs, and Word documents without sending files to cloud services.

**Why it matters:** many document-heavy workflows still depend on scanned Russian-language PDFs and Word files. Reader gives non-technical Windows users a portable, private way to turn those documents into searchable Markdown without installing Python or uploading sensitive files to cloud OCR services.

## Зачем это нужно

Reader помогает быстро превратить папку юридических, деловых или архивных документов в Markdown:

- документы остаются на компьютере пользователя;
- обычные PDF читаются как текст;
- PDF-сканы распознаются через Tesseract OCR;
- смешанные PDF обрабатываются постранично;
- DOCX читаются встроенно, включая текст, таблицы и Word-сноски;
- готовый `Reader_Portable.exe` запускается без установки Python.

Проект особенно полезен для русскоязычной работы с документами на Windows: юристы, делопроизводство, бухгалтерия, архивы, подготовка материалов для анализа и поиска.

## Быстрый запуск

1. Скачайте `Reader_Portable.exe` из [GitHub Releases](https://github.com/Hyperion5000/Reader/releases).
2. Откройте `Reader_Portable.exe`.
3. Выберите папку с PDF/DOCX-документами.
4. Дождитесь завершения обработки.
5. Откройте созданную папку `markdown_result_...`.

Главный результат находится в `00_ALL_DOCUMENTS.md`.

## Что создаётся

- `00_ALL_DOCUMENTS.md` - один общий Markdown-файл со всеми документами.
- `01_markdown` - отдельные Markdown-файлы по каждому документу.
- `02_problem_files` - появляется только если какой-то файл требует ручной проверки.

Отдельные Markdown-файлы не содержат технических HTML-шапок вроде `source`, `processed_at` или `method`.

## Что обрабатывается

- PDF с обычным текстовым слоем.
- Отсканированные PDF.
- Смешанные PDF, где часть страниц с текстом, а часть является сканом.
- DOCX, включая текст, таблицы и сноски.

Старые Word-файлы `.doc` не обрабатываются. Их лучше пересохранить в `.docx` или PDF.

## Как работает OCR

В переносимой сборке используется Tesseract OCR с языками `rus`, `eng` и `osd`.

PDF обрабатываются постранично:

- если на странице нормальный текст, программа берет его напрямую;
- если страница похожа на скан, запускается OCR;
- если встроенный текстовый слой похож на нечитаемый набор символов, программа тоже запускает OCR;
- почти пустые страницы отсекаются, чтобы OCR не превращал шум в случайный текст;
- несколько OCR-страниц обрабатываются параллельно.

## Пример результата

Вход: папка с PDF/DOCX.

Выход:

```text
markdown_result_2026-06-04_18-54/
├─ 00_ALL_DOCUMENTS.md
└─ 01_markdown/
   ├─ договор.md
   ├─ претензия.md
   └─ экспертиза.md
```

Фрагмент Markdown:

```markdown
# Документ 1: претензия.pdf

- Тип: PDF-скан
- Метод: Постранично: текст+OCR
- Статус: успешно

## Страница 1

Текст документа...
```

Безопасные синтетические примеры результата лежат в [examples/sample_result](examples/sample_result). В них нет реальных документов или личных данных.

## Запуск из исходников

Обычному пользователю это не нужно. Используйте готовый `Reader_Portable.exe`.

Для разработки:

1. Установите Python 3.12.
2. Откройте `scripts/Запустить_конвертер.bat`.
3. При первом запуске будет создана локальная папка `runtime/.venv`.
4. Компоненты будут установлены из `config/requirements.txt`.

Проверка среды:

```powershell
scripts\Проверить_среду.bat
```

## Сборка portable exe

Сборка выполняется локально на Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_portable.ps1
```

Результат появится в:

```text
release/Reader_Portable.exe
```

Готовый exe не хранится в Git. Для публичного распространения используйте GitHub Releases.

## Структура проекта

- `src/reader/markdown_converter.py` - основной код.
- `config/requirements.txt` - зависимости для запуска из исходников.
- `config/build-requirements.txt` - зависимости для сборки exe.
- `scripts/` - запуск, проверка среды, установка OCR, сборка exe.
- `tests/` - минимальные автоматические тесты.
- `docs/` - дополнительные документы проекта.
- `examples/` - безопасные синтетические примеры результата.
- `.github/` - CI, issue templates, pull request template, Dependabot.
- `runtime/` - локальная техническая папка, не загружается в Git.

## Тесты

```powershell
python -m py_compile src/reader/markdown_converter.py
python -m unittest discover -s tests
```

CI запускает эти проверки автоматически.

## Приватность

Reader не отправляет документы в интернет. Исходные PDF/DOCX, результаты `markdown_result_...`, OCR-данные, `runtime/` и `.exe` файлы исключены из Git.

Не прикладывайте реальные личные документы к публичным issue. Используйте обезличенные или синтетические примеры.

## Сопровождение

- Лицензия: MIT.
- Лицензии сторонних компонентов: см. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- Вклад: см. [CONTRIBUTING.md](CONTRIBUTING.md).
- Безопасность: см. [SECURITY.md](SECURITY.md).
- Поддержка: см. [SUPPORT.md](SUPPORT.md).
- Правила общения: см. [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Процесс релиза: см. [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md).
- Планы развития: см. [ROADMAP.md](ROADMAP.md).
- Triage: см. [docs/TRIAGE_PLAN.md](docs/TRIAGE_PLAN.md).
- FAQ: см. [docs/FAQ.md](docs/FAQ.md).

## Актуальность инструментов

Проверено 06.06.2026:

- `docling==2.97.0`.
- `markitdown[pdf,docx]==0.1.6`.
- `pypdfium2==5.9.0`.
- `pillow==12.2.0`.
- `pyinstaller==6.20.0`.
- Tesseract OCR в переносимой сборке: 5.4.0 с русским OCR.

По официальному репозиторию Tesseract последняя версия движка - 5.5.2. В текущей portable-сборке оставлена проверенная Windows-сборка 5.4.0, потому что для exe важнее стабильность запуска на обычном ПК. Обновление до 5.5.x запланировано после отдельного теста качества и переносимости.

Проверенные альтернативы:

- PaddleOCR может быть сильнее на сложных OCR-задачах, но заметно тяжелее для переносимого `.exe`.
- OCRmyPDF полезен для добавления OCR-слоя в PDF, но не решает задачу прямой конвертации PDF/DOCX в Markdown.
- NAPS2 удобен как отдельная программа для сканирования, но не подходит как минимальная основа этого конвертера.
