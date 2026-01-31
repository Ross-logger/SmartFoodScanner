"""
Barcode Scanning Service
Provides functionality to scan barcodes and retrieve product information.
"""

from backend.services.barcode.service import (
    scan_barcode,
    get_product_by_barcode,
    BarcodeResult
)

__all__ = [
    "scan_barcode",
    "get_product_by_barcode",
    "BarcodeResult"
]
