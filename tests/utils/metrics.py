"""
Evaluation Metrics for SmartFoodScanner Testing

Provides precision, recall, F1 score, and OCR accuracy calculations
for evaluating the system's performance.
"""

from typing import List, Set, Dict, Any, Optional
from dataclasses import dataclass, field
import difflib
import re


def calculate_precision(predicted: List[str], ground_truth: List[str]) -> float:
    """
    Calculate precision: correct predictions / total predictions.
    
    Args:
        predicted: List of predicted items
        ground_truth: List of ground truth items
        
    Returns:
        Precision score (0.0 to 1.0)
    """
    if not predicted:
        return 0.0
    
    predicted_set = set(item.lower().strip() for item in predicted)
    ground_truth_set = set(item.lower().strip() for item in ground_truth)

    true_positives = len(predicted_set & ground_truth_set)
    return true_positives / len(predicted_set)


def calculate_recall(predicted: List[str], ground_truth: List[str]) -> float:
    """
    Calculate recall: correct predictions / total ground truth items.
    
    Args:
        predicted: List of predicted items
        ground_truth: List of ground truth items
        
    Returns:
        Recall score (0.0 to 1.0)
    """
    if not ground_truth:
        return 1.0 if not predicted else 0.0
    
    predicted_set = set(item.lower().strip() for item in predicted)
    ground_truth_set = set(item.lower().strip() for item in ground_truth)
    
    true_positives = len(predicted_set & ground_truth_set)
    return true_positives / len(ground_truth_set)


def calculate_f1_score(predicted: List[str], ground_truth: List[str]) -> float:
    """
    Calculate F1 score: harmonic mean of precision and recall.
    
    Args:
        predicted: List of predicted items
        ground_truth: List of ground truth items
        
    Returns:
        F1 score (0.0 to 1.0)
    """
    precision = calculate_precision(predicted, ground_truth)
    recall = calculate_recall(predicted, ground_truth)
    
    if precision + recall == 0:
        return 0.0
    
    return 2 * (precision * recall) / (precision + recall)


def _merge_containment_text(s: str) -> str:
    """Normalise text for merge substring checks (slash oils, spacing)."""
    t = s.lower().strip()
    t = re.sub(r"\s*/\s*", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def calculate_merge_precision(predicted: List[str], ground_truth: List[str]) -> float:
    """
    Merge-based precision: join ground truth into one string, check how many
    predicted items appear as substrings. High value + low split precision
    suggests over-splitting (correct text but wrong boundaries).
    """
    if not predicted:
        return 0.0
    merged_gt = _merge_containment_text(" ".join(g.lower().strip() for g in ground_truth))
    count = sum(1 for p in predicted if _merge_containment_text(p) in merged_gt)
    return count / len(predicted)


def calculate_merge_recall(predicted: List[str], ground_truth: List[str]) -> float:
    """
    Merge-based recall: join predicted into one string, check how many
    ground truth items appear as substrings. High value + low split recall
    suggests wrong splitting (text is there but merged or split incorrectly).
    """
    if not ground_truth:
        return 1.0 if not predicted else 0.0
    merged_pred = _merge_containment_text(" ".join(p.lower().strip() for p in predicted))
    count = sum(1 for g in ground_truth if _merge_containment_text(g) in merged_pred)
    return count / len(ground_truth)


def calculate_merge_f1(predicted: List[str], ground_truth: List[str]) -> float:
    """F1 for merge-based (containment) metrics."""
    p = calculate_merge_precision(predicted, ground_truth)
    r = calculate_merge_recall(predicted, ground_truth)
    if p + r == 0:
        return 0.0
    return 2 * (p * r) / (p + r)


def calculate_ocr_accuracy(predicted_text: str, ground_truth_text: str) -> float:
    """
    Calculate character-level OCR accuracy using sequence matching.
    
    Args:
        predicted_text: OCR output text
        ground_truth_text: Expected text
        
    Returns:
        Accuracy score (0.0 to 1.0)
    """
    if not ground_truth_text:
        return 1.0 if not predicted_text else 0.0
    
    if not predicted_text:
        return 0.0
    
    # Use SequenceMatcher for character-level comparison
    matcher = difflib.SequenceMatcher(None, predicted_text.lower(), ground_truth_text.lower())
    return matcher.ratio()


def calculate_word_accuracy(predicted_text: str, ground_truth_text: str) -> float:
    """
    Calculate word-level OCR accuracy.
    
    Args:
        predicted_text: OCR output text
        ground_truth_text: Expected text
        
    Returns:
        Accuracy score (0.0 to 1.0)
    """
    if not ground_truth_text:
        return 1.0 if not predicted_text else 0.0
    
    if not predicted_text:
        return 0.0
    
    predicted_words = set(predicted_text.lower().split())
    ground_truth_words = set(ground_truth_text.lower().split())
    
    if not ground_truth_words:
        return 1.0 if not predicted_words else 0.0
    
    correct_words = len(predicted_words & ground_truth_words)
    total_words = len(ground_truth_words)
    
    return correct_words / total_words


def calculate_fuzzy_match_accuracy(
    predicted: List[str], 
    ground_truth: List[str],
    threshold: float = 0.8
) -> Dict[str, float]:
    """
    Calculate accuracy with fuzzy matching for ingredient names.
    Useful when OCR produces minor spelling variations.
    
    Args:
        predicted: List of predicted ingredients
        ground_truth: List of ground truth ingredients
        threshold: Minimum similarity score for a match (0.0 to 1.0)
        
    Returns:
        Dict with precision, recall, and f1 scores using fuzzy matching
    """
    if not ground_truth:
        return {"precision": 1.0 if not predicted else 0.0, "recall": 1.0, "f1": 1.0 if not predicted else 0.0}
    
    if not predicted:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    
    matched_predictions = 0
    matched_ground_truth = set()
    
    for pred in predicted:
        pred_lower = pred.lower().strip()
        best_match_score = 0
        best_match_idx = None
        
        for idx, gt in enumerate(ground_truth):
            if idx in matched_ground_truth:
                continue
            gt_lower = gt.lower().strip()
            score = difflib.SequenceMatcher(None, pred_lower, gt_lower).ratio()
            if score > best_match_score:
                best_match_score = score
                best_match_idx = idx
        
        if best_match_score >= threshold and best_match_idx is not None:
            matched_predictions += 1
            matched_ground_truth.add(best_match_idx)
    
    precision = matched_predictions / len(predicted)
    recall = len(matched_ground_truth) / len(ground_truth)
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {"precision": precision, "recall": recall, "f1": f1}


@dataclass
class EvaluationMetrics:
    """
    Container for evaluation metrics across multiple test cases.
    """
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_ocr_result(
        self,
        test_id: str,
        predicted_text: str,
        ground_truth_text: str,
        metadata: Optional[Dict] = None
    ):
        """Add an OCR test result."""
        self.test_cases.append({
            "test_id": test_id,
            "type": "ocr",
            "predicted": predicted_text,
            "ground_truth": ground_truth_text,
            "char_accuracy": calculate_ocr_accuracy(predicted_text, ground_truth_text),
            "word_accuracy": calculate_word_accuracy(predicted_text, ground_truth_text),
            "metadata": metadata or {}
        })
    
    def add_extraction_result(
        self,
        test_id: str,
        predicted_ingredients: List[str],
        ground_truth_ingredients: List[str],
        metadata: Optional[Dict] = None
    ):
        """Add an ingredient extraction test result (fuzzy token metrics only)."""
        fuzzy = calculate_fuzzy_match_accuracy(predicted_ingredients, ground_truth_ingredients)
        self.test_cases.append({
            "test_id": test_id,
            "type": "extraction",
            "predicted": predicted_ingredients,
            "ground_truth": ground_truth_ingredients,
            "fuzzy_metrics": fuzzy,
            "metadata": metadata or {}
        })
    
    def add_compliance_result(
        self,
        test_id: str,
        predicted_safe: bool,
        actual_safe: bool,
        predicted_warnings: List[str],
        expected_warnings: List[str],
        metadata: Optional[Dict] = None
    ):
        """Add a dietary compliance test result."""
        self.test_cases.append({
            "test_id": test_id,
            "type": "compliance",
            "predicted_safe": predicted_safe,
            "actual_safe": actual_safe,
            "correct": predicted_safe == actual_safe,
            "warning_precision": calculate_precision(predicted_warnings, expected_warnings),
            "warning_recall": calculate_recall(predicted_warnings, expected_warnings),
            "metadata": metadata or {}
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all test cases."""
        ocr_cases = [c for c in self.test_cases if c["type"] == "ocr"]
        extraction_cases = [c for c in self.test_cases if c["type"] == "extraction"]
        compliance_cases = [c for c in self.test_cases if c["type"] == "compliance"]
        
        summary = {
            "total_cases": len(self.test_cases),
            "ocr": {},
            "extraction": {},
            "compliance": {}
        }
        
        if ocr_cases:
            summary["ocr"] = {
                "count": len(ocr_cases),
                "avg_char_accuracy": sum(c["char_accuracy"] for c in ocr_cases) / len(ocr_cases),
                "avg_word_accuracy": sum(c["word_accuracy"] for c in ocr_cases) / len(ocr_cases),
                "min_char_accuracy": min(c["char_accuracy"] for c in ocr_cases),
                "max_char_accuracy": max(c["char_accuracy"] for c in ocr_cases),
            }
        
        if extraction_cases:
            fm = [c["fuzzy_metrics"] for c in extraction_cases]
            summary["extraction"] = {
                "count": len(extraction_cases),
                "avg_fuzzy_precision": sum(f.get("precision", 0) for f in fm) / len(fm),
                "avg_fuzzy_recall": sum(f.get("recall", 0) for f in fm) / len(fm),
                "avg_fuzzy_f1": sum(f.get("f1", 0) for f in fm) / len(fm),
            }
        
        if compliance_cases:
            correct_count = sum(1 for c in compliance_cases if c["correct"])
            summary["compliance"] = {
                "count": len(compliance_cases),
                "accuracy": correct_count / len(compliance_cases),
                "correct": correct_count,
                "incorrect": len(compliance_cases) - correct_count,
            }
        
        return summary
    
    def meets_targets(
        self,
        ocr_target: float = 0.90,
        compliance_target: float = 0.95
    ) -> Dict[str, bool]:
        """Check if metrics meet the specified targets."""
        summary = self.get_summary()
        
        results = {
            "ocr_target_met": False,
            "compliance_target_met": False,
        }
        
        if summary["ocr"]:
            results["ocr_target_met"] = summary["ocr"]["avg_char_accuracy"] >= ocr_target
        
        if summary["compliance"]:
            results["compliance_target_met"] = summary["compliance"]["accuracy"] >= compliance_target
        
        return results
