# Contributing

Thank you for considering a contribution to Reader.

Reader is a local Windows-focused PDF/DOCX to Markdown converter. The project values privacy, simple operation, and predictable output for non-technical users.

## Good first contributions

- Improve OCR quality on difficult Russian scans.
- Improve DOCX extraction while preserving privacy.
- Add tests for edge cases.
- Improve documentation and examples.
- Report files that produce bad Markdown, using anonymized samples when possible.

## Development setup

1. Install Python 3.12 on Windows.
2. Open PowerShell in the repository root.
3. Create a local virtual environment, or use the helper scripts in `scripts/`.
4. Run checks:

```powershell
python -m py_compile src/reader/markdown_converter.py
python -m unittest discover -s tests
```

## Pull request expectations

- Keep user-facing behavior simple.
- Do not upload private documents, generated Markdown results, `runtime/`, or `.exe` files.
- Add or update tests for behavior changes.
- Update README or docs when public behavior changes.

## Privacy rule

Do not include real legal, medical, financial, or personal documents in issues or pull requests. Use anonymized or synthetic samples.
