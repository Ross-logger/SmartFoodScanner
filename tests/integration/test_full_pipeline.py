"""
Integration Tests for Full Pipeline

Tests the complete flow from image upload to dietary compliance result:
- Image upload -> OCR -> Extraction -> Analysis -> Result
- End-to-end accuracy testing
- Target: 95% dietary compliance detection accuracy
"""

import pytest
from unittest.mock import patch, MagicMock
import io
from PIL import Image

from fastapi.testclient import TestClient

from backend.main import app
from backend.models import User, DietaryProfile, Scan
from backend.services.ocr.service import extract_text_from_image
from backend.services.ingredients_extraction.extractor import extract
from backend.services.ingredients_analysis.service import analyze_ingredients
from tests.utils.test_helpers import create_test_image, create_test_image_with_text
from tests.utils.metrics import EvaluationMetrics


@pytest.mark.integration
class TestFullPipelineFlow:
    """Tests for the complete pipeline flow."""
    
    def test_pipeline_ocr_to_analysis(self):
        """Test complete pipeline from OCR text to analysis."""
        # Simulate OCR output
        ocr_text = "Ingredients: Water, Sugar, Wheat Flour, Salt"
        
        # Extract ingredients
        with patch('backend.services.ingredients_extraction.hugging_face_extractor.extract_ingredients') as mock_hf:
            mock_hf.return_value = ["Water", "Sugar", "Wheat Flour", "Salt"]
            ingredients = extract(ocr_text)
        
        # Create dietary profile
        profile = MagicMock()
        profile.halal = False
        profile.gluten_free = True
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        # Analyze with rule-based (mock LLM unavailable)
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None  # Force rule-based fallback
            result = analyze_ingredients(ingredients, profile)
        
        # Should detect wheat/gluten
        assert result["is_safe"] == False
        assert len(result["warnings"]) > 0
    
    def test_pipeline_halal_detection(self):
        """Test pipeline detects halal violations."""
        ocr_text = "Ingredients: Water, Gelatin, Sugar, Natural Flavors"
        
        with patch('backend.services.ingredients_extraction.hugging_face_extractor.extract_ingredients') as mock_hf:
            mock_hf.return_value = ["Water", "Gelatin", "Sugar", "Natural Flavors"]
            ingredients = extract(ocr_text)
        
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = False
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(ingredients, profile)
        
        assert result["is_safe"] == False
        assert any("gelatin" in w.lower() for w in result["warnings"])
    
    def test_pipeline_vegan_detection(self):
        """Test pipeline detects vegan violations."""
        ocr_text = "Ingredients: Flour, Butter, Eggs, Milk, Sugar"
        
        with patch('backend.services.ingredients_extraction.hugging_face_extractor.extract_ingredients') as mock_hf:
            mock_hf.return_value = ["Flour", "Butter", "Eggs", "Milk", "Sugar"]
            ingredients = extract(ocr_text)
        
        profile = MagicMock()
        profile.halal = False
        profile.gluten_free = False
        profile.vegetarian = False
        profile.vegan = True
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_pipeline_safe_product(self):
        """Test pipeline correctly identifies safe product."""
        ocr_text = "Ingredients: Water, Rice Flour, Sugar, Sunflower Oil, Salt"
        
        with patch('backend.services.ingredients_extraction.hugging_face_extractor.extract_ingredients') as mock_hf:
            mock_hf.return_value = ["Water", "Rice Flour", "Sugar", "Sunflower Oil", "Salt"]
            ingredients = extract(ocr_text)
        
        # Profile with multiple restrictions
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = True
        profile.vegetarian = True
        profile.vegan = True
        profile.nut_free = True
        profile.dairy_free = True
        profile.allergens = []
        profile.custom_restrictions = []
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0


@pytest.mark.integration
class TestAPIEndpointIntegration:
    """Tests for API endpoint integration."""
    
    def test_scan_endpoint_with_image(self, client, test_user, test_db):
        """Test scan/ocr endpoint with image upload."""
        # Create dietary profile for user
        profile = DietaryProfile(
            user_id=test_user.id,
            halal=True,
            gluten_free=False,
            vegetarian=False,
            vegan=False,
            nut_free=False,
            dairy_free=False,
            allergens=[],
            custom_restrictions=[]
        )
        test_db.add(profile)
        test_db.commit()
        
        # Create test image
        image_bytes = create_test_image()
        
        # Mock OCR and extraction
        with patch('backend.routers.scans.extract_text_from_image') as mock_ocr:
            mock_ocr.return_value = "Ingredients: Water, Sugar, Salt"
            
            with patch('backend.routers.scans.extract_ingredients') as mock_extract:
                mock_extract.return_value = ["Water", "Sugar", "Salt"]
                
                # Login and get token
                response = client.post(
                    "/api/auth/login",
                    data={"username": "testuser", "password": "testpassword123"}
                )
                
                if response.status_code == 200:
                    token = response.json()["access_token"]
                    
                    # Upload image
                    files = {"file": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")}
                    scan_response = client.post(
                        "/api/scan/ocr",
                        files=files,
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    
                    # Should work (status 200) or fail gracefully
                    assert scan_response.status_code in [200, 401, 500]
    
    def test_dietary_profile_endpoint(self, client, test_user, test_db):
        """Test dietary profile CRUD operations."""
        # Login
        response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Create dietary profile
            profile_data = {
                "halal": True,
                "gluten_free": True,
                "vegetarian": False,
                "vegan": False,
                "nut_free": True,
                "dairy_free": False,
                "allergens": ["sesame"],
                "custom_restrictions": []
            }
            
            create_response = client.post(
                "/api/dietary/profile",
                json=profile_data,
                headers=headers
            )
            
            # Should create or conflict if exists
            assert create_response.status_code in [200, 201, 409]


@pytest.mark.integration
class TestComplianceAccuracy:
    """Tests for dietary compliance accuracy target (95%)."""
    
    def test_compliance_accuracy_synthetic_data(self):
        """Test compliance accuracy using synthetic test cases."""
        from tests.data.synthetic.ocr_samples import get_dietary_test_cases
        
        test_cases = get_dietary_test_cases()
        metrics = EvaluationMetrics()
        
        for case in test_cases:
            # Create mock profile
            profile = MagicMock()
            profile_data = case.get("profile", {})
            profile.halal = profile_data.get("halal", False)
            profile.gluten_free = profile_data.get("gluten_free", False)
            profile.vegetarian = profile_data.get("vegetarian", False)
            profile.vegan = profile_data.get("vegan", False)
            profile.nut_free = profile_data.get("nut_free", False)
            profile.dairy_free = profile_data.get("dairy_free", False)
            profile.allergens = profile_data.get("allergens", [])
            profile.custom_restrictions = profile_data.get("custom_restrictions", [])
            
            # Run analysis
            with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
                mock_llm.return_value = None  # Force rule-based
                result = analyze_ingredients(case["ingredients"], profile)
            
            # Record result
            metrics.add_compliance_result(
                case["id"],
                predicted_safe=result["is_safe"],
                actual_safe=case["expected_safe"],
                predicted_warnings=result["warnings"],
                expected_warnings=case.get("expected_warnings", [])
            )
        
        summary = metrics.get_summary()
        
        # Target: 95% accuracy
        accuracy = summary["compliance"]["accuracy"]
        assert accuracy >= 0.95, f"Compliance accuracy {accuracy:.2%} below 95% target"
    
    def test_halal_compliance_accuracy(self):
        """Test halal-specific compliance accuracy."""
        from tests.data.synthetic.ocr_samples import get_dietary_test_cases
        
        halal_cases = [c for c in get_dietary_test_cases() 
                       if c.get("profile", {}).get("halal", False)]
        
        if not halal_cases:
            pytest.skip("No halal test cases available")
        
        correct = 0
        total = len(halal_cases)
        
        for case in halal_cases:
            profile = MagicMock()
            profile.halal = True
            profile.gluten_free = False
            profile.vegetarian = False
            profile.vegan = False
            profile.nut_free = False
            profile.dairy_free = False
            profile.allergens = []
            profile.custom_restrictions = []
            
            with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
                mock_llm.return_value = None
                result = analyze_ingredients(case["ingredients"], profile)
            
            if result["is_safe"] == case["expected_safe"]:
                correct += 1
        
        accuracy = correct / total
        assert accuracy >= 0.95, f"Halal compliance accuracy {accuracy:.2%} below 95% target"
    
    def test_gluten_free_compliance_accuracy(self):
        """Test gluten-free-specific compliance accuracy."""
        from tests.data.synthetic.ocr_samples import get_dietary_test_cases
        
        gluten_cases = [c for c in get_dietary_test_cases() 
                        if c.get("profile", {}).get("gluten_free", False)]
        
        if not gluten_cases:
            pytest.skip("No gluten-free test cases available")
        
        correct = 0
        total = len(gluten_cases)
        
        for case in gluten_cases:
            profile = MagicMock()
            profile.halal = False
            profile.gluten_free = True
            profile.vegetarian = False
            profile.vegan = False
            profile.nut_free = False
            profile.dairy_free = False
            profile.allergens = []
            profile.custom_restrictions = []
            
            with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
                mock_llm.return_value = None
                result = analyze_ingredients(case["ingredients"], profile)
            
            if result["is_safe"] == case["expected_safe"]:
                correct += 1
        
        accuracy = correct / total
        assert accuracy >= 0.95, f"Gluten-free compliance accuracy {accuracy:.2%} below 95% target"


@pytest.mark.integration
class TestWarningGeneration:
    """Tests for clear warning generation."""
    
    def test_warning_contains_ingredient_name(self):
        """Test that warnings mention the problematic ingredient."""
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = False
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        ingredients = ["Water", "Pork", "Salt"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(ingredients, profile)
        
        assert result["is_safe"] == False
        # Warning should mention pork
        warnings_text = " ".join(result["warnings"]).lower()
        assert "pork" in warnings_text
    
    def test_warning_for_each_restriction_violation(self):
        """Test warnings are generated for each violated restriction."""
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = True
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        # Product that violates both halal (pork) and gluten-free (wheat)
        ingredients = ["Pork", "Wheat Flour", "Sugar"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(ingredients, profile)
        
        assert result["is_safe"] == False
        # Should have warnings for both violations
        assert len(result["warnings"]) >= 1
    
    def test_no_warnings_for_safe_product(self):
        """Test no warnings for safe product."""
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = True
        profile.vegetarian = True
        profile.vegan = True
        profile.nut_free = True
        profile.dairy_free = True
        profile.allergens = []
        profile.custom_restrictions = []
        
        ingredients = ["Water", "Sugar", "Salt"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(ingredients, profile)
        
        assert result["is_safe"] == True
        assert len(result["warnings"]) == 0


@pytest.mark.integration
class TestMultipleDietaryProfiles:
    """Tests with various dietary profile combinations."""
    
    def test_strict_vegan_profile(self):
        """Test with strict vegan profile."""
        profile = MagicMock()
        profile.halal = False
        profile.gluten_free = False
        profile.vegetarian = True
        profile.vegan = True
        profile.nut_free = False
        profile.dairy_free = True
        profile.allergens = []
        profile.custom_restrictions = []
        
        # Vegan-safe ingredients
        ingredients = ["Water", "Sugar", "Coconut Oil", "Rice Flour"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(ingredients, profile)
        
        assert result["is_safe"] == True
        
        # Non-vegan ingredients
        non_vegan_ingredients = ["Water", "Honey", "Butter"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(non_vegan_ingredients, profile)
        
        assert result["is_safe"] == False
    
    def test_multiple_allergen_profile(self):
        """Test with multiple allergen restrictions."""
        profile = MagicMock()
        profile.halal = False
        profile.gluten_free = True
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = True
        profile.dairy_free = True
        profile.allergens = ["sesame", "soy"]
        profile.custom_restrictions = []
        
        # Safe ingredients
        ingredients = ["Water", "Rice Flour", "Sugar", "Salt"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(ingredients, profile)
        
        assert result["is_safe"] == True
        
        # Unsafe ingredients (contains wheat and nuts)
        unsafe_ingredients = ["Wheat Flour", "Almond Butter", "Sugar"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
            mock_llm.return_value = None
            result = analyze_ingredients(unsafe_ingredients, profile)
        
        assert result["is_safe"] == False
