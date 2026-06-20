# Traffic Violation Detection System

![repo-languages](https://img.shields.io/github/languages/top/sachiin044/traffic-violation-detector?style=flat)
![repo-stars](https://img.shields.io/github/stars/sachiin044/traffic-violation-detector?style=flat)
![last-commit](https://img.shields.io/github/last-commit/sachiin044/traffic-violation-detector?style=flat)

Automated Photo Identification and Classification for Traffic Violations using Computer Vision.

This repository contains a production-oriented pipeline for detecting traffic violations from images (and video) with an emphasis on Indian traffic scenarios: motorcycles, autorickshaws, cars, and heavy vehicles. It combines custom object detectors, rule-based logic, OCR (PaddleOCR), and evidence packaging to produce actionable violation records.

Key highlights

- Modular detectors: vehicle detection, helmet, seatbelt, triple-riding, traffic signal, illegal parking, and license-plate readers.
- Designed for Indian license plate formats and common traffic behaviors.
- End-to-end evidence pipeline: detection → OCR → rule engine → annotated evidence and PDF challans.
- Simple HTTP API (FastAPI) and a frontend dashboard (React + Vite / Streamlit) for inspection.

Table of contents

- Architecture
- Violations Detected
- Quick Start
  - Backend
  - Frontend
- API Endpoints
- Usage Examples
  - Single Image
  - Batch Processing
  - Query Violations
- Response Schema
- Models
- License Plate OCR Pipeline
- Database
- Limitations
- Project Structure
- Contributing
- Acknowledgements & Contact

## Architecture

```
Image
  │
  ▼
Preprocess (CLAHE, denoise, brightness normalization)
  │
  ▼
Vehicle Detector (Custom YOLO11n — Indian Driving Dataset)
  │  Classes: motorcycle, car, heavy_vehicle, autorickshaw
  │
  ├── Motorcycle Crop
  │     ├── Helmet Detector
  │     ├── Triple Riding Detector
  │     └── License Plate Detector → PaddleOCR
  │
  ├── Car/Heavy Vehicle Crop
  │     ├── Seatbelt Detector
  │     └── License Plate Detector → PaddleOCR
  │
  ├── Autorickshaw Crop
  │     └── License Plate Detector → PaddleOCR (no sub-detector routing)
  │
  └── Full Image (Scene-Level)
        ├── Traffic Signal Detector (red-light violation)
        └── Illegal Parking Detector
```

This pipeline is intended to be robust in real-world conditions—images are preprocessed for contrast and noise, high-resolution crops are used for OCR, and a rule engine correlates detections to infer violations.

## Violations Detected

| Violation | Detection Method |
|---|---|
| Helmet Non Compliance | NoHelmet class on motorcycle crop |
| Seatbelt Non Compliance | no-seatbelt class on car/heavy_vehicle crop |
| Triple Riding | rider_region class on motorcycle crop |
| Red Light Violation | red_light + vehicle overlapping stop_line |
| Illegal Parking | illegal_parking class on full image |

## Quick Start

These instructions preserve the original setup commands while adding a few tips for a smoother local run.

Prerequisites

- Python 3.8+ (venv recommended)
- Node.js 16+ / npm for the frontend
- (Optional) GPU with CUDA + cuDNN to accelerate inference

### Backend

```bash
# 1. Backend Setup
# Create & activate venv
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
# or
uvicorn app:app --host 0.0.0.0 --port 8000
```

Tips:
- If you have GPU drivers and CUDA, install the GPU-specific packages (torch/cuda wheel) before pip installing the full requirements. Use smaller batch sizes if VRAM is limited.
- For reproducible environments consider using Docker (add Dockerfile to run both backend and frontend behind a reverse proxy).

### Frontend (developer)

Open a second terminal and run:

```bash
cd frontend
npm install

# Start the frontend dev server
npm run dev
```

The frontend communicates with the backend API; update the dev proxy or environment variables if your backend runs on a non-default host/port.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/predict` | Analyze a single traffic image |
| POST | `/predict-batch` | Batch analyze 1-100 images |
| GET | `/health` | Service health check |
| GET | `/models` | Loaded model information |
| GET | `/violations` | Query stored violations (with filters) |
| GET | `/stats` | Violation statistics & analytics |
| GET | `/annotated/{image_id}` | Download annotated evidence image |
| GET | `/docs` | Swagger API documentation |

## Usage

### Single Image
```bash
curl -X POST -F "file=@traffic_image.jpg" http://localhost:8000/predict
```

### Batch Processing
```bash
curl -X POST \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "files=@image3.jpg" \
  http://localhost:8000/predict-batch
```

### Query Violations
```bash
# All violations
curl http://localhost:8000/violations

# Filter by plate number
curl "http://localhost:8000/violations?plate_number=UP65"

# Filter by type
curl "http://localhost:8000/violations?violation_type=Helmet%20Non%20Compliance"
```

## Response Schema

```json
{
  "image_id": "a1b2c3d4e5f6",
  "timestamp": "2026-06-19T12:00:00Z",
  "processing_time_ms": 1250.5,
  "total_vehicles": 3,
  "total_violations": 2,
  "vehicles": [
    {
      "vehicle_id": 0,
      "vehicle_type": "motorcycle",
      "bbox": {"x1": 100, "y1": 200, "x2": 400, "y2": 500},
      "license_plate": "UP65AB1234",
      "plate_confidence": 0.92,
      "violations": [
        {"type": "Helmet Non Compliance", "confidence": 0.94},
        {"type": "Triple Riding", "confidence": 0.91}
      ]
    }
  ],
  "scene_violations": [],
  "annotated_image_path": "inference_outputs/a1b2c3d4e5f6_annotated.jpg"
}
```

## Models

| Model | mAP@50 | Classes |
|---|---|---|
| License Plate | 99.5% | license_plate |
| Seatbelt | 96.7% | seatbelt, no-seatbelt |
| Illegal Parking | 94.1% | illegal_parking |
| Vehicle (Custom YOLO11n) | 88.1% | motorcycle, car, heavy_vehicle, autorickshaw |
| Triple Riding | 87.1% | motorcycle, person, rider_region |
| Traffic Signal | 85.6% | car, green_light, motobike, red_light, stop_line, yellow_light |
| Helmet | 79.9% | Helmet, Motorbike, NoHelmet, PNumber |

Notes:
- mAP metrics are measured on internal validation sets. Use the `models` endpoint to confirm which weights are currently loaded in the running server.

## License Plate OCR Pipeline

- **Detection**: YOLO license-plate model locates plate boxes on vehicle crops and the full frame.
- **Crop**: Plate regions are read from the original high-resolution image for OCR quality.
- **Engine**: PaddleOCR is the primary OCR engine for plate text extraction.
- **Recovery path**: If the plate box is missed, the pipeline scans likely text regions and attaches a visible plate to the matching vehicle.
- **Post-processing**: Strip spaces, uppercase, character correction (O↔0, I↔1, S↔5, B↔8)
- **Validation**: Indian plate regex `^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$`

## Database

MongoDB Atlas stores all detected violations with:
- Timestamp, image ID, plate number, vehicle type
- Violation type, confidence, bounding box
- Evidence packages with annotated images

## Limitations

- **Red Light Detection**: Single-image analysis uses spatial overlap (vehicle bbox vs stop_line). Multi-frame tracking recommended for production.
- **OCR Accuracy**: Depends on plate visibility, angle, and image quality. Works best with clear, front-facing plates.
- **GPU**: Optimized for RTX 3050 4GB. Larger batch sizes may require more VRAM.

## Project Structure

```
├── app.py                  # FastAPI entry point
├── config.py               # Centralized configuration
├── dashboard.py            # Streamlit dashboard
├── requirements.txt        # Dependencies
├── detectors/              # YOLO detector wrappers
│   ├── base.py             # Base detector class
│   ├── vehicle.py          # Vehicle (Custom YOLO11n)
│   ├── helmet.py           # Helmet compliance
│   ├── seatbelt.py         # Seatbelt compliance
│   ├── triple_riding.py    # Triple riding
│   ├── traffic_signal.py   # Traffic signals
│   ├── illegal_parking.py  # Illegal parking
│   └── plate.py            # License plates
├── engine/
│   ├── rules.py            # Violation rule engine
│   ├── temporal_rules.py   # Temporal rules (video)
│   └── challan.py          # Challan generation (PDF)
├── ocr/
│   └── plate_reader.py     # PaddleOCR plate reading pipeline
├── services/
│   ├── pipeline.py         # Unified inference orchestrator
│   ├── video_pipeline.py   # Video processing pipeline
│   └── evidence.py         # Evidence package manager
├── routers/
│   ├── predict.py          # Inference API endpoints
│   └── challan.py          # Challan management API
├── database/
│   └── mongo.py            # MongoDB driver & CRUD
├── utils/
│   ├── schemas.py          # Pydantic response models
│   ├── preprocess.py       # Image preprocessing
│   └── annotate.py         # Evidence annotation
├── outputs/                # Trained model weights
│   ├── vehicle/weights/    # Custom YOLO11n vehicle detector
│   ├── helmet/weights/     # Helmet detector
│   ├── seatbelt/weights/   # Seatbelt detector
│   └── ...                 # Other model weights
└── inference_outputs/      # Annotated evidence images
```

## Contributing

Contributions are welcome — whether it's improving detection accuracy, adding new rules, or hardening the production deployment.

Recommended workflow

1. Fork the repo
2. Create a branch: `git checkout -b feat/your-change`
3. Run tests and format code
4. Submit a PR with a clear description and screenshots of improvements (if applicable)

Please open issues for feature requests or bugs so they can be triaged before large PRs.

## Acknowledgements & Contact

- Built with OpenCV, PyTorch, PaddleOCR, FastAPI, and Streamlit/React for the dashboard.
- If you have questions or want to collaborate, open an issue or contact the maintainer: @sachiin044

---

(Original README content preserved in full above — architecture diagram, API, usage examples, response schema, models, OCR pipeline, limitations, and project structure.)
