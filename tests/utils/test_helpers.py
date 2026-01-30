"""
Test Helper Utilities for SmartFoodScanner

Provides functions for creating test images, synthetic data,
and other testing utilities.
"""

import io
import random
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont


def create_test_image(
    width: int = 400,
    height: int = 300,
    color: Tuple[int, int, int] = (255, 255, 255),
    format: str = "JPEG"
) -> bytes:
    """
    Create a simple test image.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        color: RGB background color
        format: Image format (JPEG, PNG, etc.)
        
    Returns:
        Image as bytes
    """
    image = Image.new("RGB", (width, height), color)
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    return buffer.read()


def create_test_image_with_text(
    text: str,
    width: int = 800,
    height: int = 600,
    font_size: int = 20,
    background_color: Tuple[int, int, int] = (255, 255, 255),
    text_color: Tuple[int, int, int] = (0, 0, 0),
    format: str = "JPEG"
) -> bytes:
    """
    Create a test image with text drawn on it.
    
    Args:
        text: Text to draw on the image
        width: Image width in pixels
        height: Image height in pixels
        font_size: Font size for the text
        background_color: RGB background color
        text_color: RGB text color
        format: Image format (JPEG, PNG, etc.)
        
    Returns:
        Image as bytes
    """
    image = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(image)
    
    # Try to use a default font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()
    
    # Draw text with word wrapping
    lines = text.split('\n')
    y_position = 20
    for line in lines:
        # Simple word wrapping
        words = line.split()
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] < width - 40:
                current_line = test_line
            else:
                if current_line:
                    draw.text((20, y_position), current_line, fill=text_color, font=font)
                    y_position += font_size + 5
                current_line = word
        if current_line:
            draw.text((20, y_position), current_line, fill=text_color, font=font)
            y_position += font_size + 5
    
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    return buffer.read()


def create_corrupted_image() -> bytes:
    """
    Create corrupted/invalid image data for error handling tests.
    
    Returns:
        Invalid image bytes
    """
    return b"This is not a valid image file content"


def create_partial_image() -> bytes:
    """
    Create a partially corrupted image (valid header but truncated).
    
    Returns:
        Partially valid image bytes
    """
    # Create valid image
    image = Image.new("RGB", (100, 100), (255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    data = buffer.read()
    # Return only first half (truncated)
    return data[:len(data)//2]


def generate_synthetic_ocr_text(
    ingredients: List[str],
    format_type: str = "comma_separated",
    add_noise: bool = False,
    noise_level: float = 0.1
) -> str:
    """
    Generate synthetic OCR text from a list of ingredients.
    
    Args:
        ingredients: List of ingredient names
        format_type: Format type ('comma_separated', 'newline', 'mixed')
        add_noise: Whether to add OCR-like noise/errors
        noise_level: Probability of character errors (0.0 to 1.0)
        
    Returns:
        Synthetic OCR text
    """
    if format_type == "comma_separated":
        text = "Ingredients: " + ", ".join(ingredients)
    elif format_type == "newline":
        text = "Ingredients:\n" + "\n".join(ingredients)
    elif format_type == "mixed":
        # Mix of commas and semicolons
        separators = [", ", "; ", ", ", " and "]
        parts = []
        for i, ing in enumerate(ingredients):
            if i < len(ingredients) - 1:
                parts.append(ing + random.choice(separators))
            else:
                parts.append(ing)
        text = "Ingredients: " + "".join(parts)
    else:
        text = "Ingredients: " + ", ".join(ingredients)
    
    if add_noise:
        text = _add_ocr_noise(text, noise_level)
    
    return text


def _add_ocr_noise(text: str, noise_level: float) -> str:
    """
    Add OCR-like noise to text.
    
    Common OCR errors:
    - Character substitutions (l->1, O->0, etc.)
    - Missing characters
    - Extra characters
    """
    substitutions = {
        'l': '1', 'I': '1', 'O': '0', 'o': '0',
        'S': '5', 's': '5', 'B': '8', 'g': '9',
        'e': 'c', 'a': 'o', 'n': 'm', 'm': 'n'
    }
    
    result = []
    for char in text:
        if random.random() < noise_level:
            # Apply random error
            error_type = random.choice(['substitute', 'delete', 'double'])
            if error_type == 'substitute' and char in substitutions:
                result.append(substitutions[char])
            elif error_type == 'delete':
                pass  # Skip character
            elif error_type == 'double':
                result.append(char)
                result.append(char)
            else:
                result.append(char)
        else:
            result.append(char)
    
    return ''.join(result)


# Sample ingredient lists for testing
SAMPLE_INGREDIENTS = {
    "simple": ["Water", "Sugar", "Salt"],
    "common": ["Water", "Sugar", "Wheat Flour", "Palm Oil", "Salt", "Yeast"],
    "with_allergens": ["Water", "Sugar", "Wheat Flour", "Milk", "Eggs", "Peanuts", "Soy Lecithin"],
    "halal_concern": ["Water", "Sugar", "Gelatin", "Pork Fat", "Natural Flavors"],
    "vegetarian_concern": ["Water", "Sugar", "Beef Extract", "Chicken Fat", "Salt"],
    "vegan_concern": ["Water", "Sugar", "Honey", "Milk Powder", "Egg Whites", "Butter"],
    "gluten_concern": ["Water", "Wheat Flour", "Barley Malt", "Rye Flour", "Oats"],
    "complex": [
        "Water", "Sugar", "Modified Corn Starch", "Hydrogenated Vegetable Oil",
        "Salt", "Mono and Diglycerides", "Natural and Artificial Flavors",
        "Sodium Caseinate", "Dipotassium Phosphate", "Carrageenan"
    ],
    "safe_for_all": ["Water", "Sugar", "Rice Flour", "Sunflower Oil", "Salt", "Yeast"],
}


def get_sample_ingredients(category: str) -> List[str]:
    """
    Get sample ingredients for a specific category.
    
    Args:
        category: Ingredient category (simple, common, with_allergens, etc.)
        
    Returns:
        List of ingredients
    """
    return SAMPLE_INGREDIENTS.get(category, SAMPLE_INGREDIENTS["simple"])


def create_dietary_profile_dict(
    halal: bool = False,
    gluten_free: bool = False,
    vegetarian: bool = False,
    vegan: bool = False,
    nut_free: bool = False,
    dairy_free: bool = False,
    allergens: Optional[List[str]] = None,
    custom_restrictions: Optional[List[str]] = None
) -> dict:
    """
    Create a dietary profile dictionary for testing.
    
    Args:
        halal: Halal dietary restriction
        gluten_free: Gluten-free dietary restriction
        vegetarian: Vegetarian dietary restriction
        vegan: Vegan dietary restriction
        nut_free: Nut-free dietary restriction
        dairy_free: Dairy-free dietary restriction
        allergens: List of custom allergens
        custom_restrictions: List of custom dietary restrictions
        
    Returns:
        Dictionary representing dietary profile
    """
    return {
        "halal": halal,
        "gluten_free": gluten_free,
        "vegetarian": vegetarian,
        "vegan": vegan,
        "nut_free": nut_free,
        "dairy_free": dairy_free,
        "allergens": allergens or [],
        "custom_restrictions": custom_restrictions or [],
    }
