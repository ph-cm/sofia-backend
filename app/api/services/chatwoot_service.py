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

    def _log_http(self, method: str, path: str, r: requests.Response, data: Any):
        keys = list(data.keys()) if isinstance(data, dict) else None
        print(
            "CHATWOOT_HTTP:",
            {"method": method, "path": path, "status": r.status_code, "keys": keys},
        )

    # ---------- Unwrappers / Extractors ----------

    @staticmethod
    def _unwrap_payload(data: Any) -> Any:
        # Chatwoot às vezes devolve {"payload": ...}
        if isinstance(data, dict) and "payload" in data:
            return data["payload"]
        return data

    @staticmethod
    def _unwrap_contact(data: Any) -> Any:
        """
        Alguns retornos vêm como:
          {"payload": {...}}
        ou
          {"contact": {...}, "contact_inbox": {...}}
        """
        data = ChatwootService._unwrap_payload(data)
        if isinstance(data, dict) and "contact" in data and isinstance(data["contact"], dict):
            return data["contact"]
        return data

    @staticmethod
    def _extract_id(obj: Any) -> Optional[int]:
        """
        Extrai id de vários formatos possíveis do Chatwoot.
        """
        if obj is None:
            return None

        # lista de objetos
        if isinstance(obj, list):
            if not obj:
                return None
            return ChatwootService._extract_id(obj[0])

        if isinstance(obj, dict):
            # direto
            v = obj.get("id")
            if isinstance(v, int):
                return v

            # payload
            payload = obj.get("payload")
            if payload is not None:
                return ChatwootService._extract_id(payload)

            # wrappers comuns
            for k in ("contact", "conversation", "message"):
                inner = obj.get(k)
                if isinstance(inner, dict):
                    vid = inner.get("id")
                    if isinstance(vid, int):
                        return vid

            # alguns retornos: {"data": {"id": ...}}
            inner_data = obj.get("data")
            if isinstance(inner_data, dict):
                vid = inner_data.get("id")
                if isinstance(vid, int):
                    return vid

        return None

    # ---------- Contacts ----------

    def search_contact(self, phone_e164: str) -> Optional[Dict[str, Any]]:
        path = f"/api/v1/accounts/{self.account_id}/contacts/search"
        url = self._url(path)

        r = requests.get(url, params={"q": phone_e164}, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot search_contact failed")
        data = r.json()
        self._log_http("GET", path, r, data)

        items = self._unwrap_payload(data)
        if isinstance(items, list) and items:
            # itens geralmente já vem com id no topo
            return items[0]

        return None

    def create_contact(self, name: str, phone_e164: str) -> Dict[str, Any]:
        path = f"/api/v1/accounts/{self.account_id}/contacts"
        url = self._url(path)

        payload = {"name": name, "phone_number": phone_e164}
        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot create_contact failed")
        data = r.json()
        self._log_http("POST", path, r, data)

        # IMPORTANTÍSSIMO: normaliza retorno que veio como {"contact": {...}}
        contact = self._unwrap_contact(data)

        print("CHATWOOT_CONTACT_CREATED:", {"id": self._extract_id(contact), "name": name, "phone": phone_e164})
        return contact if isinstance(contact, dict) else {"raw": contact}

    def get_or_create_contact(self, name: str, phone_e164: str) -> Dict[str, Any]:
        found = self.search_contact(phone_e164=phone_e164)
        if found:
            print("CHATWOOT_CONTACT_FOUND:", {"id": self._extract_id(found), "phone": phone_e164})
            return found
        return self.create_contact(name=name, phone_e164=phone_e164)

    # ---------- Conversations ----------

    def create_conversation(self, inbox_id: int, contact_id: int) -> Dict[str, Any]:
        path = f"/api/v1/accounts/{self.account_id}/conversations"
        url = self._url(path)

        payload = {"inbox_id": inbox_id, "contact_id": contact_id}
        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot create_conversation failed")
        data = r.json()
        self._log_http("POST", path, r, data)

        print("CHATWOOT_CONVERSATION_CREATED:", {"id": self._extract_id(data), "inbox_id": inbox_id, "contact_id": contact_id})
        return data if isinstance(data, dict) else {"raw": data}

    def get_or_create_conversation(self, inbox_id: int, contact_id: int) -> Dict[str, Any]:
        # MVP: cria sempre
        return self.create_conversation(inbox_id=inbox_id, contact_id=contact_id)

    # ---------- Messages ----------

    def create_message(
        self,
        conversation_id: int,
        content: str,
        message_type: str = "incoming",
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        path = f"/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"
        url = self._url(path)

        payload: Dict[str, Any] = {
            "content": content,
            "message_type": message_type,
        }

        # atenção: attachments via external_url pode não ser suportado em todas versões
        if attachments:
            payload["attachments"] = attachments

        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot create_message failed")
        data = r.json()
        self._log_http("POST", path, r, data)

        print("CHATWOOT_MESSAGE_CREATED:", {"id": self._extract_id(data), "conversation_id": conversation_id, "type": message_type})
        return data if isinstance(data, dict) else {"raw": data}
    
    def get_contact(self, contact_id: int) -> Dict[str, Any]:
        url = self._url(f"/api/v1/accounts/{self.account_id}/contacts/{contact_id}")
        r = requests.get(url, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot get_contact failed")
        return r.json()
    
    def extract_phone_from_contact(contact_payload: Dict[str, Any]) -> Optional[str]:
        # chatwoot pode devolver {"payload": {...}} ou direto {...}
        contact = contact_payload.get("payload") if isinstance(contact_payload, dict) and isinstance(contact_payload.get("payload"), dict) else contact_payload
        if not isinstance(contact, dict):
            return None

        for k in ("phone_number", "phone", "phoneNumber"):
            v = contact.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None
    
    @staticmethod
    def extract_phone_from_contact(contact_payload: Dict[str, Any]) -> Optional[str]:
        contact = contact_payload.get("payload") if isinstance(contact_payload, dict) and isinstance(contact_payload.get("payload"), dict) else contact_payload
        if not isinstance(contact, dict):
            return None

        for k in ("phone_number", "phone", "phoneNumber"):
            v = contact.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None
    
    def _extract_contact_id(conv: Dict[str, Any]) -> Optional[int]:
        # forma 1: conversation.contact.id
        c = conv.get("contact")
        if isinstance(c, dict):
            v = c.get("id")
            try:
                return int(v) if v is not None else None
            except Exception:
                pass

        # forma 2: conversation.contact_id
        v = conv.get("contact_id")
        try:
            return int(v) if v is not None else None
        except Exception:
            return None



