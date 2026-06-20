"""
Vehicle Detector — Standard YOLO11n (COCO pretrained) for robust detection.

Uses COCO classes and remaps them to pipeline-expected names:
  car (COCO 2) -> car
  motorcycle (COCO 3) -> motorcycle
  bicycle (COCO 1) -> bicycle
  bus (COCO 5) -> heavy_vehicle
  truck (COCO 7) -> heavy_vehicle
"""

from typing import List
import numpy as np
from pathlib import Path

from detectors.base import BaseDetector
from utils.schemas import Detection
from config import CONFIDENCE_THRESHOLDS


class VehicleDetector(BaseDetector):
    """Detects vehicles using standard YOLO11n (COCO pretrained).
    
    Far more robust than custom-trained models for general internet images.
    Remaps COCO class names to pipeline-expected names.
    """

    # COCO class IDs: 1=bicycle, 2=car, 3=motorcycle, 5=bus, 7=truck
    COCO_VEHICLE_CLASSES = [1, 2, 3, 5, 7]

    # Remap COCO names -> pipeline names
    CLASS_REMAP = {
        "car": "car",
        "motorcycle": "motorcycle",
        "bicycle": "bicycle",
        "bus": "heavy_vehicle",
        "truck": "heavy_vehicle",
    }

    def __init__(self):
        super().__init__(
            name="vehicle",
            weight_path=Path("yolo11n.pt"),  # Standard COCO model (auto-downloads)
            confidence=CONFIDENCE_THRESHOLDS["vehicle"],
            allowed_classes=self.COCO_VEHICLE_CLASSES,
        )

    def _remap_detections(self, raw_dets: List[Detection]) -> List[Detection]:
        """Remap COCO class names to pipeline-expected names."""
        processed = []
        for det in raw_dets:
            new_name = self.CLASS_REMAP.get(det.class_name)
            if new_name:
                det.class_name = new_name
                processed.append(det)
        return processed

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Detect vehicles and remap class names to pipeline-expected names."""
        return self._remap_detections(self._raw_detect(image))

    def track(self, image: np.ndarray, persist: bool = True, **kwargs) -> List[Detection]:
        """Track vehicles and remap class names to pipeline-expected names."""
        raw_dets = super().track(image, persist=persist, **kwargs)
        return self._remap_detections(raw_dets)
