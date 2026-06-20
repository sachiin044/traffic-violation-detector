"""
Traffic Violation Detection System — FastAPI Application.

Entry point: uvicorn app:app --host 0.0.0.0 --port 8000
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import HOST, PORT, LOG_LEVEL, LOG_FORMAT, EVIDENCE_DIR, INFERENCE_OUTPUTS_DIR
from services.pipeline import InferencePipeline
from routers import predict, challan

# ── Logging Setup ────────────────────────────────────────────────────────
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# ── Pipeline Singleton ───────────────────────────────────────────────────
pipeline = InferencePipeline()


# ── Lifespan (startup / shutdown) ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models at startup, connect DB, cleanup at shutdown."""
    logger.info("Starting Traffic Violation Detection System...")
    start = time.time()

    # Load all models once
    pipeline.load_models()

    # Connect to MongoDB
    try:
        pipeline.db.connect()
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")

    # Inject pipeline into router
    predict.set_pipeline(pipeline)

    elapsed = time.time() - start
    logger.info(f"System ready in {elapsed:.1f}s")

    yield  # ← app is running

    # Shutdown
    logger.info("Shutting down...")
    if pipeline.db:
        pipeline.db.close()
    logger.info("Cleanup complete.")


# ── FastAPI App ──────────────────────────────────────────────────────────
app = FastAPI(
    title="Traffic Violation Detection API",
    description=(
        "Automated Photo Identification and Classification for Traffic Violations "
        "using Computer Vision. Processes traffic images, detects vehicles and "
        "violations, extracts license plates via OCR, and generates annotated "
        "evidence images."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow all for hackathon demo) ──────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routes ─────────────────────────────────────────────────────
app.include_router(predict.router, tags=["Inference"])
app.include_router(challan.router, tags=["Challan"])

app.mount("/evidence", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence")
app.mount("/outputs", StaticFiles(directory=str(INFERENCE_OUTPUTS_DIR)), name="outputs")


# ── Root Redirect ────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to API docs."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


# ── CLI Entrypoint ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level=LOG_LEVEL.lower(),
    )
