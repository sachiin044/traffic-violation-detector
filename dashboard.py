"""
Traffic Violation Detection System — Streamlit Dashboard
Run: streamlit run dashboard.py
"""

import streamlit as st
import cv2
import numpy as np
import time
import json
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image
import io

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Traffic Violation Detection System",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Global */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Hero header */
    .hero-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .hero-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 20% 50%, rgba(59,130,246,0.08) 0%, transparent 60%);
        pointer-events: none;
    }
    .hero-header h1 {
        color: #f1f5f9;
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0 0 0.3rem 0;
        letter-spacing: -0.5px;
    }
    .hero-header p {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.1);
        transform: translateY(-2px);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3b82f6, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.1;
    }
    .metric-value.success { background: linear-gradient(135deg, #22c55e, #4ade80); -webkit-background-clip: text; }
    .metric-value.warning { background: linear-gradient(135deg, #f59e0b, #fbbf24); -webkit-background-clip: text; }
    .metric-value.danger  { background: linear-gradient(135deg, #ef4444, #f87171); -webkit-background-clip: text; }
    .metric-label {
        color: #94a3b8;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.4rem;
    }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .badge-generated { background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
    .badge-review    { background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
    .badge-issued    { background: rgba(139,92,246,0.2); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }
    .badge-paid      { background: rgba(34,197,94,0.2);  color: #4ade80; border: 1px solid rgba(34,197,94,0.3);  }
    .badge-disputed  { background: rgba(239,68,68,0.2);  color: #f87171; border: 1px solid rgba(239,68,68,0.3);  }

    /* Section headers */
    .section-header {
        color: #e2e8f0;
        font-size: 1.3rem;
        font-weight: 700;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #334155;
    }

    /* Info box */
    .info-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
    }
    .info-box .label { color: #94a3b8; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .info-box .value { color: #f1f5f9; font-size: 1rem; font-weight: 600; }

    /* Violation tag */
    .violation-tag {
        display: inline-block;
        background: rgba(239,68,68,0.15);
        color: #f87171;
        border: 1px solid rgba(239,68,68,0.3);
        border-radius: 6px;
        padding: 0.2rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.15rem;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)


# ── Pipeline Loader (cached) ────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_pipeline():
    """Load the full inference pipeline once."""
    from services.pipeline import InferencePipeline
    pipe = InferencePipeline()
    pipe.load_models()
    return pipe


def get_db():
    """Get the MongoDB connection from the pipeline."""
    pipe = load_pipeline()
    return pipe.db


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0;">
        <span style="font-size: 2.5rem;">🚦</span>
        <h2 style="color: #f1f5f9; margin: 0.3rem 0 0 0; font-size: 1.1rem; font-weight: 700;">
            TrafficVD System
        </h2>
        <p style="color: #64748b; font-size: 0.75rem; margin: 0;">AI-Powered Enforcement</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "📷 Detect Violations",
            "🔍 Evidence Explorer",
            "📋 Challan Manager",
            "📊 Analytics",
            "⚙️ System Health",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("© 2026 TrafficVD • Hackathon MVP")


# ── Helper Functions ─────────────────────────────────────────────────────────
def render_metric(value, label, color_class=""):
    cls = f"metric-value {color_class}" if color_class else "metric-value"
    st.markdown(f"""
    <div class="metric-card">
        <div class="{cls}">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def get_status_badge(status):
    status = (status or "").upper()
    badge_map = {
        "GENERATED": "badge-generated",
        "REVIEW_REQUIRED": "badge-review",
        "ISSUED": "badge-issued",
        "PAID": "badge-paid",
        "DISPUTED": "badge-disputed",
    }
    cls = badge_map.get(status, "badge-generated")
    return f'<span class="badge {cls}">{status}</span>'


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown("""
    <div class="hero-header">
        <h1>🚦 Traffic Violation Detection Dashboard</h1>
        <p>Real-time overview of AI-powered traffic enforcement analytics</p>
    </div>
    """, unsafe_allow_html=True)

    # Load stats
    try:
        db = get_db()
        summary = db.get_dashboard_summary() if db.collection else {}
        enforcement = db.get_enforcement_demo_stats() if db.challans else {}
    except Exception as e:
        st.warning(f"Could not load stats from database: {e}")
        summary = {}
        enforcement = {}

    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        render_metric(summary.get("total", 0), "Total Evidence")
    with col2:
        render_metric(summary.get("helmet", 0), "Helmet Violations", "danger")
    with col3:
        render_metric(summary.get("seatbelt", 0), "Seatbelt Violations", "warning")
    with col4:
        render_metric(summary.get("triple_riding", 0), "Triple Riding", "danger")
    with col5:
        render_metric(summary.get("red_light", 0), "Red Light", "warning")

    st.markdown("")

    # Enforcement stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric(enforcement.get("total_challans", 0), "Total Challans")
    with col2:
        render_metric(enforcement.get("issued", 0), "Challans Issued", "success")
    with col3:
        render_metric(enforcement.get("review_required", 0), "Needs Review", "warning")
    with col4:
        fines = enforcement.get("estimated_fines", 0)
        render_metric(f"₹{fines:,}", "Estimated Fines", "success")

    st.markdown("")

    # Recent evidence & top offenders side by side
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown('<div class="section-header">📋 Recent Evidence</div>', unsafe_allow_html=True)
        try:
            if db.collection:
                recent = db.search_evidence(limit=8)
                records = recent.get("records", [])
                if records:
                    for rec in records:
                        violations = rec.get("violations", [])
                        viol_tags = " ".join(
                            [f'<span class="violation-tag">{v}</span>' for v in violations]
                        )
                        plate = rec.get("plate_number", "N/A") or "N/A"
                        ts = rec.get("timestamp", "")[:19]
                        conf = rec.get("confidence", 0)

                        st.markdown(f"""
                        <div class="info-box" style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div class="label">{rec.get('evidence_id', 'N/A')} • {ts}</div>
                                <div class="value" style="margin-top: 0.2rem;">🚗 {plate} &nbsp; <span style="color:#94a3b8; font-size:0.8rem;">({conf*100:.0f}% conf)</span></div>
                                <div style="margin-top: 0.3rem;">{viol_tags}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No evidence records found yet. Upload an image to get started!")
        except Exception as e:
            st.error(f"Could not load evidence: {e}")

    with col_right:
        st.markdown('<div class="section-header">🏆 Top Offenders</div>', unsafe_allow_html=True)
        try:
            if db.collection:
                top_plates = db.get_top_plates(limit=7)
                if top_plates:
                    for i, tp in enumerate(top_plates, 1):
                        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"#{i}"
                        st.markdown(f"""
                        <div class="info-box" style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-size: 1.2rem; margin-right: 0.5rem;">{medal}</span>
                                <span class="value" style="letter-spacing: 1px;">{tp['plate_number']}</span>
                            </div>
                            <span style="color: #f87171; font-weight: 700;">{tp['offenses']} offenses</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No repeat offenders detected yet.")
        except Exception as e:
            st.error(f"Could not load top plates: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Detect Violations
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📷 Detect Violations":
    st.markdown("""
    <div class="hero-header">
        <h1>📷 Violation Detection</h1>
        <p>Upload a traffic image to detect vehicles, violations, and license plates</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload a traffic image",
        type=["jpg", "jpeg", "png", "bmp", "tiff"],
        help="Supported: JPEG, PNG, BMP, TIFF. Max 20MB.",
    )

    if uploaded_file:
        # Read image
        file_bytes = uploaded_file.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            st.error("Could not decode image. Please upload a valid image file.")
        else:
            col_orig, col_result = st.columns(2)

            with col_orig:
                st.markdown('<div class="section-header">📤 Original Image</div>', unsafe_allow_html=True)
                st.image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), use_container_width=True)

            # Run prediction
            with st.spinner("🔍 Running AI inference pipeline..."):
                start = time.time()
                pipe = load_pipeline()
                result = pipe.predict(image, save_annotated=True)
                elapsed = time.time() - start

            with col_result:
                st.markdown('<div class="section-header">🎯 Annotated Evidence</div>', unsafe_allow_html=True)
                if result.annotated_image_path:
                    # Load annotated image from disk
                    from config import EVIDENCE_DIR
                    ann_path = EVIDENCE_DIR / result.evidence_id / "annotated.jpg"
                    if ann_path.exists():
                        ann_img = cv2.imread(str(ann_path))
                        st.image(cv2.cvtColor(ann_img, cv2.COLOR_BGR2RGB), use_container_width=True)
                    else:
                        st.info("Annotated image not found on disk.")
                else:
                    st.success("✅ No violations detected in this image!")

            # Results summary
            st.markdown('<div class="section-header">📊 Detection Results</div>', unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                render_metric(result.total_vehicles, "Vehicles Detected")
            with col2:
                render_metric(result.total_violations, "Violations Found", "danger" if result.total_violations > 0 else "success")
            with col3:
                render_metric(f"{elapsed:.1f}s", "Processing Time")
            with col4:
                render_metric(result.evidence_id or "—", "Evidence ID")

            # Per-vehicle details
            if result.vehicles:
                st.markdown('<div class="section-header">🚗 Vehicle Details</div>', unsafe_allow_html=True)
                for v in result.vehicles:
                    with st.expander(f"Vehicle #{v.vehicle_id} — {v.vehicle_type.upper()}", expanded=True):
                        vc1, vc2, vc3 = st.columns(3)
                        with vc1:
                            st.markdown(f"**Type:** `{v.vehicle_type}`")
                            st.markdown(f"**License Plate:** `{v.license_plate or 'Not detected'}`")
                        with vc2:
                            st.markdown(f"**Plate Confidence:** `{v.plate_confidence*100:.1f}%`" if v.plate_confidence else "**Plate Confidence:** `N/A`")
                            st.markdown(f"**Violations:** `{len(v.violations)}`")
                        with vc3:
                            if v.violations:
                                for viol in v.violations:
                                    st.markdown(f"""
                                    <span class="violation-tag">{viol.type} ({viol.confidence*100:.0f}%)</span>
                                    """, unsafe_allow_html=True)
                            else:
                                st.success("No violations")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Evidence Explorer
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Evidence Explorer":
    st.markdown("""
    <div class="hero-header">
        <h1>🔍 Evidence Explorer</h1>
        <p>Browse and search all stored traffic violation evidence packages</p>
    </div>
    """, unsafe_allow_html=True)

    # Filters
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        plate_search = st.text_input("🔎 Search by plate number", placeholder="e.g., DL01AB1234")
    with col_f2:
        violation_filter = st.selectbox("Filter by violation", [
            "", "Helmet Non Compliance", "Seatbelt Non Compliance",
            "Triple Riding", "Red Light Violation", "Illegal Parking"
        ])
    with col_f3:
        limit = st.number_input("Results", min_value=5, max_value=200, value=25)

    try:
        db = get_db()
        if db.collection:
            results = db.search_evidence(
                limit=limit,
                plate_number=plate_search or None,
                violation_type=violation_filter or None,
            )
            records = results.get("records", [])
            total = results.get("total", 0)

            st.markdown(f"**Showing {len(records)} of {total} records**")

            if records:
                for rec in records:
                    with st.expander(
                        f"📁 {rec.get('evidence_id', 'N/A')} — "
                        f"🚗 {rec.get('plate_number', 'N/A') or 'No Plate'} — "
                        f"{rec.get('timestamp', '')[:19]}"
                    ):
                        ec1, ec2 = st.columns([1, 2])
                        with ec1:
                            # Try to show thumbnail
                            from config import EVIDENCE_DIR
                            eid = rec.get("evidence_id", "")
                            thumb = EVIDENCE_DIR / eid / "thumbnail.jpg"
                            if thumb.exists():
                                st.image(str(thumb), caption="Thumbnail", use_container_width=True)
                            else:
                                st.info("No thumbnail available")
                        with ec2:
                            violations = rec.get("violations", [])
                            viol_tags = " ".join(
                                [f'<span class="violation-tag">{v}</span>' for v in violations]
                            )
                            st.markdown(f"""
                            <div class="info-box">
                                <div><span class="label">Plate:</span> <span class="value">{rec.get('plate_number', 'N/A') or 'N/A'}</span></div>
                                <div><span class="label">Confidence:</span> <span class="value">{rec.get('confidence', 0)*100:.1f}%</span></div>
                                <div><span class="label">Vehicle Type:</span> <span class="value">{rec.get('vehicle_type', 'N/A')}</span></div>
                                <div><span class="label">Processing Time:</span> <span class="value">{rec.get('processing_time_ms', 0):.0f}ms</span></div>
                                <div style="margin-top: 0.5rem;"><span class="label">Violations:</span> {viol_tags}</div>
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.info("No evidence records found matching your criteria.")
        else:
            st.warning("Database not connected. Start the backend to view evidence.")
    except Exception as e:
        st.error(f"Error loading evidence: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Challan Manager
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Challan Manager":
    st.markdown("""
    <div class="hero-header">
        <h1>📋 Challan Manager</h1>
        <p>View, filter, and manage traffic violation challans</p>
    </div>
    """, unsafe_allow_html=True)

    # Filters
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        plate_search = st.text_input("🔎 Search plate", placeholder="e.g., UP65AB1234", key="challan_plate")
    with col_f2:
        status_filter = st.selectbox("Status filter", [
            "", "GENERATED", "REVIEW_REQUIRED", "ISSUED", "PAID", "DISPUTED"
        ])
    with col_f3:
        ch_limit = st.number_input("Limit", min_value=5, max_value=200, value=25, key="ch_limit")

    try:
        db = get_db()
        if db.challans:
            results = db.search_challans(
                limit=ch_limit,
                status=status_filter or None,
                plate_number=plate_search or None,
            )
            records = results.get("records", [])
            total = results.get("total", 0)

            st.markdown(f"**Showing {len(records)} of {total} challans**")

            if records:
                for ch in records:
                    status_badge = get_status_badge(ch.get("status", ""))
                    fine = ch.get("fine_amount", 0)
                    conf = ch.get("confidence", 0)

                    with st.expander(
                        f"🧾 {ch.get('challan_id', 'N/A')} — "
                        f"🚗 {ch.get('plate_number', 'N/A')} — "
                        f"₹{fine}"
                    ):
                        cc1, cc2, cc3 = st.columns(3)
                        with cc1:
                            st.markdown(f"""
                            <div class="info-box">
                                <div><span class="label">Challan ID</span></div>
                                <div class="value">{ch.get('challan_id', 'N/A')}</div>
                                <div style="margin-top:0.5rem;"><span class="label">Evidence ID</span></div>
                                <div class="value" style="font-size:0.85rem;">{ch.get('evidence_id', 'N/A')}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with cc2:
                            st.markdown(f"""
                            <div class="info-box">
                                <div><span class="label">Violation</span></div>
                                <div><span class="violation-tag">{ch.get('violation_type', 'N/A')}</span></div>
                                <div style="margin-top:0.5rem;"><span class="label">Confidence</span></div>
                                <div class="value">{conf*100:.1f}%</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with cc3:
                            st.markdown(f"""
                            <div class="info-box">
                                <div><span class="label">Fine Amount</span></div>
                                <div class="value" style="color: #f59e0b;">₹{fine:,}</div>
                                <div style="margin-top:0.5rem;"><span class="label">Status</span></div>
                                <div>{status_badge}</div>
                            </div>
                            """, unsafe_allow_html=True)

                        # Status update
                        new_status = st.selectbox(
                            "Update Status",
                            ["", "GENERATED", "REVIEW_REQUIRED", "ISSUED", "PAID", "DISPUTED"],
                            key=f"status_{ch.get('challan_id', '')}",
                        )
                        if new_status:
                            if st.button(f"Update → {new_status}", key=f"btn_{ch.get('challan_id', '')}"):
                                db.update_challan_status(ch["challan_id"], new_status)
                                st.success(f"✅ Status updated to {new_status}")
                                st.rerun()
            else:
                st.info("No challans found. Process some images to generate challans automatically!")
        else:
            st.warning("Database not connected. Challans collection unavailable.")
    except Exception as e:
        st.error(f"Error loading challans: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Analytics
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Analytics":
    st.markdown("""
    <div class="hero-header">
        <h1>📊 Analytics & Trends</h1>
        <p>Violation trends, hotspot analysis, and enforcement metrics</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        db = get_db()

        # Violation breakdown
        st.markdown('<div class="section-header">📈 Violation Type Breakdown</div>', unsafe_allow_html=True)
        if db.collection:
            summary = db.get_dashboard_summary()
            violation_data = {
                "Helmet": summary.get("helmet", 0),
                "Seatbelt": summary.get("seatbelt", 0),
                "Triple Riding": summary.get("triple_riding", 0),
                "Red Light": summary.get("red_light", 0),
                "Illegal Parking": summary.get("illegal_parking", 0),
            }

            # Display as bar chart
            import pandas as pd
            df = pd.DataFrame(
                list(violation_data.items()),
                columns=["Violation Type", "Count"]
            )
            if df["Count"].sum() > 0:
                st.bar_chart(df.set_index("Violation Type"), color="#3b82f6")
            else:
                st.info("No violation data available yet.")

        # Daily trends
        st.markdown('<div class="section-header">📆 Daily Trends</div>', unsafe_allow_html=True)
        if db.collection:
            trends = db.get_daily_trends()
            if trends:
                import pandas as pd
                df_trends = pd.DataFrame(trends)
                if "date" in df_trends.columns:
                    df_trends = df_trends.set_index("date")
                    st.line_chart(df_trends)
                else:
                    st.info("No trend data available.")
            else:
                st.info("No daily trend data available yet.")

        # Enforcement stats
        st.markdown('<div class="section-header">⚖️ Enforcement Summary</div>', unsafe_allow_html=True)
        if db.challans:
            enforcement = db.get_enforcement_demo_stats()
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                render_metric(enforcement.get("total_challans", 0), "Total Challans")
            with col2:
                render_metric(enforcement.get("generated", 0), "Generated")
            with col3:
                render_metric(enforcement.get("review_required", 0), "Under Review", "warning")
            with col4:
                render_metric(enforcement.get("issued", 0), "Issued", "success")
            with col5:
                render_metric(enforcement.get("disputed", 0), "Disputed", "danger")

        # Hotspots
        st.markdown('<div class="section-header">🗺️ Violation Hotspots</div>', unsafe_allow_html=True)
        if db.collection:
            hotspots = db.get_hotspots()
            if hotspots:
                for hs in hotspots:
                    st.markdown(f"""
                    <div class="info-box" style="display: flex; justify-content: space-between;">
                        <div>
                            <span class="label">📍 {hs.get('location', 'Unknown')}</span>
                            <span style="color:#64748b;"> (Camera: {hs.get('camera_id', 'N/A')})</span>
                        </div>
                        <span class="value" style="color: #f87171;">{hs.get('total_violations', 0)} violations</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No hotspot data available. Process video feeds to generate location-based analytics.")

    except Exception as e:
        st.error(f"Error loading analytics: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: System Health
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ System Health":
    st.markdown("""
    <div class="hero-header">
        <h1>⚙️ System Health</h1>
        <p>Monitor AI models, GPU status, and system performance</p>
    </div>
    """, unsafe_allow_html=True)

    pipe = load_pipeline()

    # GPU Status
    st.markdown('<div class="section-header">🖥️ Hardware</div>', unsafe_allow_html=True)
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if gpu_available else "N/A"
    except Exception:
        gpu_available = False
        gpu_name = "N/A"

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric("✅ Yes" if gpu_available else "❌ No", "GPU Available", "success" if gpu_available else "danger")
    with col2:
        render_metric(gpu_name, "GPU Name")
    with col3:
        render_metric(f"{pipe.uptime_seconds:.0f}s", "Pipeline Uptime")

    # Model status
    st.markdown('<div class="section-header">🤖 Loaded Models</div>', unsafe_allow_html=True)
    model_info = pipe.get_model_info()

    for m in model_info:
        status_icon = "🟢" if m["status"] == "loaded" else "🔴"
        with st.expander(f"{status_icon} {m['name'].upper()} — {m['status']}", expanded=False):
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown(f"""
                <div class="info-box">
                    <div><span class="label">Weight Path</span></div>
                    <div class="value" style="font-size: 0.8rem; word-break: break-all;">{m['weight_path']}</div>
                </div>
                """, unsafe_allow_html=True)
            with mc2:
                st.markdown(f"""
                <div class="info-box">
                    <div><span class="label">Confidence Threshold</span></div>
                    <div class="value">{m['confidence_threshold']}</div>
                    <div style="margin-top: 0.5rem;"><span class="label">Classes</span></div>
                    <div class="value" style="font-size: 0.8rem;">{json.dumps(m['class_names'], indent=0)}</div>
                </div>
                """, unsafe_allow_html=True)

    # Database status
    st.markdown('<div class="section-header">🗄️ Database</div>', unsafe_allow_html=True)
    db = get_db()
    db_connected = db.client is not None and db.collection is not None
    col1, col2 = st.columns(2)
    with col1:
        render_metric("✅ Connected" if db_connected else "❌ Disconnected", "MongoDB Status", "success" if db_connected else "danger")
    with col2:
        try:
            total_evidence = db.collection.count_documents({}) if db.collection else 0
            total_challans = db.challans.count_documents({}) if db.challans else 0
            render_metric(f"{total_evidence} / {total_challans}", "Evidence / Challans")
        except Exception:
            render_metric("N/A", "Evidence / Challans")
