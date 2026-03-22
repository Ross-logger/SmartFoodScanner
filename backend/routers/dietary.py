from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import User, DietaryProfile
from backend.schemas import (
    DietaryProfileResponse, 
    DietaryProfileCreate,
    LLMIngredientExtractionRequest,
    LLMIngredientExtractionResponse
)
from backend.security import get_current_user
from backend.services.ingredients_extraction import extract_ingredients_with_llm

router = APIRouter(prefix="/dietary-profiles", tags=["dietary"])


@router.get("", response_model=DietaryProfileResponse)
def get_dietary_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's dietary profile"""
    profile = db.query(DietaryProfile).filter(
        DietaryProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        profile = DietaryProfile(
            user_id=current_user.id,
            halal=False,
            gluten_free=False,
            vegetarian=False,
            vegan=False,
            nut_free=False,
            dairy_free=False,
            use_llm_ingredient_extractor=False,
            use_mistral_ocr=False,
            use_hf_section_detection=False,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    if profile.use_llm_ingredient_extractor is None:
        profile.use_llm_ingredient_extractor = False
    if profile.use_mistral_ocr is None:
        profile.use_mistral_ocr = False
    if profile.use_hf_section_detection is None:
        profile.use_hf_section_detection = False

    return profile


@router.post("/custom")
def create_custom_dietary_profile(
    profile_data: DietaryProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update custom dietary profile"""
    profile = db.query(DietaryProfile).filter(
        DietaryProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        profile = DietaryProfile(user_id=current_user.id, **profile_data.model_dump())
        db.add(profile)
    else:
        for key, value in profile_data.model_dump().items():
            setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile


@router.post("/extract-ingredients", response_model=LLMIngredientExtractionResponse)
def extract_ingredients_llm(
    request: LLMIngredientExtractionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Extract ingredients from text using LLM.
    The LLM will identify ingredients and translate them to English.
    """
    result = extract_ingredients_with_llm(request.text)
    
    # If extraction failed due to no provider, return 503
    if not result["success"] and "No LLM providers configured" in result.get("message", ""):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service is not available. Please configure LLM settings."
        )
    
    return LLMIngredientExtractionResponse(
        ingredients=result["ingredients"],
        original_text=request.text,
        success=result["success"],
        message=result.get("message")
    )

