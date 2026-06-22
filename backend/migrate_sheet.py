import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.services.sheets_service import sheets_service

async def migrate():
    print("Fetching all rows from Google Sheets...")
    rows = await sheets_service.get_all_rows()
    if not rows:
        print("No rows found or error fetching rows.")
        return
        
    service = sheets_service._get_service()
    if not service:
        print("Failed to initialize Google Sheets service.")
        return

    print(f"Scanning {len(rows)} rows for misaligned audio details...")
    migrated_count = 0

    for row in rows:
        row_index = row.get("_row_index")
        audio_url = row.get("Audio URL", "").strip()
        audio_notes = row.get("Audio Notes", "").strip()

        # Detect if Column F (Audio URL) contains transcription text instead of a valid URL,
        # and Column G (Audio Notes) is empty.
        is_misaligned = (
            audio_url 
            and not audio_url.startswith("http://") 
            and not audio_url.startswith("https://") 
            and not audio_notes
        )

        if is_misaligned:
            print(f"Row {row_index} is misaligned:")
            print(f"  Old Audio URL:  '{audio_url}'")
            print(f"  Old Audio Notes: '{audio_notes}'")
            
            # Shift the transcription from F to G, setting F (Audio URL) to empty
            new_values = [["", audio_url]]
            body = {'values': new_values}
            range_name = f'Sheet1!F{row_index}:G{row_index}'
            
            def _update():
                return service.spreadsheets().values().update(
                    spreadsheetId=sheets_service.sheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()

            try:
                await asyncio.to_thread(_update)
                print(f"  Successfully migrated Row {row_index}!")
                migrated_count += 1
            except Exception as e:
                print(f"  Failed to update Row {row_index}: {e}")

    print(f"\nMigration complete. Total rows shifted: {migrated_count}")

if __name__ == "__main__":
    asyncio.run(migrate())
