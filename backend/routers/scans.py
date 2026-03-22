import base64
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Scan, DietaryProfile
from backend.schemas import (
    ScanOCRRequest, 
    ScanOCRResponse, 
    ScanResponse,
    BarcodeScanRequest,
    BarcodeScanResponse,
    BarcodeProductResponse
)
from backend.security import get_current_user
from backend.services.ocr import extract_text_from_image, extract_ingredients
from backend.services.ingredients_analysis import analyze_ingredients
from backend.services.ingredients_extraction import extract_ingredients_with_llm
from backend.services.barcode import get_product_by_barcode
from backend import settings

router = APIRouter(prefix="/scan", tags=["scan"])

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@router.post("/ocr", response_model=ScanOCRResponse)
def scan_ocr(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload image and perform OCR with ingredient analysis"""
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Read image data
    image_data = file.file.read()
    
    if len(image_data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large"
        )
    
    # Get user's dietary profile (needed before OCR to check TrOCR preference)
    dietary_profile = db.query(DietaryProfile).filter(
        DietaryProfile.user_id == current_user.id
    ).first()

    use_trocr = bool(dietary_profile and dietary_profile.use_trocr)

    # Extract text using OCR
    try:
        ocr_text = extract_text_from_image(image_data, use_trocr=use_trocr)
        ocr_engine = "TrOCR" if use_trocr else "EasyOCR"
        print(f"OCR Text ({ocr_engine}): ", ocr_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR failed: {str(e)}"
        )
    
    # Extract ingredients — use LLM if enabled, otherwise fall back to SymSpell
    if dietary_profile and dietary_profile.use_llm_ingredient_extractor:
        # Use LLM-based extraction
        llm_result = extract_ingredients_with_llm(ocr_text)
        if llm_result["success"] and llm_result["ingredients"]:
            ingredients = llm_result["ingredients"]
            print(f"LLM Extracted Ingredients: {ingredients}")
        else:
            ingredients = extract_ingredients(ocr_text)
            print(f"Fallback to SymSpell - Extracted Ingredients: {ingredients}")
    else:

        ingredients = extract_ingredients(ocr_text)
        print(f"SymSpell Extracted Ingredients: {ingredients}")
    
    # Analyze ingredients
    analysis = analyze_ingredients(ingredients, dietary_profile)
    
    # Save image (we'll use a UUID-based filename)
    image_filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}_image.jpg"
    image_path = os.path.join(settings.UPLOAD_DIR, image_filename)
    
    with open(image_path, "wb") as f:
        f.write(image_data)
    
    # Save scan to database
    scan = Scan(
        user_id=current_user.id,
        image_path=image_path,
        ocr_text=ocr_text,
        corrected_text=ocr_text,  # No separate correction step, use OCR text directly
        ingredients=ingredients,
        is_safe=analysis["is_safe"],
        warnings=analysis["warnings"],
        analysis_result=analysis["analysis_result"]
    )
    
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    return ScanOCRResponse(
        ocr_text=ocr_text,
        corrected_text=ocr_text,  # No separate correction step, use OCR text directly
        ingredients=ingredients,
        is_safe=analysis["is_safe"],
        warnings=analysis["warnings"],
        analysis_result=analysis["analysis_result"],
        scan_id=scan.id
    )


@router.post("/barcode", response_model=BarcodeScanResponse)
def scan_barcode(
    request: BarcodeScanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scan a barcode and analyze the product ingredients.
    
    Looks up the product in Open Food Facts database, extracts ingredients,
    and analyzes them against the user's dietary profile.
    """
    barcode = request.barcode
    
    # Fetch product information from Open Food Facts
    barcode_result = get_product_by_barcode(barcode)
    
    if not barcode_result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=barcode_result.error_message or "Product not found"
        )
    
    # Get ingredients list from barcode lookup
    ingredients = barcode_result.ingredients
    print(f"Barcode scan - Product: {barcode_result.product_name}")
    print(f"Barcode scan - Extracted ingredients: {ingredients}")
    
    # If no ingredients found from barcode, return error
    if not ingredients:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ingredients information available for this product."
        )
    
    # Get user's dietary profile for analysis
    dietary_profile = db.query(DietaryProfile).filter(
        DietaryProfile.user_id == current_user.id
    ).first()
    
    # Analyze ingredients against dietary profile
    analysis = analyze_ingredients(ingredients, dietary_profile)
    
    # Add allergen warnings from barcode data
    warnings = list(analysis["warnings"])
    if barcode_result.allergens:
        for allergen in barcode_result.allergens:
            allergen_warning = f"Contains allergen: {allergen}"
            if allergen_warning not in warnings:
                warnings.append(allergen_warning)
    
    if barcode_result.traces:
        for trace in barcode_result.traces:
            trace_warning = f"May contain traces of: {trace}"
            if trace_warning not in warnings:
                warnings.append(trace_warning)
    
    # Save scan to database
    scan = Scan(
        user_id=current_user.id,
        barcode=barcode,
        ocr_text=barcode_result.ingredients_text,
        corrected_text=barcode_result.ingredients_text,
        ingredients=ingredients,
        is_safe=analysis["is_safe"] and len(warnings) == len(analysis["warnings"]),
        warnings=warnings,
        analysis_result=analysis["analysis_result"]
    )
    
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    return BarcodeScanResponse(
        scan_id=scan.id,
        barcode=barcode,
        product_name=barcode_result.product_name,
        brand=barcode_result.brand,
        ingredients_text=barcode_result.ingredients_text,
        ingredients=ingredients,
        allergens=barcode_result.allergens,
        traces=barcode_result.traces,
        image_url=barcode_result.image_url,
        is_safe=scan.is_safe,
        warnings=warnings,
        analysis_result=analysis["analysis_result"]
    )


@router.get("/barcode/{barcode}", response_model=BarcodeProductResponse)
def lookup_barcode(
    barcode: str,
    current_user: User = Depends(get_current_user)
):
    """
    Look up product information by barcode without saving or analyzing.
    Useful for previewing product info before full scan.
    """
    barcode_result = get_product_by_barcode(barcode)
    
    return BarcodeProductResponse(
        success=barcode_result.success,
        barcode=barcode_result.barcode,
        product_name=barcode_result.product_name if barcode_result.success else None,
        brand=barcode_result.brand if barcode_result.success else None,
        ingredients_text=barcode_result.ingredients_text if barcode_result.success else None,
        ingredients=barcode_result.ingredients,
        allergens=barcode_result.allergens,
        traces=barcode_result.traces,
        image_url=barcode_result.image_url if barcode_result.success else None,
        error_message=barcode_result.error_message
    )

