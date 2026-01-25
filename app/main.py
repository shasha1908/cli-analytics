"""FastAPI application entrypoint."""
import logging
import sys

from fastapi import FastAPI
from sqlalchemy import text

from app.db import engine
from app.ingest import router as ingest_router
from app.infer import router as infer_router
from app.reports import router as reports_router
from app.keys import router as keys_router
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

# Include routers
app.include_router(ingest_router, tags=["Ingestion"])
app.include_router(infer_router, tags=["Inference"])
app.include_router(reports_router, tags=["Reports"])
app.include_router(keys_router, tags=["API Keys"])


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
    }
