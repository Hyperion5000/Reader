# OCR Benchmark

The `benchmarks/` folder contains a local, synthetic benchmark for Reader OCR quality.

The benchmark creates safe temporary PDF/DOCX files, runs Reader in both OCR quality modes, and writes a local report comparing:

- key phrases found in the generated Markdown;
- synthetic Russian OCR pass/fail status;
- OCR page count;
- manual-review page count;
- OCR of a text-bearing image embedded in DOCX;
- extracted character count;
- average OCR confidence when available;
- processing time.

Run on Windows from the repository root:

```powershell
runtime\.venv\Scripts\python.exe benchmarks\run_ocr_benchmark.py
```

The output is written to a local `benchmark_result_...` folder. Benchmark result folders are ignored by Git.

To compare another Tesseract build:

```powershell
runtime\.venv\Scripts\python.exe benchmarks\run_ocr_benchmark.py --label tesseract-5.5 --tesseract-path "C:\Path\to\tesseract.exe" --tessdata-dir "C:\Path\to\tessdata"
```

The benchmark uses only synthetic control phrases. The Russian OCR section is reported separately so weak local `rus.traineddata` can be diagnosed without hiding the rest of the pipeline result.
