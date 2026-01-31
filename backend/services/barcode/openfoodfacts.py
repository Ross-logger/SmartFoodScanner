"""
Open Food Facts API Integration
Fetches product information from the Open Food Facts database using barcodes.
https://world.openfoodfacts.org/
"""

import requests
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Open Food Facts API endpoint (using world for broadest coverage)
# Products are often stored in local language, but we'll extract English fields when available
OFF_API_BASE = "https://world.openfoodfacts.org/api/v2"
OFF_PRODUCT_URL = f"{OFF_API_BASE}/product"

# Request specific fields including English versions
PRODUCT_FIELDS = [
    "code", "product_name", "product_name_en", "generic_name", "generic_name_en",
    "brands", "categories", "categories_en",
    "ingredients_text", "ingredients_text_en", 
    "ingredients_text_with_allergens", "ingredients_text_with_allergens_en",
    "allergens", "allergens_tags", "traces", "traces_tags",
    "image_front_url", "image_url",
    "nutrition_grades", "nova_group", "ecoscore_grade",
    "quantity", "countries", "labels", "labels_en"
]

# Request timeout in seconds
REQUEST_TIMEOUT = 10

# User agent as per Open Food Facts API guidelines
USER_AGENT = "SmartFoodScanner/1.0 (https://github.com/smartfoodscanner)"


def fetch_product(barcode: str) -> Optional[Dict[str, Any]]:
    """
    Fetch product information from Open Food Facts API.
    
    Args:
        barcode: The product barcode (EAN-13, UPC, etc.)
        
    Returns:
        Product data dictionary or None if not found/error
    """
    try:
        url = f"{OFF_PRODUCT_URL}/{barcode}.json"
        
        # Request specific fields including English versions
        params = {
            "fields": ",".join(PRODUCT_FIELDS)
        }
        
        response = requests.get(
            url,
            params=params,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json"
            },
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if product was found
            if data.get("status") == 1 and data.get("product"):
                return data["product"]
            else:
                logger.info(f"Product not found for barcode: {barcode}")
                return None
        else:
            logger.warning(
                f"Open Food Facts API error: {response.status_code} for barcode {barcode}"
            )
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching barcode {barcode} from Open Food Facts")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching from Open Food Facts: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching barcode {barcode}: {e}")
        return None


def extract_product_info(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant product information from Open Food Facts response.
    Prefers English fields when available.
    
    Args:
        product_data: Raw product data from Open Food Facts
        
    Returns:
        Cleaned product information dictionary
    """
    # Prefer English product name, then generic, then "Unknown Product"
    product_name = (
        product_data.get("product_name_en") or 
        product_data.get("product_name") or 
        product_data.get("generic_name_en") or
        product_data.get("generic_name") or
        "Unknown Product"
    )
    
    # Prefer English ingredients text
    ingredients_text = (
        product_data.get("ingredients_text_en") or
        product_data.get("ingredients_text_with_allergens_en") or
        product_data.get("ingredients_text") or
        product_data.get("ingredients_text_with_allergens") or
        ""
    )
    
    return {
        "barcode": product_data.get("code", ""),
        "product_name": product_name,
        "brand": product_data.get("brands", ""),
        "categories": product_data.get("categories_en") or product_data.get("categories", ""),
        "ingredients_text": ingredients_text,
        "allergens": product_data.get("allergens", ""),
        "traces": product_data.get("traces", ""),
        "image_url": product_data.get("image_front_url", "") or product_data.get("image_url", ""),
        "nutrition_grade": product_data.get("nutrition_grades", ""),
        "nova_group": product_data.get("nova_group", ""),
        "ecoscore": product_data.get("ecoscore_grade", ""),
        "quantity": product_data.get("quantity", ""),
        "countries": product_data.get("countries", ""),
        "labels": product_data.get("labels_en") or product_data.get("labels", "")
    }


def parse_ingredients_list(ingredients_text: str) -> List[str]:
    """
    Parse ingredients text into a list of individual ingredients.
    
    Args:
        ingredients_text: Raw ingredients string from product
        
    Returns:
        List of cleaned ingredient names
    """
    if not ingredients_text:
        return []
    
    # Common separators in ingredient lists
    import re
    
    # Remove common prefixes
    text = ingredients_text.strip()
    prefixes = ["ingredients:", "ingredients", "contains:"]
    for prefix in prefixes:
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
    
    # Split by common delimiters
    # Ingredients are typically separated by commas, but may contain parentheses
    ingredients = []
    current = ""
    paren_depth = 0
    
    for char in text:
        if char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            ingredient = current.strip()
            if ingredient:
                ingredients.append(ingredient)
            current = ""
        else:
            current += char
    
    # Don't forget the last ingredient
    if current.strip():
        ingredients.append(current.strip())
    
    # Clean up each ingredient
    cleaned_ingredients = []
    for ing in ingredients:
        # Remove percentages like "30%"
        ing = re.sub(r'\d+(\.\d+)?%', '', ing)
        # Remove leading/trailing punctuation and whitespace
        ing = ing.strip(' .,;:')
        # Remove content in brackets if it's just numbers/percentages
        ing = re.sub(r'\([0-9%\s.,]+\)', '', ing)
        ing = ing.strip()
        
        if ing and len(ing) > 1:  # Filter out single characters
            cleaned_ingredients.append(ing)
    
    return cleaned_ingredients


def get_allergen_list(product_data: Dict[str, Any]) -> List[str]:
    """
    Extract allergens from product data.
    
    Args:
        product_data: Raw product data from Open Food Facts
        
    Returns:
        List of allergen names
    """
    allergens = []
    
    # Get allergens from allergens field
    allergens_str = product_data.get("allergens", "")
    if allergens_str:
        # Format is usually "en:gluten,en:milk"
        for allergen in allergens_str.split(","):
            # Remove language prefix (e.g., "en:")
            clean = allergen.split(":")[-1].strip()
            if clean:
                allergens.append(clean.title())
    
    # Also check allergens_tags
    allergens_tags = product_data.get("allergens_tags", [])
    for tag in allergens_tags:
        clean = tag.split(":")[-1].strip().replace("-", " ")
        if clean and clean.title() not in allergens:
            allergens.append(clean.title())
    
    return allergens


def get_traces_list(product_data: Dict[str, Any]) -> List[str]:
    """
    Extract traces/may contain from product data.
    
    Args:
        product_data: Raw product data from Open Food Facts
        
    Returns:
        List of trace ingredient names
    """
    traces = []
    
    traces_str = product_data.get("traces", "")
    if traces_str:
        for trace in traces_str.split(","):
            clean = trace.split(":")[-1].strip()
            if clean:
                traces.append(clean.title())
    
    traces_tags = product_data.get("traces_tags", [])
    for tag in traces_tags:
        clean = tag.split(":")[-1].strip().replace("-", " ")
        if clean and clean.title() not in traces:
            traces.append(clean.title())
    
    return traces
