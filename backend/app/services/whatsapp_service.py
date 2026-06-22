import json

import httpx

from app.config import config


class WhatsAppService:
    def __init__(self):
        self.token = config.whatsapp_token
        self.phone_number_id = config.whatsapp_phone_number_id
        self.manager_number = config.manager_phone_number
        self.api_url = (
            f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"
        )

    async def send_notification(self, name: str, company: str):
        if not self.token or not self.manager_number or not self.phone_number_id:
            print("WhatsApp not configured, skipping notification.")
            return False

        print(
            f"Sending WhatsApp notification to {self.manager_number} for {name} ({company})..."
        )

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": self.manager_number,
            "type": "text",
            "text": {
                "body": f"New Contact Captured!\nName: {name}\nCompany: {company}\nCheck your Google Sheet for details."
            },
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.api_url, headers=headers, json=payload, timeout=10.0
                )
                response.raise_for_status()
                print("WhatsApp notification sent successfully.")
                return True
            except Exception as e:
                status_code = getattr(e, "response", None) and e.response.status_code
                response_text = getattr(e, "response", None) and e.response.text
                print(
                    f"Error sending WhatsApp message: {e}. Status: {status_code}. Response: {response_text}"
                )
                # We do not raise the exception to avoid failing the whole pipeline if just notification fails
                return False


whatsapp_service = WhatsAppService()
