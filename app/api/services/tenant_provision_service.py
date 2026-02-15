from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.models.user import User
from app.api.models.tenant_integration import TenantIntegration
from app.api.services.chatwoot_service import ChatwootService

class TenantProvisionService:
    @staticmethod
    def provision_chatwoot(
        db: Session,
        user_id: int,
        account_name: str | None,
        inbox_name: str | None,
        evolution_instance_id: str | None = None,
    ) -> TenantIntegration:

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        integration = (
            db.query(TenantIntegration)
            .filter(TenantIntegration.user_id == user_id)
            .first()
        )

        if not integration:
            integration = TenantIntegration(user_id=user_id)
            db.add(integration)
            db.flush()

        # SALVA CORRETAMENTE O evolution_instance_id
        if evolution_instance_id:
            integration.evolution_instance_id = evolution_instance_id

        # mantém sua lógica igual
        if integration.chatwoot_account_id and integration.chatwoot_inbox_id:
            db.commit()
            db.refresh(integration)
            return integration

        acct_name = account_name or (user.nome or f"Tenant {user.id}")
        inbox_display = inbox_name or f"Inbox - {acct_name}"

        # criação de conta/inbox normalmente
        acc = ChatwootService.create_account(acct_name)
        account_id = acc.get("id")

        inbox = ChatwootService.create_api_inbox(
            account_id=account_id,
            name=inbox_display,
        )

        inbox_id = inbox.get("id") or inbox.get("inbox", {}).get("id")
        inbox_identifier = inbox.get("inbox_identifier") or inbox.get(
            "inbox", {}
        ).get("inbox_identifier")

        integration.chatwoot_account_id = account_id
        integration.chatwoot_inbox_id = inbox_id
        integration.chatwoot_inbox_identifier = inbox_identifier

        db.commit()
        db.refresh(integration)
        return integration

