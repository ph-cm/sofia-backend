from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Any, Dict, Optional
from app.core.config import settings
from app.api.services.tenant_service import TenantService
from app.db.session import SessionLocal
from app.api.services.tenant_integration_service import TenantIntegrationService
from app.api.services.evolution_service import EvolutionService
from app.api.services.chatwoot_service import ChatwootService
from app.api.services.conversation_map_service import ConversationMapService

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
        if v is None: return None
        return int(v)
    except Exception:
        return None

def _extract_id(source: Any) -> Optional[int]:
    if source is None: return None
    if isinstance(source, int): return source
    if isinstance(source, dict): return _safe_int(source.get("id"))
    return _safe_int(source)

def _extract_event_name(payload: Dict[str, Any]) -> str:
    return (payload.get("event") or payload.get("type") or payload.get("name") or "unknown") if isinstance(payload, dict) else "unknown"

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

def _extract_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    msg = payload.get("message")
    if isinstance(msg, dict) and msg: return msg
    if isinstance(payload.get("content"), str) or payload.get("message_type") in ("incoming", "outgoing"):
        return payload
    return {}

def _extract_conversation(payload: Dict[str, Any]) -> Dict[str, Any]:
    conv = payload.get("conversation")
    return conv if isinstance(conv, dict) else {}

def _extract_account_id(payload: Dict[str, Any], conv: Dict[str, Any]) -> Optional[int]:
    acc = payload.get("account")
    if isinstance(acc, dict):
        v = _safe_int(acc.get("id"))
        if v: return v
    return _safe_int(conv.get("account_id"))

def _extract_inbox_id(conv: Dict[str, Any]) -> Optional[int]:
    v = _safe_int(conv.get("inbox_id"))
    if v: return v
    inbox = conv.get("inbox")
    if isinstance(inbox, dict): return _safe_int(inbox.get("id"))
    return None

def _extract_recipient_phone(payload: Dict[str, Any], conv: Dict[str, Any]) -> Optional[str]:
    contact = conv.get("contact")
    if isinstance(contact, dict):
        for k in ("phone_number", "phone", "phoneNumber"):
            v = contact.get(k)
            if isinstance(v, str) and v.strip(): return v.strip()
    msg = _extract_message(payload)
    sender = msg.get("sender")
    if isinstance(sender, dict):
        for k in ("phone_number", "phone"):
            v = sender.get(k)
            if isinstance(v, str) and v.strip(): return v.strip()
    return None

def _normalize_phone_for_evolution(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())

@router.post("/events")
async def chatwoot_events(request: Request, secret: str = Query(default="")):
    payload: Dict[str, Any] = await request.json()
    event_name = _extract_event_name(payload)
    msg = _extract_message(payload)
    conv = _extract_conversation(payload)

    _log_info("received", {"event": event_name, "has_message": bool(msg), "has_conversation": bool(conv)})

    try:
        if not msg or not conv:
            _log_ignore("missing_message_or_conversation", {"event": event_name})
            return {"ok": True}

        message_type = msg.get("message_type") or msg.get("type")
        if message_type != "outgoing":
            _log_ignore("not_outgoing", {"message_type": message_type, "event": event_name})
            return {"ok": True}

        if bool(msg.get("private")):
            _log_ignore("private_note", {"event": event_name})
            return {"ok": True}

        account_id = _extract_account_id(payload, conv)
        inbox_id = _extract_inbox_id(conv)
        if not account_id or not inbox_id:
            _log_ignore("missing_ids", {"account_id": account_id, "inbox_id": inbox_id})
            return {"ok": True}

        # _log_info("routing_keys", {"account_id": account_id, "inbox_id": inbox_id})

        db = SessionLocal()
        try:
            user_id = TenantIntegrationService.resolve_user_id(db=db, chatwoot_account_id=account_id, chatwoot_inbox_id=inbox_id)
        finally:
            db.close()

        _log_info("tenant_resolved", {"user_id": user_id, "account_id": account_id, "inbox_id": inbox_id})

        db = SessionLocal()
        try:
            integration = (
                db.query(__import__("app.api.models.tenant_integration", fromlist=["TenantIntegration"]).TenantIntegration)
                .filter_by(user_id=user_id)
                .first()
            )
        finally:
            db.close()

        if not integration or not getattr(integration, "evolution_instance_id", None):
            _log_ignore("no_integration_or_instance", {"user_id": user_id})
            return {"ok": True}

        instance_name = str(integration.evolution_instance_id)

        # =========================================================================
        # 7) RESOLUÇÃO DE TELEFONE (ROBUSTA)
        # =========================================================================
        
        # Tentativa 1: Payload direto
        raw_phone = _extract_recipient_phone(payload, conv)
        
        # Garante que temos o ID da conversa (essencial para as próximas etapas)
        conversation_id = _extract_id(conv) or _safe_int(conv.get("id"))

        # Tentativa 2: Banco de Dados (Map)
        if not raw_phone and conversation_id:
            db_map = SessionLocal()
            try:
                mapped_phone = ConversationMapService.get_phone_by_conversation(
                    db=db_map,
                    chatwoot_account_id=int(account_id),
                    chatwoot_conversation_id=int(conversation_id)
                )
                if mapped_phone:
                    raw_phone = mapped_phone
                    _log_info("phone_resolved_via_map", {"conv_id": conversation_id, "phone": raw_phone})
            except Exception as e:
                _log_err("map_service_error", {"error": str(e)})
            finally:
                db_map.close()

        # Tentativa 3: API do Chatwoot (Fallback Final com Debug e Múltiplas Estratégias)
        if not raw_phone:
            chatwoot_token = getattr(integration, "chatwoot_api_token", None) or getattr(settings, "CHATWOOT_API_TOKEN", None)
            
            _log_info("api_fallback_check", {
                "token_present": bool(chatwoot_token), 
                "conv_id": conversation_id
            })

            if chatwoot_token and conversation_id:
                try:
                    cw_temp = ChatwootService(
                        base_url=settings.CHATWOOT_BASE_URL,
                        api_token=chatwoot_token,
                        account_id=account_id,
                    )
                    full_conv = cw_temp.get_conversation(conversation_id)

                    # --- DEBUG: Imprime o começo do JSON para vermos a estrutura real ---
                    import json
                    try:
                        # Imprime os primeiros 600 caracteres para não poluir demais, mas mostrar o inicio
                        print(f"DEBUG_API_RESPONSE: {json.dumps(full_conv, default=str)[:600]}")
                    except: 
                        print("DEBUG_API_RESPONSE: (erro ao converter json)")
                    # -------------------------------------------------------------------
                    
                    # Estratégia 3.A: contact_inbox -> source_id (Geralmente é o telefone/UID no WhatsApp)
                    ci = full_conv.get("contact_inbox")
                    if isinstance(ci, dict):
                        raw_phone = ci.get("source_id")
                        if raw_phone: _log_info("phone_found_in_contact_inbox", {"val": raw_phone})

                    # Estratégia 3.B: meta -> sender -> phone_number
                    if not raw_phone:
                        meta = full_conv.get("meta", {})
                        sender = meta.get("sender")
                        if isinstance(sender, dict):
                            raw_phone = sender.get("phone_number")
                            if raw_phone: _log_info("phone_found_in_meta_sender", {"val": raw_phone})

                    # Estratégia 3.C: meta -> contact -> phone_number
                    if not raw_phone:
                        meta = full_conv.get("meta", {})
                        contact_obj = meta.get("contact")
                        if isinstance(contact_obj, dict):
                            raw_phone = contact_obj.get("phone_number")
                            if raw_phone: _log_info("phone_found_in_meta_contact", {"val": raw_phone})

                    # Estratégia 3.D: Busca ID do contato e faz nova chamada (O mais lento, mas garantido)
                    if not raw_phone:
                        cid_temp = _extract_contact_id(full_conv)
                        if cid_temp:
                            _log_info("fetching_contact_directly", {"contact_id": cid_temp})
                            c_data = cw_temp.get_contact(cid_temp)
                            raw_phone = ChatwootService.extract_phone_from_contact(c_data)

                    # Se achou em qualquer estratégia, salva no Map (Self-Healing)
                    if raw_phone:
                        try:
                            db_save = SessionLocal()
                            ConversationMapService.upsert_map(
                                db=db_save,
                                chatwoot_account_id=int(account_id),
                                chatwoot_conversation_id=int(conversation_id),
                                wa_phone_digits=_normalize_phone_for_evolution(raw_phone),
                            )
                            db_save.commit()
                            db_save.close()
                        except: pass

                except Exception as ex_api:
                    _log_err("api_fallback_failed", {"error": str(ex_api)})

        if not raw_phone:
            _log_ignore("missing_recipient_phone", {"note": "failed all strategies", "conv_id": conversation_id})
            return {"ok": True}

        to_phone = _normalize_phone_for_evolution(raw_phone)
        
        # =========================================================================

        content = (msg.get("content") or "").strip()
        attachments = msg.get("attachments") or []

        _log_info("sending_msg", {"instance": instance_name, "to": to_phone, "content_len": len(content)})

        audio_url = None
        for att in attachments:
            if not isinstance(att, dict): continue
            ft = (att.get("file_type") or att.get("type") or "").lower()
            ct = (att.get("content_type") or "").lower()
            if ft == "audio" or ct.startswith("audio/"):
                audio_url = att.get("data_url") or att.get("url") or att.get("file_url")
                break

        if audio_url:
            EvolutionService.send_audio(instance_name=instance_name, to_number=to_phone, audio_url=audio_url)
        else:
            if not content:
                return {"ok": True}
            EvolutionService.send_text(instance_name=instance_name, to_number=to_phone, text=content)

        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        _log_err("exception", {"event": event_name, "error": repr(e)})
        return {"ok": True}