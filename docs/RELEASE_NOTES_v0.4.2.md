# Reader v0.4.2 Release Notes

Reader v0.4.2 adds practical processing reports for users who need to verify document conversion and OCR quality without reading console logs.

## Highlights

- Added `REPORT.txt` to every generated result folder.
- Added `OCR_REPORT.txt` with page-level OCR details for scanned and mixed PDFs.
- Reports summarize processed files, status, page counts, OCR pages, blank pages, warnings, and errors.
- OCR report marks pages that may need manual review because of low text volume or suspicious OCR quality.
- Added tests for report generation.
- Added manual GitHub Actions dispatch support through `workflow_dispatch`.

## Verified Locally

Checked on Windows before release:

- `python -m py_compile src/reader/markdown_converter.py`
- `python -m unittest discover -s tests`
- `Reader_Portable.exe --check`
- Real-folder conversion test with 10 PDF/DOCX documents:
  - 10 documents processed;
  - `00_ALL_DOCUMENTS.md` created;
  - `REPORT.txt` created;
  - `OCR_REPORT.txt` created;
  - no `02_problem_files` directory;
  - no technical metadata headers in Markdown output;
  - no replacement-character corruption detected.

## Known Limitations

- GitHub Actions still requires the account billing/actions lock to be resolved before public CI can run successfully.
- Old `.doc` files are not supported directly. Re-save them as `.docx` or PDF.
- OCR quality depends on scan contrast, rotation, stamps, handwriting, and page damage.
- For legally important text, OCR pages should still be checked against the original PDF.

## Release Checklist

- [x] Source code pushed to `main`.
- [x] Tests pass locally.
- [x] Portable exe rebuilt locally.
- [x] Exe excluded from Git source tree.
- [x] Release checksum generated.
- [ ] GitHub Actions green after account Actions access is fixed.
- [ ] GitHub Release created with `Reader_Portable.exe` asset.
