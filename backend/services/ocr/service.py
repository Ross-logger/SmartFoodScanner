"""
OCR Service
Extracts text from images using EasyOCR (default) or Mistral OCR (cloud API).
"""

import base64
import io
import logging
from PIL import Image, ImageOps
import numpy as np
import easyocr
import requests
from typing import List, Tuple

from backend import settings
from backend.services.ocr.preprocess import preprocess_image_for_ocr
from pillow_heif import register_heif_opener

logger = logging.getLogger(__name__)

register_heif_opener()

# ---------------------------------------------------------------------------
# EasyOCR singleton
# ---------------------------------------------------------------------------
_ocr_reader = None


def get_ocr_reader():
    """
    Get or create EasyOCR reader instance.
    Uses singleton pattern to avoid reloading models on every request.
    
    Returns:
        EasyOCR Reader instance
    """
    global _ocr_reader
    
    if _ocr_reader is None:
        try:
            # Use GPU if available, fallback to CPU
            _ocr_reader = easyocr.Reader(['en'], gpu=True)
            print("✅ EasyOCR reader initialized (GPU mode)")
        except Exception as e:
            # Fallback to CPU if GPU fails
            try:
                _ocr_reader = easyocr.Reader(['en'], gpu=False)
                print("✅ EasyOCR reader initialized (CPU mode)")
            except Exception as cpu_error:
                raise Exception(f"Failed to initialize EasyOCR: {str(cpu_error)}")
    
    return _ocr_reader


def filter_ocr_results_by_confidence(
    results: List[Tuple],
    confidence_threshold: float = 0.3
) -> List[str]:
    """
    Filter OCR results by confidence threshold.
    
    Args:
        results: List of tuples from EasyOCR (bbox, text, confidence)
        confidence_threshold: Minimum confidence value (0.0 to 1.0)
        
    Returns:
        List of filtered text strings
    """
    text_lines = []
    for result in results:
        if len(result) >= 2:
            text = result[1]
            confidence = result[2] if len(result) >= 3 else 1.0
            
            # Only include text with confidence above threshold
            if confidence >= confidence_threshold and text.strip():
                text_lines.append(text.strip())
    
    return text_lines


def _run_readtext(reader, image_array: np.ndarray):
    """Run EasyOCR readtext, re-raising any OS-level I/O errors as Python exceptions."""
    try:
        return reader.readtext(image_array)
    except OSError as e:
        raise e
    except Exception as e:
        raise e


def extract_text_with_mistral_ocr(image_data: bytes) -> str:
    """
    Send image to the Mistral OCR API and return the recognised text.

    The image bytes are base64-encoded and sent as a data-URI to the
    ``/v1/ocr`` endpoint.  The response ``pages[].markdown`` fields are
    concatenated into a single string.
    """
    api_key = settings.MISTRAL_API_KEY
    if not api_key:
        raise Exception("MISTRAL_API_KEY is not configured")

    image = Image.open(io.BytesIO(image_data))
    image = ImageOps.exif_transpose(image)
    if image.mode != "RGB":
        image = image.convert("RGB")

    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=95)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    payload = {
        "model": settings.MISTRAL_OCR_MODEL,
        "document": {
            "type": "image_url",
            "image_url": f"data:image/jpeg;base64,{b64}",
        },
    }

    resp = requests.post(
        "https://api.mistral.ai/v1/ocr",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=payload,
        timeout=60,
    )

    if resp.status_code != 200:
        logger.error("Mistral OCR API error %s: %s", resp.status_code, resp.text[:300])
        raise Exception(f"Mistral OCR API returned {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    pages = data.get("pages", [])
    text_parts = [p.get("markdown", "") for p in pages if p.get("markdown")]
    text = "\n".join(text_parts)
    logger.info("Mistral OCR returned %d pages, %d chars", len(pages), len(text))
    return text.strip()


def extract_text_from_image(image_data: bytes, use_mistral_ocr: bool = False) -> str:
    """
    Extract text from image using EasyOCR (default) or Mistral OCR.

    Supported image formats: JPEG/JPG, PNG, GIF, BMP, TIFF, WebP, HEIC/HEIF.

    Args:
        image_data:       Raw image bytes.
        use_mistral_ocr:  When True, image is sent to the Mistral OCR cloud
                          API instead of running EasyOCR locally.

    Returns:
        Extracted text as string.

    Raises:
        Exception: If OCR extraction fails.
    """
    global _ocr_reader

    if use_mistral_ocr:
        logger.info("Using Mistral OCR for text extraction.")
        return extract_text_with_mistral_ocr(image_data)

    try:
        image = Image.open(io.BytesIO(image_data))

        # Apply EXIF orientation so sideways/upside-down photos are upright.
        image = ImageOps.exif_transpose(image)

        if hasattr(image, 'format') and image.format == 'HEIF':
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image = Image.frombytes('RGB', image.size, image.tobytes())
        else:
            if image.mode != 'RGB':
                image = image.convert('RGB')

        image_array = np.array(image)

        # Automatic preprocess: contrast (CLAHE), upscale small images, cap huge ones
        if settings.OCR_PREPROCESS_ENABLED:
            image_array = preprocess_image_for_ocr(
                image_array,
                enabled=True,
                target_short_edge=settings.OCR_PREPROCESS_TARGET_SHORT_EDGE,
                max_long_edge=settings.OCR_PREPROCESS_MAX_LONG_EDGE,
            )
            logger.debug(
                "OCR preprocess applied -> shape %s",
                getattr(image_array, "shape", None),
            )

        # Get OCR reader (singleton)
        reader = get_ocr_reader()

        # Perform OCR — if the GPU backend raises an I/O error (errno 5, common with
        # Apple MPS) reset the singleton and retry on CPU so the process stays alive.
        try:
            results = _run_readtext(reader, image_array)
        except OSError as e:
            logger.warning(
                "GPU OCR failed with OS error (%s), resetting reader and retrying on CPU.",
                e,
            )
            _ocr_reader = None
            try:
                _ocr_reader = easyocr.Reader(['en'], gpu=False)
                logger.info("EasyOCR CPU fallback reader initialised.")
            except Exception as init_err:
                raise Exception(f"OCR extraction failed (CPU fallback init): {init_err}") from init_err
            try:
                results = _run_readtext(_ocr_reader, image_array)
            except Exception as cpu_err:
                raise Exception(f"OCR extraction failed (CPU fallback): {cpu_err}") from cpu_err

        # Filter by confidence if enabled
        if settings.IS_OCR_CONFIDENCE_FILTER:
            text_lines = filter_ocr_results_by_confidence(results)
        else:
            text_lines = [result[1].strip() for result in results if len(result) >= 2 and result[1].strip()]

        text = '\n'.join(text_lines)
        return text.strip()

    except Exception as e:
        raise Exception(f"OCR extraction failed: {str(e)}") from e


def extract_ingredients(text: str) -> list:
    """
    Extract ingredients from OCR text.
    
    Args:
        text: OCR text to extract ingredients from
        
    Returns:
        List of extracted ingredients
    """
    from backend.services.ingredients_extraction import extract
    
    return extract(text)
