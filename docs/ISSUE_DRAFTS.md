# Issue Drafts

These are ready-to-copy GitHub issue drafts for the first public triage items.

## 1. Roadmap: Reader v0.5.0

Labels: `enhancement`, `documentation`

```markdown
Reader v0.5.0 should focus on reliability and user confidence after the first OSS-ready release.

Planned work:

- Add OCR quality report with page-level warnings.
- Add more tests for mixed PDFs and OCR edge cases.
- Improve Markdown formatting for tables and long legal documents.
- Add a clearer GUI progress window for non-technical users.
- Add more synthetic sample documents.

Privacy rule: use only anonymized or synthetic documents in public discussion.
```

## 2. OCR quality benchmark

Labels: `ocr-quality`, `testing`

```markdown
Define a small repeatable benchmark for Russian OCR and document conversion quality.

Benchmark cases:

- PDF with normal text layer.
- Fully scanned PDF.
- Mixed PDF with both text pages and scanned pages.
- Low-contrast scanned PDF.
- DOCX with tables, footnotes, and endnotes.

Expected output:

- Markdown created successfully.
- No technical HTML metadata headers.
- Page-level OCR decisions are reasonable.
- Problem files are created only when manual review is needed.

All samples must be anonymized or synthetic.
```

## 3. Release v0.4.0 checklist

Labels: `release`

```markdown
Track the first public Reader release.

Checklist:

- [ ] GitHub Actions is green.
- [ ] Tag `v0.4.0` is present.
- [ ] GitHub Release `v0.4.0` is created.
- [ ] `Reader_Portable.exe` is uploaded as a release asset.
- [ ] SHA256 checksum is attached or included in the release notes.
- [ ] Uploaded exe passes `Reader_Portable.exe --check` on Windows.
- [ ] README release link works.
- [ ] Known limitations are listed in the release notes.
```

## 4. Add page-level OCR quality report

Labels: `enhancement`, `ocr-quality`

```markdown
Reader already decides OCR per PDF page. Add a clearer page-level quality report so users know which pages need manual review.

Possible report fields:

- page number;
- source method: text layer or OCR;
- extracted character count;
- cyrillic ratio;
- blank-page detection result;
- warning flag for manual review.

The report should not expose private data beyond local output files and should remain optional or lightweight.
```
