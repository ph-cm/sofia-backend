# app/api/endpoints/chatwoot_provisioning.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import SessionLocal
from app.api.services.chatwoot_service import ChatwootService
from app.api.services.tenant_integration_service import TenantIntegrationService


router = APIRouter(prefix="/provision", tags=["Provisioning"])


class ProvisionChatwootInboxIn(BaseModel):
    user_id: int
    inbox_name: str
    evolution_instance_id: str  # ex: "tenant_2"


class ProvisionChatwootInboxOut(BaseModel):
    user_id: int
    chatwoot_account_id: int
    chatwoot_inbox_id: int
    chatwoot_inbox_identifier: str | None
    evolution_instance_id: str


@router.post("/chatwoot/inbox", response_model=ProvisionChatwootInboxOut)
def provision_chatwoot_inbox(payload: ProvisionChatwootInboxIn):
    """
    Cria um inbox (Channel API) no Chatwoot e salva o binding no tenant_integrations.
    Isso é o multi-tenant: 1 inbox por médico.
    """
    if not getattr(settings, "CHATWOOT_BASE_URL", None):
        raise HTTPException(status_code=500, detail="CHATWOOT_BASE_URL not configured")
    if not getattr(settings, "CHATWOOT_ADMIN_API_TOKEN", None):
        raise HTTPException(status_code=500, detail="CHATWOOT_ADMIN_API_TOKEN not configured")
    if not getattr(settings, "CHATWOOT_ACCOUNT_ID", None):
        raise HTTPException(status_code=500, detail="CHATWOOT_ACCOUNT_ID not configured")
    if not getattr(settings, "CHATWOOT_WEBHOOK_SECRET", None):
        raise HTTPException(status_code=500, detail="CHATWOOT_WEBHOOK_SECRET not configured")

    account_id = int(settings.CHATWOOT_ACCOUNT_ID)

    # Webhook do Chatwoot -> seu backend (outgoing)
    # O Chatwoot vai chamar isso quando você mandar msg pela UI dele.
    webhook_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/integrations/chatwoot/events?secret={settings.CHATWOOT_WEBHOOK_SECRET}"

    cw = ChatwootService(
        base_url=settings.CHATWOOT_BASE_URL,
        api_token=settings.CHATWOOT_ADMIN_API_TOKEN,
        account_id=account_id,
    )

    inbox_obj = cw.create_inbox_api(
        name=payload.inbox_name,
        webhook_url=webhook_url,
        webhook_secret=settings.CHATWOOT_WEBHOOK_SECRET,
    )

    inbox_id = ChatwootService._extract_id(inbox_obj)
    if not inbox_id:
        raise HTTPException(status_code=500, detail="Chatwoot returned no inbox_id")

    inbox_identifier = (
        inbox_obj.get("inbox_identifier")
        or inbox_obj.get("identifier")
        or inbox_obj.get("channel_id")
        or (inbox_obj.get("channel", {}) or {}).get("identifier")
        if isinstance(inbox_obj, dict)
        else None
    )

    db = SessionLocal()
    try:
        integration = TenantIntegrationService.bind_chatwoot(
            db=db,
            user_id=payload.user_id,
            chatwoot_account_id=account_id,
            chatwoot_inbox_id=int(inbox_id),
            chatwoot_inbox_identifier=str(inbox_identifier) if inbox_identifier else "",
            evolution_instance_id=payload.evolution_instance_id,
        )
    finally:
        db.close()

    return ProvisionChatwootInboxOut(
        user_id=payload.user_id,
        chatwoot_account_id=account_id,
        chatwoot_inbox_id=int(inbox_id),
        chatwoot_inbox_identifier=inbox_identifier,
        evolution_instance_id=payload.evolution_instance_id,
    )
