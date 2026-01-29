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
from backend.services.llm_ingredient_extractor import extract_ingredients_with_llm
from backend import settings

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
        # Create default profile
        profile = DietaryProfile(
            user_id=current_user.id,
            halal=False,
            gluten_free=False,
            vegetarian=False,
            vegan=False,
            nut_free=False,
            dairy_free=False,
            use_llm_ingredient_extractor=False
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
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
    if not settings.USE_LLM_ANALYZER:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM analyzer is not enabled. Please configure LLM settings."
        )
    
    result = extract_ingredients_with_llm(request.text)
    
    return LLMIngredientExtractionResponse(
        ingredients=result["ingredients"],
        original_text=request.text,
        success=result["success"],
        message=result.get("message")
    )

