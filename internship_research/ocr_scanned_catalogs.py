from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

import fitz
from winsdk.windows.graphics.imaging import BitmapAlphaMode, BitmapDecoder, BitmapPixelFormat
from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.storage import FileAccessMode, StorageFile


ROOT = Path(__file__).resolve().parent
PDF_DIR = Path(r"C:\Users\arvin\Downloads\OneDrive_1_6-10-2026")
TMP_DIR = ROOT / "_ocr_tmp"
TMP_DIR.mkdir(exist_ok=True)

SCANNED_PDFS = {
    "2022": PDF_DIR / "Job Fair CAtalog June 2022.pdf",
    "2023": PDF_DIR / "Job Fair Catalog June 2023.pdf",
    "2024": PDF_DIR / "Job Fair Catalog June 2024.pdf",
}


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")


async def ocr_image(path: Path, engine: OcrEngine) -> tuple[str, list[dict[str, object]]]:
    image_file = await StorageFile.get_file_from_path_async(str(path))
    stream = await image_file.open_async(FileAccessMode.READ)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async(
        BitmapPixelFormat.BGRA8,
        BitmapAlphaMode.PREMULTIPLIED,
    )
    result = await engine.recognize_async(bitmap)
    lines = []
    for line in result.lines:
        rects = [word.bounding_rect for word in line.words]
        if rects:
            left = min(rect.x for rect in rects)
            top = min(rect.y for rect in rects)
            right = max(rect.x + rect.width for rect in rects)
            bottom = max(rect.y + rect.height for rect in rects)
        else:
            left = top = right = bottom = 0
        lines.append(
            {
                "text": line.text,
                "left": round(float(left), 2),
                "top": round(float(top), 2),
                "right": round(float(right), 2),
                "bottom": round(float(bottom), 2),
            }
        )
    return "\n".join(line["text"] for line in lines), lines


def render_page(doc: fitz.Document, page_index: int, output_path: Path, scale: float) -> None:
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    pix.save(output_path)


def load_existing(json_path: Path) -> dict[int, dict[str, object]]:
    if not json_path.exists():
        return {}
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return {int(page["page"]): page for page in data.get("pages", [])}


def write_outputs(year: str, pdf_path: Path, pages: dict[int, dict[str, object]]) -> None:
    ordered = [pages[i] for i in sorted(pages)]
    json_path = ROOT / f"{slugify(pdf_path.stem)}.ocr.pages.json"
    txt_path = ROOT / f"{slugify(pdf_path.stem)}.ocr.txt"
    json_path.write_text(
        json.dumps({"year": year, "source": str(pdf_path), "pages": ordered}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    txt_path.write_text(
        "\n".join(f"\n\n===== PAGE {page['page']} =====\n{page['text']}" for page in ordered),
        encoding="utf-8",
    )


async def process_pdf(year: str, pdf_path: Path, start: int | None, end: int | None, scale: float, force: bool) -> None:
    json_path = ROOT / f"{slugify(pdf_path.stem)}.ocr.pages.json"
    pages = load_existing(json_path)
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("Windows OCR engine is unavailable for the current user profile language.")

    doc = fitz.open(pdf_path)
    first = max(1, start or 1)
    last = min(len(doc), end or len(doc))
    for page_number in range(first, last + 1):
        if page_number in pages and not force:
            print(f"{year} page {page_number}/{len(doc)} skipped")
            continue
        image_path = TMP_DIR / f"{slugify(pdf_path.stem)}_p{page_number}.png"
        render_page(doc, page_number - 1, image_path, scale)
        text, lines = await ocr_image(image_path, engine)
        try:
            image_path.unlink()
        except OSError:
            pass
        pages[page_number] = {"page": page_number, "chars": len(text), "text": text, "lines": lines}
        write_outputs(year, pdf_path, pages)
        print(f"{year} page {page_number}/{len(doc)} chars={len(text)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", choices=sorted(SCANNED_PDFS), required=True)
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    parser.add_argument("--scale", type=float, default=4.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    asyncio.run(process_pdf(args.year, SCANNED_PDFS[args.year], args.start, args.end, args.scale, args.force))


if __name__ == "__main__":
    main()
