"""
Governance OS - FastAPI Application

Main entry point for the deterministic governance kernel API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import engine, Base
from core.api import signals, evaluations, exceptions, decisions, evidence, policies, stats, replay

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Policy-driven coordination layer for high-stakes professional work",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(signals.router, prefix=settings.api_v1_prefix)
app.include_router(evaluations.router, prefix=settings.api_v1_prefix)
app.include_router(exceptions.router, prefix=settings.api_v1_prefix)
app.include_router(decisions.router, prefix=settings.api_v1_prefix)
app.include_router(evidence.router, prefix=settings.api_v1_prefix)
app.include_router(policies.router, prefix=settings.api_v1_prefix)
app.include_router(stats.router, prefix=settings.api_v1_prefix)
app.include_router(replay.router, prefix=settings.api_v1_prefix)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Create tables (in development - use Alembic in production)
# Base.metadata.create_all(bind=engine)
