# Changelog

All notable changes to Reader are documented here.

## Unreleased

- Added local OCR for large text-bearing images embedded in DOCX files.
- Added DOCX image OCR counts, confidence details, and warnings to `REPORT.txt` and `OCR_REPORT.txt`.
- A damaged DOCX image no longer cancels text extraction from the rest of the document.
- Fixed run status so any OCR element listed for manual review also marks its document as requiring review.
- Max mode now compares at least one complete set of preprocessing and page-layout variants before early stopping.
- Improved OCR result selection with a preference for stable paragraph order when candidate quality is otherwise close.
- Added an embedded DOCX image case to the synthetic benchmark.
- Added `--quality-mode max|standard`; `max` is now the default OCR mode for better scan quality.
- Added multi-attempt OCR in max mode with multiple DPI values, image preprocessing variants, and Tesseract PSM modes.
- Added Tesseract TSV confidence scoring and best-attempt selection for OCR pages.
- Fixed TSV confidence collection when Reader uses bundled local Tesseract language data.
- OCR pages without a measurable confidence value are now marked for manual review in max quality mode.
- Added a synthetic OCR benchmark for comparing `standard` and `max` quality modes.
- Expanded the benchmark with Russian OCR reporting, harder synthetic scans, and Tesseract override options.
- Added `--tesseract-path`, `--tessdata-dir`, and `--preserve-page-breaks` for advanced testing workflows.
- Added OCR language and speed settings through command-line options.
- Added a small Windows progress window for interactive folder-picker runs.
- Added a manual-review summary at the top of `OCR_REPORT.txt`.

## 0.4.3 - High-resolution scan handling

- Raised the local OCR image safety limit so normal high-resolution scanned pages no longer print Pillow decompression-bomb warnings during processing.

## 0.4.2 - Processing reports

- Added `REPORT.txt` with a short processing summary for each run.
- Added `OCR_REPORT.txt` with page-level OCR details for scanned and mixed PDFs.
- Added manual GitHub Actions dispatch support for easier CI rechecks after account Actions access is fixed.

## 0.4.0 - OSS readiness

- Added MIT license and open-source contributor documentation.
- Added GitHub issue templates and CI checks.
- Added pull request template, Dependabot config, support guide, code of conduct, and release process documentation.
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
