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
    inbox_name: str | None = None


class ProvisionChatwootInboxOut(BaseModel):
    ok: bool
    user_id: int
    chatwoot_account_id: int
    inbox_id: int
    inbox_identifier: str | None = None


@router.post("/chatwoot/inbox", response_model=ProvisionChatwootInboxOut)
def provision_chatwoot_inbox(payload: ProvisionChatwootInboxIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")

    account_id = int(settings.CHATWOOT_ACCOUNT_ID)

    # Se já tem inbox, só garante que a integração existe (self-healing)
    if user.inbox_id and int(user.inbox_id) > 0:
        TenantIntegrationService.bind_chatwoot(
            db=db,
            user_id=user.id,
            chatwoot_account_id=account_id,
            chatwoot_inbox_id=int(user.inbox_id),
            chatwoot_inbox_identifier=None,
        )
        return ProvisionChatwootInboxOut(
            ok=True,
            user_id=user.id,
            chatwoot_account_id=account_id,
            inbox_id=int(user.inbox_id),
            inbox_identifier=None,
        )

    # cria inbox no Chatwoot com token global/admin
    cw = ChatwootService(
        base_url=settings.CHATWOOT_BASE_URL,
        api_token=settings.CHATWOOT_API_TOKEN,
        account_id=account_id,
    )

    inbox_name = payload.inbox_name or f"medico_{user.id}_{user.nome}"
    created = cw.create_api_inbox(name=inbox_name)

    inbox_id = ChatwootService._extract_id(created)
    if not inbox_id:
        raise HTTPException(status_code=502, detail=f"chatwoot_inbox_create_failed: {created}")

    inbox_identifier = None
    if isinstance(created, dict):
        # Chatwoot retorna inbox_identifier no root
        inbox_identifier = created.get("inbox_identifier") or created.get("identifier")

    # ATÔMICO: atualiza user + integração e dá commit uma vez (bind_chatwoot já commita)
    # então: primeiro coloca no user (sem commit), depois bind_chatwoot (commit final).
    user.inbox_id = int(inbox_id)
    db.add(user)
    db.flush()  # não commita, só prepara

    TenantIntegrationService.bind_chatwoot(
        db=db,
        user_id=user.id,
        chatwoot_account_id=account_id,
        chatwoot_inbox_id=int(inbox_id),
        chatwoot_inbox_identifier=inbox_identifier,
    )

    # bind_chatwoot já commitou; garante refresh do user também
    db.refresh(user)

    return ProvisionChatwootInboxOut(
        ok=True,
        user_id=user.id,
        chatwoot_account_id=account_id,
        inbox_id=int(inbox_id),
        inbox_identifier=inbox_identifier,
    )
