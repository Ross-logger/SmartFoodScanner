import base64
import io
import os
from PIL import Image
import easyocr
import numpy as np
from typing import Optional
import re

from pillow_heif import register_heif_opener
register_heif_opener()


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
        
        # Perform OCR using EasyOCR
        reader = easyocr.Reader(['en'], gpu=False)
        results = reader.readtext(image_array)
        
        # Extract text from results
        # EasyOCR returns list of tuples: (bbox, text, confidence)
        text_lines = [result[1] for result in results]
        text = '\n'.join(text_lines)
        
        return text.strip()
    except Exception as e:
        raise Exception(f"OCR extraction failed: {str(e)}")


def correct_ocr_text(text: str) -> str:
    """
    Simple rule-based OCR correction - fix common OCR mistakes.
    
    NOTE: This function is now used as a FALLBACK only.
    The primary OCR correction uses the ML model (ML/models/hybrid)
    which is automatically loaded in app/routers/scans.py
    
    The ML model provides:
    - 90%+ accuracy on common English ingredients
    - <1ms inference time
    - 3,610 ingredient vocabulary
    - Smart character-level error correction
    
    This rule-based function is kept for:
    - Fallback when ML model is not available
    - Backwards compatibility
    - Simple deployment scenarios
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
    Extract ingredients from text.
    This is a simple parser - in production, you'd use NLP/ML models.
    """
    if not text:
        return []
    
    # Simple extraction: look for common patterns
    # Split by common separators
    ingredients = []
    
    # Try to find ingredients list (often after "Ingredients:" or "Contains:")
    lines = text.split('\n')
    in_ingredients_section = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detect ingredients section
        if 'ingredients' in line.lower() or 'contains' in line.lower():
            in_ingredients_section = True
            # Extract ingredients from this line too
            line = re.sub(r'^.*?[:]\s*', '', line, flags=re.IGNORECASE)
        
        if in_ingredients_section or len(ingredients) == 0:
            # Split by comma, semicolon, or newline
            parts = re.split(r'[,;]', line)
            for part in parts:
                part = part.strip()
                if part and len(part) > 2:  # Minimum length
                    # Remove common prefixes/suffixes
                    part = re.sub(r'^[-•\*\d\.\s]+', '', part)
                    part = part.strip()
                    if part:
                        ingredients.append(part.lower())
    
    # If no section found, try to extract from whole text
    if not ingredients:
        # Simple word extraction (basic approach)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        ingredients = list(set(words))[:20]  # Limit to 20 unique words
    
    return ingredients[:50]  # Limit total ingredients

