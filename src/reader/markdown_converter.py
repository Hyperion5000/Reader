from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Callable


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
LOW_TEXT_THRESHOLD = 400
PDF_TEXT_LAYER_THRESHOLD = 40
PDF_TEXT_LAYER_MIN_LETTERS_FOR_QUALITY_CHECK = 60
PDF_TEXT_LAYER_BAD_SINGLE_TOKEN_RATIO = 0.65
PDF_TEXT_LAYER_BAD_CYRILLIC_RATIO = 0.25
BLANK_PAGE_DARK_PIXEL_RATIO = 0.01
MAX_OCR_WORKERS = 4
PIL_MAX_OCR_IMAGE_PIXELS = 250_000_000
SKIP_DIR_NAMES = {".venv", "__pycache__", "build", "dist", "runtime", "tessdata"}


@dataclass
class PageOcrEntry:
    page_index: int
    source: str
    char_count: int
    warning: str = ""


@dataclass
class ConversionResult:
    source: Path
    output_name: str
    doc_type: str
    method: str
    status: str
    char_count: int
    page_count: int | None
    cyrillic_ratio: float
    replacement_count: int
    quality_status: str
    text_page_count: int = 0
    ocr_page_count: int = 0
    blank_page_count: int = 0
    page_report: list[PageOcrEntry] = field(default_factory=list)
    warning: str = ""
    error: str = ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Local PDF/DOCX to Markdown converter")
    parser.add_argument("folder", nargs="?", help="Folder with PDF/DOCX files")
    parser.add_argument("--check", action="store_true", help="Check local environment only")
    parser.add_argument("--open-result", action="store_true", help="Open result folder when finished")
    args = parser.parse_args()

    if args.check:
        print_environment_check()
        return 0

    source_dir = Path(args.folder).resolve() if args.folder else choose_folder()
    if not source_dir:
        print("Папка не выбрана. Работа остановлена.")
        return 1
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Папка не найдена: {source_dir}")
        return 1

    started_at = dt.datetime.now()
    print(f"Папка с документами: {source_dir}")
    print_environment_check()

    result_dir = make_result_dir(source_dir)
    clean_dir = result_dir / "01_markdown"
    problem_dir = result_dir / "02_problem_files"
    clean_dir.mkdir(parents=True, exist_ok=True)

    files = find_documents(source_dir, result_dir)
    if not files:
        print("В выбранной папке не найдено PDF/DOCX файлов.")
        return 1

    print(f"Найдено документов: {len(files)}")
    tesseract_info = get_tesseract_info()
    print("Финальный Markdown создаётся безопасной очисткой без нейросетевых редакторов.")

    used_names: set[str] = set()
    results: list[ConversionResult] = []

    for index, file_path in enumerate(files, start=1):
        print(f"\n[{index}/{len(files)}] {file_path.name}")
        output_name = unique_output_name(file_path, source_dir, used_names)
        result = process_document(
            file_path=file_path,
            output_name=output_name,
            clean_dir=clean_dir,
            problem_dir=problem_dir,
            tesseract_info=tesseract_info,
        )
        results.append(result)
        print(f"Результат: {result.status}. Символов: {result.char_count}. {result.warning}".strip())

    finished_at = dt.datetime.now()
    write_combined_markdown_file(result_dir, clean_dir, results)
    write_run_report_file(result_dir, source_dir, results, tesseract_info, started_at, finished_at)
    write_ocr_report_file(result_dir, results, started_at, finished_at)
    print("\nГотово.")
    print(f"Папка результата: {result_dir}")
    print(f"Общий файл: {result_dir / '00_ALL_DOCUMENTS.md'}")
    print(f"Отчет: {result_dir / 'REPORT.txt'}")
    print(f"OCR-отчет: {result_dir / 'OCR_REPORT.txt'}")
    if args.open_result:
        open_result_folder(result_dir)
    return 0


def choose_folder() -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(
            title="Выберите папку с PDF и DOCX",
            initialdir=str(Path.cwd()),
        )
        root.destroy()
        return Path(folder).resolve() if folder else None
    except Exception:
        print("Не удалось открыть окно выбора папки. Будет использована текущая папка.")
        return Path.cwd().resolve()


def open_result_folder(result_dir: Path) -> None:
    try:
        os.startfile(str(result_dir))
    except Exception:
        pass


def print_environment_check() -> None:
    print("\nПроверка среды:")
    print(f"- Python: {sys.version.split()[0]}")
    print(f"- Docling: {package_state('docling', 'docling')}")
    print(f"- MarkItDown: {package_state('markitdown', 'markitdown')}")
    print(f"- PDFium: {package_state('pypdfium2', 'pypdfium2')}")
    tess = get_tesseract_info()
    if tess["path"]:
        langs = ", ".join(tess["languages"]) if tess["languages"] else "языки не определены"
        tess_version = f", версия {tess['version']}" if tess.get("version") else ""
        print(f"- Tesseract OCR: найден{tess_version} ({langs})")
    else:
        print("- Tesseract OCR: не найден")


def package_state(module_name: str, package_name: str) -> str:
    if not importlib.util.find_spec(module_name):
        return "не установлен"
    try:
        return f"установлен, версия {version(package_name)}"
    except PackageNotFoundError:
        return "установлен"


def find_documents(source_dir: Path, result_dir: Path) -> list[Path]:
    files: list[Path] = []
    for item in source_dir.rglob("*"):
        if not item.is_file():
            continue
        if result_dir in item.parents:
            continue
        if should_skip_path(item, source_dir):
            continue
        if item.name.startswith("~$"):
            continue
        if item.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(item)
    return sorted(files, key=lambda p: str(p).lower())


def should_skip_path(item: Path, source_dir: Path) -> bool:
    try:
        relative_parts = item.relative_to(source_dir).parts[:-1]
    except ValueError:
        return False
    for part in relative_parts:
        if part in SKIP_DIR_NAMES:
            return True
        if part.startswith("markdown_result_") or part.startswith(".converter_"):
            return True
    return False


def make_result_dir(source_dir: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M")
    base = source_dir / f"markdown_result_{stamp}"
    if not base.exists():
        return base
    counter = 2
    while True:
        candidate = source_dir / f"markdown_result_{stamp}_{counter}"
        if not candidate.exists():
            return candidate
        counter += 1


def unique_output_name(file_path: Path, source_dir: Path, used_names: set[str]) -> str:
    relative = file_path.relative_to(source_dir)
    stem = "__".join(relative.with_suffix("").parts)
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", stem).strip(" .")
    stem = stem or "document"
    candidate = f"{stem}.md"
    counter = 2
    while candidate.lower() in used_names:
        candidate = f"{stem}_{counter}.md"
        counter += 1
    used_names.add(candidate.lower())
    return candidate


def process_document(
    file_path: Path,
    output_name: str,
    clean_dir: Path,
    problem_dir: Path,
    tesseract_info: dict,
) -> ConversionResult:
    doc_type = detect_doc_type(file_path)
    method = ""
    warning = ""
    error = ""
    status = "успешно"
    raw_markdown = ""
    page_count = get_page_count(file_path)
    quality_status = "нет текста"
    cyrillic_ratio = 0.0
    replacement_count = 0
    page_report: list[PageOcrEntry] = []

    try:
        raw_markdown, method, page_report = convert_file(file_path, doc_type, tesseract_info)
        raw_markdown = normalize_newlines(raw_markdown).strip()
        if not raw_markdown:
            raise RuntimeError("Конвертер вернул пустой текст.")
        quality = assess_text_quality(raw_markdown, doc_type)
        quality_status = quality["status"]
        cyrillic_ratio = quality["cyrillic_ratio"]
        replacement_count = quality["replacement_count"]
        if len(raw_markdown) < LOW_TEXT_THRESHOLD:
            status = "требует проверки"
            warning = "Мало извлечённого текста, нужно проверить вручную."
        if doc_type in {"PDF-скан", "PDF смешанный"} and "OCR" not in method:
            status = "требует проверки"
            warning = join_warning(warning, "Скан обработан запасным методом, OCR нужно проверить.")
        if doc_type in {"PDF-скан", "PDF смешанный"} and looks_like_bad_russian_ocr(raw_markdown):
            status = "требует проверки"
            warning = join_warning(warning, "Похоже на слабое распознавание русского текста.")
        if quality["warning"]:
            warning = join_warning(warning, quality["warning"])
            if quality["status"] != "норма":
                status = "требует проверки" if status == "успешно" else status
    except Exception as exc:
        status = "ошибка"
        error = str(exc)
        warning = "Файл не удалось конвертировать."

    char_count = len(raw_markdown)
    if doc_type in {"PDF-скан", "PDF смешанный"} and not tesseract_info["path"]:
        status = "требует проверки" if status == "успешно" else status
        warning = join_warning(warning, "Tesseract OCR не найден; качество сканов может быть низким.")
    if doc_type in {"PDF-скан", "PDF смешанный"} and tesseract_info["path"] and "rus" not in tesseract_info["languages"]:
        status = "требует проверки" if status == "успешно" else status
        warning = join_warning(warning, "В Tesseract не найден русский язык rus.")

    clean_path = clean_dir / output_name

    clean_text = raw_markdown.strip() + "\n" if raw_markdown else f"Ошибка: {error}\n"
    if raw_markdown:
        cleaned_body = conservative_cleanup(raw_markdown)
        if cleaned_body.strip():
            clean_text = cleaned_body.strip() + "\n"
    clean_path.write_text(clean_text, encoding="utf-8")

    if status != "успешно":
        problem_dir.mkdir(parents=True, exist_ok=True)
        problem_note = build_problem_note(file_path, doc_type, method, status, warning, error)
        (problem_dir / output_name).write_text(problem_note, encoding="utf-8")

    return ConversionResult(
        source=file_path,
        output_name=output_name,
        doc_type=doc_type,
        method=method or "не выполнено",
        status=status,
        char_count=char_count,
        page_count=page_count,
        cyrillic_ratio=cyrillic_ratio,
        replacement_count=replacement_count,
        quality_status=quality_status,
        text_page_count=sum(1 for page in page_report if page.source == "text"),
        ocr_page_count=sum(1 for page in page_report if page.source == "ocr"),
        blank_page_count=sum(1 for page in page_report if page.source == "blank"),
        page_report=page_report,
        warning=warning,
        error=error,
    )


def detect_doc_type(file_path: Path) -> str:
    if file_path.suffix.lower() == ".docx":
        return "DOCX"
    if file_path.suffix.lower() != ".pdf":
        return file_path.suffix.lower().lstrip(".").upper()
    page_texts = get_pdf_page_texts(file_path)
    if not page_texts:
        return "PDF-скан"
    ocr_pages = sum(1 for page_text in page_texts if should_ocr_pdf_page_text(page_text))
    if ocr_pages == len(page_texts):
        return "PDF-скан"
    if ocr_pages:
        return "PDF смешанный"
    return "PDF с текстом"


def get_page_count(file_path: Path) -> int | None:
    if file_path.suffix.lower() != ".pdf":
        return None
    try:
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(str(file_path)) as document:
            return len(document)
    except Exception:
        return None


def assess_text_quality(text: str, doc_type: str) -> dict:
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text)
    cyrillic = re.findall(r"[А-Яа-яЁё]", text)
    cyrillic_ratio = round(len(cyrillic) / len(letters), 3) if letters else 0.0
    replacement_count = text.count("\uFFFD")
    warnings: list[str] = []

    if replacement_count:
        warnings.append(f"Есть нечитаемые символы: {replacement_count}.")
    if len(text) < LOW_TEXT_THRESHOLD:
        warnings.append("Очень мало текста.")
    if doc_type in {"PDF-скан", "PDF смешанный"} and cyrillic_ratio < 0.35 and len(letters) >= 200:
        warnings.append("Низкая доля кириллицы для русского скана.")

    status = "норма" if not warnings else "проверить"
    return {
        "status": status,
        "cyrillic_ratio": cyrillic_ratio,
        "replacement_count": replacement_count,
        "warning": " ".join(warnings),
    }


def get_pdf_page_text_counts(file_path: Path) -> list[int]:
    return [len(page_text.strip()) for page_text in get_pdf_page_texts(file_path)]


def get_pdf_page_texts(file_path: Path) -> list[str]:
    try:
        import pypdfium2 as pdfium

        texts: list[str] = []
        with pdfium.PdfDocument(str(file_path)) as document:
            for page_index in range(len(document)):
                page = document[page_index]
                try:
                    texts.append(extract_pdfium_page_text(page))
                finally:
                    page.close()
        return texts
    except Exception:
        return []


def extract_pdfium_page_text(page) -> str:
    text_page = page.get_textpage()
    try:
        return normalize_newlines(text_page.get_text_range()).strip()
    finally:
        text_page.close()


def convert_file(file_path: Path, doc_type: str, tesseract_info: dict) -> tuple[str, str, list[PageOcrEntry]]:
    errors: list[str] = []
    converters: list[tuple[str, Callable[[], str | tuple[str, list[PageOcrEntry]]]]] = []

    if file_path.suffix.lower() == ".docx":
        converters = [
            ("Встроенное чтение DOCX", lambda: convert_docx_direct(file_path)),
            ("MarkItDown", lambda: convert_with_markitdown(file_path)),
            ("Docling", lambda: convert_with_docling(file_path, use_ocr=False, tesseract_info=tesseract_info)),
        ]
    elif file_path.suffix.lower() == ".pdf":
        use_page_ocr = doc_type in {"PDF-скан", "PDF смешанный"}
        if use_page_ocr:
            converters = [
                ("Постранично: текст+OCR", lambda: convert_pdf_page_by_page(file_path, tesseract_info)),
                ("Docling OCR", lambda: convert_with_docling(file_path, use_ocr=True, tesseract_info=tesseract_info)),
                ("MarkItDown", lambda: convert_with_markitdown(file_path)),
                ("PDFium text", lambda: convert_with_pdfium_text(file_path)),
            ]
        else:
            converters = [
                ("Docling", lambda: convert_with_docling(file_path, use_ocr=False, tesseract_info=tesseract_info)),
                ("MarkItDown", lambda: convert_with_markitdown(file_path)),
                ("PDFium text", lambda: convert_with_pdfium_text(file_path)),
            ]
    else:
        raise RuntimeError("Неподдерживаемый формат файла.")

    for name, converter in converters:
        try:
            converted = converter()
            if isinstance(converted, tuple):
                text, page_report = converted
            else:
                text = converted
                page_report = []
            if text and text.strip():
                return text, name, page_report
            errors.append(f"{name}: пустой результат")
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError("; ".join(errors))


def convert_with_markitdown(file_path: Path) -> str:
    def run() -> str:
        from markitdown import MarkItDown

        md = MarkItDown(enable_plugins=False)
        if hasattr(md, "convert_local"):
            result = md.convert_local(str(file_path))
        else:
            result = md.convert(str(file_path))
        return extract_result_text(result)

    return run_without_library_noise(run)


def convert_with_docling(file_path: Path, use_ocr: bool, tesseract_info: dict) -> str:
    def run() -> str:
        converter = build_docling_converter(use_ocr=use_ocr, tesseract_info=tesseract_info)
        result = converter.convert(str(file_path))
        return result.document.export_to_markdown()

    return run_without_library_noise(run)


def run_without_library_noise(action: Callable[[], str]) -> str:
    with open(os.devnull, "w", encoding="utf-8") as sink:
        with redirect_stdout(sink), redirect_stderr(sink):
            return action()


def convert_pdf_page_by_page(file_path: Path, tesseract_info: dict) -> tuple[str, list[PageOcrEntry]]:
    if not tesseract_info.get("path"):
        raise RuntimeError("Tesseract OCR не найден.")
    languages = set(tesseract_info.get("languages") or [])
    if not {"rus", "eng"}.issubset(languages):
        raise RuntimeError("Для OCR нужны языки rus и eng.")

    import pypdfium2 as pdfium

    pages_text: list[str] = []
    page_report: list[PageOcrEntry] = []
    tesseract_path = tesseract_info["path"]
    tessdata_dir = tesseract_info.get("tessdata_dir")

    with tempfile.TemporaryDirectory(prefix="pdf_ocr_") as temp_dir:
        temp_path = Path(temp_dir)
        ocr_jobs: list[tuple[int, int, Path]] = []
        with pdfium.PdfDocument(str(file_path)) as document:
            page_count = len(document)
            if page_count == 0:
                raise RuntimeError("PDF не содержит страниц.")
            for page_index in range(1, page_count + 1):
                page = document[page_index - 1]
                try:
                    page_text = extract_pdfium_page_text(page)
                    if not should_ocr_pdf_page_text(page_text):
                        pages_text.append(format_page_text(page_index, page_text))
                        page_report.append(
                            PageOcrEntry(
                                page_index=page_index,
                                source="text",
                                char_count=len(page_text.strip()),
                                warning=assess_page_text_warning(page_text, source="text"),
                            )
                        )
                        continue

                    image_path = temp_path / f"page_{page_index:04d}.png"
                    image = page.render(scale=3.0).to_pil()
                    try:
                        image.save(image_path)
                    finally:
                        image.close()
                    if is_probably_blank_image(image_path):
                        pages_text.append(format_page_text(page_index, ""))
                        page_report.append(
                            PageOcrEntry(
                                page_index=page_index,
                                source="blank",
                                char_count=0,
                                warning="Страница похожа на пустую.",
                            )
                        )
                        continue
                    preprocess_ocr_image(image_path)
                    ocr_jobs.append((page_index, page_count, image_path))
                finally:
                    page.close()

        if ocr_jobs:
            workers = choose_ocr_worker_count(len(ocr_jobs))
            print(f"  OCR страниц: {len(ocr_jobs)}. Параллельно: {workers}")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {
                    executor.submit(run_tesseract_on_image, image_path, tesseract_path, tessdata_dir): page_index
                    for page_index, _, image_path in ocr_jobs
                }
                ocr_results: dict[int, str] = {}
                for future in concurrent.futures.as_completed(future_map):
                    page_index = future_map[future]
                    print(f"  OCR страница {page_index}/{ocr_jobs[0][1]}")
                    ocr_results[page_index] = future.result().strip()
            for page_index, _, _ in ocr_jobs:
                page_text = ocr_results.get(page_index, "")
                pages_text.append(format_page_text(page_index, page_text))
                page_report.append(
                    PageOcrEntry(
                        page_index=page_index,
                        source="ocr",
                        char_count=len(page_text.strip()),
                        warning=assess_page_text_warning(page_text, source="ocr"),
                    )
                )

    pages_text.sort(key=page_number_from_markdown)
    page_report.sort(key=lambda page: page.page_index)
    result = "\n\n".join(page for page in pages_text if page.strip()).strip()
    if not result:
        raise RuntimeError("Tesseract OCR не извлёк текст.")
    return result, page_report


def should_ocr_pdf_page_text(page_text: str) -> bool:
    text = normalize_newlines(page_text).strip()
    if len(text) < PDF_TEXT_LAYER_THRESHOLD:
        return True
    return looks_like_bad_pdf_text_layer(text)


def assess_page_text_warning(page_text: str, source: str) -> str:
    text = normalize_newlines(page_text).strip()
    warnings: list[str] = []
    if not text:
        warnings.append("Текст не извлечен.")
    elif len(text) < PDF_TEXT_LAYER_THRESHOLD:
        warnings.append("Мало текста.")

    replacement_count = text.count("\uFFFD")
    if replacement_count:
        warnings.append(f"Нечитаемые символы: {replacement_count}.")

    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text)
    if source == "ocr" and len(letters) >= 100:
        cyrillic = re.findall(r"[А-Яа-яЁё]", text)
        if len(cyrillic) / len(letters) < 0.35:
            warnings.append("Низкая доля кириллицы после OCR.")

    return " ".join(warnings)


def looks_like_bad_pdf_text_layer(text: str) -> bool:
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text)
    if len(letters) < PDF_TEXT_LAYER_MIN_LETTERS_FOR_QUALITY_CHECK:
        return False

    words = re.findall(r"[A-Za-zА-Яа-яЁё]{2,}", text)
    single_tokens = re.findall(
        r"(?<![A-Za-zА-Яа-яЁё])[A-Za-zА-Яа-яЁё](?![A-Za-zА-Яа-яЁё])",
        text,
    )
    cyrillic = re.findall(r"[А-Яа-яЁё]", text)
    single_token_ratio = len(single_tokens) / max(1, len(words) + len(single_tokens))
    cyrillic_ratio = len(cyrillic) / len(letters)

    return (
        single_token_ratio >= PDF_TEXT_LAYER_BAD_SINGLE_TOKEN_RATIO
        and cyrillic_ratio < PDF_TEXT_LAYER_BAD_CYRILLIC_RATIO
    )


def configure_pillow_for_ocr(image_module) -> None:
    current_limit = getattr(image_module, "MAX_IMAGE_PIXELS", None)
    if current_limit is not None and current_limit < PIL_MAX_OCR_IMAGE_PIXELS:
        image_module.MAX_IMAGE_PIXELS = PIL_MAX_OCR_IMAGE_PIXELS


def is_probably_blank_image(image_path: Path) -> bool:
    try:
        from PIL import Image

        configure_pillow_for_ocr(Image)
        with Image.open(image_path).convert("L") as image:
            histogram = image.histogram()
            dark_pixels = sum(histogram[:245])
            total_pixels = image.width * image.height
        return total_pixels > 0 and (dark_pixels / total_pixels) < BLANK_PAGE_DARK_PIXEL_RATIO
    except Exception:
        return False


def choose_ocr_worker_count(job_count: int) -> int:
    cpu_count = os.cpu_count() or 2
    return max(1, min(MAX_OCR_WORKERS, job_count, max(1, cpu_count // 2)))


def preprocess_ocr_image(image_path: Path) -> None:
    try:
        from PIL import Image, ImageFilter, ImageOps

        configure_pillow_for_ocr(Image)
        with Image.open(image_path) as image:
            processed = ImageOps.grayscale(image)
            processed = ImageOps.autocontrast(processed, cutoff=1)
            processed = processed.filter(ImageFilter.SHARPEN)
            processed.save(image_path)
    except Exception:
        pass


def run_tesseract_on_image(image_path: Path, tesseract_path: str, tessdata_dir: str | None) -> str:
    command = [tesseract_path, str(image_path), "stdout"]
    if tessdata_dir:
        command.extend(["--tessdata-dir", tessdata_dir])
    command.extend(["-l", "rus+eng", "--psm", "6"])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Tesseract вернул ошибку.")
    return completed.stdout


def format_page_text(page_index: int, page_text: str) -> str:
    return f"## Страница {page_index}\n\n{page_text.strip()}".strip()


def page_number_from_markdown(page_text: str) -> int:
    match = re.match(r"## Страница (\d+)", page_text)
    return int(match.group(1)) if match else 0


def build_docling_converter(use_ocr: bool, tesseract_info: dict):
    from docling.document_converter import DocumentConverter

    if not use_ocr:
        return DocumentConverter()
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
        from docling.document_converter import PdfFormatOption

        options = PdfPipelineOptions()
        options.do_ocr = True
        options.ocr_options = TesseractCliOcrOptions(
            lang=["rus", "eng"],
            force_full_page_ocr=True,
            tesseract_cmd=tesseract_info.get("path") or "tesseract",
            path=tesseract_info.get("tessdata_dir"),
            psm=6,
        )
        return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    except Exception:
        return DocumentConverter()


def convert_with_pdfium_text(file_path: Path) -> str:
    import pypdfium2 as pdfium

    pages: list[str] = []
    with pdfium.PdfDocument(str(file_path)) as document:
        for page_index in range(1, len(document) + 1):
            page = document[page_index - 1]
            try:
                text = extract_pdfium_page_text(page)
                if text:
                    pages.append(f"## Страница {page_index}\n\n{text}")
            finally:
                page.close()
    return "\n\n".join(pages)


def convert_docx_direct(file_path: Path) -> str:
    with zipfile.ZipFile(file_path) as archive:
        try:
            xml_bytes = archive.read("word/document.xml")
        except KeyError as exc:
            raise RuntimeError("DOCX не содержит основного текста word/document.xml.") from exc

        root = ET.fromstring(xml_bytes)
        body = root.find(f".//{word_tag('body')}")
        if body is None:
            raise RuntimeError("В DOCX не найден основной текст.")

        blocks = extract_docx_blocks(body)
        blocks.extend(extract_docx_notes(archive, "word/footnotes.xml", "Сноски"))
        blocks.extend(extract_docx_notes(archive, "word/endnotes.xml", "Концевые сноски"))

    result = "\n\n".join(blocks).strip()
    if not result:
        raise RuntimeError("Встроенное чтение DOCX не извлекло текст.")
    return result


def word_tag(name: str) -> str:
    return f"{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{name}"


def extract_docx_blocks(container) -> list[str]:
    blocks: list[str] = []
    for child in container:
        if child.tag == word_tag("p"):
            paragraph = extract_docx_paragraph_text(child)
            if paragraph:
                blocks.append(paragraph)
        elif child.tag == word_tag("tbl"):
            table = extract_docx_table(child)
            if table:
                blocks.append(table)
    return blocks


def extract_docx_notes(archive: zipfile.ZipFile, part_name: str, title: str) -> list[str]:
    try:
        root = ET.fromstring(archive.read(part_name))
    except KeyError:
        return []

    notes: list[str] = []
    for note in root:
        note_id = note.attrib.get(word_tag("id"), "")
        if not note_id or note_id.startswith("-"):
            continue
        note_text = "\n\n".join(extract_docx_blocks(note)).strip()
        if note_text:
            notes.append(f"[{note_id}] {note_text}")

    if not notes:
        return []
    return [f"## {title}", *notes]


def extract_docx_paragraph_text(paragraph) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == word_tag("t") and node.text:
            parts.append(node.text)
        elif node.tag == word_tag("tab"):
            parts.append("\t")
        elif node.tag in {word_tag("br"), word_tag("cr")}:
            parts.append("\n")
        elif node.tag in {word_tag("footnoteReference"), word_tag("endnoteReference")}:
            note_id = node.attrib.get(word_tag("id"))
            if note_id and not note_id.startswith("-"):
                parts.append(f"[{note_id}]")
    return clean_docx_text("".join(parts))


def extract_docx_table(table) -> str:
    rows: list[list[str]] = []
    for row in table.findall(f".//{word_tag('tr')}"):
        cells: list[str] = []
        for cell in row.findall(f"./{word_tag('tc')}"):
            paragraphs = [
                extract_docx_paragraph_text(paragraph)
                for paragraph in cell.findall(f".//{word_tag('p')}")
            ]
            cell_text = " ".join(part for part in paragraphs if part)
            cells.append(escape_markdown_table_cell(cell_text))
        if any(cells):
            rows.append(cells)

    if not rows:
        return ""

    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    header = normalized[0]
    separator = ["---"] * width
    body_rows = normalized[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body_rows)
    return "\n".join(lines)


def clean_docx_text(text: str) -> str:
    text = normalize_newlines(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def escape_markdown_table_cell(text: str) -> str:
    return clean_docx_text(text).replace("|", "\\|").replace("\n", " / ")


def extract_result_text(result) -> str:
    for attr in ("text_content", "markdown", "text"):
        value = getattr(result, attr, None)
        if isinstance(value, str):
            return value
    if isinstance(result, str):
        return result
    return str(result)


def conservative_cleanup(markdown: str) -> str:
    text = normalize_newlines(markdown).strip()
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text, flags=re.UNICODE)
    text = re.sub(r"[ \t]+", " ", text)

    lines = [line.strip() for line in text.split("\n")]
    filtered: list[str] = []
    for line in lines:
        if is_probable_page_number(line):
            continue
        filtered.append(line)

    output: list[str] = []
    paragraph = ""
    for line in filtered:
        if not line:
            if paragraph:
                output.append(paragraph.strip())
                paragraph = ""
            if output and output[-1] != "":
                output.append("")
            continue
        if is_markdown_structural_line(line):
            if paragraph:
                output.append(paragraph.strip())
                paragraph = ""
            output.append(line)
            continue
        if paragraph and should_join_lines(paragraph, line):
            paragraph = f"{paragraph} {line}"
        else:
            if paragraph:
                output.append(paragraph.strip())
            paragraph = line
    if paragraph:
        output.append(paragraph.strip())

    cleaned = "\n".join(output)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def is_probable_page_number(line: str) -> bool:
    if re.fullmatch(r"(стр\.?|страница)\s*\d{1,3}(\s*из\s*\d{1,3})?", line, flags=re.IGNORECASE):
        return True
    return False


def is_markdown_structural_line(line: str) -> bool:
    return bool(
        line.startswith(("#", ">", "|"))
        or re.match(r"^[-*+]\s+", line)
        or re.match(r"^\d+[.)]\s+", line)
        or re.match(r"^-{3,}$", line)
    )


def should_join_lines(left: str, right: str) -> bool:
    if is_markdown_structural_line(left) or is_markdown_structural_line(right):
        return False
    if left.endswith((".", "!", "?", ":", ";", "»", "\"")):
        return False
    if right[:1].isupper() and len(left) > 80:
        return False
    return True


def get_tesseract_info() -> dict:
    bundled_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    bundled_tesseract = bundled_dir / "tesseract.exe"
    path = str(bundled_tesseract) if bundled_tesseract.exists() else shutil.which("tesseract")
    if not path:
        common_paths = [
            Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
            Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        ]
        for candidate in common_paths:
            if candidate.exists():
                path = str(candidate)
                break
    tessdata_path = find_tessdata_dir(bundled_dir)
    tessdata_dir = str(tessdata_path) if tessdata_path else None
    languages: list[str] = []
    tesseract_version = ""
    if path:
        os.environ["PATH"] = str(Path(path).parent) + os.pathsep + os.environ.get("PATH", "")
        if tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = tessdata_dir
        try:
            completed_version = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=15,
            )
            first_line = completed_version.stdout.splitlines()[0].strip()
            tesseract_version = first_line.replace("tesseract ", "") if first_line else ""
        except Exception:
            tesseract_version = ""
        command = [path]
        if tessdata_dir:
            command.extend(["--tessdata-dir", tessdata_dir])
        command.append("--list-langs")
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=15,
            )
            for line in completed.stdout.splitlines():
                line = line.strip()
                if line and not line.lower().startswith("list of"):
                    languages.append(line)
        except Exception:
            languages = []
    return {"path": path, "languages": languages, "tessdata_dir": tessdata_dir, "version": tesseract_version}


def find_tessdata_dir(bundled_dir: Path) -> Path | None:
    source_dir = Path(__file__).resolve().parent
    candidates = [
        bundled_dir / "tessdata",
        source_dir / "tessdata",
        source_dir.parent / "tessdata",
        source_dir.parent.parent / "tessdata",
        source_dir.parent.parent / "runtime" / "tessdata",
        Path.cwd() / "tessdata",
        Path.cwd() / "runtime" / "tessdata",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def build_problem_note(source: Path, doc_type: str, method: str, status: str, warning: str, error: str) -> str:
    return "\n".join(
        [
            f"# Требует проверки: {source.name}",
            "",
            f"- Исходный файл: `{source}`",
            f"- Тип: {doc_type}",
            f"- Метод: {method or 'не выполнено'}",
            f"- Статус: {status}",
            f"- Предупреждение: {warning or 'нет'}",
            f"- Ошибка: {error or 'нет'}",
            "",
            "Проверьте исходный документ вручную, особенно если это бумажный скан.",
            "",
        ]
    )


def write_combined_markdown_file(result_dir: Path, clean_dir: Path, results: list[ConversionResult]) -> None:
    lines = [
        "# Все документы",
        "",
        "Источник: очищенные Markdown-файлы из папки `01_markdown`.",
        "Для юридически важных мест сверяйте OCR-сканы с оригинальными PDF.",
        "",
    ]
    for index, item in enumerate(results, start=1):
        clean_path = clean_dir / item.output_name
        if not clean_path.exists():
            continue
        body = clean_path.read_text(encoding="utf-8").strip()
        lines.extend(
            [
                f"\n\n---\n\n# Документ {index}: {item.source.name}",
                "",
                f"- Тип: {item.doc_type}",
                f"- Метод: {item.method}",
                f"- Статус: {item.status}",
                f"- Качество: {item.quality_status}",
                f"- Исходный файл: `{item.source}`",
                "",
                body,
            ]
        )
    (result_dir / "00_ALL_DOCUMENTS.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_run_report_file(
    result_dir: Path,
    source_dir: Path,
    results: list[ConversionResult],
    tesseract_info: dict,
    started_at: dt.datetime,
    finished_at: dt.datetime,
) -> None:
    success_count = sum(1 for item in results if item.status == "успешно")
    review_count = sum(1 for item in results if item.status == "требует проверки")
    error_count = sum(1 for item in results if item.status == "ошибка")
    total_pages = sum(item.page_count or 0 for item in results)
    total_chars = sum(item.char_count for item in results)
    total_ocr_pages = sum(item.ocr_page_count for item in results)
    total_text_pages = sum(item.text_page_count for item in results)
    total_blank_pages = sum(item.blank_page_count for item in results)
    total_page_warnings = sum(1 for item in results for page in item.page_report if page.warning)

    tesseract_status = "не найден"
    if tesseract_info.get("path"):
        languages = ", ".join(tesseract_info.get("languages") or []) or "языки не определены"
        version_text = f", версия {tesseract_info.get('version')}" if tesseract_info.get("version") else ""
        tesseract_status = f"найден{version_text} ({languages})"

    lines = [
        "Reader report",
        "",
        f"Создан: {format_report_datetime(finished_at)}",
        f"Исходная папка: {source_dir}",
        f"Папка результата: {result_dir}",
        f"Время обработки: {format_duration(started_at, finished_at)}",
        "",
        "Итог:",
        f"- документов обработано: {len(results)}",
        f"- успешно: {success_count}",
        f"- требует проверки: {review_count}",
        f"- ошибки: {error_count}",
        f"- страниц PDF: {total_pages}",
        f"- страниц OCR: {total_ocr_pages}",
        f"- страниц прочитано текстовым слоем: {total_text_pages}",
        f"- пустых/почти пустых страниц: {total_blank_pages}",
        f"- страниц с замечаниями OCR: {total_page_warnings}",
        f"- символов извлечено: {total_chars}",
        f"- Tesseract OCR: {tesseract_status}",
        "",
        "Файлы:",
    ]

    for index, item in enumerate(results, start=1):
        lines.extend(
            [
                f"{index}. {item.source.name}",
                f"   Статус: {item.status}",
                f"   Тип: {item.doc_type}",
                f"   Метод: {item.method}",
                f"   Markdown: 01_markdown/{item.output_name}",
                f"   Страниц: {format_optional_int(item.page_count)}",
                f"   OCR страниц: {item.ocr_page_count}",
                f"   Текстовый слой: {item.text_page_count}",
                f"   Пустые страницы: {item.blank_page_count}",
                f"   Страниц с замечаниями OCR: {sum(1 for page in item.page_report if page.warning)}",
                f"   Символов: {item.char_count}",
                f"   Качество: {item.quality_status}",
                f"   Предупреждение: {item.warning or 'нет'}",
                f"   Ошибка: {item.error or 'нет'}",
                "",
            ]
        )

    (result_dir / "REPORT.txt").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_ocr_report_file(
    result_dir: Path,
    results: list[ConversionResult],
    started_at: dt.datetime,
    finished_at: dt.datetime,
) -> None:
    lines = [
        "Постраничный OCR-отчет",
        "",
        f"Создан: {format_report_datetime(finished_at)}",
        f"Время обработки: {format_duration(started_at, finished_at)}",
        "",
    ]

    page_level_results = [item for item in results if item.page_report]
    if not page_level_results:
        lines.append("Постраничный OCR не выполнялся: в обработанных файлах не было PDF-сканов или смешанных PDF.")
        (result_dir / "OCR_REPORT.txt").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return

    for item in page_level_results:
        lines.extend(
            [
                f"Файл: {item.source.name}",
                f"Тип: {item.doc_type}",
                f"Метод: {item.method}",
                f"Страниц: {format_optional_int(item.page_count)}",
                f"OCR страниц: {item.ocr_page_count}",
                f"Текстовый слой: {item.text_page_count}",
                f"Пустые страницы: {item.blank_page_count}",
                "",
                "Страницы:",
            ]
        )
        for page in item.page_report:
            warning = page.warning or "нет"
            lines.append(
                f"- стр. {page.page_index}: {format_page_source(page.source)}, "
                f"символов: {page.char_count}, замечание: {warning}"
            )
        lines.append("")

    (result_dir / "OCR_REPORT.txt").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def format_report_datetime(value: dt.datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def format_duration(started_at: dt.datetime, finished_at: dt.datetime) -> str:
    seconds = max(0, int((finished_at - started_at).total_seconds()))
    minutes, rest = divmod(seconds, 60)
    if minutes:
        return f"{minutes} мин {rest} сек"
    return f"{rest} сек"


def format_optional_int(value: int | None) -> str:
    return str(value) if value is not None else "не определено"


def format_page_source(source: str) -> str:
    if source == "ocr":
        return "OCR"
    if source == "text":
        return "текстовый слой"
    if source == "blank":
        return "пустая/почти пустая"
    return source


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def join_warning(left: str, right: str) -> str:
    if left and right:
        return f"{left} {right}"
    return left or right


def looks_like_bad_russian_ocr(text: str) -> bool:
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text)
    if len(letters) < 200:
        return False
    cyrillic = re.findall(r"[А-Яа-яЁё]", text)
    return len(cyrillic) / len(letters) < 0.35


if __name__ == "__main__":
    raise SystemExit(main())
