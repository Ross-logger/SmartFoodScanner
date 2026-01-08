import base64
import io
import os
from PIL import Image
import numpy as np
import easyocr
from typing import Optional, List, Tuple
import re

from app.config import settings
from pillow_heif import register_heif_opener
register_heif_opener()

# Global EasyOCR reader instance (singleton pattern for efficiency)
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


def extract_text_from_image(image_data: bytes) -> str:
    """
    Extract text from image using EasyOCR.
    
    Supported image formats:
    - JPEG/JPG
    - PNG
    - GIF
    - BMP
    - TIFF
    - WebP
    - HEIC/HEIF (iPhone/iPad images)
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Extracted text as string
        
    Raises:
        Exception: If OCR extraction fails
    """
    try:
        # Open and process image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert HEIF/HEIC images
        if hasattr(image, 'format') and image.format == 'HEIF':
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image = Image.frombytes('RGB', image.size, image.tobytes())
        else:
            if image.mode != 'RGB':
                image = image.convert('RGB')
        
        # Convert PIL Image to numpy array for EasyOCR
        image_array = np.array(image)
        
        # Get OCR reader (singleton)
        reader = get_ocr_reader()
        
        # Perform OCR using EasyOCR
        # EasyOCR returns list of tuples: (bbox, text, confidence)
        results = reader.readtext(image_array)
        
        # Extract text from results, filtering by confidence if enabled
        if settings.IS_OCR_CONFIDENCE_FILTER:
            text_lines = filter_ocr_results_by_confidence(results)
        else:
            # Include all results without filtering
            text_lines = [result[1].strip() for result in results if len(result) >= 2 and result[1].strip()]
        
        text = '\n'.join(text_lines)
        
        return text.strip()
    except Exception as e:
        raise Exception(f"OCR extraction failed: {str(e)}")


def correct_ocr_text(text: str) -> str:
    """
    Simple rule-based OCR correction - fix common OCR mistakes.
    
    NOTE: This function provides basic rule-based corrections for display purposes.
    The primary OCR error correction and misspelling handling is done by the
    NLP extractor during ingredient extraction, which uses fuzzy matching against
    the ingredient dictionary (896 ingredients).
    
    This function is kept for:
    - Basic text cleaning for display
    - Simple rule-based corrections
    - Backwards compatibility
    """
    if not text:
        return text
    
    # Common OCR corrections dictionary
    corrections = {
        r'\bs0\b': 'so',
        r'\bs0y\b': 'soy',
        r'\blicethin\b': 'lecithin',
        r'\bs0y licethin\b': 'soy lecithin',
        r'\bwheat\b': 'wheat',
        r'\bgluten\b': 'gluten',
        r'\bmi1k\b': 'milk',
        r'\beggs\b': 'eggs',
        r'\bpeanuts\b': 'peanuts',
        r'\btree nuts\b': 'tree nuts',
    }
    
    corrected = text
    for pattern, replacement in corrections.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    
    return corrected


def extract_ingredients(text: str) -> list:
    """
    Extract ingredients from OCR text.
    Uses maintainable ingredient extraction service.
    
    Args:
        text: OCR text to extract ingredients from
        
    Returns:
        List of extracted ingredients
    """
    from app.services.ingredient_extraction import IngredientExtractor
    
    extractor = IngredientExtractor()
    return extractor.extract(text)

