"""
FastAPI Integration Examples for OCR Correction Models

This file shows how to integrate the OCR correction models into your FastAPI backend.
Copy the relevant code into your app/routers/scans.py or create a new router.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import the corrector you want to use
# Option 1: Hybrid (Recommended - Fast, No GPU)
from inference_hybrid import OcrCorrector

# Option 2: Seq2Seq (Good balance)
# from inference_seq2seq import OcrCorrectorSeq2Seq

# Option 3: Transformer (Best accuracy)
# from inference_transformer import OcrCorrectorTransformer


# ============================================================================
# MODELS / SCHEMAS
# ============================================================================

class OcrCorrectionRequest(BaseModel):
    """Request model for OCR correction"""
    text: str
    return_details: bool = False


class OcrCorrectionResponse(BaseModel):
    """Response model for OCR correction"""
    original: str
    corrected: str
    confidence: Optional[float] = None
    corrections: Optional[List[dict]] = None


class BatchOcrCorrectionRequest(BaseModel):
    """Request model for batch OCR correction"""
    texts: List[str]


class BatchOcrCorrectionResponse(BaseModel):
    """Response model for batch OCR correction"""
    results: List[OcrCorrectionResponse]


# ============================================================================
# ROUTER SETUP
# ============================================================================

# Create router
router = APIRouter(prefix="/ocr", tags=["OCR Correction"])

# Initialize corrector (do this once at startup)
# This should be done in your main.py or as a global variable

# Option 1: Hybrid approach (RECOMMENDED)
ocr_corrector = OcrCorrector(model_dir="ML/models/hybrid")

# Option 2: Seq2Seq
# ocr_corrector = OcrCorrectorSeq2Seq(model_dir="ML/models/seq2seq")

# Option 3: Transformer
# ocr_corrector = OcrCorrectorTransformer(model_dir="ML/models/transformer")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/correct", response_model=OcrCorrectionResponse)
async def correct_ocr_text(request: OcrCorrectionRequest):
    """
    Correct OCR errors in text
    
    Example:
        POST /ocr/correct
        {
            "text": "s0y lec1th1n",
            "return_details": true
        }
        
        Response:
        {
            "original": "s0y lec1th1n",
            "corrected": "soy lecithin",
            "confidence": 0.95,
            "corrections": [...]
        }
    """
    try:
        if request.return_details:
            result = ocr_corrector.correct_with_details(request.text)
            return OcrCorrectionResponse(**result)
        else:
            corrected = ocr_corrector.correct(request.text)
            return OcrCorrectionResponse(
                original=request.text,
                corrected=corrected
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR correction failed: {str(e)}")


@router.post("/correct/batch", response_model=BatchOcrCorrectionResponse)
async def correct_ocr_batch(request: BatchOcrCorrectionRequest):
    """
    Correct OCR errors in multiple texts
    
    Example:
        POST /ocr/correct/batch
        {
            "texts": ["s0y lec1th1n", "whey pr0te1n", "c0rn syrup"]
        }
        
        Response:
        {
            "results": [
                {"original": "s0y lec1th1n", "corrected": "soy lecithin"},
                {"original": "whey pr0te1n", "corrected": "whey protein"},
                {"original": "c0rn syrup", "corrected": "corn syrup"}
            ]
        }
    """
    try:
        corrected_texts = ocr_corrector.correct_batch(request.texts)
        
        results = [
            OcrCorrectionResponse(original=orig, corrected=corr)
            for orig, corr in zip(request.texts, corrected_texts)
        ]
        
        return BatchOcrCorrectionResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch OCR correction failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Check if OCR correction service is available"""
    return {
        "status": "healthy",
        "model_loaded": ocr_corrector.model is not None if hasattr(ocr_corrector, 'model') else True
    }


# ============================================================================
# INTEGRATION INTO EXISTING SCAN ENDPOINT
# ============================================================================

"""
To integrate into your existing scan endpoint, modify app/routers/scans.py:

from ML.inference_hybrid import OcrCorrector

# Initialize at module level
ocr_corrector = OcrCorrector(model_dir="ML/models/hybrid")

@router.post("/scan")
async def scan_product(file: UploadFile = File(...)):
    # ... existing OCR code ...
    
    # After getting raw OCR text
    raw_text = perform_ocr(image)  # Your existing OCR function
    
    # Correct OCR errors
    corrected_text = ocr_corrector.correct(raw_text)
    
    # Use corrected_text for ingredient analysis
    ingredients = parse_ingredients(corrected_text)
    
    # ... rest of your code ...
    
    return {
        "raw_ocr": raw_text,
        "corrected_ocr": corrected_text,
        "ingredients": ingredients,
        ...
    }
"""


# ============================================================================
# ALTERNATIVE: MIDDLEWARE FOR AUTOMATIC CORRECTION
# ============================================================================

class OcrCorrectionMiddleware:
    """
    Middleware to automatically correct OCR text in responses
    Use this if you want automatic correction without modifying endpoints
    """
    
    def __init__(self, corrector):
        self.corrector = corrector
    
    def correct_response_data(self, data: dict) -> dict:
        """
        Automatically correct OCR fields in response data
        """
        if isinstance(data, dict):
            # Correct common OCR field names
            ocr_fields = ['ocr_text', 'ingredients_text', 'raw_text', 'scanned_text']
            
            for field in ocr_fields:
                if field in data and isinstance(data[field], str):
                    data[f'{field}_original'] = data[field]
                    data[field] = self.corrector.correct(data[field])
            
            # Recursively process nested dicts
            for key, value in data.items():
                if isinstance(value, dict):
                    data[key] = self.correct_response_data(value)
                elif isinstance(value, list):
                    data[key] = [
                        self.correct_response_data(item) if isinstance(item, dict) else item
                        for item in value
                    ]
        
        return data


# ============================================================================
# USAGE IN MAIN.PY
# ============================================================================

"""
# Add to your main.py:

from ML.fastapi_integration import router as ocr_router
from ML.inference_hybrid import OcrCorrector

# Initialize corrector
ocr_corrector = OcrCorrector(model_dir="ML/models/hybrid")

# Include router
app.include_router(ocr_router)

# Optional: Add startup event to verify model
@app.on_event("startup")
async def startup_event():
    print("Initializing OCR correction model...")
    # Model is already loaded in the router
    print("OCR correction model ready!")
"""


# ============================================================================
# EXAMPLE: INGREDIENT LIST PROCESSING
# ============================================================================

def process_ingredient_list(raw_ocr_text: str) -> List[str]:
    """
    Process raw OCR text into clean ingredient list
    
    Args:
        raw_ocr_text: Raw OCR output from scanning
        
    Returns:
        List of clean ingredient names
    """
    # Correct OCR errors
    corrected_text = ocr_corrector.correct(raw_ocr_text)
    
    # Split into ingredients (assuming comma-separated)
    ingredients = [ing.strip() for ing in corrected_text.split(',')]
    
    # Further clean each ingredient
    cleaned_ingredients = []
    for ingredient in ingredients:
        # Remove percentages, parentheses, etc.
        cleaned = ingredient.split('(')[0].strip()
        cleaned = cleaned.split('%')[0].strip()
        
        if cleaned:
            cleaned_ingredients.append(cleaned)
    
    return cleaned_ingredients


# Example usage in scan endpoint:
"""
@router.post("/scan")
async def scan_product(file: UploadFile = File(...)):
    # Get raw OCR text
    raw_text = perform_ocr(image)
    
    # Process into clean ingredient list
    ingredients = process_ingredient_list(raw_text)
    
    return {
        "raw_ocr": raw_text,
        "ingredients": ingredients,
        "ingredient_count": len(ingredients)
    }
"""


# ============================================================================
# TESTING THE INTEGRATION
# ============================================================================

if __name__ == "__main__":
    """
    Test the OCR correction locally
    """
    print("Testing OCR Correction Integration")
    print("="*60)
    
    # Test cases
    test_cases = [
        "s0y lec1th1n",
        "whey pr0te1n",
        "m0n0s0d1um glUtamate",
        "natral flvors",
        "palm o1l, c0rn syrup, sod1um benzoate"
    ]
    
    print("\nSingle corrections:")
    for text in test_cases[:4]:
        corrected = ocr_corrector.correct(text)
        print(f"{text:40s} → {corrected}")
    
    print("\nIngredient list processing:")
    raw_list = test_cases[-1]
    ingredients = process_ingredient_list(raw_list)
    print(f"Raw: {raw_list}")
    print(f"Cleaned: {ingredients}")
    
    print("\n" + "="*60)
    print("Integration test complete!")
    print("\nTo use in FastAPI:")
    print("1. Copy relevant code to your app/routers/")
    print("2. Import and initialize the corrector")
    print("3. Use ocr_corrector.correct() in your endpoints")

