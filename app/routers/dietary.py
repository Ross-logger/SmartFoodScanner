from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, DietaryProfile
from app.schemas import DietaryProfileResponse, DietaryProfileCreate
from app.security import get_current_user

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
            dairy_free=False
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

