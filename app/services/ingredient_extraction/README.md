# Ingredient Extraction Service

Ingredient extraction from OCR text using Hugging Face model.

**Uses:**
- OpenFoodFacts ingredient-detection model (Hugging Face)
- Token classification for accurate ingredient span detection

## Architecture

```
ingredient_extraction/
├── __init__.py                  # Module exports
├── hugging_face_extractor.py    # Hugging Face model extraction
├── extractor.py                 # Main extraction wrapper
├── validator.py                 # Validation logic
├── normalizer.py                # Normalization logic
└── README.md                    # This file
```

## Usage

```python
from app.services.ingredient_extraction import extract

ingredients = extract(ocr_text)
```

## How It Works

The extraction uses the `openfoodfacts/ingredient-detection` model from Hugging Face:
1. OCR text is tokenized using SentencePiece tokenization
2. Model predicts token-level labels (B-ING, I-ING, O)
3. Ingredient spans are reconstructed from token predictions
4. Handles SentencePiece subword tokenization correctly

## Testing

```python
# Test extractor
from app.services.ingredient_extraction import extract

result = extract("Ingredients: wheat flour, sugar, salt")
# Returns: ['wheat flour', 'sugar', 'salt']

# Test validator
from app.services.ingredient_extraction import IngredientValidator
validator = IngredientValidator()
valid = validator.validate(['wheat flour', 'garbage text'])
```

## Notes

- Uses Hugging Face transformers library
- Model is loaded once at module import time
- Handles SentencePiece tokenization correctly
- Returns list of ingredient strings

