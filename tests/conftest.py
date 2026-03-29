"""
Pytest Configuration and Fixtures for SmartFoodScanner Tests

This module provides shared fixtures for:
- Test database (SQLite in-memory)
- Mock LLM services
- Sample dietary profiles
- Test user creation
- FastAPI test client
"""

import os
import sys
import pytest
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend.models import User, DietaryProfile, Scan
from backend.security import get_password_hash

from tests.utils.mock_llm import MockLLMService, MockLLMProvider


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine using SQLite in-memory."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_db) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with test database."""
    from backend.main import app

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =============================================================================
# User Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_user(test_db) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user_token(client, test_user) -> str:
    """Get authentication token for test user."""
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    # If login fails, we need to handle it differently
    return "test_token"


@pytest.fixture(scope="function")
def auth_headers(test_user_token) -> Dict[str, str]:
    """Get authentication headers for API requests."""
    return {"Authorization": f"Bearer {test_user_token}"}


# =============================================================================
# Dietary Profile Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def halal_profile(test_db, test_user) -> DietaryProfile:
    """Create a halal dietary profile."""
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
    test_db.refresh(profile)
    return profile


@pytest.fixture(scope="function")
def gluten_free_profile(test_db, test_user) -> DietaryProfile:
    """Create a gluten-free dietary profile."""
    profile = DietaryProfile(
        user_id=test_user.id,
        halal=False,
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
    test_db.refresh(profile)
    return profile


@pytest.fixture(scope="function")
def vegan_profile(test_db, test_user) -> DietaryProfile:
    """Create a vegan dietary profile."""
    profile = DietaryProfile(
        user_id=test_user.id,
        halal=False,
        gluten_free=False,
        vegetarian=True,
        vegan=True,
        nut_free=False,
        dairy_free=True,
        allergens=[],
        custom_restrictions=[]
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


@pytest.fixture(scope="function")
def vegetarian_profile(test_db, test_user) -> DietaryProfile:
    """Create a vegetarian dietary profile."""
    profile = DietaryProfile(
        user_id=test_user.id,
        halal=False,
        gluten_free=False,
        vegetarian=True,
        vegan=False,
        nut_free=False,
        dairy_free=False,
        allergens=[],
        custom_restrictions=[]
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


@pytest.fixture(scope="function")
def nut_free_profile(test_db, test_user) -> DietaryProfile:
    """Create a nut-free dietary profile."""
    profile = DietaryProfile(
        user_id=test_user.id,
        halal=False,
        gluten_free=False,
        vegetarian=False,
        vegan=False,
        nut_free=True,
        dairy_free=False,
        allergens=["peanuts", "tree nuts"],
        custom_restrictions=[]
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


@pytest.fixture(scope="function")
def dairy_free_profile(test_db, test_user) -> DietaryProfile:
    """Create a dairy-free dietary profile."""
    profile = DietaryProfile(
        user_id=test_user.id,
        halal=False,
        gluten_free=False,
        vegetarian=False,
        vegan=False,
        nut_free=False,
        dairy_free=True,
        allergens=[],
        custom_restrictions=[]
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


@pytest.fixture(scope="function")
def multiple_restrictions_profile(test_db, test_user) -> DietaryProfile:
    """Create a profile with multiple dietary restrictions."""
    profile = DietaryProfile(
        user_id=test_user.id,
        halal=True,
        gluten_free=True,
        vegetarian=False,
        vegan=False,
        nut_free=True,
        dairy_free=False,
        allergens=["shellfish", "soy"],
        custom_restrictions=["no artificial colors"]
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


@pytest.fixture(scope="function")
def no_restrictions_profile(test_db, test_user) -> DietaryProfile:
    """Create a profile with no dietary restrictions."""
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
    test_db.refresh(profile)
    return profile


# =============================================================================
# Mock LLM Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def mock_llm_service() -> MockLLMService:
    """Create a mock LLM service."""
    return MockLLMService.create_default()


@pytest.fixture(scope="function")
def mock_llm_unavailable() -> MockLLMService:
    """Create a mock LLM service that is unavailable."""
    return MockLLMService.create_unavailable()


@pytest.fixture(scope="function")
def mock_llm_provider() -> MockLLMProvider:
    """Create a mock LLM provider."""
    return MockLLMProvider()


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def sample_ingredients_simple():
    """Simple ingredient list for testing."""
    return ["Water", "Sugar", "Salt"]


@pytest.fixture(scope="session")
def sample_ingredients_complex():
    """Complex ingredient list for testing."""
    return [
        "Water", "Sugar", "Wheat Flour", "Palm Oil", "Salt",
        "Mono and Diglycerides", "Natural and Artificial Flavors",
        "Soy Lecithin", "Sodium Caseinate"
    ]


@pytest.fixture(scope="session")
def sample_ingredients_with_allergens():
    """Ingredient list with common allergens."""
    return [
        "Wheat Flour", "Milk Powder", "Eggs", "Peanut Butter",
        "Soy Lecithin", "Tree Nuts", "Fish Oil"
    ]


@pytest.fixture(scope="session")
def sample_ocr_text():
    """Sample OCR text for testing."""
    return "Ingredients: Water, Sugar, Wheat Flour, Palm Oil, Salt, Natural Flavors"


@pytest.fixture(scope="session")
def sample_ocr_text_with_errors():
    """Sample OCR text with common OCR errors."""
    return "lngredients: Water, 5ugar, Wheat F1our, Pa1m 0il, 5alt, Natura1 F1avors"


# =============================================================================
# Image Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def sample_image_bytes():
    """Create sample image bytes for testing."""
    from tests.utils.test_helpers import create_test_image
    return create_test_image()


@pytest.fixture(scope="function")
def sample_image_with_text():
    """Create sample image with text for OCR testing."""
    from tests.utils.test_helpers import create_test_image_with_text
    return create_test_image_with_text(
        "Ingredients: Water, Sugar, Salt, Wheat Flour"
    )


@pytest.fixture(scope="function")
def corrupted_image():
    """Create corrupted image data for error handling tests."""
    from tests.utils.test_helpers import create_corrupted_image
    return create_corrupted_image()


# =============================================================================
# Patch Fixtures for External Services
# =============================================================================

@pytest.fixture(scope="function")
def mock_ocr_reader():
    """Mock EasyOCR reader."""
    with patch('backend.services.ocr.service.get_ocr_reader') as mock:
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Ingredients:", 0.95),
            ([[0, 25], [200, 25], [200, 45], [0, 45]], "Water, Sugar, Salt", 0.92),
        ]
        mock.return_value = mock_reader
        yield mock_reader


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_uploads():
    """Clean up any test uploads after each test."""
    yield
    # Cleanup logic if needed
    import shutil
    test_upload_dir = "test_uploads"
    if os.path.exists(test_upload_dir):
        shutil.rmtree(test_upload_dir)


# =============================================================================
# Markers Configuration
# =============================================================================

def pytest_addoption(parser):
    """Register custom command-line options for performance tests."""
    parser.addoption(
        "--perf-output",
        default=None,
        help="Path to save pipeline performance results JSON (default: tests/data/performance_results.json)",
    )
    parser.addoption(
        "--perf-num-images",
        type=int,
        default=None,
        help="Number of images to test (default: all images in the directory)",
    )
    parser.addoption(
        "--perf-images-dir",
        default=None,
        help="Directory of test images (default: tests/data/images)",
    )


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line("markers", "uat: marks tests as user acceptance tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
