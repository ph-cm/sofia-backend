from __future__ import annotations

import requests
from typing import Any, Dict, Optional, List, Union


class ChatwootService:
    """
    ChatwootService (robusto para variações de resposta entre versões)

    - Chatwoot às vezes retorna {"payload": {...}} ou {"payload": [...]}.
    - Algumas rotas podem retornar objeto direto.
    - Este service normaliza e LOGA o essencial sem vazar token.
    """

    def __init__(self, base_url: str, api_token: str, account_id: int):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.account_id = account_id

    # ---------- Core helpers ----------

    def _headers(self) -> Dict[str, str]:
        return {
            "api_access_token": self.api_token,
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _req(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        url = self._url(path)

        r = requests.request(
            method=method.upper(),
            url=url,
            headers=self._headers(),
            json=json,
            params=params,
            timeout=timeout,
        )

        # parse JSON (fallback para texto)
        try:
            data: Union[Dict[str, Any], List[Any]] = r.json()
        except Exception:
            data = {"_raw_text": r.text}

        # log leve
        if isinstance(data, dict):
            print("CHATWOOT_HTTP:", {"method": method.upper(), "path": path, "status": r.status_code, "keys": list(data.keys())})
        else:
            print("CHATWOOT_HTTP:", {"method": method.upper(), "path": path, "status": r.status_code, "type": "list"})

        if r.status_code >= 300:
            raise RuntimeError(f"Chatwoot {method.upper()} {path} failed: {r.status_code} {r.text}")

        # sempre retornar dict
        if isinstance(data, dict):
            return data
        return {"payload": data}

    @staticmethod
    def _unwrap_payload(resp: Any) -> Any:
        """Desembrulha {"payload": ...} quando existir."""
        if isinstance(resp, dict) and "payload" in resp:
            return resp["payload"]
        return resp

    @staticmethod
    def _extract_id(resp: Any) -> Optional[int]:
        """
        Extrai id em formatos comuns:
        - {"id": 123}
        - {"payload": {"id": 123}}
        - {"payload": [{"id": 123}, ...]}
        """
        if isinstance(resp, dict):
            if isinstance(resp.get("id"), int):
                return resp["id"]

            payload = resp.get("payload")
            if isinstance(payload, dict) and isinstance(payload.get("id"), int):
                return payload["id"]

            if isinstance(payload, list) and payload:
                first = payload[0]
                if isinstance(first, dict) and isinstance(first.get("id"), int):
                    return first["id"]

        return None

    @staticmethod
    def _ensure_obj(payload: Any, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Garante retorno dict; se vier inesperado, devolve debug."""
        if isinstance(payload, dict):
            return payload
        return {"_unexpected_payload_type": type(payload).__name__, "_raw": raw}

    # ---------- Admin (Accounts / Inboxes) ----------

    def create_account(self, name: str) -> Dict[str, Any]:
        """
        Cria Account no Chatwoot.
        OBS: dependendo da instalação, pode exigir token de SUPERADMIN.
        """
        raw = self._req("POST", "/api/v1/accounts", json={"name": name})
        payload = self._unwrap_payload(raw)
        obj = self._ensure_obj(payload, raw)

        acc_id = self._extract_id(obj) or self._extract_id(raw)
        print("CHATWOOT_ACCOUNT_CREATED:", {"id": acc_id, "name": name})
        return obj

    def create_api_inbox(self, account_id: int, name: str) -> Dict[str, Any]:
        """
        Cria inbox do tipo API Channel.
        """
        raw = self._req(
            "POST",
            f"/api/v1/accounts/{account_id}/inboxes",
            json={
                "name": name,
                "channel": {"type": "api", "webhook_url": None},
            },
        )
        payload = self._unwrap_payload(raw)
        obj = self._ensure_obj(payload, raw)

        inbox_id = self._extract_id(obj) or self._extract_id(raw)
        print("CHATWOOT_INBOX_CREATED:", {"id": inbox_id, "account_id": account_id, "name": name})
        return obj

    # ---------- Contacts ----------

    def search_contacts(self, query: str) -> List[Dict[str, Any]]:
        raw = self._req(
            "GET",
            f"/api/v1/accounts/{self.account_id}/contacts/search",
            params={"q": query},
        )
        payload = self._unwrap_payload(raw)

        # formato 1: lista direta
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]

        # formato 2: dict com lista dentro
        if isinstance(payload, dict):
            if isinstance(payload.get("payload"), list):
                return [x for x in payload["payload"] if isinstance(x, dict)]
            if isinstance(payload.get("contacts"), list):
                return [x for x in payload["contacts"] if isinstance(x, dict)]

        print("CHATWOOT_WARN: search_contacts_unexpected", {"type": type(payload).__name__})
        return []

    def search_contact(self, phone_e164: str) -> Optional[Dict[str, Any]]:
        items = self.search_contacts(query=phone_e164)
        return items[0] if items else None

    def create_contact(self, name: str, phone_e164: str) -> Dict[str, Any]:
        raw = self._req(
            "POST",
            f"/api/v1/accounts/{self.account_id}/contacts",
            json={"name": name, "phone_number": phone_e164},
        )
        payload = self._unwrap_payload(raw)
        obj = self._ensure_obj(payload, raw)

        cid = self._extract_id(obj) or self._extract_id(raw)
        print("CHATWOOT_CONTACT_CREATED:", {"id": cid, "name": name, "phone": phone_e164})
        return obj

    def get_or_create_contact(self, name: str, phone_e164: str) -> Dict[str, Any]:
        found = self.search_contact(phone_e164=phone_e164)
        if found:
            cid = self._extract_id(found)
            print("CHATWOOT_CONTACT_FOUND:", {"id": cid, "phone": phone_e164})
            return found
        return self.create_contact(name=name, phone_e164=phone_e164)

    # ---------- Conversations ----------

    def create_conversation(self, inbox_id: int, contact_id: int) -> Dict[str, Any]:
        raw = self._req(
            "POST",
            f"/api/v1/accounts/{self.account_id}/conversations",
            json={"inbox_id": inbox_id, "contact_id": contact_id},
        )
        payload = self._unwrap_payload(raw)
        obj = self._ensure_obj(payload, raw)

        conv_id = self._extract_id(obj) or self._extract_id(raw)
        print("CHATWOOT_CONVERSATION_CREATED:", {"id": conv_id, "inbox_id": inbox_id, "contact_id": contact_id})
        return obj

    def get_or_create_conversation(self, inbox_id: int, contact_id: int) -> Dict[str, Any]:
        """
        MVP: cria sempre.
        Depois você pode implementar "buscar conversa aberta por contato+inbox".
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
        payload: Dict[str, Any] = {"content": content, "message_type": message_type}
        if attachments:
            payload["attachments"] = attachments

        raw = self._req(
            "POST",
            f"/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages",
            json=payload,
        )
        unwrapped = self._unwrap_payload(raw)
        obj = self._ensure_obj(unwrapped, raw)

        msg_id = self._extract_id(obj) or self._extract_id(raw)
        print("CHATWOOT_MESSAGE_CREATED:", {"id": msg_id, "conversation_id": conversation_id, "type": message_type})
        return obj
