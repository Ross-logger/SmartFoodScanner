from __future__ import annotations

import logging
from typing import Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def preprocess_image_for_ocr(
    rgb: np.ndarray,
    *,
    enabled: bool = True,
    target_short_edge: int = 1000,
    max_long_edge: int = 2400,
    clahe_clip: float = 2.0,
    clahe_grid: Tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Enhance a label image for OCR.

    Args:
        rgb: HxWx3 uint8 RGB (e.g. from PIL / numpy).
        enabled: If False, returns input unchanged (after copy).
        target_short_edge: If min(h, w) is below this, upscale (helps tiny text).
        max_long_edge: If max(h, w) exceeds this, downscale (speed / memory).
        clahe_clip: CLAHE clip limit on L channel (LAB).
        clahe_grid: CLAHE tile grid size.

    Returns:
        RGB uint8 numpy array ready for EasyOCR.
    """
    if not enabled:
        return np.ascontiguousarray(rgb)

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("Expected RGB image with shape (H, W, 3)")

    work = rgb.astype(np.uint8)
    h, w = work.shape[:2]
    short_edge = min(h, w)
    long_edge = max(h, w)

    # --- Resize: small images → upscale; very large → downscale ---
    scale = 1.0
    if short_edge < target_short_edge:
        scale = target_short_edge / float(short_edge)
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    if max(new_w, new_h) > max_long_edge:
        scale2 = max_long_edge / float(max(new_w, new_h))
        new_w = int(round(new_w * scale2))
        new_h = int(round(new_h * scale2))
    if new_w != w or new_h != h:
        work = cv2.resize(work, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        logger.debug("OCR preprocess resize: %sx%s -> %sx%s", w, h, new_w, new_h)

    # --- LAB + CLAHE (handles uneven lighting / low contrast) ---
    bgr = cv2.cvtColor(work, cv2.COLOR_RGB2BGR)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=clahe_grid)
    l2 = clahe.apply(l_ch)
    lab2 = cv2.merge([l2, a_ch, b_ch])
    bgr = cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)

    # --- Light denoise (fast; avoids slow NLM on megapixel images) ---
    bgr = cv2.bilateralFilter(bgr, d=5, sigmaColor=50, sigmaSpace=50)

    out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return out
