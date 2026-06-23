import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.config import Settings
from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_storage_fallback_to_local():
    """Verify that StorageService falls back to local storage when cloud credentials are empty."""
    custom_config = Settings(
        supabase_url="",
        supabase_key="",
        cloudinary_cloud_name="",
        cloudinary_upload_preset="",
    )

    with patch("app.services.storage_service.config", custom_config):
        service = StorageService()
        
        # Mock file write
        from unittest.mock import mock_open
        with patch("builtins.open", mock_open()) as mock_open_file, \
             patch("os.makedirs") as mock_makedirs, \
             patch("os.path.exists", return_value=True):
            
            url = await service.upload_audio("test-session-fallback", b"fake_wav_bytes")
            
            assert "test-session-fallback.wav" in url
            mock_makedirs.assert_called_with("uploads", exist_ok=True)
