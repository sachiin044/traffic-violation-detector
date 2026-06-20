import os
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch

from database.mongo import MongoDB
from config import INFERENCE_OUTPUTS_DIR

logger = logging.getLogger(__name__)

class ChallanManager:
    def __init__(self, db: MongoDB):
        self.db = db
        self.challan_dir = INFERENCE_OUTPUTS_DIR / "challans"
        self.challan_dir.mkdir(parents=True, exist_ok=True)
        
        # Load Fines config
        fines_path = Path(__file__).parent.parent / "config" / "fines.json"
        try:
            with open(fines_path, "r") as f:
                self.fines_config = json.load(f)
        except Exception as e:
            logger.error(f"Could not load fines.json: {e}")
            self.fines_config = {}

    def generate_challan_id(self) -> str:
        """CH-YYYYMMDD-XXXXXX"""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"CH-{date_str}-{unique_id}"

    def evaluate_evidence(self, evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate an evidence package to see if a challan should be created.
        Rule: Must have a plate. High confidence (>=0.85) -> GENERATED. Medium -> REVIEW_REQUIRED.
        """
        # Hackathon Logic: Only look at the first vehicle's first violation for simplicity
        vehicles = evidence.get("vehicles", [])
        if not vehicles:
            return None
            
        # Find a vehicle with a license plate and a violation
        target_vehicle = None
        target_violation = None
        for v in vehicles:
            if v.get("license_plate") and v.get("violations"):
                target_vehicle = v
                target_violation = v["violations"][0] # Just take the first one
                break
                
        if not target_vehicle or not target_violation:
            return None
            
        plate = target_vehicle["license_plate"]
        v_type = target_violation["type"]
        confidence = target_violation["confidence"]
        
        # Threshold logic
        if confidence >= 0.85:
            status = "GENERATED"
        elif confidence >= 0.70:
            status = "REVIEW_REQUIRED"
        else:
            return None # Skip
            
        fine_amount = self.fines_config.get(v_type, 1000)
        challan_id = self.generate_challan_id()
        
        challan_data = {
            "challan_id": challan_id,
            "evidence_id": evidence["evidence_id"],
            "plate_number": plate,
            "vehicle_type": target_vehicle["vehicle_type"],
            "violation_type": v_type,
            "fine_amount": fine_amount,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "location": evidence.get("location", "Smart City Checkpoint"),
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Generate PDF
        pdf_path = self.generate_pdf(challan_data, evidence)
        challan_data["pdf_path"] = f"/outputs/challans/{Path(pdf_path).name}"
        
        self.db.insert_challan(challan_data)
        logger.info(f"Created Challan {challan_id} with status {status}")
        return challan_data

    def generate_pdf(self, challan: Dict[str, Any], evidence: Dict[str, Any]) -> str:
        """Render the official PDF Notice."""
        challan_id = challan["challan_id"]
        pdf_path = self.challan_dir / f"{challan_id}.pdf"
        
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        width, height = A4
        
        # Header
        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(colors.darkblue)
        c.drawString(50, height - 50, "TRAFFIC VIOLATION NOTICE")
        
        c.setFont("Helvetica", 12)
        c.setFillColor(colors.gray)
        c.drawString(50, height - 70, "Authority: Smart Traffic Enforcement System")
        c.line(50, height - 80, width - 50, height - 80)
        
        # Details
        c.setFont("Helvetica", 12)
        c.setFillColor(colors.black)
        
        y = height - 120
        details = [
            f"Challan ID: {challan_id}",
            f"Evidence ID: {challan['evidence_id']}",
            f"Date/Time: {challan['timestamp']}",
            f"Location: {challan['location']}",
            "",
            f"Vehicle Plate: {challan['plate_number']}",
            f"Vehicle Type: {challan['vehicle_type']}",
            "",
            f"Violation: {challan['violation_type']}",
            f"AI Confidence: {challan['confidence'] * 100:.1f}%",
            f"Fine Amount: INR {challan['fine_amount']}"
        ]
        
        for text in details:
            if text.startswith("Fine Amount"):
                c.setFont("Helvetica-Bold", 14)
                c.setFillColor(colors.red)
            c.drawString(50, y, text)
            c.setFont("Helvetica", 12)
            c.setFillColor(colors.black)
            y -= 20
            
        # Evidence Images (Draw them if they exist)
        y -= 20
        c.drawString(50, y, "Photographic Evidence:")
        y -= 10
        
        orig_path = Path(evidence.get("original_path", "")).name
        orig_full = INFERENCE_OUTPUTS_DIR / orig_path
        annot_path = Path(evidence.get("annotated_path", "")).name
        annot_full = INFERENCE_OUTPUTS_DIR / annot_path
        
        try:
            if orig_full.exists():
                c.drawImage(str(orig_full), 50, y - 200, width=220, height=180, preserveAspectRatio=True)
            if annot_full.exists():
                c.drawImage(str(annot_full), 300, y - 200, width=220, height=180, preserveAspectRatio=True)
        except Exception as e:
            logger.error(f"Failed to embed images in PDF: {e}")
            
        y -= 250
        
        # QR Code
        qr_data = f"http://localhost:5173/verify/challan/{challan_id}"
        qr = qrcode.make(qr_data)
        qr_path = self.challan_dir / f"{challan_id}_qr.png"
        qr.save(qr_path)
        
        c.drawImage(str(qr_path), width - 150, 50, width=100, height=100)
        
        # Disclaimer
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(colors.gray)
        c.drawString(50, 60, "Generated by AI-Assisted Traffic Violation Enforcement System.")
        c.drawString(50, 45, "This notice requires human verification before legal issuance.")
        
        c.save()
        
        # Cleanup QR temp file
        if qr_path.exists():
            qr_path.unlink()
            
        return str(pdf_path)
