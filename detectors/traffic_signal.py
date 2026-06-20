"""
Traffic Signal Detector.
Classes: {0: 'car', 1: 'green_light', 2: 'motobike', 3: 'red_light',
          4: 'stop_line', 5: 'yellow_light'}
Runs on the FULL image (not on vehicle crops).

Red Light Violation Logic (image-only MVP):
  - red_light is detected
  - AND a vehicle bbox overlaps with / crosses the stop_line

LIMITATION: True red-light running requires multi-frame tracking
(vehicle before stop_line in frame N, after it in frame N+1 while red).
For single-image analysis, we use spatial overlap as a proxy.
"""

from typing import List, Tuple
import numpy as np

from detectors.base import BaseDetector
from utils.schemas import Detection, BBox
from config import MODEL_WEIGHTS, CONFIDENCE_THRESHOLDS


class TrafficSignalDetector(BaseDetector):
    """Detects traffic signal state and stop-line violations."""

    CLS_RED_LIGHT = "red_light"
    CLS_YELLOW_LIGHT = "yellow_light"
    CLS_GREEN_LIGHT = "green_light"
    CLS_STOP_LINE = "stop_line"
    CLS_CAR = "car"
    CLS_MOTORBIKE = "motobike"  # note: trained model uses "motobike" not "motorbike"

    def __init__(self):
        super().__init__(
            name="traffic_signal",
            weight_path=MODEL_WEIGHTS["traffic_signal"],
            confidence=CONFIDENCE_THRESHOLDS["traffic_signal"],
        )

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Run traffic signal detection on the full image."""
        return self._raw_detect(image)

    def get_signal_state(self, detections: List[Detection]) -> str:
        """Return the dominant signal state: 'red', 'yellow', 'green', or 'unknown'."""
        signals = {
            "red":    max((d.confidence for d in detections if d.class_name == self.CLS_RED_LIGHT), default=0),
            "yellow": max((d.confidence for d in detections if d.class_name == self.CLS_YELLOW_LIGHT), default=0),
            "green":  max((d.confidence for d in detections if d.class_name == self.CLS_GREEN_LIGHT), default=0),
        }
        best = max(signals, key=signals.get)
        return best if signals[best] > 0 else "unknown"

    def get_stop_lines(self, detections: List[Detection]) -> List[Detection]:
        """Return all stop_line detections."""
        return [d for d in detections if d.class_name == self.CLS_STOP_LINE]

    @staticmethod
    def bbox_overlaps_stop_line(vehicle_bbox: BBox, stop_line: Detection) -> bool:
        """
        Check if a vehicle's bottom edge is at or past the stop line.
        Uses simple vertical overlap: vehicle bottom >= stop_line top.
        """
        return vehicle_bbox.y2 >= stop_line.bbox.y1

    def check_red_light_violation(
        self,
        detections: List[Detection],
        vehicle_bboxes: List[BBox],
    ) -> List[Tuple[int, float]]:
        """
        Check for red-light violations.

        Returns list of (vehicle_index, confidence) for vehicles violating.
        """
        signal_state = self.get_signal_state(detections)
        if signal_state != "red":
            return []

        stop_lines = self.get_stop_lines(detections)
        if not stop_lines:
            return []

        red_conf = max(
            (d.confidence for d in detections if d.class_name == self.CLS_RED_LIGHT),
            default=0.0,
        )

        violations = []
        for idx, v_bbox in enumerate(vehicle_bboxes):
            for sl in stop_lines:
                if self.bbox_overlaps_stop_line(v_bbox, sl):
                    violations.append((idx, red_conf))
                    break  # one stop_line match is enough

        return violations
