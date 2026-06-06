# Reader v0.4.0 Release Notes

Reader v0.4.0 is the first OSS-ready release candidate.

## Highlights

- Portable Windows build target: `Reader_Portable.exe`.
- Local PDF/DOCX to Markdown conversion without cloud document upload.
- Russian OCR through bundled Tesseract language data.
- Page-level OCR decisions for mixed PDFs.
- Scan preprocessing before OCR.
- Parallel OCR for multi-page scanned PDFs.
- Built-in DOCX extraction for text, tables, footnotes, and endnotes.
- Clean Markdown output without technical HTML metadata headers.
- OSS documentation: license, changelog, contribution guide, security policy, roadmap, FAQ, and third-party notices.
- GitHub issue templates and CI workflow.
- Minimal automated tests for core conversion rules.

## Verified Locally

Checked on Windows before release:

- `python -m py_compile src/reader/markdown_converter.py`
- `python -m unittest discover -s tests`
- `Reader_Portable.exe --check`
- Real-folder conversion test with 10 PDF/DOCX documents:
  - 10 documents processed;
  - `00_ALL_DOCUMENTS.md` created;
  - no `02_problem_files` directory;
  - no technical metadata headers in Markdown output.

## Known Limitations

- GitHub Actions may need account billing/actions access to be enabled before the public CI badge turns green.
- Old `.doc` files are not supported directly. Re-save them as `.docx` or PDF.
- OCR quality still depends on scan contrast, rotation, stamps, handwriting, and page damage.
- The portable build currently uses a verified Windows Tesseract 5.4.0 bundle; migration to Tesseract 5.5.x is planned after separate quality testing.

## Release Checklist

- [x] Source code pushed to `main`.
- [x] Tests pass locally.
- [x] Portable exe rebuilt locally.
- [x] Exe excluded from Git source tree.
- [ ] GitHub Actions green after account Actions access is fixed.
- [ ] GitHub Release created with `Reader_Portable.exe` asset.
