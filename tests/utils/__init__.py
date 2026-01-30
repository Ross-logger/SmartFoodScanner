"""
Test Utilities for SmartFoodScanner
"""

from tests.utils.metrics import (
    calculate_precision,
    calculate_recall,
    calculate_f1_score,
    calculate_ocr_accuracy,
    calculate_word_accuracy,
    EvaluationMetrics
)
from tests.utils.test_helpers import (
    create_test_image,
    create_test_image_with_text,
    generate_synthetic_ocr_text
)
from tests.utils.mock_llm import MockLLMService, MockLLMProvider

__all__ = [
    'calculate_precision',
    'calculate_recall',
    'calculate_f1_score',
    'calculate_ocr_accuracy',
    'calculate_word_accuracy',
    'EvaluationMetrics',
    'create_test_image',
    'create_test_image_with_text',
    'generate_synthetic_ocr_text',
    'MockLLMService',
    'MockLLMProvider',
]
