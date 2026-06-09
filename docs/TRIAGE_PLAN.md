# Triage Plan

Reader is a young project, so issue triage is intentionally simple.

## Current Focus

1. Make the first public GitHub Release with `Reader_Portable.exe`.
2. Keep CI green after GitHub Actions access is fixed.
3. Collect OCR quality reports using anonymized or synthetic samples.
4. Improve page-level OCR diagnostics for difficult Russian scans.
5. Add more repeatable tests for mixed PDFs and DOCX edge cases.

## Issue Labels To Use

- `bug` - broken behavior.
- `ocr-quality` - OCR accuracy, page detection, scan preprocessing.
- `documentation` - README, FAQ, examples, release notes.
- `release` - release checklist and packaging.
- `privacy` - handling of private documents or sensitive data.
- `enhancement` - new feature requests.

## First Issues To Open

### Roadmap: Reader v0.5.0

Track improvements after the first OSS-ready release:

- OCR quality report with page-level warnings.
- More tests for mixed PDFs.
- Clearer progress window for non-technical users.
- More synthetic sample documents.

### OCR quality benchmark

Define a small anonymized benchmark for Russian scanned documents:

- text layer PDF;
- scanned PDF;
- mixed PDF;
- low-contrast PDF;
- DOCX with tables and footnotes.

### Release v0.4.1 checklist

Track the first public release:

- GitHub Actions green;
- tag pushed;
- `Reader_Portable.exe` uploaded to GitHub Releases;
- README release link verified;
- download test on a clean Windows machine.

