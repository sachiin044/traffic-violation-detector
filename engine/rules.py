"""
Violation Rule Engine.

Maps detection combinations to violation types using the improved
vehicle-first crop-based architecture:

Image
  |
Vehicle Detector
  |
  +-- Motorcycle Crop --> Helmet, Triple Riding, Plate
  +-- Car/Bus/Truck Crop --> Seatbelt, Plate
  +-- Full Image --> Traffic Signal, Illegal Parking

Seatbelt logic: no-seatbelt detection above threshold IS the violation
directly — no need to additionally require vehicle detection gate.

Red-light logic (image-only MVP): red_light detected AND vehicle bbox
overlaps stop_line. Single-image limitation documented.
"""

import logging
from typing import List, Tuple

from utils.schemas import Detection, Violation, BBox

logger = logging.getLogger(__name__)


class ViolationRuleEngine:
    """Stateless rule engine that maps detections to violations."""

    # ── Violation Type Constants ──────────────────────────────────────────
    HELMET_NON_COMPLIANCE = "Helmet Non Compliance"
    SEATBELT_NON_COMPLIANCE = "Seatbelt Non Compliance"
    TRIPLE_RIDING = "Triple Riding"
    RED_LIGHT_VIOLATION = "Red Light Violation"
    ILLEGAL_PARKING = "Illegal Parking"

    # ── Helmet Rules ─────────────────────────────────────────────────────
    @staticmethod
    def check_helmet(
        helmet_detections: List[Detection],
    ) -> List[Violation]:
        """
        Rule: NoHelmet detection on a motorcycle crop = violation.
        """
        violations = []
        no_helmet = [d for d in helmet_detections if d.class_name == "NoHelmet"]

        for det in no_helmet:
            violations.append(Violation(
                type=ViolationRuleEngine.HELMET_NON_COMPLIANCE,
                confidence=det.confidence,
                details=f"No helmet detected (conf: {det.confidence:.2f})",
            ))

        return violations

    # ── Seatbelt Rules ───────────────────────────────────────────────────
    @staticmethod
    def check_seatbelt(
        seatbelt_detections: List[Detection],
    ) -> List[Violation]:
        """
        Rule: no-seatbelt detection above threshold IS the violation.
        The model directly predicts seatbelt/no-seatbelt.
        """
        violations = []
        no_belt = [d for d in seatbelt_detections if d.class_name == "no-seatbelt"]
        belt = [d for d in seatbelt_detections if d.class_name == "seatbelt"]

        for nb in no_belt:
            # Suppress if there's an overlapping 'seatbelt' detection with reasonable confidence
            suppressed = False
            for b in belt:
                iou = ViolationRuleEngine._bbox_iou(nb.bbox, b.bbox)
                # If they overlap and the model also thinks there is a seatbelt,
                # trust the seatbelt detection to avoid false positives.
                if iou > 0.1 and b.confidence >= nb.confidence * 0.5:
                    suppressed = True
                    break
            
            if suppressed:
                continue

            violations.append(Violation(
                type=ViolationRuleEngine.SEATBELT_NON_COMPLIANCE,
                confidence=nb.confidence,
                details=f"No seatbelt detected (conf: {nb.confidence:.2f})",
            ))

        return violations

    # ── Triple Riding Rules ──────────────────────────────────────────────
    @staticmethod
    def _bbox_iou(a: 'BBox', b: 'BBox') -> float:
        """Compute IoU between two bounding boxes."""
        x1 = max(a.x1, b.x1)
        y1 = max(a.y1, b.y1)
        x2 = min(a.x2, b.x2)
        y2 = min(a.y2, b.y2)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (a.x2 - a.x1) * (a.y2 - a.y1)
        area_b = (b.x2 - b.x1) * (b.y2 - b.y1)
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0

    @staticmethod
    def _bbox_area(b: 'BBox') -> float:
        return max(0, b.x2 - b.x1) * max(0, b.y2 - b.y1)

    @staticmethod
    def check_triple_riding(
        triple_detections: List[Detection],
    ) -> List[Violation]:
        """
        Rule: rider_region detection = 3+ riders on motorcycle OR 3+ persons detected.

        Balanced validation to reduce false positives while catching real violations:
        1. 3+ person detections on a single bike crop = violation (strongest signal)
        2. High confidence rider_region (>=0.70) + at least 2 person detections = violation
        3. Single person + rider_region = suppressed (likely false positive)
        """
        violations = []
        regions = [d for d in triple_detections if d.class_name == "rider_region"]
        persons = [d for d in triple_detections if d.class_name == "person"]
        num_persons = len(persons)

        # Path 1: 3+ persons detected is definitive proof of triple riding
        # We use the confidence of the 3rd most confident person detection
        if num_persons >= 3:
            sorted_persons = sorted(persons, key=lambda p: p.confidence, reverse=True)
            violations.append(Violation(
                type=ViolationRuleEngine.TRIPLE_RIDING,
                confidence=sorted_persons[2].confidence,  # Confidence of the 3rd person
            ))
            return violations

        if not regions:
            return violations

        for det in regions:
            # Path 2: Strong rider_region + at least 2 persons visible
            if det.confidence >= 0.70 and num_persons >= 2:
                violations.append(Violation(
                    type=ViolationRuleEngine.TRIPLE_RIDING,
                    confidence=det.confidence,
                ))
            else:
                logger.debug(
                    f"Triple riding suppressed: "
                    f"{num_persons} person(s), rider_region conf={det.confidence:.2f}"
                )

        return violations

    # ── Red Light Rules ──────────────────────────────────────────────────
    @staticmethod
    def check_red_light(
        signal_detections: List[Detection],
        vehicle_bbox: BBox,
    ) -> List[Violation]:
        """
        Rule (image-only MVP):
          - red_light detected in scene
          - AND vehicle bbox overlaps / crosses stop_line

        LIMITATION: True red-light running requires multi-frame tracking.
        For single-image, we use spatial overlap as proxy.
        """
        violations = []

        red_lights = [d for d in signal_detections if d.class_name == "red_light"]
        stop_lines = [d for d in signal_detections if d.class_name == "stop_line"]

        if not red_lights or not stop_lines:
            return violations

        best_red_conf = max(d.confidence for d in red_lights)

        for sl in stop_lines:
            # Vehicle bottom edge at or past stop line top
            if vehicle_bbox.y2 >= sl.bbox.y1:
                violations.append(Violation(
                    type=ViolationRuleEngine.RED_LIGHT_VIOLATION,
                    confidence=best_red_conf,
                    details=(
                        f"Vehicle crosses stop line during red signal "
                        f"(red conf: {best_red_conf:.2f}). "
                        f"Note: single-image analysis — "
                        f"multi-frame tracking recommended for production."
                    ),
                ))
                break  # one stop line match is enough

        return violations

    # ── Illegal Parking Rules ────────────────────────────────────────────
    @staticmethod
    def check_illegal_parking(
        parking_detections: List[Detection],
    ) -> List[Violation]:
        """
        Rule: illegal_parking detection = violation.
        """
        violations = []

        for det in parking_detections:
            if det.class_name == "illegal_parking":
                violations.append(Violation(
                    type=ViolationRuleEngine.ILLEGAL_PARKING,
                    confidence=det.confidence,
                    details=f"Illegal parking detected (conf: {det.confidence:.2f})",
                ))

        return violations

    # ── Aggregate ────────────────────────────────────────────────────────
    @staticmethod
    def aggregate_violations(*violation_lists: List[Violation]) -> List[Violation]:
        """
        Merge multiple violation lists, deduplicating by type
        and keeping the highest confidence for each.
        """
        best: dict[str, Violation] = {}

        for vlist in violation_lists:
            for v in vlist:
                if v.type not in best or v.confidence > best[v.type].confidence:
                    best[v.type] = v

        return list(best.values())
