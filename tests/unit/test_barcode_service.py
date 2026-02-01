"""
Unit Tests for Barcode Scanning Service

Tests for barcode lookup, product information extraction, and data parsing.
"""

import pytest
from unittest.mock import patch, MagicMock
import requests

from backend.services.barcode.service import (
    BarcodeResult,
    get_product_by_barcode,
    scan_barcode,
)
from backend.services.barcode.openfoodfacts import (
    fetch_product,
    extract_product_info,
    parse_ingredients_list,
    get_allergen_list,
    get_traces_list,
    OFF_PRODUCT_URL,
    USER_AGENT,
)


# =============================================================================
# TEST DATA
# =============================================================================

SAMPLE_PRODUCT_DATA = {
    "code": "5000159407236",
    "product_name": "Cadbury Dairy Milk",
    "product_name_en": "Cadbury Dairy Milk Chocolate",
    "brands": "Cadbury",
    "categories": "Chocolates",
    "categories_en": "Chocolates, Milk chocolates",
    "ingredients_text": "Sugar, Cocoa butter, Milk, Cocoa mass",
    "ingredients_text_en": "Sugar, Cocoa butter, Whole milk powder, Cocoa mass, Emulsifier (E442)",
    "allergens": "en:milk",
    "allergens_tags": ["en:milk"],
    "traces": "en:nuts,en:soybeans",
    "traces_tags": ["en:nuts", "en:soybeans"],
    "image_front_url": "https://images.openfoodfacts.org/images/products/123.jpg",
    "nutrition_grades": "d",
    "nova_group": 4,
    "ecoscore_grade": "c",
    "quantity": "100g",
    "countries": "United Kingdom",
    "labels": "No artificial colors",
}

SAMPLE_API_RESPONSE_SUCCESS = {
    "status": 1,
    "product": SAMPLE_PRODUCT_DATA,
}

SAMPLE_API_RESPONSE_NOT_FOUND = {
    "status": 0,
    "status_verbose": "product not found",
}


# =============================================================================
# TESTS FOR BarcodeResult DATACLASS
# =============================================================================

class TestBarcodeResult:
    """Tests for the BarcodeResult dataclass."""

    def test_barcode_result_creation_success(self):
        """Test creating a successful barcode result."""
        result = BarcodeResult(
            success=True,
            barcode="1234567890123",
            product_name="Test Product",
            brand="Test Brand",
            ingredients_text="Water, Sugar, Salt",
            ingredients=["Water", "Sugar", "Salt"],
            allergens=["Milk"],
            traces=["Nuts"],
            image_url="https://example.com/image.jpg",
            nutrition_grade="a",
        )

        assert result.success == True
        assert result.barcode == "1234567890123"
        assert result.product_name == "Test Product"
        assert result.brand == "Test Brand"
        assert result.ingredients == ["Water", "Sugar", "Salt"]
        assert result.allergens == ["Milk"]
        assert result.traces == ["Nuts"]
        assert result.error_message is None

    def test_barcode_result_creation_failure(self):
        """Test creating a failed barcode result."""
        result = BarcodeResult(
            success=False,
            barcode="invalid",
            error_message="Product not found",
        )

        assert result.success == False
        assert result.barcode == "invalid"
        assert result.error_message == "Product not found"
        assert result.product_name == ""
        assert result.ingredients == []

    def test_barcode_result_default_values(self):
        """Test default values in BarcodeResult."""
        result = BarcodeResult(success=True, barcode="123")

        assert result.product_name == ""
        assert result.brand == ""
        assert result.ingredients_text == ""
        assert result.ingredients == []
        assert result.allergens == []
        assert result.traces == []
        assert result.image_url == ""
        assert result.nutrition_grade == ""
        assert result.error_message is None
        assert result.raw_data is None

    def test_barcode_result_to_dict(self):
        """Test BarcodeResult to_dict method."""
        result = BarcodeResult(
            success=True,
            barcode="1234567890123",
            product_name="Test Product",
            brand="Test Brand",
            ingredients_text="Water, Sugar",
            ingredients=["Water", "Sugar"],
            allergens=["Milk"],
            traces=["Nuts"],
            image_url="https://example.com/image.jpg",
            nutrition_grade="b",
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["success"] == True
        assert result_dict["barcode"] == "1234567890123"
        assert result_dict["product_name"] == "Test Product"
        assert result_dict["brand"] == "Test Brand"
        assert result_dict["ingredients"] == ["Water", "Sugar"]
        assert result_dict["allergens"] == ["Milk"]
        assert result_dict["traces"] == ["Nuts"]
        assert "raw_data" not in result_dict  # raw_data should not be in dict

    def test_barcode_result_to_dict_with_error(self):
        """Test to_dict with error message."""
        result = BarcodeResult(
            success=False,
            barcode="invalid",
            error_message="Invalid barcode format",
        )

        result_dict = result.to_dict()

        assert result_dict["success"] == False
        assert result_dict["error_message"] == "Invalid barcode format"


# =============================================================================
# TESTS FOR get_product_by_barcode
# =============================================================================

class TestGetProductByBarcode:
    """Tests for the get_product_by_barcode function."""

    def test_empty_barcode(self):
        """Test with empty barcode."""
        result = get_product_by_barcode("")

        assert result.success == False
        assert "empty" in result.error_message.lower()

    def test_whitespace_barcode(self):
        """Test with whitespace-only barcode."""
        result = get_product_by_barcode("   ")

        assert result.success == False
        assert "empty" in result.error_message.lower()

    def test_invalid_barcode_with_letters(self):
        """Test with barcode containing letters."""
        result = get_product_by_barcode("ABC123")

        assert result.success == False
        assert "invalid" in result.error_message.lower()
        assert "digits" in result.error_message.lower()

    def test_invalid_barcode_with_special_chars(self):
        """Test with barcode containing special characters."""
        result = get_product_by_barcode("123-456-789")

        assert result.success == False
        assert "invalid" in result.error_message.lower()

    @patch("backend.services.barcode.service.fetch_product")
    def test_product_not_found(self, mock_fetch):
        """Test when product is not found in database."""
        mock_fetch.return_value = None

        result = get_product_by_barcode("0000000000000")

        assert result.success == False
        assert "not found" in result.error_message.lower()
        mock_fetch.assert_called_once_with("0000000000000")

    @patch("backend.services.barcode.service.fetch_product")
    @patch("backend.services.barcode.service.extract_product_info")
    @patch("backend.services.barcode.service.parse_ingredients_list")
    @patch("backend.services.barcode.service.get_allergen_list")
    @patch("backend.services.barcode.service.get_traces_list")
    def test_successful_lookup(
        self, mock_traces, mock_allergens, mock_parse, mock_extract, mock_fetch
    ):
        """Test successful product lookup."""
        mock_fetch.return_value = SAMPLE_PRODUCT_DATA
        mock_extract.return_value = {
            "product_name": "Test Product",
            "brand": "Test Brand",
            "ingredients_text": "Water, Sugar, Salt",
            "image_url": "https://example.com/image.jpg",
            "nutrition_grade": "a",
        }
        mock_parse.return_value = ["Water", "Sugar", "Salt"]
        mock_allergens.return_value = ["Milk"]
        mock_traces.return_value = ["Nuts"]

        result = get_product_by_barcode("1234567890123")

        assert result.success == True
        assert result.barcode == "1234567890123"
        assert result.product_name == "Test Product"
        assert result.brand == "Test Brand"
        assert result.ingredients == ["Water", "Sugar", "Salt"]
        assert result.allergens == ["Milk"]
        assert result.traces == ["Nuts"]

    @patch("backend.services.barcode.service.fetch_product")
    def test_barcode_trimming(self, mock_fetch):
        """Test that barcode whitespace is trimmed."""
        mock_fetch.return_value = None

        get_product_by_barcode("  1234567890123  ")

        mock_fetch.assert_called_once_with("1234567890123")


# =============================================================================
# TESTS FOR scan_barcode
# =============================================================================

class TestScanBarcode:
    """Tests for the scan_barcode convenience function."""

    @patch("backend.services.barcode.service.get_product_by_barcode")
    def test_scan_barcode_returns_dict(self, mock_get_product):
        """Test that scan_barcode returns a dictionary."""
        mock_result = BarcodeResult(
            success=True,
            barcode="123",
            product_name="Test",
        )
        mock_get_product.return_value = mock_result

        result = scan_barcode("123")

        assert isinstance(result, dict)
        assert result["success"] == True
        assert result["barcode"] == "123"

    @patch("backend.services.barcode.service.get_product_by_barcode")
    def test_scan_barcode_passes_barcode(self, mock_get_product):
        """Test that scan_barcode passes barcode to get_product_by_barcode."""
        mock_get_product.return_value = BarcodeResult(success=False, barcode="test")

        scan_barcode("test_barcode")

        mock_get_product.assert_called_once_with("test_barcode")


# =============================================================================
# TESTS FOR fetch_product (Open Food Facts API)
# =============================================================================

class TestFetchProduct:
    """Tests for the fetch_product function."""

    @patch("backend.services.barcode.openfoodfacts.requests.get")
    def test_fetch_product_success(self, mock_get):
        """Test successful product fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_API_RESPONSE_SUCCESS
        mock_get.return_value = mock_response

        result = fetch_product("5000159407236")

        assert result is not None
        assert result["code"] == "5000159407236"
        assert result["product_name"] == "Cadbury Dairy Milk"

    @patch("backend.services.barcode.openfoodfacts.requests.get")
    def test_fetch_product_not_found(self, mock_get):
        """Test product not found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_API_RESPONSE_NOT_FOUND
        mock_get.return_value = mock_response

        result = fetch_product("0000000000000")

        assert result is None

    @patch("backend.services.barcode.openfoodfacts.requests.get")
    def test_fetch_product_api_error(self, mock_get):
        """Test API error response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = fetch_product("1234567890123")

        assert result is None

    @patch("backend.services.barcode.openfoodfacts.requests.get")
    def test_fetch_product_timeout(self, mock_get):
        """Test request timeout handling."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = fetch_product("1234567890123")

        assert result is None

    @patch("backend.services.barcode.openfoodfacts.requests.get")
    def test_fetch_product_connection_error(self, mock_get):
        """Test connection error handling."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = fetch_product("1234567890123")

        assert result is None

    @patch("backend.services.barcode.openfoodfacts.requests.get")
    def test_fetch_product_request_exception(self, mock_get):
        """Test generic request exception handling."""
        mock_get.side_effect = requests.exceptions.RequestException("Some error")

        result = fetch_product("1234567890123")

        assert result is None

    @patch("backend.services.barcode.openfoodfacts.requests.get")
    def test_fetch_product_uses_correct_url(self, mock_get):
        """Test that correct API URL is used."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_API_RESPONSE_NOT_FOUND
        mock_get.return_value = mock_response

        fetch_product("1234567890123")

        call_args = mock_get.call_args
        assert "1234567890123" in call_args[0][0]
        assert ".json" in call_args[0][0]

    @patch("backend.services.barcode.openfoodfacts.requests.get")
    def test_fetch_product_uses_user_agent(self, mock_get):
        """Test that User-Agent header is set."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_API_RESPONSE_NOT_FOUND
        mock_get.return_value = mock_response

        fetch_product("1234567890123")

        call_kwargs = mock_get.call_args[1]
        assert "headers" in call_kwargs
        assert "User-Agent" in call_kwargs["headers"]


# =============================================================================
# TESTS FOR extract_product_info
# =============================================================================

class TestExtractProductInfo:
    """Tests for the extract_product_info function."""

    def test_extract_product_info_complete(self):
        """Test extraction with complete product data."""
        result = extract_product_info(SAMPLE_PRODUCT_DATA)

        assert result["barcode"] == "5000159407236"
        assert result["product_name"] == "Cadbury Dairy Milk Chocolate"  # English preferred
        assert result["brand"] == "Cadbury"
        assert "Sugar" in result["ingredients_text"]
        assert result["nutrition_grade"] == "d"

    def test_extract_product_info_prefers_english(self):
        """Test that English fields are preferred."""
        data = {
            "product_name": "Produit Français",
            "product_name_en": "English Product",
            "ingredients_text": "Ingrédients français",
            "ingredients_text_en": "English ingredients",
        }

        result = extract_product_info(data)

        assert result["product_name"] == "English Product"
        assert result["ingredients_text"] == "English ingredients"

    def test_extract_product_info_fallback_to_non_english(self):
        """Test fallback to non-English fields when English not available."""
        data = {
            "product_name": "Produit Français",
            "ingredients_text": "Ingrédients français",
        }

        result = extract_product_info(data)

        assert result["product_name"] == "Produit Français"
        assert result["ingredients_text"] == "Ingrédients français"

    def test_extract_product_info_empty_data(self):
        """Test extraction with empty data."""
        result = extract_product_info({})

        assert result["product_name"] == "Unknown Product"
        assert result["brand"] == ""
        assert result["ingredients_text"] == ""

    def test_extract_product_info_generic_name_fallback(self):
        """Test fallback to generic_name when product_name not available."""
        data = {
            "generic_name_en": "Generic Product Name",
        }

        result = extract_product_info(data)

        assert result["product_name"] == "Generic Product Name"

    def test_extract_product_info_image_url_fallback(self):
        """Test image URL extraction with fallback."""
        data_with_front = {"image_front_url": "https://front.jpg"}
        data_with_regular = {"image_url": "https://regular.jpg"}
        data_with_both = {
            "image_front_url": "https://front.jpg",
            "image_url": "https://regular.jpg",
        }

        assert extract_product_info(data_with_front)["image_url"] == "https://front.jpg"
        assert extract_product_info(data_with_regular)["image_url"] == "https://regular.jpg"
        assert extract_product_info(data_with_both)["image_url"] == "https://front.jpg"


# =============================================================================
# TESTS FOR parse_ingredients_list
# =============================================================================

class TestParseIngredientsList:
    """Tests for the parse_ingredients_list function."""

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_ingredients_list("")

        assert result == []

    def test_parse_none(self):
        """Test parsing None (should handle gracefully)."""
        result = parse_ingredients_list(None)

        assert result == []

    def test_parse_simple_list(self):
        """Test parsing simple comma-separated list."""
        result = parse_ingredients_list("Water, Sugar, Salt")

        assert len(result) == 3
        assert "Water" in result
        assert "Sugar" in result
        assert "Salt" in result

    def test_parse_with_ingredients_prefix(self):
        """Test parsing with 'Ingredients:' prefix."""
        result = parse_ingredients_list("Ingredients: Water, Sugar, Salt")

        assert len(result) == 3
        assert "Water" in result

    def test_parse_with_contains_prefix(self):
        """Test parsing with 'Contains:' prefix."""
        result = parse_ingredients_list("Contains: Milk, Eggs, Wheat")

        assert len(result) == 3

    def test_parse_with_parentheses(self):
        """Test parsing ingredients with parenthetical content."""
        result = parse_ingredients_list(
            "Emulsifier (E471), Cocoa butter (organic), Salt"
        )

        assert len(result) == 3
        assert any("E471" in ing for ing in result)

    def test_parse_nested_parentheses(self):
        """Test parsing with nested parentheses."""
        result = parse_ingredients_list(
            "Sugar, Chocolate (Cocoa mass (40%), Sugar, Cocoa butter), Salt"
        )

        # Should preserve nested content together
        assert len(result) == 3
        assert any("Chocolate" in ing for ing in result)

    def test_parse_removes_percentages(self):
        """Test that percentages are removed."""
        result = parse_ingredients_list("Sugar 30%, Water 50%, Salt 20%")

        for ingredient in result:
            assert "%" not in ingredient

    def test_parse_single_characters_filtered(self):
        """Test that single character items are filtered out."""
        result = parse_ingredients_list("Water, , , Salt, a, Sugar")

        # Single characters and empty items should be filtered
        for ingredient in result:
            assert len(ingredient) > 1

    def test_parse_trims_whitespace(self):
        """Test that whitespace is trimmed from ingredients."""
        result = parse_ingredients_list("  Water  ,  Sugar  ,  Salt  ")

        for ingredient in result:
            assert ingredient == ingredient.strip()
            assert not ingredient.startswith(" ")
            assert not ingredient.endswith(" ")

    def test_parse_complex_real_world(self):
        """Test parsing complex real-world ingredient list."""
        text = (
            "Ingredients: Sugar, Cocoa butter, Whole milk powder, "
            "Cocoa mass, Emulsifier (Soya lecithin E322), "
            "Flavourings, Milk fat"
        )

        result = parse_ingredients_list(text)

        assert len(result) >= 5
        assert any("Sugar" in ing for ing in result)
        assert any("Cocoa butter" in ing for ing in result)


# =============================================================================
# TESTS FOR get_allergen_list
# =============================================================================

class TestGetAllergenList:
    """Tests for the get_allergen_list function."""

    def test_get_allergens_from_string(self):
        """Test extracting allergens from allergens string."""
        data = {"allergens": "en:milk,en:gluten"}

        result = get_allergen_list(data)

        assert "Milk" in result
        assert "Gluten" in result

    def test_get_allergens_from_tags(self):
        """Test extracting allergens from allergens_tags."""
        data = {"allergens_tags": ["en:milk", "en:soybeans", "en:eggs"]}

        result = get_allergen_list(data)

        assert "Milk" in result
        assert "Soybeans" in result
        assert "Eggs" in result

    def test_get_allergens_combined(self):
        """Test combining allergens from both sources."""
        data = {
            "allergens": "en:milk",
            "allergens_tags": ["en:gluten"],
        }

        result = get_allergen_list(data)

        assert "Milk" in result
        assert "Gluten" in result

    def test_get_allergens_no_duplicates(self):
        """Test that duplicates are removed."""
        data = {
            "allergens": "en:milk",
            "allergens_tags": ["en:milk"],
        }

        result = get_allergen_list(data)

        # Should only have one Milk entry
        assert result.count("Milk") == 1

    def test_get_allergens_empty_data(self):
        """Test with empty data."""
        result = get_allergen_list({})

        assert result == []

    def test_get_allergens_handles_dashes(self):
        """Test that dashes in tags are replaced with spaces."""
        data = {"allergens_tags": ["en:tree-nuts"]}

        result = get_allergen_list(data)

        assert "Tree Nuts" in result

    def test_get_allergens_title_case(self):
        """Test that allergens are title-cased."""
        data = {"allergens": "en:MILK,en:eggs"}

        result = get_allergen_list(data)

        assert "Milk" in result
        assert "Eggs" in result


# =============================================================================
# TESTS FOR get_traces_list
# =============================================================================

class TestGetTracesList:
    """Tests for the get_traces_list function."""

    def test_get_traces_from_string(self):
        """Test extracting traces from traces string."""
        data = {"traces": "en:nuts,en:soybeans"}

        result = get_traces_list(data)

        assert "Nuts" in result
        assert "Soybeans" in result

    def test_get_traces_from_tags(self):
        """Test extracting traces from traces_tags."""
        data = {"traces_tags": ["en:nuts", "en:peanuts", "en:sesame-seeds"]}

        result = get_traces_list(data)

        assert "Nuts" in result
        assert "Peanuts" in result
        assert "Sesame Seeds" in result

    def test_get_traces_combined(self):
        """Test combining traces from both sources."""
        data = {
            "traces": "en:milk",
            "traces_tags": ["en:eggs"],
        }

        result = get_traces_list(data)

        assert "Milk" in result
        assert "Eggs" in result

    def test_get_traces_no_duplicates(self):
        """Test that duplicates are removed."""
        data = {
            "traces": "en:nuts",
            "traces_tags": ["en:nuts"],
        }

        result = get_traces_list(data)

        assert result.count("Nuts") == 1

    def test_get_traces_empty_data(self):
        """Test with empty data."""
        result = get_traces_list({})

        assert result == []

    def test_get_traces_handles_dashes(self):
        """Test that dashes in tags are replaced with spaces."""
        data = {"traces_tags": ["en:sesame-seeds"]}

        result = get_traces_list(data)

        assert "Sesame Seeds" in result


# =============================================================================
# INTEGRATION-STYLE TESTS (within unit test scope)
# =============================================================================

class TestBarcodeServiceIntegration:
    """Integration-style tests for the barcode service."""

    @patch("backend.services.barcode.service.fetch_product")
    def test_full_flow_with_real_data_structure(self, mock_fetch):
        """Test full flow with realistic data structure."""
        mock_fetch.return_value = SAMPLE_PRODUCT_DATA

        result = get_product_by_barcode("5000159407236")

        assert result.success == True
        assert result.product_name == "Cadbury Dairy Milk Chocolate"
        assert result.brand == "Cadbury"
        assert len(result.ingredients) > 0
        assert "Milk" in result.allergens
        assert len(result.traces) > 0

    @patch("backend.services.barcode.service.fetch_product")
    def test_full_flow_minimal_data(self, mock_fetch):
        """Test full flow with minimal data."""
        mock_fetch.return_value = {
            "code": "123",
            "product_name": "Simple Product",
        }

        result = get_product_by_barcode("123")

        assert result.success == True
        assert result.product_name == "Simple Product"
        assert result.ingredients == []
        assert result.allergens == []

    def test_validation_before_api_call(self):
        """Test that validation happens before API call."""
        # Invalid barcodes should fail without making API call
        result = get_product_by_barcode("invalid!")

        assert result.success == False
        # If it reached API, we would see different error message


class TestBarcodeEdgeCases:
    """Tests for edge cases in barcode service."""

    def test_barcode_with_leading_zeros(self):
        """Test barcode with leading zeros is preserved."""
        with patch("backend.services.barcode.service.fetch_product") as mock_fetch:
            mock_fetch.return_value = None

            get_product_by_barcode("0000012345678")

            mock_fetch.assert_called_once_with("0000012345678")

    @patch("backend.services.barcode.service.fetch_product")
    def test_very_long_barcode(self, mock_fetch):
        """Test handling of very long barcode."""
        mock_fetch.return_value = None
        long_barcode = "1" * 50

        result = get_product_by_barcode(long_barcode)

        # Should still attempt lookup (validation only checks for digits)
        mock_fetch.assert_called_once()

    @patch("backend.services.barcode.service.fetch_product")
    def test_product_with_empty_ingredients(self, mock_fetch):
        """Test product with no ingredients listed."""
        mock_fetch.return_value = {
            "code": "123",
            "product_name": "Mystery Product",
            "ingredients_text": "",
        }

        result = get_product_by_barcode("123")

        assert result.success == True
        assert result.ingredients == []

    @patch("backend.services.barcode.service.fetch_product")
    def test_product_with_special_characters_in_name(self, mock_fetch):
        """Test product with special characters in name."""
        mock_fetch.return_value = {
            "code": "123",
            "product_name": "Café Crème™ (Premium)",
            "brands": "L'Oréal",  # API uses 'brands' (plural)
        }

        result = get_product_by_barcode("123")

        assert result.success == True
        assert "Café" in result.product_name
        assert "L'Oréal" == result.brand
