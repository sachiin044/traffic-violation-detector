"""
Vehicle Detector.

Modes (VEHICLE_MODEL in config.py / .env):
  "ensemble" (default): stock YOLO11n (COCO) finds motorcycles, cars, buses and
      trucks; your custom Indian-traffic model (outputs/vehicle/weights/best.pt)
      runs alongside it only to add autorickshaws, which COCO has no class for.
      A COCO box that overlaps a custom autorickshaw box is relabelled.
  "custom": only the custom model (motorcycle, car, heavy_vehicle, autorickshaw).
  "coco":   only stock YOLO11n.

COCO names are remapped to pipeline names:
  bicycle -> bicycle, car -> car, motorcycle -> motorcycle, bus/truck -> heavy_vehicle

If a model can't be loaded, the detector logs a warning and uses the other one.
Video tracking always uses the primary model.
"""

import logging
from typing import List, Optional
import numpy as np
from pathlib import Path
from ultralytics import YOLO

from detectors.base import BaseDetector
from utils.schemas import Detection, BBox
from config import (
    CONFIDENCE_THRESHOLDS,
    MODEL_WEIGHTS,
    VEHICLE_MODEL,
    VEHICLE_CLASS_MAP,
    COCO_MODEL_PATH,
    NMS_IOU_THRESHOLD,
)

logger = logging.getLogger(__name__)


def _iou(a: BBox, b: BBox) -> float:
    x1, y1 = max(a.x1, b.x1), max(a.y1, b.y1)
    x2, y2 = min(a.x2, b.x2), min(a.y2, b.y2)
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (a.x2 - a.x1) * (a.y2 - a.y1) + (b.x2 - b.x1) * (b.y2 - b.y1) - inter
    return inter / union if union > 0 else 0.0


class VehicleDetector(BaseDetector):
    """Detects vehicles (COCO + custom autorickshaw by default)."""

    # COCO class IDs: 1=bicycle, 2=car, 3=motorcycle, 5=bus, 7=truck
    COCO_VEHICLE_CLASSES = [1, 2, 3, 5, 7]

    CLASS_REMAP = {
        "car": "car",
        "motorcycle": "motorcycle",
        "bicycle": "bicycle",
        "bus": "heavy_vehicle",
        "truck": "heavy_vehicle",
    }

    CUSTOM_CLASSES = set(VEHICLE_CLASS_MAP.values())
    AUTORICKSHAW = "autorickshaw"

    def __init__(self):
        mode = VEHICLE_MODEL if VEHICLE_MODEL in ("ensemble", "custom", "coco") else "ensemble"
        self.mode = mode
        self.use_coco = mode in ("ensemble", "coco")
        self.aux_model: Optional[YOLO] = None  # custom model used for autorickshaws in ensemble mode
        super().__init__(
            name="vehicle",
            weight_path=Path(COCO_MODEL_PATH) if self.use_coco else MODEL_WEIGHTS["vehicle"],
            confidence=CONFIDENCE_THRESHOLDS["vehicle"],
            allowed_classes=self.COCO_VEHICLE_CLASSES if self.use_coco else None,
        )

    def _set_primary(self, use_coco: bool) -> None:
        self.use_coco = use_coco
        self.weight_path = Path(COCO_MODEL_PATH) if use_coco else MODEL_WEIGHTS["vehicle"]
        self.allowed_classes = self.COCO_VEHICLE_CLASSES if use_coco else None
        self.model = None
        self._loaded = False

    def load(self) -> None:
        try:
            super().load()
        except Exception as e:
            if self.mode == "coco":
                raise
            fallback_coco = not self.use_coco
            logger.warning(
                f"[vehicle] {'Custom' if fallback_coco else 'COCO'} weights failed to load ({e}); "
                f"falling back to {'COCO yolo11n.pt' if fallback_coco else 'custom weights'}"
            )
            self.mode = "coco" if fallback_coco else "custom"
            self._set_primary(use_coco=fallback_coco)
            super().load()
            return

        if self.mode == "ensemble":
            aux_path = Path(MODEL_WEIGHTS["vehicle"])
            try:
                if not aux_path.exists():
                    raise FileNotFoundError(str(aux_path))
                self.aux_model = YOLO(str(aux_path))
                logger.info(f"[vehicle] Ensemble mode: COCO + custom autorickshaw model ({aux_path})")
            except Exception as e:
                logger.warning(f"[vehicle] Custom autorickshaw model not loaded ({e}); using COCO only")
                self.aux_model = None

    def _remap_detections(self, raw_dets: List[Detection]) -> List[Detection]:
        """Map detections to pipeline names and drop anything that isn't a vehicle."""
        if not self.use_coco:
            return [d for d in raw_dets if d.class_name in self.CUSTOM_CLASSES]
        processed = []
        for det in raw_dets:
            new_name = self.CLASS_REMAP.get(det.class_name)
            if new_name:
                det.class_name = new_name
                processed.append(det)
        return processed

    def _detect_autorickshaws(self, image: np.ndarray) -> List[Detection]:
        if self.aux_model is None:
            return []
        dets: List[Detection] = []
        results = self.aux_model.predict(
            image, conf=self.confidence, iou=NMS_IOU_THRESHOLD, verbose=False
        )
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                name = self.aux_model.names.get(int(box.cls[0]), "")
                if name != self.AUTORICKSHAW:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                dets.append(Detection(
                    class_name=self.AUTORICKSHAW,
                    confidence=float(box.conf[0]),
                    bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    model_source=self.name,
                ))
        return dets

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Detect vehicles and return them with pipeline class names."""
        dets = self._remap_detections(self._raw_detect(image))
        if self.mode != "ensemble":
            return dets
        for auto in self._detect_autorickshaws(image):
            match = max(dets, key=lambda d: _iou(d.bbox, auto.bbox), default=None)
            if match is not None and _iou(match.bbox, auto.bbox) >= 0.5:
                # COCO usually calls an auto a car or motorcycle; trust the custom label
                match.class_name = self.AUTORICKSHAW
                match.confidence = max(match.confidence, auto.confidence)
            else:
                dets.append(auto)
        return dets

    def track(self, image: np.ndarray, persist: bool = True, **kwargs) -> List[Detection]:
        """Track vehicles (primary model) and return them with pipeline class names."""
        raw_dets = super().track(image, persist=persist, **kwargs)
        return self._remap_detections(raw_dets)
