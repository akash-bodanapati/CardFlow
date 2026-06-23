import os
import logging
import httpx
from app.config import config

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.supabase_url = config.supabase_url.strip() if config.supabase_url else ""
        self.supabase_key = config.supabase_key.strip() if config.supabase_key else ""
        self.supabase_bucket = config.supabase_bucket.strip() if config.supabase_bucket else "cardflow"
        
        self.cloudinary_cloud_name = config.cloudinary_cloud_name.strip() if config.cloudinary_cloud_name else ""
        self.cloudinary_upload_preset = config.cloudinary_upload_preset.strip() if config.cloudinary_upload_preset else ""

    async def upload_audio(self, session_id: str, file_data: bytes) -> str:
        """
        Uploads audio to persistent storage (Supabase or Cloudinary) and returns a permanent URL.
        Falls back to local file storage if no cloud credentials are configured.
        """
        filename = f"{session_id}.wav"
        
        # 1. Supabase Storage
        if self.supabase_url and self.supabase_key:
            logger.info("StorageService: Attempting Supabase Storage upload...")
            upload_url = f"{self.supabase_url.rstrip('/')}/storage/v1/object/{self.supabase_bucket}/{filename}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "x-upsert": "true",
                "Content-Type": "audio/wav"
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(upload_url, headers=headers, content=file_data, timeout=30.0)
                    # If POST fails because it already exists (and upsert isn't allowed or failed), try PUT
                    if response.status_code not in (200, 201):
                        logger.info(f"POST failed with {response.status_code}, trying PUT...")
                        response = await client.put(upload_url, headers=headers, content=file_data, timeout=30.0)
                    
                    if response.status_code in (200, 201):
                        public_url = f"{self.supabase_url.rstrip('/')}/storage/v1/object/public/{self.supabase_bucket}/{filename}"
                        logger.info(f"StorageService: Supabase upload successful. Save path/url: {public_url}, Filename: {filename}")
                        # Verify upload immediately
                        verify_res = await client.head(public_url)
                        logger.info(f"StorageService: Verified object public existence. HEAD status: {verify_res.status_code}")
                        return public_url
                    else:
                        logger.error(f"StorageService: Supabase upload failed. status_code={response.status_code}, response={response.text}")
            except Exception as e:
                logger.exception("StorageService: Supabase upload failed with exception")

        # 2. Cloudinary
        elif self.cloudinary_cloud_name and self.cloudinary_upload_preset:
            logger.info("StorageService: Attempting Cloudinary upload...")
            upload_url = f"https://api.cloudinary.com/v1_1/{self.cloudinary_cloud_name}/upload"
            files = {
                "file": (filename, file_data, "audio/wav")
            }
            data = {
                "upload_preset": self.cloudinary_upload_preset,
                "public_id": session_id,
                "resource_type": "video"  # Cloudinary handles audio files under resource_type = video or auto
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(upload_url, files=files, data=data, timeout=30.0)
                    if response.status_code == 200:
                        res_json = response.json()
                        public_url = res_json.get("secure_url") or res_json.get("url")
                        logger.info(f"StorageService: Cloudinary upload successful. Save path/url: {public_url}, Filename: {filename}")
                        # Verify existence
                        verify_res = await client.head(public_url)
                        logger.info(f"StorageService: Verified object public existence. HEAD status: {verify_res.status_code}")
                        return public_url
                    else:
                        logger.error(f"StorageService: Cloudinary upload failed. status_code={response.status_code}, response={response.text}")
            except Exception as e:
                logger.exception("StorageService: Cloudinary upload failed with exception")

        # 3. Fallback to Local Disk
        logger.warning("StorageService: No valid cloud storage credentials. Falling back to local filesystem.")
        os.makedirs("uploads", exist_ok=True)
        local_path = f"uploads/{filename}"
        with open(local_path, "wb") as f:
            f.write(file_data)
        
        file_exists = os.path.exists(local_path)
        logger.info(f"StorageService: Local file save. Path: {local_path}, Filename: {filename}, Exists immediately after save: {file_exists}")
        
        # Construct public URL using public_base_url or fallback
        base_url = (config.public_base_url or "http://localhost:8000").rstrip("/")
        return f"{base_url}/uploads/{filename}"


storage_service = StorageService()
