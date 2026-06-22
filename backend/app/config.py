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
    cors_allowed_origins: str = "http://localhost:5173"
    public_base_url: str = ""
    env: str = "development"


    class Config:
        env_file = ".env"


config = Settings()
