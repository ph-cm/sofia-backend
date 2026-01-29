from __future__ import annotations

from fastapi import APIRouter, Request
from typing import Any, Dict, Optional

from app.core.config import settings
from app.api.services.chatwoot_service import ChatwootService
from app.api.services.tenant_service import TenantService

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

    # seu caso real: string "tenant_1"
    if isinstance(inst, str) and inst.strip():
        return inst.strip()

    # alguns builds: dict
    if isinstance(inst, dict):
        name = inst.get("instanceName") or inst.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()

    # fallback: dentro de data
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
    key = (data.get("key") or {})
    return bool(key.get("fromMe"))


def extract_phone_e164(payload: Dict[str, Any]) -> Optional[str]:
    """
    Retorna algo como: 553499190547 (sem sufixo @s.whatsapp.net)
    """
    data = payload.get("data", {})
    key = data.get("key", {}) if isinstance(data, dict) else {}
    remote = key.get("remoteJid")

    if isinstance(remote, str) and remote:
        # pode vir "5534...@s.whatsapp.net" ou "@lid" etc
        if "@" in remote:
            num = remote.split("@", 1)[0]
            # se for lid, não é telefone
            if num.isdigit():
                return num
        if remote.isdigit():
            return remote

    # fallback: sender pode vir "553499...@s.whatsapp.net"
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
    """
    Normaliza o conteúdo da mensagem.
    Retorna:
      {"type": "text", "content": "..."}
      {"type": "audio", "url": "...", "mimetype": "...", "seconds": 12, "ptt": true}
      {"type": "image", "url": "...", "caption": "..."}
      {"type": "document", "url": "...", "fileName": "..."}
      {"type": "unknown"}
    """
    data = payload.get("data", {})
    msg = data.get("message", {}) if isinstance(data, dict) else {}

    if not isinstance(msg, dict):
        return {"type": "unknown"}

    # TEXTO (conversa simples)
    conv = msg.get("conversation")
    if isinstance(conv, str) and conv.strip():
        return {"type": "text", "content": conv.strip()}

    # TEXTO (extended)
    ext = msg.get("extendedTextMessage")
    if isinstance(ext, dict):
        txt = ext.get("text")
        if isinstance(txt, str) and txt.strip():
            return {"type": "text", "content": txt.strip()}

    # ÁUDIO
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

    # IMAGEM
    image = msg.get("imageMessage")
    if isinstance(image, dict):
        return {
            "type": "image",
            "url": image.get("url"),
            "caption": image.get("caption"),
            "mimetype": image.get("mimetype"),
            "file_sha256": image.get("fileSha256"),
        }

    # DOCUMENTO
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
    """
    Dedup simples pelo ID do evento (Evolution manda data.key.id)
    """
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return None
    key = data.get("key")
    if not isinstance(key, dict):
        return None
    mid = key.get("id")
    return mid if isinstance(mid, str) and mid.strip() else None


# ---------- Route ----------

@router.post("/{event}")
async def evolution_webhook(event: str, request: Request):
    payload: Dict[str, Any] = await request.json()

    instance_name = extract_instance_name(payload) or "unknown"
    msg_type = "n/a"
    remote_jid = None
    dedup_key = None

    try:
        # log curto inicial
        print(f"EVOLUTION_WEBHOOK: event={event} instance={instance_name}")

        # só mensagens
        if event != "messages-upsert":
            log_ignore(instance_name, "non_message_event", {"event": event})
            return {"ok": True, "ignored": "non_message_event", "event": event}

        # ignore mensagens do próprio número
        if extract_from_me(payload):
            remote_jid = extract_remote_jid(payload)
            log_ignore(instance_name, "from_me", {"remote_jid": remote_jid})
            return {"ok": True, "ignored": "from_me"}

        # ignore grupos por enquanto (remoteJid @g.us)
        remote_jid = extract_remote_jid(payload)
        if isinstance(remote_jid, str) and remote_jid.endswith("@g.us"):
            log_ignore(instance_name, "group_message", {"remote_jid": remote_jid})
            return {"ok": True, "ignored": "group_message"}

        # dedup (evita loop/spam)
        dedup_key = extract_dedup_key(payload)
        if dedup_key:
            is_dup = TenantService.is_duplicate_message(instance_name=instance_name, message_id=dedup_key)
            if is_dup:
                log_ignore(instance_name, "duplicate", {"message_id": dedup_key, "remote_jid": remote_jid})
                return {"ok": True, "ignored": "duplicate", "message_id": dedup_key}
            else:
                log_info(instance_name, "dedup_key_new", {"message_id": dedup_key, "remote_jid": remote_jid})
        else:
            log_info(instance_name, "no_dedup_key", {"remote_jid": remote_jid})

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

        # pega config do tenant
        tenant = TenantService.get_by_evolution_instance(instance_name)
        if not tenant:
            log_ignore(instance_name, "tenant_not_found", {"instance": instance_name, "phone": phone})
            return {"ok": True, "ignored": "tenant_not_found", "instance": instance_name}

        # loga o que vier do tenant (sem vazar token)
        log_info(
            instance_name,
            "tenant_loaded",
            {
                "chatwoot_account_id": tenant.get("chatwoot_account_id"),
                "chatwoot_inbox_id": tenant.get("chatwoot_inbox_id"),
                "has_chatwoot_token": bool(tenant.get("chatwoot_api_token")),
            },
        )

        if not tenant.get("chatwoot_account_id") or not tenant.get("chatwoot_inbox_id") or not tenant.get("chatwoot_api_token"):
            log_ignore(
                instance_name,
                "tenant_chatwoot_not_configured",
                {
                    "chatwoot_account_id": tenant.get("chatwoot_account_id"),
                    "chatwoot_inbox_id": tenant.get("chatwoot_inbox_id"),
                    "has_chatwoot_token": bool(tenant.get("chatwoot_api_token")),
                },
            )
            return {"ok": True, "ignored": "tenant_chatwoot_not_configured", "instance": instance_name}

        cw = ChatwootService(
            base_url=settings.CHATWOOT_BASE_URL,
            api_token=tenant["chatwoot_api_token"],
            account_id=int(tenant["chatwoot_account_id"]),
        )

        # contato + conversa
        contact_name = push_name or phone
        contact = cw.get_or_create_contact(
            name=contact_name,
            phone_e164=f"+{phone}",
        )
        log_info(instance_name, "chatwoot_contact_ok", {"contact_id": contact.get("id"), "name": contact_name, "phone": phone})

        conv = cw.get_or_create_conversation(
            inbox_id=int(tenant["chatwoot_inbox_id"]),
            contact_id=int(contact["id"]),
        )
        log_info(instance_name, "chatwoot_conversation_ok", {"conversation_id": conv.get("id"), "inbox_id": tenant.get("chatwoot_inbox_id")})

        created = None

        # mensagem
        if msg_type == "text":
            content = message.get("content") or "(sem texto)"
            created = cw.create_message(
                conversation_id=int(conv["id"]),
                content=content,
                message_type="incoming",
            )
            log_info(instance_name, "chatwoot_message_text_ok", {"message_id": (created or {}).get("id")})

        elif msg_type == "audio":
            url = message.get("url")
            content = "🎤 Áudio recebido"
            if not url:
                log_info(instance_name, "audio_without_url", {"note": "registrando apenas texto"})
            created = cw.create_message(
                conversation_id=int(conv["id"]),
                content=content,
                message_type="incoming",
                attachments=[{"file_type": "audio", "external_url": url}] if url else None,
            )
            log_info(instance_name, "chatwoot_message_audio_ok", {"message_id": (created or {}).get("id"), "has_url": bool(url)})

        elif msg_type == "image":
            url = message.get("url")
            caption = message.get("caption") or "🖼️ Imagem recebida"
            if not url:
                log_info(instance_name, "image_without_url", {"note": "registrando apenas texto"})
            created = cw.create_message(
                conversation_id=int(conv["id"]),
                content=caption,
                message_type="incoming",
                attachments=[{"file_type": "image", "external_url": url}] if url else None,
            )
            log_info(instance_name, "chatwoot_message_image_ok", {"message_id": (created or {}).get("id"), "has_url": bool(url)})

        elif msg_type == "document":
            url = message.get("url")
            fname = message.get("fileName") or "📎 Documento recebido"
            if not url:
                log_info(instance_name, "document_without_url", {"note": "registrando apenas texto"})
            created = cw.create_message(
                conversation_id=int(conv["id"]),
                content=fname,
                message_type="incoming",
                attachments=[{"file_type": "file", "external_url": url}] if url else None,
            )
            log_info(instance_name, "chatwoot_message_document_ok", {"message_id": (created or {}).get("id"), "has_url": bool(url)})

        else:
            log_ignore(instance_name, "unhandled_type", {"type": msg_type})
            return {"ok": True, "ignored": "unhandled_type", "type": msg_type}

        # marca dedup como processado
        if dedup_key:
            TenantService.mark_message_processed(instance_name=instance_name, message_id=dedup_key)
            log_info(instance_name, "dedup_marked_processed", {"message_id": dedup_key})

        print(f"EVOLUTION_WEBHOOK_OK: instance={instance_name} type={msg_type} chatwoot_conv={conv.get('id')}")

        return {
            "ok": True,
            "instance_name": instance_name,
            "type": msg_type,
            "chatwoot": {
                "contact_id": contact.get("id"),
                "conversation_id": conv.get("id"),
                "message_id": (created or {}).get("id"),
            },
        }

    except Exception as e:
        # webhook NÃO pode derrubar com 500 (senão vira retry infinito)
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
        return {"ok": True, "ignored": "exception", "error": str(e)}
