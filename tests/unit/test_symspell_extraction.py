"""
Unit Tests for SymSpell Ingredient Extraction

Tests for the symspell_extraction module including:
- Spell correction of OCR errors
- Ingredient extraction with filtering
- E-number handling
- Edge cases and error handling
"""

import re

import pytest
from backend.services.ingredients_extraction.symspell_extraction import (
    spellcheck_ingredients,
    extract_ingredients,
    extract_ingredient_segments,
    get_e_number_name,
)


def _extract_regex_symspell(ocr_text):
    """Regex section + SymSpell; returns comma-joined string for substring assertions."""
    rows = extract_ingredient_segments(ocr_text, use_hf_section_detection=False)
    return ", ".join(rows) if rows else ""


class TestSpellcheckIngredients:
    """Tests for the spellcheck_ingredients function."""
    
    # =========================================================================
    # Basic Functionality
    # =========================================================================
    
    def test_spellcheck_simple_ingredients(self):
        """Test spell correction of simple ingredient list."""
        result = spellcheck_ingredients("water, sugar, salt")
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
    
    def test_spellcheck_with_ocr_errors(self):
        """Test spell correction of common OCR errors."""
        # Common OCR mistakes
        result = spellcheck_ingredients("watar, suger, salf")
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
    
    def test_spellcheck_compound_ingredients(self):
        """Test spell correction of compound ingredients."""
        result = spellcheck_ingredients("wheat flour, palm oil, soy lecithin")
        
        assert "wheat flour" in result
        assert "palm oil" in result
        assert "soy lecithin" in result
    
    def test_spellcheck_compound_with_errors(self):
        """Test spell correction of compound ingredients with OCR errors."""
        result = spellcheck_ingredients("wheal flour, plam oil")
        
        assert "wheat flour" in result
        assert "palm oil" in result
    
    def test_spellcheck_preserves_delimiter_format(self):
        """Test that output is comma-separated (delimiters normalized when splitting)."""
        result = spellcheck_ingredients("water; sugar; salt")

        assert result == "water, sugar, salt"
        assert ", " in result

    def test_spellcheck_skips_symspell_for_easyocr_high_confidence_segments(self):
        """Segments in the skip set are not corrected (simulates EasyOCR conf ≥ 0.9)."""
        skip = frozenset({"watar", "suger"})
        result = spellcheck_ingredients(
            "watar, suger, salf",
            easyocr_skip_symspell_normalized=skip,
        )
        assert "watar" in result
        assert "suger" in result
        assert "salt" in result

    # =========================================================================
    # E-Number Handling
    # =========================================================================
    
    def test_spellcheck_e_numbers(self):
        """Test that E-numbers are preserved."""
        result = spellcheck_ingredients("E471, E322, E150a")
        
        assert "e471" in result
        assert "e322" in result
        assert "e150a" in result
    
    def test_spellcheck_e_numbers_with_spaces(self):
        """Test E-numbers with spaces (OCR artifact)."""
        result = spellcheck_ingredients("E 471, e 322")
        
        assert "e471" in result
        assert "e322" in result
    
    def test_spellcheck_e_numbers_lowercase(self):
        """Test lowercase E-numbers."""
        result = spellcheck_ingredients("e471, e322")
        
        assert "e471" in result
        assert "e322" in result
    
    # =========================================================================
    # Edge Cases
    # =========================================================================
    
    def test_spellcheck_empty_string(self):
        """Test with empty string."""
        result = spellcheck_ingredients("")
        assert result == ""
    
    def test_spellcheck_none(self):
        """Test with None input."""
        result = spellcheck_ingredients(None)
        assert result == ""
    
    def test_spellcheck_whitespace_only(self):
        """Test with whitespace only."""
        result = spellcheck_ingredients("   \n\t   ")
        assert result == ""
    
    def test_spellcheck_single_ingredient(self):
        """Test with single ingredient."""
        result = spellcheck_ingredients("sugar")
        assert result == "sugar"
    
    def test_spellcheck_mixed_delimiters(self):
        """Test with mixed delimiters (comma and semicolon)."""
        result = spellcheck_ingredients("water, sugar; salt, flour")
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "flour" in result

    def test_spellcheck_middot_normalized_to_comma(self):
        """Test that middle dot separators are normalized to comma-separated output."""
        result = spellcheck_ingredients("water · sugar · salt")

        assert result == "water, sugar, salt"

    def test_spellcheck_newline_separated_like_hf_merge(self):
        """HF merge keeps OCR newlines between ING spans; split treats them like boundaries."""
        text = "Potatoes\nVegetable Oil\n(Sunflower/Rapeseed)\nSugar"
        result = spellcheck_ingredients(text)

        assert "potatoes" in result
        assert "vegetable oil" in result
        assert "sugar" in result
        assert ", " in result

    def test_spellcheck_extra_whitespace(self):
        """Test with extra whitespace around ingredients."""
        result = spellcheck_ingredients("  water  ,   sugar   ,  salt  ")
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result


class TestExtractIngredients:
    """Tests for the extract_ingredients function."""
    
    # =========================================================================
    # Basic Extraction
    # =========================================================================
    
    def test_extract_simple_list(self):
        """Test extraction of simple ingredient list."""
        result = _extract_regex_symspell("water, sugar, salt")
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert result.count(",") >= 2
    
    def test_extract_with_header(self):
        """Test extraction with 'Ingredients:' header."""
        text = "Ingredients: water, sugar, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
    
    def test_extract_with_ocr_errors(self):
        """Test extraction corrects OCR errors."""
        result = _extract_regex_symspell("watar, suger, salf, wheal flour")
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "wheat flour" in result
    
    def test_extract_returns_list(self):
        """API returns one comma-joined block in a list from extract_ingredients."""
        result = extract_ingredients("water, sugar", use_hf_section_detection=False)
        assert isinstance(result, list)
        assert len(result) == 1
        assert "water" in result[0]
        assert "sugar" in result[0]
        assert ", " in result[0]
    
    # =========================================================================
    # Non-Ingredient Filtering
    # =========================================================================
    
    def test_extract_filters_addresses(self):
        """Test that addresses are filtered out."""
        text = "water, sugar, Address: 123 Main St, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "address" not in result.lower()
        assert "main st" not in result.lower()
    
    def test_extract_filters_manufactured_in(self):
        """Test that 'manufactured in' text is filtered."""
        text = "water, sugar, manufactured in USA, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "manufactured" not in result.lower()
        assert "usa" not in result.lower()
    
    def test_extract_filters_distributed_by(self):
        """Test that 'distributed by' text is filtered."""
        text = "water, sugar, distributed by XYZ Corp, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "distributed" not in result.lower()
    
    def test_extract_filters_urls(self):
        """Test that URLs are filtered out."""
        text = "water, sugar, www.example.com, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "www" not in result.lower()
        assert "example" not in result.lower()
    
    def test_extract_filters_contact_info(self):
        """Test that contact info is filtered."""
        text = "water, sugar, contact: support@food.com, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "contact" not in result.lower()
        assert "@" not in result
    
    def test_extract_filters_net_weight(self):
        """Test that net weight is filtered."""
        text = "water, sugar, net weight 250g, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "net weight" not in result.lower()
        assert "250g" not in result.lower()
    
    def test_extract_filters_storage_instructions(self):
        """Test that storage instructions are filtered."""
        text = "water, sugar, store in a cool place, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "store" not in result.lower()
    
    def test_extract_filters_expiry_info(self):
        """Test that expiry info is filtered."""
        text = "water, sugar, best before 2025, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "best before" not in result.lower()
    
    # =========================================================================
    # Garbage Text Filtering
    # =========================================================================
    
    def test_extract_filters_numbers_only(self):
        """Test that number-only entries are filtered."""
        text = "water, 123, sugar, 456, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "123" not in result
        assert "456" not in result
    
    def test_extract_filters_single_characters(self):
        """Test that single characters are filtered."""
        text = "water, a, sugar, b, salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert not re.search(r",\s*a\s*,", result)
        assert not re.search(r",\s*b\s*,", result)
    
    def test_extract_filters_empty_entries(self):
        """Test that empty entries are filtered."""
        text = "water, , sugar, , salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert ", ," not in result and ",," not in result
    
    def test_extract_filters_whitespace_entries(self):
        """Test that whitespace-only entries are filtered."""
        text = "water,    , sugar,   , salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert result.count(",") >= 2
    
    # =========================================================================
    # Section Extraction
    # =========================================================================
    
    def test_extract_stops_at_manufactured(self):
        """Test extraction stops at 'Manufactured in' section."""
        text = """Ingredients: water, sugar, salt
        Manufactured in USA
        Distributed by ABC Corp"""
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert result.count(",") >= 2
    
    def test_extract_stops_at_allergen_warning(self):
        """Test extraction stops at allergen warning."""
        text = """Ingredients: water, sugar, salt
        Allergen Warning: Contains milk"""
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        # Should not include allergen warning content
        assert "allergen warning" not in result.lower()
    
    def test_extract_multiline_ingredients(self):
        """Test extraction of multi-line ingredient list."""
        text = """Ingredients: water, sugar,
        salt, wheat flour,
        palm oil, soy lecithin"""
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "wheat flour" in result
        assert "palm oil" in result
        assert "soy lecithin" in result
    
    # =========================================================================
    # E-Number Handling
    # =========================================================================
    
    def test_extract_e_numbers(self):
        """Test extraction preserves E-numbers."""
        result = _extract_regex_symspell("water, E471, sugar, E322")
        
        assert "water" in result
        assert "sugar" in result
        assert "e471" in result
        assert "e322" in result
    
    def test_extract_e_numbers_with_names(self):
        """Test extraction with E-numbers and names."""
        result = _extract_regex_symspell("water, emulsifier (E471), sugar")
        
        assert "water" in result
        assert "sugar" in result
        # Should contain the emulsifier reference
        rl = result.lower()
        assert "e471" in rl or "emulsifier" in rl
    
    # =========================================================================
    # Edge Cases
    # =========================================================================
    
    def test_extract_empty_string(self):
        """Test with empty string."""
        result = _extract_regex_symspell("")
        assert result == ""
    
    def test_extract_none(self):
        """Test with None input."""
        result = _extract_regex_symspell(None)
        assert result == ""
    
    def test_extract_whitespace_only(self):
        """Test with whitespace only."""
        result = _extract_regex_symspell("   \n\t   ")
        assert result == ""
    
    def test_extract_no_valid_ingredients(self):
        """Test with no valid ingredients."""
        result = _extract_regex_symspell("Made in USA, distributed by Corp, www.example.com")
        assert result == ""
    
    def test_extract_single_ingredient(self):
        """Test with single ingredient."""
        result = _extract_regex_symspell("sugar")
        assert result == "sugar"
    
    def test_extract_case_insensitive(self):
        """Test that extraction is case-insensitive."""
        result = _extract_regex_symspell("WATER, SUGAR, SALT")
        
        # Results should be lowercase
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result

    def test_extract_splits_on_ampersand(self):
        """Test that & is treated as delimiter (e.g., Milk & Tree Nuts)."""
        result = _extract_regex_symspell("Ingredients: milk & tree nuts, sugar")
        assert "milk" in result
        assert "tree nuts" in result
        assert "sugar" in result

    def test_extract_splits_on_and(self):
        """Test that ' and ' is treated as delimiter."""
        result = _extract_regex_symspell("water, milk and cream, salt")
        assert "water" in result
        assert "milk" in result
        assert "cream" in result
        assert "salt" in result

    def test_extract_splits_on_or(self):
        """Test that ' or ' is treated as delimiter."""
        result = _extract_regex_symspell("soy or sunflower lecithin, sugar")
        assert "sugar" in result
        rl = result.lower()
        assert "lecithin" in rl or "soy" in rl or "sunflower" in rl

    def test_extract_splits_on_middot(self):
        """EU labels often use middle dot (·) between ingredients."""
        text = (
            "Ingredients: Wheatflour (contains Gluten) · Invert Sugar Syrup · Palm Oil · Salt · "
            "Gelling Agent: Pectins (from Fruit)"
        )
        result = _extract_regex_symspell(text)
        assert "wheatflour" in result or "wheat" in result
        assert "palm oil" in result
        assert "salt" in result
        assert result.count(",") >= 3

    def test_extract_filters_allergen_warning_segments(self):
        """Test that allergen warning text is filtered out."""
        text = (
            "Ingredients: wheat, sugar, milk & tree nut walnuts . "
            "the product is being produced on the same premises where nuts are processed"
        )
        result = _extract_regex_symspell(text)
        assert "wheat" in result
        assert "sugar" in result
        assert "milk" in result
        rl = result.lower()
        assert "product is" not in rl and "premises" not in rl and "beans produced" not in rl

    def test_extract_preserves_parenthetical_content(self):
        """Test that content in parentheses stays with parent (e.g., Emulsifier (E322 and E476))."""
        result = _extract_regex_symspell("sugar, emulsifier (e322 and e476), salt")
        rl = result.lower()
        assert "emulsifier" in rl and ("e322" in rl or "e476" in rl)


class TestGetENumberName:
    """Tests for the get_e_number_name function."""
    
    def test_get_common_e_numbers(self):
        """Test lookup of common E-numbers."""
        # E471 is mono- and diglycerides
        result = get_e_number_name("E471")
        assert result is not None
        
        # E322 is lecithin
        result = get_e_number_name("E322")
        assert result is not None
    
    def test_get_e_number_lowercase(self):
        """Test lookup with lowercase E-number."""
        result = get_e_number_name("e471")
        assert result is not None
    
    def test_get_e_number_with_space(self):
        """Test lookup with space in E-number."""
        result = get_e_number_name("E 471")
        assert result is not None
    
    def test_get_invalid_e_number(self):
        """Test lookup of invalid E-number."""
        result = get_e_number_name("E999999")
        assert result is None
    
    def test_get_e_number_empty_string(self):
        """Test lookup with empty string."""
        result = get_e_number_name("")
        assert result is None
    
    def test_get_e_number_non_e_number(self):
        """Test lookup with non-E-number string."""
        result = get_e_number_name("sugar")
        assert result is None


class TestRealisticOCRScenarios:
    """Tests with realistic OCR scenarios from food labels."""
    
    def test_full_label_extraction(self):
        """Test extraction from a full food label."""
        text = """NUTRITION FACTS
        Serving Size: 30g
        Ingredients: Wheat Flour, Sugar, Palm Oil, Salt,
        Soy Lecithin (E322), Natural Flavors, Baking Powder
        Manufactured in USA
        Distributed by: ABC Foods Inc.
        www.abcfoods.com
        Net Weight: 250g
        Best Before: See packaging"""
        
        result = _extract_regex_symspell(text)
        
        # Should extract ingredients
        assert "wheat flour" in result
        assert "sugar" in result
        assert "palm oil" in result
        assert "salt" in result
        
        # Should filter non-ingredients
        rl = result.lower()
        assert "nutrition" not in rl
        assert "serving" not in rl
        assert "manufactured" not in result.lower()
        assert "www" not in result.lower()
        assert "net weight" not in result.lower()
    
    def test_ocr_with_errors(self):
        """Test extraction from OCR text with typical errors."""
        text = """Ingredients: Watar, Suger, Salf, Wheal Flour,
        Plam Oil, Soy Lecithln, Naturai Flavors"""
        
        result = _extract_regex_symspell(text)
        
        # OCR errors should be corrected
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        assert "wheat flour" in result
        assert "palm oil" in result
    
    def test_ocr_with_header_errors(self):
        """Test extraction when the header itself has OCR errors."""
        # "lngredients" is a common OCR error (lowercase L instead of I)
        text = """lngredients: Watar, Suger, Salf"""
        
        result = _extract_regex_symspell(text)
        
        # Key ingredients should still be extracted (header may be partially included)
        # Check that corrected ingredients appear somewhere in result
        result_joined = result.lower()
        assert "water" in result_joined
        assert "sugar" in result_joined
        assert "salt" in result_joined
    
    def test_mixed_language_label(self):
        """Test extraction from bilingual label."""
        text = """Ingredients: Water, Sugar, Salt
        Ingrédients: Eau, Sucre, Sel
        Made in Canada / Fabriqué au Canada"""
        
        result = _extract_regex_symspell(text)
        
        # Should extract English ingredients at minimum
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        
        # Should filter manufacturing info
        assert "canada" not in result.lower()
    
    def test_ingredients_with_percentages(self):
        """Test extraction handles percentages correctly."""
        text = "Ingredients: Water (65%), Sugar (20%), Salt (15%)"
        result = _extract_regex_symspell(text)
        
        # Should extract ingredients (percentages may be included or stripped)
        rl = result.lower()
        assert "water" in rl
        assert "sugar" in rl
        assert "salt" in rl
    
    def test_ingredients_with_parenthetical_info(self):
        """Test extraction with parenthetical information."""
        text = "water, sugar, emulsifier (soy lecithin), salt"
        result = _extract_regex_symspell(text)
        
        assert "water" in result
        assert "sugar" in result
        assert "salt" in result
        # Parenthetical info should be preserved
        rl = result.lower()
        assert "soy" in rl or "lecithin" in rl or "emulsifier" in rl


class TestSpellCorrectionAccuracy:
    """Tests for spell correction accuracy on common OCR errors."""
    
    @pytest.mark.parametrize("ocr_error,expected", [
        ("watar", "water"),
        ("suger", "sugar"),
        ("salf", "salt"),
        ("fleur", "flour"),
        ("oii", "oil"),
        ("sugr", "sugar"),
        ("watr", "water"),
    ])
    def test_common_ocr_errors(self, ocr_error, expected):
        """Test correction of common OCR errors."""
        result = spellcheck_ingredients(ocr_error)
        assert expected in result.lower()
    
    @pytest.mark.parametrize("compound,expected", [
        ("wheal flour", "wheat flour"),
        ("plam oil", "palm oil"),
        ("soy lecithln", "soy lecithin"),
        ("baking powdr", "baking powder"),
    ])
    def test_compound_ingredient_errors(self, compound, expected):
        """Test correction of compound ingredient OCR errors."""
        result = spellcheck_ingredients(compound)
        assert expected in result.lower()
    
    def test_preserves_correct_ingredients(self):
        """Test that correctly spelled ingredients are preserved."""
        correct = "water, sugar, salt, flour, oil, milk, butter, eggs"
        result = spellcheck_ingredients(correct)
        
        for ingredient in ["water", "sugar", "salt", "flour", "oil", "milk", "butter"]:
            assert ingredient in result.lower()
