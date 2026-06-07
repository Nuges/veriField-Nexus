"""
=============================================================================
VeriField Nexus — Backend API Main Entrypoint
=============================================================================
Defines the FastAPI application instance, registers routes, and handles
cross-origin (CORS) resource sharing middleware.
=============================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes import health, verify

app = FastAPI(
    title="VeriField Nexus API",
    description="Verification Infrastructure for Real-World Climate Assets on Solana",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Set up CORS middleware to support dashboard and mobile web requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router, prefix="/api/v1")
app.include_router(verify.router, prefix="/api/v1")
