# GitHub Release Draft: Reader v0.4.0

Use this text when creating the GitHub Release for tag `v0.4.0`.

## Title

Reader v0.4.0 - OSS-ready portable release

## Body

Reader v0.4.0 is the first OSS-ready portable release candidate.

### Highlights

- Local Windows PDF/DOCX to Markdown conversion.
- Portable `Reader_Portable.exe` for users who cannot install Python.
- Russian OCR through Tesseract language data.
- Page-level OCR decisions for mixed PDFs.
- Scan preprocessing and parallel OCR.
- Built-in DOCX extraction for text, tables, footnotes, and endnotes.
- Clean Markdown output without technical HTML metadata headers.
- OSS documentation, issue templates, release notes, tests, and CI workflow.

### Download

Download `Reader_Portable.exe` from the release assets below.

Optional verification: compare the downloaded file with `Reader_Portable.exe.sha256.txt`.

### First Run

1. Open `Reader_Portable.exe`.
2. Choose a folder with PDF/DOCX documents.
3. Wait until processing finishes.
4. Open `markdown_result_.../00_ALL_DOCUMENTS.md`.

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
