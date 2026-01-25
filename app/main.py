"""FastAPI application entrypoint."""
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.db import engine
from app.ingest import router as ingest_router
from app.infer import router as infer_router
from app.reports import router as reports_router
from app.keys import router as keys_router
from app.recommendations import router as recommendations_router
from app.experiments import router as experiments_router
from app.schemas import HealthResponse
from app.settings import get_settings

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CLI Analytics",
    description="Workflow/Outcome Intelligence for CLI Tools",
    version="0.1.0",
)

# CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest_router, tags=["Ingestion"])
app.include_router(infer_router, tags=["Inference"])
app.include_router(reports_router, tags=["Reports"])
app.include_router(keys_router, tags=["API Keys"])
app.include_router(recommendations_router, tags=["Recommendations"])
app.include_router(experiments_router, tags=["Experiments"])


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    db_status = "unhealthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
    )


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "CLI Analytics",
        "version": "0.1.0",
        "docs": "/docs",
        "dashboard": "/dashboard",
    }


@app.get("/dashboard")
def dashboard():
    """Serve the dashboard."""
    dashboard_path = Path(__file__).parent.parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"error": "Dashboard not found"}
