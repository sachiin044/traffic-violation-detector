# 🚦 Platform Features

A quick-reference list of all capabilities offered by the Automated Traffic Violation Detection & Enforcement Platform.

## 🧠 AI & Computer Vision
* **Real-Time Vehicle Detection:** Custom YOLO11n model trained on Indian Driving Dataset for high-accuracy detection of Motorcycles, Cars, Heavy Vehicles, and Autorickshaws.
* **License Plate OCR:** YOLO plate localization followed by PaddleOCR text extraction, cleanup, and regex validation for regional plates.
* **Temporal Video Tracking:** ByteTrack multi-object tracking to assign persistent IDs to vehicles across frames.

## 🚨 Automated Violation Detection
* **Helmet Non-Compliance:** Identifies motorcycle/bicycle riders without helmets.
* **Triple Riding:** Detects when more than two occupants are on a single two-wheeler.
* **Seatbelt Non-Compliance:** Flags drivers in four-wheelers who are not wearing seatbelts.
* **Red-Light Jumping:** Stateful tracking (BEFORE → ON → AFTER line) synchronized with traffic signal detection.
* **Wrong-Side Driving:** Motion vector analysis (dx, dy) against allowed camera directions.
* **Illegal Parking:** Identifies stationary vehicles dwelling in restricted "No Parking" zones.

## 📁 Evidence Management
* **Tamper-Evident Media:** Saves raw frames alongside AI-annotated frames featuring bounding boxes, timestamps, and confidence scores.
* **Smart Packaging:** Bundles images and machine-readable JSON metadata into an official Evidence Package (`TVD-YYYYMMDD-XXXX`).
* **Downloadable Archives:** One-click ZIP generation for easy handover to authorities or courts.

## ⚖️ Legal Enforcement & Challans
* **Auto-Challan Generation:** Automatically evaluates confidence scores to generate official Notice of Violation PDFs via ReportLab.
* **Human-in-the-Loop Queue:** Routes marginal confidence detections (0.70 - 0.84) to a "Review Required" queue for manual verification.
* **Dynamic Fine Mapping:** Assigns financial penalties based on localized violation configurations.
* **QR Verification:** Embeds a scannable QR code on every physical/digital notice for citizen verification.

## 📊 Analytics & Dashboards
* **Enforcement Center:** High-level operational view showing Estimated Revenue, Paid vs Pending notices, and queue sizes.
* **Hotspot Mapping:** Aggregates violations by camera GPS coordinates to identify dangerous intersections.
* **Daily Trend Analysis:** Interactive Recharts plotting the frequency of specific violations over time.
* **Repeat Offender Tracking:** Ranks the most frequent offending license plates.
* **Live Operations Dashboard:** Upload video footage and monitor background inference jobs with real-time progress bars.

## ⚡ Architecture & Performance
* **Asynchronous Video Processing:** Non-blocking background workers ensuring zero HTTP timeouts during heavy video inference.
* **Scalable MongoDB Atlas Storage:** Cloud-hosted NoSQL architecture for flexible schema management.
* **Crop-Based Inference Routing:** Optimized pipeline that only runs relevant sub-models (e.g., Seatbelt detector only runs on cropped Car bounding boxes, saving massive compute).
