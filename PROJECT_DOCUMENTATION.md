# Automated Traffic Violation Detection, Analytics & Enforcement Platform

---

## 1. Project Overview

### Problem Statement
Rapid urbanization and increasing vehicle density have led to a significant rise in traffic violations, resulting in accidents, congestion, and fatalities. Manual enforcement by traffic police is unscalable, subjective, and limited by physical constraints, leading to inconsistent enforcement and low compliance rates.

### Motivation
To build a safer, more efficient urban mobility network, cities require intelligent, round-the-clock monitoring. By leveraging state-of-the-art computer vision and deep learning, we can automate the identification of traffic offenses, ensuring objective, consistent, and scalable law enforcement.

### Real-world Impact
This system directly reduces traffic-related injuries and fatalities by deterring dangerous behaviors such as helmetless riding, triple riding, and red-light jumping. It also improves traffic flow by deterring illegal parking and wrong-side driving.

### Smart City Applications
The platform serves as a core module for Smart City infrastructure. It provides actionable intelligence to city planners, traffic management authorities, and law enforcement agencies, enabling data-driven decisions on road safety and infrastructure improvements.

### Why Automation is Needed
Automated enforcement removes human bias, operates 24/7 in varying weather conditions, processes thousands of vehicles per minute, and generates legally reviewable evidence packages instantly, vastly increasing the efficiency of the traffic police force.

---

## 2. System Features

### Vehicle Detection
* **YOLO Vehicle Detector**: Utilizes a custom YOLO11n model retrained on the Indian Driving Dataset (mAP50=88.1%).
* **Supported Vehicle Classes**: Identifies and categorizes vehicles into distinct classes: Motorcycle, Car, Heavy Vehicle, and Autorickshaw, enabling vehicle-specific violation routing tailored to Indian traffic conditions.

### Helmet Violation Detection
* **Helmet**: Detects compliant riders wearing helmets.
* **No Helmet**: Flags two-wheeler riders (motorcycles/bicycles) operating without protective headgear.

### Seatbelt Violation Detection
* **Seatbelt**: Detects compliant drivers wearing seatbelts.
* **No Seatbelt**: Flags drivers in four-wheelers (cars/trucks/buses) failing to wear seatbelts.

### Triple Riding Detection
* **Rider Counting**: Accurately counts the number of human occupants on a single two-wheeler.
* **Violation Logic**: Triggers a violation if > 2 individuals are detected on a single motorcycle.

### Traffic Signal Detection
* **Red / Yellow / Green**: Continuously monitors the state of the traffic light in the camera's field of view.
* **Stop Line**: Detects the designated stop line at intersections to correlate with vehicle positions.

### Illegal Parking Detection
* **Detection Workflow**: Analyzes static vehicles in designated "No Parking" zones or vehicles dwelling in restricted lanes beyond a permissible time threshold.

### License Plate Recognition
* **Plate Detection**: Isolates the bounding box of the vehicle's license plate using the trained YOLO plate model on vehicle crops and the full frame.
* **OCR**: Extracts alphanumeric text using PaddleOCR on high-resolution plate crops.
* **Recovery Path**: Scans likely plate text regions when a visible plate is missed by the plate detector, then attaches the result to the matching vehicle.
* **Validation**: Applies regex patterns to ensure the extracted text conforms to standard regional license plate formats.

### Video Analytics
* **ByteTrack**: Employs the ByteTrack algorithm for high-performance, real-time multi-object tracking.
* **Track IDs**: Assigns and maintains unique IDs for vehicles across video frames.
* **Vehicle Trajectories**: Records the coordinate history of vehicles to analyze movement patterns.

### Wrong Side Driving Detection
* **Motion Vectors**: Computes the trajectory vector (dx, dy) over a rolling window of frames.
* **Direction Analysis**: Compares the vehicle's vector against the camera's configured "allowed direction" vector.

### Red Light Violation Detection
* **State Machine**: Tracks vehicle bounding boxes through three states: `BEFORE_LINE` → `ON_LINE` → `AFTER_LINE`.
* **Stop Line Crossing**: Triggers a violation if the state transition occurs while the Traffic Signal model detects a `RED` light.

### Evidence Management
* **Evidence Packages**: Compiles all data related to an incident into a single unified record.
* **Images**: Saves the original high-resolution frame and an AI-annotated frame (with bounding boxes).
* **JSON Reports**: Generates machine-readable metadata containing confidence scores, timestamps, and locations.

### Analytics Dashboard
* **Real-time Monitoring**: Displays live metrics and recent violations.
* **Trends**: Plots daily and weekly violation trends via interactive charts.
* **Statistics**: Aggregates data by camera location to identify geographic "hotspots".

### Challan Generation
* **PDF Generation**: Automatically compiles an official, printable Notice of Violation using ReportLab.
* **QR Verification**: Embeds a unique QR code allowing citizens to verify the challan online.
* **Human Review Workflow**: Routes low-confidence detections (0.70 - 0.84) to a human operator, while auto-issuing high-confidence (>= 0.85) violations.

---

## 3. System Architecture

```text
[ Traffic Camera / Video Stream ]
             │
             ▼
    ┌─────────────────┐
    │ Preprocessing & │
      │ Inference     │ (Custom YOLO11n + ByteTrack)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Temporal Rule   │ (State Machines, Vector Math)
    │    Engine       │
    └────────┬────────┘
             │ (Violation Detected)
             ▼
    ┌─────────────────┐
    │ Plate Detection │
     │    & OCR        │ (PaddleOCR)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │    Evidence     │ (Generates TVD-YYYYMMDD-XXXX)
    │   Management    │ (Annotates & Saves Images)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │     Challan     │ (Evaluates Confidence Threshold)
    │     Engine      │ (Generates CH-YYYYMMDD-XXXX PDF)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  MongoDB Atlas  │ (Stores Evidence & Challan Metadata)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ React Dashboard │ (Analytics, Evidence Explorer, 
    │ & Enforcement   │  Enforcement Center)
    └─────────────────┘
```

---

## 4. Technology Stack

### Backend
* **FastAPI**: High-performance asynchronous web framework for Python.
* **Python 3.10+**: Core programming language.

### AI Models
* **YOLO11n / YOLOv8**: State-of-the-art object detection (Ultralytics). Vehicle detector uses custom YOLO11n; sub-detectors use YOLOv8-based architectures.
* **ByteTrack**: Multi-object tracking algorithm for temporal analysis.

### OCR
* **PaddleOCR**: Deep-learning based Optical Character Recognition for license plate crops, with cleanup, confidence scoring, and regional plate validation.

### Database
* **MongoDB Atlas**: Cloud-hosted NoSQL database for flexible JSON-document storage.

### Frontend
* **React**: Component-based UI library.
* **Vite**: Next-generation frontend tooling and bundler.
* **TailwindCSS**: Utility-first CSS framework for rapid UI styling.
* **Recharts**: Composable charting library for React.

### PDF & Utilities
* **ReportLab**: Programmatic PDF document generation.
* **OpenCV**: Image and video processing.

---

## 5. Project Directory Structure

```text
d:\final-filipkart-hackathon\
├── app.py                      # FastAPI application entry point
├── config.py                   # Global configuration and environment variables
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (DB credentials, ports)
│
├── config/
│   └── fines.json              # Configurable penalty amounts for violations
│
├── database/
│   ├── mongo.py                # MongoDB driver, CRUD operations, and aggregations
│   └── seed_cameras.py         # Script to seed mock camera configurations
│
├── detectors/                  # YOLO Model Wrappers
│   ├── base.py                 # BaseDetector class with predict() and track()
│   ├── vehicle.py              # Custom YOLO11n Vehicle Detector
│   ├── helmet.py               # Helmet / No Helmet
│   ├── seatbelt.py             # Seatbelt / No Seatbelt
│   ├── triple_riding.py        # Counts riders on motorcycles
│   ├── traffic_signal.py       # Red/Yellow/Green & Stop Line
│   ├── illegal_parking.py      # Identifies parked vehicles
│   └── plate.py                # Detects license plate bounding boxes
│
├── engine/                     # Business Logic & Rules
│   ├── rules.py                # Stateless spatial rules (e.g. Helmet check)
│   ├── temporal_rules.py       # Stateful temporal rules (Red Light, Wrong Side)
│   └── challan.py              # Generates Official PDFs via ReportLab
│
├── ocr/                        
│   └── plate_reader.py         # PaddleOCR integration and Regex validation
│
├── routers/                    # FastAPI Endpoints
│   ├── predict.py              # Image/Video inference and Analytics APIs
│   └── challan.py              # Enforcement and Challan management APIs
│
├── services/                   # Orchestration
│   ├── pipeline.py             # Single Image Inference Pipeline
│   ├── video_pipeline.py       # Background Video Processing Pipeline
│   └── evidence.py             # Creates Evidence Packages (ZIP, annotations)
│
├── utils/                      
│   ├── annotate.py             # Draws Bounding Boxes and Text on images
│   ├── preprocess.py           # Image resizing and cropping utilities
│   └── schemas.py              # Pydantic models for API request/response validation
│
├── outputs/                    # Generated Artifacts (Ignored in Git)
│   ├── originals/              # Raw frames
│   ├── annotated/              # Annotated evidence frames
│   ├── reports/                # JSON metadata
│   ├── thumbnails/             # Compressed images for web
│   └── challans/               # Generated PDF notices
│
└── frontend/                   # React Application
    ├── package.json            # Node dependencies
    ├── vite.config.js          # Vite bundler config
    ├── tailwind.config.js      # Tailwind theme configuration
    └── src/
        ├── App.jsx             # React Router definitions
        ├── main.jsx            # React DOM entry
        ├── index.css           # Global styles
        ├── services/
        │   └── api.js          # Axios API client
        ├── components/         # Reusable UI components (Sidebar, StatCard, etc.)
        └── pages/              # Route views
            ├── DashboardOverview.jsx
            ├── VideoProcessor.jsx
            ├── EvidenceExplorer.jsx
            ├── EvidenceDetails.jsx
            ├── Analytics.jsx
            ├── EnforcementCenter.jsx
            ├── ChallanExplorer.jsx
            └── ChallanDetails.jsx
```

---

## 6. Installation Guide

### Prerequisites
* **Python**: 3.10 or higher.
* **Node.js**: v18+ and npm.
* **MongoDB Atlas**: An active cluster (or a local MongoDB instance).
* **GPU Requirements**: NVIDIA GPU with CUDA support is highly recommended for real-time video processing, though it can run on CPU at lower FPS.

### Step-by-Step Installation

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd final-filipkart-hackathon
   ```

2. **Setup Python Virtual Environment**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Install Backend Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install lapx reportlab qrcode Pillow
   ```

4. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

5. **Seed the Database**
   ```bash
   python database/seed_cameras.py
   ```

---

## 7. Environment Configuration

Create a `.env` file in the root directory:

```env
# .env
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=traffic_violations_db

# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
```

---

## 8. Running the Backend

Start the FastAPI server using Uvicorn:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

**Startup Process**: Upon startup, the application initializes the `InferencePipeline` singleton. This loads all YOLOv8 weights into GPU/CPU memory and establishes a connection pool to MongoDB Atlas to ensure sub-100ms inference times on incoming requests.

---

## 9. Running the Frontend

In a separate terminal, navigate to the `frontend` directory:

```bash
cd frontend
npm run dev
```

**Frontend Workflow**: Vite will bundle the React application and start a hot-reloading development server, typically available at `http://localhost:5173`. The application communicates with the backend via Axios (configured in `api.js`).

---

## 10. API Documentation

### Health APIs
**`GET /health`**
* **Purpose**: Check system status and model load states.
* **Output**: JSON containing uptime and loaded components.

### Image Processing APIs
**`POST /predict`**
* **Purpose**: Process a single image for violations.
* **Input**: `multipart/form-data` with `file` (image).
* **Output**: `PredictionResponse` JSON with evidence ID and bounding boxes.

### Video Processing APIs
**`POST /video/predict`**
* **Purpose**: Process a traffic video temporally.
* **Input**: `multipart/form-data` with `file` (video) and `camera_id`.
* **Output**: `{"task_id": "task_1234", "status": "processing_started"}`

**`GET /video/status/{id}`**
* **Purpose**: Poll video processing progress.
* **Output**: `{"progress": 45, "status": "processing"}`

**`GET /video/result/{id}`**
* **Purpose**: Retrieve final video results.
* **Output**: Contains `violations` count and `processed_video` URL.

### Evidence APIs
**`GET /evidence/{id}`**
* **Purpose**: Retrieve evidence package metadata.
* **Output**: Full JSON of detected violations and OCR text.

**`GET /evidence/{id}/download`**
* **Purpose**: Download a ZIP archive containing images and JSON reports for court submission.

### Analytics APIs
**`GET /analytics/trends`**
* **Purpose**: Fetch daily violation frequencies for Line charts.
* **Output**: List of dates mapped to violation counts.

**`GET /analytics/hotspots`**
* **Purpose**: Aggregate violations by geographic coordinates.
* **Output**: Array of camera locations and total violations.

### Challan APIs
**`GET /challan/list`**
* **Purpose**: Paginated list of challans.
* **Input**: Query params `limit`, `skip`, `status`, `plate_number`.
* **Output**: `{ "total": 100, "records": [...] }`

**`GET /challan/{id}`**
* **Purpose**: Retrieve specific challan details.

**`GET /challan/pdf/{id}`**
* **Purpose**: Download the generated official PDF notice.

**`PUT /challan/status/{id}`**
* **Purpose**: Update workflow status (e.g., `REVIEW_REQUIRED` to `GENERATED`).

**`POST /challan/generate`**
* **Purpose**: Force manual generation of a challan from an evidence ID.

**`GET /demo/enforcement`**
* **Purpose**: Aggregated statistics for the Enforcement Dashboard (estimated revenue, pending reviews).

---

## 11. Database Design

### `evidence` Collection
Stores raw violation data.
* `evidence_id`: String (e.g., `TVD-YYYYMMDD-XXXX`)
* `timestamp`: ISO-8601 Date
* `vehicles`: Array of detected vehicles with bounding boxes and OCR results.
* `scene_violations`: Array of environment violations (e.g., Illegal Parking).
* `camera_id`, `latitude`, `longitude`: Geospatial data.

### `challans` Collection
Stores actionable enforcement notices.
* `challan_id`: String (e.g., `CH-YYYYMMDD-XXXX`)
* `evidence_id`: Reference to the `evidence` collection.
* `plate_number`: String (Validated OCR text).
* `violation_type`: String (e.g., `Red Light Violation`).
* `fine_amount`: Integer (in local currency).
* `confidence`: Float (0.0 to 1.0).
* `status`: String Enum (`PENDING`, `REVIEW_REQUIRED`, `GENERATED`, `ISSUED`, `PAID`, `DISPUTED`).
* `pdf_path`: String URL to the generated document.

### `camera_configs` Collection
Stores intersection calibration data.
* `camera_id`: String
* `location`: String description.
* `allowed_vector`: Array `[x, y]` defining legal traffic flow direction.
* `stop_line_coords`: Array `[x1, y1, x2, y2]` defining the virtual stop line.

---

## 12. Violation Detection Logic

* **Helmet / Seatbelt / Triple Riding**: Spatial rules. Analyzes bounding boxes from sub-models cropped around the parent Vehicle bounding box. If sub-model detects "No Helmet", a violation is logged.
* **Illegal Parking**: If a vehicle's bounding box remains stationary (IoU > 0.95 across frames) in a restricted ROI for `T > max_dwell_time`.
* **Stop Line Violation**: Bounding box `y_max` intersects the virtual `stop_line_coords`.
* **Red Light Violation**: `TemporalRuleEngine` tracks transition `BEFORE_LINE` to `AFTER_LINE`. Checks if `TrafficSignal` model outputs `Red` during the exact frame of intersection.
* **Wrong Side Driving**:
  ```python
  # Pseudocode
  dx = current_x - past_x
  dy = current_y - past_y
  motion_vector = normalize(dx, dy)
  if dot_product(motion_vector, camera.allowed_vector) < -0.5:
      trigger_wrong_side_violation()
  ```

---

## 13. OCR Pipeline

1. **Plate Detection**: YOLO model isolates the license plate.
2. **Crop & Enhance**: The bounding box is extracted from the *original* high-res frame (not the resized inference frame).
3. **PaddleOCR Read**: PaddleOCR extracts raw text and confidence scores from the crop.
4. **Recovery Scan**: If no plate box is found, likely text regions are scanned and matched back to the vehicle.
5. **Regex Validation**: Filters out noise (e.g., bumper stickers) by enforcing standard patterns (e.g., `^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$`).

---

## 14. Evidence Management

When a violation occurs, the `EvidenceManager` compiles a robust legal package:
* **Evidence ID**: Unique tracking hash (`TVD-...`).
* **Directory Structure**: Saves artifacts in `outputs/` (Originals, Annotated, Thumbnails).
* **Annotated Images**: Uses OpenCV to draw bounding boxes, text overlays, timestamps, and Watermarks on the image to ensure tamper-evident visual proof.
* **Downloadable Packages**: Packages all related files into a ZIP archive for easy handover to courts or defendants.

---

## 15. Challan Workflow

```text
[ Detection ] (YOLOv8 + ByteTrack)
      │
      ▼
[ Evidence Package Created ]
      │
      ▼
[ OCR Validation Check ] ────(Fail)───> [ End (Analytics Only) ]
      │
      ▼ (Success)
[ Confidence Check ]
      │
      ├────( >= 0.85 )──────────────┐
      │                             │
      ├────( 0.70 to 0.84 )──┐      │
      │                      ▼      ▼
      │               [ REVIEW ]  [ AUTO GENERATE ]
      ▼                 (Human)      (PDF Created)
[ End ]                      │      │
                             ▼      ▼
                       [ ENFORCEMENT DB ]
```

---

## 16. Dashboard Guide

* **Dashboard Overview**: Live feed of the latest violations, high-level metrics, and system status.
* **Video Upload**: An interface to upload MP4/AVI footage. Displays a real-time progress bar polling the backend inference job.
* **Evidence Explorer**: Search and filter raw evidence packages by date, violation type, or plate number.
* **Analytics**: Interactive Recharts displaying daily trend lines, violation pie charts, and geographic Hotspot tables.
* **Enforcement Center**: High-level financial and operational view (Revenue Estimates, Paid vs Pending statistics).
* **Challan Explorer**: Operational data table for managing notices.
* **Challan Details**: Embedded PDF viewer allowing an administrator to update statuses (`REVIEW_REQUIRED` → `GENERATED` → `ISSUED` → `PAID`).

---

## 17. Performance Metrics

*(Note: Metrics depend on hardware. Benchmarks below represent an NVIDIA RTX 3080/4090)*

| Component | Inference Time (ms) | mAP@50 | False Positive Rate |
| :--- | :--- | :--- | :--- |
| Vehicle Detector (Custom YOLO11n) | 8 - 12ms | 0.881 | < 3% |
| License Plate | 8 - 10ms | 0.995 | < 1% |
| OCR (PaddleOCR) | 25 - 40ms | 0.91 | - |
| Helmet Detector | 10 - 12ms | 0.799 | 4% |
| Video Tracking (ByteTrack)| 3 - 5ms / frame | N/A | N/A |

---

## 18. Future Scope

* **Redis Integration**: Move `TrackState` from in-memory Python dictionaries to a Redis cluster to allow multi-node horizontal scaling.
* **Live CCTV Streams**: Replace static video file uploads with continuous RTSP stream processing.
* **Government Database Integration**: Connect OCR outputs to VAHAN (or equivalent DMV databases) to automatically fetch owner addresses and SMS contact numbers.
* **Automatic E-Challan Integration**: Directly hook into the government's official E-Challan payment gateway APIs.
* **Mobile App**: A companion app for traffic wardens to receive live alerts.

---

## 19. Limitations

* **OCR in Poor Conditions**: Heavy rain, mud-covered plates, or extreme glare significantly reduce OCR accuracy.
* **Camera Calibration Dependency**: Wrong-side driving and Stop-line crossing require precise `camera_configs`. Moving the physical camera requires updating the virtual database coordinates.
* **Human Verification**: While highly accurate, the system requires humans to verify `REVIEW_REQUIRED` (0.70-0.84 confidence) flags to prevent unjust penalization.

---

## 20. Conclusion

The Automated Traffic Violation Detection, Analytics & Enforcement Platform is a comprehensive, production-ready solution for Smart City infrastructure. By bridging the gap between raw computer vision AI and legal enforcement workflows (Evidence Packaging, PDF Generation, State Machines), it provides a scalable, bias-free, and highly efficient tool to drastically improve urban road safety and traffic management.
