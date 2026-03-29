"""
Performance Tests for SmartFoodScanner

Tests for system throughput and response time:
- End-to-end processing time (target: < 10 seconds)
- Throughput with concurrent requests
- Memory usage monitoring
- Full-pipeline comparison: LLM-based vs model-based on real images

NOTE: These are real performance tests - NO MOCKING.
All services are called with real implementations.

Usage (full-pipeline comparison on real images):
  pytest tests/performance/test_performance.py::TestFullPipelineComparison -v -s
  pytest tests/performance/test_performance.py::TestFullPipelineComparison -v -s --perf-num-images 5
  pytest tests/performance/test_performance.py::TestFullPipelineComparison -v -s --perf-images-dir tests/data/images --perf-output results.json
"""

import json
import re
import time
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from backend.services.barcode.openfoodfacts import fetch_product
from backend.services.ocr.service import (
    extract_ocr_from_image,
    extract_text_from_image,
    extract_text_with_mistral_ocr,
)
from backend.services.ingredients_extraction import extract_ingredients_with_llm
from backend.services.ingredients_extraction.ingredient_box_classifier import (
    classify_boxes,
    extract_ingredients_from_boxes,
)
from backend.services.ingredients_extraction.ocr_corrector import correct_ingredient_list
from backend.services.ingredients_extraction.utils import split_ingredients_text
from backend.services.ingredients_analysis.service import analyze_ingredients
from backend import settings
from tests.utils.test_helpers import create_test_image, create_test_image_with_text


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_IMAGES_DIR = PROJECT_ROOT / "tests" / "data" / "images"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "tests" / "data" / "performance_results.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


# =============================================================================
# PERFORMANCE CONSTANTS - All timing targets and thresholds
# =============================================================================

TARGET_FULL_PIPELINE_TIME = 12.0
TARGET_MAX_SINGLE_REQUEST_TIME = 15.0
TARGET_OCR_TIME = 5.0
TARGET_BARCODE_TIME = 3.0
TARGET_EXTRACTION_TIME = 5.0
TARGET_ANALYSIS_TIME = 5.0

TARGET_LARGE_INGREDIENT_LIST_TIME = 8.0
TARGET_COMPLEX_PROFILE_TIME = 6.0
TARGET_SHORT_TEXT_EXTRACTION_TIME = 5.0
TARGET_MEDIUM_TEXT_EXTRACTION_TIME = 6.0
TARGET_LONG_TEXT_EXTRACTION_TIME = 8.0

TARGET_CONCURRENT_THROUGHPUT = 0.5
TARGET_SEQUENTIAL_THROUGHPUT = 1.0
TARGET_INDIVIDUAL_REQUEST_TIME = 5.0

TARGET_P50_TIME = 3.0
TARGET_P95_TIME = 6.0
TARGET_P99_TIME = 8.0

NUM_WARMUP_ITERATIONS = 1
NUM_TIMING_ITERATIONS_SMALL = 3
NUM_TIMING_ITERATIONS_MEDIUM = 5
NUM_TIMING_ITERATIONS_LARGE = 10
NUM_CONCURRENT_SAMPLES = 10
NUM_SEQUENTIAL_SAMPLES = 20

TEST_BARCODE = "5000159407236"
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


PROFILE_HALAL_GLUTEN_FREE = DietaryProfileData(halal=True, gluten_free=True)
PROFILE_HALAL = DietaryProfileData(halal=True)
PROFILE_ALL_RESTRICTIONS = DietaryProfileData(
    halal=True, gluten_free=True, vegetarian=True,
    vegan=True, nut_free=True, dairy_free=True,
)
PROFILE_COMPLEX = DietaryProfileData(
    halal=True, gluten_free=True, vegetarian=True,
    vegan=True, nut_free=True, dairy_free=True,
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
            pass


def _natural_sort_key(path: Path):
    """Sort by natural numeric order (in0, in1, in2, in10, not in0, in1, in10, in2)."""
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _discover_images(images_dir: Path, limit: Optional[int] = None) -> List[Path]:
    """Discover image files in a directory, sorted naturally, optionally limited."""
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    image_files = sorted(
        (f for f in images_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS),
        key=_natural_sort_key,
    )
    if limit is not None and limit > 0:
        image_files = image_files[:limit]
    return image_files


def _stats(times: List[float]) -> Dict[str, float]:
    """Compute summary statistics for a list of timings."""
    if not times:
        return {"avg": 0.0, "min": 0.0, "max": 0.0, "median": 0.0, "stdev": 0.0, "count": 0}
    return {
        "avg": round(statistics.mean(times), 4),
        "min": round(min(times), 4),
        "max": round(max(times), 4),
        "median": round(statistics.median(times), 4),
        "stdev": round(statistics.stdev(times), 4) if len(times) >= 2 else 0.0,
        "count": len(times),
    }


# =============================================================================
# PIPELINE RUNNERS
# =============================================================================

def run_model_pipeline(image_data: bytes, profile) -> Dict[str, Any]:
    """
    Model-based pipeline: EasyOCR -> box classifier -> merge -> OCR corrector -> analysis.
    Returns per-stage timings and results.
    """
    ocr_start = time.perf_counter()
    ocr_result = extract_ocr_from_image(image_data, use_mistral_ocr=False)
    ocr_time = time.perf_counter() - ocr_start

    extract_start = time.perf_counter()
    ingredients: List[str] = []
    merged_text = ""
    if ocr_result.easyocr_raw_results:
        df_boxes = classify_boxes(ocr_result.easyocr_raw_results)
        merged_text = extract_ingredients_from_boxes(df_boxes)
        if merged_text.strip():
            candidates = split_ingredients_text(merged_text)
            ingredients_list = correct_ingredient_list(
                candidates, use_ocr_corrector=settings.USE_OCR_CORRECTOR,
            )
            if ingredients_list:
                ingredients = [", ".join(ingredients_list)]
    extract_time = time.perf_counter() - extract_start

    analysis_start = time.perf_counter()
    analysis = analyze_ingredients(ingredients, profile)
    analysis_time = time.perf_counter() - analysis_start

    return {
        "ocr_text": ocr_result.text[:200],
        "merged_text": merged_text[:200] if merged_text else "",
        "ingredients": ingredients,
        "is_safe": analysis.get("is_safe"),
        "ocr_time": round(ocr_time, 4),
        "extraction_time": round(extract_time, 4),
        "analysis_time": round(analysis_time, 4),
        "total_time": round(ocr_time + extract_time + analysis_time, 4),
    }


def run_llm_pipeline(image_data: bytes, profile) -> Dict[str, Any]:
    """
    LLM-based pipeline: Mistral OCR (no cache) -> LLM extraction -> analysis.
    Returns per-stage timings and results.
    """
    ocr_start = time.perf_counter()
    ocr_text = extract_text_with_mistral_ocr(image_data)
    ocr_time = time.perf_counter() - ocr_start

    extract_start = time.perf_counter()
    llm_result = extract_ingredients_with_llm(ocr_text)
    ingredients = llm_result.get("ingredients", []) if llm_result.get("success") else []
    extract_time = time.perf_counter() - extract_start

    analysis_start = time.perf_counter()
    analysis = analyze_ingredients(ingredients, profile)
    analysis_time = time.perf_counter() - analysis_start

    return {
        "ocr_text": ocr_text[:200],
        "ingredients": ingredients,
        "is_safe": analysis.get("is_safe"),
        "ocr_time": round(ocr_time, 4),
        "extraction_time": round(extract_time, 4),
        "analysis_time": round(analysis_time, 4),
        "total_time": round(ocr_time + extract_time + analysis_time, 4),
    }


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
        warmup(extract_text_from_image, NUM_WARMUP_ITERATIONS, image_bytes)
        times = run_timed_iterations(extract_text_from_image, NUM_TIMING_ITERATIONS_SMALL, image_bytes)
        avg_time = statistics.mean(times)
        assert avg_time < TARGET_OCR_TIME, \
            f"OCR processing time {avg_time:.2f}s exceeds {TARGET_OCR_TIME}s target"

    def test_barcode_response_time(self):
        """Test barcode lookup time with real API call."""
        warmup(fetch_product, NUM_WARMUP_ITERATIONS, TEST_BARCODE)
        times = run_timed_iterations(fetch_product, NUM_TIMING_ITERATIONS_SMALL, TEST_BARCODE)
        avg_time = statistics.mean(times)
        assert avg_time < TARGET_BARCODE_TIME, \
            f"Barcode lookup time {avg_time:.2f}s exceeds {TARGET_BARCODE_TIME}s target"

    def test_analysis_response_time(self):
        """Test dietary analysis time with real analysis service."""
        profile = PROFILE_HALAL_GLUTEN_FREE
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, TEST_INGREDIENTS_SIMPLE, profile)
        times = run_timed_iterations(
            analyze_ingredients, NUM_TIMING_ITERATIONS_SMALL,
            TEST_INGREDIENTS_SIMPLE, profile,
        )
        avg_time = statistics.mean(times)
        assert avg_time < TARGET_ANALYSIS_TIME, \
            f"Analysis time {avg_time:.2f}s exceeds {TARGET_ANALYSIS_TIME}s target"

    def test_full_pipeline_response_time(self):
        """Test complete model-based pipeline processing time."""
        image_bytes = create_test_image_with_text(TEST_IMAGE_TEXT)
        profile = PROFILE_HALAL_GLUTEN_FREE

        def full_pipeline():
            return run_model_pipeline(image_bytes, profile)

        warmup(full_pipeline, NUM_WARMUP_ITERATIONS)
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
        ingredient_lists = [
            TEST_INGREDIENTS_SIMPLE,
            TEST_INGREDIENTS_COMPLEX,
            ["Water", "Sugar", "Salt", "Flour"],
            ["Milk", "Butter", "Cream", "Whey"],
            ["Soy Lecithin", "Palm Oil", "Cocoa Butter"],
            TEST_INGREDIENTS_SIMPLE,
            TEST_INGREDIENTS_COMPLEX,
            ["Rice", "Corn Starch", "Tapioca"],
            ["Gelatin", "Beef Extract", "Lard"],
            ["Oat Flour", "Barley Malt", "Rye"],
        ][:NUM_CONCURRENT_SAMPLES]

        def process_ingredients(ingredients):
            start = time.time()
            result = analyze_ingredients(ingredients, profile)
            elapsed = time.time() - start
            return elapsed, result["is_safe"]

        warmup(process_ingredients, 1, ingredient_lists[0])
        start_total = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_ingredients, ing) for ing in ingredient_lists]
            results = [f.result() for f in as_completed(futures)]
        total_time = time.time() - start_total
        individual_times = [r[0] for r in results]
        throughput = len(ingredient_lists) / total_time
        assert throughput >= TARGET_CONCURRENT_THROUGHPUT, \
            f"Throughput {throughput:.2f} req/s below {TARGET_CONCURRENT_THROUGHPUT} req/s target"
        avg_individual = statistics.mean(individual_times)
        assert avg_individual < TARGET_INDIVIDUAL_REQUEST_TIME, \
            f"Average individual time {avg_individual:.2f}s exceeds {TARGET_INDIVIDUAL_REQUEST_TIME}s"

    def test_sequential_requests_throughput(self):
        """Test sequential request throughput."""
        profile = PROFILE_HALAL_GLUTEN_FREE
        ingredient_lists = [TEST_INGREDIENTS_SIMPLE, TEST_INGREDIENTS_COMPLEX] * 10
        ingredient_lists = ingredient_lists[:NUM_SEQUENTIAL_SAMPLES]
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, ingredient_lists[0], profile)
        start = time.time()
        for ingredients in ingredient_lists:
            analyze_ingredients(ingredients, profile)
        total_time = time.time() - start
        throughput = len(ingredient_lists) / total_time
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
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, TEST_INGREDIENTS_LARGE, profile)
        times = run_timed_iterations(
            analyze_ingredients, NUM_TIMING_ITERATIONS_SMALL,
            TEST_INGREDIENTS_LARGE, profile,
        )
        avg_time = statistics.mean(times)
        assert avg_time < TARGET_LARGE_INGREDIENT_LIST_TIME, \
            f"Large list processing {avg_time:.2f}s exceeds {TARGET_LARGE_INGREDIENT_LIST_TIME}s target"

    def test_complex_profile_performance(self):
        """Test performance with complex dietary profile."""
        profile = PROFILE_COMPLEX
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, TEST_INGREDIENTS_COMPLEX, profile)
        times = run_timed_iterations(
            analyze_ingredients, NUM_TIMING_ITERATIONS_SMALL,
            TEST_INGREDIENTS_COMPLEX, profile,
        )
        avg_time = statistics.mean(times)
        assert avg_time < TARGET_COMPLEX_PROFILE_TIME, \
            f"Complex profile processing {avg_time:.2f}s exceeds {TARGET_COMPLEX_PROFILE_TIME}s target"


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
        warmup(analyze_ingredients, NUM_WARMUP_ITERATIONS, ingredients, profile)
        times = run_timed_iterations(
            analyze_ingredients, NUM_TIMING_ITERATIONS_LARGE,
            ingredients, profile,
        )
        times.sort()
        n = len(times)
        p50 = times[int(n * 0.50)]
        p95 = times[int(n * 0.95)]
        p99 = times[min(int(n * 0.99), n - 1)]
        assert p50 < TARGET_P50_TIME, f"P50 {p50:.4f}s exceeds {TARGET_P50_TIME}s"
        assert p95 < TARGET_P95_TIME, f"P95 {p95:.4f}s exceeds {TARGET_P95_TIME}s"
        assert p99 < TARGET_P99_TIME, f"P99 {p99:.4f}s exceeds {TARGET_P99_TIME}s"


# =============================================================================
# FULL PIPELINE COMPARISON: Model-based vs LLM-based (real images)
# =============================================================================

@pytest.mark.performance
@pytest.mark.slow
class TestFullPipelineComparison:
    """
    Compare full-pipeline performance: model-based (EasyOCR + box classifier)
    vs LLM-based (Mistral OCR + LLM extraction) on real food-label images.

    Configurable via pytest CLI options:
      --perf-images-dir   Directory of test images       (default: tests/data/images)
      --perf-num-images   Number of images to test       (default: all)
      --perf-output       Path to save JSON results      (default: tests/data/performance_results.json)

    Example:
      pytest tests/performance/test_performance.py::TestFullPipelineComparison -v -s \\
        --perf-num-images 10 --perf-output my_results.json
    """

    def _get_config(self, request) -> Dict[str, Any]:
        images_dir_opt = request.config.getoption("--perf-images-dir", default=None)
        images_dir = Path(images_dir_opt) if images_dir_opt else DEFAULT_IMAGES_DIR
        if not images_dir.is_absolute():
            images_dir = PROJECT_ROOT / images_dir

        output_opt = request.config.getoption("--perf-output", default=None)
        output_path = Path(output_opt) if output_opt else DEFAULT_OUTPUT_PATH
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

        num_images = request.config.getoption("--perf-num-images", default=None)

        return {
            "images_dir": images_dir,
            "output_path": output_path,
            "num_images": num_images,
        }

    def test_model_vs_llm_pipeline(self, request):
        """Run both pipelines on real images and report timing comparison."""
        cfg = self._get_config(request)
        images_dir: Path = cfg["images_dir"]
        output_path: Path = cfg["output_path"]
        num_images: Optional[int] = cfg["num_images"]

        image_files = _discover_images(images_dir, limit=num_images)
        assert image_files, f"No images found in {images_dir}"

        profile = PROFILE_HALAL_GLUTEN_FREE

        # Warmup: run the model-based pipeline once to load EasyOCR, box
        # classifier, and OCR-corrector models into memory before timing.
        warmup_data = image_files[0].read_bytes()
        print("\n  Warming up model-based pipeline (loading models)…", end=" ", flush=True)
        try:
            run_model_pipeline(warmup_data, profile)
            print("done.")
        except Exception:
            print("warmup failed (will proceed anyway).")

        per_image_results: List[Dict[str, Any]] = []
        model_times: List[float] = []
        llm_times: List[float] = []
        total = len(image_files)

        print(f"\n{'='*80}")
        print(f"  FULL PIPELINE COMPARISON — {total} images from {images_dir.name}/")
        print(f"{'='*80}\n")

        for idx, img_path in enumerate(image_files, 1):
            image_data = img_path.read_bytes()
            entry: Dict[str, Any] = {"image": img_path.name}

            # --- Model-based pipeline ---
            try:
                model_result = run_model_pipeline(image_data, profile)
                entry["model_based"] = model_result
                model_times.append(model_result["total_time"])
            except Exception as e:
                entry["model_based"] = {"error": str(e), "total_time": None}

            # --- LLM-based pipeline (Mistral OCR, no cache) ---
            try:
                llm_result = run_llm_pipeline(image_data, profile)
                entry["llm_based"] = llm_result
                llm_times.append(llm_result["total_time"])
            except Exception as e:
                entry["llm_based"] = {"error": str(e), "total_time": None}

            m_time = entry["model_based"].get("total_time")
            l_time = entry["llm_based"].get("total_time")
            m_str = f"{m_time:.2f}s" if m_time is not None else "ERROR"
            l_str = f"{l_time:.2f}s" if l_time is not None else "ERROR"
            print(f"  [{idx:>{len(str(total))}}/{total}] {img_path.name:<20}  model: {m_str:<10}  llm: {l_str}")

            per_image_results.append(entry)

        # --- Build summary ---
        model_stats = _stats(model_times) if model_times else {}
        llm_stats = _stats(llm_times) if llm_times else {}

        def _stage_stats(results: List[Dict], pipeline_key: str, stage_key: str) -> Dict[str, float]:
            vals = [
                r[pipeline_key][stage_key]
                for r in results
                if pipeline_key in r and stage_key in r[pipeline_key] and r[pipeline_key][stage_key] is not None
            ]
            return _stats(vals)

        summary = {
            "model_based": {
                "total": model_stats,
                "ocr": _stage_stats(per_image_results, "model_based", "ocr_time"),
                "extraction": _stage_stats(per_image_results, "model_based", "extraction_time"),
                "analysis": _stage_stats(per_image_results, "model_based", "analysis_time"),
                "errors": sum(1 for r in per_image_results if "error" in r.get("model_based", {})),
            },
            "llm_based": {
                "total": llm_stats,
                "ocr": _stage_stats(per_image_results, "llm_based", "ocr_time"),
                "extraction": _stage_stats(per_image_results, "llm_based", "extraction_time"),
                "analysis": _stage_stats(per_image_results, "llm_based", "analysis_time"),
                "errors": sum(1 for r in per_image_results if "error" in r.get("llm_based", {})),
            },
        }

        payload = {
            "config": {
                "images_dir": str(images_dir),
                "num_images": total,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "summary": summary,
            "per_image": per_image_results,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

        # --- Print summary table ---
        print(f"\n{'='*80}")
        print(f"  PERFORMANCE SUMMARY — {total} images")
        print(f"{'='*80}")
        print(f"  {'':30s} {'Model-based':>18s} {'LLM-based':>18s}")
        print(f"  {'-'*66}")

        for label, key in [("Total", "total"), ("OCR", "ocr"), ("Extraction", "extraction"), ("Analysis", "analysis")]:
            m = summary["model_based"].get(key, {})
            l = summary["llm_based"].get(key, {})
            m_avg = f"{m.get('avg', 0):.4f}s" if m else "N/A"
            l_avg = f"{l.get('avg', 0):.4f}s" if l else "N/A"
            print(f"  {'Avg ' + label + ' time':<30s} {m_avg:>18s} {l_avg:>18s}")

        for label, key in [("Total", "total")]:
            m = summary["model_based"].get(key, {})
            l = summary["llm_based"].get(key, {})
            print(f"  {'Min ' + label + ' time':<30s} {m.get('min', 0):>17.4f}s {l.get('min', 0):>17.4f}s")
            print(f"  {'Max ' + label + ' time':<30s} {m.get('max', 0):>17.4f}s {l.get('max', 0):>17.4f}s")
            print(f"  {'Median ' + label + ' time':<30s} {m.get('median', 0):>17.4f}s {l.get('median', 0):>17.4f}s")
            if m.get("stdev"):
                print(f"  {'Stdev ' + label + ' time':<30s} {m.get('stdev', 0):>17.4f}s {l.get('stdev', 0):>17.4f}s")

        m_err = summary["model_based"]["errors"]
        l_err = summary["llm_based"]["errors"]
        print(f"  {'Errors':<30s} {m_err:>18d} {l_err:>18d}")

        if model_times and llm_times:
            speedup = statistics.mean(llm_times) / statistics.mean(model_times)
            print(f"\n  Model-based is ~{speedup:.1f}x faster than LLM-based (avg total)")

        print(f"\n  Results saved to: {output_path}")
        print(f"{'='*80}\n")

        if model_times:
            assert model_stats["avg"] < TARGET_FULL_PIPELINE_TIME, (
                f"Model-based avg {model_stats['avg']:.2f}s exceeds {TARGET_FULL_PIPELINE_TIME}s target"
            )
