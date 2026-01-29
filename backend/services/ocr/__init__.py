"""
OCR Service Module
Provides text extraction from images using EasyOCR.
"""

from backend.services.ocr.service import (
    extract_text_from_image,
    extract_ingredients,
    get_ocr_reader,
    filter_ocr_results_by_confidence,
)

__all__ = [
    'extract_text_from_image',
    'extract_ingredients',
    'get_ocr_reader',
    'filter_ocr_results_by_confidence',
]
