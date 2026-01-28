import requests
from typing import Dict, Any, Optional
from app.core.config import settings

class ChatwootService:
    @staticmethod
    def _headers() -> Dict[str, str]:
        # Chatwoot usa header api_access_token
        return {
            "api_access_token": settings.CHATWOOT_API_TOKEN,
            "Content-Type": "application/json",
        }

    @staticmethod
    def create_account(name: str) -> Dict[str, Any]:
        """
        Cria Account no Chatwoot.
        Retorna JSON do Chatwoot (deve conter id, name, etc).
        """
        url = f"{settings.CHATWOOT_BASE_URL}/api/v1/accounts"
        payload = {"name": name}
        r = requests.post(url, json=payload, headers=ChatwootService._headers(), timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"Chatwoot create_account failed: {r.status_code} {r.text}")
        return r.json()

    @staticmethod
    def create_api_inbox(account_id: int, name: str) -> Dict[str, Any]:
        """
        Cria Inbox do tipo API Channel (escala bem e serve para Evolution depois).
        Retorna JSON da inbox (id, name, channel, inbox_identifier em algumas versões).
        """
        url = f"{settings.CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}/inboxes"
        payload = {
            "name": name,
            "channel": {
                "type": "api",
                "webhook_url": None,  # opcional
            },
        }
        r = requests.post(url, json=payload, headers=ChatwootService._headers(), timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"Chatwoot create_inbox failed: {r.status_code} {r.text}")
        return r.json()
