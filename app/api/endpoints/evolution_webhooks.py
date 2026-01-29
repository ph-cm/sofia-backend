from __future__ import annotations

from fastapi import APIRouter, Request
from typing import Any, Dict, Optional

from app.core.config import settings
from app.api.services.chatwoot_service import ChatwootService
from app.api.services.tenant_service import TenantService

router = APIRouter(prefix="/webhooks/evolution", tags=["Evolution Webhooks"])


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

    try:
        # log curto
        print(f"EVOLUTION_WEBHOOK: {event} instance={instance_name}")

        # só mensagens
        if event != "messages-upsert":
            return {"ok": True}

        # ignore mensagens do próprio número
        if extract_from_me(payload):
            return {"ok": True, "ignored": "from_me"}

        # ignore grupos por enquanto (remoteJid @g.us)
        remote_jid = extract_remote_jid(payload)
        if isinstance(remote_jid, str) and remote_jid.endswith("@g.us"):
            return {"ok": True, "ignored": "group_message"}

        # dedup (evita 409 / loop / spam)
        dedup_key = extract_dedup_key(payload)
        if dedup_key and TenantService.is_duplicate_message(instance_name=instance_name, message_id=dedup_key):
            return {"ok": True, "ignored": "duplicate", "message_id": dedup_key}

        message = extract_message(payload)
        msg_type = message.get("type", "unknown")
        if msg_type == "unknown":
            return {"ok": True, "ignored": "unsupported_message"}

        phone = extract_phone_e164(payload)
        push_name = extract_push_name(payload)
        if not phone:
            return {"ok": True, "ignored": "no_phone"}

        # pega config do tenant
        tenant = TenantService.get_by_evolution_instance(instance_name)
        if not tenant:
            return {"ok": True, "ignored": "tenant_not_found", "instance": instance_name}

        if not tenant.get("chatwoot_account_id") or not tenant.get("chatwoot_inbox_id") or not tenant.get("chatwoot_api_token"):
            return {"ok": True, "ignored": "tenant_chatwoot_not_configured", "instance": instance_name}

        cw = ChatwootService(
            base_url=settings.CHATWOOT_BASE_URL,
            api_token=tenant["chatwoot_api_token"],
            account_id=int(tenant["chatwoot_account_id"]),
        )

        # contato + conversa
        contact = cw.get_or_create_contact(
            name=push_name or phone,
            phone_e164=f"+{phone}",  # Chatwoot costuma aceitar E.164 com +
        )

        conv = cw.get_or_create_conversation(
            inbox_id=int(tenant["chatwoot_inbox_id"]),
            contact_id=int(contact["id"]),
        )

        # mensagem
        if msg_type == "text":
            content = message.get("content") or "(sem texto)"
            created = cw.create_message(
                conversation_id=int(conv["id"]),
                content=content,
                message_type="incoming",
            )

        elif msg_type == "audio":
            url = message.get("url")
            # se não vier url, ainda registra evento
            content = "🎤 Áudio recebido"
            created = cw.create_message(
                conversation_id=int(conv["id"]),
                content=content,
                message_type="incoming",
                attachments=[{
                    "file_type": "audio",
                    "external_url": url,
                }] if url else None,
            )

        elif msg_type == "image":
            url = message.get("url")
            caption = message.get("caption") or "🖼️ Imagem recebida"
            created = cw.create_message(
                conversation_id=int(conv["id"]),
                content=caption,
                message_type="incoming",
                attachments=[{
                    "file_type": "image",
                    "external_url": url,
                }] if url else None,
            )

        elif msg_type == "document":
            url = message.get("url")
            fname = message.get("fileName") or "📎 Documento recebido"
            created = cw.create_message(
                conversation_id=int(conv["id"]),
                content=fname,
                message_type="incoming",
                attachments=[{
                    "file_type": "file",
                    "external_url": url,
                }] if url else None,
            )
        else:
            return {"ok": True, "ignored": "unhandled_type", "type": msg_type}

        # marca dedup como processado
        if dedup_key:
            TenantService.mark_message_processed(instance_name=instance_name, message_id=dedup_key)

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
        print(f"EVOLUTION_WEBHOOK_ERR: instance={instance_name} type={msg_type} err={repr(e)}")
        return {"ok": True, "ignored": "exception", "error": str(e)}
