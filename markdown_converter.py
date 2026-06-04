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
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Callable


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
LOW_TEXT_THRESHOLD = 400
PDF_TEXT_LAYER_THRESHOLD = 40
MAX_OCR_WORKERS = 4
SKIP_DIR_NAMES = {".venv", "__pycache__", "tessdata"}


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

    write_combined_markdown_file(result_dir, clean_dir, results)
    print("\nГотово.")
    print(f"Папка результата: {result_dir}")
    print(f"Общий файл: {result_dir / '00_ALL_DOCUMENTS.md'}")
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
    print(f"- PyMuPDF: {package_state('fitz', 'pymupdf')}")
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
    processed_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

    try:
        raw_markdown, method = convert_file(file_path, doc_type, tesseract_info)
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

    header = build_header(file_path, processed_at, doc_type, method or "не выполнено", warning)
    clean_path = clean_dir / output_name

    clean_text = header + ("\n\n" + raw_markdown if raw_markdown else f"\n\nОшибка: {error}\n")
    if raw_markdown:
        cleaned_body = conservative_cleanup(raw_markdown)
        if cleaned_body.strip():
            clean_text = header + "\n\n" + cleaned_body.strip() + "\n"
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
        warning=warning,
        error=error,
    )


def detect_doc_type(file_path: Path) -> str:
    if file_path.suffix.lower() == ".docx":
        return "DOCX"
    if file_path.suffix.lower() != ".pdf":
        return file_path.suffix.lower().lstrip(".").upper()
    page_text_counts = get_pdf_page_text_counts(file_path)
    if not page_text_counts:
        return "PDF-скан"
    text_pages = sum(1 for count in page_text_counts if count >= PDF_TEXT_LAYER_THRESHOLD)
    if text_pages == 0:
        return "PDF-скан"
    if text_pages < len(page_text_counts):
        return "PDF смешанный"
    return "PDF с текстом"


def get_page_count(file_path: Path) -> int | None:
    if file_path.suffix.lower() != ".pdf":
        return None
    try:
        import fitz

        with fitz.open(file_path) as document:
            return document.page_count
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
    try:
        import fitz

        counts: list[int] = []
        with fitz.open(file_path) as doc:
            for page in doc:
                counts.append(len(page.get_text("text").strip()))
        return counts
    except Exception:
        return []


def convert_file(file_path: Path, doc_type: str, tesseract_info: dict) -> tuple[str, str]:
    errors: list[str] = []
    converters: list[tuple[str, Callable[[], str]]] = []

    if file_path.suffix.lower() == ".docx":
        converters = [
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
                ("PyMuPDF text", lambda: convert_with_pymupdf_text(file_path)),
            ]
        else:
            converters = [
                ("Docling", lambda: convert_with_docling(file_path, use_ocr=False, tesseract_info=tesseract_info)),
                ("MarkItDown", lambda: convert_with_markitdown(file_path)),
                ("PyMuPDF text", lambda: convert_with_pymupdf_text(file_path)),
            ]
    else:
        raise RuntimeError("Неподдерживаемый формат файла.")

    for name, converter in converters:
        try:
            text = converter()
            if text and text.strip():
                return text, name
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


def convert_pdf_page_by_page(file_path: Path, tesseract_info: dict) -> str:
    if not tesseract_info.get("path"):
        raise RuntimeError("Tesseract OCR не найден.")
    languages = set(tesseract_info.get("languages") or [])
    if not {"rus", "eng"}.issubset(languages):
        raise RuntimeError("Для OCR нужны языки rus и eng.")

    import fitz

    pages_text: list[str] = []
    tesseract_path = tesseract_info["path"]
    tessdata_dir = tesseract_info.get("tessdata_dir")

    with tempfile.TemporaryDirectory(prefix="pdf_ocr_") as temp_dir:
        temp_path = Path(temp_dir)
        ocr_jobs: list[tuple[int, int, Path]] = []
        with fitz.open(file_path) as document:
            if document.page_count == 0:
                raise RuntimeError("PDF не содержит страниц.")
            for page_index, page in enumerate(document, start=1):
                page_text = normalize_newlines(page.get_text("text")).strip()
                if len(page_text) >= PDF_TEXT_LAYER_THRESHOLD:
                    pages_text.append(format_page_text(page_index, page_text))
                    continue

                image_path = temp_path / f"page_{page_index:04d}.png"
                pixmap = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0), alpha=False)
                pixmap.save(image_path)
                preprocess_ocr_image(image_path)
                ocr_jobs.append((page_index, document.page_count, image_path))

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

    pages_text.sort(key=page_number_from_markdown)
    result = "\n\n".join(page for page in pages_text if page.strip()).strip()
    if not result:
        raise RuntimeError("Tesseract OCR не извлёк текст.")
    return result


def choose_ocr_worker_count(job_count: int) -> int:
    cpu_count = os.cpu_count() or 2
    return max(1, min(MAX_OCR_WORKERS, job_count, max(1, cpu_count // 2)))


def preprocess_ocr_image(image_path: Path) -> None:
    try:
        from PIL import Image, ImageFilter, ImageOps

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


def convert_with_pymupdf_text(file_path: Path) -> str:
    import fitz

    pages: list[str] = []
    with fitz.open(file_path) as document:
        for page_index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append(f"## Страница {page_index}\n\n{text}")
    return "\n\n".join(pages)


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
    bundled_tessdata = bundled_dir / "tessdata"
    local_tessdata = bundled_tessdata if bundled_tessdata.exists() else Path(__file__).resolve().parent / "tessdata"
    tessdata_dir = str(local_tessdata) if local_tessdata.exists() else None
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


def build_header(source: Path, processed_at: str, doc_type: str, method: str, warning: str) -> str:
    warning_line = f"warning: {warning}" if warning else "warning: нет"
    return "\n".join(
        [
            "<!--",
            f"source: {source}",
            f"processed_at: {processed_at}",
            f"document_type: {doc_type}",
            f"method: {method}",
            warning_line,
            "-->",
        ]
    )


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
