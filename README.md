# Traffic Violation Detection System

![repo-languages](https://img.shields.io/github/languages/top/sachiin044/traffic-violation-detector?style=flat)
![repo-stars](https://img.shields.io/github/stars/sachiin044/traffic-violation-detector?style=flat)
![last-commit](https://img.shields.io/github/last-commit/sachiin044/traffic-violation-detector?style=flat)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?style=flat&logo=fastapi)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react)

Automated detection and enforcement of traffic violations using computer vision, custom YOLO models, and an end-to-end e-challan pipeline — designed for Indian road conditions.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Violations Detected](#violations-detected)
- [ML Models](#ml-models)
- [License Plate OCR Pipeline](#license-plate-ocr-pipeline)
- [e-Challan Engine](#e-challan-engine)
- [API Reference](#api-reference)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Database](#database)
- [Docker](#docker)
- [Limitations](#limitations)
- [Contributing](#contributing)

---

## Overview

This system processes traffic images and videos to detect violations, extract license plates via OCR, and automatically generate PDF e-challans. It is built around a **vehicle-first crop-based routing** strategy: a primary vehicle detector localises each vehicle, then dedicated sub-detectors run on the cropped region only — greatly reducing false positives.

**Key highlights:**
- 7 custom YOLO11n models trained on Indian driving datasets
- Dual OCR (PaddleOCR primary, EasyOCR fallback) with OpenAI Vision as optional high-accuracy path
- Rule engine maps raw detections → typed violations with confidence gating
- e-Challan PDF generation with QR codes, MV Act sections, and RTO registration lookup
- Async video pipeline with temporal tracking for red-light and repeat-offence detection
- FastAPI backend + React 19 / Vite dashboard

---

## Architecture

### Inference Pipeline (Image)

```
Input Image
    │
    ▼
┌─────────────────────────────────┐
│   Preprocess                    │
│   CLAHE · Denoise · Normalize   │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   Vehicle Detector (YOLO11n)    │
│   Full image scan               │
│   Classes: motorcycle · car     │
│            heavy_vehicle        │
│            autorickshaw         │
└──────────┬──────────────────────┘
           │
     ┌─────┴──────────────────────────┐
     │  Per-vehicle crop (+padding)   │
     └──┬────────────┬────────────────┘
        │            │
  ┌─────▼──────┐  ┌──▼──────────────┐
  │ 2-Wheeler  │  │ 4-Wheeler       │
  │ motorcycle │  │ car / heavy_veh │
  │ bicycle    │  └──────┬──────────┘
  └─────┬──────┘         │
        │           ┌────▼──────────┐
   ┌────▼──────┐    │ Seatbelt Det. │
   │ Helmet    │    └────┬──────────┘
   │ Detector  │         │
   └────┬──────┘    ┌────▼──────────┐
   ┌────▼──────┐    │ Plate Det.    │
   │ Triple    │    │ → OCR         │
   │ Riding    │    └───────────────┘
   │ Detector  │
   └────┬──────┘
   ┌────▼──────┐
   │ Plate Det.│
   │ → OCR     │
   └───────────┘

  Full Image (scene-level, only when vehicles present)
  ├── Traffic Signal Detector → Red Light check
  └── Illegal Parking Detector
               │
               ▼
┌─────────────────────────────────┐
│   Violation Rule Engine         │
│   Stateless · Confidence-gated  │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   Evidence Manager              │
│   Annotated image · JSON report │
│   Thumbnail · ZIP package       │
└──────────────┬──────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
  MongoDB Atlas    Challan Engine
  (evidence +      PDF e-challan
   challans)       QR code · RTO
```

### Video Pipeline

```
Uploaded Video
    │
    ▼
Background Thread (async)
    │
    ├── Frame extraction (OpenCV)
    ├── InferencePipeline.predict() per frame
    ├── TemporalRuleEngine (track IDs across frames)
    │       ├── Red-light dwell check
    │       └── Repeat-offence aggregation
    └── Evidence + Challan per unique violation
```

### Application Layers

```
┌──────────────────────────────────────────────┐
│  React 19 + Vite Frontend  (port 5173)       │
│  Tailwind CSS · Recharts · React Router      │
└───────────────────┬──────────────────────────┘
                    │ HTTP / REST
┌───────────────────▼──────────────────────────┐
│  FastAPI Backend  (port 8000)                │
│  ├── POST /predict          (image)          │
│  ├── POST /predict-batch    (batch)          │
│  ├── POST /video/predict    (video async)    │
│  ├── GET  /video/status/:id                  │
│  ├── GET  /dashboard/summary                 │
│  ├── GET  /analytics/hotspots                │
│  ├── GET  /analytics/trends                  │
│  ├── GET  /evidence/:id                      │
│  ├── GET  /evidence/:id/download             │
│  ├── GET  /challan/:id/pdf                   │
│  └── GET  /health · /models · /search        │
└───────┬────────────────────┬─────────────────┘
        │                    │
   MongoDB Atlas        Local Filesystem
   (violations,         /evidence/
    challans,           /inference_outputs/
    video tasks)        /inference_outputs/challans/
```

---

## Project Structure

```
traffic-violation-detector/
│
├── app.py                      # FastAPI entry point, lifespan, CORS, routers
├── config.py                   # All constants: model paths, thresholds, colors, OCR
├── dashboard.py                # Standalone Streamlit dashboard (alternative UI)
├── requirements.txt
├── Dockerfile                  # Python 3.10-slim; ffmpeg + OpenCV deps
├── .env                        # Secrets (MONGODB_URI, OPENAI_API_KEY, …)
│
├── detectors/                  # YOLO detector wrappers (all extend BaseDetector)
│   ├── base.py                 # BaseDetector: load(), detect(), confidence threshold
│   ├── vehicle.py              # Ensemble or custom YOLO11n — 4 Indian vehicle classes
│   ├── helmet.py               # Helmet / NoHelmet / PNumber / Motorbike
│   ├── seatbelt.py             # seatbelt / no-seatbelt
│   ├── triple_riding.py        # motorcycle / person / rider_region
│   ├── traffic_signal.py       # red_light / green_light / yellow_light / stop_line
│   ├── illegal_parking.py      # illegal_parking class
│   └── plate.py                # license_plate class + best-plate selector
│
├── engine/                     # Business logic (stateless)
│   ├── rules.py                # ViolationRuleEngine: check_helmet, check_seatbelt,
│   │                           #   check_triple_riding, check_red_light,
│   │                           #   check_illegal_parking, _bbox_iou
│   ├── temporal_rules.py       # TemporalRuleEngine for video frame sequences
│   └── challan.py              # ChallanManager: PDF generation (ReportLab + QR),
│                               #   RTO lookup, fines.json, auto threshold
│
├── ocr/
│   ├── plate_reader.py         # PaddleOCR primary + EasyOCR fallback
│   │                           #   crop_and_read, direct_ocr_scan,
│   │                           #   char correction, Indian regex validation
│   └── openai_plate_reader.py  # GPT Vision fallback when OPENAI_API_KEY set
│
├── services/
│   ├── pipeline.py             # InferencePipeline singleton (orchestrates all above)
│   ├── video_pipeline.py       # VideoInferencePipeline (background thread)
│   └── evidence.py             # EvidenceManager: annotated jpg, thumbnail, ZIP, JSON
│
├── routers/
│   ├── predict.py              # All inference + analytics + evidence endpoints
│   └── challan.py              # Challan CRUD, PDF download, status update
│
├── database/
│   ├── mongo.py                # MongoDB driver: insert/search evidence & challans,
│   │                           #   video tasks, dashboard aggregations
│   └── seed_cameras.py         # Seed script for camera location data
│
├── utils/
│   ├── schemas.py              # Pydantic models: Detection, BBox, Violation,
│   │                           #   VehicleResult, PredictionResponse, HealthResponse
│   ├── preprocess.py           # CLAHE, denoise, brightness norm, crop_region
│   ├── annotate.py             # OpenCV annotation: bboxes, labels, legend overlay
│   └── rto.py                  # Indian RTO code → city/state lookup
│
├── config/
│   ├── fines.json              # Violation → fine amount + MV Act section mapping
│   └── rto_codes.json          # State/district RTO code database
│
├── outputs/                    # Trained model weights (not in git LFS by default)
│   ├── vehicle/weights/best.pt
│   ├── helmet/weights/best.pt
│   ├── seatbelt/weights/best.pt
│   ├── triple_riding/weights/best.pt
│   ├── traffic_signal/weights/best.pt
│   ├── illegal_parking/weights/best.pt
│   └── plate/weights/best.pt
│
├── frontend/                   # React 19 + Vite dashboard
│   ├── package.json            # React, React Router, Recharts, Axios, Tailwind
│   └── src/
│       └── ...                 # Pages: Dashboard, Evidence, Challans, Analytics
│
├── evidence/                   # Runtime: per-evidence packages (original, annotated,
│                               #           thumbnail, report.json, ZIP)
├── inference_outputs/          # Runtime: annotated jpegs + challans/CH-*.pdf
├── test_images/                # 29 labelled test images (helmet, seatbelt, plates…)
└── test_videos/                # Sample Indian road footage for video pipeline tests
```

---

## Violations Detected

| Violation | Detection Method | Rule Logic |
|---|---|---|
| **Helmet Non Compliance** | `NoHelmet` class on motorcycle crop | Any `NoHelmet` detection → violation per rider |
| **Seatbelt Non Compliance** | `no-seatbelt` class on car/heavy_vehicle crop | Direct model output above confidence threshold |
| **Triple Riding** | `rider_region` + `person` count on motorcycle crop | ≥ 3 persons or rider_region detection |
| **Red Light Violation** | `red_light` + vehicle bbox overlaps `stop_line` | Spatial IoU check; temporal dwell in video mode |
| **Illegal Parking** | `illegal_parking` class on full frame | Above 0.85 confidence threshold |

---

## ML Models

All models are YOLO11n fine-tuned on custom Indian traffic datasets.

| Model | mAP@50 | Confidence Threshold | Classes |
|---|---|---|---|
| License Plate | 99.5% | 0.25 | `license_plate` |
| Seatbelt | 96.7% | 0.70 | `seatbelt`, `no-seatbelt` |
| Illegal Parking | 94.1% | 0.85 | `illegal_parking` |
| Vehicle | 88.1% | 0.25 | `motorcycle`, `car`, `heavy_vehicle`, `autorickshaw` |
| Triple Riding | 87.1% | 0.30 | `motorcycle`, `person`, `rider_region` |
| Traffic Signal | 85.6% | 0.85 | `car`, `green_light`, `motobike`, `red_light`, `stop_line`, `yellow_light` |
| Helmet | 79.9% | 0.10 | `Helmet`, `Motorbike`, `NoHelmet`, `PNumber` |

> **Note on thresholds:** Helmet is intentionally loose (0.10) to maximise recall on difficult crops. Scene-level models (illegal parking, traffic signal) use very high thresholds (0.85) to prevent phantom violations.

**Vehicle detector modes** (set via `VEHICLE_MODEL` in `.env`):

| Mode | Behaviour |
|---|---|
| `ensemble` *(default)* | COCO `yolo11n.pt` + custom model — broadest coverage including autorickshaws |
| `custom` | Custom model only |
| `coco` | Stock COCO model only (no autorickshaw class) |

---

## License Plate OCR Pipeline

```
Vehicle crop (original resolution)
    │
    ▼
YOLO Plate Detector  ──fallback 1──▶  Wider crop (30% pad)
    │                ──fallback 2──▶  Full-frame plate detections
    │                ──fallback 3──▶  Direct OCR scan on vehicle crop
    │                ──fallback 4──▶  Full-frame OCR result
    ▼
Plate region crop (from original high-res image)
    │
    ▼
PaddleOCR (primary)  ──if unavailable──▶  EasyOCR
    │
    ▼
Post-processing
    ├── Strip spaces, uppercase
    ├── Positional character correction
    │       digit positions: O→0  I→1  S→5  B→8  Z→2  G→6  T→7
    │       letter positions: 0→O  1→I  5→S  8→B
    └── Regex validation: ^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$
```

Optional **OpenAI Vision** path (enabled when `OPENAI_API_KEY` is set): bypasses the YOLO plate model entirely and sends the vehicle crop to GPT Vision for plate extraction — higher accuracy on difficult angles.

---

## e-Challan Engine

Auto-challan is triggered after every evidence record with a readable plate:

```
Detection confidence
    ≥ 85%  →  Status: GENERATED     (auto-approved, ready to issue)
    ≥ 70%  →  Status: REVIEW_REQUIRED (queued for officer review)
    < 70%  →  No challan issued
```

Each PDF challan includes:
- Challan number, date/time, place of offence, evidence ID
- Vehicle registration box, vehicle class, registering RTO (from `rto_codes.json`)
- Offence table with **Motor Vehicles Act section**, penalty amount, AI confidence
- Photographic evidence (original + annotated side-by-side)
- Payment/contest instructions with deadline date
- QR code linking to `CHALLAN_VERIFY_URL/verify/challan/<id>`
- "DEMO — NOT AN OFFICIAL CHALLAN" watermark

---

## API Reference

### Inference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/predict` | Analyse a single image (up to 20 MB) |
| `POST` | `/predict-batch` | Batch analyse 1–100 images |
| `POST` | `/video/predict` | Submit a video for async processing |
| `GET` | `/video/status/{task_id}` | Poll async video job status |
| `GET` | `/video/result/{task_id}` | Fetch completed video results |

### Evidence & Challans

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/evidence/{id}` | Full evidence record (merged from MongoDB + JSON) |
| `GET` | `/evidence/{id}/download` | Download evidence ZIP package |
| `GET` | `/challan/{id}/pdf` | Download challan PDF |
| `PUT` | `/challan/{id}/status` | Update challan status (ISSUED / PAID / DISPUTED) |

### Dashboard & Analytics

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/dashboard/summary` | Aggregated stats (totals, recent activity) |
| `GET` | `/dashboard/top-plates` | Most-frequent offending plates |
| `GET` | `/analytics/hotspots` | Violations grouped by camera location |
| `GET` | `/analytics/trends` | Daily violation trend data |
| `GET` | `/search` | Filtered evidence search (plate, type, date, confidence) |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health, GPU info, uptime, models loaded |
| `GET` | `/models` | Loaded model weights, class names, thresholds |
| `GET` | `/docs` | Swagger / OpenAPI UI |

### Response Schema (single image)

```json
{
  "image_id": "a1b2c3d4e5f6",
  "evidence_id": "TVD-20260619-ABCD12",
  "timestamp": "2026-06-19T12:00:00Z",
  "processing_time_ms": 1250.5,
  "image_width": 1920,
  "image_height": 1080,
  "total_vehicles": 2,
  "total_violations": 2,
  "vehicles": [
    {
      "vehicle_id": 0,
      "vehicle_type": "motorcycle",
      "bbox": {"x1": 100, "y1": 200, "x2": 400, "y2": 500},
      "license_plate": "UP65AB1234",
      "plate_confidence": 0.92,
      "plate_bbox": {"x1": 180, "y1": 460, "x2": 340, "y2": 495},
      "violations": [
        {"type": "Helmet Non Compliance", "confidence": 0.94, "details": "No helmet detected (conf: 0.94)"},
        {"type": "Triple Riding", "confidence": 0.91, "details": "3 riders detected"}
      ],
      "all_detections": [...]
    }
  ],
  "scene_violations": [],
  "annotated_image_path": "/evidence/TVD-20260619-ABCD12/annotated.jpg"
}
```

---

## Quick Start

### Prerequisites

- Python 3.10+ (venv recommended)
- Node.js 18+ / npm (for the React frontend)
- MongoDB Atlas URI (or local MongoDB) — set in `.env`
- GPU with CUDA + cuDNN (optional but recommended for real-time use)

### Backend

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate        # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (copy and edit)
cp .env.example .env
# Set MONGODB_URI, OPENAI_API_KEY (optional), CHALLAN_AUTHORITY, etc.

# 4. Start the server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
# API docs at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard at http://localhost:5173
```

### Usage Examples

**Single image:**
```bash
curl -X POST -F "file=@traffic_image.jpg" http://localhost:8000/predict
```

**Batch (multiple images):**
```bash
curl -X POST \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  http://localhost:8000/predict-batch
```

**Video (async):**
```bash
# Submit
curl -X POST -F "file=@road_footage.mp4" "http://localhost:8000/video/predict?camera_id=CAM_001"
# → { "task_id": "task_abc123", "status": "processing_started" }

# Poll
curl http://localhost:8000/video/status/task_abc123
```

**Search violations:**
```bash
# By plate prefix
curl "http://localhost:8000/search?plate_number=UP65"

# By violation type, date range, minimum confidence
curl "http://localhost:8000/search?violation_type=Helmet%20Non%20Compliance&date_from=2026-01-01&min_confidence=0.85"
```

---

## Configuration

All settings live in `config.py` and can be overridden via `.env`:

| Variable | Default | Description |
|---|---|---|
| `MONGODB_URI` | — | MongoDB Atlas connection string |
| `OPENAI_API_KEY` | — | Enables GPT Vision plate reader |
| `OPENAI_PLATE_MODEL` | `gpt-5.4-mini` | Model for plate OCR |
| `VEHICLE_MODEL` | `ensemble` | `ensemble` / `custom` / `coco` |
| `TRIPLE_RIDING_MODEL` | `custom` | `custom` / `coco` |
| `PORT` | `8000` | Backend port |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `CHALLAN_AUTHORITY` | `Traffic Enforcement Unit` | PDF challan header |
| `CHALLAN_CITY` | `Bhubaneswar` | Default offence location |
| `CHALLAN_PAYMENT_DAYS` | `60` | Payment deadline window |
| `CHALLAN_VERIFY_URL` | `http://localhost:5173` | QR code base URL |

---

## Database

**MongoDB Atlas** stores all operational data in two main collections:

**`evidence`** — one document per analysed image/video frame with violations:
- `evidence_id`, `timestamp`, `camera_id`, `location`
- `vehicles[]` — per-vehicle detections, plate, violations, bounding boxes
- `annotated_path`, `image_path`, `thumbnail_path`

**`challans`** — one document per auto-generated e-challan:
- `challan_id` (format: `CH-YYYYMMDD-XXXXXX`), `evidence_id`, `plate_number`
- `violation_type`, `fine_amount`, `status`, `offences[]`
- `pdf_path`, `registered_at`, `location`, `camera_id`

**`video_tasks`** — async video job tracking:
- `task_id`, `status` (`processing` / `completed` / `failed`)
- `violations_found`, `violation_details`, `processed_video_path`

---

## Docker

```bash
# Build
docker build -t traffic-violation-detector .

# Run (set your MONGODB_URI in env)
docker run -p 8000:7860 \
  -e MONGODB_URI="mongodb+srv://..." \
  -e OPENAI_API_KEY="sk-..." \
  traffic-violation-detector
```

The image is based on `python:3.10-slim` with `ffmpeg`, `libgl1`, and `libglib2.0` for OpenCV and video support. Exposed on port 7860 (Hugging Face Spaces compatible).

---

## Limitations

| Area | Current Limitation | Recommended Improvement |
|---|---|---|
| **Red Light** | Single-image uses spatial overlap heuristic | Multi-frame tracking with vehicle ID persistence |
| **OCR Accuracy** | Sensitive to plate angle, blur, and lighting | Higher-res training data; super-resolution preprocessing |
| **GPU** | Tuned for RTX 3050 4GB (VRAM constrained) | Dynamic batch sizing; TensorRT export for inference speedup |
| **Owner Lookup** | RTO lookup by code only; no Vahan API integration | Integrate MoRTH Vahan API for real owner data |
| **Autorickshaw** | Plate OCR only — no sub-detector routing | Train dedicated sub-detectors for autorickshaw scenarios |

---

## Contributing

Contributions are welcome — improvements to detection accuracy, new violation types, or production hardening are all valuable.

**Recommended workflow:**
1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-change`
3. Test with images from `test_images/` and videos from `test_videos/`
4. Submit a PR with a clear description; include before/after metrics or screenshots where applicable

Please open an issue before submitting large PRs so the approach can be discussed first.

---

## Acknowledgements & Contact

Built with **PyTorch · Ultralytics YOLO11 · PaddleOCR · EasyOCR · OpenCV · FastAPI · ReportLab · React 19 · Tailwind CSS · Recharts**.

Trained on Indian Driving Dataset (IDD) and custom annotated traffic footage.

Questions or collaboration: open an issue or contact the maintainer [@sachiin044](https://github.com/sachiin044).
