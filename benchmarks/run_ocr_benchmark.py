from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODES = ("standard", "max")
PAGE_WIDTH = 612
PAGE_HEIGHT = 792


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    filename: str
    required_phrases: tuple[str, ...]
    russian_phrases: tuple[str, ...] = ()


@dataclass
class ModeResult:
    label: str
    mode: str
    command: list[str]
    source_dir: str
    result_dir: str
    return_code: int
    duration_seconds: float
    phrase_total: int
    phrase_found: int
    missing_phrases: list[str]
    russian_phrase_total: int
    russian_phrase_found: int
    missing_russian_phrases: list[str]
    russian_passed: bool
    extracted_chars: int | None
    ocr_pages: int | None
    review_pages: int | None
    average_confidence: float | None
    passed: bool


BENCHMARK_CASES = (
    BenchmarkCase(
        name="text_layer_pdf",
        filename="text_layer.pdf",
        required_phrases=(
            "text layer benchmark",
            "reader keeps searchable pdf text",
        ),
    ),
    BenchmarkCase(
        name="scanned_pdf",
        filename="scanned.pdf",
        required_phrases=(
            "reader benchmark scanned page",
            "reader should extract text accurately",
        ),
    ),
    BenchmarkCase(
        name="rotated_pdf",
        filename="rotated.pdf",
        required_phrases=(
            "rotated benchmark page",
            "reader handles slight rotation",
        ),
    ),
    BenchmarkCase(
        name="small_text_pdf",
        filename="small_text.pdf",
        required_phrases=(
            "small text benchmark",
            "reader keeps tiny text useful",
        ),
    ),
    BenchmarkCase(
        name="table_scan_pdf",
        filename="table_scan.pdf",
        required_phrases=(
            "table scan benchmark",
            "amount due",
        ),
    ),
    BenchmarkCase(
        name="russian_scan_pdf",
        filename="russian_scan.pdf",
        required_phrases=(),
        russian_phrases=(
            "проверка русского текста",
            "качество распознавания",
        ),
    ),
    BenchmarkCase(
        name="mixed_pdf",
        filename="mixed.pdf",
        required_phrases=(
            "mixed text page benchmark",
            "mixed scanned page benchmark",
        ),
    ),
    BenchmarkCase(
        name="low_contrast_pdf",
        filename="low_contrast.pdf",
        required_phrases=(
            "low contrast benchmark",
            "quality signal phrase alpha beta",
        ),
    ),
    BenchmarkCase(
        name="structured_docx",
        filename="structured.docx",
        required_phrases=(
            "docx table benchmark",
            "payment schedule",
            "quality clause",
        ),
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Reader synthetic OCR benchmark")
    parser.add_argument("--output-dir", type=Path, help="Optional benchmark result directory")
    parser.add_argument("--ocr-languages", default="rus+eng", help="Tesseract languages for benchmark runs")
    parser.add_argument("--ocr-workers", default="1", help="OCR worker count for stable timing")
    parser.add_argument("--label", default="current", help="Label for this Tesseract/Reader benchmark run")
    parser.add_argument("--tesseract-path", type=Path, help="Optional tesseract.exe path to pass to Reader")
    parser.add_argument("--tessdata-dir", type=Path, help="Optional tessdata folder to pass to Reader")
    args = parser.parse_args()

    ensure_pillow_available()

    result_root = args.output_dir.resolve() if args.output_dir else make_benchmark_result_dir(PROJECT_ROOT)
    result_root.mkdir(parents=True, exist_ok=True)

    started_at = dt.datetime.now()
    mode_results = [
        run_mode(
            result_root,
            mode,
            args.ocr_languages,
            args.ocr_workers,
            args.label,
            args.tesseract_path,
            args.tessdata_dir,
        )
        for mode in DEFAULT_MODES
    ]
    finished_at = dt.datetime.now()

    report_lines = build_markdown_report(mode_results, result_root, started_at, finished_at)
    report_path = result_root / "BENCHMARK_REPORT.md"
    report_path.write_text("\n".join(report_lines).strip() + "\n", encoding="utf-8")
    summary_path = result_root / "benchmark_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "created_at": started_at.isoformat(timespec="seconds"),
                "finished_at": finished_at.isoformat(timespec="seconds"),
                "overall_passed": benchmark_passed(mode_results),
                "max_not_worse_than_standard": max_not_worse_than_standard(mode_results),
                "russian_ocr_passed": russian_benchmark_passed(mode_results),
                "results": [asdict(item) for item in mode_results],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Benchmark report: {report_path}")
    print(f"Benchmark summary: {summary_path}")
    return 0 if benchmark_passed(mode_results) else 1


def ensure_pillow_available() -> None:
    try:
        import PIL  # noqa: F401

        return
    except ImportError:
        runtime_python = PROJECT_ROOT / "runtime" / ".venv" / "Scripts" / "python.exe"
        if runtime_python.exists() and Path(sys.executable).resolve() != runtime_python.resolve():
            os.execv(str(runtime_python), [str(runtime_python), *sys.argv])
        raise


def make_benchmark_result_dir(root: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M")
    base = root / f"benchmark_result_{stamp}"
    if not base.exists():
        return base
    for counter in range(2, 1000):
        candidate = root / f"benchmark_result_{stamp}_{counter}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not create a unique benchmark result directory.")


def run_mode(
    result_root: Path,
    mode: str,
    ocr_languages: str,
    ocr_workers: str,
    label: str = "current",
    tesseract_path: Path | None = None,
    tessdata_dir: Path | None = None,
) -> ModeResult:
    safe_label = sanitize_path_part(label)
    mode_root = result_root / safe_label / mode
    source_dir = mode_root / "input_documents"
    source_dir.mkdir(parents=True, exist_ok=True)
    create_benchmark_documents(source_dir)

    command = [
        sys.executable,
        str(PROJECT_ROOT / "src" / "reader" / "markdown_converter.py"),
        str(source_dir),
        "--no-progress-window",
        "--quality-mode",
        mode,
        "--ocr-languages",
        ocr_languages,
        "--ocr-workers",
        ocr_workers,
        "--preserve-page-breaks",
    ]
    if tesseract_path:
        command.extend(["--tesseract-path", str(tesseract_path.resolve())])
    if tessdata_dir:
        command.extend(["--tessdata-dir", str(tessdata_dir.resolve())])

    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    duration = round(time.perf_counter() - started, 2)
    mode_root.mkdir(parents=True, exist_ok=True)
    (mode_root / "converter_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (mode_root / "converter_stderr.txt").write_text(completed.stderr, encoding="utf-8")

    result_dir = find_latest_reader_result_dir(source_dir)
    combined_text = ""
    report_text = ""
    if result_dir:
        combined_path = result_dir / "00_ALL_DOCUMENTS.md"
        report_path = result_dir / "REPORT.txt"
        if combined_path.exists():
            combined_text = combined_path.read_text(encoding="utf-8")
        if report_path.exists():
            report_text = report_path.read_text(encoding="utf-8")

    phrase_total, phrase_found, missing_phrases = evaluate_required_phrases(combined_text)
    russian_total, russian_found, missing_russian = evaluate_russian_phrases(combined_text)
    metrics = parse_report_metrics(report_text)
    passed = completed.returncode == 0 and not missing_phrases
    if mode == "max":
        passed = passed and metrics["average_confidence"] is not None

    russian_passed = russian_total > 0 and not missing_russian

    return ModeResult(
        label=label,
        mode=mode,
        command=command,
        source_dir=str(source_dir),
        result_dir=str(result_dir or ""),
        return_code=completed.returncode,
        duration_seconds=duration,
        phrase_total=phrase_total,
        phrase_found=phrase_found,
        missing_phrases=missing_phrases,
        russian_phrase_total=russian_total,
        russian_phrase_found=russian_found,
        missing_russian_phrases=missing_russian,
        russian_passed=russian_passed,
        extracted_chars=metrics["extracted_chars"],
        ocr_pages=metrics["ocr_pages"],
        review_pages=metrics["review_pages"],
        average_confidence=metrics["average_confidence"],
        passed=passed,
    )


def create_benchmark_documents(source_dir: Path) -> None:
    create_text_pdf(
        source_dir / "text_layer.pdf",
        [
            ["Text layer benchmark", "Reader keeps searchable PDF text", "This page should not need OCR."],
        ],
    )
    create_image_pdf(
        source_dir / "scanned.pdf",
        [
            ["Reader benchmark scanned page", "Reader should extract text accurately", "quality signal phrase alpha beta"],
        ],
    )
    create_image_pdf(
        source_dir / "rotated.pdf",
        [
            ["Rotated benchmark page", "Reader handles slight rotation", "Quality stays measurable"],
        ],
        rotate_degrees=1.5,
    )
    create_image_pdf(
        source_dir / "small_text.pdf",
        [
            ["Small text benchmark", "Reader keeps tiny text useful", "Control phrase remains visible"],
        ],
        font_size=72,
    )
    create_image_pdf(
        source_dir / "table_scan.pdf",
        [
            ["Table scan benchmark", "Item amount due", "Service 100", "Delivery 200"],
        ],
    )
    create_image_pdf(
        source_dir / "russian_scan.pdf",
        [
            ["Проверка русского текста", "Качество распознавания", "Документ создан безопасно"],
        ],
        font_size=82,
    )
    create_mixed_pdf(source_dir / "mixed.pdf")
    create_image_pdf(
        source_dir / "low_contrast.pdf",
        [
            ["Low contrast benchmark", "Reader should still extract useful text", "quality signal phrase alpha beta"],
        ],
        low_contrast=True,
    )
    create_docx(
        source_dir / "structured.docx",
        [
            "DOCX table benchmark",
            "Quality clause: Reader must preserve useful document text.",
            "Payment schedule is included below.",
        ],
    )


def create_text_pdf(path: Path, pages: list[list[str]]) -> None:
    write_pdf(path, [{"type": "text", "lines": lines} for lines in pages])


def create_image_pdf(
    path: Path,
    pages: list[list[str]],
    low_contrast: bool = False,
    rotate_degrees: float = 0.0,
    font_size: int = 86,
) -> None:
    pdf_pages = []
    temp_images: list[Path] = []
    try:
        for index, lines in enumerate(pages, start=1):
            image_path = path.with_name(f".{path.stem}_{index}.jpg")
            create_scan_image(
                image_path,
                lines,
                low_contrast=low_contrast,
                rotate_degrees=rotate_degrees,
                font_size=font_size,
            )
            temp_images.append(image_path)
            pdf_pages.append({"type": "image", "image_path": image_path})
        write_pdf(path, pdf_pages)
    finally:
        for image_path in temp_images:
            image_path.unlink(missing_ok=True)


def create_mixed_pdf(path: Path) -> None:
    image_path = path.with_name(".mixed_scanned_page.jpg")
    try:
        create_scan_image(
            image_path,
            ["Mixed scanned page benchmark", "Reader should OCR only this page"],
            low_contrast=False,
        )
        write_pdf(
            path,
            [
                {"type": "text", "lines": ["Mixed text page benchmark", "Reader should use the PDF text layer here"]},
                {"type": "image", "image_path": image_path},
            ],
        )
    finally:
        image_path.unlink(missing_ok=True)


def create_scan_image(
    path: Path,
    lines: list[str],
    low_contrast: bool = False,
    rotate_degrees: float = 0.0,
    font_size: int = 86,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    background = (238, 238, 238) if low_contrast else "white"
    foreground = (92, 92, 92) if low_contrast else "black"
    image = Image.new("RGB", (1700, 2200), background)
    draw = ImageDraw.Draw(image)
    font_path = Path(r"C:\Windows\Fonts\arial.ttf")
    font = ImageFont.truetype(str(font_path), font_size) if font_path.exists() else ImageFont.load_default()
    y = 420
    for line in lines:
        draw.text((130, y), line, fill=foreground, font=font)
        y += 155
    if rotate_degrees:
        image = image.rotate(rotate_degrees, expand=True, fillcolor=background)
    image.save(path, "JPEG", quality=95)


def create_docx(path: Path, paragraphs: list[str]) -> None:
    paragraph_xml = "".join(f"<w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>" for text in paragraphs)
    table_xml = """
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Milestone</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Payment schedule</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Delivery</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Quality clause</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    """
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {paragraph_xml}
    {table_xml}
    <w:sectPr/>
  </w:body>
</w:document>"""
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)


def write_pdf(path: Path, pages: list[dict]) -> None:
    objects: list[bytes] = [b"", b""]
    font_id = add_pdf_object(objects, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []

    for page in pages:
        if page["type"] == "text":
            content = build_text_page_content(page["lines"])
            content_id = add_pdf_stream(objects, content.encode("latin-1"))
            page_id = add_pdf_object(
                objects,
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
                ).encode("ascii"),
            )
        elif page["type"] == "image":
            image_id, width, height = add_pdf_image_object(objects, Path(page["image_path"]))
            draw_width, draw_height, offset_x, offset_y = fit_image_to_page(width, height)
            content = f"q {draw_width:.2f} 0 0 {draw_height:.2f} {offset_x:.2f} {offset_y:.2f} cm /Im1 Do Q\n"
            content_id = add_pdf_stream(objects, content.encode("ascii"))
            page_id = add_pdf_object(
                objects,
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                    f"/Resources << /XObject << /Im1 {image_id} 0 R >> >> /Contents {content_id} 0 R >>"
                ).encode("ascii"),
            )
        else:
            raise ValueError(f"Unsupported PDF page type: {page['type']}")
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    write_pdf_objects(path, objects)


def add_pdf_object(objects: list[bytes], body: bytes) -> int:
    objects.append(body)
    return len(objects)


def add_pdf_stream(objects: list[bytes], stream: bytes, extra: str = "") -> int:
    header = f"<< {extra} /Length {len(stream)} >>".encode("ascii")
    return add_pdf_object(objects, header + b"\nstream\n" + stream + b"\nendstream")


def add_pdf_image_object(objects: list[bytes], image_path: Path) -> tuple[int, int, int]:
    from PIL import Image

    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        buffer = BytesIO()
        rgb.save(buffer, format="JPEG", quality=92)
    extra = (
        f"/Type /XObject /Subtype /Image /Width {width} /Height {height} "
        "/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode"
    )
    return add_pdf_stream(objects, buffer.getvalue(), extra), width, height


def write_pdf_objects(path: Path, objects: list[bytes]) -> None:
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode("ascii"))
        data.extend(body)
        data.extend(b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    data.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(data)


def build_text_page_content(lines: list[str]) -> str:
    content = ["BT", "/F1 24 Tf", "72 720 Td"]
    for index, line in enumerate(lines):
        if index:
            content.append("0 -34 Td")
        content.append(f"({escape_pdf_text(line)}) Tj")
    content.append("ET")
    return "\n".join(content) + "\n"


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def fit_image_to_page(width: int, height: int) -> tuple[float, float, float, float]:
    scale = min(PAGE_WIDTH / width, PAGE_HEIGHT / height)
    draw_width = width * scale
    draw_height = height * scale
    return draw_width, draw_height, (PAGE_WIDTH - draw_width) / 2, (PAGE_HEIGHT - draw_height) / 2


def find_latest_reader_result_dir(source_dir: Path) -> Path | None:
    result_dirs = [path for path in source_dir.glob("markdown_result_*") if path.is_dir()]
    if not result_dirs:
        return None
    return max(result_dirs, key=lambda path: path.stat().st_mtime)


def evaluate_required_phrases(markdown_text: str) -> tuple[int, int, list[str]]:
    phrases = [phrase for case in BENCHMARK_CASES for phrase in case.required_phrases]
    missing = [phrase for phrase in phrases if not phrase_present(markdown_text, phrase)]
    return len(phrases), len(phrases) - len(missing), missing


def evaluate_russian_phrases(markdown_text: str) -> tuple[int, int, list[str]]:
    phrases = [phrase for case in BENCHMARK_CASES for phrase in case.russian_phrases]
    missing = [phrase for phrase in phrases if not phrase_present(markdown_text, phrase)]
    return len(phrases), len(phrases) - len(missing), missing


def phrase_present(text: str, phrase: str) -> bool:
    normalized_text = normalize_for_match(text)
    normalized_phrase = normalize_for_match(phrase)
    if normalized_phrase in normalized_text:
        return True
    words = [word for word in normalized_phrase.split() if len(word) >= 4]
    return bool(words) and all(word in normalized_text for word in words)


def normalize_for_match(text: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-zА-Яа-яЁё]+", " ", text.upper())
    return re.sub(r"\s+", " ", normalized).strip()


def parse_report_metrics(report_text: str) -> dict[str, int | float | None]:
    return {
        "extracted_chars": parse_int_metric(report_text, "символов извлечено"),
        "ocr_pages": parse_int_metric(report_text, "страниц OCR"),
        "review_pages": parse_int_metric(report_text, "страниц с замечаниями OCR"),
        "average_confidence": parse_float_metric(report_text, "средняя уверенность OCR"),
    }


def parse_int_metric(text: str, label: str) -> int | None:
    match = re.search(rf"- {re.escape(label)}:\s*([0-9]+)", text)
    return int(match.group(1)) if match else None


def parse_float_metric(text: str, label: str) -> float | None:
    match = re.search(rf"- {re.escape(label)}:\s*([0-9]+(?:[.,][0-9]+)?)", text)
    return float(match.group(1).replace(",", ".")) if match else None


def benchmark_passed(results: list[ModeResult]) -> bool:
    by_mode = {result.mode: result for result in results}
    standard = by_mode.get("standard")
    maximum = by_mode.get("max")
    if not standard or not maximum:
        return False
    if not all(result.passed for result in results):
        return False
    return max_not_worse_than_standard(results)


def max_not_worse_than_standard(results: list[ModeResult]) -> bool:
    by_mode = {result.mode: result for result in results}
    standard = by_mode.get("standard")
    maximum = by_mode.get("max")
    if not standard or not maximum:
        return False
    return maximum.phrase_found >= standard.phrase_found


def russian_benchmark_passed(results: list[ModeResult]) -> bool:
    max_result = next((result for result in results if result.mode == "max"), None)
    return bool(max_result and max_result.russian_passed)


def build_markdown_report(
    results: list[ModeResult],
    result_root: Path,
    started_at: dt.datetime,
    finished_at: dt.datetime,
) -> list[str]:
    overall = "PASS" if benchmark_passed(results) else "FAIL"
    russian_status = "PASS" if russian_benchmark_passed(results) else "FAIL"
    lines = [
        "# Reader OCR Benchmark Report",
        "",
        f"- Created: {started_at:%Y-%m-%d %H:%M:%S}",
        f"- Finished: {finished_at:%Y-%m-%d %H:%M:%S}",
        f"- Result folder: `{result_root}`",
        f"- Overall: **{overall}**",
        f"- Max not worse than standard: **{'PASS' if max_not_worse_than_standard(results) else 'FAIL'}**",
        f"- Russian OCR: **{russian_status}**",
        "",
        "## Summary",
        "",
        "| Label | Mode | Result | Phrases | Russian | Seconds | OCR pages | Review pages | Avg confidence | Characters |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            "| "
            f"{result.label} | "
            f"{result.mode} | "
            f"{'PASS' if result.passed else 'FAIL'} | "
            f"{result.phrase_found}/{result.phrase_total} | "
            f"{result.russian_phrase_found}/{result.russian_phrase_total} | "
            f"{result.duration_seconds:.2f} | "
            f"{format_optional(result.ocr_pages)} | "
            f"{format_optional(result.review_pages)} | "
            f"{format_optional_float(result.average_confidence)} | "
            f"{format_optional(result.extracted_chars)} |"
        )

    lines.extend(["", "## Details", ""])
    for result in results:
        lines.extend(
            [
                f"### {result.mode}",
                "",
                f"- Command: `{format_command(result.command)}`",
                f"- Source folder: `{result.source_dir}`",
                f"- Reader result folder: `{result.result_dir or 'not created'}`",
                f"- Return code: {result.return_code}",
                f"- Missing phrases: {', '.join(result.missing_phrases) if result.missing_phrases else 'none'}",
                f"- Missing Russian phrases: {', '.join(result.missing_russian_phrases) if result.missing_russian_phrases else 'none'}",
                "",
            ]
        )
    return lines


def format_optional(value: int | None) -> str:
    return str(value) if value is not None else "n/a"


def format_optional_float(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "n/a"


def format_command(command: list[str]) -> str:
    return " ".join(f'"{part}"' if " " in part else part for part in command)


def sanitize_path_part(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", value).strip(" .")
    return cleaned or "current"


if __name__ == "__main__":
    raise SystemExit(main())
