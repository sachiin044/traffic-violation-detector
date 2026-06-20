"""
Evidence Management System.
Handles creating TVD-IDs, saving evidence files (original, annotated, report),
and packaging them into ZIP files for download.
"""

import os
import json
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import cv2
import numpy as np

from utils.schemas import VehicleResult, Violation
from config import EVIDENCE_DIR

import logging
logger = logging.getLogger(__name__)


def _model_to_dict(model: Any) -> Dict[str, Any]:
    """Convert Pydantic v1/v2 models to plain dictionaries."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return dict(model)


class EvidenceManager:
    """Manages generation, storage, and retrieval of evidence packages."""

    def __init__(self, base_dir: Path = EVIDENCE_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def generate_evidence_id(self) -> str:
        """Generate a new Evidence ID (TVD-YYYYMMDD-XXXXXX)."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        # Use a short hex for the suffix for the MVP, or random digits
        unique_suffix = str(uuid.uuid4().int)[:6]
        return f"TVD-{date_str}-{unique_suffix}"

    def create_evidence_package(
        self,
        original_image: np.ndarray,
        annotated_image: np.ndarray,
        vehicle_results: List[VehicleResult],
        scene_violations: List[Violation],
        processing_time_ms: float,
    ) -> Dict[str, Any]:
        """
        Create a new evidence package folder and save all files.
        Returns the dictionary representing the MongoDB document.
        """
        evidence_id = self.generate_evidence_id()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 1. Create directory
        evidence_path = self.base_dir / evidence_id
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        # 2. Save Images
        orig_path = evidence_path / "original.jpg"
        ann_path = evidence_path / "annotated.jpg"
        thumb_path = evidence_path / "thumbnail.jpg"
        
        cv2.imwrite(str(orig_path), original_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(str(ann_path), annotated_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        # Create thumbnail (resize annotated to max 400px width)
        h, w = annotated_image.shape[:2]
        thumb_w = 400
        if w > thumb_w:
            thumb_h = int(h * (thumb_w / w))
            thumbnail = cv2.resize(annotated_image, (thumb_w, thumb_h))
            cv2.imwrite(str(thumb_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])
        else:
            cv2.imwrite(str(thumb_path), annotated_image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
        # 3. Aggregate all violations
        all_violation_types = []
        best_plate = None
        best_ocr_conf = 0.0
        max_violation_conf = 0.0
        primary_vehicle_type = "scene"
        
        for v in vehicle_results:
            for viol in v.violations:
                all_violation_types.append(viol.type)
                if viol.confidence > max_violation_conf:
                    max_violation_conf = viol.confidence
                    primary_vehicle_type = v.vehicle_type
                    
            if v.license_plate and (v.plate_confidence or 0) > best_ocr_conf:
                best_plate = v.license_plate
                best_ocr_conf = v.plate_confidence
                
        for sv in scene_violations:
            all_violation_types.append(sv.type)
            if sv.confidence > max_violation_conf:
                max_violation_conf = sv.confidence
                
        # Deduplicate violations list
        unique_violations = list(set(all_violation_types))
        
        # 4. Generate JSON Report
        report_data = {
            "evidence_id": evidence_id,
            "timestamp": timestamp,
            "plate_number": best_plate,
            "vehicle_type": primary_vehicle_type,
            "violations": unique_violations,
            "vehicles": [_model_to_dict(v) for v in vehicle_results],
            "scene_violations": [_model_to_dict(v) for v in scene_violations],
            "confidence": round(max_violation_conf, 3),
            "ocr_text": best_plate,
            "ocr_confidence": round(best_ocr_conf, 3),
            "processing_time_ms": round(processing_time_ms, 1),
            "image_path": f"/evidence/{evidence_id}/original.jpg",
            "annotated_path": f"/evidence/{evidence_id}/annotated.jpg",
            "thumbnail_path": f"/evidence/{evidence_id}/thumbnail.jpg"
        }
        
        report_path = evidence_path / "report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
            
        logger.info(f"[{evidence_id}] Created evidence package in {evidence_path}")
        return report_data

    def create_zip_package(self, evidence_id: str) -> Optional[str]:
        """
        Zip the evidence folder for download.
        Returns the path to the ZIP file or None if evidence doesn't exist.
        """
        evidence_path = self.base_dir / evidence_id
        if not evidence_path.exists() or not evidence_path.is_dir():
            return None
            
        zip_base_path = str(self.base_dir / f"{evidence_id}")
        # shutil.make_archive adds .zip automatically
        zip_path = shutil.make_archive(zip_base_path, 'zip', root_dir=evidence_path)
        
        return zip_path
