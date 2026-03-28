import base64
import re
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
from backend.services.ocr import extract_ocr_from_image
from backend.services.ocr.easyocr_confidence import build_easyocr_skip_symspell_normalized_keys
from backend.services.ingredients_extraction.symspell_extraction import extract_ingredients
from backend.services.ingredients_analysis import analyze_ingredients
from backend.services.ingredients_extraction import extract_ingredients_with_llm
from backend.services.barcode import get_product_by_barcode
from backend import settings

router = APIRouter(prefix="/scan", tags=["scan"])


def _normalize_llm_ingredients(ingredients: list) -> list:
    """Strip optional ``Ingredients:`` prefix from LLM strings; return a flat list."""
    if not ingredients:
        return []
    out = []
    for raw in ingredients:
        s = str(raw).strip()
        if not s:
            continue
        m = re.match(r"^\s*ingredients\s*:\s*(.*)$", s, re.I | re.DOTALL)
        if m:
            s = m.group(1).strip()
        if s:
            out.append(s)
    return out


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
    
    # Get user's dietary profile
    dietary_profile = db.query(DietaryProfile).filter(
        DietaryProfile.user_id == current_user.id
    ).first()

    use_mistral_ocr = bool(dietary_profile and dietary_profile.use_mistral_ocr)

    # Extract text using OCR (EasyOCR yields per-line confidences for SymSpell skip)
    try:
        ocr_result = extract_ocr_from_image(image_data, use_mistral_ocr=use_mistral_ocr)
        ocr_text = ocr_result.text
        ocr_engine = "Mistral OCR" if use_mistral_ocr else "EasyOCR"
        print(f"OCR Text ({ocr_engine}): ", ocr_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR failed: {str(e)}"
        )

    corrected_text = ocr_text
    ingredients = []

    def _symspell_fallback(label: str) -> list:
        easyocr_skip = None
        if ocr_result.easyocr_lines:
            easyocr_skip = build_easyocr_skip_symspell_normalized_keys(
                ocr_result.easyocr_lines,
                min_confidence=settings.EASYOCR_SKIP_SYMSPELL_MIN_CONFIDENCE,
            )
        result = extract_ingredients(ocr_text, easyocr_skip_symspell_normalized=easyocr_skip)
        print(f"{label}: {result}")
        return result

    if dietary_profile and dietary_profile.use_llm_ingredient_extractor:
        # --- LLM extraction ---
        llm_result = extract_ingredients_with_llm(ocr_text)
        if llm_result["success"] and llm_result["ingredients"]:
            ingredients = _normalize_llm_ingredients(llm_result["ingredients"])
            print(f"LLM Extracted Ingredients: {ingredients}")
        else:
            ingredients = _symspell_fallback("LLM failed – fallback to SymSpell")

    elif ocr_result.easyocr_raw_results and not use_mistral_ocr:
        # --- Box classifier extraction (default when LLM is off) ---
        try:
            from backend.services.ingredients_extraction.ingredient_box_classifier import classify_boxes, extract_ingredients_from_boxes
            from backend.services.ingredients_extraction.ocr_corrector import correct_ingredient_list
            from backend.services.ingredients_extraction.utils import split_ingredients_text

            df_boxes = classify_boxes(ocr_result.easyocr_raw_results)
            merged_text = extract_ingredients_from_boxes(df_boxes)

            if merged_text.strip():
                corrected_text = merged_text
                candidates = split_ingredients_text(merged_text)
                ingredients_list = correct_ingredient_list(
                    candidates,
                    use_ocr_corrector=settings.USE_OCR_CORRECTOR,
                )
                if ingredients_list:
                    ingredients = [", ".join(ingredients_list)]
                    print(f"Box classifier – merged text: {merged_text[:200]}")
                    print(f"Box classifier – corrected ingredients: {ingredients}")

            if not ingredients:
                ingredients = _symspell_fallback("Box classifier produced nothing – fallback to SymSpell")

        except Exception as e:
            print(f"Box classifier failed ({e}), falling back to SymSpell")
            ingredients = _symspell_fallback("Box classifier error – fallback to SymSpell")

    else:
        # --- Mistral OCR path: no EasyOCR boxes available ---
        ingredients = _symspell_fallback("Extracted Ingredients (regex section + SymSpell)")

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
        corrected_text=corrected_text,
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
        corrected_text=corrected_text,
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

