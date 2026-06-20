# Traffic Violation Detection System

Automated Photo Identification and Classification for Traffic Violations using Computer Vision.

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

## Violations Detected

| Violation | Detection Method |
|---|---|
| Helmet Non Compliance | NoHelmet class on motorcycle crop |
| Seatbelt Non Compliance | no-seatbelt class on car/heavy_vehicle crop |
| Triple Riding | rider_region class on motorcycle crop |
| Red Light Violation | red_light + vehicle overlapping stop_line |
| Illegal Parking | illegal_parking class on full image |

## Setup

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

# 2. Frontend Setup (in a new terminal)
cd frontend
npm install

# Start the frontend dev server
npm run dev
```

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
