import httpx
import asyncio
import os
import sys

# Add backend directory to path if needed
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

async def run_audit():
    async with httpx.AsyncClient(timeout=60) as client:
        print("=== TEST 1: Unique Card Upload, HITL Confirm, sheet write, enrichment & WhatsApp ===")
        # 1. Create a session
        r = await client.post("http://localhost:8000/api/sessions/", json={})
        session_id = r.json()["session_id"]
        print(f"Created Session ID: {session_id}")
        
        # 2. Upload card image (we use the actual Priya Sharma image)
        card_image_path = "backend/priya_sharma_card.png"
        with open(card_image_path, "rb") as f:
            image_bytes = f.read()
        
        files = {"image": ("priya_sharma_card.png", image_bytes, "image/png")}
        r2 = await client.post(
            f"http://localhost:8000/api/sessions/{session_id}/messages",
            data={"text": "Digitize this card please"},
            files=files,
        )
        extract_result = r2.json()
        print(f"Extraction result: {extract_result}")
        
        # 3. Confirm with a UNIQUE contact details to ensure it appends and sends WhatsApp
        # We append a unique timestamp to email and phone to guarantee uniqueness
        import time
        ts = int(time.time())
        unique_name = f"Audit User {ts}"
        unique_email = f"audit.user.{ts}@novatech.io"
        unique_phone = f"+91 99999 {ts % 100000:05d}"
        
        payload = {
            "name": unique_name,
            "phone": unique_phone,
            "email": unique_email,
            "company": "Audit Labs Ltd"
        }
        print(f"Confirming with payload: {payload}")
        r3 = await client.post(
            f"http://localhost:8000/api/sessions/{session_id}/confirm",
            json=payload
        )
        confirm_result = r3.json()
        print(f"Confirm result: {confirm_result}")
        
        # Check Sheet rows using the sheets_service directly
        # Wait, since sheets_service needs to run in python, we can inspect rows by calling sheets_service
        # Let's import it locally inside the script
        from app.services.sheets_service import sheets_service
        
        print("Fetching all rows to check before audio upload...")
        rows = await sheets_service.get_all_rows()
        target_row = None
        for r in rows:
            if r.get("Session ID") == session_id:
                target_row = r
                break
        
        if target_row:
            print(f"Found Sheet Row BEFORE Audio: {target_row}")
        else:
            print("❌ Error: Row not found in Google Sheets!")
            return
            
        print("\n=== TEST 2: Voice recording upload in SAME session ===")
        # Upload a dummy audio file
        dummy_audio = b"RIFF....WAVEfmt ...."
        files_audio = {"audio": ("audit_voice.wav", dummy_audio, "audio/wav")}
        r4 = await client.post(
            f"http://localhost:8000/api/sessions/{session_id}/messages",
            files=files_audio
        )
        audio_result = r4.json()
        print(f"Audio Upload response: {audio_result}")
        
        print("Fetching all rows to check AFTER audio upload...")
        rows = await sheets_service.get_all_rows()
        target_row_after = None
        for r in rows:
            if r.get("Session ID") == session_id:
                target_row_after = r
                break
        
        if target_row_after:
            print(f"Found Sheet Row AFTER Audio: {target_row_after}")
            print(f"  Audio URL (Col F): {target_row_after.get('Audio URL')}")
            print(f"  Audio Notes (Col G): {target_row_after.get('Audio Notes')}")
        else:
            print("❌ Error: Row not found after audio update!")
            
        print("\n=== TEST 3: Voice recording upload in a session with NO prior card upload ===")
        # 1. Create a brand new session
        r_new = await client.post("http://localhost:8000/api/sessions/", json={})
        new_session_id = r_new.json()["session_id"]
        print(f"Created Session ID (No Card): {new_session_id}")
        
        # 2. Upload audio directly
        r_audio_fail = await client.post(
            f"http://localhost:8000/api/sessions/{new_session_id}/messages",
            files={"audio": ("fail_voice.wav", dummy_audio, "audio/wav")}
        )
        print(f"Audio upload response (expect grace fail): {r_audio_fail.json()}")
        
        print("\n=== TEST 4: Duplicate Card does not trigger WhatsApp / second sheet write ===")
        # Create another session
        r_dup = await client.post("http://localhost:8000/api/sessions/", json={})
        dup_session_id = r_dup.json()["session_id"]
        print(f"Created Session ID for Duplicate: {dup_session_id}")
        
        # Confirm with the SAME details we confirmed in Test 1
        print(f"Attempting duplicate confirmation with details of: {unique_name}")
        r_confirm_dup = await client.post(
            f"http://localhost:8000/api/sessions/{dup_session_id}/confirm",
            json=payload
        )
        dup_confirm_result = r_confirm_dup.json()
        print(f"Duplicate Confirm result: {dup_confirm_result}")

if __name__ == "__main__":
    asyncio.run(run_audit())
