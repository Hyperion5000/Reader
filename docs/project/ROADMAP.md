# Roadmap

Reader is a young project. The near-term roadmap focuses on reliability before feature expansion.

## Recently completed

- Added a small Windows progress window for interactive runs.
- Added settings for OCR language and processing speed.
- Added a manual-review summary to `OCR_REPORT.txt`.
- Added a max-quality OCR mode with confidence scoring and multiple OCR attempts.
- Added a repeatable synthetic OCR benchmark to compare `standard` and `max` quality modes.
- Added synthetic Russian OCR reporting, harder OCR benchmark cases, and Tesseract override options for benchmark comparisons.
- Added an optional page-break preservation mode for Markdown output.
- Added OCR for large text-bearing images embedded in DOCX files.
- Made file-level review status consistent with page/image warnings in OCR reports.
- Added a real-document release check covering scans, mixed PDFs, tables, and image-heavy DOCX files.
- Published the clearly versioned `Reader v0.5.0` GitHub Release with the portable EXE and SHA256 file.
- Added a release checklist and versioned release tags.

## Near term

- Use the benchmark to test migration from bundled Tesseract 5.4.0 to 5.5.x for Windows portable builds.
- Improve Markdown formatting for more complex nested tables and long legal documents.
- Add anonymized sample documents for repeatable demos.
- Add more real-world anonymized OCR edge cases after the synthetic benchmark is stable.

## Medium term

- Evaluate PaddleOCR or another heavy local OCR engine after the benchmark exists.
- Add optional layout-aware OCR improvements for difficult scans.
- Add a fuller GUI for selecting OCR settings without command-line options.
- Evaluate optional local-only post-processing for Markdown cleanup without changing document meaning.

## Not planned for now

- Uploading documents to cloud OCR services.
- Requiring users to install Python.
- Supporting old `.doc` files directly.
