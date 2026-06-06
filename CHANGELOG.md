# Changelog

All notable changes to Reader are documented here.

## 0.4.0 - OSS readiness

- Added MIT license and open-source contributor documentation.
- Added GitHub issue templates and CI checks.
- Added a portable Windows build script for `Reader_Portable.exe`.
- Added synthetic examples, release notes, and triage plan for the first OSS release.
- Added minimal tests for DOCX extraction, OCR page decisions, output metadata, and skipped technical folders.
- Replaced direct PyMuPDF usage with PDFium-based PDF handling for cleaner OSS licensing.

## 0.3.0 - Project structure

- Moved source code to `src/reader`.
- Moved helper scripts to `scripts`.
- Moved dependency pins to `config`.
- Moved local runtime data to ignored `runtime`.

## 0.2.0 - Robust document conversion

- Added built-in DOCX text/table extraction.
- Added per-page OCR for mixed PDFs.
- Added detection of broken PDF text layers.
- Added blank-page filtering before OCR.

## 0.1.0 - Initial local converter

- Added local PDF/DOCX to Markdown conversion for Windows.
- Added Tesseract OCR support for Russian and English scans.
