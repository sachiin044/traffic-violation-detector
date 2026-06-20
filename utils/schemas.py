"""
Pydantic response schemas for the Traffic Violation Detection API.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """Bounding box coordinates."""
    x1: float
    y1: float
    x2: float
    y2: float


class Detection(BaseModel):
    """A generic detection (bounding box, class, confidence)."""
    class_name: str
    confidence: float
    bbox: BBox
    model_source: str
    track_id: Optional[int] = None


class Violation(BaseModel):
    """A detected violation."""
    type: str  # e.g., "Helmet Non Compliance"
    confidence: float
    bbox: Optional[BBox] = None


class VehicleResult(BaseModel):
    """All data associated with a single detected vehicle."""
    vehicle_id: int
    vehicle_type: str
    bbox: BBox
    license_plate: Optional[str] = None
    plate_confidence: Optional[float] = None
    plate_bbox: Optional[BBox] = None
    violations: List[Violation] = []
    all_detections: List[Detection] = []
    track_id: Optional[int] = None


class PredictionResponse(BaseModel):
    """Full response for a single image prediction."""
    image_id: str
    evidence_id: Optional[str] = None
    timestamp: str
    processing_time_ms: float
    image_width: int
    image_height: int
    total_vehicles: int
    total_violations: int
    vehicles: List[VehicleResult] = []
    scene_violations: List[Violation] = []  # violations not tied to a specific vehicle
    annotated_image_path: Optional[str] = None


class BatchPredictionResponse(BaseModel):
    """Response for batch prediction."""
    batch_id: str
    timestamp: str
    total_images: int
    total_processing_time_ms: float
    results: List[PredictionResponse] = []


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    gpu_available: bool
    gpu_name: Optional[str] = None
    models_loaded: int
    uptime_seconds: float


class ModelInfo(BaseModel):
    """Info about a loaded model."""
    name: str
    status: str
    weight_path: str
    class_names: dict
    confidence_threshold: float


class ModelsResponse(BaseModel):
    """Response for /models endpoint."""
    total_models: int
    models: List[ModelInfo] = []


class ViolationRecord(BaseModel):
    """Database record for a violation."""
    id: Optional[int] = None
    timestamp: str
    image_id: str
    plate_number: Optional[str] = None
    vehicle_type: str
    violation_type: str
    confidence: float
    image_path: Optional[str] = None
