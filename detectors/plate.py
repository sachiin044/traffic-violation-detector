"""
License Plate Detector.
Classes: {0: 'license_plate'}
Runs on vehicle crops to locate plates for OCR.
"""

from typing import List
import numpy as np

from detectors.base import BaseDetector
from utils.schemas import Detection
from config import MODEL_WEIGHTS, CONFIDENCE_THRESHOLDS


class PlateDetector(BaseDetector):
    """Detects license plates in vehicle crops."""

    CLS_LICENSE_PLATE = "license_plate"

    def __init__(self):
        super().__init__(
            name="plate",
            weight_path=MODEL_WEIGHTS["plate"],
            confidence=CONFIDENCE_THRESHOLDS["plate"],
        )

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Run plate detection on a (cropped) image."""
        return self._raw_detect(image)

    def get_best_plate(self, detections: List[Detection]) -> Detection | None:
        """Return the highest-confidence plate detection."""
        plates = [d for d in detections if d.class_name == self.CLS_LICENSE_PLATE]
        if not plates:
            return None
        return max(plates, key=lambda d: d.confidence)
