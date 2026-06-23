from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or .env file."""

    google_application_credentials: str = "./service-account.json"
    google_sheet_id: str = ""
    mongo_uri: str = ""
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    manager_phone_number: str = ""
    gemini_api_key: str = ""
    gemini_ocr_key: str = ""
    gemini_audio_key: str = ""
    gemini_enrichment_key: str = ""
    cors_allowed_origins: str = "http://localhost:5173"
    public_base_url: str = ""
    env: str = "development"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "cardflow"
    cloudinary_cloud_name: str = ""
    cloudinary_upload_preset: str = ""


    class Config:
        env_file = ".env"


config = Settings()

