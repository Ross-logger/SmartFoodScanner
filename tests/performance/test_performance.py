"""
Performance Tests for SmartFoodScanner

Tests for system throughput and response time:
- End-to-end processing time (target: < 10 seconds)
- Throughput with concurrent requests
- Memory usage monitoring
"""

import pytest
import time
import statistics
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

from backend.services.ocr.service import extract_text_from_image
from backend.services.ingredients_extraction.extractor import extract
from backend.services.ingredients_analysis.service import analyze_ingredients
from tests.utils.test_helpers import create_test_image
from tests.data.synthetic.ocr_samples import get_performance_samples


@pytest.mark.performance
@pytest.mark.slow
class TestResponseTime:
    """Tests for response time requirements."""
    
    # Target: < 10 seconds for end-to-end processing
    TARGET_RESPONSE_TIME = 10.0
    
    def test_ocr_response_time(self):
        """Test OCR processing time."""
        image_bytes = create_test_image()
        
        with patch('backend.services.ocr.service.get_ocr_reader') as mock:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = [
                ([[0, 0], [100, 0], [100, 20], [0, 20]], "Ingredients:", 0.95),
                ([[0, 25], [200, 25], [200, 45], [0, 45]], "Water, Sugar, Salt", 0.92),
            ]
            mock.return_value = mock_reader
            
            times = []
            for _ in range(5):
                start = time.time()
                extract_text_from_image(image_bytes)
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = statistics.mean(times)
            
            # OCR should be fast with mocked reader (< 1 second)
            assert avg_time < 1.0, f"OCR average time {avg_time:.2f}s exceeds 1s target"
    
    def test_extraction_response_time(self):
        """Test ingredient extraction processing time."""
        ocr_text = "Ingredients: Water, Sugar, Wheat Flour, Palm Oil, Salt, Natural Flavors"
        
        with patch('backend.services.ingredients_extraction.hugging_face_extractor.extract_ingredients') as mock:
            mock.return_value = ["Water", "Sugar", "Wheat Flour", "Palm Oil", "Salt", "Natural Flavors"]
            
            times = []
            for _ in range(10):
                start = time.time()
                extract(ocr_text)
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = statistics.mean(times)
            
            # Extraction should be fast with mocked model (< 0.5 seconds)
            assert avg_time < 0.5, f"Extraction average time {avg_time:.2f}s exceeds 0.5s target"
    
    def test_analysis_response_time(self):
        """Test dietary analysis processing time."""
        ingredients = ["Water", "Sugar", "Wheat Flour", "Palm Oil", "Salt"]
        
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = True
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock:
            mock.return_value = None  # Force rule-based (faster)
            
            times = []
            for _ in range(20):
                start = time.time()
                analyze_ingredients(ingredients, profile)
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = statistics.mean(times)
            
            # Rule-based analysis should be very fast (< 0.1 seconds)
            assert avg_time < 0.1, f"Analysis average time {avg_time:.2f}s exceeds 0.1s target"
    
    def test_full_pipeline_response_time(self):
        """Test complete pipeline processing time (target: < 10 seconds)."""
        image_bytes = create_test_image()
        
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = True
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        with patch('backend.services.ocr.service.get_ocr_reader') as mock_ocr:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = [
                ([[0, 0], [200, 0], [200, 20], [0, 20]], "Ingredients: Water, Sugar, Wheat Flour, Salt", 0.9),
            ]
            mock_ocr.return_value = mock_reader
            
            with patch('backend.services.ingredients_extraction.hugging_face_extractor.extract_ingredients') as mock_extract:
                mock_extract.return_value = ["Water", "Sugar", "Wheat Flour", "Salt"]
                
                with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
                    mock_llm.return_value = None
                    
                    times = []
                    for _ in range(5):
                        start = time.time()
                        
                        # Full pipeline
                        ocr_text = extract_text_from_image(image_bytes)
                        ingredients = extract(ocr_text)
                        result = analyze_ingredients(ingredients, profile)
                        
                        elapsed = time.time() - start
                        times.append(elapsed)
                    
                    avg_time = statistics.mean(times)
                    max_time = max(times)
                    
                    # Target: < 10 seconds average
                    assert avg_time < self.TARGET_RESPONSE_TIME, \
                        f"Pipeline average time {avg_time:.2f}s exceeds {self.TARGET_RESPONSE_TIME}s target"
                    
                    # No single request should take more than 15 seconds
                    assert max_time < 15.0, \
                        f"Pipeline max time {max_time:.2f}s exceeds 15s limit"


@pytest.mark.performance
@pytest.mark.slow
class TestThroughput:
    """Tests for system throughput."""
    
    def test_concurrent_analysis_requests(self):
        """Test handling multiple concurrent analysis requests."""
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = False
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        samples = get_performance_samples()[:20]  # Use 20 samples
        
        def process_sample(sample):
            with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock:
                mock.return_value = None
                start = time.time()
                result = analyze_ingredients(sample["ingredients"], profile)
                elapsed = time.time() - start
                return elapsed, result["is_safe"]
        
        start_total = time.time()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_sample, s) for s in samples]
            results = [f.result() for f in as_completed(futures)]
        
        total_time = time.time() - start_total
        individual_times = [r[0] for r in results]
        
        # Calculate throughput
        throughput = len(samples) / total_time
        
        # Should handle at least 5 requests per second
        assert throughput >= 5.0, \
            f"Throughput {throughput:.2f} req/s below 5 req/s target"
        
        # Average individual time should be reasonable
        avg_individual = statistics.mean(individual_times)
        assert avg_individual < 0.5, \
            f"Average individual time {avg_individual:.2f}s exceeds 0.5s"
    
    def test_sequential_requests_throughput(self):
        """Test sequential request throughput."""
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = True
        profile.vegetarian = True
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        samples = get_performance_samples()[:50]  # Use 50 samples
        
        start = time.time()
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock:
            mock.return_value = None
            
            for sample in samples:
                analyze_ingredients(sample["ingredients"], profile)
        
        total_time = time.time() - start
        throughput = len(samples) / total_time
        
        # Should process at least 20 requests per second sequentially
        assert throughput >= 20.0, \
            f"Sequential throughput {throughput:.2f} req/s below 20 req/s target"


@pytest.mark.performance
class TestScalability:
    """Tests for system scalability."""
    
    def test_large_ingredient_list_performance(self):
        """Test performance with large ingredient lists."""
        # Create a large ingredient list
        large_ingredients = [f"Ingredient{i}" for i in range(100)]
        
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = True
        profile.vegetarian = True
        profile.vegan = True
        profile.nut_free = True
        profile.dairy_free = True
        profile.allergens = ["allergen1", "allergen2", "allergen3"]
        profile.custom_restrictions = []
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock:
            mock.return_value = None
            
            times = []
            for _ in range(5):
                start = time.time()
                analyze_ingredients(large_ingredients, profile)
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = statistics.mean(times)
            
            # Should handle 100 ingredients in < 0.5 seconds
            assert avg_time < 0.5, \
                f"Large list processing {avg_time:.2f}s exceeds 0.5s target"
    
    def test_complex_profile_performance(self):
        """Test performance with complex dietary profile."""
        ingredients = ["Water", "Sugar", "Wheat Flour", "Milk", "Eggs", "Peanuts"]
        
        # Profile with all restrictions and multiple allergens
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = True
        profile.vegetarian = True
        profile.vegan = True
        profile.nut_free = True
        profile.dairy_free = True
        profile.allergens = [f"allergen{i}" for i in range(20)]  # 20 custom allergens
        profile.custom_restrictions = [f"restriction{i}" for i in range(10)]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock:
            mock.return_value = None
            
            times = []
            for _ in range(10):
                start = time.time()
                analyze_ingredients(ingredients, profile)
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = statistics.mean(times)
            
            # Complex profile should not significantly impact performance
            assert avg_time < 0.2, \
                f"Complex profile processing {avg_time:.2f}s exceeds 0.2s target"
    
    def test_extraction_scalability(self):
        """Test extraction performance with various text lengths."""
        # Short text
        short_text = "Ingredients: Water, Sugar, Salt"
        
        # Medium text
        medium_text = "Ingredients: " + ", ".join([f"Ingredient{i}" for i in range(20)])
        
        # Long text
        long_text = "Ingredients: " + ", ".join([f"Ingredient{i}" for i in range(100)])
        
        with patch('backend.services.ingredients_extraction.hugging_face_extractor.extract_ingredients') as mock:
            mock.return_value = ["Water", "Sugar", "Salt"]  # Mock returns same for all
            
            results = {}
            for name, text in [("short", short_text), ("medium", medium_text), ("long", long_text)]:
                times = []
                for _ in range(5):
                    start = time.time()
                    extract(text)
                    elapsed = time.time() - start
                    times.append(elapsed)
                results[name] = statistics.mean(times)
            
            # All should be fast with mocked extraction
            # Note: Allowing more time for longer texts to account for system variations
            # Short/medium texts should be faster, long texts can take more time
            time_limits = {"short": 0.2, "medium": 0.3, "long": 0.5}
            for name, avg_time in results.items():
                limit = time_limits.get(name, 0.5)
                assert avg_time < limit, \
                    f"{name} text extraction {avg_time:.2f}s exceeds {limit}s target"


@pytest.mark.performance
class TestPerformanceMetrics:
    """Tests for performance metrics collection."""
    
    def test_response_time_percentiles(self):
        """Test response time percentile calculations."""
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = False
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        ingredients = ["Water", "Sugar", "Salt", "Wheat Flour"]
        
        with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock:
            mock.return_value = None
            
            times = []
            for _ in range(100):
                start = time.time()
                analyze_ingredients(ingredients, profile)
                elapsed = time.time() - start
                times.append(elapsed)
        
        times.sort()
        
        # Calculate percentiles
        p50 = times[50]
        p90 = times[90]
        p95 = times[95]
        p99 = times[99]
        
        # P50 should be very fast
        assert p50 < 0.05, f"P50 {p50:.4f}s exceeds 0.05s"
        
        # P95 should still be fast
        assert p95 < 0.1, f"P95 {p95:.4f}s exceeds 0.1s"
        
        # P99 should be acceptable
        assert p99 < 0.2, f"P99 {p99:.4f}s exceeds 0.2s"
    
    def test_performance_summary_report(self):
        """Generate a performance summary report."""
        profile = MagicMock()
        profile.halal = True
        profile.gluten_free = True
        profile.vegetarian = False
        profile.vegan = False
        profile.nut_free = False
        profile.dairy_free = False
        profile.allergens = []
        profile.custom_restrictions = []
        
        samples = get_performance_samples()[:30]
        
        ocr_times = []
        extraction_times = []
        analysis_times = []
        total_times = []
        
        with patch('backend.services.ocr.service.get_ocr_reader') as mock_ocr:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = [
                ([[0, 0], [200, 0], [200, 20], [0, 20]], "Test text", 0.9),
            ]
            mock_ocr.return_value = mock_reader
            
            with patch('backend.services.ingredients_extraction.hugging_face_extractor.extract_ingredients') as mock_extract:
                mock_extract.side_effect = lambda x: ["Water", "Sugar", "Salt"]
                
                with patch('backend.services.ingredients_analysis.service.analyze_with_llm') as mock_llm:
                    mock_llm.return_value = None
                    
                    image_bytes = create_test_image()
                    
                    for sample in samples:
                        total_start = time.time()
                        
                        # OCR
                        start = time.time()
                        ocr_text = extract_text_from_image(image_bytes)
                        ocr_times.append(time.time() - start)
                        
                        # Extraction
                        start = time.time()
                        ingredients = extract(sample["ocr_text"])
                        extraction_times.append(time.time() - start)
                        
                        # Analysis
                        start = time.time()
                        result = analyze_ingredients(sample["ingredients"], profile)
                        analysis_times.append(time.time() - start)
                        
                        total_times.append(time.time() - total_start)
        
        # Generate summary
        summary = {
            "samples": len(samples),
            "ocr": {
                "avg": statistics.mean(ocr_times),
                "max": max(ocr_times),
                "min": min(ocr_times),
            },
            "extraction": {
                "avg": statistics.mean(extraction_times),
                "max": max(extraction_times),
                "min": min(extraction_times),
            },
            "analysis": {
                "avg": statistics.mean(analysis_times),
                "max": max(analysis_times),
                "min": min(analysis_times),
            },
            "total": {
                "avg": statistics.mean(total_times),
                "max": max(total_times),
                "min": min(total_times),
            },
        }
        
        # Verify target is met
        assert summary["total"]["avg"] < 10.0, \
            f"Average total time {summary['total']['avg']:.2f}s exceeds 10s target"
        
        # Print summary for informational purposes
        print("\n=== Performance Summary ===")
        print(f"Samples tested: {summary['samples']}")
        print(f"OCR: avg={summary['ocr']['avg']:.4f}s, max={summary['ocr']['max']:.4f}s")
        print(f"Extraction: avg={summary['extraction']['avg']:.4f}s, max={summary['extraction']['max']:.4f}s")
        print(f"Analysis: avg={summary['analysis']['avg']:.4f}s, max={summary['analysis']['max']:.4f}s")
        print(f"Total: avg={summary['total']['avg']:.4f}s, max={summary['total']['max']:.4f}s")
        print("===========================")
