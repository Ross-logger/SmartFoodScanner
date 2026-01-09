import base64
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Scan, DietaryProfile
from app.schemas import ScanOCRRequest, ScanOCRResponse, ScanResponse
from app.security import get_current_user
from app.services.ocr import extract_text_from_image, extract_ingredients
from app.services.analysis import analyze_ingredients
from app.config import settings

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
    
    # Extract text using OCR
    try:
        ocr_text = extract_text_from_image(image_data)
        print("OCR Text: ", ocr_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR failed: {str(e)}"
        )
    
    # Extract ingredients using Hugging Face model
    # The model handles OCR errors and tokenization automatically
    ingredients = extract_ingredients(ocr_text)
    
    # Get user's dietary profile
    dietary_profile = db.query(DietaryProfile).filter(
        DietaryProfile.user_id == current_user.id
    ).first()
    
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


@router.post("/barcode", response_model=ScanResponse)
def scan_barcode(
    barcode: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Scan barcode (placeholder - would integrate with barcode API)"""
    
    # In a real implementation, you'd fetch product info from a barcode API
    # For now, just create a scan record with the barcode
    
    scan = Scan(
        user_id=current_user.id,
        barcode=barcode,
        ocr_text=f"Barcode: {barcode}",
        ingredients=[],
        is_safe=True,
        analysis_result="Barcode scanned. Product information not available."
    )
    
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    return scan

