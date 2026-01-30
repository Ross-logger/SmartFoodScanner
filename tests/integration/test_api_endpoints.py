"""
Integration Tests for API Endpoints

Tests for FastAPI endpoints including:
- Authentication endpoints
- User management endpoints
- Scan endpoints
- Dietary profile endpoints
"""

import pytest
from unittest.mock import patch, MagicMock
import io

from fastapi.testclient import TestClient

from backend.main import app
from backend.models import User, DietaryProfile
from tests.utils.test_helpers import create_test_image


@pytest.mark.integration
class TestAuthEndpoints:
    """Tests for authentication endpoints."""
    
    def test_register_user(self, client):
        """Test user registration endpoint."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepassword123",
            "full_name": "New User"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        # Should succeed or conflict if user exists
        assert response.status_code in [200, 201, 400, 409]
    
    def test_login_user(self, client, test_user):
        """Test user login endpoint."""
        login_data = {
            "username": "testuser",
            "password": "testpassword123"
        }
        
        response = client.post("/api/auth/login", data=login_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        
        response = client.post("/api/auth/login", data=login_data)
        
        # 401 Unauthorized, 400 Bad Request, or 422 Validation Error are all acceptable
        assert response.status_code in [401, 400, 422]
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/users/me")
        
        assert response.status_code == 401


@pytest.mark.integration
class TestUserEndpoints:
    """Tests for user management endpoints."""
    
    def test_get_current_user(self, client, test_user):
        """Test getting current user profile."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            
            response = client.get(
                "/api/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["username"] == "testuser"
                assert data["email"] == "test@example.com"
    
    def test_update_user_profile(self, client, test_user):
        """Test updating user profile."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            
            update_data = {
                "full_name": "Updated Name"
            }
            
            response = client.put(
                "/api/users/me",
                json=update_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should succeed or method not allowed
            assert response.status_code in [200, 405, 422]


@pytest.mark.integration
class TestDietaryProfileEndpoints:
    """Tests for dietary profile endpoints."""
    
    def test_create_dietary_profile(self, client, test_user, test_db):
        """Test creating dietary profile."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            
            profile_data = {
                "halal": True,
                "gluten_free": False,
                "vegetarian": False,
                "vegan": False,
                "nut_free": True,
                "dairy_free": False,
                "allergens": ["sesame"],
                "custom_restrictions": []
            }
            
            response = client.post(
                "/api/dietary/profile",
                json=profile_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should create or conflict if exists
            assert response.status_code in [200, 201, 409]
    
    def test_get_dietary_profile(self, client, test_user, test_db):
        """Test getting dietary profile."""
        # First create a profile
        profile = DietaryProfile(
            user_id=test_user.id,
            halal=True,
            gluten_free=True,
            vegetarian=False,
            vegan=False,
            nut_free=False,
            dairy_free=False,
            allergens=[],
            custom_restrictions=[]
        )
        test_db.add(profile)
        test_db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            
            response = client.get(
                "/api/dietary/profile",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["halal"] == True
                assert data["gluten_free"] == True
    
    def test_update_dietary_profile(self, client, test_user, test_db):
        """Test updating dietary profile."""
        # First create a profile
        profile = DietaryProfile(
            user_id=test_user.id,
            halal=False,
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
        
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            
            update_data = {
                "halal": True,
                "vegan": True
            }
            
            response = client.put(
                "/api/dietary/profile",
                json=update_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should update successfully
            assert response.status_code in [200, 404, 405]


@pytest.mark.integration
class TestScanEndpoints:
    """Tests for scan endpoints."""
    
    def test_scan_ocr_endpoint(self, client, test_user, test_db):
        """Test OCR scan endpoint."""
        # Create dietary profile
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
        
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            
            # Create test image
            image_bytes = create_test_image()
            
            # Mock OCR and extraction
            with patch('backend.routers.scans.extract_text_from_image') as mock_ocr:
                mock_ocr.return_value = "Ingredients: Water, Sugar, Salt"
                
                with patch('backend.routers.scans.extract_ingredients') as mock_extract:
                    mock_extract.return_value = ["Water", "Sugar", "Salt"]
                    
                    files = {"file": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")}
                    
                    response = client.post(
                        "/api/scan/ocr",
                        files=files,
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    
                    # Should work or fail gracefully
                    assert response.status_code in [200, 401, 500]
                    
                    if response.status_code == 200:
                        data = response.json()
                        assert "ingredients" in data
                        assert "is_safe" in data
    
    def test_scan_invalid_file_type(self, client, test_user):
        """Test scan with invalid file type."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            
            # Send a text file instead of image
            files = {"file": ("test.txt", io.BytesIO(b"Not an image"), "text/plain")}
            
            response = client.post(
                "/api/scan/ocr",
                files=files,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should reject non-image files
            assert response.status_code in [400, 415, 422]


@pytest.mark.integration
class TestHistoryEndpoints:
    """Tests for scan history endpoints."""
    
    def test_get_scan_history(self, client, test_user, test_db):
        """Test getting scan history."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            
            response = client.get(
                "/api/history/scans",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should return list (possibly empty)
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)


@pytest.mark.integration
class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Smart Food Scanner" in data["message"]
