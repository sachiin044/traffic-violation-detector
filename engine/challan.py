"""
Challan creation and the e-challan PDF notice.

One challan is created per offending vehicle and lists every offence found on
it, the way Indian e-challans do. Sections and amounts come from
config/fines.json (Motor Vehicles Act, 1988 as amended in 2019).

The PDF follows the structure of an Indian e-challan (challan number, offence
date/time/place, vehicle registration, offence table with MV Act sections,
photographic evidence, payment window and court referral), but it is clearly
marked as a demo. It carries no government emblem or real portal links, so it
can't be mistaken for an official notice.
"""

import io
import json
import uuid
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from database.mongo import MongoDB
from utils.rto import lookup_rto
from config import (
    INFERENCE_OUTPUTS_DIR,
    EVIDENCE_DIR,
    CHALLAN_AUTHORITY,
    CHALLAN_CITY,
    CHALLAN_PAYMENT_DAYS,
    CHALLAN_VERIFY_URL,
)

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30), "IST")

# Same thresholds the frontend shows
AUTO_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.70

VEHICLE_CLASS = {
    "motorcycle": "Two-wheeler (motorcycle / scooter)",
    "bicycle": "Bicycle",
    "car": "Light motor vehicle (car)",
    "heavy_vehicle": "Heavy vehicle (bus / truck)",
    "autorickshaw": "Three-wheeler (autorickshaw)",
}

STATUS_TEXT = {
    "GENERATED": "Approved, ready to issue",
    "REVIEW_REQUIRED": "Pending officer review",
    "ISSUED": "Issued",
    "PAID": "Paid",
    "DISPUTED": "Disputed",
    "PENDING": "Pending",
}

# ── Colours ────────────────────────────────────────────────────────────
INK = colors.HexColor("#14171B")
MUTED = colors.HexColor("#5A636E")
RULE = colors.HexColor("#C9CED4")
BAND = colors.HexColor("#1B2A41")
TINT = colors.HexColor("#F1F3F5")
SIGN = colors.HexColor("#1B4E9B")
RED = colors.HexColor("#B3261E")


def _to_ist(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def _fmt_dt(iso: Optional[str]) -> str:
    dt = _to_ist(iso)
    return dt.strftime("%d-%m-%Y %I:%M %p IST") if dt else "-"


def _fmt_date(dt: Optional[datetime]) -> str:
    return dt.strftime("%d-%m-%Y") if dt else "-"


def _rupees(n: float) -> str:
    """Indian digit grouping: 125000 -> 1,25,000."""
    n = int(round(n or 0))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return f"{'-' if n < 0 else ''}{s}"


def _plate_display(plate: Optional[str]) -> str:
    """Print plates the usual way: 'KA 00 TE 0001'."""
    import re
    if not plate:
        return "Not read"
    p = re.sub(r"[^A-Z0-9]", "", str(plate).upper())
    m = re.match(r"^(\d{2})(BH)(\d{4})([A-Z]{1,2})$", p)
    if m:
        return " ".join(m.groups())
    m = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{1,4})$", p)
    if m:
        return " ".join(g for g in m.groups() if g)
    return p


class ChallanManager:
    def __init__(self, db: MongoDB):
        self.db = db
        self.challan_dir = INFERENCE_OUTPUTS_DIR / "challans"
        self.challan_dir.mkdir(parents=True, exist_ok=True)

        fines_path = Path(__file__).parent.parent / "config" / "fines.json"
        try:
            with open(fines_path, "r", encoding="utf-8") as f:
                self.fines_config = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
        except Exception as e:
            logger.error(f"Could not load fines.json: {e}")
            self.fines_config = {}

    # ── Lookups ────────────────────────────────────────────────────────

    def generate_challan_id(self) -> str:
        """CH-YYYYMMDD-XXXXXX"""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"CH-{date_str}-{uuid.uuid4().hex[:6].upper()}"

    def offence_info(self, violation_type: str) -> Dict[str, Any]:
        """Section, wording and penalty for a violation type (supports the old number-only format)."""
        entry = self.fines_config.get(violation_type)
        if isinstance(entry, (int, float)):
            entry = {"amount": entry}
        entry = dict(entry or {})
        return {
            "type": violation_type,
            "offence": entry.get("offence", violation_type),
            "section": entry.get("section", "177"),
            "amount": float(entry.get("amount", 500)),
            "court": bool(entry.get("court", False)),
            "note": entry.get("note", ""),
        }

    def build_offences(self, violations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """One line per offence type, keeping the strongest confidence and counting repeats."""
        merged: Dict[str, Dict[str, Any]] = {}
        for v in violations or []:
            v_type = v.get("type")
            if not v_type:
                continue
            conf = float(v.get("confidence") or 0)
            if v_type not in merged:
                merged[v_type] = {**self.offence_info(v_type), "confidence": conf, "count": 1}
            else:
                merged[v_type]["count"] += 1
                merged[v_type]["confidence"] = max(merged[v_type]["confidence"], conf)
        return sorted(merged.values(), key=lambda o: -o["confidence"])

    # ── Creating challans ──────────────────────────────────────────────

    @staticmethod
    def _target_vehicle(evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """The flagged vehicle with a readable plate and the strongest violation."""
        candidates = [
            v for v in evidence.get("vehicles", []) or []
            if v.get("license_plate") and v.get("violations")
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda v: max(float(x.get("confidence") or 0) for x in v["violations"]))

    def build_challan(self, evidence: Dict[str, Any], vehicle: Dict[str, Any], status: str) -> Dict[str, Any]:
        """Create the challan record, write its PDF and store it."""
        offences = self.build_offences(vehicle.get("violations", []))
        primary = offences[0]
        now = datetime.now(timezone.utc).isoformat()

        # Where the vehicle is registered, from the plate's RTO code (e.g. UP 93 -> Jhansi)
        rto = lookup_rto(vehicle.get("license_plate"))
        registered_at = f"{rto['place']} (RTO {rto['display_code']})" if rto else None
        # Place of offence: the camera's location when known. Otherwise fall back to the
        # registering RTO, labelled so it isn't mistaken for the actual spot.
        if evidence.get("location"):
            location = evidence["location"]
        elif rto:
            location = f"{rto['place']} (by vehicle registration {rto['display_code']})"
        else:
            location = CHALLAN_CITY
        challan = {
            "challan_id": self.generate_challan_id(),
            "evidence_id": evidence["evidence_id"],
            "plate_number": vehicle["license_plate"],
            "vehicle_type": vehicle.get("vehicle_type"),
            "violation_type": primary["type"],
            "fine_amount": sum(o["amount"] for o in offences),
            "confidence": primary["confidence"],
            "timestamp": evidence.get("timestamp") or now,  # when the offence was recorded
            "created_at": now,
            "location": location,
            "registered_at": registered_at,
            "camera_id": evidence.get("camera_id"),
            "status": status,
            "offences": offences,
        }
        pdf_path = self.generate_pdf(challan, evidence)
        challan["pdf_path"] = f"/outputs/challans/{Path(pdf_path).name}"
        self.db.insert_challan(challan)
        logger.info(
            f"Created challan {challan['challan_id']} ({status}) for {challan['plate_number']}: "
            f"{len(offences)} offence(s), Rs. {_rupees(challan['fine_amount'])}"
        )
        return challan

    def evaluate_evidence(self, evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Automatic challan after a detection.
        Needs a readable plate. Strongest violation >= 85% -> GENERATED,
        >= 70% -> REVIEW_REQUIRED, otherwise no challan.
        """
        vehicle = self._target_vehicle(evidence)
        if not vehicle:
            return None
        best = max(float(v.get("confidence") or 0) for v in vehicle["violations"])
        if best >= AUTO_THRESHOLD:
            status = "GENERATED"
        elif best >= REVIEW_THRESHOLD:
            status = "REVIEW_REQUIRED"
        else:
            return None
        return self.build_challan(evidence, vehicle, status)

    # ── PDF ────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_evidence_file(web_path: Optional[str], evidence_id: Optional[str], default_name: str) -> Optional[Path]:
        """Map a web path like /evidence/TVD-.../original.jpg to the file on disk."""
        candidates = []
        if web_path:
            rel = str(web_path).replace("\\", "/").lstrip("/")
            if rel.startswith("evidence/"):
                candidates.append(EVIDENCE_DIR / rel[len("evidence/"):])
            elif rel.startswith("outputs/"):
                candidates.append(INFERENCE_OUTPUTS_DIR / rel[len("outputs/"):])
        if evidence_id:
            candidates.append(EVIDENCE_DIR / evidence_id / default_name)
        for p in candidates:
            if p.is_file():
                return p
        return None

    @staticmethod
    def _fit_image(path: Optional[Path], max_w: float, max_h: float):
        if not path:
            return None
        try:
            iw, ih = ImageReader(str(path)).getSize()
            scale = min(max_w / iw, max_h / ih)
            return Image(str(path), width=iw * scale, height=ih * scale)
        except Exception as e:
            logger.error(f"Could not embed {path} in challan PDF: {e}")
            return None

    def generate_pdf(self, challan: Dict[str, Any], evidence: Dict[str, Any]) -> str:
        """Render the e-challan notice and return its file path."""
        challan_id = challan["challan_id"]
        pdf_path = self.challan_dir / f"{challan_id}.pdf"
        offences = challan.get("offences") or self.build_offences(
            [{"type": challan.get("violation_type"), "confidence": challan.get("confidence")}]
        )

        issued = _to_ist(challan.get("created_at")) or datetime.now(IST)
        pay_by = issued + timedelta(days=CHALLAN_PAYMENT_DAYS)
        verify_url = f"{CHALLAN_VERIFY_URL.rstrip('/')}/verify/challan/{challan_id}"

        # ── Text styles ──
        base = ParagraphStyle("base", fontName="Helvetica", fontSize=9, leading=12, textColor=INK)
        small = ParagraphStyle("small", parent=base, fontSize=7.8, leading=10, textColor=MUTED)
        label = ParagraphStyle("label", parent=base, fontSize=7.8, leading=10, textColor=MUTED)
        value = ParagraphStyle("value", parent=base, fontName="Helvetica-Bold", fontSize=9.5, leading=12)
        h2 = ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=10.5, leading=14, spaceBefore=4)
        cell = ParagraphStyle("cell", parent=base, fontSize=8.6, leading=11)
        cell_r = ParagraphStyle("cell_r", parent=cell, alignment=TA_RIGHT)
        cell_head = ParagraphStyle("cell_head", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
        cell_head_r = ParagraphStyle("cell_head_r", parent=cell_head, alignment=TA_RIGHT)

        page_w, page_h = A4
        margin = 15 * mm
        content_w = page_w - 2 * margin

        def section_title(text: str):
            return Paragraph(text.upper(), ParagraphStyle(
                "sec", parent=h2, fontSize=8.5, textColor=SIGN, spaceBefore=10, spaceAfter=4,
            ))

        story: List[Any] = []

        # ── Challan particulars + QR ──
        qr_img = qrcode.make(verify_url, box_size=4, border=1)
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format="PNG")
        qr_buf.seek(0)
        qr = Image(qr_buf, width=28 * mm, height=28 * mm)

        def kv(k, v):
            return [Paragraph(k, label), Paragraph(v, value)]

        place = challan.get("location") or CHALLAN_CITY
        if challan.get("camera_id"):
            place = f"{place} (camera {challan['camera_id']})"

        particulars = Table(
            [
                kv("Challan No.", challan_id) + kv("Date of challan", _fmt_date(issued)),
                kv("Date &amp; time of offence", _fmt_dt(challan.get("timestamp"))) + kv("Status", STATUS_TEXT.get(challan.get("status"), challan.get("status") or "-")),
                kv("Place of offence", place) + kv("Evidence ID", challan.get("evidence_id") or "-"),
                kv("Detected by", "AI traffic camera system") + kv("Detection confidence", f"{float(challan.get('confidence') or 0) * 100:.1f}%"),
            ],
            colWidths=[25 * mm, 50 * mm, 28 * mm, 41 * mm],
        )
        particulars.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ]))
        qr_block = Table([[qr], [Paragraph("Scan to verify this challan", ParagraphStyle("qrc", parent=small, alignment=1))]],
                         colWidths=[34 * mm])
        qr_block.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        top = Table([[particulars, qr_block]], colWidths=[content_w - 36 * mm, 36 * mm])
        top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(top)

        # ── Vehicle ──
        story.append(section_title("Vehicle details"))
        registered_rto = challan.get("registered_at")
        if registered_rto is None:
            rto = lookup_rto(challan.get("plate_number"))
            registered_rto = f"{rto['place']} (RTO {rto['display_code']})" if rto else None
        plate_para = Paragraph(
            _plate_display(challan.get("plate_number")),
            ParagraphStyle("plate", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=1),
        )
        plate_box = Table([[plate_para]], colWidths=[58 * mm], rowHeights=[11 * mm])
        plate_box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.6, INK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ]))
        vehicle = Table(
            [
                [Paragraph("Registration No.", label), Paragraph("Vehicle class", label), Paragraph("Registered owner", label)],
                [plate_box,
                 Paragraph(VEHICLE_CLASS.get(challan.get("vehicle_type"), (challan.get("vehicle_type") or "-").replace("_", " ").title()), value),
                 Paragraph("Not linked. Owner lookup from vehicle registration records is not part of this demo.", cell)],
                [Paragraph(
                    f"Registering authority: <b>{registered_rto}</b>" if registered_rto
                    else "Registering authority: not found in the RTO list for this plate", small), "", ""],
            ],
            colWidths=[64 * mm, 50 * mm, content_w - 114 * mm],
        )
        vehicle.setStyle(TableStyle([
            ("SPAN", (0, 2), (-1, 2)),
            ("TOPPADDING", (0, 2), (-1, 2), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ]))
        story.append(vehicle)

        # ── Offences ──
        story.append(section_title("Offence details"))
        rows = [[
            Paragraph("Sl.", cell_head),
            Paragraph("Offence", cell_head),
            Paragraph("Section (MV Act)", cell_head),
            Paragraph("Penalty (Rs.)", cell_head_r),
            Paragraph("Remarks", cell_head),
        ]]
        any_court = False
        for i, o in enumerate(offences, 1):
            offence_text = o["offence"]
            if o.get("count", 1) > 1 and o["type"] == "Helmet Non Compliance":
                offence_text += f" ({o['count']} riders)"
            remarks = o.get("note") or ""
            amount = _rupees(o["amount"])
            if o.get("court"):
                any_court = True
                amount = f"{amount}*"
            remarks = (remarks + "<br/>" if remarks else "") + f"<font color='#5A636E'>AI confidence {o['confidence'] * 100:.1f}%</font>"
            rows.append([
                Paragraph(str(i), cell),
                Paragraph(offence_text, cell),
                Paragraph(f"Sec. {o['section']}", cell),
                Paragraph(amount, cell_r),
                Paragraph(remarks, cell),
            ])
        total = sum(o["amount"] for o in offences)
        rows.append([
            "", Paragraph("<b>Total penalty</b>", cell), "",
            Paragraph(f"<b>{_rupees(total)}{'*' if any_court else ''}</b>", cell_r), "",
        ])
        offence_table = Table(rows, colWidths=[9 * mm, 66 * mm, 30 * mm, 24 * mm, content_w - 129 * mm], repeatRows=1)
        offence_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BAND),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 1), (-1, -2), 0.4, RULE),
            ("BACKGROUND", (0, -1), (-1, -1), TINT),
            ("LINEABOVE", (0, -1), (-1, -1), 0.8, INK),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(offence_table)
        if any_court:
            story.append(Spacer(1, 3))
            story.append(Paragraph(
                "* Court challan. The amount shown is the minimum; the final penalty is decided by the court.", small,
            ))

        # ── Evidence ──
        orig = self._resolve_evidence_file(
            evidence.get("image_path") or evidence.get("original_image_path"), challan.get("evidence_id"), "original.jpg")
        annot = self._resolve_evidence_file(evidence.get("annotated_path"), challan.get("evidence_id"), "annotated.jpg")
        img_w = (content_w - 6 * mm) / 2
        pics = [self._fit_image(orig, img_w, 62 * mm), self._fit_image(annot, img_w, 62 * mm)]
        if any(pics):
            ev = Table(
                [
                    [pics[0] or Paragraph("Photo not available", small), pics[1] or Paragraph("Photo not available", small)],
                    [Paragraph("Photograph as captured", small), Paragraph("Detections marked by the system", small)],
                ],
                colWidths=[img_w + 3 * mm, img_w + 3 * mm],
            )
            ev.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, 0), TINT),
                ("TOPPADDING", (0, 0), (-1, 0), 4),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(KeepTogether([section_title("Photographic evidence"), ev]))

        # ── Payment and instructions ──
        steps = [
            f"Pay the penalty within <b>{CHALLAN_PAYMENT_DAYS} days</b> of the date of challan, that is by <b>{_fmt_date(pay_by)}</b>, quoting Challan No. <b>{challan_id}</b>.",
            "Payment can be made at the e-challan payment counter of the issuing traffic authority, or through its authorised online payment service.",
            "If the penalty is not paid within this time, the challan may be forwarded to the court for disposal.",
            "If you believe this challan is wrong, you may contest it before the issuing authority with this notice and any supporting proof.",
        ]
        if any(o["type"] in ("Helmet Non Compliance", "Triple Riding") for o in offences):
            steps.append("For helmet and triple-riding offences the licensing authority may disqualify the driving licence for 3 months.")
        steps_table = Table(
            [[Paragraph(f"{i}.", cell), Paragraph(t, cell)] for i, t in enumerate(steps, 1)],
            colWidths=[6 * mm, content_w - 16 * mm],
        )
        steps_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        pay_box = Table([[steps_table]], colWidths=[content_w])
        pay_box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, RULE),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFBFC")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(KeepTogether([section_title("How to pay or contest"), pay_box]))

        # ── Page furniture: header band, demo watermark, footer ──
        def decorate(canv, doc):
            canv.saveState()
            band_h = 25 * mm
            canv.setFillColor(BAND)
            canv.rect(0, page_h - band_h, page_w, band_h, fill=1, stroke=0)
            canv.setFillColor(colors.HexColor("#E0A526"))
            canv.rect(0, page_h - band_h, page_w, 1.4 * mm, fill=1, stroke=0)
            canv.setFillColor(colors.white)
            canv.setFont("Helvetica-Bold", 13)
            canv.drawString(margin, page_h - 11 * mm, CHALLAN_AUTHORITY)
            canv.setFont("Helvetica", 8.5)
            canv.setFillColor(colors.HexColor("#C9D3E0"))
            canv.drawString(margin, page_h - 16 * mm, f"{CHALLAN_CITY}  |  Notice of traffic violation under the Motor Vehicles Act, 1988")
            canv.setFillColor(colors.white)
            canv.setFont("Helvetica-Bold", 20)
            canv.drawRightString(page_w - margin, page_h - 12.5 * mm, "e-CHALLAN")
            canv.setFont("Helvetica", 8)
            canv.setFillColor(colors.HexColor("#C9D3E0"))
            canv.drawRightString(page_w - margin, page_h - 17.5 * mm, f"No. {challan_id}")

            # Demo watermark
            canv.setFillColor(colors.Color(0.70, 0.15, 0.12, alpha=0.08))
            canv.setFont("Helvetica-Bold", 46)
            canv.translate(page_w / 2, page_h / 2 - 20 * mm)
            canv.rotate(32)
            canv.drawCentredString(0, 0, "DEMO - NOT AN OFFICIAL CHALLAN")
            canv.restoreState()

            canv.saveState()
            canv.setStrokeColor(RULE)
            canv.line(margin, 16 * mm, page_w - margin, 16 * mm)
            canv.setFont("Helvetica", 7.2)
            canv.setFillColor(MUTED)
            canv.drawString(margin, 11.5 * mm, "This is a computer-generated notice and does not require a signature.")
            canv.setFillColor(RED)
            canv.drawString(margin, 8 * mm, "Generated by Violation Desk, an AI-assisted student project. For demonstration only; not valid as an official challan.")
            canv.setFillColor(MUTED)
            canv.drawRightString(page_w - margin, 11.5 * mm, f"Page {doc.page}")
            canv.restoreState()

        doc = SimpleDocTemplate(
            str(pdf_path), pagesize=A4,
            leftMargin=margin, rightMargin=margin, topMargin=31 * mm, bottomMargin=21 * mm,
            title=f"e-Challan {challan_id}", author=CHALLAN_AUTHORITY, subject="Traffic violation notice (demo)",
        )
        doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
        return str(pdf_path)
