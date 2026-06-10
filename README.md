# Reader

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)](README.md)
[![Privacy](https://img.shields.io/badge/privacy-local%20processing-brightgreen.svg)](SECURITY.md)
[![OCR](https://img.shields.io/badge/OCR-rus%20%7C%20eng%20%7C%20osd-orange.svg)](README.md)

Local Windows PDF/DOCX to Markdown converter with Russian OCR.

Reader converts folders of PDF and DOCX documents into clean Markdown. It supports scanned PDFs, mixed text/OCR PDFs, Russian OCR, Word tables, Word footnotes, and portable Windows usage without requiring users to install Python.

## Why It Matters

Many document-heavy workflows still depend on scanned Russian-language PDFs and Word files. Reader gives non-technical Windows users a portable, private way to turn those documents into searchable Markdown without uploading sensitive files to cloud OCR services.

Reader is useful for:

- legal and administrative document review;
- document-heavy private practice workflows;
- archive cleanup and search preparation;
- converting scanned Russian PDFs into reusable text;
- preparing local Markdown files for further private analysis.

## Quick Start

1. Download `Reader_Portable.exe` from [GitHub Releases](https://github.com/Hyperion5000/Reader/releases).
2. Open `Reader_Portable.exe`.
3. Choose a folder with PDF/DOCX documents.
4. Wait until processing finishes.
5. Open the generated `markdown_result_...` folder.

The main output file is `00_ALL_DOCUMENTS.md`.

## Output Structure

- `00_ALL_DOCUMENTS.md` - one combined Markdown file with all processed documents.
- `REPORT.txt` - short processing summary: files, status, OCR pages, warnings, and errors.
- `OCR_REPORT.txt` - page-level PDF OCR report for scanned and mixed PDFs.
- `01_markdown` - separate Markdown files for each document.
- `02_problem_files` - created only when a file needs manual review.

Generated Markdown files do not contain technical HTML metadata headers such as `source`, `processed_at`, or `method`.

## Supported Inputs

- PDFs with a normal text layer.
- Fully scanned PDFs.
- Mixed PDFs where some pages contain text and other pages are scans.
- DOCX files with text, tables, footnotes, and endnotes.

Old `.doc` files are not supported directly. Re-save them as `.docx` or PDF first.

## OCR Behavior

The portable build uses Tesseract OCR with `rus`, `eng`, and `osd` language data.

PDFs are processed page by page:

- pages with a good text layer are read directly;
- scanned pages are sent to OCR;
- broken PDF text layers are detected and sent to OCR;
- nearly blank pages are filtered before OCR;
- multiple OCR pages are processed in parallel.

## Example Result

Input: a folder with PDF/DOCX documents.

Output:

```text
markdown_result_2026-06-04_18-54/
├─ 00_ALL_DOCUMENTS.md
├─ REPORT.txt
├─ OCR_REPORT.txt
└─ 01_markdown/
   ├─ contract.md
   ├─ notice.md
   └─ report.md
```

Example Markdown fragment:

```markdown
# Document 1: scanned_notice.pdf

- Type: PDF scan
- Method: Page-by-page text+OCR
- Status: success

## Page 1

Extracted document text...
```

Safe synthetic examples are available in [examples/sample_result](examples/sample_result). They do not contain real private documents or personal data.

## Run From Source

Most users should use `Reader_Portable.exe`. Source usage is intended for development.

Development setup:

1. Install Python 3.12 on Windows.
2. Create a virtual environment or use the existing helper scripts in `scripts/`.
3. Dependencies are installed from `config/requirements.txt`.

Environment check:

```powershell
python src\reader\markdown_converter.py --check
```

## Build Portable EXE

Build on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_portable.ps1
```

Output:

```text
release/Reader_Portable.exe
```

The portable exe is not stored in Git. Public binaries should be published through GitHub Releases.

## Project Structure

- `src/reader/markdown_converter.py` - main application code.
- `config/requirements.txt` - source runtime dependencies.
- `config/build-requirements.txt` - portable exe build dependencies.
- `scripts/` - launch, environment check, OCR setup, build, and release checksum scripts.
- `tests/` - automated tests.
- `docs/` - project documentation.
- `examples/` - safe synthetic output examples.
- `.github/` - CI, issue templates, pull request template, and Dependabot.
- `runtime/` - local technical folder, excluded from Git.

## Tests

```powershell
python -m py_compile src/reader/markdown_converter.py
python -m unittest discover -s tests
```

CI runs these checks automatically when GitHub Actions is available.

## Privacy

Reader does not upload documents to the internet. Source PDFs/DOCX files, generated `markdown_result_...` folders, OCR data, `runtime/`, and `.exe` files are excluded from Git.

Do not attach real private documents to public GitHub issues. Use anonymized or synthetic examples.

## Maintenance

- License: MIT.
- Third-party notices: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).
- Security: [SECURITY.md](SECURITY.md).
- Support: [SUPPORT.md](SUPPORT.md).
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Release process: [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md).
- Roadmap: [ROADMAP.md](ROADMAP.md).
- Triage: [docs/TRIAGE_PLAN.md](docs/TRIAGE_PLAN.md).
- Issue drafts: [docs/ISSUE_DRAFTS.md](docs/ISSUE_DRAFTS.md).
- AI-assisted maintenance: [docs/AI_ASSISTED_MAINTENANCE.md](docs/AI_ASSISTED_MAINTENANCE.md).
- FAQ: [docs/FAQ.md](docs/FAQ.md).

## Tooling Status

Checked on 2026-06-09:

- `docling==2.97.0`.
- `markitdown[pdf,docx]==0.1.6`.
- `pypdfium2==5.9.0`.
- `pillow==12.2.0`.
- `pyinstaller==6.20.0`.
- Portable Tesseract OCR bundle: 5.4.0 with Russian OCR data.

The latest official Tesseract line is newer than the bundled Windows build. Reader keeps the verified portable Windows bundle for now because reliable startup on ordinary PCs is more important than changing OCR engines without a separate quality test. Migration to a newer Tesseract 5.5.x build is tracked in the roadmap.

Checked alternatives:

- PaddleOCR may be stronger for some difficult OCR cases, but it is much heavier for a portable Windows exe.
- OCRmyPDF is useful for adding an OCR layer to PDFs, but it does not solve direct PDF/DOCX to Markdown conversion.
- NAPS2 is useful as a separate scanning application, but not as the minimal base for this converter.
