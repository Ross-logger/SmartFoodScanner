"""
OCR Service
Extracts text from images using EasyOCR (default) or TrOCR (optional).

When TrOCR is enabled for a user:
  - EasyOCR is used for *text-region detection* (bounding boxes only).
  - Each detected region is cropped from the **original** (non-preprocessed)
    PIL image and fed to TrOCR for transformer-quality recognition.
  - The global OCR preprocessing pipeline is bypassed for TrOCR crops.
"""

import io
import logging
from PIL import Image, ImageOps
import numpy as np
import easyocr
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

# ---------------------------------------------------------------------------
# TrOCR singletons (loaded lazily on first use)
# ---------------------------------------------------------------------------
_trocr_processor = None
_trocr_model = None


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


def get_trocr_model():
    """
    Get or create TrOCR processor + model instances (lazy singleton).

    TrOCR is a VisionEncoderDecoderModel — it MUST be loaded with that class.
    AutoModelForImageTextToText adds extra pooling layers that are absent from
    the checkpoint, leaving them randomly initialised and making the decoder
    produce noise.  TrOCRProcessor is the matching processor.

    Returns:
        Tuple of (processor, model)
    """
    global _trocr_processor, _trocr_model

    if _trocr_processor is None or _trocr_model is None:
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            model_name = settings.TROCR_MODEL
            logger.info("Loading TrOCR model: %s", model_name)
            _trocr_processor = TrOCRProcessor.from_pretrained(model_name)
            _trocr_model = VisionEncoderDecoderModel.from_pretrained(model_name)
            print(f"✅ TrOCR model loaded ({model_name})")
        except Exception as e:
            raise Exception(f"Failed to load TrOCR model: {e}") from e

    return _trocr_processor, _trocr_model


def extract_text_with_trocr(original_image: Image.Image) -> str:
    """
    Extract text using EasyOCR for detection + TrOCR for recognition.

    Strategy:
    1. Run EasyOCR on the original image to detect text bounding boxes.
    2. Crop each detected region from the *original* PIL image (no preprocessing).
    3. Feed each crop to TrOCR for transformer-quality recognition.
    4. Concatenate all recognised lines.

    Args:
        original_image: PIL Image in RGB mode (no preprocessing applied).

    Returns:
        Recognised text as a newline-separated string.
    """
    import torch

    if original_image.mode != 'RGB':
        original_image = original_image.convert('RGB')

    image_array = np.array(original_image)

    # EasyOCR — detection only (bounding boxes)
    reader = get_ocr_reader()
    try:
        detection_results = _run_readtext(reader, image_array)
    except OSError as e:
        logger.warning("TrOCR: EasyOCR detection failed (%s), aborting.", e)
        return ""

    if not detection_results:
        logger.warning("TrOCR: EasyOCR found no text regions.")
        return ""

    processor, model = get_trocr_model()

    img_w, img_h = original_image.size
    text_lines: List[str] = []

    for result in detection_results:
        bbox = result[0]  # [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]

        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        x1 = max(0, int(min(xs)))
        y1 = max(0, int(min(ys)))
        x2 = min(img_w, int(max(xs)))
        y2 = min(img_h, int(max(ys)))

        if x2 <= x1 or y2 <= y1:
            continue

        # Crop from the original (non-preprocessed) image
        crop = original_image.crop((x1, y1, x2, y2))

        try:
            pixel_values = processor(images=crop, return_tensors="pt").pixel_values
            with torch.no_grad():
                generated_ids = model.generate(pixel_values)
            recognised = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
            logger.debug("TrOCR crop recognised: %r", recognised)
            if recognised:
                text_lines.append(recognised)
        except Exception as crop_err:
            logger.debug("TrOCR: skipping crop — %s", crop_err)

    result_text = '\n'.join(text_lines)
    logger.info("TrOCR recognised %d lines: %s", len(text_lines), result_text[:120])
    return result_text


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


def extract_text_from_image(image_data: bytes, use_trocr: bool = False) -> str:
    """
    Extract text from image using EasyOCR (default) or TrOCR.

    Supported image formats:
    - JPEG/JPG
    - PNG
    - GIF
    - BMP
    - TIFF
    - WebP
    - HEIC/HEIF (iPhone/iPad images)

    Args:
        image_data:  Raw image bytes.
        use_trocr:   When True, EasyOCR detects text regions and TrOCR
                     recognises each crop from the *original* (non-preprocessed)
                     image.  When False (default) the standard EasyOCR pipeline
                     runs with optional preprocessing.

    Returns:
        Extracted text as string.

    Raises:
        Exception: If OCR extraction fails.
    """
    global _ocr_reader

    try:
        # Open image and normalise to RGB
        image = Image.open(io.BytesIO(image_data))

        # Apply EXIF orientation so sideways/upside-down photos (e.g. iPhone
        # images) are upright before OCR — PIL does NOT do this automatically.
        image = ImageOps.exif_transpose(image)

        if hasattr(image, 'format') and image.format == 'HEIF':
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image = Image.frombytes('RGB', image.size, image.tobytes())
        else:
            if image.mode != 'RGB':
                image = image.convert('RGB')

        # ------------------------------------------------------------------
        # TrOCR path — use original image (no preprocessing)
        # ------------------------------------------------------------------
        if use_trocr:
            logger.info("Using TrOCR for text extraction.")
            text = extract_text_with_trocr(image)
            return text.strip()

        # ------------------------------------------------------------------
        # EasyOCR path (default)
        # ------------------------------------------------------------------
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
