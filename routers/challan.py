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

    # The DB row has no per-vehicle data; merge in report.json, which does.
    report = pipe.evidence_manager.load_report(evidence_id)
    if report:
        report.update({k: v for k, v in evidence.items() if v is not None})
        evidence = report
        
    # Same builder as the automatic path: one challan for the vehicle, all its offences.
    # An officer asked for it, so it skips the confidence threshold.
    vehicle = pipe.challan_manager._target_vehicle(evidence)
    if not vehicle:
        raise HTTPException(status_code=400, detail="Evidence has no detected license plate")

    challan = pipe.challan_manager.build_challan(evidence, vehicle, status="GENERATED")
    challan_id = challan["challan_id"]
    return {"message": "Challan generated manually", "challan_id": challan_id}

@router.get("/demo/enforcement")
async def get_enforcement_demo():
    """Judge Demo endpoint returning high level stats."""
    pipe = _get_pipeline()
    return pipe.db.get_enforcement_demo_stats()


@router.get("/rto/{plate}")
async def rto_lookup(plate: str):
    """Which RTO a plate is registered with, from its state + district code (e.g. UP93 -> Jhansi)."""
    from utils.rto import lookup_rto
    info = lookup_rto(plate)
    if not info:
        raise HTTPException(status_code=404, detail="No RTO found for this plate's district code")
    return info
