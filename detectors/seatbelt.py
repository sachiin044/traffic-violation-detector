"""
Seatbelt Detector.
Classes: {0: 'no-seatbelt', 1: 'seatbelt'}
Runs on cropped car/bus/truck regions.

NOTE: The seatbelt model directly predicts seatbelt/no-seatbelt.
      A no-seatbelt detection above threshold IS the violation.
      No need to additionally require a vehicle detection gate.
"""

from typing import List
import numpy as np

from detectors.base import BaseDetector
from utils.schemas import Detection
from config import MODEL_WEIGHTS, CONFIDENCE_THRESHOLDS


class SeatbeltDetector(BaseDetector):
    """Detects seatbelt compliance on vehicle crops."""

    CLS_NO_SEATBELT = "no-seatbelt"
    CLS_SEATBELT = "seatbelt"

    def __init__(self):
        super().__init__(
            name="seatbelt",
            weight_path=MODEL_WEIGHTS["seatbelt"],
            confidence=CONFIDENCE_THRESHOLDS["seatbelt"],
        )

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Run seatbelt detection on a (cropped) image."""
        return self._raw_detect(image)

    def has_violation(self, detections: List[Detection]) -> bool:
        """Check if any no-seatbelt detection exists."""
        return any(d.class_name == self.CLS_NO_SEATBELT for d in detections)

    def get_violation_confidence(self, detections: List[Detection]) -> float:
        """Get the highest no-seatbelt confidence."""
        violations = [d for d in detections if d.class_name == self.CLS_NO_SEATBELT]
        return max((d.confidence for d in violations), default=0.0)
