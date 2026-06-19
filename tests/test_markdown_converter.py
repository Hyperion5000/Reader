from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "reader"))

import markdown_converter as converter


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def w_tag(name: str) -> str:
    return f"w:{name}"


def make_docx(path: Path) -> None:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p><w:r><w:t>Исковое заявление</w:t></w:r></w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Колонка</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Значение</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Цена</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>100</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:p><w:r><w:t>Ссылка</w:t></w:r><w:r><w:footnoteReference w:id="2"/></w:r></w:p>
  </w:body>
</w:document>"""
    footnotes_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="{WORD_NS}">
  <w:footnote w:id="-1"><w:p /></w:footnote>
  <w:footnote w:id="2"><w:p><w:r><w:t>Текст сноски</w:t></w:r></w:p></w:footnote>
</w:footnotes>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/footnotes.xml", footnotes_xml)


def make_docx_with_image(path: Path) -> None:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{WORD_NS}"
  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p><w:r><w:t>Основной текст</w:t></w:r></w:p>
    <w:p><w:r><w:drawing><a:blip r:embed="rId1"/></w:drawing></w:r></w:p>
  </w:body>
</w:document>"""
    relationships_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
    Target="media/image1.png"/>
    </Relationships>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", relationships_xml)
        archive.writestr("word/media/image1.png", b"synthetic-test-image")


class ReaderConversionTests(unittest.TestCase):
    def test_docx_direct_extracts_text_tables_and_footnotes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "sample.docx"
            make_docx(docx_path)

            text = converter.convert_docx_direct(docx_path)

        self.assertIn("Исковое заявление", text)
        self.assertIn("| Колонка | Значение |", text)
        self.assertIn("Ссылка[2]", text)
        self.assertIn("## Сноски", text)
        self.assertIn("[2] Текст сноски", text)

    def test_docx_direct_adds_ocr_text_from_embedded_images(self) -> None:
        original_ocr = converter.run_ocr_attempts_for_page
        original_candidate_check = converter.is_docx_ocr_candidate_image

        def fake_ocr(*_args, **_kwargs):
            attempt = converter.OcrAttemptResult(
                text="Распознанный текст из изображения документа",
                confidence=96.0,
                psm=6,
                dpi=0,
                variant="gray",
                score=300.0,
            )
            return attempt.text, attempt, 3

        try:
            converter.run_ocr_attempts_for_page = fake_ocr
            converter.is_docx_ocr_candidate_image = lambda _path: True
            with tempfile.TemporaryDirectory() as temp_dir:
                docx_path = Path(temp_dir) / "images.docx"
                make_docx_with_image(docx_path)
                converted = converter.convert_docx_direct(
                    docx_path,
                    {"path": "tesseract.exe", "tessdata_dir": None},
                    converter.ConversionSettings(max_ocr_workers=1),
                )
        finally:
            converter.run_ocr_attempts_for_page = original_ocr
            converter.is_docx_ocr_candidate_image = original_candidate_check

        text, page_report = converted
        self.assertIn("## Текст из изображений DOCX", text)
        self.assertIn("Распознанный текст из изображения документа", text)
        self.assertEqual(len(page_report), 1)
        self.assertEqual(page_report[0].source, "docx-image")

    def test_docx_image_ocr_failure_keeps_regular_document_text(self) -> None:
        original_ocr = converter.run_ocr_attempts_for_page
        original_candidate_check = converter.is_docx_ocr_candidate_image

        def failing_ocr(*_args, **_kwargs):
            raise RuntimeError("broken embedded image")

        try:
            converter.run_ocr_attempts_for_page = failing_ocr
            converter.is_docx_ocr_candidate_image = lambda _path: True
            with tempfile.TemporaryDirectory() as temp_dir:
                docx_path = Path(temp_dir) / "images.docx"
                make_docx_with_image(docx_path)
                converted = converter.convert_docx_direct(
                    docx_path,
                    {"path": "tesseract.exe", "tessdata_dir": None},
                    converter.ConversionSettings(max_ocr_workers=1),
                )
        finally:
            converter.run_ocr_attempts_for_page = original_ocr
            converter.is_docx_ocr_candidate_image = original_candidate_check

        text, page_report = converted
        self.assertIn("Основной текст", text)
        self.assertEqual(page_report, [])

    def test_process_document_marks_ocr_warnings_for_review(self) -> None:
        original_convert_file = converter.convert_file
        try:
            converter.convert_file = lambda *_args, **_kwargs: (
                "Достаточно длинный основной текст документа. " * 30,
                "test",
                [converter.PageOcrEntry(1, "docx-image", 20, warning="Мало текста.")],
            )
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                source = root / "sample.docx"
                source.write_text("placeholder", encoding="utf-8")
                clean_dir = root / "out"
                problem_dir = root / "problems"
                clean_dir.mkdir()
                result = converter.process_document(
                    source,
                    "sample.md",
                    clean_dir,
                    problem_dir,
                    {"path": None, "languages": []},
                )
                problem_exists = (problem_dir / "sample.md").exists()
        finally:
            converter.convert_file = original_convert_file

        self.assertEqual(result.status, "требует проверки")
        self.assertIn("элементы OCR", result.warning)
        self.assertTrue(problem_exists)

    def test_find_documents_skips_runtime_build_dist_and_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "markdown_result_new"
            for folder in ["runtime", "build", "dist", "markdown_result_old", "benchmark_result_old", "docs"]:
                (root / folder).mkdir()
            (root / "runtime" / "hidden.pdf").write_text("x", encoding="utf-8")
            (root / "build" / "hidden.pdf").write_text("x", encoding="utf-8")
            (root / "dist" / "hidden.pdf").write_text("x", encoding="utf-8")
            (root / "markdown_result_old" / "hidden.pdf").write_text("x", encoding="utf-8")
            (root / "benchmark_result_old" / "hidden.pdf").write_text("x", encoding="utf-8")
            (root / "docs" / "visible.pdf").write_text("x", encoding="utf-8")
            (root / "visible.docx").write_text("x", encoding="utf-8")

            found = converter.find_documents(root, result_dir)

        names = {path.name for path in found}
        self.assertEqual(names, {"visible.docx", "visible.pdf"})

    def test_process_document_writes_no_metadata_header(self) -> None:
        original_convert_file = converter.convert_file
        try:
            converter.convert_file = lambda *_args, **_kwargs: ("Основной текст", "test", [])
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                source = root / "sample.docx"
                source.write_text("placeholder", encoding="utf-8")
                clean_dir = root / "out"
                problem_dir = root / "problems"
                clean_dir.mkdir()

                converter.process_document(source, "sample.md", clean_dir, problem_dir, {"path": None, "languages": []})
                text = (clean_dir / "sample.md").read_text(encoding="utf-8")
        finally:
            converter.convert_file = original_convert_file

        self.assertFalse(text.lstrip().startswith("<!--"))
        self.assertNotIn("source:", text)
        self.assertNotIn("processed_at:", text)
        self.assertNotIn("document_type:", text)
        self.assertIn("Основной текст", text)

    def test_pdf_page_ocr_decision(self) -> None:
        self.assertTrue(converter.should_ocr_pdf_page_text(""))
        self.assertFalse(converter.should_ocr_pdf_page_text("Это нормальный русский текст документа " * 5))
        bad_layer = "\n".join(["z", "q", "x", "F", "E", "a", "o", "N"] * 20)
        self.assertTrue(converter.should_ocr_pdf_page_text(bad_layer))

    def test_configure_pillow_for_ocr_allows_large_scans(self) -> None:
        class DummyImageModule:
            MAX_IMAGE_PIXELS = 10

        converter.configure_pillow_for_ocr(DummyImageModule)

        self.assertEqual(DummyImageModule.MAX_IMAGE_PIXELS, converter.PIL_MAX_OCR_IMAGE_PIXELS)

    def test_parse_ocr_languages_accepts_common_separators(self) -> None:
        self.assertEqual(converter.parse_ocr_languages("rus+eng,osd"), ("rus", "eng", "osd"))
        self.assertEqual(converter.parse_ocr_languages("eng eng"), ("eng",))

    def test_run_tesseract_uses_selected_languages(self) -> None:
        calls = []
        original_run = converter.subprocess.run

        class Completed:
            returncode = 0
            stdout = "recognized text"
            stderr = ""

        def fake_run(command, **_kwargs):
            calls.append(command)
            return Completed()

        try:
            converter.subprocess.run = fake_run
            result = converter.run_tesseract_on_image(
                Path("page.png"),
                "tesseract.exe",
                None,
                converter.ConversionSettings(ocr_languages=("eng",), max_ocr_workers=1),
            )
        finally:
            converter.subprocess.run = original_run

        self.assertEqual(result, "recognized text")
        self.assertIn("-l", calls[0])
        self.assertIn("eng", calls[0])

    def test_get_tesseract_info_accepts_advanced_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tesseract_path = root / "tesseract.exe"
            tessdata_dir = root / "tessdata"
            tesseract_path.write_text("", encoding="utf-8")
            tessdata_dir.mkdir()

            info = converter.get_tesseract_info(
                converter.ConversionSettings(
                    tesseract_path=str(tesseract_path),
                    tessdata_dir=str(tessdata_dir),
                )
            )

        self.assertEqual(info["path"], str(tesseract_path))
        self.assertEqual(info["tessdata_dir"], str(tessdata_dir))

    def test_run_tesseract_tsv_uses_inline_tsv_config(self) -> None:
        calls = []
        original_run = converter.subprocess.run

        class Completed:
            returncode = 0
            stdout = "\n".join(
                [
                    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
                    "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t95.0\tReader",
                ]
            )
            stderr = ""

        def fake_run(command, **_kwargs):
            calls.append(command)
            return Completed()

        try:
            converter.subprocess.run = fake_run
            result = converter.run_tesseract_tsv_on_image(
                Path("page.png"),
                "tesseract.exe",
                "runtime/tessdata",
                converter.ConversionSettings(ocr_languages=("eng",), max_ocr_workers=1),
                psm=6,
                dpi=300,
                variant="gray",
            )
        finally:
            converter.subprocess.run = original_run

        self.assertEqual(result.text, "Reader")
        self.assertEqual(result.confidence, 95.0)
        self.assertIn("-c", calls[0])
        self.assertIn("tessedit_create_tsv=1", calls[0])
        self.assertNotIn("tsv", calls[0])

    def test_choose_ocr_worker_count_respects_settings(self) -> None:
        settings = converter.ConversionSettings(ocr_languages=("rus", "eng"), max_ocr_workers=1)
        self.assertEqual(converter.choose_ocr_worker_count(10, settings), 1)

    def test_quality_mode_controls_ocr_attempt_matrix(self) -> None:
        standard = converter.ConversionSettings(quality_mode="standard")
        maximum = converter.ConversionSettings(quality_mode="max")

        self.assertEqual(standard.ocr_dpi_values, (converter.STANDARD_OCR_DPI,))
        self.assertEqual(standard.ocr_psm_values, converter.STANDARD_OCR_PSM_VALUES)
        self.assertGreater(len(maximum.ocr_dpi_values), len(standard.ocr_dpi_values))
        self.assertGreater(len(maximum.ocr_psm_values), len(standard.ocr_psm_values))

    def test_format_page_text_can_preserve_page_breaks(self) -> None:
        text = converter.format_page_text(2, "Page body", preserve_page_breaks=True)

        self.assertTrue(text.startswith("---\n\n## Страница 2"))
        self.assertEqual(converter.page_number_from_markdown(text), 2)

    def test_parse_tesseract_tsv_extracts_text_and_confidence(self) -> None:
        tsv = "\n".join(
            [
                "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
                "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t90.0\tHello",
                "5\t1\t1\t1\t1\t2\t12\t0\t10\t10\t80.0\tworld",
                "5\t1\t1\t1\t2\t1\t0\t20\t10\t10\t70.0\tAgain",
            ]
        )

        text, confidence = converter.parse_tesseract_tsv(tsv)

        self.assertEqual(text, "Hello world\nAgain")
        self.assertEqual(confidence, 80.0)

    def test_score_prefers_higher_confidence_clean_text(self) -> None:
        good = converter.build_ocr_attempt_result("Normal readable text " * 30, 90.0, 6, 300, "gray")
        weak = converter.build_ocr_attempt_result("N o r m a l r e a d a b l e t e x t", 30.0, 11, 216, "binary")

        self.assertGreater(good.score, weak.score)
        self.assertTrue(converter.is_high_confidence_ocr_attempt(good))
        self.assertFalse(converter.is_high_confidence_ocr_attempt(weak))

    def test_score_prefers_stable_paragraph_layout_when_quality_is_equal(self) -> None:
        text = "Структурированный текст документа " * 30
        paragraph = converter.build_ocr_attempt_result(text, 90.0, 6, 300, "gray")
        sparse = converter.build_ocr_attempt_result(text, 90.0, 11, 300, "gray")

        self.assertGreater(paragraph.score, sparse.score)

    def test_max_quality_warns_when_ocr_confidence_is_missing(self) -> None:
        warning = converter.assess_page_text_warning(
            "Readable OCR text with enough words for a confidence check.",
            source="ocr",
            confidence=None,
            require_confidence=True,
        )

        self.assertIn("Уверенность OCR не получена.", warning)

    def test_report_files_include_summary_and_page_ocr_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "markdown_result_test"
            result_dir.mkdir()
            source = root / "scan.pdf"
            source.write_text("placeholder", encoding="utf-8")
            result = converter.ConversionResult(
                source=source,
                output_name="scan.md",
                doc_type="PDF-скан",
                method="Постранично: текст+OCR",
                status="успешно",
                char_count=1200,
                page_count=2,
                cyrillic_ratio=0.9,
                replacement_count=0,
                quality_status="норма",
                text_page_count=1,
                ocr_page_count=1,
                blank_page_count=0,
                page_report=[
                    converter.PageOcrEntry(page_index=1, source="text", char_count=700),
                    converter.PageOcrEntry(page_index=2, source="ocr", char_count=500, warning="Мало текста."),
                ],
            )

            started = converter.dt.datetime(2026, 6, 10, 10, 0, 0)
            finished = converter.dt.datetime(2026, 6, 10, 10, 0, 5)
            converter.write_run_report_file(
                result_dir,
                root,
                [result],
                {"path": "tesseract.exe", "version": "5.4.0", "languages": ["eng", "osd", "rus"]},
                started,
                finished,
            )
            converter.write_ocr_report_file(result_dir, [result], started, finished)

            run_report = (result_dir / "REPORT.txt").read_text(encoding="utf-8")
            ocr_report = (result_dir / "OCR_REPORT.txt").read_text(encoding="utf-8")

        self.assertIn("документов обработано: 1", run_report)
        self.assertIn("страниц OCR: 1", run_report)
        self.assertIn("страниц с замечаниями OCR: 1", run_report)
        self.assertIn("OCR языки: rus+eng", run_report)
        self.assertIn("границы страниц в Markdown: обычный режим", run_report)
        self.assertIn("scan.pdf", ocr_report)
        self.assertIn("Страницы и изображения для ручной проверки:", ocr_report)
        self.assertIn("стр. 2: OCR", ocr_report)
        self.assertIn("Мало текста.", ocr_report)


    def test_ocr_report_includes_max_quality_attempt_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "markdown_result_test"
            result_dir.mkdir()
            source = root / "scan.pdf"
            source.write_text("placeholder", encoding="utf-8")
            result = converter.ConversionResult(
                source=source,
                output_name="scan.md",
                doc_type="PDF-scan",
                method="Page OCR",
                status="success",
                char_count=650,
                page_count=1,
                cyrillic_ratio=0.0,
                replacement_count=0,
                quality_status="ok",
                ocr_page_count=1,
                page_report=[
                    converter.PageOcrEntry(
                        page_index=1,
                        source="ocr",
                        char_count=650,
                        confidence=72.5,
                        psm=6,
                        dpi=300,
                        variant="contrast_sharp",
                        attempt_count=4,
                        selected_reason="score=210.0; confidence=72.5; dpi=300; psm=6",
                    )
                ],
            )
            started = converter.dt.datetime(2026, 6, 10, 10, 0, 0)
            finished = converter.dt.datetime(2026, 6, 10, 10, 0, 5)

            converter.write_run_report_file(
                result_dir,
                root,
                [result],
                {"path": "tesseract.exe", "version": "5.4.0", "languages": ["eng", "osd", "rus"]},
                started,
                finished,
            )
            converter.write_ocr_report_file(result_dir, [result], started, finished)

            run_report = (result_dir / "REPORT.txt").read_text(encoding="utf-8")
            ocr_report = (result_dir / "OCR_REPORT.txt").read_text(encoding="utf-8")

        self.assertIn("max", run_report)
        self.assertIn("72.5", run_report)
        self.assertIn("72.5", ocr_report)
        self.assertIn("dpi: 300", ocr_report)
        self.assertIn("psm: 6", ocr_report)
        self.assertIn("contrast_sharp", ocr_report)


if __name__ == "__main__":
    unittest.main()
