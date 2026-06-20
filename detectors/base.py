"""
Base detector class.
All YOLO-based detectors inherit from this. Models are loaded once (singleton).
"""

import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
from ultralytics import YOLO

from utils.schemas import Detection, BBox
from config import NMS_IOU_THRESHOLD

logger = logging.getLogger(__name__)


class BaseDetector:
    """
    Abstract base for all YOLO detectors.

    Loads the model once on first call to load().
    Subclasses override `detect()` to add model-specific filtering.
    """

    def __init__(
        self,
        name: str,
        weight_path: Path,
        confidence: float = 0.4,
        allowed_classes: Optional[List[int]] = None,
    ):
        self.name = name
        self.weight_path = weight_path
        self.confidence = confidence
        self.allowed_classes = allowed_classes  # COCO class IDs to keep
        self.model: Optional[YOLO] = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        """Load the YOLO model from disk. Called once at startup."""
        if self._loaded:
            return

        path = str(self.weight_path)
        # Skip the existence check for standard pretrained models (they auto-download)
        if not Path(path).exists() and "/" not in path and "\\" not in path and path.endswith(".pt"):
            logger.info(f"[{self.name}] Weight file '{path}' not found locally. Ultralytics will attempt to auto-download it.")
        elif not Path(path).exists():
            raise FileNotFoundError(f"[{self.name}] Weight file not found: {path}")

        logger.info(f"[{self.name}] Loading model from {path}")
        self.model = YOLO(path)
        self._loaded = True
        logger.info(f"[{self.name}] Model loaded. Classes: {self.model.names}")

    def get_class_names(self) -> dict:
        """Return the model's class name mapping."""
        if self.model is None:
            return {}
        return dict(self.model.names)

    def _raw_detect(
        self,
        image: np.ndarray,
        conf: Optional[float] = None,
        classes: Optional[List[int]] = None,
    ) -> List[Detection]:
        """
        Run YOLO inference and return a list of Detection objects.
        """
        if not self._loaded or self.model is None:
            raise RuntimeError(f"[{self.name}] Model not loaded. Call load() first.")

        results = self.model.predict(
            image,
            conf=conf or self.confidence,
            iou=NMS_IOU_THRESHOLD,
            classes=classes or self.allowed_classes,
            verbose=False,
        )

        detections: List[Detection] = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf_val = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                class_name = self.model.names.get(cls_id, f"class_{cls_id}")

                detections.append(Detection(
                    class_name=class_name,
                    confidence=conf_val,
                    bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    model_source=self.name,
                ))

        return detections

    def detect(self, image: np.ndarray) -> List[Detection]:
        """
        Run detection. Override in subclasses for custom filtering.
        Default: return all detections from _raw_detect.
        """
        return self._raw_detect(image)

    def track(
        self,
        image: np.ndarray,
        persist: bool = True,
        tracker: str = "bytetrack.yaml",
        conf: Optional[float] = None,
        classes: Optional[List[int]] = None,
    ) -> List[Detection]:
        """
        Run tracking (ByteTrack/BoT-SORT) and return Detections with track_id.
        """
        if not self._loaded or self.model is None:
            raise RuntimeError(f"[{self.name}] Model not loaded. Call load() first.")

        results = self.model.track(
            image,
            persist=persist,
            tracker=tracker,
            conf=conf or self.confidence,
            iou=NMS_IOU_THRESHOLD,
            classes=classes or self.allowed_classes,
            verbose=False,
        )

        detections: List[Detection] = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf_val = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                class_name = self.model.names.get(cls_id, f"class_{cls_id}")
                
                # Check for track_id
                track_id = None
                if box.id is not None:
                    track_id = int(box.id[0])

                detections.append(Detection(
                    class_name=class_name,
                    confidence=conf_val,
                    bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    model_source=self.name,
                    track_id=track_id
                ))

        return detections
