from __future__ import annotations

import requests
from typing import Any, Dict, Optional, List


class ChatwootService:
    def __init__(self, base_url: str, api_token: str, account_id: int):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.account_id = account_id

    def _headers(self) -> Dict[str, str]:
        return {
            "api_access_token": self.api_token,
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _raise(self, r: requests.Response, msg: str):
        if r.status_code >= 300:
            raise RuntimeError(f"{msg}: {r.status_code} {r.text}")

    # ---------- Contacts ----------

    def search_contact(self, phone_e164: str) -> Optional[Dict[str, Any]]:
        # endpoint comum: /contacts/search?q=
        url = self._url(f"/api/v1/accounts/{self.account_id}/contacts/search")
        r = requests.get(url, params={"q": phone_e164}, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot search_contact failed")
        data = r.json()

        # Chatwoot pode devolver {"payload": [...]} ou lista direta dependendo da versão
        items = data.get("payload") if isinstance(data, dict) else data
        if isinstance(items, list) and items:
            return items[0]
        return None

    def create_contact(self, name: str, phone_e164: str) -> Dict[str, Any]:
        url = self._url(f"/api/v1/accounts/{self.account_id}/contacts")
        payload = {
            "name": name,
            "phone_number": phone_e164,
        }
        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot create_contact failed")
        return r.json()

    def get_or_create_contact(self, name: str, phone_e164: str) -> Dict[str, Any]:
        found = self.search_contact(phone_e164=phone_e164)
        if found:
            return found
        return self.create_contact(name=name, phone_e164=phone_e164)

    # ---------- Conversations ----------

    def create_conversation(self, inbox_id: int, contact_id: int) -> Dict[str, Any]:
        url = self._url(f"/api/v1/accounts/{self.account_id}/conversations")
        payload = {
            "inbox_id": inbox_id,
            "contact_id": contact_id,
        }
        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot create_conversation failed")
        return r.json()

    def get_or_create_conversation(self, inbox_id: int, contact_id: int) -> Dict[str, Any]:
        """
        Chatwoot não tem um "get active conversation by contact+inbox" super estável em todas versões.
        Então, por agora: sempre cria.
        (Depois você pode buscar conversas do contato e reutilizar se estiver aberta.)
        """
        return self.create_conversation(inbox_id=inbox_id, contact_id=contact_id)

    # ---------- Messages ----------

    def create_message(
        self,
        conversation_id: int,
        content: str,
        message_type: str = "incoming",
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        url = self._url(f"/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages")
        payload: Dict[str, Any] = {
            "content": content,
            "message_type": message_type,  # incoming/outgoing
        }

        # Observação: "attachments" via external_url pode variar por versão.
        # Se a sua versão não suportar, você ainda terá a mensagem de texto.
        if attachments:
            payload["attachments"] = attachments

        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot create_message failed")
        return r.json()
