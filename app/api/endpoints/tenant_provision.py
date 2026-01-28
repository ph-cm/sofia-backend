from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import verify_n8n_api_key
from app.schemas.tenant_provision import ProvisionChatwootIn, ProvisionChatwootOut
from app.api.services.tenant_provision_service import TenantProvisionService

router = APIRouter(prefix="/integrations", tags=["Integrations"])

@router.post(
    "/chatwoot/provision",
    response_model=ProvisionChatwootOut,
    dependencies=[Depends(verify_n8n_api_key)],
)
def provision_chatwoot(payload: ProvisionChatwootIn, db: Session = Depends(get_db)):
    integration = TenantProvisionService.provision_chatwoot(
        db=db,
        user_id=payload.user_id,
        account_name=payload.account_name,
        inbox_name=payload.inbox_name,
    )
    return ProvisionChatwootOut(
        ok=True,
        user_id=integration.user_id,
        chatwoot_account_id=integration.chatwoot_account_id,
        chatwoot_inbox_id=integration.chatwoot_inbox_id,
        chatwoot_inbox_identifier=integration.chatwoot_inbox_identifier,
    )
