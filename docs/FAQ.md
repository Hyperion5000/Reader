# FAQ

## Does Reader upload documents to the internet?

No. Reader processes PDF/DOCX files locally on the user's Windows computer.

## How is Reader different from online AI PDF converters?

Online AI converters can be convenient for non-private files and may restore document structure well, but they usually require uploading the PDF to a web service. Reader's main purpose is different: it keeps the source documents and extracted text on the user's Windows computer.

Reader can still improve formatting and OCR quality over time, but privacy-first local processing remains the default.

## Do users need to install Python?

No for the portable build. `Reader_Portable.exe` is intended for users who cannot or do not want to install Python. Python is needed only for development from source.

## Where can I get `Reader_Portable.exe`?

Portable builds should be published through GitHub Releases:

https://github.com/Hyperion5000/Reader/releases

The exe is not stored in the Git repository because it is a large build artifact.

## Why Tesseract instead of PaddleOCR?

Tesseract is lighter for a portable Windows build and works well for local OCR without cloud services. PaddleOCR may be stronger for some difficult documents, but it is heavier and less suitable for a minimal portable exe.

## Can I change OCR language or speed?

Yes. Advanced users can pass command-line options:

```powershell
Reader_Portable.exe "C:\Documents" --quality-mode max --ocr-languages rus+eng --ocr-workers 2
```

Use fewer OCR workers on weaker computers, or more workers when the computer has enough CPU power. Reader keeps a built-in safe upper limit.

For quality testing, Reader also supports `--preserve-page-breaks`, `--tesseract-path`, and `--tessdata-dir`. Most users do not need these options.

## Why can OCR take longer now?

Reader's default `max` quality mode prioritizes better recognition over speed. For scanned pages it can try multiple image cleanup variants, DPI values, and Tesseract page segmentation modes, then choose the best result by confidence score.

For faster processing, use:

```powershell
Reader_Portable.exe "C:\Documents" --quality-mode standard
```

## What should I do with old `.doc` files?

Re-save them as `.docx` or PDF. The old `.doc` format is not supported directly.

## Why do some OCR results require manual review?

OCR quality depends on scan quality. Rotation, noise, stamps, handwriting, and poor contrast can reduce accuracy. Reader can mark suspicious files in `02_problem_files`.

In `max` quality mode, `OCR_REPORT.txt` also marks OCR pages for manual review when confidence is low or when Tesseract cannot return a measurable confidence value.

## How do I compare OCR quality?

Use the local benchmark:

```powershell
runtime\.venv\Scripts\python.exe benchmarks\run_ocr_benchmark.py
```

It creates only synthetic test documents and reports `standard` versus `max`, including a separate Russian OCR pass/fail indicator.

## Can Reader be used for legally important documents?

Yes, as a text extraction tool. For legally important text, OCR results should always be checked against the original PDF.
