"""
License Plate OCR Pipeline.

Engine: PaddleOCR primary, EasyOCR fallback.

Post-processing:
  - Strip spaces, uppercase
  - Context-aware character correction (0<->O, 1<->I, etc.)
  - Indian registration plate regex validation

config.py declared OCR_PRIMARY = "easyocr" — the two never agreed, and the
EasyOCR remains available for fallback reads and direct text-region scans.
"""

import logging
import re
from typing import Optional, Tuple

import cv2
import numpy as np

from config import (
    OCR_PRIMARY,
    OCR_FALLBACK,
    OCR_CONFIDENCE_THRESHOLD,
    PLATE_REGEX,
    CHAR_CORRECTIONS_TO_DIGIT,
    CHAR_CORRECTIONS_TO_LETTER,
    PLATE_PADDING,
)

logger = logging.getLogger(__name__)


class PlateReader:
    """
    OCR pipeline for extracting text from license plate crops.
    Loaded once at startup (singleton pattern).
    """

    def __init__(self):
        self._paddle_ocr = None
        self._paddle_available = False
        self._easy_ocr = None
        self._easy_available = False

    def load(self) -> None:
        """Load the OCR engine. Called once at startup."""
        if OCR_PRIMARY.lower() == "paddleocr" or OCR_FALLBACK.lower() == "paddleocr":
            try:
                from paddleocr import PaddleOCR

                self._paddle_ocr = PaddleOCR(
                    lang="en",
                    device="cpu",
                    enable_mkldnn=False,
                    cpu_threads=4,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                )
                self._paddle_available = True
                logger.info("[OCR] PaddleOCR loaded successfully")
            except Exception as e:
                logger.error(f"[OCR] PaddleOCR failed to load: {e}")

        if OCR_PRIMARY.lower() == "easyocr" or OCR_FALLBACK.lower() == "easyocr":
            try:
                import easyocr
                self._easy_ocr = easyocr.Reader(["en"], gpu=False, verbose=False)
                self._easy_available = True
                logger.info("[OCR] EasyOCR loaded successfully")
            except Exception as e:
                logger.error(f"[OCR] EasyOCR failed to load: {e}")

    @property
    def is_loaded(self) -> bool:
        return self._paddle_available or self._easy_available

    # ── Plate Image Preprocessing ────────────────────────────────────────

    @staticmethod
    def preprocess_plate(plate_img: np.ndarray) -> np.ndarray:
        """
        Preprocess the cropped plate image for better OCR accuracy.
        """
        if plate_img is None or plate_img.size == 0:
            return plate_img

        # Resize if too small
        h, w = plate_img.shape[:2]
        if w < 100:
            scale = 200 / w
            plate_img = cv2.resize(
                plate_img, None, fx=scale, fy=scale,
                interpolation=cv2.INTER_CUBIC,
            )

        # Convert to grayscale
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)

        # Denoise
        gray = cv2.bilateralFilter(gray, 11, 17, 17)

        # Adaptive threshold
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2,
        )

        # Slight dilation to connect broken characters
        kernel = np.ones((1, 1), np.uint8)
        binary = cv2.dilate(binary, kernel, iterations=1)

        return binary

    # ── OCR Engine ───────────────────────────────────────────────────────

    @staticmethod
    def _flatten_paddle_lines(results) -> list[Tuple[str, float]]:
        """Normalize PaddleOCR 2.x/3.x outputs into (text, confidence) pairs."""
        lines: list[Tuple[str, float]] = []

        def visit(item):
            if item is None:
                return
            if isinstance(item, dict):
                texts = item.get("rec_texts") or item.get("texts") or []
                scores = item.get("rec_scores") or item.get("scores") or []
                for text, score in zip(texts, scores):
                    lines.append((str(text), float(score)))
                return
            if isinstance(item, (list, tuple)):
                if len(item) >= 2 and isinstance(item[1], (list, tuple)) and len(item[1]) >= 2:
                    text, score = item[1][0], item[1][1]
                    if isinstance(text, str):
                        lines.append((text, float(score)))
                        return
                for child in item:
                    visit(child)

        visit(results)
        return lines

    def _paddle_read(self, plate_img: np.ndarray) -> Tuple[str, float]:
        """Run PaddleOCR on plate image."""
        try:
            results = self._paddle_ocr.predict(plate_img)
            lines = self._flatten_paddle_lines(results)
            if not lines:
                return "", 0.0

            combined = "".join(text for text, _ in lines)
            avg_conf = sum(conf for _, conf in lines) / len(lines)
            return combined, avg_conf
        except Exception as e:
            logger.warning(f"[OCR] PaddleOCR error: {e}")
            return "", 0.0

    def _easy_read(self, plate_img: np.ndarray) -> Tuple[str, float]:
        """Run EasyOCR on plate image."""
        try:
            results = self._easy_ocr.readtext(plate_img)
            if not results:
                return "", 0.0

            texts = []
            confs = []
            for (_, text, conf) in results:
                texts.append(text)
                confs.append(conf)

            combined = "".join(texts)
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            return combined, avg_conf
        except Exception as e:
            logger.warning(f"[OCR] EasyOCR error: {e}")
            return "", 0.0

    # ── Post-Processing ──────────────────────────────────────────────────

    @staticmethod
    def clean_plate_text(raw_text: str) -> str:
        """
        Clean raw OCR output:
        - Strip spaces
        - Uppercase
        - Remove non-alphanumeric characters
        """
        text = raw_text.replace(" ", "").upper()
        text = re.sub(r"[^A-Z0-9]", "", text)
        return text

    @staticmethod
    def correct_characters(text: str) -> str:
        """
        Context-aware character correction for Indian plates.

        Indian plate format: SS DD SS DDDD
        (S = state letter, D = digit, S = series letter, D = number)

        Example: UP65AB1234
        Positions: [0,1] = letters, [2,3] = digits, [4,5] = letters, [6-9] = digits
        """
        if len(text) < 9:
            return text  # too short to apply positional correction

        corrected = list(text)

        # Positions 0,1: should be letters (state code)
        for i in [0, 1]:
            if i < len(corrected) and corrected[i] in CHAR_CORRECTIONS_TO_LETTER:
                corrected[i] = CHAR_CORRECTIONS_TO_LETTER[corrected[i]]

        # Positions 2,3: should be digits (district code)
        for i in [2, 3]:
            if i < len(corrected) and corrected[i] in CHAR_CORRECTIONS_TO_DIGIT:
                corrected[i] = CHAR_CORRECTIONS_TO_DIGIT[corrected[i]]

        # Positions 4,5 (or just 4): should be letters (series)
        letter_end = 5 if len(corrected) >= 10 else 4
        for i in range(4, min(letter_end + 1, len(corrected))):
            if corrected[i] in CHAR_CORRECTIONS_TO_LETTER:
                corrected[i] = CHAR_CORRECTIONS_TO_LETTER[corrected[i]]

        # Remaining positions: should be digits
        for i in range(letter_end + 1, len(corrected)):
            if corrected[i] in CHAR_CORRECTIONS_TO_DIGIT:
                corrected[i] = CHAR_CORRECTIONS_TO_DIGIT[corrected[i]]

        return "".join(corrected)

    @staticmethod
    def validate_plate(text: str) -> bool:
        """Validate against Indian registration plate regex."""
        return bool(re.match(PLATE_REGEX, text))

    # ── Main Read Method ─────────────────────────────────────────────────

    def read_plate(
        self, plate_img: np.ndarray,
    ) -> Tuple[Optional[str], float]:
        """
        Full OCR pipeline:
        1. Preprocess plate crop
        2. EasyOCR
        3. Clean, correct, validate

        Returns:
            (plate_text or None, confidence)
        """
        if plate_img is None or plate_img.size == 0:
            return None, 0.0

        if not self.is_loaded:
            logger.error("[OCR] EasyOCR not loaded — cannot read plate")
            return None, 0.0

        # Color crop works better with EasyOCR than the binarized version
        readers = []
        for engine in [OCR_PRIMARY.lower(), OCR_FALLBACK.lower()]:
            if engine == "paddleocr" and self._paddle_available:
                readers.append(("PaddleOCR", self._paddle_read))
            elif engine == "easyocr" and self._easy_available:
                readers.append(("EasyOCR", self._easy_read))

        text, conf = "", 0.0
        for engine_name, reader in readers:
            text, conf = reader(plate_img)
            logger.debug(f"[OCR] {engine_name} raw: '{text}' (conf: {conf:.2f})")
            if text and conf >= OCR_CONFIDENCE_THRESHOLD:
                break

        if conf < OCR_CONFIDENCE_THRESHOLD:
            # Retry once on the preprocessed (denoised/thresholded) crop —
            # sometimes recovers a read the raw color crop missed.
            processed = self.preprocess_plate(plate_img)
            for engine_name, reader in readers:
                retry_text, retry_conf = reader(processed)
                logger.debug(
                    f"[OCR] {engine_name} retry (preprocessed): '{retry_text}' "
                    f"(conf: {retry_conf:.2f})"
                )
                if retry_text and retry_conf > conf:
                    text, conf = retry_text, retry_conf

        if not text:
            return None, 0.0

        # Post-process
        cleaned = self.clean_plate_text(text)
        corrected = self.correct_characters(cleaned)

        # Validate
        if self.validate_plate(corrected):
            logger.info(f"[OCR] Valid plate: {corrected} (conf: {conf:.2f})")
            return corrected, conf
        else:
            # Return raw cleaned text even if not valid pattern
            # (might still be useful for partial reads)
            logger.info(
                f"[OCR] Plate '{corrected}' does not match Indian format, "
                f"returning as-is (conf: {conf:.2f})"
            )
            return corrected if len(corrected) >= 4 else None, conf

    def crop_and_read(
        self,
        image: np.ndarray,
        x1: int, y1: int, x2: int, y2: int,
        pad: int = PLATE_PADDING,
    ) -> Tuple[Optional[str], float]:
        """
        Crop plate region from image and run OCR.
        """
        h, w = image.shape[:2]
        cx1 = max(0, x1 - pad)
        cy1 = max(0, y1 - pad)
        cx2 = min(w, x2 + pad)
        cy2 = min(h, y2 + pad)

        plate_crop = image[cy1:cy2, cx1:cx2]
        return self.read_plate(plate_crop)

    def direct_ocr_scan(
        self,
        vehicle_crop: np.ndarray,
    ) -> Tuple[Optional[str], float, Optional[Tuple[int, int, int, int]]]:
        """
        Scan a vehicle crop directly with EasyOCR to find plate text.
        
        This bypasses the YOLO plate detection model entirely.
        EasyOCR's readtext() returns bounding boxes of detected text regions,
        so we validate each against the Indian plate regex.
        
        Returns:
            (plate_text or None, confidence, (x1, y1, x2, y2) or None)
        """
        if not self._easy_available or vehicle_crop is None or vehicle_crop.size == 0:
            return None, 0.0, None

        try:
            # Focus on the lower 2/3 of the crop where plates usually are
            h, w = vehicle_crop.shape[:2]
            plate_region = vehicle_crop[h // 3:, :]

            results = self._easy_ocr.readtext(plate_region)
            if not results:
                # Retry on full crop
                results = self._easy_ocr.readtext(vehicle_crop)
                plate_region = vehicle_crop  # reset offset

            if not results:
                return None, 0.0, None

            # Check each detected text region for plate-like content
            best_plate = None
            best_conf = 0.0
            best_bbox = None

            for (bbox_pts, text, conf) in results:
                cleaned = self.clean_plate_text(text)
                if len(cleaned) < 4:
                    continue

                corrected = self.correct_characters(cleaned)

                # Reject obvious non-plates: must have at least 2 letters and 2 digits
                letters = sum(1 for c in corrected if c.isalpha())
                digits = sum(1 for c in corrected if c.isdigit())
                
                if letters < 2 or digits < 2:
                    continue

                # Score: prefer valid Indian plates, then longer alphanumeric strings
                is_valid = self.validate_plate(corrected)
                
                # If not strictly valid but has the right mix, accept with lower score
                score = conf * (2.0 if is_valid else 1.0) * (len(corrected) / 10.0)

                if score > best_conf:
                    best_plate = corrected
                    best_conf = conf
                    # Convert EasyOCR bbox points to x1,y1,x2,y2
                    xs = [p[0] for p in bbox_pts]
                    ys = [p[1] for p in bbox_pts]
                    # Offset if we used the lower region
                    y_offset = h // 3 if plate_region is not vehicle_crop else 0
                    best_bbox = (
                        int(min(xs)),
                        int(min(ys)) + y_offset,
                        int(max(xs)),
                        int(max(ys)) + y_offset,
                    )

            if best_plate:
                logger.info(f"[OCR] Direct scan found plate: {best_plate} (conf: {best_conf:.2f})")
                return best_plate, best_conf, best_bbox

        except Exception as e:
            logger.warning(f"[OCR] Direct scan error: {e}")

        return None, 0.0, None
