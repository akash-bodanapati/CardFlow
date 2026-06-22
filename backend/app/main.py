import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import config
from app.routers import chat, sessions

# Configure structured system-wide logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("cardflow")
logger.info("Initializing CardFlow API server")

app = FastAPI(
    title="CardFlow API",
    description="API for Visiting Card Digitization & Voice Notes Orchestrator",
    version="1.0.0",
)

# Parse allowed origins from configuration
origins = [
    origin.strip()
    for origin in config.cors_allowed_origins.split(",")
    if origin.strip()
]
if not origins:
    origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(chat.router, prefix="/api/sessions", tags=["chat"])

# Mount static files folder for local audio storage
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def read_root():
    """Welcome endpoint for API verification."""
    return {"message": "Welcome to CardFlow API"}


@app.get("/health")
def health_check():
    """Health check endpoint for container uptime and readiness monitoring."""
    return {"status": "ok"}
