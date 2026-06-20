"""
Helmet Detector.
Classes: {0: 'Helmet', 1: 'Motorbike', 2: 'NoHelmet', 3: 'PNumber'}
Runs on cropped motorcycle regions.
"""

from typing import List
import numpy as np

from detectors.base import BaseDetector
from utils.schemas import Detection
from config import MODEL_WEIGHTS, CONFIDENCE_THRESHOLDS


class HelmetDetector(BaseDetector):
    """Detects helmet compliance on motorcycle crops."""

    # Class name constants matching trained model
    CLS_HELMET = "Helmet"
    CLS_NO_HELMET = "NoHelmet"
    CLS_MOTORBIKE = "Motorbike"

    def __init__(self):
        super().__init__(
            name="helmet",
            weight_path=MODEL_WEIGHTS["helmet"],
            confidence=CONFIDENCE_THRESHOLDS["helmet"],
        )

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Run helmet detection on a (cropped) image."""
        return self._raw_detect(image)

    def has_violation(self, detections: List[Detection]) -> bool:
        """Check if any NoHelmet detection exists."""
        return any(d.class_name == self.CLS_NO_HELMET for d in detections)

    def get_violation_confidence(self, detections: List[Detection]) -> float:
        """Get the highest NoHelmet confidence."""
        no_helmet = [d for d in detections if d.class_name == self.CLS_NO_HELMET]
        return max((d.confidence for d in no_helmet), default=0.0)
