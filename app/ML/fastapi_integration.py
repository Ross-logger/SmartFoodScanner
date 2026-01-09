"""
FastAPI Integration Examples for OCR Correction Models

This file shows how to integrate the OCR correction models into your FastAPI backend.
Copy the relevant code into your app/routers/scans.py or create a new router.
"""

from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import the corrector you want to use
# Option 1: Hybrid (Recommended - Fast, No GPU)
from app.ML.inference_hybrid import OcrCorrector

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
# Get the model directory path relative to this file
_model_dir = Path(__file__).parent / "models" / "hybrid"
ocr_corrector = OcrCorrector(model_dir=str(_model_dir))

# Option 2: Seq2Seq
# from app.ML.inference_seq2seq import OcrCorrectorSeq2Seq
# _model_dir = Path(__file__).parent / "models" / "seq2seq"
# ocr_corrector = OcrCorrectorSeq2Seq(model_dir=str(_model_dir))

# Option 3: Transformer
# from app.ML.inference_transformer import OcrCorrectorTransformer
# _model_dir = Path(__file__).parent / "models" / "transformer"
# ocr_corrector = OcrCorrectorTransformer(model_dir=str(_model_dir))


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

from app.ML.inference_hybrid import OcrCorrector
from pathlib import Path

# Initialize at module level
_model_dir = Path(__file__).parent.parent / "ML" / "models" / "hybrid"
ocr_corrector = OcrCorrector(model_dir=str(_model_dir))

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