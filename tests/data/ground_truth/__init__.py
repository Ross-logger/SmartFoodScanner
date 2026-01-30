"""
Ground Truth Test Data Module
"""

import json
from pathlib import Path
from typing import Dict, Any


def load_ground_truth() -> Dict[str, Any]:
    """Load ground truth data from JSON file."""
    ground_truth_path = Path(__file__).parent / "sample_labels.json"
    if ground_truth_path.exists():
        with open(ground_truth_path, 'r') as f:
            return json.load(f)
    return {}


def get_ground_truth_for_image(image_id: str) -> Dict[str, Any]:
    """Get ground truth data for a specific image."""
    data = load_ground_truth()
    return data.get(image_id, {})


def get_all_test_labels() -> Dict[str, Any]:
    """Get all test labels excluding metadata."""
    data = load_ground_truth()
    return {k: v for k, v in data.items() if not k.startswith('_')}
