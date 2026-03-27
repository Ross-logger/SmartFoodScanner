"""
Unit Tests for OCR Service

Tests for the OCR text extraction functionality including:
- Basic text extraction from images
- Confidence filtering
- Image format handling (JPEG, PNG, HEIF)
- Corrupted image handling
- Edge cases
"""

import pytest
from unittest.mock import patch, MagicMock
import io
from PIL import Image

from backend.services.ocr.service import (
    extract_text_from_image,
    filter_ocr_results_by_confidence,
    get_ocr_reader,
)
from tests.utils.test_helpers import (
    create_test_image,
    create_test_image_with_text,
    create_corrupted_image,
    create_partial_image,
)
from tests.utils.metrics import calculate_ocr_accuracy, calculate_word_accuracy


class TestFilterOCRResultsByConfidence:
    """Tests for the confidence filtering function."""
    
    def test_filter_high_confidence_results(self):
        """Test filtering with high confidence threshold."""
        results = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Hello", 0.95),
            ([[0, 25], [100, 25], [100, 45], [0, 45]], "World", 0.85),
            ([[0, 50], [100, 50], [100, 70], [0, 70]], "Test", 0.25),
        ]
        
        filtered = filter_ocr_results_by_confidence(results, confidence_threshold=0.5)
        
        assert len(filtered) == 2
        assert "Hello" in filtered
        assert "World" in filtered
        assert "Test" not in filtered
    
    def test_filter_low_confidence_threshold(self):
        """Test filtering with low confidence threshold."""
        results = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Hello", 0.95),
            ([[0, 25], [100, 25], [100, 45], [0, 45]], "World", 0.85),
            ([[0, 50], [100, 50], [100, 70], [0, 70]], "Test", 0.25),
        ]
        
        filtered = filter_ocr_results_by_confidence(results, confidence_threshold=0.2)
        
        assert len(filtered) == 3
        assert "Test" in filtered
    
    def test_filter_default_threshold(self):
        """Test filtering with default threshold (0.3)."""
        results = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Good", 0.8),
            ([[0, 25], [100, 25], [100, 45], [0, 45]], "Bad", 0.2),
        ]
        
        filtered = filter_ocr_results_by_confidence(results)
        
        assert len(filtered) == 1
        assert "Good" in filtered
    
    def test_filter_empty_results(self):
        """Test filtering empty results list."""
        filtered = filter_ocr_results_by_confidence([])
        assert filtered == []
    
    def test_filter_strips_whitespace(self):
        """Test that filtering strips whitespace from text."""
        results = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "  Hello  ", 0.9),
            ([[0, 25], [100, 25], [100, 45], [0, 45]], "\nWorld\n", 0.9),
        ]
        
        filtered = filter_ocr_results_by_confidence(results)
        
        assert "Hello" in filtered
        assert "World" in filtered
        assert "  Hello  " not in filtered
    
    def test_filter_excludes_empty_text(self):
        """Test that empty text is excluded even with high confidence."""
        results = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "", 0.95),
            ([[0, 25], [100, 25], [100, 45], [0, 45]], "   ", 0.95),
            ([[0, 50], [100, 50], [100, 70], [0, 70]], "Valid", 0.9),
        ]
        
        filtered = filter_ocr_results_by_confidence(results)
        
        assert len(filtered) == 1
        assert "Valid" in filtered
    
    def test_filter_handles_missing_confidence(self):
        """Test handling results with missing confidence value."""
        results = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "NoConf"),  # Missing confidence
            ([[0, 25], [100, 25], [100, 45], [0, 45]], "WithConf", 0.9),
        ]
        
        # Should use default confidence of 1.0 for missing values
        filtered = filter_ocr_results_by_confidence(results)
        
        assert "NoConf" in filtered
        assert "WithConf" in filtered


class TestExtractTextFromImage:
    """Tests for the main OCR extraction function."""
    
    @pytest.fixture
    def mock_reader(self):
        """Create a mock OCR reader."""
        with patch('backend.services.ocr.service.get_ocr_reader') as mock:
            mock_reader = MagicMock()
            mock.return_value = mock_reader
            yield mock_reader
    
    def test_extract_text_basic(self, mock_reader):
        """Test basic text extraction from image."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Ingredients:", 0.95),
            ([[0, 25], [200, 25], [200, 45], [0, 45]], "Water, Sugar, Salt", 0.92),
        ]
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        assert "Ingredients:" in result
        assert "Water, Sugar, Salt" in result
        mock_reader.readtext.assert_called_once()
    
    def test_extract_text_multiline(self, mock_reader):
        """Test extraction of multi-line text."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Line 1", 0.9),
            ([[0, 25], [100, 25], [100, 45], [0, 45]], "Line 2", 0.9),
            ([[0, 50], [100, 50], [100, 70], [0, 70]], "Line 3", 0.9),
        ]
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
    
    def test_extract_text_jpeg_format(self, mock_reader):
        """Test extraction from JPEG image."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "JPEG Test", 0.9),
        ]
        
        image_bytes = create_test_image(format="JPEG")
        result = extract_text_from_image(image_bytes)
        
        assert "JPEG Test" in result
    
    def test_extract_text_png_format(self, mock_reader):
        """Test extraction from PNG image."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "PNG Test", 0.9),
        ]
        
        image_bytes = create_test_image(format="PNG")
        result = extract_text_from_image(image_bytes)
        
        assert "PNG Test" in result
    
    def test_extract_text_empty_image(self, mock_reader):
        """Test extraction from image with no text."""
        mock_reader.readtext.return_value = []
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        assert result == ""
    
    def test_extract_text_corrupted_image(self):
        """Test handling of corrupted image data."""
        corrupted_data = create_corrupted_image()
        
        with pytest.raises(Exception) as exc_info:
            extract_text_from_image(corrupted_data)
        
        assert "OCR extraction failed" in str(exc_info.value)
    
    def test_extract_text_partial_image(self):
        """Test handling of truncated/partial image."""
        partial_data = create_partial_image()
        
        with pytest.raises(Exception) as exc_info:
            extract_text_from_image(partial_data)
        
        assert "OCR extraction failed" in str(exc_info.value)
    
    def test_extract_text_with_confidence_filter(self, mock_reader):
        """Test extraction with confidence filtering enabled."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "High Conf", 0.95),
            ([[0, 25], [100, 25], [100, 45], [0, 45]], "Low Conf", 0.1),
        ]
        
        with patch('backend.services.ocr.service.settings') as mock_settings:
            mock_settings.IS_OCR_CONFIDENCE_FILTER = True
            mock_settings.OCR_CONFIDENCE_FILTER_THRESHOLD = 0.3
            mock_settings.OCR_PREPROCESS_ENABLED = True
            mock_settings.OCR_PREPROCESS_TARGET_SHORT_EDGE = 1000
            mock_settings.OCR_PREPROCESS_MAX_LONG_EDGE = 2400

            image_bytes = create_test_image()
            result = extract_text_from_image(image_bytes)
            
            assert "High Conf" in result
            # Low confidence text should be filtered out
    
    def test_extract_text_without_confidence_filter(self, mock_reader):
        """Test extraction without confidence filtering."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "High Conf", 0.95),
            ([[0, 25], [100, 25], [100, 45], [0, 45]], "Low Conf", 0.1),
        ]
        
        with patch('backend.services.ocr.service.settings') as mock_settings:
            mock_settings.IS_OCR_CONFIDENCE_FILTER = False
            mock_settings.OCR_PREPROCESS_ENABLED = True
            mock_settings.OCR_PREPROCESS_TARGET_SHORT_EDGE = 1000
            mock_settings.OCR_PREPROCESS_MAX_LONG_EDGE = 2400

            image_bytes = create_test_image()
            result = extract_text_from_image(image_bytes)
            
            assert "High Conf" in result
            assert "Low Conf" in result
    
    def test_extract_text_grayscale_image(self, mock_reader):
        """Test extraction from grayscale image (mode conversion)."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Grayscale", 0.9),
        ]
        
        # Create a grayscale image
        image = Image.new("L", (400, 300), 128)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        
        result = extract_text_from_image(buffer.read())
        
        assert "Grayscale" in result
    
    def test_extract_text_rgba_image(self, mock_reader):
        """Test extraction from RGBA image (mode conversion)."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "RGBA", 0.9),
        ]
        
        # Create an RGBA image
        image = Image.new("RGBA", (400, 300), (255, 255, 255, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        result = extract_text_from_image(buffer.read())
        
        assert "RGBA" in result


class TestOCRAccuracyMetrics:
    """Tests for OCR accuracy calculations."""
    
    def test_perfect_ocr_accuracy(self):
        """Test perfect OCR accuracy calculation."""
        predicted = "Ingredients: Water, Sugar, Salt"
        ground_truth = "Ingredients: Water, Sugar, Salt"
        
        accuracy = calculate_ocr_accuracy(predicted, ground_truth)
        
        assert accuracy == 1.0
    
    def test_partial_ocr_accuracy(self):
        """Test partial OCR accuracy."""
        predicted = "Ingredients: Water, Sugar"
        ground_truth = "Ingredients: Water, Sugar, Salt"
        
        accuracy = calculate_ocr_accuracy(predicted, ground_truth)
        
        assert 0.7 < accuracy < 1.0
    
    def test_ocr_accuracy_with_errors(self):
        """Test OCR accuracy with common OCR errors."""
        predicted = "lngredients: Water, 5ugar, Sa1t"  # OCR errors
        ground_truth = "Ingredients: Water, Sugar, Salt"
        
        accuracy = calculate_ocr_accuracy(predicted, ground_truth)
        
        # Should be lower due to character errors
        assert 0.7 < accuracy < 1.0
    
    def test_word_accuracy_perfect(self):
        """Test perfect word accuracy."""
        predicted = "Water Sugar Salt"
        ground_truth = "Water Sugar Salt"
        
        accuracy = calculate_word_accuracy(predicted, ground_truth)
        
        assert accuracy == 1.0
    
    def test_word_accuracy_partial(self):
        """Test partial word accuracy."""
        predicted = "Water Sugar"
        ground_truth = "Water Sugar Salt"
        
        accuracy = calculate_word_accuracy(predicted, ground_truth)
        
        assert accuracy == pytest.approx(2/3, rel=0.01)
    
    def test_empty_ground_truth(self):
        """Test accuracy with empty ground truth."""
        assert calculate_ocr_accuracy("some text", "") == 0.0
        assert calculate_ocr_accuracy("", "") == 1.0
    
    def test_empty_predicted(self):
        """Test accuracy with empty prediction."""
        assert calculate_ocr_accuracy("", "expected text") == 0.0


class TestOCREdgeCases:
    """Tests for OCR edge cases and special scenarios."""
    
    @pytest.fixture
    def mock_reader(self):
        """Create a mock OCR reader."""
        with patch('backend.services.ocr.service.get_ocr_reader') as mock:
            mock_reader = MagicMock()
            mock.return_value = mock_reader
            yield mock_reader
    
    def test_special_characters(self, mock_reader):
        """Test extraction with special characters."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [200, 0], [200, 20], [0, 20]], "E471 (Mono-diglycerides)", 0.9),
            ([[0, 25], [200, 25], [200, 45], [0, 45]], "Vitamin C: 100%", 0.9),
        ]
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        assert "E471" in result
        assert "100%" in result
    
    def test_unicode_characters(self, mock_reader):
        """Test extraction with unicode characters."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [200, 0], [200, 20], [0, 20]], "Café Latté", 0.9),
            ([[0, 25], [200, 25], [200, 45], [0, 45]], "日本語テスト", 0.85),
        ]
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        assert "Café" in result
    
    def test_very_long_text(self, mock_reader):
        """Test extraction with very long text."""
        long_text = ", ".join([f"Ingredient{i}" for i in range(50)])
        mock_reader.readtext.return_value = [
            ([[0, 0], [1000, 0], [1000, 20], [0, 20]], long_text, 0.9),
        ]
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        assert "Ingredient0" in result
        assert "Ingredient49" in result
    
    def test_mixed_case_text(self, mock_reader):
        """Test extraction preserves case."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [200, 0], [200, 20], [0, 20]], "WATER, Sugar, salt", 0.9),
        ]
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        assert "WATER" in result
        assert "Sugar" in result
        assert "salt" in result
    
    def test_numeric_text(self, mock_reader):
        """Test extraction of numeric content."""
        mock_reader.readtext.return_value = [
            ([[0, 0], [200, 0], [200, 20], [0, 20]], "E322 E471 E500", 0.9),
            ([[0, 25], [200, 25], [200, 45], [0, 45]], "12345", 0.9),
        ]
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        assert "E322" in result
        assert "12345" in result


class TestSyntheticOCRData:
    """Tests using synthetic OCR data samples."""
    
    @pytest.fixture
    def mock_reader(self):
        """Create a mock OCR reader."""
        with patch('backend.services.ocr.service.get_ocr_reader') as mock:
            mock_reader = MagicMock()
            mock.return_value = mock_reader
            yield mock_reader
    
    def test_synthetic_sample_simple(self, mock_reader):
        """Test with simple synthetic sample."""
        from tests.data.synthetic.ocr_samples import get_synthetic_ocr_samples
        
        sample = get_synthetic_ocr_samples()[0]
        mock_reader.readtext.return_value = [
            ([[0, 0], [500, 0], [500, 20], [0, 20]], sample["ocr_text"], 0.95),
        ]
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        # Calculate accuracy
        accuracy = calculate_ocr_accuracy(result, sample["ground_truth_text"])
        assert accuracy >= 0.9, f"OCR accuracy {accuracy} below 90% target"
    
    def test_synthetic_sample_with_errors(self, mock_reader):
        """Test with synthetic sample containing OCR errors."""
        from tests.data.synthetic.ocr_samples import get_synthetic_ocr_samples
        
        # Get sample with OCR errors (syn_003)
        samples = get_synthetic_ocr_samples()
        error_sample = next((s for s in samples if s["id"] == "syn_003"), samples[0])
        
        mock_reader.readtext.return_value = [
            ([[0, 0], [500, 0], [500, 20], [0, 20]], error_sample["ocr_text"], 0.7),
        ]
        
        image_bytes = create_test_image()
        result = extract_text_from_image(image_bytes)
        
        # With OCR errors, accuracy should be lower but still reasonable
        accuracy = calculate_ocr_accuracy(result, error_sample["ground_truth_text"])
        assert accuracy >= 0.7, f"OCR accuracy {accuracy} too low even with expected errors"


@pytest.mark.unit
class TestOCRReaderSingleton:
    """Tests for OCR reader singleton pattern."""
    
    def test_reader_initialization(self):
        """Test that reader is initialized correctly."""
        with patch('backend.services.ocr.service._ocr_reader', None):
            with patch('backend.services.ocr.service.easyocr') as mock_easyocr:
                mock_reader = MagicMock()
                mock_easyocr.Reader.return_value = mock_reader
                
                reader = get_ocr_reader()
                
                assert reader is not None
                mock_easyocr.Reader.assert_called()
    
    def test_reader_reuse(self):
        """Test that reader is reused (singleton)."""
        with patch('backend.services.ocr.service.easyocr') as mock_easyocr:
            mock_reader = MagicMock()
            mock_easyocr.Reader.return_value = mock_reader
            
            # Reset the singleton
            import backend.services.ocr.service as ocr_module
            original_reader = ocr_module._ocr_reader
            ocr_module._ocr_reader = None
            
            try:
                reader1 = get_ocr_reader()
                reader2 = get_ocr_reader()
                
                # Should only create one instance
                assert mock_easyocr.Reader.call_count == 1
                assert reader1 is reader2
            finally:
                ocr_module._ocr_reader = original_reader
