from fastapi import APIRouter, Request, HTTPException
from typing import Any, Dict, Optional

from app.core.config import settings
from app.api.services.chatwoot_service import ChatwootService

router = APIRouter(prefix="/webhooks/evolution", tags=["Evolution Webhooks"])


def extract_instance_name(payload: Dict[str, Any]) -> Optional[str]:
    # tenta achar instanceName nos lugares mais comuns
    return (
        payload.get("instanceName")
        or payload.get("instance_name")
        or (payload.get("instance") or {}).get("instanceName")
        or (payload.get("instance") or {}).get("instance_name")
    )


def extract_message_text(payload: Dict[str, Any]) -> Optional[str]:
    """
    EVOLUTION varia MUITO.
    Aqui é um extractor tolerante. Ajusta depois com um payload real do teu messages-upsert.
    """
    # alguns formatos:
    # payload["data"]["message"]["conversation"]...
    data = payload.get("data") or payload
    msg = data.get("message") or data.get("messages") or data.get("messagesUpsert") or data

    if isinstance(msg, dict):
        # tentativas comuns
        return (
            msg.get("text")
            or (msg.get("message") or {}).get("text")
            or (msg.get("content") or {}).get("text")
            or msg.get("conversation")
        )

    return None


def extract_phone(payload: Dict[str, Any]) -> Optional[str]:
    """
    Tenta pegar o telefone do remetente.
    """
    data = payload.get("data") or payload
    # tentativas comuns (ajusta depois com payload real)
    return (
        data.get("from")
        or data.get("sender")
        or (data.get("key") or {}).get("remoteJid")
        or (data.get("message") or {}).get("from")
    )


@router.post("/{event}")
async def evolution_webhook(event: str, request: Request):
    payload: Dict[str, Any] = await request.json()

    print("EVOLUTION_WEBHOOK:", event)
    print("====== EVOLUTION WEBHOOK ======")
    print("EVENT:", event)
    print("PAYLOAD:")
    print(payload)
    print("================================")
    
    # só processa mensagem aqui (o resto você pode logar/ignorar)
    if event != "messages-upsert":
        return {"ok": True, "event": event}

    instance_name = extract_instance_name(payload)
    if not instance_name:
        raise HTTPException(status_code=400, detail="Missing instance_name in webhook payload")

    # TODO: AQUI é onde você busca o tenant no banco pelo instance_name
    # Exemplo (você vai adaptar pro teu model/repo):
    # tenant = TenantService.get_by_evolution_instance(instance_name)
    #
    # Vou simular o formato esperado:
    tenant = {
        "chatwoot_account_id": None,
        "chatwoot_inbox_id": None,
        "chatwoot_api_token": None,
    }

    if not tenant["chatwoot_account_id"] or not tenant["chatwoot_inbox_id"] or not tenant["chatwoot_api_token"]:
        raise HTTPException(
            status_code=409,
            detail="Tenant Chatwoot not configured (account_id/inbox_id/api_token missing)",
        )

    phone = extract_phone(payload) or "unknown"
    text = extract_message_text(payload) or "(sem texto)"
    contact_name = phone  # depois você melhora com profile pushname

    cw = ChatwootService(
        base_url=settings.CHATWOOT_BASE_URL,
        api_token=tenant["chatwoot_api_token"],
        account_id=tenant["chatwoot_account_id"],
    )

    # 1) cria contato
    contact = cw.create_contact(name=contact_name, phone_e164=phone)

    # 2) cria conversa na inbox do tenant
    conv = cw.create_conversation(inbox_id=tenant["chatwoot_inbox_id"], contact_id=contact["id"])

    # 3) cria mensagem incoming
    msg = cw.create_message(conversation_id=conv["id"], content=text, message_type="incoming")

    return {"ok": True, "event": event, "instance_name": instance_name, "chatwoot": {"contact": contact["id"], "conversation": conv["id"], "message": msg["id"]}}
