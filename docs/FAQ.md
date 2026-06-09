# FAQ

## Does Reader upload documents to the internet?

No. Reader processes PDF/DOCX files locally on the user's Windows computer.

## Do users need to install Python?

No for the portable build. `Reader_Portable.exe` is intended for users who cannot or do not want to install Python. Python is needed only for development from source.

## Where can I get `Reader_Portable.exe`?

Portable builds should be published through GitHub Releases:

https://github.com/Hyperion5000/Reader/releases

The exe is not stored in the Git repository because it is a large build artifact.

## Why Tesseract instead of PaddleOCR?

Tesseract is lighter for a portable Windows build and works well for local OCR without cloud services. PaddleOCR may be stronger for some difficult documents, but it is heavier and less suitable for a minimal portable exe.

## What should I do with old `.doc` files?

Re-save them as `.docx` or PDF. The old `.doc` format is not supported directly.

## Why do some OCR results require manual review?

OCR quality depends on scan quality. Rotation, noise, stamps, handwriting, and poor contrast can reduce accuracy. Reader can mark suspicious files in `02_problem_files`.

## Can Reader be used for legally important documents?

Yes, as a text extraction tool. For legally important text, OCR results should always be checked against the original PDF.
