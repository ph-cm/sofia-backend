from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.api.models.user import User
from app.schemas.tenant_integration import TenantContextIn, TenantContextOut

from app.db.session import get_db
from app.core.security import get_current_user, verify_n8n_api_key
from app.schemas.tenant_integration import (
    BindChatwootIn,
    BindChatwootOut,
    ResolveTenantIn,
    ResolveTenantOut,
)
from app.api.services.tenant_integration_service import TenantIntegrationService

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.post("/chatwoot/bind", response_model=BindChatwootOut, dependencies=[Depends(verify_n8n_api_key)])
def bind_chatwoot(payload: BindChatwootIn, db: Session = Depends(get_db)):
    integration = TenantIntegrationService.bind_chatwoot(
        db=db,
        user_id=payload.user_id,  # 🔥 vem do payload
        chatwoot_account_id=payload.chatwoot_account_id,
        chatwoot_inbox_id=payload.chatwoot_inbox_id,
        chatwoot_inbox_identifier=payload.chatwoot_inbox_identifier,
        evolution_instance_id=payload.evolution_instance_id,
        evolution_phone=payload.evolution_phone,
    )
    return BindChatwootOut(
        ok=True,
        user_id=integration.user_id,
        chatwoot_account_id=integration.chatwoot_account_id,
        chatwoot_inbox_id=integration.chatwoot_inbox_id,
    )


@router.post(
    "/chatwoot/resolve-tenant",
    response_model=ResolveTenantOut,
    dependencies=[Depends(verify_n8n_api_key)],
)
def resolve_tenant(payload: ResolveTenantIn, db: Session = Depends(get_db)):
    user_id = TenantIntegrationService.resolve_user_id(
        db=db,
        chatwoot_account_id=payload.chatwoot_account_id,
        chatwoot_inbox_id=payload.chatwoot_inbox_id,
    )
    return ResolveTenantOut(user_id=user_id)


from fastapi import Body
from typing import Any, Dict
from fastapi import Query
from app.core.config import settings

@router.post("/chatwoot/events")
async def chatwoot_events(
    payload: dict = Body(...),
    secret: str = Query(...),
    db: Session = Depends(get_db),
):
    if secret != settings.CHATWOOT_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    if payload.get("event") != "message_created":
        return {"ok": True, "ignored": True, "reason": "not_message_created"}

    inbox = payload.get("inbox") or {}
    sender = payload.get("sender") or {}
    account = (sender.get("account") or {})

    inbox_id = inbox.get("id")
    account_id = account.get("id")
    content = payload.get("content")
    msg_type = payload.get("message_type")  # "incoming" ou "outgoing"

    if not inbox_id or not account_id:
        return {"ok": True, "ignored": True, "reason": "missing_ids"}

    # resolve tenant SEMPRE (incoming e outgoing)
    user_id = TenantIntegrationService.resolve_user_id(
        db=db,
        chatwoot_account_id=account_id,
        chatwoot_inbox_id=inbox_id,
    )

    # aqui você só "observa"
    return {
        "ok": True,
        "message_type": msg_type,
        "user_id": user_id,
        "account_id": account_id,
        "inbox_id": inbox_id,
        "content_preview": (content or "")[:80],
    }

@router.post(
    "/chatwoot/tenant-context",
    response_model=TenantContextOut,
    dependencies=[Depends(verify_n8n_api_key)],
)
def tenant_context(payload: TenantContextIn, db: Session = Depends(get_db)):
    # 1) resolve tenant pelo mapeamento Chatwoot → user_id
    user_id = TenantIntegrationService.resolve_user_id(
        db=db,
        chatwoot_account_id=payload.chatwoot_account_id,
        chatwoot_inbox_id=payload.chatwoot_inbox_id,
    )

    # 2) busca o médico no banco
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 3) devolve um contexto "compatível com n8n"
    return TenantContextOut(
        ok=True,
        user_id=user_id,
        chatwoot_account_id=payload.chatwoot_account_id,
        chatwoot_inbox_id=payload.chatwoot_inbox_id,
        tenant={
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "phone_channel": user.phone_channel,
            "calendar_id": user.calendar_id,
            "timezone": user.timezone,
            "duracao_consulta": user.duracao_consulta,
            "valor_consulta": user.valor_consulta,
            "ativo": user.ativo,
            "inbox_id": user.inbox_id,  # se ainda estiver usando
        },
    )