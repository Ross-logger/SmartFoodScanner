from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, DietaryProfile
from app.schemas import UserResponse, DietaryProfileCreate, DietaryProfileResponse, DietaryProfileUpdate
from app.security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.get("/profile/restrictions", response_model=DietaryProfileResponse)
def get_dietary_restrictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's dietary restrictions"""
    profile = db.query(DietaryProfile).filter(DietaryProfile.user_id == current_user.id).first()
    
    if not profile:
        # Create default profile if none exists
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


@router.patch("/profile/restrictions", response_model=DietaryProfileResponse)
def update_dietary_restrictions(
    profile_data: DietaryProfileUpdate = Body(
        ..., 
        example={
            "halal": False,
            "gluten_free": False,
            "vegetarian": False,
            "vegan": False,
            "nut_free": False,
            "dairy_free": False,
            "allergens": [],
            "custom_restrictions": None
        }
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's dietary restrictions"""
    profile = db.query(DietaryProfile).filter(DietaryProfile.user_id == current_user.id).first()
    
    if not profile:
        # Create new profile with provided fields applied over defaults
        create_data = DietaryProfileCreate(**{k: v for k, v in profile_data.model_dump(exclude_unset=True).items() if v is not None})
        profile = DietaryProfile(user_id=current_user.id, **create_data.model_dump())
        db.add(profile)
    else:
        # Partial update existing profile
        for key, value in profile_data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile

