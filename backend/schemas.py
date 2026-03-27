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


class UserUpdate(BaseModel):
    """Schema for updating user profile - only full_name and email are allowed"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


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
    use_llm_ingredient_extractor: bool = False
    use_mistral_ocr: bool = False
    use_hf_section_detection: bool = True
    
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
                "custom_restrictions": [],
                "use_llm_ingredient_extractor": False,
                "use_mistral_ocr": False,
                "use_hf_section_detection": True
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
    use_llm_ingredient_extractor: Optional[bool] = None
    use_mistral_ocr: Optional[bool] = None
    use_hf_section_detection: Optional[bool] = None
    
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
                "custom_restrictions": [],
                "use_llm_ingredient_extractor": False,
                "use_mistral_ocr": False,
                "use_hf_section_detection": True
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
    use_llm_ingredient_extractor: bool
    use_mistral_ocr: bool
    use_hf_section_detection: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# LLM Ingredient Extraction schemas
class LLMIngredientExtractionRequest(BaseModel):
    text: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Ingredients: Water, Sugar, Wheat Flour, Palm Oil, Salt, Emulsifier (E471), Flavoring"
            }
        }


class LLMIngredientExtractionResponse(BaseModel):
    ingredients: List[str]
    original_text: str
    success: bool
    message: Optional[str] = None


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


# Barcode Scan schemas
class BarcodeScanRequest(BaseModel):
    barcode: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "barcode": "3017620422003"
            }
        }


class BarcodeScanResponse(BaseModel):
    scan_id: int
    barcode: str
    product_name: str
    brand: Optional[str] = None
    ingredients_text: str
    ingredients: List[str]
    allergens: List[str]
    traces: List[str]
    image_url: Optional[str] = None
    is_safe: bool
    warnings: List[str]
    analysis_result: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "scan_id": 1,
                "barcode": "3017620422003",
                "product_name": "Nutella",
                "brand": "Ferrero",
                "ingredients_text": "Sugar, Palm oil, Hazelnuts...",
                "ingredients": ["Sugar", "Palm oil", "Hazelnuts"],
                "allergens": ["Milk", "Hazelnuts"],
                "traces": ["Soy"],
                "image_url": "https://example.com/image.jpg",
                "is_safe": False,
                "warnings": ["Contains hazelnuts"],
                "analysis_result": "This product contains allergens."
            }
        }


class UpdateIngredientsRequest(BaseModel):
    """Schema for updating ingredients of an existing scan"""
    ingredients: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "ingredients": ["Sugar", "Palm oil", "Hazelnuts", "Cocoa"]
            }
        }


class UpdateIngredientsResponse(BaseModel):
    """Response after updating ingredients and re-analyzing"""
    id: int
    ingredients: List[str]
    is_safe: bool
    warnings: List[str]
    analysis_result: str

    class Config:
        from_attributes = True


class BarcodeProductResponse(BaseModel):
    """Response for barcode lookup without analysis (just product info)"""
    success: bool
    barcode: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    ingredients_text: Optional[str] = None
    ingredients: List[str] = []
    allergens: List[str] = []
    traces: List[str] = []
    image_url: Optional[str] = None
    error_message: Optional[str] = None

