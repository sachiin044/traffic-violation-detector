"""
Illegal Parking Detector.
Classes: {0: 'illegal_parking'}
Runs on the FULL image (not on vehicle crops).
"""

from typing import List
import numpy as np

from detectors.base import BaseDetector
from utils.schemas import Detection
from config import MODEL_WEIGHTS, CONFIDENCE_THRESHOLDS


class IllegalParkingDetector(BaseDetector):
    """Detects illegally parked vehicles."""

    CLS_ILLEGAL_PARKING = "illegal_parking"

    def __init__(self):
        super().__init__(
            name="illegal_parking",
            weight_path=MODEL_WEIGHTS["illegal_parking"],
            confidence=CONFIDENCE_THRESHOLDS["illegal_parking"],
        )

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Run illegal parking detection on the full image."""
        return self._raw_detect(image)

    def has_violation(self, detections: List[Detection]) -> bool:
        """Check if any illegal_parking detection exists."""
        return any(d.class_name == self.CLS_ILLEGAL_PARKING for d in detections)

    def get_violation_confidence(self, detections: List[Detection]) -> float:
        """Get the highest illegal_parking confidence."""
        violations = [d for d in detections if d.class_name == self.CLS_ILLEGAL_PARKING]
        return max((d.confidence for d in violations), default=0.0)
