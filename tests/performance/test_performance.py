"""
Performance Tests for SmartFoodScanner

Tests for system throughput and response time:
- End-to-end processing time (target: < 10 seconds)
- Throughput with concurrent requests
- Memory usage monitoring

NOTE: These are real performance tests - NO MOCKING.
All services are called with real implementations.
"""

import pytest
import time
import statistics
from dataclasses import dataclass, field
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.services.barcode.openfoodfacts import fetch_product
from backend.services.ocr.service import extract_text_from_image
from backend.services.ingredients_extraction.extractor import extract
from backend.services.ingredients_extraction import extract_ingredients_with_llm
from backend.services.ingredients_analysis.service import analyze_ingredients
from tests.utils.test_helpers import create_test_image, create_test_image_with_text
from tests.data.synthetic.ocr_samples import get_performance_samples


# =============================================================================
# PERFORMANCE CONSTANTS - All timing targets and thresholds
# =============================================================================

# Response Time Targets (in seconds)
TARGET_FULL_PIPELINE_TIME = 12.0  # End-to-end processing target
TARGET_MAX_SINGLE_REQUEST_TIME = 15.0  # Max time for any single request
TARGET_OCR_TIME = 5.0  # OCR processing target
TARGET_BARCODE_TIME = 3.0  # Barcode lookup target (network dependent)
TARGET_EXTRACTION_TIME = 5.0  # Ingredient extraction target (uses LLM/model)
TARGET_ANALYSIS_TIME = 5.0  # Dietary analysis target (uses LLM)

# Scalability Targets (in seconds)
TARGET_LARGE_INGREDIENT_LIST_TIME = 8.0  # 100 ingredients
TARGET_COMPLEX_PROFILE_TIME = 6.0  # All restrictions enabled
TARGET_SHORT_TEXT_EXTRACTION_TIME = 5.0
TARGET_MEDIUM_TEXT_EXTRACTION_TIME = 6.0
TARGET_LONG_TEXT_EXTRACTION_TIME = 8.0

# Throughput Targets
TARGET_CONCURRENT_THROUGHPUT = 0.5  # Requests per second (4 workers)
TARGET_SEQUENTIAL_THROUGHPUT = 1.0  # Requests per second
TARGET_INDIVIDUAL_REQUEST_TIME = 5.0  # Per-request time in concurrent tests

# Percentile Targets (in seconds)
TARGET_P50_TIME = 3.0
TARGET_P95_TIME = 6.0
TARGET_P99_TIME = 8.0

# Test Configuration
NUM_WARMUP_ITERATIONS = 1  # Warmup calls before timing
NUM_TIMING_ITERATIONS_SMALL = 3  # For slow tests
NUM_TIMING_ITERATIONS_MEDIUM = 5  # For medium tests
NUM_TIMING_ITERATIONS_LARGE = 10  # For percentile tests
NUM_CONCURRENT_SAMPLES = 10
NUM_SEQUENTIAL_SAMPLES = 20

# Test Data
TEST_BARCODE = "5000159407236"  # A known product barcode
TEST_INGREDIENTS_SIMPLE = ["Water", "Sugar", "Wheat Flour", "Palm Oil", "Salt"]
TEST_INGREDIENTS_COMPLEX = ["Water", "Sugar", "Wheat Flour", "Milk", "Eggs", "Peanuts"]
TEST_INGREDIENTS_LARGE = [f"Ingredient{i}" for i in range(100)]
TEST_OCR_TEXT = "Ingredients: Water, Sugar, Wheat Flour, Palm Oil, Salt, Natural Flavors"
TEST_IMAGE_TEXT = "Ingredients: Water, Sugar, Wheat Flour, Salt, Yeast, Natural Flavors"


# =============================================================================
# TEST DATA CLASSES
# =============================================================================

@dataclass
class DietaryProfileData:
    """
    Test dietary profile data class.
    Mimics the DietaryProfile SQLAlchemy model for testing.
    """
    halal: bool = False
    gluten_free: bool = False
    vegetarian: bool = False
    vegan: bool = False
    nut_free: bool = False
    dairy_free: bool = False
    allergens: List[str] = field(default_factory=list)
    custom_restrictions: List[str] = field(default_factory=list)


# Pre-defined test profiles
PROFILE_HALAL_GLUTEN_FREE = DietaryProfileData(halal=True, gluten_free=True)
PROFILE_HALAL = DietaryProfileData(halal=True)
PROFILE_ALL_RESTRICTIONS = DietaryProfileData(
    halal=True,
    gluten_free=True,
    vegetarian=True,
    vegan=True,
    nut_free=True,
    dairy_free=True,
)
PROFILE_COMPLEX = DietaryProfileData(
    halal=True,
    gluten_free=True,
    vegetarian=True,
    vegan=True,
    nut_free=True,
    dairy_free=True,
    allergens=[f"allergen{i}" for i in range(20)],
    custom_restrictions=[f"restriction{i}" for i in range(10)],
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def measure_time(func, *args, **kwargs):
    """Execute function and return (result, elapsed_time)."""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed


def run_timed_iterations(func, iterations: int, *args, **kwargs) -> List[float]:
    """Run function multiple times and return list of execution times."""
    times = []
    for _ in range(iterations):
        _, elapsed = measure_time(func, *args, **kwargs)
        times.append(elapsed)
    return times


def warmup(func, iterations: int = 1, *args, **kwargs):
    """Run warmup iterations (not timed)."""
    for _ in range(iterations):
        try:
            func(*args, **kwargs)
        except Exception:
            pass  # Ignore errors during warmup


# =============================================================================
# RESPONSE TIME TESTS
# =============================================================================

@pytest.mark.performance
@pytest.mark.slow
class TestResponseTime:
    """Tests for response time requirements."""

    def test_ocr_response_time(self):
        """Test OCR processing time with real OCR engine."""
        image_bytes = create_test_image_with_text(TEST_IMAGE_TEXT)
        
        # Warmup
        warmup(extract_text_from_image, NUM_WARMUP_ITERATIONS, image_bytes)
        
        # Measure
        times = run_timed_iterations(
            extract_text_from_image, 
            NUM_TIMING_ITERATIONS_SMALL, 
            image_bytes
        )
        avg_time = statistics.mean(times)
        
        assert avg_time < TARGET_OCR_TIME, \
            f"OCR processing time {avg_time:.2f}s exceeds {TARGET_OCR_TIME}s target"

    def test_barcode_response_time(self):
        """Test barcode lookup time with real API call."""
        # Warmup
        warmup(fetch_product, NUM_WARMUP_ITERATIONS, TEST_BARCODE)
        
        # Measure
        times = run_timed_iterations(
            fetch_product, 
            NUM_TIMING_ITERATIONS_SMALL, 
            TEST_BARCODE
        )
        avg_time = statistics.mean(times)
        
        assert avg_time < TARGET_BARCODE_TIME, \
            f"Barcode lookup time {avg_time:.2f}s exceeds {TARGET_BARCODE_TIME}s target"

    def test_extraction_response_time(self):
        """Test ingredient extraction time with real extraction service."""
        # Warmup
        warmup(extract, NUM_WARMUP_ITERATIONS, TEST_OCR_TEXT)
        
        # Measure
        times = run_timed_iterations(
            extract, 
            NUM_TIMING_ITERATIONS_SMALL, 
            TEST_OCR_TEXT
        )
        avg_time = statistics.mean(times)
        
        assert avg_time < TARGET_EXTRACTION_TIME, \
            f"Extraction time {avg_time:.2f}s exceeds {TARGET_EXTRACTION_TIME}s target"

    def test_analysis_response_time(self):
        """Test dietary analysis time with real analysis service."""
        profile = PROFILE_HALAL_GLUTEN_FREE
        
        # Warmup
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, TEST_INGREDIENTS_SIMPLE, profile)
        
        # Measure
        times = run_timed_iterations(
            analyze_ingredients, 
            NUM_TIMING_ITERATIONS_SMALL, 
            TEST_INGREDIENTS_SIMPLE, 
            profile
        )
        avg_time = statistics.mean(times)
        
        assert avg_time < TARGET_ANALYSIS_TIME, \
            f"Analysis time {avg_time:.2f}s exceeds {TARGET_ANALYSIS_TIME}s target"

    def test_full_pipeline_response_time(self):
        """Test complete pipeline processing time (target: < 10 seconds)."""
        image_bytes = create_test_image_with_text(TEST_IMAGE_TEXT)
        profile = PROFILE_HALAL_GLUTEN_FREE
        
        def full_pipeline():
            # Step 1: OCR
            ocr_text = extract_text_from_image(image_bytes)
            # Step 2: Extraction
            ingredients = extract(ocr_text)
            # Step 3: Analysis
            result = analyze_ingredients(ingredients, profile)
            return result
        
        # Warmup
        warmup(full_pipeline, NUM_WARMUP_ITERATIONS)
        
        # Measure
        times = run_timed_iterations(full_pipeline, NUM_TIMING_ITERATIONS_SMALL)
        
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        assert avg_time < TARGET_FULL_PIPELINE_TIME, \
            f"Pipeline average time {avg_time:.2f}s exceeds {TARGET_FULL_PIPELINE_TIME}s target"
        
        assert max_time < TARGET_MAX_SINGLE_REQUEST_TIME, \
            f"Pipeline max time {max_time:.2f}s exceeds {TARGET_MAX_SINGLE_REQUEST_TIME}s limit"


# =============================================================================
# THROUGHPUT TESTS
# =============================================================================

@pytest.mark.performance
@pytest.mark.slow
class TestThroughput:
    """Tests for system throughput."""

    def test_concurrent_analysis_requests(self):
        """Test handling multiple concurrent analysis requests."""
        profile = PROFILE_HALAL
        samples = get_performance_samples()[:NUM_CONCURRENT_SAMPLES]
        
        def process_sample(sample):
            start = time.time()
            result = analyze_ingredients(sample["ingredients"], profile)
            elapsed = time.time() - start
            return elapsed, result["is_safe"]
        
        # Warmup with one sample
        warmup(process_sample, 1, samples[0])
        
        start_total = time.time()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_sample, s) for s in samples]
            results = [f.result() for f in as_completed(futures)]
        
        total_time = time.time() - start_total
        individual_times = [r[0] for r in results]
        
        # Calculate throughput
        throughput = len(samples) / total_time
        
        assert throughput >= TARGET_CONCURRENT_THROUGHPUT, \
            f"Throughput {throughput:.2f} req/s below {TARGET_CONCURRENT_THROUGHPUT} req/s target"
        
        avg_individual = statistics.mean(individual_times)
        assert avg_individual < TARGET_INDIVIDUAL_REQUEST_TIME, \
            f"Average individual time {avg_individual:.2f}s exceeds {TARGET_INDIVIDUAL_REQUEST_TIME}s"

    def test_sequential_requests_throughput(self):
        """Test sequential request throughput."""
        profile = PROFILE_HALAL_GLUTEN_FREE
        samples = get_performance_samples()[:NUM_SEQUENTIAL_SAMPLES]
        
        # Warmup
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, samples[0]["ingredients"], profile)
        
        start = time.time()
        
        for sample in samples:
            analyze_ingredients(sample["ingredients"], profile)
        
        total_time = time.time() - start
        throughput = len(samples) / total_time
        
        assert throughput >= TARGET_SEQUENTIAL_THROUGHPUT, \
            f"Sequential throughput {throughput:.2f} req/s below {TARGET_SEQUENTIAL_THROUGHPUT} req/s target"


# =============================================================================
# SCALABILITY TESTS
# =============================================================================

@pytest.mark.performance
class TestScalability:
    """Tests for system scalability."""

    def test_large_ingredient_list_performance(self):
        """Test performance with large ingredient lists (100 ingredients)."""
        profile = PROFILE_ALL_RESTRICTIONS
        
        # Warmup
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, TEST_INGREDIENTS_LARGE, profile)
        
        # Measure
        times = run_timed_iterations(
            analyze_ingredients, 
            NUM_TIMING_ITERATIONS_SMALL, 
            TEST_INGREDIENTS_LARGE, 
            profile
        )
        avg_time = statistics.mean(times)
        
        assert avg_time < TARGET_LARGE_INGREDIENT_LIST_TIME, \
            f"Large list processing {avg_time:.2f}s exceeds {TARGET_LARGE_INGREDIENT_LIST_TIME}s target"

    def test_complex_profile_performance(self):
        """Test performance with complex dietary profile (all restrictions + custom allergens)."""
        profile = PROFILE_COMPLEX
        
        # Warmup
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, TEST_INGREDIENTS_COMPLEX, profile)
        
        # Measure
        times = run_timed_iterations(
            analyze_ingredients, 
            NUM_TIMING_ITERATIONS_SMALL, 
            TEST_INGREDIENTS_COMPLEX, 
            profile
        )
        avg_time = statistics.mean(times)
        
        assert avg_time < TARGET_COMPLEX_PROFILE_TIME, \
            f"Complex profile processing {avg_time:.2f}s exceeds {TARGET_COMPLEX_PROFILE_TIME}s target"

    def test_extraction_scalability(self):
        """Test extraction performance with various text lengths."""
        # Short text
        short_text = "Ingredients: Water, Sugar, Salt"
        
        # Medium text (20 ingredients)
        medium_text = "Ingredients: " + ", ".join([f"Ingredient{i}" for i in range(20)])
        
        # Long text (100 ingredients)
        long_text = "Ingredients: " + ", ".join([f"Ingredient{i}" for i in range(100)])
        
        time_limits = {
            "short": TARGET_SHORT_TEXT_EXTRACTION_TIME,
            "medium": TARGET_MEDIUM_TEXT_EXTRACTION_TIME,
            "long": TARGET_LONG_TEXT_EXTRACTION_TIME,
        }
        
        results = {}
        for name, text in [("short", short_text), ("medium", medium_text), ("long", long_text)]:
            # Warmup for each
            warmup(extract, NUM_WARMUP_ITERATIONS, text)
            
            # Measure
            times = run_timed_iterations(extract, NUM_TIMING_ITERATIONS_SMALL, text)
            results[name] = statistics.mean(times)
        
        for name, avg_time in results.items():
            limit = time_limits[name]
            assert avg_time < limit, \
                f"{name} text extraction {avg_time:.2f}s exceeds {limit}s target"


# =============================================================================
# PERFORMANCE METRICS TESTS
# =============================================================================

@pytest.mark.performance
class TestPerformanceMetrics:
    """Tests for performance metrics collection."""

    def test_response_time_percentiles(self):
        """Test response time percentile calculations."""
        profile = PROFILE_HALAL
        ingredients = TEST_INGREDIENTS_SIMPLE
        
        # Warmup
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, ingredients, profile)
        
        # Measure
        times = run_timed_iterations(
            analyze_ingredients, 
            NUM_TIMING_ITERATIONS_LARGE, 
            ingredients, 
            profile
        )
        times.sort()
        
        # Calculate percentiles
        n = len(times)
        p50 = times[int(n * 0.50)]
        p90 = times[int(n * 0.90)]
        p95 = times[int(n * 0.95)]
        p99 = times[min(int(n * 0.99), n - 1)]
        
        # P50 should be within target
        assert p50 < TARGET_P50_TIME, f"P50 {p50:.4f}s exceeds {TARGET_P50_TIME}s"
        
        # P95 should still be acceptable
        assert p95 < TARGET_P95_TIME, f"P95 {p95:.4f}s exceeds {TARGET_P95_TIME}s"
        
        # P99 should be within limit
        assert p99 < TARGET_P99_TIME, f"P99 {p99:.4f}s exceeds {TARGET_P99_TIME}s"

    def test_performance_summary_report(self):
        """Generate a performance summary report."""
        profile = PROFILE_HALAL_GLUTEN_FREE
        samples = get_performance_samples()[:10]  # Use fewer samples for real tests
        
        image_bytes = create_test_image_with_text(TEST_IMAGE_TEXT)
        
        ocr_times = []
        extraction_times = []
        analysis_times = []
        total_times = []
        
        # Warmup
        try:
            extract_text_from_image(image_bytes)
            extract(samples[0]["ocr_text"])
            analyze_ingredients(samples[0]["ingredients"], profile)
        except Exception:
            pass
        
        for sample in samples:
            total_start = time.time()
            
            # OCR
            _, ocr_elapsed = measure_time(extract_text_from_image, image_bytes)
            ocr_times.append(ocr_elapsed)
            
            # Extraction
            _, extract_elapsed = measure_time(extract, sample["ocr_text"])
            extraction_times.append(extract_elapsed)
            
            # Analysis
            _, analysis_elapsed = measure_time(
                analyze_ingredients, sample["ingredients"], profile
            )
            analysis_times.append(analysis_elapsed)
            
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
        assert summary["total"]["avg"] < TARGET_FULL_PIPELINE_TIME, \
            f"Average total time {summary['total']['avg']:.2f}s exceeds {TARGET_FULL_PIPELINE_TIME}s target"
        
        # Print summary for informational purposes
        print("\n=== Performance Summary (REAL SERVICES) ===")
        print(f"Samples tested: {summary['samples']}")
        print(f"OCR: avg={summary['ocr']['avg']:.4f}s, max={summary['ocr']['max']:.4f}s, min={summary['ocr']['min']:.4f}s")
        print(f"Extraction: avg={summary['extraction']['avg']:.4f}s, max={summary['extraction']['max']:.4f}s, min={summary['extraction']['min']:.4f}s")
        print(f"Analysis: avg={summary['analysis']['avg']:.4f}s, max={summary['analysis']['max']:.4f}s, min={summary['analysis']['min']:.4f}s")
        print(f"Total: avg={summary['total']['avg']:.4f}s, max={summary['total']['max']:.4f}s, min={summary['total']['min']:.4f}s")
        print("============================================")

