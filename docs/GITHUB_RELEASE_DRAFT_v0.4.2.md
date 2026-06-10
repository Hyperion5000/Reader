# GitHub Release Draft: Reader v0.4.2

Use this text when creating the GitHub Release for tag `v0.4.2`.

## Title

Reader v0.4.2 - Processing reports and page-level OCR audit

## Body

Reader v0.4.2 adds practical run reports for local document conversion and OCR quality review.

### Highlights

- Local Windows PDF/DOCX to Markdown conversion.
- Portable `Reader_Portable.exe` for users who cannot install Python.
- Russian/Cyrillic and English OCR through bundled Tesseract language data.
- New `REPORT.txt` summary for every processing run.
- New `OCR_REPORT.txt` with page-level OCR decisions for scanned and mixed PDFs.
- Page-level warnings for low text volume, blank pages, and suspicious OCR quality.
- Clean Markdown output without technical HTML metadata headers.
- Tests updated for report generation.
- Manual GitHub Actions dispatch added for CI rechecks.

### Download

Download `Reader_Portable.exe` from the release assets below.

Optional verification: compare the downloaded file with `Reader_Portable.exe.sha256.txt`.

SHA256:

```text
db6a172dd37c80be4a358c194ceed92d83f231b02bd4cb3e0d47e2695a789618
```

### First Run

1. Open `Reader_Portable.exe`.
2. Choose a folder with PDF/DOCX documents.
3. Wait until processing finishes.
4. Open the generated `markdown_result_...` folder.
5. Start with `00_ALL_DOCUMENTS.md`, then check `REPORT.txt` and `OCR_REPORT.txt` if needed.

### Local Verification

This release was checked locally on Windows:

- `python -m py_compile src/reader/markdown_converter.py`
- `python -m unittest discover -s tests`
- `Reader_Portable.exe --check`
- 10-document smoke test with PDF/DOCX files

### Known Limitations

- Old `.doc` files are not supported directly.
- OCR quality depends on scan quality and should be reviewed for legally important documents.
- GitHub Actions may require account Actions/billing access before public CI is green.

### Privacy

Reader processes documents locally. Do not attach private documents to public GitHub issues.
