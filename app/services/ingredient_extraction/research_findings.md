# Research Findings: Ingredient Extraction Solutions

## Key Findings from Internet Research

### 1. **Ingredient-Slicer** (Python Package)
- **Purpose**: Parses unstructured recipe ingredient text into standardized format
- **Approach**: Heuristic methods, no external dependencies
- **Key Insight**: Uses structured parsing for quantities, units, and food names
- **URL**: https://pypi.org/project/ingredient-slicer/
- **Applicability**: Could be integrated for better ingredient normalization

### 2. **Open Food Facts API**
- **Purpose**: Comprehensive database of food products with ingredients
- **Approach**: API-based validation and reference
- **Key Insight**: Can validate extracted ingredients against known database
- **URL**: https://github.com/openfoodfacts
- **Applicability**: Use for ingredient validation and standardization

### 3. **ToxFox OCR Module** (GitHub)
- **Purpose**: AI-based ingredient scanning from photos
- **Approach**: EasyOCR + similarity search against ingredient database
- **Key Insight**: Uses similarity matching rather than exact matching
- **URL**: https://github.com/ki-iw/toxfox-ocr
- **Applicability**: Similar to our ML approach, validates our direction

### 4. **Ingredient-Safety-Analyzer** (GitHub)
- **Purpose**: Extracts ingredients using Tesseract OCR
- **Approach**: Image processing → OCR → Text extraction → Database lookup
- **Key Insight**: Clear separation: preprocessing, OCR, postprocessing
- **URL**: https://github.com/likhithasree2/Ingredient-Safety-Analyzer-using-Tesseract-OCR
- **Applicability**: Validates our modular architecture approach

### 5. **Open Food Facts Ingredient Detection Dataset**
- **Purpose**: Training data for ingredient list detection
- **Approach**: Annotated OCR results for model training
- **Key Insight**: Uses Google Cloud Vision OCR results
- **URL**: https://huggingface.co/datasets/openfoodfacts/ingredient-detection
- **Applicability**: Could improve our ML model training

## Best Practices Identified

### 1. **Modular Architecture**
- Separate preprocessing, OCR, and postprocessing
- Clear separation of concerns
- Easy to swap components

### 2. **Database-Backed Validation**
- Use ingredient databases for validation
- Similarity search for fuzzy matching
- Reference data for standardization

### 3. **Heuristic + ML Hybrid**
- Rule-based patterns for common cases
- ML for complex/ambiguous cases
- Fallback mechanisms

### 4. **Structured Parsing**
- Parse into structured format (name, quantity, unit)
- Normalize ingredient names
- Handle variations and synonyms

## Recommendations for Our Implementation

1. **Integrate Ingredient-Slicer** for better parsing
2. **Add Open Food Facts API** for validation
3. **Improve similarity matching** using ingredient database
4. **Add structured output** (normalized ingredient names)
5. **Implement fallback chain**: ML → Database → Heuristics


