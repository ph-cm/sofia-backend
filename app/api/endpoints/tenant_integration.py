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


@router.post("/chatwoot/bind", response_model=BindChatwootOut)
def bind_chatwoot(
    payload: BindChatwootIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    integration = TenantIntegrationService.bind_chatwoot(
        db=db,
        user_id=current_user["id"],
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


@router.post(
    "/chatwoot/events",
    dependencies=[Depends(verify_n8n_api_key)],
)
async def chatwoot_events(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()

    if payload.get("event") != "message_created":
        return {"ok": True, "ignored": True}

    if payload.get("message_type") != "outgoing":
        return {"ok": True, "ignored": True, "reason": "not_outgoing"}

    inbox = payload.get("inbox") or {}
    sender = payload.get("sender") or {}
    account = sender.get("account") or {}

    inbox_id = inbox.get("id")
    account_id = account.get("id")
    content = payload.get("content")

    if not inbox_id or not account_id:
        raise HTTPException(status_code=400, detail="Missing inbox_id or account_id")

    user_id = TenantIntegrationService.resolve_user_id(
        db, chatwoot_account_id=account_id, chatwoot_inbox_id=inbox_id
    )

    # FASE EVOLUTION: aqui entraremos com envio via provider
    return {
        "ok": True,
        "user_id": user_id,
        "account_id": account_id,
        "inbox_id": inbox_id,
        "content_preview": (content or "")[:80],
    }
