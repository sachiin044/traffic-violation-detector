"""
Triple Riding Detector.

Default ("custom"): your trained model (outputs/triple_riding/weights/best.pt)
  with classes motorcycle, person, rider_region. Returns person and
  rider_region detections; the rule engine uses both.

Fallback ("coco"): stock YOLO11n, person class only (previous behaviour).

Choose with TRIPLE_RIDING_MODEL in config.py / .env. If the custom weights
can't be loaded, the detector logs a warning and falls back to COCO.
"""

import logging
from typing import List
import numpy as np
from pathlib import Path

from detectors.base import BaseDetector
from utils.schemas import Detection
from config import (
    CONFIDENCE_THRESHOLDS,
    MODEL_WEIGHTS,
    TRIPLE_RIDING_MODEL,
    COCO_MODEL_PATH,
)

logger = logging.getLogger(__name__)


class TripleRidingDetector(BaseDetector):
    """Detects triple riding on motorcycle crops (persons + rider_region)."""

    CLS_PERSON = "person"
    CLS_RIDER_REGION = "rider_region"
    KEEP_CLASSES = {CLS_PERSON, CLS_RIDER_REGION}

    def __init__(self):
        self.use_coco = TRIPLE_RIDING_MODEL == "coco"
        super().__init__(
            name="triple_riding",
            weight_path=Path(COCO_MODEL_PATH) if self.use_coco else MODEL_WEIGHTS["triple_riding"],
            confidence=CONFIDENCE_THRESHOLDS["triple_riding"],
            allowed_classes=[0] if self.use_coco else None,  # COCO class 0 = person
        )

    def load(self) -> None:
        try:
            super().load()
        except Exception as e:
            if self.use_coco:
                raise
            logger.warning(f"[triple_riding] Custom weights failed to load ({e}); falling back to COCO yolo11n.pt")
            self.use_coco = True
            self.weight_path = Path(COCO_MODEL_PATH)
            self.allowed_classes = [0]
            self.model = None
            self._loaded = False
            super().load()

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Run detection on the motorcycle crop; keep person + rider_region."""
        return [d for d in self._raw_detect(image) if d.class_name in self.KEEP_CLASSES]

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
