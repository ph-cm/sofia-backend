from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

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

@router.post(
    "/chatwoot/events",
    dependencies=[Depends(verify_n8n_api_key)],
)
async def chatwoot_events(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    # 1) filtra eventos que você não quer processar
    if payload.get("event") != "message_created":
        return {"ok": True, "ignored": True, "reason": "not_message_created"}

    # 2) se você só quer saída do agente (ou seja, mensagem enviada pelo bot/agente)
    if payload.get("message_type") != "outgoing":
        return {"ok": True, "ignored": True, "reason": "not_outgoing"}

    inbox = payload.get("inbox") or {}
    sender = payload.get("sender") or {}
    account = sender.get("account") or {}

    inbox_id = inbox.get("id")
    account_id = account.get("id")
    content = payload.get("content")

    if not inbox_id or not account_id:
        raise HTTPException(status_code=400, detail="Missing inbox.id or sender.account.id")

    user_id = TenantIntegrationService.resolve_user_id(
        db=db,
        chatwoot_account_id=account_id,
        chatwoot_inbox_id=inbox_id,
    )

    return {
        "ok": True,
        "user_id": user_id,
        "account_id": account_id,
        "inbox_id": inbox_id,
        "content_preview": (content or "")[:80],
    }
