import requests
from typing import Dict, Any, Optional


class ChatwootService:
    """
    Service multi-tenant:
      - base_url é global (pode vir de settings)
      - api_token + account_id (e inbox_id quando necessário) vêm do tenant (DB)
    """

    def __init__(self, base_url: str, api_token: str, account_id: Optional[int] = None):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.account_id = account_id

    def _headers(self) -> Dict[str, str]:
        return {
            "api_access_token": self.api_token,
            "Content-Type": "application/json",
        }

    # ---------- Admin-level (não precisa account_id) ----------
    def create_account(self, name: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/accounts"
        payload = {"name": name}
        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"Chatwoot create_account failed: {r.status_code} {r.text}")
        return r.json()

    # ---------- Account-level (precisa account_id) ----------
    def create_api_inbox(self, name: str) -> Dict[str, Any]:
        if not self.account_id:
            raise RuntimeError("ChatwootService.account_id is required for create_api_inbox")
        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/inboxes"
        payload = {
            "name": name,
            "channel": {"type": "api", "webhook_url": None},
        }
        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"Chatwoot create_inbox failed: {r.status_code} {r.text}")
        return r.json()

    def create_contact(self, name: str, phone_e164: str, identifier: Optional[str] = None) -> Dict[str, Any]:
        """
        phone_e164: ex '553499190547' (sem '+') ou com '+', mas mantenha um padrão.
        identifier: opcional (ex: wa:5534...)
        """
        if not self.account_id:
            raise RuntimeError("ChatwootService.account_id is required for create_contact")

        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts"
        payload = {
            "name": name,
            "phone_number": phone_e164,
        }
        if identifier:
            payload["identifier"] = identifier

        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"Chatwoot create_contact failed: {r.status_code} {r.text}")
        return r.json()

    def create_conversation(self, inbox_id: int, contact_id: int) -> Dict[str, Any]:
        if not self.account_id:
            raise RuntimeError("ChatwootService.account_id is required for create_conversation")

        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations"
        payload = {"inbox_id": inbox_id, "contact_id": contact_id}

        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"Chatwoot create_conversation failed: {r.status_code} {r.text}")
        return r.json()

    def create_message(self, conversation_id: int, content: str, message_type: str = "incoming") -> Dict[str, Any]:
        """
        message_type: 'incoming' (mensagem recebida do WhatsApp) ou 'outgoing'
        """
        if not self.account_id:
            raise RuntimeError("ChatwootService.account_id is required for create_message")

        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"
        payload = {"content": content, "message_type": message_type}

        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"Chatwoot create_message failed: {r.status_code} {r.text}")
        return r.json()
