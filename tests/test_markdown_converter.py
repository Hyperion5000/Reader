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

    def test_find_documents_skips_runtime_build_dist_and_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "markdown_result_new"
            for folder in ["runtime", "build", "dist", "markdown_result_old", "docs"]:
                (root / folder).mkdir()
            (root / "runtime" / "hidden.pdf").write_text("x", encoding="utf-8")
            (root / "build" / "hidden.pdf").write_text("x", encoding="utf-8")
            (root / "dist" / "hidden.pdf").write_text("x", encoding="utf-8")
            (root / "markdown_result_old" / "hidden.pdf").write_text("x", encoding="utf-8")
            (root / "docs" / "visible.pdf").write_text("x", encoding="utf-8")
            (root / "visible.docx").write_text("x", encoding="utf-8")

            found = converter.find_documents(root, result_dir)

        names = {path.name for path in found}
        self.assertEqual(names, {"visible.docx", "visible.pdf"})

    def test_process_document_writes_no_metadata_header(self) -> None:
        original_convert_file = converter.convert_file
        try:
            converter.convert_file = lambda *_args, **_kwargs: ("Основной текст", "test")
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


if __name__ == "__main__":
    unittest.main()
