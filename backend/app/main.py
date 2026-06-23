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

ocr_ok = bool(config.gemini_ocr_key or config.gemini_api_key)
audio_ok = bool(config.gemini_audio_key or config.gemini_api_key)
enrichment_ok = bool(config.gemini_enrichment_key or config.gemini_api_key)
sheets_ok = bool(config.google_sheet_id and os.path.exists(config.google_application_credentials))
whatsapp_ok = bool(config.whatsapp_token and config.whatsapp_phone_number_id and config.manager_phone_number)

if config.supabase_url and config.supabase_key:
    storage_provider = "Supabase Storage"
    storage_ok = True
elif config.cloudinary_cloud_name and config.cloudinary_upload_preset:
    storage_provider = "Cloudinary"
    storage_ok = True
else:
    storage_provider = "Local Storage"
    storage_ok = False

logger.info("Initializing CardFlow API server")
logger.info(f"{'✓' if ocr_ok else '✗'} OCR key configured")
if not ocr_ok:
    logger.warning("  WARNING: OCR feature will be disabled (Missing GEMINI_OCR_KEY and fallback GEMINI_API_KEY)")

logger.info(f"{'✓' if audio_ok else '✗'} Audio key configured")
if not audio_ok:
    logger.warning("  WARNING: Audio feature will be disabled (Missing GEMINI_AUDIO_KEY and fallback GEMINI_API_KEY)")

logger.info(f"{'✓' if enrichment_ok else '✗'} Enrichment key configured")
if not enrichment_ok:
    logger.warning("  WARNING: Enrichment feature will be disabled (Missing GEMINI_ENRICHMENT_KEY and fallback GEMINI_API_KEY)")

logger.info(f"{'✓' if sheets_ok else '✗'} Google Sheets configured")
if not sheets_ok:
    logger.warning("  WARNING: Google Sheets syncing will be disabled (Missing GOOGLE_SHEET_ID or credentials file)")

logger.info(f"{'✓' if whatsapp_ok else '✗'} WhatsApp configured")
if not whatsapp_ok:
    logger.warning("  WARNING: WhatsApp alerts will be disabled (Missing WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, or MANAGER_PHONE_NUMBER)")

logger.info(f"{'✓' if storage_ok else '✗'} Persistent Storage configured")
logger.info(f"  Active Storage Provider: {storage_provider}")
if not storage_ok:
    logger.warning("  WARNING: Persistent audio storage is NOT configured. Uploaded voice notes will be lost after redeploys or restarts.")

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


@app.get("/health/summary")
@app.get("/api/health/summary")
def health_summary():
    """Returns a health summary showing which features are configured, without leaking secrets."""
    return {
        "ocr": bool(config.gemini_ocr_key or config.gemini_api_key),
        "audio": bool(config.gemini_audio_key or config.gemini_api_key),
        "enrichment": bool(config.gemini_enrichment_key or config.gemini_api_key),
        "google_sheets": bool(config.google_sheet_id and os.path.exists(config.google_application_credentials)),
        "whatsapp": bool(config.whatsapp_token and config.whatsapp_phone_number_id and config.manager_phone_number),
        "storage": bool((config.supabase_url and config.supabase_key) or (config.cloudinary_cloud_name and config.cloudinary_upload_preset))
    }
