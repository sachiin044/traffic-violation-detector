"""
Image preprocessing utilities.
CLAHE enhancement, brightness normalization, denoising, optional deblur.
"""

import cv2
import numpy as np
import logging
from typing import Optional

from config import CLAHE_CLIP_LIMIT, CLAHE_TILE_SIZE, DENOISE_STRENGTH

logger = logging.getLogger(__name__)


def apply_clahe(image: np.ndarray) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    if len(image.shape) == 2:
        clahe = cv2.createCLAHE(
            clipLimit=CLAHE_CLIP_LIMIT,
            tileGridSize=CLAHE_TILE_SIZE,
        )
        return clahe.apply(image)

    # Convert to LAB, apply CLAHE to L channel
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=CLAHE_CLIP_LIMIT,
        tileGridSize=CLAHE_TILE_SIZE,
    )
    l_enhanced = clahe.apply(l_channel)

    lab_enhanced = cv2.merge([l_enhanced, a, b])
    return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)


def normalize_brightness(image: np.ndarray, target_brightness: int = 127) -> np.ndarray:
    """Normalize image brightness to a target mean value."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    current_brightness = np.mean(v)
    if current_brightness == 0:
        return image

    ratio = target_brightness / current_brightness
    v = np.clip(v * ratio, 0, 255).astype(np.uint8)

    hsv_adjusted = cv2.merge([h, s, v])
    return cv2.cvtColor(hsv_adjusted, cv2.COLOR_HSV2BGR)


def denoise(image: np.ndarray) -> np.ndarray:
    """Apply non-local means denoising."""
    return cv2.fastNlMeansDenoisingColored(
        image,
        None,
        h=DENOISE_STRENGTH,
        hForColorComponents=DENOISE_STRENGTH,
        templateWindowSize=7,
        searchWindowSize=21,
    )


def deblur(image: np.ndarray) -> np.ndarray:
    """Apply sharpening to reduce motion blur."""
    kernel = np.array([
        [0, -1, 0],
        [-1,  5, -1],
        [0, -1, 0],
    ], dtype=np.float32)
    return cv2.filter2D(image, -1, kernel)


def is_low_quality(image: np.ndarray) -> bool:
    """Check if image has low contrast or is too dark/bright."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    mean_val = np.mean(gray)
    std_val = np.std(gray)
    return std_val < 30 or mean_val < 50 or mean_val > 220


def preprocess_image(image: np.ndarray, aggressive: bool = False) -> np.ndarray:
    """
    Full preprocessing pipeline.

    Args:
        image: BGR image (OpenCV format)
        aggressive: if True, apply denoising and deblur (slower)

    Returns:
        Preprocessed BGR image
    """
    if image is None or image.size == 0:
        raise ValueError("Empty or invalid image")

    logger.debug(f"Preprocessing image: {image.shape}, aggressive={aggressive}")

    # Disabled all preprocessing (CLAHE, brightness normalization, etc.) 
    # because the custom YOLO model was trained on raw/natural images 
    # and any manipulation of the image domain causes it to fail.
    return image


def crop_region(
    image: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    pad_fraction: float = 0.1,
    pad_top_fraction: Optional[float] = None,
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """
    Crop a region from the image with optional padding.

    Args:
        pad_fraction: Symmetrical padding fraction for left, right, and bottom.
        pad_top_fraction: Optional specific padding for the top (useful for capturing heads on motorcycles). If None, pad_fraction is used.

    Returns:
        (cropped_image, (actual_x1, actual_y1, actual_x2, actual_y2))
        The actual coordinates account for padding and image boundary clipping.
    """
    h, w = image.shape[:2]

    # Compute padding
    box_w = x2 - x1
    box_h = y2 - y1
    pad_x = int(box_w * pad_fraction)
    pad_bottom = int(box_h * pad_fraction)
    pad_top = int(box_h * (pad_top_fraction if pad_top_fraction is not None else pad_fraction))

    # Apply padding with boundary clipping
    actual_x1 = max(0, x1 - pad_x)
    actual_y1 = max(0, y1 - pad_top)
    actual_x2 = min(w, x2 + pad_x)
    actual_y2 = min(h, y2 + pad_bottom)

    crop = image[actual_y1:actual_y2, actual_x1:actual_x2]
    return crop, (actual_x1, actual_y1, actual_x2, actual_y2)
