# Ingredient Extraction Service

Scalable and maintainable ingredient extraction from OCR text.

**Based on research of existing solutions:**
- Ingredient-Slicer (Python package)
- Open Food Facts API patterns
- ToxFox OCR Module approach
- Ingredient-Safety-Analyzer best practices
- Production systems research

See `research_findings.md` for detailed research notes.

## Architecture

```
ingredient_extraction/
├── __init__.py          # Module exports
├── config.py            # Configuration (patterns, settings)
├── extractor.py         # Main extraction logic
├── validator.py         # Validation logic
└── README.md           # This file
```

## Design Principles

1. **Configuration-Driven**: All patterns and settings are in `config.py`
2. **Separation of Concerns**: Extraction, validation, and configuration are separate
3. **Extensible**: Easy to add new patterns or modify behavior
4. **Testable**: Each component can be tested independently
5. **Maintainable**: Clear structure, no hardcoding

## Usage

```python
from app.services.ingredient_extraction import IngredientExtractor

extractor = IngredientExtractor()
ingredients = extractor.extract(ocr_text)
```

## Configuration

All patterns and settings are in `config.py`:

- **START_PATTERNS**: Patterns that indicate start of ingredients section
- **STOP_PATTERNS**: Patterns that indicate end of ingredients section
- **COMPOUND_PATTERNS**: Multi-word ingredients to keep together
- **GARBAGE_PATTERNS**: Patterns to filter out
- **VALIDATION_PATTERNS**: Patterns for ingredient validation

### Adding New Patterns

To add new patterns, simply update `config.py`:

```python
# In config.py
START_PATTERNS.append(r'\bnew_pattern\b')
STOP_PATTERNS.append(r'\bend_pattern\b')
```

### Loading from JSON (Future)

Configuration can be loaded from JSON for dynamic updates:

```python
from app.services.ingredient_extraction.config import IngredientExtractionConfig
from pathlib import Path

config = IngredientExtractionConfig.load_from_json(Path('config.json'))
extractor = IngredientExtractor(config)
```

## Extending the Service

### Adding New Extraction Logic

1. Add new method to `IngredientExtractor` class
2. Update `extract()` method to use new logic
3. Add configuration if needed

### Adding New Validation Rules

1. Update `VALIDATION_PATTERNS` in `config.py`
2. Or add new method to `IngredientValidator` class

## Testing

Each component can be tested independently:

```python
# Test extractor
from app.services.ingredient_extraction import IngredientExtractor
extractor = IngredientExtractor()
result = extractor.extract(test_text)

# Test validator
from app.services.ingredient_extraction import IngredientValidator
validator = IngredientValidator()
valid = validator.validate(['wheat flour', 'garbage text'])
```

## Maintenance

- **Patterns**: Update `config.py` when new patterns are discovered
- **Logic**: Modify `extractor.py` or `validator.py` for behavior changes
- **Settings**: Adjust constants in `config.py` for thresholds

## Notes

- All patterns use regex for flexibility
- ML model integration is optional (falls back gracefully)
- Configuration is class-based for easy extension
- No hardcoded values in extraction logic

