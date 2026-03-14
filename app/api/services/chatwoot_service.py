from __future__ import annotations

import os
import mimetypes
import requests
from typing import Any, Dict, Optional, List


class ChatwootService:
    def __init__(self, base_url: str, api_token: str, account_id: int):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.account_id = account_id

    # =========================
    # HEADERS
    # =========================
    def _headers(self) -> Dict[str, str]:
        return {
            "api_access_token": self.api_token,
            "Content-Type": "application/json",
        }

    def _headers_multipart(self) -> Dict[str, str]:
        # IMPORTANTE:
        # não mandar Content-Type aqui.
        # O requests define multipart/form-data automaticamente.
        return {
            "api_access_token": self.api_token,
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

    # =========================
    # UNWRAPPERS / EXTRACTORS
    # =========================
    @staticmethod
    def _unwrap_payload(data: Any) -> Any:
        if isinstance(data, dict) and "payload" in data:
            return data["payload"]
        return data

    @staticmethod
    def _unwrap_contact(data: Any) -> Any:
        data = ChatwootService._unwrap_payload(data)
        if isinstance(data, dict) and "contact" in data and isinstance(data["contact"], dict):
            return data["contact"]
        return data

    @staticmethod
    def _extract_id(obj: Any) -> Optional[int]:
        if obj is None:
            return None

        if isinstance(obj, list):
            if not obj:
                return None
            return ChatwootService._extract_id(obj[0])

        if isinstance(obj, dict):
            v = obj.get("id")
            if isinstance(v, int):
                return v

            payload = obj.get("payload")
            if payload is not None:
                return ChatwootService._extract_id(payload)

            for k in ("contact", "conversation", "message"):
                inner = obj.get(k)
                if isinstance(inner, dict):
                    vid = inner.get("id")
                    if isinstance(vid, int):
                        return vid

            inner_data = obj.get("data")
            if isinstance(inner_data, dict):
                vid = inner_data.get("id")
                if isinstance(vid, int):
                    return vid

        return None

    @staticmethod
    def extract_phone_from_contact(contact_payload: Dict[str, Any]) -> Optional[str]:
        contact = (
            contact_payload.get("payload")
            if isinstance(contact_payload, dict) and isinstance(contact_payload.get("payload"), dict)
            else contact_payload
        )
        if not isinstance(contact, dict):
            return None

        for k in ("phone_number", "phone", "phoneNumber"):
            v = contact.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None

    @staticmethod
    def _guess_filename_and_mime(
        media_url: str,
        media_type: Optional[str] = None,
        fallback_filename: Optional[str] = None,
        response_content_type: Optional[str] = None,
    ) -> tuple[str, str]:
        mt = (media_type or "").lower().strip()

        if mt == "audio":
            return (fallback_filename or "audio.ogg", response_content_type or "audio/ogg")
        if mt == "image":
            return (fallback_filename or "image.jpg", response_content_type or "image/jpeg")
        if mt == "video":
            return (fallback_filename or "video.mp4", response_content_type or "video/mp4")
        if mt == "document":
            guessed = mimetypes.guess_type(fallback_filename or "")[0]
            return (
                fallback_filename or "document.bin",
                response_content_type or guessed or "application/octet-stream",
            )

        # tenta inferir pela URL/nome
        guessed = mimetypes.guess_type(media_url)[0]
        if fallback_filename:
            guessed2 = mimetypes.guess_type(fallback_filename)[0]
            guessed = guessed2 or guessed

        return (
            fallback_filename or "file.bin",
            response_content_type or guessed or "application/octet-stream",
        )

    # =========================
    # INBOXES
    # =========================
    def create_api_inbox(
        self,
        name: str,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = f"/api/v1/accounts/{self.account_id}/inboxes"
        url = self._url(path)

        channel_payload: Dict[str, Any] = {"type": "api"}

        if webhook_url:
            channel_payload["webhook_url"] = webhook_url

        if webhook_secret:
            channel_payload["webhook_secret"] = webhook_secret

        payload = {
            "name": name,
            "channel": channel_payload,
        }

        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot create_api_inbox failed")

        data = r.json()
        self._log_http("POST", path, r, data)

        inbox_obj = self._unwrap_payload(data)

        if not isinstance(inbox_obj, dict):
            return {"raw": inbox_obj}

        inbox_id = inbox_obj.get("id")
        identifier = (
            inbox_obj.get("inbox_identifier")
            or inbox_obj.get("identifier")
            or (
                inbox_obj.get("channel", {}).get("identifier")
                if isinstance(inbox_obj.get("channel"), dict)
                else None
            )
        )

        print(
            "CHATWOOT_INBOX_CREATED:",
            {
                "id": inbox_id,
                "name": name,
                "identifier": identifier,
                "webhook_url": webhook_url,
            },
        )

        return {
            "id": inbox_id,
            "identifier": identifier,
            "raw": inbox_obj,
        }

    # =========================
    # CONTACTS
    # =========================
    def search_contact(self, phone_e164: str) -> Optional[Dict[str, Any]]:
        path = f"/api/v1/accounts/{self.account_id}/contacts/search"
        url = self._url(path)

        r = requests.get(url, params={"q": phone_e164}, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot search_contact failed")
        data = r.json()
        self._log_http("GET", path, r, data)

        items = self._unwrap_payload(data)
        if isinstance(items, list) and items:
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

        contact = self._unwrap_contact(data)

        print(
            "CHATWOOT_CONTACT_CREATED:",
            {"id": self._extract_id(contact), "name": name, "phone": phone_e164},
        )
        return contact if isinstance(contact, dict) else {"raw": contact}

    def get_or_create_contact(self, name: str, phone_e164: str) -> Dict[str, Any]:
        found = self.search_contact(phone_e164=phone_e164)
        if found:
            print("CHATWOOT_CONTACT_FOUND:", {"id": self._extract_id(found), "phone": phone_e164})
            return found
        return self.create_contact(name=name, phone_e164=phone_e164)

    def get_contact(self, contact_id: int) -> Dict[str, Any]:
        url = self._url(f"/api/v1/accounts/{self.account_id}/contacts/{contact_id}")
        r = requests.get(url, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot get_contact failed")
        return r.json()

    # =========================
    # CONVERSATIONS
    # =========================
    def create_conversation(self, inbox_id: int, contact_id: int) -> Dict[str, Any]:
        path = f"/api/v1/accounts/{self.account_id}/conversations"
        url = self._url(path)

        payload = {"inbox_id": inbox_id, "contact_id": contact_id}
        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot create_conversation failed")
        data = r.json()
        self._log_http("POST", path, r, data)

        print(
            "CHATWOOT_CONVERSATION_CREATED:",
            {"id": self._extract_id(data), "inbox_id": inbox_id, "contact_id": contact_id},
        )
        return data if isinstance(data, dict) else {"raw": data}

    def get_or_create_conversation(self, inbox_id: int, contact_id: int) -> Dict[str, Any]:
        return self.create_conversation(inbox_id=inbox_id, contact_id=contact_id)

    def get_conversation(self, conversation_id: int) -> Dict[str, Any]:
        url = self._url(f"/api/v1/accounts/{self.account_id}/conversations/{conversation_id}")
        r = requests.get(url, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot get_conversation failed")
        return r.json()

    @staticmethod
    def _extract_contact_id(conv: Dict[str, Any]) -> Optional[int]:
        c = conv.get("contact")
        if isinstance(c, dict):
            v = c.get("id")
            try:
                return int(v) if v is not None else None
            except Exception:
                pass

        v = conv.get("contact_id")
        try:
            return int(v) if v is not None else None
        except Exception:
            return None

    # =========================
    # MESSAGES
    # =========================
    def create_message(
        self,
        conversation_id: int,
        content: str,
        message_type: str = "incoming",
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Mantido para texto/json.
        Não usar este método para mídia real.
        """
        path = f"/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"
        url = self._url(path)

        payload: Dict[str, Any] = {
            "content": content,
            "message_type": message_type,
        }

        if attachments:
            payload["attachments"] = attachments

        r = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        self._raise(r, "Chatwoot create_message failed")
        data = r.json()
        self._log_http("POST", path, r, data)

        print(
            "CHATWOOT_MESSAGE_CREATED:",
            {"id": self._extract_id(data), "conversation_id": conversation_id, "type": message_type},
        )
        return data if isinstance(data, dict) else {"raw": data}

    def create_message_with_media(
        self,
        conversation_id: int,
        media_url: str,
        content: str = "",
        message_type: str = "incoming",
        media_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Baixa a mídia e reenvi a para o Chatwoot como attachment real.
        Use este método para audio/image/video/document.
        """
        path = f"/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"
        url = self._url(path)

        media_response = requests.get(media_url, timeout=60)
        media_response.raise_for_status()

        response_content_type = media_response.headers.get("Content-Type")
        safe_filename, safe_mime = self._guess_filename_and_mime(
            media_url=media_url,
            media_type=media_type,
            fallback_filename=filename,
            response_content_type=response_content_type,
        )

        files = {
            "attachments[]": (
                safe_filename,
                media_response.content,
                safe_mime,
            )
        }

        data = {
            "content": content,
            "message_type": message_type,
        }

        r = requests.post(
            url,
            data=data,
            files=files,
            headers=self._headers_multipart(),
            timeout=60,
        )
        self._raise(r, "Chatwoot create_message_with_media failed")
        data_resp = r.json()
        self._log_http("POST", path, r, data_resp)

        print(
            "CHATWOOT_MESSAGE_MEDIA_CREATED:",
            {
                "id": self._extract_id(data_resp),
                "conversation_id": conversation_id,
                "type": message_type,
                "filename": safe_filename,
                "mime_type": safe_mime,
                "media_type": media_type,
            },
        )
        return data_resp if isinstance(data_resp, dict) else {"raw": data_resp}
