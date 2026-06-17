from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

import run_ocr_benchmark as benchmark


class OcrBenchmarkTests(unittest.TestCase):
    def test_phrase_present_handles_case_spacing_and_punctuation(self) -> None:
        text = "Reader, should extract\ntext accurately from this page."

        self.assertTrue(benchmark.phrase_present(text, "reader should extract text accurately"))

    def test_parse_report_metrics_extracts_summary_values(self) -> None:
        report = "\n".join(
            [
                "- страниц OCR: 3",
                "- страниц с замечаниями OCR: 1",
                "- символов извлечено: 1280",
                "- средняя уверенность OCR: 96.4",
            ]
        )

        metrics = benchmark.parse_report_metrics(report)

        self.assertEqual(metrics["ocr_pages"], 3)
        self.assertEqual(metrics["review_pages"], 1)
        self.assertEqual(metrics["extracted_chars"], 1280)
        self.assertEqual(metrics["average_confidence"], 96.4)

    def test_russian_phrase_evaluation_reports_missing_phrases(self) -> None:
        total, found, missing = benchmark.evaluate_russian_phrases("Проверка русского текста")

        self.assertGreaterEqual(total, 1)
        self.assertGreaterEqual(found, 1)
        self.assertIn("качество распознавания", missing)

    def test_build_markdown_report_includes_standard_and_max_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_root = Path(temp_dir)
            results = [
                benchmark.ModeResult(
                    label="current",
                    mode="standard",
                    command=["python", "converter.py"],
                    source_dir=str(result_root / "standard"),
                    result_dir=str(result_root / "standard" / "markdown_result"),
                    return_code=0,
                    duration_seconds=1.25,
                    phrase_total=3,
                    phrase_found=3,
                    missing_phrases=[],
                    russian_phrase_total=2,
                    russian_phrase_found=1,
                    missing_russian_phrases=["качество распознавания"],
                    russian_passed=False,
                    extracted_chars=1000,
                    ocr_pages=2,
                    review_pages=0,
                    average_confidence=None,
                    passed=True,
                ),
                benchmark.ModeResult(
                    label="current",
                    mode="max",
                    command=["python", "converter.py"],
                    source_dir=str(result_root / "max"),
                    result_dir=str(result_root / "max" / "markdown_result"),
                    return_code=0,
                    duration_seconds=2.5,
                    phrase_total=3,
                    phrase_found=3,
                    missing_phrases=[],
                    russian_phrase_total=2,
                    russian_phrase_found=2,
                    missing_russian_phrases=[],
                    russian_passed=True,
                    extracted_chars=1000,
                    ocr_pages=2,
                    review_pages=0,
                    average_confidence=96.4,
                    passed=True,
                ),
            ]

            lines = benchmark.build_markdown_report(
                results,
                result_root,
                dt.datetime(2026, 6, 17, 10, 0, 0),
                dt.datetime(2026, 6, 17, 10, 0, 3),
            )

        report = "\n".join(lines)
        self.assertIn("Overall: **PASS**", report)
        self.assertIn("Russian OCR: **PASS**", report)
        self.assertIn("| current | standard | PASS | 3/3 | 1/2 |", report)
        self.assertIn("| current | max | PASS | 3/3 | 2/2 |", report)
        self.assertIn("96.4", report)

    def test_run_mode_command_includes_tesseract_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tesseract_path = root / "tesseract.exe"
            tessdata_dir = root / "tessdata"
            tesseract_path.write_text("", encoding="utf-8")
            tessdata_dir.mkdir()

            result = benchmark.ModeResult(
                label="candidate",
                mode="max",
                command=[
                    "python",
                    "converter.py",
                    "--tesseract-path",
                    str(tesseract_path),
                    "--tessdata-dir",
                    str(tessdata_dir),
                ],
                source_dir=str(root),
                result_dir=str(root),
                return_code=0,
                duration_seconds=1.0,
                phrase_total=1,
                phrase_found=1,
                missing_phrases=[],
                russian_phrase_total=1,
                russian_phrase_found=0,
                missing_russian_phrases=["текст"],
                russian_passed=False,
                extracted_chars=100,
                ocr_pages=1,
                review_pages=0,
                average_confidence=90.0,
                passed=True,
            )

            report = "\n".join(
                benchmark.build_markdown_report(
                    [result],
                    root,
                    dt.datetime(2026, 6, 17, 10, 0, 0),
                    dt.datetime(2026, 6, 17, 10, 0, 1),
                )
            )

        self.assertIn("--tesseract-path", report)
        self.assertIn("--tessdata-dir", report)


if __name__ == "__main__":
    unittest.main()
