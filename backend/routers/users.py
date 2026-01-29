from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, DietaryProfile
from backend.schemas import UserResponse, UserUpdate, DietaryProfileCreate, DietaryProfileResponse, DietaryProfileUpdate
from backend.security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile - only full_name and email can be changed"""
    # Check if email is being updated and if it's already taken
    if user_data.email and user_data.email != current_user.email:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Update allowed fields only
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.email is not None:
        current_user.email = user_data.email
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


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

