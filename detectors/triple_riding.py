"""
Triple Riding Detector.
Swapped to standard YOLO11n for perfectly robust person counting!
"""

from typing import List
import numpy as np
from pathlib import Path

from detectors.base import BaseDetector
from utils.schemas import Detection
from config import CONFIDENCE_THRESHOLDS


class TripleRidingDetector(BaseDetector):
    """Detects triple riding by counting persons on motorcycle crops using standard YOLO."""

    CLS_PERSON = "person"

    def __init__(self):
        super().__init__(
            name="triple_riding",
            weight_path=Path("yolo11n.pt"), # Use standard COCO model for flawless person detection
            confidence=CONFIDENCE_THRESHOLDS["triple_riding"],
            allowed_classes=[0], # Class 0 in COCO is 'person'
        )

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Run person detection on the motorcycle crop."""
        raw_dets = self._raw_detect(image)
        processed = []
        for det in raw_dets:
            if det.class_name == "person":
                processed.append(det)
        return processed

    def has_violation(self, detections: List[Detection]) -> bool:
        """Check if 3 or more persons are detected."""
        persons = [d for d in detections if d.class_name == self.CLS_PERSON]
        return len(persons) >= 3

    def get_violation_confidence(self, detections: List[Detection]) -> float:
        """Get the confidence of the 3rd person (the one causing the violation)."""
        persons = [d for d in detections if d.class_name == self.CLS_PERSON]
        if len(persons) >= 3:
            sorted_persons = sorted(persons, key=lambda p: p.confidence, reverse=True)
            return sorted_persons[2].confidence
        return 0.0
