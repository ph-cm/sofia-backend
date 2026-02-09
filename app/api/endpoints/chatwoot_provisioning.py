from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.api.models.user import User
from app.api.services.chatwoot_service import ChatwootService
from app.api.services.tenant_integration_service import TenantIntegrationService

router = APIRouter(prefix="/provision", tags=["Provisioning"])


class ProvisionChatwootInboxIn(BaseModel):
    user_id: int
    # opcional: nome custom do inbox no Chatwoot
    inbox_name: str | None = None


class ProvisionChatwootInboxOut(BaseModel):
    ok: bool
    user_id: int
    chatwoot_account_id: int
    inbox_id: int
    inbox_identifier: str | None = None


@router.post("/chatwoot/inbox", response_model=ProvisionChatwootInboxOut)
def provision_chatwoot_inbox(payload: ProvisionChatwootInboxIn, db: Session = Depends(get_db)):
    # 1) valida user
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")

    # 2) se já tem inbox_id, não recria
    if user.inbox_id and int(user.inbox_id) > 0:
        return ProvisionChatwootInboxOut(
            ok=True,
            user_id=user.id,
            chatwoot_account_id=int(settings.CHATWOOT_ACCOUNT_ID),
            inbox_id=int(user.inbox_id),
            inbox_identifier=None,
        )

    # 3) cria inbox no Chatwoot usando token global/admin
    cw = ChatwootService(
        base_url=settings.CHATWOOT_BASE_URL,
        api_token=settings.CHATWOOT_API_TOKEN_GLOBAL,  # ✅ token admin/global
        account_id=int(settings.CHATWOOT_ACCOUNT_ID),
    )

    inbox_name = payload.inbox_name or f"medico_{user.id}_{user.nome}"

    created = cw.create_api_inbox(name=inbox_name)
    inbox_id = ChatwootService._extract_id(created)

    if not inbox_id:
        raise HTTPException(status_code=502, detail=f"chatwoot_inbox_create_failed: {created}")

    inbox_identifier = None
    if isinstance(created, dict):
        inbox_identifier = (
            created.get("identifier")
            or (created.get("channel") or {}).get("identifier")  # fallback
        )

    # 4) salva em users.inbox_id
    user.inbox_id = int(inbox_id)
    db.add(user)
    db.commit()
    db.refresh(user)

    # 5) salva/atualiza tenant_integrations (roteamento multi-tenant)
    TenantIntegrationService.bind_chatwoot(
        db=db,
        user_id=user.id,
        chatwoot_account_id=int(settings.CHATWOOT_ACCOUNT_ID),
        chatwoot_inbox_id=int(inbox_id),
        chatwoot_inbox_identifier=str(inbox_identifier or ""),
        # evolution_instance_id / evolution_phone ficam como já estão (se quiser setar aqui, passe também)
    )

    return ProvisionChatwootInboxOut(
        ok=True,
        user_id=user.id,
        chatwoot_account_id=int(settings.CHATWOOT_ACCOUNT_ID),
        inbox_id=int(inbox_id),
        inbox_identifier=inbox_identifier,
    )
