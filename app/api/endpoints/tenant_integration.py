from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Any, Dict, Optional
from app.core.config import settings
from app.api.services.tenant_service import TenantService
from app.db.session import SessionLocal
from app.api.services.tenant_integration_service import TenantIntegrationService
from app.api.services.evolution_service import EvolutionService
from app.api.services.chatwoot_service import ChatwootService

router = APIRouter(prefix="/integrations/chatwoot", tags=["Chatwoot Integration"])


def _log_info(msg: str, extra: dict | None = None):
    extra = extra or {}
    print(f"CHATWOOT_EVT_INFO: msg={msg} extra={extra}")


def _log_ignore(reason: str, extra: dict | None = None):
    extra = extra or {}
    print(f"CHATWOOT_EVT_IGNORED: reason={reason} extra={extra}")


def _log_err(msg: str, extra: dict | None = None):
    extra = extra or {}
    print(f"CHATWOOT_EVT_ERROR: msg={msg} extra={extra}")


def _safe_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None

def _extract_id(source: Any) -> Optional[int]:
    """
    Helper para extrair o ID de um objeto (dict) ou retornar o valor se já for int/str numérico.
    """
    if source is None:
        return None
    
    # Se já for um inteiro
    if isinstance(source, int):
        return source
        
    # Se for um dicionário, tenta pegar a chave "id"
    if isinstance(source, dict):
        return _safe_int(source.get("id"))
        
    # Tenta converter string numérica
    return _safe_int(source)


def _extract_event_name(payload: Dict[str, Any]) -> str:
    # dependendo da versão do Chatwoot pode vir "event", "type", etc.
    return (
        (payload.get("event") or payload.get("type") or payload.get("name") or "unknown")
        if isinstance(payload, dict)
        else "unknown"
    )

def _extract_contact_id(conv: Dict[str, Any]) -> Optional[int]:
    # conv["contact"]["id"]
    c = conv.get("contact")
    if isinstance(c, dict):
        v = c.get("id")
        try:
            return int(v) if v is not None else None
        except Exception:
            pass

    # conv["contact_id"]
    v = conv.get("contact_id")
    try:
        return int(v) if v is not None else None
    except Exception:
        return None


def _extract_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chatwoot pode enviar:
      A) payload["message"] = {...}
      B) "mensagem no root" (payload já tem content/message_type/etc)
    """
    msg = payload.get("message")
    if isinstance(msg, dict) and msg:
        return msg

    # fallback: payload é a própria msg (se tiver cara de msg)
    if isinstance(payload.get("content"), str) or payload.get("message_type") in ("incoming", "outgoing"):
        return payload

    return {}



def _extract_conversation(payload: Dict[str, Any]) -> Dict[str, Any]:
    conv = payload.get("conversation")
    return conv if isinstance(conv, dict) else {}


def _extract_account_id(payload: Dict[str, Any], conv: Dict[str, Any]) -> Optional[int]:
    # às vezes vem em payload["account"]["id"], às vezes em conversation["account_id"]
    acc = payload.get("account")
    if isinstance(acc, dict):
        v = _safe_int(acc.get("id"))
        if v:
            return v
    return _safe_int(conv.get("account_id"))


def _extract_inbox_id(conv: Dict[str, Any]) -> Optional[int]:
    # pode vir direto: conversation["inbox_id"]
    v = _safe_int(conv.get("inbox_id"))
    if v:
        return v
    # ou: conversation["inbox"]["id"]
    inbox = conv.get("inbox")
    if isinstance(inbox, dict):
        return _safe_int(inbox.get("id"))
    return None


def _extract_recipient_phone(payload: Dict[str, Any], conv: Dict[str, Any]) -> Optional[str]:
    """
    Precisamos do telefone do contato pra enviar no WhatsApp via Evolution.
    O Chatwoot costuma enviar o contato dentro de conversation["contact"].
    """
    contact = conv.get("contact")
    if isinstance(contact, dict):
        # dependendo do modelo: "phone_number", "phone", etc.
        for k in ("phone_number", "phone", "phoneNumber"):
            v = contact.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    # fallback: alguns payloads trazem message["sender"]["phone_number"]
    msg = _extract_message(payload)
    sender = msg.get("sender")
    if isinstance(sender, dict):
        for k in ("phone_number", "phone"):
            v = sender.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    return None


def _normalize_phone_for_evolution(phone: str) -> str:
    """
    Evolution geralmente quer só dígitos (DDD+numero+pais) ou dependendo do endpoint.
    Aqui vamos remover + e espaços.
    """
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits


@router.post("/events")
async def chatwoot_events(
    request: Request,
    secret: str = Query(default=""),
):
    """
    Recebe eventos do ChatChatwoot.
    Você já validou secret via querystring.
    Aqui vamos processar outgoing e mandar para Evolution.
    """
    payload: Dict[str, Any] = await request.json()

    event_name = _extract_event_name(payload)
    msg = _extract_message(payload)
    conv = _extract_conversation(payload)

    # logs iniciais (preview sem vazar conteúdo gigante)
    _log_info(
        "received",
        {
            "event": event_name,
            "payload_keys": list(payload.keys()) if isinstance(payload, dict) else None,
            "has_message": bool(msg),
            "has_conversation": bool(conv),
        },
    )

    try:
        # 1) filtra evento que não interessa
        # O que interessa aqui: criação/atualização de mensagem
        # (nome varia, então filtramos pelo presence do campo message)
        if not msg or not conv:
            _log_ignore("missing_message_or_conversation", {"event": event_name})
            return {"ok": True}

        # 2) só outgoing (Chatwoot → WhatsApp)
        # Em várias versões: message_type pode ser "incoming"/"outgoing"
        message_type = msg.get("message_type") or msg.get("type")
        if message_type != "outgoing":
            _log_ignore("not_outgoing", {"message_type": message_type, "event": event_name})
            return {"ok": True}

        # 3) ignora nota privada
        if bool(msg.get("private")):
            _log_ignore("private_note", {"event": event_name})
            return {"ok": True}

        # 4) resolve account_id + inbox_id
        account_id = _extract_account_id(payload, conv)
        inbox_id = _extract_inbox_id(conv)

        if not account_id:
            _log_ignore("missing_account_id", {"event": event_name})
            return {"ok": True}
        if not inbox_id:
            _log_ignore("missing_inbox_id", {"event": event_name, "account_id": account_id})
            return {"ok": True}

        _log_info("routing_keys", {"account_id": account_id, "inbox_id": inbox_id})

        # 5) resolve user_id do “tenant”/médico pelo binding que você criou
        db = SessionLocal()
        try:
            user_id = TenantIntegrationService.resolve_user_id(
                db=db,
                chatwoot_account_id=account_id,
                chatwoot_inbox_id=inbox_id,
            )
        finally:
            db.close()

        _log_info("tenant_resolved", {"user_id": user_id, "account_id": account_id, "inbox_id": inbox_id})

        # 6) pega integration completa (pra pegar evolution_instance_id e evolution_phone)
        db = SessionLocal()
        try:
            integration = (
                db.query(__import__("app.api.models.tenant_integration", fromlist=["TenantIntegration"]).TenantIntegration)
                .filter_by(user_id=user_id)
                .first()
            )
        finally:
            db.close()

        if not integration:
            _log_ignore("integration_not_found", {"user_id": user_id})
            return {"ok": True}

        if not getattr(integration, "evolution_instance_id", None):
            _log_ignore("missing_evolution_instance", {"user_id": user_id})
            return {"ok": True}

        instance_name = str(integration.evolution_instance_id)

       # 7) extrai telefone do destinatário
        raw_phone = _extract_recipient_phone(payload, conv)

        if not raw_phone:
            contact_id = _extract_contact_id(conv)
            
            # Tenta pegar token da integração ou o Global das configurações
            chatwoot_token = getattr(integration, "chatwoot_api_token", None) or getattr(settings, "CHATWOOT_API_TOKEN_GLOBAL", None)
            
            # --- DEBUG: Verifica por que a API não está sendo chamada ---
            conversation_id = _extract_id(conv) or _safe_int(conv.get("id"))
            _log_info("debug_fallback_check", {
                "has_phone": bool(raw_phone),
                "contact_id_local": contact_id,
                "has_token": bool(chatwoot_token),
                "conv_id": conversation_id
            })
            # ------------------------------------------------------------

            if not contact_id and chatwoot_token and conversation_id:
                try:
                    _log_info("fetching_conversation_details", {"conv_id": conversation_id})
                    cw_temp = ChatwootService(
                        base_url=settings.CHATWOOT_BASE_URL,
                        api_token=chatwoot_token,
                        account_id=account_id,
                    )
                    full_conv_data = cw_temp.get_conversation(conversation_id)
                    
                    # Debug da resposta da API para garantir que estamos pegando o campo certo
                    meta = full_conv_data.get("meta", {})
                    # _log_info("api_response_structure", {"meta_keys": list(meta.keys())})

                    # Tenta pegar o contato (cliente) dentro de meta
                    contact_obj = meta.get("contact")
                    
                    if isinstance(contact_obj, dict):
                        contact_id = contact_obj.get("id")
                        # Se a API já devolver o telefone, pegamos aqui!
                        if not raw_phone:
                            raw_phone = contact_obj.get("phone_number")
                    
                    # Fallback: tenta pegar do contact_inbox
                    if not contact_id:
                        contact_id = _extract_contact_id(full_conv_data)
                        
                except Exception as e:
                    _log_err("failed_fetching_conversation", {"error": str(e)})

            if not contact_id:
                # Se falhar aqui, verifique se "has_token" deu False no log acima
                _log_ignore(
                    "missing_recipient_phone",
                    {"note": "no phone in payload and could not resolve contact_id via API", "user_id": user_id},
                )
                return {"ok": True}

            if not chatwoot_token:
                _log_ignore("missing_chatwoot_token_for_lookup", {"user_id": user_id})
                return {"ok": True}

            # Se ainda não temos o telefone, mas temos o contact_id, buscamos o contato
            if not raw_phone:
                cw = ChatwootService(
                    base_url=settings.CHATWOOT_BASE_URL,
                    api_token=chatwoot_token,
                    account_id=account_id,
                )
                contact_payload = cw.get_contact(contact_id)
                raw_phone = ChatwootService.extract_phone_from_contact(contact_payload)

            if not raw_phone:
                _log_ignore(
                    "missing_recipient_phone",
                    {"note": "contact fetched but phone empty", "contact_id": contact_id},
                )
                return {"ok": True}

        to_phone = _normalize_phone_for_evolution(raw_phone)

        # ... (continua para o passo 8 normalmente)


        # 8) detectar se é texto ou áudio
        content = (msg.get("content") or "").strip()

        # anexos: em algumas versões vem em msg["attachments"] como lista
        attachments = msg.get("attachments")
        attachments = attachments if isinstance(attachments, list) else []

        _log_info(
            "outgoing_parsed",
            {
                "user_id": user_id,
                "instance": instance_name,
                "to": to_phone,
                "content_len": len(content),
                "attachments_count": len(attachments),
            },
        )

        # Se tiver attachment de áudio, manda áudio.
        # Caso contrário, manda texto.
        sent = None

        audio_url = None
        for att in attachments:
            if not isinstance(att, dict):
                continue
            # dependendo do Chatwoot, pode ser "file_type", "file_type"="audio" ou "content_type" etc.
            ft = (att.get("file_type") or att.get("type") or "").lower()
            ct = (att.get("content_type") or "").lower()
            if ft == "audio" or ct.startswith("audio/"):
                # url pode variar: "data_url", "url", "file_url"
                audio_url = att.get("data_url") or att.get("url") or att.get("file_url")
                break

        if audio_url:
            _log_info("sending_audio", {"to": to_phone, "has_url": True})
            sent = EvolutionService.send_audio(
                instance_name=instance_name,
                to_number=to_phone,
                audio_url=audio_url,
            )
        else:
            if not content:
                _log_ignore("empty_content_no_audio", {"to": to_phone})
                return {"ok": True}
            _log_info("sending_text", {"to": to_phone, "preview": content[:80]})
            sent = EvolutionService.send_text(
                instance_name=instance_name,
                to_number=to_phone,
                text=content,
            )

        _log_info("sent_ok", {"to": to_phone, "instance": instance_name, "result_keys": list(sent.keys()) if isinstance(sent, dict) else None})
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        _log_err("exception", {"event": event_name, "error": repr(e)})
        return {"ok": True}
