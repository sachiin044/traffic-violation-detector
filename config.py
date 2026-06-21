"""
Centralized configuration for the Traffic Violation Detection System.
All model paths, thresholds, and settings in one place.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# ── Project Root ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
INFERENCE_OUTPUTS_DIR = PROJECT_ROOT / "inference_outputs"
INFERENCE_OUTPUTS_DIR.mkdir(exist_ok=True)
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "violations.db"

# ── Model Weight Paths ──────────────────────────────────────────────────────
# All models use custom-trained weights under OUTPUTS_DIR.
# Vehicle detector: YOLO11n retrained on Indian Driving Dataset
#   (mAP50=0.881, precision=0.851, recall=0.803)
#   Classes: {0: motorcycle, 1: car, 2: heavy_vehicle, 3: autorickshaw}
MODEL_WEIGHTS = {
    "vehicle":         OUTPUTS_DIR / "vehicle"         / "weights" / "best.pt",
    "helmet":          OUTPUTS_DIR / "helmet"          / "weights" / "best.pt",
    "seatbelt":        OUTPUTS_DIR / "seatbelt"        / "weights" / "best.pt",
    "triple_riding":   OUTPUTS_DIR / "triple_riding"   / "weights" / "best.pt",
    "traffic_signal":  OUTPUTS_DIR / "traffic_signal"  / "weights" / "best.pt",
    "illegal_parking": OUTPUTS_DIR / "illegal_parking" / "weights" / "best.pt",
    "plate":           OUTPUTS_DIR / "plate"           / "weights" / "best.pt",
}

# ── Detection Confidence Thresholds ──────────────────────────────────────
# Tuned per actual validation metrics in training_summary.md / training_summary.json.
#   vehicle  (mAP50=0.881)          -> custom model, slightly tighter than default
#   plate    (mAP50=0.995)          -> can afford a tight threshold
#   helmet   (mAP50=0.799, recall .76)-> kept looser to not miss violations
#   seatbelt (mAP50=0.967)          -> reliable, mid threshold is fine
#   traffic_signal (mAP50=0.856)    -> moderate, some false positive risk
#   triple_riding  (mAP50=0.871)    -> moderate
#   illegal_parking (mAP50=0.941)   -> reliable
CONFIDENCE_THRESHOLDS = {
    "vehicle":         0.25,  # Robust COCO vehicle detection
    "helmet":          0.10,  # Lowered to aggressively catch NoHelmet on difficult/filtered images
    "seatbelt":        0.70,  # Raised to stop 60-66% false positives when driver is wearing a seatbelt
    "triple_riding":   0.30,  # Lowered to detect tiny, occluded children with standard YOLO
    "traffic_signal":  0.85,  # Raised VERY high to stop false scene violations
    "illegal_parking": 0.85,  # Raised VERY high to stop false scene violations
    "plate":           0.25,
}

# ── Vehicle Detector: class mapping ──────────────────────────────────────
# Custom YOLO11n trained on Indian Driving Dataset — 4 classes (0-indexed).
# No COCO class filtering needed; the model only detects vehicle types.
VEHICLE_CLASS_MAP = {
    0: "motorcycle",
    1: "car",
    2: "heavy_vehicle",
    3: "autorickshaw",
}

# ── Vehicle type groupings for routing to correct sub-detectors ──────────
# NOTE: autorickshaw is intentionally excluded from sub-detector routing.
# It is still detected as a vehicle and gets plate detection + OCR, but
# no helmet/seatbelt/triple-riding checks are run on autorickshaw crops.
TWO_WHEELER_TYPES = {"motorcycle", "bicycle"}
FOUR_WHEELER_TYPES = {"car", "heavy_vehicle"}

# ── NMS IoU threshold ────────────────────────────────────────────────────────
NMS_IOU_THRESHOLD = 0.45

# ── Crop padding (fraction of bbox to expand when cropping vehicles) ─────────
CROP_PAD_FRACTION = 0.10  # 10% padding around vehicle crop

# ── Image preprocessing ─────────────────────────────────────────────────────
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_SIZE = (8, 8)
DENOISE_STRENGTH = 10

# ── OCR Settings ─────────────────────────────────────────────────────────────
# PaddleOCR primary, EasyOCR fallback.
# OCR_PRIMARY/OCR_FALLBACK both as "easyocr" — a no-op fallback — while
OCR_PRIMARY = "paddleocr"
OCR_FALLBACK = "easyocr"
OCR_CONFIDENCE_THRESHOLD = 0.5  # below this, OCR result is treated as unreliable
PLATE_PADDING = 5               # pixels to expand plate crop
OPENAI_PLATE_MODEL = os.getenv("OPENAI_PLATE_MODEL", "gpt-5.4-mini")
OPENAI_PLATE_TIMEOUT_SECONDS = float(os.getenv("OPENAI_PLATE_TIMEOUT_SECONDS", "12"))

# ── Indian Registration Plate Pattern ────────────────────────────────────────
# e.g. UP65AB1234, DL01CD1234, OD02AK5678
PLATE_REGEX = r"^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$"

# ── Character Correction Map (common OCR errors) ────────────────────────────
# Applied only to digit positions vs letter positions contextually
CHAR_CORRECTIONS_TO_DIGIT = {
    "O": "0", "I": "1", "S": "5", "B": "8",
    "o": "0", "i": "1", "s": "5", "b": "8",
    "Z": "2", "G": "6", "T": "7",
}
CHAR_CORRECTIONS_TO_LETTER = {
    "0": "O", "1": "I", "5": "S", "8": "B",
    "2": "Z", "6": "G", "7": "T",
}

# ── Batch processing ────────────────────────────────────────────────────────
BATCH_MIN_IMAGES = 1
BATCH_MAX_IMAGES = 100

# ── Server ───────────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8000"))
MAX_IMAGE_SIZE_MB = 20

# ── Annotation Colors (BGR for OpenCV) ───────────────────────────────────────
COLORS = {
    "vehicle":    (255, 165, 0),    # orange
    "violation":  (0, 0, 255),      # red
    "plate":      (0, 255, 0),      # green
    "helmet_ok":  (0, 200, 0),      # green
    "seatbelt_ok":(0, 200, 0),      # green
    "text":       (255, 255, 255),  # white
    "background": (40, 40, 40),     # dark gray
}

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
