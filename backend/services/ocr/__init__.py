"""
OCR Service Module
Provides text extraction from images using EasyOCR or Mistral OCR.
"""

from backend.services.ocr.service import (
    OCRResult,
    extract_ocr_from_image,
    extract_text_from_image,
    extract_ingredients,
    get_ocr_reader,
    filter_ocr_results_by_confidence,
    collect_filtered_easyocr_lines,
)

__all__ = [
    "OCRResult",
    "collect_filtered_easyocr_lines",
    "extract_ocr_from_image",
    "extract_text_from_image",
    "extract_ingredients",
    "get_ocr_reader",
    "filter_ocr_results_by_confidence",
]
