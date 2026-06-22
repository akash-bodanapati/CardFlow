import asyncio
import json
import logging
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
logger = logging.getLogger(__name__)


class SheetsService:
    def __init__(self):
        self.sheet_id = config.google_sheet_id
        self.creds_path = config.google_application_credentials
        self._service = None

    def _get_service(self):
        if not self._service:
            logger.info(f"SheetsService: _get_service - credential path: '{self.creds_path}'")
            exists = os.path.exists(self.creds_path)
            logger.info(f"SheetsService: _get_service - credentials file exists: {exists}")
            if exists:
                try:
                    size = os.path.getsize(self.creds_path)
                    logger.info(f"SheetsService: _get_service - credentials file size: {size} bytes")
                except Exception as size_err:
                    logger.warning(f"SheetsService: Failed to get file size: {size_err}")

            if not exists:
                logger.error(f"SheetsService: Credentials not found at {self.creds_path}")
                return None

            try:
                logger.info("SheetsService: Loading credentials from file...")
                creds = service_account.Credentials.from_service_account_file(
                    self.creds_path, scopes=SCOPES
                )
                logger.info("SheetsService: Credentials loaded successfully.")
            except Exception as e:
                logger.exception("SheetsService: Exception in from_service_account_file")
                raise e

            try:
                logger.info("SheetsService: Building sheets v4 service (cache_discovery=False)...")
                self._service = build(
                    "sheets", "v4", credentials=creds, cache_discovery=False
                )
                logger.info("SheetsService: Service built successfully.")
            except Exception as e:
                logger.exception("SheetsService: Exception in build('sheets', 'v4')")
                raise e

        return self._service

    async def get_all_rows(self) -> list[dict]:
        logger.info("SheetsService: get_all_rows - calling _get_service()")
        service = self._get_service()
        if not service:
            logger.warning("SheetsService: _get_service returned None")
            return []

        def _fetch():
            logger.info("SheetsService: _fetch - preparing spreadsheets values get request")
            sheet = service.spreadsheets()
            logger.info(f"SheetsService: _fetch - calling execute() for range Sheet1!A:H on sheet {self.sheet_id}")
            result = (
                sheet.values()
                .get(spreadsheetId=self.sheet_id, range="Sheet1!A:H")
                .execute()
            )
            logger.info("SheetsService: _fetch - execute() completed successfully")
            return result.get("values", [])

        try:
            values = await asyncio.to_thread(_fetch)
            if not values:
                return []
            # Assuming first row is header
            headers = values[0]
            rows = []
            for i, row in enumerate(values[1:], start=2):  # 1-indexed, skipping header
                row_dict = {
                    headers[j]: row[j] if j < len(row) else ""
                    for j in range(len(headers))
                }
                row_dict["_row_index"] = i
                rows.append(row_dict)
            return rows
        except Exception as e:
            logger.exception("SheetsService: Exception inside get_all_rows")
            raise e

    async def append_row(
        self, name: str, phone: str, email: str, company: str, session_id: str
    ) -> dict:
        print(f"Appending row to sheets: {name}, {phone}, {email}, {company}")
        service = self._get_service()
        if not service:
            raise ValueError("Sheets service not initialized")

        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values = [[timestamp, name, phone, email, company, "", "", session_id]]
        body = {"values": values}

        def _append():
            return (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self.sheet_id,
                    range="Sheet1!A:H",
                    valueInputOption="RAW",
                    body=body,
                )
                .execute()
            )

        try:
            result = await asyncio.to_thread(_append)
            # Find the row index from updatedRange (e.g. 'Sheet1!A2:E2')
            updated_range = result.get("updates", {}).get("updatedRange", "")
            row_index = 2
            if updated_range:
                import re

                match = re.search(r"\![A-Z]+(\d+)", updated_range)
                if match:
                    row_index = int(match.group(1))

            return {
                "row_index": row_index,
                "data": {
                    "Name": name,
                    "Phone": phone,
                    "Email": email,
                    "Company": company,
                    "Session ID": session_id,
                },
            }
        except Exception as e:
            print(f"Error appending to sheets: {e}")
            raise e

    async def update_row_audio(self, row_index: int, audio_url: str, transcript: str):
        print(f"Updating row {row_index} with audio note: {transcript}")
        service = self._get_service()
        if not service:
            return False

        # Update Audio URL (Column F) and Audio Notes / Transcript (Column G)
        values = [[audio_url, transcript]]
        body = {"values": values}
        range_name = f"Sheet1!F{row_index}:G{row_index}"

        def _update():
            return (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=self.sheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    body=body,
                )
                .execute()
            )

        try:
            await asyncio.to_thread(_update)
            return True
        except Exception as e:
            print(f"Error updating sheets: {e}")
            return False


sheets_service = SheetsService()
