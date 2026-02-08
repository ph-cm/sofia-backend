from __future__ import annotations

from fastapi import APIRouter, Request
from typing import Any, Dict, Optional

from app.core.config import settings
from app.api.services.chatwoot_service import ChatwootService
from app.api.services.tenant_service import TenantService
from app.db.session import SessionLocal
from app.api.services.conversation_map_service import ConversationMapService

router = APIRouter(prefix="/webhooks/evolution", tags=["Evolution Webhooks"])


def log_ignore(instance_name: str, reason: str, extra: dict | None = None):
    extra = extra or {}
    print(f"EVOLUTION_IGNORED: instance={instance_name} reason={reason} extra={extra}")


def log_info(instance_name: str, msg: str, extra: dict | None = None):
    extra = extra or {}
    print(f"EVOLUTION_INFO: instance={instance_name} msg={msg} extra={extra}")


def log_err(instance_name: str, msg: str, extra: dict | None = None):
    extra = extra or {}
    print(f"EVOLUTION_ERROR: instance={instance_name} msg={msg} extra={extra}")


# ---------- Extractors (tolerantes) ----------

def extract_instance_name(payload: Dict[str, Any]) -> Optional[str]:
    inst = payload.get("instance")

    if isinstance(inst, str) and inst.strip():
        return inst.strip()

    if isinstance(inst, dict):
        name = inst.get("instanceName") or inst.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()

    data = payload.get("data")
    if isinstance(data, dict):
        name = data.get("instanceName") or data.get("instance")
        if isinstance(name, str) and name.strip():
            return name.strip()

    return None


def extract_remote_jid(payload: Dict[str, Any]) -> Optional[str]:
    data = payload.get("data")
    if isinstance(data, dict):
        key = data.get("key")
        if isinstance(key, dict):
            jid = key.get("remoteJid")
            if isinstance(jid, str) and jid.strip():
                return jid.strip()
    return None


def extract_from_me(payload: Dict[str, Any]) -> bool:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return False
    key = data.get("key") or {}
    return bool(key.get("fromMe"))


def extract_phone_e164(payload: Dict[str, Any]) -> Optional[str]:
    data = payload.get("data", {})
    key = data.get("key", {}) if isinstance(data, dict) else {}
    remote = key.get("remoteJid")

    if isinstance(remote, str) and remote:
        if "@" in remote:
            num = remote.split("@", 1)[0]
            if num.isdigit():
                return num
        if remote.isdigit():
            return remote

    sender = payload.get("sender")
    if isinstance(sender, str) and sender:
        num = sender.split("@", 1)[0]
        if num.isdigit():
            return num

    return None


def extract_push_name(payload: Dict[str, Any]) -> Optional[str]:
    data = payload.get("data", {})
    if isinstance(data, dict):
        pn = data.get("pushName")
        if isinstance(pn, str) and pn.strip():
            return pn.strip()
    return None


def extract_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get("data", {})
    msg = data.get("message", {}) if isinstance(data, dict) else {}

    if not isinstance(msg, dict):
        return {"type": "unknown"}

    conv = msg.get("conversation")
    if isinstance(conv, str) and conv.strip():
        return {"type": "text", "content": conv.strip()}

    ext = msg.get("extendedTextMessage")
    if isinstance(ext, dict):
        txt = ext.get("text")
        if isinstance(txt, str) and txt.strip():
            return {"type": "text", "content": txt.strip()}

    audio = msg.get("audioMessage")
    if isinstance(audio, dict):
        return {
            "type": "audio",
            "url": audio.get("url"),
            "mimetype": audio.get("mimetype"),
            "seconds": audio.get("seconds"),
            "ptt": bool(audio.get("ptt", False)),
            "file_sha256": audio.get("fileSha256"),
        }

    image = msg.get("imageMessage")
    if isinstance(image, dict):
        return {
            "type": "image",
            "url": image.get("url"),
            "caption": image.get("caption"),
            "mimetype": image.get("mimetype"),
            "file_sha256": image.get("fileSha256"),
        }

    doc = msg.get("documentMessage")
    if isinstance(doc, dict):
        return {
            "type": "document",
            "url": doc.get("url"),
            "fileName": doc.get("fileName"),
            "mimetype": doc.get("mimetype"),
            "file_sha256": doc.get("fileSha256"),
        }

    return {"type": "unknown"}


def extract_dedup_key(payload: Dict[str, Any]) -> Optional[str]:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return None
    key = data.get("key")
    if not isinstance(key, dict):
        return None
    mid = key.get("id")
    return mid if isinstance(mid, str) and mid.strip() else None


# ---------- Helpers ----------

def safe_extract_id(obj: Any, label: str, instance_name: str) -> Optional[int]:
    """
    Usa o extractor tolerante do ChatwootService para pegar o id.
    """
    try:
        cid = ChatwootService._extract_id(obj)  # staticmethod do service robusto
        if not cid:
            log_err(instance_name, "missing_id", {"label": label, "type": type(obj).__name__, "keys": list(obj.keys()) if isinstance(obj, dict) else None})
        return cid
    except Exception as e:
        log_err(instance_name, "extract_id_exception", {"label": label, "error": repr(e)})
        return None


# ---------- Route ----------

@router.post("/{event}")
async def evolution_webhook(event: str, request: Request):
    payload: Dict[str, Any] = await request.json()

    instance_name = extract_instance_name(payload) or "unknown"
    msg_type = "n/a"
    remote_jid = None
    dedup_key = None

    try:
        print(f"EVOLUTION_WEBHOOK: event={event} instance={instance_name}")

        if event != "messages-upsert":
            log_ignore(instance_name, "non_message_event", {"event": event})
            return {"ok": True, "ignored": "non_message_event", "event": event}

        if extract_from_me(payload):
            remote_jid = extract_remote_jid(payload)
            log_ignore(instance_name, "from_me", {"remote_jid": remote_jid})
            return {"ok": True, "ignored": "from_me"}

        remote_jid = extract_remote_jid(payload)

        # (você está ignorando grupos — então NUNCA vai aparecer no Chatwoot)
        if isinstance(remote_jid, str) and remote_jid.endswith("@g.us"):
            log_ignore(instance_name, "group_message", {"remote_jid": remote_jid})
            return {"ok": True, "ignored": "group_message"}

        dedup_key = extract_dedup_key(payload)
        if dedup_key:
            if TenantService.is_duplicate_message(instance_name=instance_name, message_id=dedup_key):
                log_ignore(instance_name, "duplicate", {"message_id": dedup_key, "remote_jid": remote_jid})
                return {"ok": True, "ignored": "duplicate", "message_id": dedup_key}
            log_info(instance_name, "dedup_key_new", {"message_id": dedup_key, "remote_jid": remote_jid})

        message = extract_message(payload)
        msg_type = message.get("type", "unknown")
        if msg_type == "unknown":
            log_ignore(instance_name, "unsupported_message", {"remote_jid": remote_jid})
            return {"ok": True, "ignored": "unsupported_message"}

        phone = extract_phone_e164(payload)
        push_name = extract_push_name(payload)

        if not phone:
            log_ignore(instance_name, "no_phone", {"remote_jid": remote_jid, "push_name": push_name, "type": msg_type})
            return {"ok": True, "ignored": "no_phone"}

        tenant = TenantService.get_by_evolution_instance(instance_name)
        if not tenant:
            log_ignore(instance_name, "tenant_not_found", {"instance": instance_name, "phone": phone})
            return {"ok": True, "ignored": "tenant_not_found"}

        log_info(
            instance_name,
            "tenant_loaded",
            {
                "tenant_id": tenant.get("id"),
                "chatwoot_account_id": tenant.get("chatwoot_account_id"),
                "chatwoot_inbox_id": tenant.get("chatwoot_inbox_id"),
                "has_chatwoot_token": bool(tenant.get("chatwoot_api_token")),
            },
        )

        if not tenant.get("chatwoot_account_id") or not tenant.get("chatwoot_inbox_id") or not tenant.get("chatwoot_api_token"):
            log_ignore(instance_name, "tenant_chatwoot_not_configured", {"tenant_id": tenant.get("id")})
            return {"ok": True, "ignored": "tenant_chatwoot_not_configured"}

        cw = ChatwootService(
            base_url=settings.CHATWOOT_BASE_URL,
            api_token=tenant["chatwoot_api_token"],
            account_id=int(tenant["chatwoot_account_id"]),
        )

        # 1) contato
        contact_name = push_name or phone
        contact = cw.get_or_create_contact(name=contact_name, phone_e164=f"+{phone}")
        contact_id = safe_extract_id(contact, "contact", instance_name)
        log_info(instance_name, "chatwoot_contact_result", {"contact_id": contact_id, "name": contact_name, "phone": phone})

        if not contact_id:
            log_err(instance_name, "stop_no_contact_id", {"note": "Chatwoot respondeu sem id para contato"})
            return {"ok": True, "ignored": "chatwoot_no_contact_id"}

        # 2) conversa
        conv = cw.get_or_create_conversation(inbox_id=int(tenant["chatwoot_inbox_id"]), contact_id=int(contact_id))
        conv_id = safe_extract_id(conv, "conversation", instance_name)
        log_info(instance_name, "chatwoot_conversation_result", {"conversation_id": conv_id, "inbox_id": tenant.get("chatwoot_inbox_id")})

        if not conv_id:
            log_err(instance_name, "stop_no_conversation_id", {"note": "Chatwoot respondeu sem id para conversa"})
            return {"ok": True, "ignored": "chatwoot_no_conversation_id"}
                # 2) conversa
        conv = cw.get_or_create_conversation(inbox_id=int(tenant["chatwoot_inbox_id"]), contact_id=int(contact_id))
        conv_id = safe_extract_id(conv, "conversation", instance_name)
        log_info(instance_name, "chatwoot_conversation_result", {"conversation_id": conv_id, "inbox_id": tenant.get("chatwoot_inbox_id")})

        if not conv_id:
            log_err(instance_name, "stop_no_conversation_id", {"note": "Chatwoot respondeu sem id para conversa"})
            return {"ok": True, "ignored": "chatwoot_no_conversation_id"}
                # ✅ salva mapping (conversation -> phone) para o outgoing do Chatwoot conseguir enviar no WhatsApp
        try:
            db = SessionLocal()
            try:
                ConversationMapService.upsert_map(
                    db=db,
                    chatwoot_account_id=int(tenant["chatwoot_account_id"]),
                    chatwoot_conversation_id=int(conv_id),
                    wa_phone_digits=str(phone),
                )
                log_info(
                    instance_name,
                    "cw_map_saved",
                    {
                        "account_id": int(tenant["chatwoot_account_id"]),
                        "conversation_id": int(conv_id),
                        "phone": phone,
                    },
                )
            finally:
                db.close()
        except Exception as e:
            log_err(instance_name, "cw_map_save_failed", {"error": repr(e), "conversation_id": conv_id})

        # 3) mensagem
        created = None

        if msg_type == "text":
            content = message.get("content") or "(sem texto)"
            created = cw.create_message(conversation_id=int(conv_id), content=content, message_type="incoming")

        elif msg_type == "audio":
            url = message.get("url")
            created = cw.create_message(
                conversation_id=int(conv_id),
                content="🎤 Áudio recebido",
                message_type="incoming",
                attachments=[{"file_type": "audio", "external_url": url}] if url else None,
            )

        elif msg_type == "image":
            url = message.get("url")
            caption = message.get("caption") or "🖼️ Imagem recebida"
            created = cw.create_message(
                conversation_id=int(conv_id),
                content=caption,
                message_type="incoming",
                attachments=[{"file_type": "image", "external_url": url}] if url else None,
            )

        elif msg_type == "document":
            url = message.get("url")
            fname = message.get("fileName") or "📎 Documento recebido"
            created = cw.create_message(
                conversation_id=int(conv_id),
                content=fname,
                message_type="incoming",
                attachments=[{"file_type": "file", "external_url": url}] if url else None,
            )

        else:
            log_ignore(instance_name, "unhandled_type", {"type": msg_type})
            return {"ok": True, "ignored": "unhandled_type"}

        msg_id = safe_extract_id(created, "message", instance_name)
        log_info(instance_name, "chatwoot_message_result", {"message_id": msg_id, "conversation_id": conv_id})

        if dedup_key:
            TenantService.mark_message_processed(instance_name=instance_name, message_id=dedup_key)
            log_info(instance_name, "dedup_marked_processed", {"message_id": dedup_key})

        print(f"EVOLUTION_WEBHOOK_OK: instance={instance_name} type={msg_type} contact_id={contact_id} conv_id={conv_id} msg_id={msg_id}")

        return {
            "ok": True,
            "instance_name": instance_name,
            "type": msg_type,
            "chatwoot": {
                "contact_id": contact_id,
                "conversation_id": conv_id,
                "message_id": msg_id,
            },
        }

    except Exception as e:
        log_err(
            instance_name,
            "exception",
            {
                "event": event,
                "type": msg_type,
                "remote_jid": remote_jid,
                "message_id": dedup_key,
                "error": repr(e),
            },
        )
        # não devolve 500 pra evitar retry infinito
        return {"ok": True, "ignored": "exception", "error": str(e)}
