"""
Annotation utilities for generating evidence images.

Draws, scaled to the image size so labels stay readable on large photos:
- Vehicle boxes (orange) with the vehicle type
- Helmet / no-helmet and seatbelt / no-seatbelt boxes on each vehicle
- Violation labels (red) stacked under each vehicle box, kept inside the frame
- License plate box (green) with OCR text
- Scene-level violations (top-left) and evidence ID + timestamp (top-right)
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple

from utils.schemas import VehicleResult, Violation
from config import COLORS

FONT = cv2.FONT_HERSHEY_SIMPLEX

# Sub-detections worth showing on evidence: class -> (colour BGR, label)
SUB_DETECTION_STYLE = {
    "NoHelmet":    (COLORS["violation"], "No helmet"),
    "Helmet":      (COLORS["helmet_ok"], "Helmet"),
    "no-seatbelt": (COLORS["violation"], "No seatbelt"),
    "seatbelt":    (COLORS["seatbelt_ok"], "Seatbelt"),
}


class _Style:
    """Font size and line thickness derived from image size."""

    def __init__(self, image: np.ndarray):
        h, w = image.shape[:2]
        s = max(0.5, min(3.0, max(h, w) / 1000.0))
        # Floors keep labels legible on small photos (e.g. 759x422)
        self.font = max(0.5, 0.55 * s)
        self.small_font = max(0.42, 0.45 * s)
        self.text_thick = max(1, int(round(1.2 * s)))
        self.box_thick = max(2, int(round(2.5 * s)))
        self.thin_box = max(1, int(round(1.5 * s)))
        self.pad = max(3, int(round(4 * s)))
        self.w, self.h = w, h


def _text_size(text: str, font: float, thick: int) -> Tuple[int, int, int]:
    (tw, th), base = cv2.getTextSize(text, FONT, font, thick)
    return tw, th, base


def _draw_label(
    image: np.ndarray, st: _Style, text: str, x: int, y: int,
    bg: tuple, fg: tuple = None, font: Optional[float] = None, above: bool = True,
) -> Tuple[int, int, int, int]:
    """
    Draw a filled label. If `above`, its bottom edge sits at y; otherwise its top
    edge sits at y. The label is shifted as needed to stay inside the image.
    Returns the label rectangle (x1, y1, x2, y2).
    """
    font = font or st.font
    fg = fg or COLORS["text"]
    tw, th, base = _text_size(text, font, st.text_thick)
    lw, lh = tw + 2 * st.pad, th + base + 2 * st.pad

    x1 = int(min(max(0, x), max(0, st.w - lw)))
    y1 = int(y - lh if above else y)
    if y1 < 0:                 # no room above: put it below instead
        y1 = int(y if above else 0)
    y1 = int(min(max(0, y1), max(0, st.h - lh)))
    x2, y2 = x1 + lw, y1 + lh

    cv2.rectangle(image, (x1, y1), (x2, y2), bg, -1)
    cv2.putText(image, text, (x1 + st.pad, y2 - st.pad - base), FONT, font, fg,
                st.text_thick, cv2.LINE_AA)
    return x1, y1, x2, y2


def _clip_box(st: _Style, b) -> Tuple[int, int, int, int]:
    return (
        int(max(0, min(st.w - 1, b.x1))), int(max(0, min(st.h - 1, b.y1))),
        int(max(0, min(st.w - 1, b.x2))), int(max(0, min(st.h - 1, b.y2))),
    )


def annotate_image(
    image: np.ndarray,
    vehicles: List[VehicleResult],
    scene_violations: List[Violation] = None,
    evidence_id: str = "",
    timestamp: str = "",
) -> np.ndarray:
    """Generate a fully annotated evidence image."""
    annotated = image.copy()
    st = _Style(annotated)

    for vehicle in vehicles:
        x1, y1, x2, y2 = _clip_box(st, vehicle.bbox)
        has_violation = bool(vehicle.violations)
        v_color = COLORS["violation"] if has_violation else COLORS["vehicle"]

        # Vehicle box + type label
        cv2.rectangle(annotated, (x1, y1), (x2, y2), v_color, st.box_thick)
        _draw_label(annotated, st, vehicle.vehicle_type.upper().replace("_", " "),
                    x1, y1, bg=v_color, above=True)

        # Helmet / seatbelt boxes found on this vehicle (stored in full-image coords)
        for det in (vehicle.all_detections or [])[1:]:
            style = SUB_DETECTION_STYLE.get(det.class_name)
            if not style:
                continue
            color, name = style
            dx1, dy1, dx2, dy2 = _clip_box(st, det.bbox)
            cv2.rectangle(annotated, (dx1, dy1), (dx2, dy2), color, st.thin_box)
            _draw_label(annotated, st, f"{name} {det.confidence:.0%}", dx1, dy1,
                        bg=color, font=st.small_font, above=True)

        # Violation labels: stacked under the box if they fit in the frame,
        # otherwise stacked upward from the box's bottom edge (inside the box)
        texts = [f"! {v.type} ({v.confidence:.0%})" for v in vehicle.violations]
        gap = 2
        heights = []
        for t in texts:
            _, th, base = _text_size(t, st.font, st.text_thick)
            heights.append(th + base + 2 * st.pad)
        if y2 + sum(h_ + gap for h_ in heights) <= st.h:
            y_cursor = y2
            for t in texts:
                _, _, _, ly2 = _draw_label(annotated, st, t, x1, y_cursor,
                                           bg=COLORS["violation"], above=False)
                y_cursor = ly2 + gap
        else:
            y_cursor = y2
            for t in texts:
                _, ly1, _, _ = _draw_label(annotated, st, t, x1, y_cursor,
                                           bg=COLORS["violation"], above=True)
                y_cursor = ly1 - gap

        # Plate box + text
        if vehicle.plate_bbox:
            px1, py1, px2, py2 = _clip_box(st, vehicle.plate_bbox)
            cv2.rectangle(annotated, (px1, py1), (px2, py2), COLORS["plate"], st.box_thick)
            if vehicle.license_plate:
                _draw_label(annotated, st, f"PLATE: {vehicle.license_plate}", px1, py2,
                            bg=COLORS["plate"], fg=(0, 0, 0), above=False)

    # Scene-level violations (top-left)
    y_cursor = st.pad
    for sv in scene_violations or []:
        _, _, _, ly2 = _draw_label(annotated, st, f"SCENE: {sv.type} ({sv.confidence:.0%})",
                                   st.pad, y_cursor, bg=COLORS["violation"], above=False)
        y_cursor = ly2 + 2

    # Evidence ID & timestamp (top-right)
    if evidence_id:
        text = f"ID: {evidence_id} | {timestamp[:19]}"
        tw, _, _ = _text_size(text, st.small_font, st.text_thick)
        _draw_label(annotated, st, text, st.w - tw - 3 * st.pad, st.pad,
                    bg=(0, 0, 0), font=st.small_font, above=False)

    return annotated
