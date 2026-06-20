from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any
from pathlib import Path

from config import INFERENCE_OUTPUTS_DIR
from routers.predict import _get_pipeline

router = APIRouter(tags=["Enforcement"])

@router.get("/challan/list")
async def list_challans(
    limit: int = 50, 
    skip: int = 0, 
    status: Optional[str] = None, 
    plate_number: Optional[str] = None
):
    """List challans with filtering."""
    pipe = _get_pipeline()
    return pipe.db.search_challans(limit, skip, status, plate_number)

@router.get("/challan/{challan_id}")
async def get_challan(challan_id: str):
    """Get full details of a specific challan."""
    pipe = _get_pipeline()
    challan = pipe.db.get_challan(challan_id)
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found")
    return challan

@router.get("/challan/pdf/{challan_id}")
async def download_challan_pdf(challan_id: str):
    """Download the generated official PDF."""
    pdf_path = INFERENCE_OUTPUTS_DIR / "challans" / f"{challan_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found on disk")
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"{challan_id}.pdf"
    )

@router.put("/challan/status/{challan_id}")
async def update_status(challan_id: str, status: str = Query(...)):
    """Update challan status (e.g. REVIEW_REQUIRED -> ISSUED)."""
    valid_statuses = ["PENDING", "REVIEW_REQUIRED", "GENERATED", "ISSUED", "PAID", "DISPUTED"]
    if status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    pipe = _get_pipeline()
    success = pipe.db.update_challan_status(challan_id, status.upper())
    if not success:
        raise HTTPException(status_code=404, detail="Challan not found")
    return {"message": f"Status updated to {status.upper()}"}

@router.post("/challan/generate")
async def generate_challan_manual(evidence_id: str = Query(...)):
    """Manually override and generate a challan from evidence."""
    pipe = _get_pipeline()
    evidence = pipe.db.get_evidence(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
        
    # We must load the ChallanManager
    from engine.challan import ChallanManager
    manager = ChallanManager(pipe.db)
    
    # We will forcefully evaluate it. For manual, we skip threshold check
    # so we'll just mock the evaluation by running evaluate_evidence but setting 
    # it to bypass, or just building it directly.
    # For hackathon simplicity, we just run evaluate_evidence and hope it meets threshold,
    # but let's just do a direct build to guarantee generation if they requested it manually.
    
    vehicles = evidence.get("vehicles", [])
    target_vehicle = None
    target_violation = None
    for v in vehicles:
        if v.get("license_plate") and v.get("violations"):
            target_vehicle = v
            target_violation = v["violations"][0]
            break
            
    if not target_vehicle:
        raise HTTPException(status_code=400, detail="Evidence has no detected license plate")
        
    challan_id = manager.generate_challan_id()
    v_type = target_violation["type"]
    fine_amount = manager.fines_config.get(v_type, 1000)
    
    challan_data = {
        "challan_id": challan_id,
        "evidence_id": evidence_id,
        "plate_number": target_vehicle["license_plate"],
        "vehicle_type": target_vehicle["vehicle_type"],
        "violation_type": v_type,
        "fine_amount": fine_amount,
        "confidence": target_violation["confidence"],
        "timestamp": evidence["timestamp"],
        "location": evidence.get("location", "Smart City Checkpoint"),
        "status": "GENERATED",
        "created_at": evidence["timestamp"],
    }
    
    pdf_path = manager.generate_pdf(challan_data, evidence)
    challan_data["pdf_path"] = f"/outputs/challans/{Path(pdf_path).name}"
    
    pipe.db.insert_challan(challan_data)
    return {"message": "Challan generated manually", "challan_id": challan_id}

@router.get("/demo/enforcement")
async def get_enforcement_demo():
    """Judge Demo endpoint returning high level stats."""
    pipe = _get_pipeline()
    return pipe.db.get_enforcement_demo_stats()
