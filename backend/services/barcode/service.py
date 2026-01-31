"""
Barcode Scanning Service
Main service for processing barcode scans and retrieving product information.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from backend.services.barcode.openfoodfacts import (
    fetch_product,
    extract_product_info,
    parse_ingredients_list,
    get_allergen_list,
    get_traces_list
)

logger = logging.getLogger(__name__)


@dataclass
class BarcodeResult:
    """Result of a barcode scan."""
    success: bool
    barcode: str
    product_name: str = ""
    brand: str = ""
    ingredients_text: str = ""
    ingredients: List[str] = field(default_factory=list)
    allergens: List[str] = field(default_factory=list)
    traces: List[str] = field(default_factory=list)
    image_url: str = ""
    nutrition_grade: str = ""
    error_message: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "barcode": self.barcode,
            "product_name": self.product_name,
            "brand": self.brand,
            "ingredients_text": self.ingredients_text,
            "ingredients": self.ingredients,
            "allergens": self.allergens,
            "traces": self.traces,
            "image_url": self.image_url,
            "nutrition_grade": self.nutrition_grade,
            "error_message": self.error_message
        }


def get_product_by_barcode(barcode: str) -> BarcodeResult:
    """
    Get product information by barcode.
    
    Args:
        barcode: The product barcode (EAN-13, UPC, etc.)
        
    Returns:
        BarcodeResult with product information or error
    """
    # Validate barcode format
    cleaned_barcode = barcode.strip()
    if not cleaned_barcode:
        return BarcodeResult(
            success=False,
            barcode=barcode,
            error_message="Barcode cannot be empty"
        )
    
    # Check if barcode contains only digits
    if not cleaned_barcode.isdigit():
        return BarcodeResult(
            success=False,
            barcode=barcode,
            error_message="Invalid barcode format. Barcode should contain only digits."
        )
    
    # Fetch product from Open Food Facts
    logger.info(f"Looking up barcode: {cleaned_barcode}")
    product_data = fetch_product(cleaned_barcode)
    
    if not product_data:
        return BarcodeResult(
            success=False,
            barcode=cleaned_barcode,
            error_message="Product not found. This barcode is not in our database."
        )
    
    # Extract product information
    product_info = extract_product_info(product_data)
    
    # Parse ingredients
    ingredients_text = product_info.get("ingredients_text", "")
    ingredients = parse_ingredients_list(ingredients_text)
    
    # Get allergens and traces
    allergens = get_allergen_list(product_data)
    traces = get_traces_list(product_data)
    
    logger.info(f"Found product: {product_info.get('product_name', 'Unknown')}")
    logger.info(f"Extracted {len(ingredients)} ingredients")
    
    return BarcodeResult(
        success=True,
        barcode=cleaned_barcode,
        product_name=product_info.get("product_name", "Unknown Product"),
        brand=product_info.get("brand", ""),
        ingredients_text=ingredients_text,
        ingredients=ingredients,
        allergens=allergens,
        traces=traces,
        image_url=product_info.get("image_url", ""),
        nutrition_grade=product_info.get("nutrition_grade", ""),
        raw_data=product_info
    )


def scan_barcode(barcode: str) -> Dict[str, Any]:
    """
    Scan a barcode and return product information.
    Convenience function that returns a dictionary.
    
    Args:
        barcode: The product barcode
        
    Returns:
        Dictionary with product information
    """
    result = get_product_by_barcode(barcode)
    return result.to_dict()
