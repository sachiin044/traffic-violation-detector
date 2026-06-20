"""
Annotation utilities for generating evidence images.
Draws bounding boxes, violation labels, confidence scores, and plate text.
"""

import cv2
import numpy as np
from typing import List

from utils.schemas import VehicleResult, Violation
from config import COLORS


def draw_bbox(
    image: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    color: tuple,
    thickness: int = 2,
    label: str = "",
    confidence: float = 0.0,
    font_scale: float = 0.6,
) -> np.ndarray:
    """Draw a bounding box with optional label and confidence."""
    cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

    if label:
        text = f"{label}"
        if confidence > 0:
            text += f" ({confidence:.0%})"

        (text_w, text_h), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )

        # Background rectangle for text
        cv2.rectangle(
            image,
            (x1, y1 - text_h - baseline - 6),
            (x1 + text_w + 4, y1),
            color,
            -1,
        )

        # Text
        cv2.putText(
            image,
            text,
            (x1 + 2, y1 - baseline - 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            COLORS["text"],
            1,
            cv2.LINE_AA,
        )

    return image


def draw_violation_label(
    image: np.ndarray,
    x1: int, y1: int, x2: int,
    violation: Violation,
    offset_y: int = 0,
    font_scale: float = 0.55,
) -> np.ndarray:
    """Draw a violation label below the vehicle bounding box."""
    text = f"[!] {violation.type} ({violation.confidence:.0%})"

    (text_w, text_h), baseline = cv2.getTextSize(
        text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
    )

    label_y = y1 + offset_y + text_h + 8

    # Red background for violation
    cv2.rectangle(
        image,
        (x1, label_y - text_h - 4),
        (x1 + text_w + 6, label_y + 4),
        COLORS["violation"],
        -1,
    )

    cv2.putText(
        image,
        text,
        (x1 + 3, label_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        COLORS["text"],
        1,
        cv2.LINE_AA,
    )

    return image


def draw_plate_text(
    image: np.ndarray,
    x1: int, y2: int,
    plate_text: str,
    font_scale: float = 0.65,
) -> np.ndarray:
    """Draw license plate text below the plate bounding box."""
    text = f"PLATE: {plate_text}"

    (text_w, text_h), baseline = cv2.getTextSize(
        text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2
    )

    label_y = y2 + text_h + 8

    # Green background for plate
    cv2.rectangle(
        image,
        (x1, label_y - text_h - 4),
        (x1 + text_w + 6, label_y + 4),
        COLORS["plate"],
        -1,
    )

    cv2.putText(
        image,
        text,
        (x1 + 3, label_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    return image


def annotate_image(
    image: np.ndarray,
    vehicles: List[VehicleResult],
    scene_violations: List[Violation] = None,
    evidence_id: str = "",
    timestamp: str = "",
) -> np.ndarray:
    """
    Generate a fully annotated evidence image.

    Draws:
    - Vehicle bounding boxes (orange)
    - Violation labels (red) stacked under each vehicle
    - License plate boxes (green) with OCR text
    - Scene-level violations at the top
    """
    annotated = image.copy()

    for vehicle in vehicles:
        bbox = vehicle.bbox
        x1, y1 = int(bbox.x1), int(bbox.y1)
        x2, y2 = int(bbox.x2), int(bbox.y2)

        # Vehicle box
        annotated = draw_bbox(
            annotated, x1, y1, x2, y2,
            color=COLORS["vehicle"],
            label=vehicle.vehicle_type.upper(),
            thickness=2,
        )

        # Violation labels stacked below the box
        offset = 0
        for violation in vehicle.violations:
            annotated = draw_violation_label(
                annotated, x1, y2, x2, violation, offset_y=offset
            )
            offset += 28

        # Plate box + text
        if vehicle.plate_bbox:
            px1, py1 = int(vehicle.plate_bbox.x1), int(vehicle.plate_bbox.y1)
            px2, py2 = int(vehicle.plate_bbox.x2), int(vehicle.plate_bbox.y2)
            annotated = draw_bbox(
                annotated, px1, py1, px2, py2,
                color=COLORS["plate"],
                label="Plate",
                confidence=vehicle.plate_confidence or 0.0,
                thickness=2,
            )
            if vehicle.license_plate:
                annotated = draw_plate_text(annotated, px1, py2, vehicle.license_plate)

    # Scene-level violations (top of image)
    offset = 10
    if scene_violations:
        for sv in scene_violations:
            text = f"[SCENE] {sv.type} ({sv.confidence:.0%})"
            (tw, th), _ = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
            )
            cv2.rectangle(
                annotated,
                (10, offset),
                (10 + tw + 10, offset + th + 10),
                COLORS["violation"],
                -1,
            )
            cv2.putText(
                annotated, text,
                (15, offset + th + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                COLORS["text"], 2, cv2.LINE_AA,
            )
            offset += th + 20

    # Draw Evidence ID & Timestamp (top right)
    if evidence_id:
        text = f"ID: {evidence_id} | {timestamp[:19]}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        h, w = annotated.shape[:2]
        
        cv2.rectangle(
            annotated,
            (w - tw - 20, 10),
            (w - 10, 10 + th + 10),
            (0, 0, 0),
            -1,
        )
        cv2.putText(
            annotated, text,
            (w - tw - 15, 10 + th + 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
            (255, 255, 255), 2, cv2.LINE_AA,
        )

    return annotated
