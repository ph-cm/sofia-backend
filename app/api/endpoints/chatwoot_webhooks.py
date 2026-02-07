# app/api/endpoints/chatwoot_webhooks.py
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from typing import Any, Dict, Optional, Tuple, List

from app.core.config import settings
from app.api.services.tenant_service import TenantService
from app.api.services.evolution_service import EvolutionService


router = APIRouter(prefix="/integrations/chatwoot", tags=["Chatwoot Webhooks"])


def log_info(msg: str, extra: dict | None = None):
    print(f"CHATWOOT_WEBHOOK_INFO: {msg} extra={extra or {}}")


def log_ignore(reason: str, extra: dict | None = None):
    print(f"CHATWOOT_WEBHOOK_IGNORED: reason={reason} extra={extra or {}}")


def log_err(msg: str, extra: dict | None = None):
    print(f"CHATWOOT_WEBHOOK_ERROR: {msg} extra={extra or {}}")


def _dig_only(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


def extract_outgoing(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Retorna (is_outgoing, message_type_str)
    Chatwoot costuma mandar payload com "message_type": "outgoing"/"incoming"
    ou "message": {...}
    """
    msg = payload.get("message") if isinstance(payload.get("message"), dict) else payload
    mt = msg.get("message_type") or msg.get("messageType")
    if isinstance(mt, str):
        return (mt.lower() == "outgoing", mt.lower())
    return (False, None)


def extract_conversation_inbox_id(payload: Dict[str, Any]) -> Optional[int]:
    msg = payload.get("message") if isinstance(payload.get("message"), dict) else payload
    conv = msg.get("conversation")
    if isinstance(conv, dict):
        inbox_id = conv.get("inbox_id")
        if isinstance(inbox_id, int):
            return inbox_id
        if isinstance(inbox_id, str) and inbox_id.isdigit():
            return int(inbox_id)
    return None


def extract_recipient_phone(payload: Dict[str, Any]) -> Optional[str]:
    """
    Tenta extrair o telefone do paciente (destinatário) a partir do payload do Chatwoot.
    O campo mais estável costuma ser:
      message.conversation.contact_inbox.source_id   -> ex "+5534...." ou "5534...."
    Em outras versões:
      conversation.meta.sender.phone_number
      message.sender.phone_number (nem sempre)
    """
    msg = payload.get("message") if isinstance(payload.get("message"), dict) else payload
    conv = msg.get("conversation")
    if isinstance(conv, dict):
        ci = conv.get("contact_inbox")
        if isinstance(ci, dict):
            sid = ci.get("source_id")
            if isinstance(sid, str) and sid.strip():
                return sid.strip()

        meta = conv.get("meta")
        if isinstance(meta, dict):
            sender = meta.get("sender")
            if isinstance(sender, dict):
                pn = sender.get("phone_number")
                if isinstance(pn, str) and pn.strip():
                    return pn.strip()

    sender = msg.get("sender")
    if isinstance(sender, dict):
        pn = sender.get("phone_number")
        if isinstance(pn, str) and pn.strip():
            return pn.strip()

    return None


def extract_text_or_audio(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza conteúdo outgoing:
      {"kind": "text", "text": "..."}
      {"kind": "audio", "url": "...", "ptt": False}
    """
    msg = payload.get("message") if isinstance(payload.get("message"), dict) else payload

    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return {"kind": "text", "text": content.strip()}

    # attachments (áudio)
    attachments = msg.get("attachments")
    if isinstance(attachments, list) and attachments:
        # pega o primeiro áudio que achar
        for att in attachments:
            if not isinstance(att, dict):
                continue

            file_type = att.get("file_type") or att.get("fileType")
            # chatwoot costuma usar file_type: "audio" | "image" | "file"
            if isinstance(file_type, str) and file_type.lower() == "audio":
                # pode vir em vários campos dependendo da versão
                url = (
                    att.get("data_url")
                    or att.get("file_url")
                    or att.get("url")
                    or att.get("external_url")
                )
                if isinstance(url, str) and url.strip():
                    return {"kind": "audio", "url": url.strip(), "ptt": False}

        # se não achou áudio, mas existe attachment: cai como "unknown_attachment"
        return {"kind": "unknown_attachment", "count": len(attachments)}

    return {"kind": "empty"}


@router.post("/events")
async def chatwoot_events(request: Request, secret: str):
    # 0) valida secret
    if secret != settings.CHATWOOT_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    payload: Dict[str, Any] = await request.json()

    try:
        # 1) só outgoing
        is_outgoing, mt = extract_outgoing(payload)
        if not is_outgoing:
            log_ignore("not_outgoing", {"message_type": mt})
            return {"ok": True, "ignored": "not_outgoing"}

        # 2) inbox_id -> tenant
        inbox_id = extract_conversation_inbox_id(payload)
        if not inbox_id:
            log_err("missing_inbox_id")
            return {"ok": True, "ignored": "missing_inbox_id"}

        tenant = TenantService.get_by_chatwoot_inbox_id(inbox_id)
        if not tenant:
            log_ignore("tenant_not_found_by_inbox", {"inbox_id": inbox_id})
            return {"ok": True, "ignored": "tenant_not_found_by_inbox", "inbox_id": inbox_id}

        instance_name = tenant.get("evolution_instance_name")
        if not instance_name:
            log_ignore("tenant_missing_evolution_instance", {"tenant_id": tenant.get("id"), "inbox_id": inbox_id})
            return {"ok": True, "ignored": "tenant_missing_evolution_instance"}

        # 3) telefone do paciente
        phone = extract_recipient_phone(payload)
        if not phone:
            log_err("missing_recipient_phone", {"tenant_id": tenant.get("id"), "inbox_id": inbox_id})
            return {"ok": True, "ignored": "missing_recipient_phone"}

        phone_digits = _dig_only(phone)
        if not phone_digits:
            log_err("invalid_recipient_phone", {"phone": phone})
            return {"ok": True, "ignored": "invalid_recipient_phone"}

        # 4) conteúdo (texto ou áudio)
        content = extract_text_or_audio(payload)

        evo = EvolutionService(
            base_url=settings.EVOLUTION_BASE_URL,
            api_key=settings.EVOLUTION_API_KEY,
        )

        if content["kind"] == "text":
            text = content["text"]
            log_info("sending_text", {"tenant_id": tenant.get("id"), "inbox_id": inbox_id, "to": phone_digits})
            out = evo.send_text(instance_name=instance_name, to=phone_digits, text=text)
            return {"ok": True, "sent": "text", "to": phone_digits, "evolution": out}

        if content["kind"] == "audio":
            url = content["url"]
            log_info("sending_audio", {"tenant_id": tenant.get("id"), "inbox_id": inbox_id, "to": phone_digits, "url": url})
            out = evo.send_audio_url(instance_name=instance_name, to=phone_digits, audio_url=url, ptt=False)
            return {"ok": True, "sent": "audio", "to": phone_digits, "evolution": out}

        log_ignore("unsupported_outgoing_content", {"kind": content["kind"]})
        return {"ok": True, "ignored": "unsupported_outgoing_content", "kind": content["kind"]}

    except Exception as e:
        log_err("exception", {"error": repr(e)})
        # não retorna 500 pra evitar retry infinito
        return {"ok": True, "ignored": "exception", "error": str(e)}
