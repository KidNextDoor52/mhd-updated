# app/utils/ocr.py
from __future__ import annotations
from typing import List, Tuple
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from pdf2image import convert_from_path
from PyPDF2 import PdfReader

def _prep(img: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(img)
    return gray.filter(ImageFilter.SHARPEN)

def ocr_image_path(image_path: str, lang: str = "eng") -> str:
    img = Image.open(image_path)
    img = _prep(img)
    return pytesseract.image_to_string(img, lang=lang)

def pdf_native_text(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        out = []
        for p in reader.pages:
            out.append(p.extract_text() or "")
        return "\n".join(out).strip()
    except Exception:
        return ""

def ocr_pdf(pdf_path: str, dpi: int = 300, lang: str = "eng") -> Tuple[str, int]:
    pages: List[Image.Image] = convert_from_path(pdf_path, dpi=dpi)
    chunks = []
    for pg in pages:
        chunks.append(pytesseract.image_to_string(_prep(pg), lang=lang))
    return ("\n\n".join(chunks).strip(), len(pages))

def extract_text_from_pdf_or_ocr(pdf_path: str, text_min_len: int = 64) -> str:
    native = pdf_native_text(pdf_path)
    if len(native) >= text_min_len:
        return native
    txt, _ = ocr_pdf(pdf_path)
    return txt
