import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import User, Scan, DietaryProfile
from backend.schemas import ScanResponse, UpdateIngredientsRequest, UpdateIngredientsResponse
from backend.security import get_current_user
from backend.services.ingredients_analysis import analyze_ingredients

router = APIRouter(prefix="/scans", tags=["history"])


def normalize_scan_data(scan: Scan) -> dict:
    """
    Normalize scan data to ensure ingredients and warnings are lists.
    Each ingredient entry in the list represents a single ingredient.
    """
    
    # Normalize ingredients to ensure it's a list
    ingredients = scan.ingredients
    if not isinstance(ingredients, list):
        if isinstance(ingredients, str):
            # If stored as string, split by common delimiters
            ingredients = [ing.strip() for ing in ingredients.replace(',', '\n').split('\n') if ing.strip()]
        elif ingredients is None:
            ingredients = []
        else:
            # Try to convert to list
            ingredients = list(ingredients)
    
    # Ensure each ingredient is a string
    ingredients = [str(ing).strip() for ing in ingredients if str(ing).strip()]
    
    # Normalize warnings to ensure it's a list
    warnings = scan.warnings
    if not isinstance(warnings, list):
        if isinstance(warnings, str):
            warnings = [warnings] if warnings.strip() else []
        elif warnings is None:
            warnings = []
        else:
            warnings = list(warnings)
    
    return {
        "id": scan.id,
        "user_id": scan.user_id,
        "image_path": scan.image_path,
        "barcode": scan.barcode,
        "ocr_text": scan.ocr_text,
        "corrected_text": scan.corrected_text,
        "ingredients": ingredients,
        "is_safe": scan.is_safe,
        "warnings": warnings,
        "analysis_result": scan.analysis_result,
        "created_at": scan.created_at
    }


@router.get("", response_model=List[ScanResponse])
def get_scans(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's scan history"""
    scans = db.query(Scan).filter(
        Scan.user_id == current_user.id
    ).order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
    
    # Normalize scan data to ensure proper types
    normalized_scans = [normalize_scan_data(scan) for scan in scans]
    return normalized_scans


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific scan by ID"""
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id
    ).first()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    # Normalize scan data to ensure proper types
    return normalize_scan_data(scan)


@router.put("/{scan_id}/ingredients", response_model=UpdateIngredientsResponse)
def update_scan_ingredients(
    scan_id: int,
    request: UpdateIngredientsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the ingredients list for a scan and re-run the dietary analysis.
    
    This allows users to fix OCR misspellings or add/remove ingredients,
    then get an updated safety assessment.
    """
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id
    ).first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )

    # Clean up ingredients - strip whitespace and remove empty entries
    ingredients = [ing.strip() for ing in request.ingredients if ing.strip()]

    if not ingredients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingredients list cannot be empty"
        )

    # Get user's dietary profile for re-analysis
    dietary_profile = db.query(DietaryProfile).filter(
        DietaryProfile.user_id == current_user.id
    ).first()

    # Re-run ingredient analysis with the updated list
    analysis = analyze_ingredients(ingredients, dietary_profile)

    # Update the scan record
    scan.ingredients = ingredients
    scan.is_safe = analysis["is_safe"]
    scan.warnings = analysis["warnings"]
    scan.analysis_result = analysis["analysis_result"]

    db.commit()
    db.refresh(scan)

    return UpdateIngredientsResponse(
        id=scan.id,
        ingredients=ingredients,
        is_safe=analysis["is_safe"],
        warnings=analysis["warnings"],
        analysis_result=analysis["analysis_result"]
    )

