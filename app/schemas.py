from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Auth schemas
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


# User schemas
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenWithUser(BaseModel):
    """Token response with user information"""
    access_token: str
    token_type: str
    user: UserResponse


# Dietary profile schemas
class DietaryProfileCreate(BaseModel):
    halal: bool = False
    gluten_free: bool = False
    vegetarian: bool = False
    vegan: bool = False
    nut_free: bool = False
    dairy_free: bool = False
    allergens: List[str] = []
    custom_restrictions: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "halal": False,
                "gluten_free": False,
                "vegetarian": False,
                "vegan": False,
                "nut_free": False,
                "dairy_free": False,
                "allergens": [],
                "custom_restrictions": []
            }
        }


class DietaryProfileUpdate(BaseModel):
    halal: Optional[bool] = None
    gluten_free: Optional[bool] = None
    vegetarian: Optional[bool] = None
    vegan: Optional[bool] = None
    nut_free: Optional[bool] = None
    dairy_free: Optional[bool] = None
    allergens: Optional[List[str]] = None
    custom_restrictions: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "halal": False,
                "gluten_free": False,
                "vegetarian": False,
                "vegan": False,
                "nut_free": False,
                "dairy_free": False,
                "allergens": [],
                "custom_restrictions": []
            }
        }


class DietaryProfileResponse(BaseModel):
    id: int
    user_id: int
    halal: bool
    gluten_free: bool
    vegetarian: bool
    vegan: bool
    nut_free: bool
    dairy_free: bool
    allergens: List[str]
    custom_restrictions: List[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Scan schemas
class ScanCreate(BaseModel):
    barcode: Optional[str] = None


class ScanResponse(BaseModel):
    id: int
    user_id: int
    image_path: Optional[str]
    barcode: Optional[str]
    ocr_text: Optional[str]
    corrected_text: Optional[str]
    ingredients: List[str]
    is_safe: Optional[bool]
    warnings: List[str]
    analysis_result: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScanOCRRequest(BaseModel):
    image_base64: Optional[str] = None


class ScanOCRResponse(BaseModel):
    ocr_text: str
    corrected_text: Optional[str] = None
    ingredients: List[str]
    is_safe: bool
    warnings: List[str]
    analysis_result: str
    scan_id: int

