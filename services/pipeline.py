"""
Unified Inference Pipeline.

Architecture (vehicle-first crop-based routing):

    Image
      |
    Preprocess
      |
    Vehicle Detector (full image)
      |
      +-- Motorcycle/Bicycle Crop
      |      +-- Helmet Detector
      |      +-- Triple Riding Detector
      |      +-- Plate Detector --> OCR
      |
      +-- Car/Bus/Truck Crop
      |      +-- Seatbelt Detector
      |      +-- Plate Detector --> OCR
      |
      +-- Full Image (scene-level)
             +-- Traffic Signal Detector
             +-- Illegal Parking Detector

Models are loaded once at startup (singleton pattern).
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from config import (
    TWO_WHEELER_TYPES,
    FOUR_WHEELER_TYPES,
    CROP_PAD_FRACTION,
    INFERENCE_OUTPUTS_DIR,
)
from detectors.vehicle import VehicleDetector
from detectors.helmet import HelmetDetector
from detectors.seatbelt import SeatbeltDetector
from detectors.triple_riding import TripleRidingDetector
from detectors.traffic_signal import TrafficSignalDetector
from detectors.illegal_parking import IllegalParkingDetector
from detectors.plate import PlateDetector
from engine.rules import ViolationRuleEngine
from ocr.plate_reader import PlateReader
from ocr.openai_plate_reader import OpenAIPlateReader
from database.mongo import MongoDB
from services.evidence import EvidenceManager
from utils.preprocess import preprocess_image, crop_region
from utils.annotate import annotate_image
from utils.schemas import (
    Detection, BBox, Violation,
    VehicleResult, PredictionResponse,
)
from engine.challan import ChallanManager

logger = logging.getLogger(__name__)


class InferencePipeline:
    """
    Singleton inference pipeline. Load once, predict many.
    """

    def __init__(self):
        # Detectors
        self.vehicle_detector = VehicleDetector()
        self.helmet_detector = HelmetDetector()
        self.seatbelt_detector = SeatbeltDetector()
        self.triple_riding_detector = TripleRidingDetector()
        self.traffic_signal_detector = TrafficSignalDetector()
        self.illegal_parking_detector = IllegalParkingDetector()
        self.plate_detector = PlateDetector()

        # OCR
        self.plate_reader = PlateReader()
        self.openai_plate_reader = OpenAIPlateReader()

        # Rule engine (stateless)
        self.rules = ViolationRuleEngine()

        # Database & Evidence
        self.db = MongoDB()
        self.evidence_manager = EvidenceManager()
        self.challan_manager = ChallanManager(self.db)

        self._loaded = False
        self._load_time: Optional[float] = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def uptime_seconds(self) -> float:
        if self._load_time is None:
            return 0.0
        return time.time() - self._load_time

    def load_models(self) -> None:
        """Load all models and OCR engines. Called once at startup."""
        if self._loaded:
            logger.warning("Models already loaded, skipping")
            return

        logger.info("=" * 60)
        logger.info("  LOADING INFERENCE PIPELINE")
        logger.info("=" * 60)

        start = time.time()

        # Load all detectors
        detectors = [
            self.vehicle_detector,
            self.helmet_detector,
            self.seatbelt_detector,
            self.triple_riding_detector,
            self.traffic_signal_detector,
            self.illegal_parking_detector,
            self.plate_detector,
        ]

        for det in detectors:
            try:
                det.load()
            except Exception as e:
                logger.error(f"Failed to load {det.name}: {e}")

        # Load OCR
        try:
            self.plate_reader.load()
        except Exception as e:
            logger.error(f"Failed to load OCR: {e}")

        # Connect database
        try:
            self.db.connect()
        except Exception as e:
            logger.error(f"Failed to connect DB: {e}")

        elapsed = time.time() - start
        self._loaded = True
        self._load_time = time.time()

        logger.info(f"Pipeline loaded in {elapsed:.1f}s")
        logger.info("=" * 60)

    def get_model_info(self) -> list:
        """Return info about all loaded models."""
        detectors = [
            self.vehicle_detector,
            self.helmet_detector,
            self.seatbelt_detector,
            self.triple_riding_detector,
            self.traffic_signal_detector,
            self.illegal_parking_detector,
            self.plate_detector,
        ]
        info = []
        for det in detectors:
            info.append({
                "name": det.name,
                "status": "loaded" if det.is_loaded else "not loaded",
                "weight_path": str(det.weight_path),
                "class_names": det.get_class_names(),
                "confidence_threshold": det.confidence,
            })
        return info

    # ── Per-rider helmet check ───────────────────────────────────────────

    # Stricter than the whole-bike helmet threshold, since these are extra checks
    PER_RIDER_HELMET_MIN_CONF = 0.25

    def _per_rider_helmet_checks(
        self,
        crop: np.ndarray,
        rider_dets: List[Detection],
        helmet_dets: List[Detection],
    ) -> List[Detection]:
        """
        Run the helmet model on each detected rider's head area (crop coords).
        Returns only NEW Helmet/NoHelmet detections for heads that the
        whole-bike pass did not already cover, so existing results never change.
        """
        head_classes = (HelmetDetector.CLS_HELMET, HelmetDetector.CLS_NO_HELMET)
        known = [d for d in helmet_dets if d.class_name in head_classes]
        added: List[Detection] = []
        h, w = crop.shape[:2]

        def center_in(box: BBox, other: BBox) -> bool:
            cx, cy = (box.x1 + box.x2) / 2, (box.y1 + box.y2) / 2
            return other.x1 <= cx <= other.x2 and other.y1 <= cy <= other.y2

        for person in rider_dets:
            if person.class_name != "person":
                continue
            pb = person.bbox
            bw, bh = pb.x2 - pb.x1, pb.y2 - pb.y1
            if bw < 8 or bh < 8:
                continue
            # Head + shoulders: top ~45% of the person box, slightly padded
            hx1 = int(max(0, pb.x1 - 0.15 * bw))
            hx2 = int(min(w, pb.x2 + 0.15 * bw))
            hy1 = int(max(0, pb.y1 - 0.10 * bh))
            hy2 = int(min(h, pb.y1 + 0.45 * bh))
            if hx2 - hx1 < 8 or hy2 - hy1 < 8:
                continue

            try:
                dets = self.helmet_detector.detect(crop[hy1:hy2, hx1:hx2])
            except Exception as e:
                logger.warning(f"Per-rider helmet check failed: {e}")
                continue
            dets = [
                d for d in dets
                if d.class_name in head_classes and d.confidence >= self.PER_RIDER_HELMET_MIN_CONF
            ]
            if not dets:
                continue

            best = max(dets, key=lambda d: d.confidence)
            head = BBox(
                x1=best.bbox.x1 + hx1, y1=best.bbox.y1 + hy1,
                x2=best.bbox.x2 + hx1, y2=best.bbox.y2 + hy1,
            )
            already = any(
                self.rules._bbox_iou(e.bbox, head) > 0.3
                or center_in(head, e.bbox) or center_in(e.bbox, head)
                for e in known + added
            )
            if not already:
                added.append(Detection(
                    class_name=best.class_name,
                    confidence=best.confidence,
                    bbox=head,
                    model_source=best.model_source,
                ))

        if added:
            logger.info(f"Per-rider helmet check added {len(added)} head(s)")
        return added

    # ── Core Inference ───────────────────────────────────────────────────

    def predict(
        self,
        image: np.ndarray,
        save_annotated: bool = True,
    ) -> PredictionResponse:
        """
        Run the full inference pipeline on a single image.

        Flow:
        1. Preprocess image
        2. Detect vehicles (full image)
        3. For each vehicle crop, run relevant sub-detectors
        4. Run scene-level detectors (signal, parking) on full image
        5. Apply rule engine
        6. Run plate OCR
        7. Annotate evidence image
        8. Store violations in DB
        """
        start_time = time.time()
        image_id = str(uuid.uuid4())[:12]
        timestamp = datetime.now(timezone.utc).isoformat()
        h, w = image.shape[:2]

        logger.info(f"[{image_id}] Starting prediction ({w}x{h})")

        # ── Step 1: Preprocess ───────────────────────────────────────────
        preprocessed = preprocess_image(image)

        # ── Step 2: Vehicle Detection (full image) ───────────────────────
        vehicle_detections = self.vehicle_detector.detect(preprocessed)
        logger.info(f"[{image_id}] Found {len(vehicle_detections)} vehicles")

        # ── Step 3: Scene-level detectors (full image) ───────────────────
        # Only run scene-level detectors if vehicles were found.
        # These custom models have high false-positive rates on random images,
        # so gating on vehicle presence prevents phantom violations.
        scene_violations: List[Violation] = []
        signal_detections: List[Detection] = []

        if vehicle_detections:
            signal_detections = self.traffic_signal_detector.detect(preprocessed)
            parking_detections = self.illegal_parking_detector.detect(preprocessed)
            parking_viols = self.rules.check_illegal_parking(parking_detections)
            scene_violations.extend(parking_viols)

        # License plate path only. If OPENAI_API_KEY is configured, use OpenAI
        # vision for plate text and keep all other detectors local/unchanged.
        use_openai_plate_reader = self.openai_plate_reader.is_available
        full_frame_plate_text = None
        full_frame_plate_conf = None
        full_frame_plate_bbox = None
        full_plate_dets: List[Detection] = []

        if use_openai_plate_reader:
            full_frame_plate_text, full_frame_plate_conf = self.openai_plate_reader.read_plate(image)
        else:
            full_plate_dets = self.plate_detector.detect(preprocessed)
            best_full_plate = self.plate_detector.get_best_plate(full_plate_dets)
            if best_full_plate:
                full_frame_plate_bbox = best_full_plate.bbox
                full_frame_plate_text, full_frame_plate_conf = self.plate_reader.crop_and_read(
                    image,
                    int(best_full_plate.bbox.x1), int(best_full_plate.bbox.y1),
                    int(best_full_plate.bbox.x2), int(best_full_plate.bbox.y2),
                )

            if not full_frame_plate_text:
                direct_text, direct_conf, direct_bbox = self.plate_reader.direct_ocr_scan(preprocessed)
                if direct_text and direct_bbox:
                    full_frame_plate_text = direct_text
                    full_frame_plate_conf = direct_conf
                    full_frame_plate_bbox = BBox(
                        x1=direct_bbox[0],
                        y1=direct_bbox[1],
                        x2=direct_bbox[2],
                        y2=direct_bbox[3],
                    )

        def plate_matches_vehicle(plate_bbox: BBox | None, vehicle_bbox: BBox) -> bool:
            if plate_bbox is None:
                return False
            margin = 80
            px = (plate_bbox.x1 + plate_bbox.x2) / 2
            py = (plate_bbox.y1 + plate_bbox.y2) / 2
            return (
                vehicle_bbox.x1 - margin <= px <= vehicle_bbox.x2 + margin and
                vehicle_bbox.y1 - margin <= py <= vehicle_bbox.y2 + margin
            )

        # ── Step 4: Per-vehicle analysis ─────────────────────────────────
        vehicle_results: List[VehicleResult] = []

        for v_idx, v_det in enumerate(vehicle_detections):
            v_type = v_det.class_name
            v_bbox = v_det.bbox

            # For two-wheelers, the bounding box often cuts off the riders' heads and edge passengers.
            # We expand the crop significantly upwards (40%) and horizontally/bottom (30%) 
            # to ensure all passengers are captured for triple-riding and helmet checks.
            pad_top = 0.40 if v_type in TWO_WHEELER_TYPES else None
            pad_horiz = 0.30 if v_type in TWO_WHEELER_TYPES else CROP_PAD_FRACTION

            # Crop the vehicle region with padding
            crop, (cx1, cy1, cx2, cy2) = crop_region(
                preprocessed,
                int(v_bbox.x1), int(v_bbox.y1),
                int(v_bbox.x2), int(v_bbox.y2),
                pad_fraction=pad_horiz,
                pad_top_fraction=pad_top,
            )

            violations: List[Violation] = []
            all_dets: List[Detection] = [v_det]

            def to_full(dets: List[Detection], ox: int = cx1, oy: int = cy1) -> List[Detection]:
                """Shift crop-relative detections into full-image coordinates."""
                return [
                    Detection(
                        class_name=d.class_name,
                        confidence=d.confidence,
                        bbox=BBox(x1=d.bbox.x1 + ox, y1=d.bbox.y1 + oy,
                                  x2=d.bbox.x2 + ox, y2=d.bbox.y2 + oy),
                        model_source=d.model_source,
                    )
                    for d in dets
                ]

            # ── Route to sub-detectors based on vehicle type ─────────
            if v_type in TWO_WHEELER_TYPES:
                # Motorcycle/Bicycle → Helmet + Triple Riding + Plate
                helmet_dets = self.helmet_detector.detect(crop)
                triple_dets = self.triple_riding_detector.detect(crop)
                # Re-check each rider's head on its own to catch heads the
                # whole-bike pass missed (e.g. a half-hidden middle passenger)
                helmet_dets = helmet_dets + self._per_rider_helmet_checks(
                    crop, triple_dets, helmet_dets
                )
                all_dets.extend(to_full(helmet_dets))
                all_dets.extend(to_full(triple_dets))

                # Helmet violations
                helmet_viols = self.rules.check_helmet(helmet_dets)
                violations.extend(helmet_viols)

                # Triple riding violations
                triple_viols = self.rules.check_triple_riding(triple_dets)
                violations.extend(triple_viols)

            elif v_type in FOUR_WHEELER_TYPES:
                # Car/Bus/Truck → Seatbelt + Plate
                seatbelt_dets = self.seatbelt_detector.detect(crop)
                all_dets.extend(to_full(seatbelt_dets))

                # Seatbelt violations (direct model output)
                seatbelt_viols = self.rules.check_seatbelt(seatbelt_dets)
                violations.extend(seatbelt_viols)

            # ── Red light check (needs scene-level signal + vehicle bbox)
            red_viols = self.rules.check_red_light(signal_detections, v_bbox)
            violations.extend(red_viols)

            # ── Plate Detection + OCR (all vehicle types) ────────────
            plate_text = None
            plate_conf = None
            plate_bbox_result = None

            if use_openai_plate_reader:
                original_vehicle_crop = image[cy1:cy2, cx1:cx2]
                plate_text, plate_conf = self.openai_plate_reader.read_plate(original_vehicle_crop)
                if not plate_text and len(vehicle_detections) == 1:
                    plate_text = full_frame_plate_text
                    plate_conf = full_frame_plate_conf

                vehicle_results.append(VehicleResult(
                    vehicle_id=v_idx,
                    vehicle_type=v_type,
                    bbox=v_bbox,
                    license_plate=plate_text,
                    plate_confidence=plate_conf,
                    plate_bbox=plate_bbox_result,
                    violations=violations,
                    all_detections=all_dets,
                ))
                continue

            plate_dets = self.plate_detector.detect(crop)
            best_plate = self.plate_detector.get_best_plate(plate_dets)

            # Fallback 1: Try a wider crop if no plate found in tight crop
            if not best_plate:
                wider_crop, (wcx1, wcy1, wcx2, wcy2) = crop_region(
                    preprocessed,
                    int(v_bbox.x1), int(v_bbox.y1),
                    int(v_bbox.x2), int(v_bbox.y2),
                    pad_fraction=0.30,  # 30% wider padding
                )
                plate_dets_wide = self.plate_detector.detect(wider_crop)
                best_plate_wide = self.plate_detector.get_best_plate(plate_dets_wide)
                if best_plate_wide:
                    best_plate = best_plate_wide
                    # Remap coordinates from wider crop
                    cx1, cy1 = wcx1, wcy1

            # Fallback 2: Try on full image around the vehicle area
            if not best_plate:
                # Find plate closest to vehicle bbox
                for pd in sorted(full_plate_dets, key=lambda d: d.confidence, reverse=True):
                    # Check if plate overlaps with vehicle bbox area (with margin)
                    margin = 50
                    if (pd.bbox.x1 >= v_bbox.x1 - margin and
                        pd.bbox.y1 >= v_bbox.y1 - margin and
                        pd.bbox.x2 <= v_bbox.x2 + margin and
                        pd.bbox.y2 <= v_bbox.y2 + margin):
                        best_plate = pd
                        cx1, cy1 = 0, 0  # full image coords, no offset
                        break

            if best_plate:
                # Map plate bbox back to full image coordinates
                plate_bbox_full = BBox(
                    x1=best_plate.bbox.x1 + cx1,
                    y1=best_plate.bbox.y1 + cy1,
                    x2=best_plate.bbox.x2 + cx1,
                    y2=best_plate.bbox.y2 + cy1,
                )
                plate_bbox_result = plate_bbox_full

                # OCR on the plate region from original image
                plate_text, plate_conf = self.plate_reader.crop_and_read(
                    image,  # use original for better OCR quality
                    int(plate_bbox_full.x1), int(plate_bbox_full.y1),
                    int(plate_bbox_full.x2), int(plate_bbox_full.y2),
                )

            # ── Fallback 3: Direct OCR scan on vehicle crop ──────────
            # If the YOLO plate model completely failed (which happens often
            # with the custom model), bypass it and run EasyOCR directly
            # on the vehicle crop to find plate-like text.
            if not plate_text:
                direct_text, direct_conf, direct_bbox = self.plate_reader.direct_ocr_scan(crop)
                if direct_text:
                    plate_text = direct_text
                    plate_conf = direct_conf
                    if direct_bbox:
                        plate_bbox_result = BBox(
                            x1=direct_bbox[0] + cx1,
                            y1=direct_bbox[1] + cy1,
                            x2=direct_bbox[2] + cx1,
                            y2=direct_bbox[3] + cy1,
                        )

            # Fallback 4: full-frame OCR result, attached to the vehicle whose
            # expanded box contains the detected text region. If there is only
            # one vehicle, use it even when the OCR bbox is imperfect.
            if (
                not plate_text
                and full_frame_plate_text
                and (
                    len(vehicle_detections) == 1
                    or plate_matches_vehicle(full_frame_plate_bbox, v_bbox)
                )
            ):
                plate_text = full_frame_plate_text
                plate_conf = full_frame_plate_conf
                plate_bbox_result = full_frame_plate_bbox

            # ── Build vehicle result ─────────────────────────────────
            vehicle_results.append(VehicleResult(
                vehicle_id=v_idx,
                vehicle_type=v_type,
                bbox=v_bbox,
                license_plate=plate_text,
                plate_confidence=plate_conf,
                plate_bbox=plate_bbox_result,
                violations=violations,
                all_detections=all_dets,
            ))

        # ── Step 5: Process Evidence if Violations Detected ──────────────
        if not vehicle_results and full_frame_plate_text:
            inferred_plate_bbox = full_frame_plate_bbox or BBox(x1=0, y1=0, x2=w, y2=h)
            vehicle_results.append(VehicleResult(
                vehicle_id=0,
                vehicle_type="unknown",
                bbox=inferred_plate_bbox,
                license_plate=full_frame_plate_text,
                plate_confidence=full_frame_plate_conf,
                plate_bbox=full_frame_plate_bbox,
                violations=[],
                all_detections=full_plate_dets,
            ))

        total_violations = sum(len(v.violations) for v in vehicle_results) + len(scene_violations)
        
        evidence_id = None
        annotated_path = None
        
        if total_violations > 0 and save_annotated:
            # Generate new evidence ID
            evidence_id = self.evidence_manager.generate_evidence_id()
            
            # Annotate with evidence ID
            annotated = annotate_image(
                image, vehicle_results, scene_violations, 
                evidence_id=evidence_id, timestamp=timestamp
            )
            
            # Save package
            elapsed_ms = (time.time() - start_time) * 1000
            report_data = self.evidence_manager.create_evidence_package(
                original_image=image,
                annotated_image=annotated,
                vehicle_results=vehicle_results,
                scene_violations=scene_violations,
                processing_time_ms=elapsed_ms,
                evidence_id=evidence_id,
                timestamp=timestamp,
            )
            
            # Save to MongoDB
            try:
                self.db.insert_evidence(report_data)
                logger.info(f"[{image_id}] Stored evidence {evidence_id} in MongoDB")
                
                # Phase 6: Auto-Challan Evaluation
                self.challan_manager.evaluate_evidence(report_data)
                
            except Exception as e:
                logger.error(f"[{image_id}] DB insert failed: {e}")
                
            annotated_path = report_data["annotated_path"]
        else:
            # No violations, just return regular metadata
            elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[{image_id}] Done: {len(vehicle_results)} vehicles, "
            f"{total_violations} violations, {elapsed_ms:.0f}ms"
        )

        return PredictionResponse(
            image_id=image_id,
            evidence_id=evidence_id,
            timestamp=timestamp,
            processing_time_ms=round(elapsed_ms, 1),
            image_width=w,
            image_height=h,
            total_vehicles=len(vehicle_results),
            total_violations=total_violations,
            vehicles=vehicle_results,
            scene_violations=scene_violations,
            annotated_image_path=annotated_path,
        )
