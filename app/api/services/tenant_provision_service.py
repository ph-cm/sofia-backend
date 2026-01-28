from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.models.user import User
from app.api.models.tenant_integration import TenantIntegration
from app.api.services.chatwoot_service import ChatwootService

class TenantProvisionService:
    @staticmethod
    def provision_chatwoot(db: Session, user_id: int, account_name: str | None, inbox_name: str | None) -> TenantIntegration:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        integration = db.query(TenantIntegration).filter(TenantIntegration.user_id == user_id).first()
        if not integration:
            integration = TenantIntegration(user_id=user_id)
            db.add(integration)
            db.flush()  # pega id se precisar

        # Se já provisionou, retorna sem recriar
        if integration.chatwoot_account_id and integration.chatwoot_inbox_id:
            return integration

        acct_name = account_name or (user.nome or f"Tenant {user.id}")
        inbox_display = inbox_name or f"Inbox - {acct_name}"

        # 1) cria account
        acc = ChatwootService.create_account(acct_name)
        account_id = acc.get("id")
        if not account_id:
            raise HTTPException(status_code=502, detail=f"Chatwoot account did not return id: {acc}")

        # 2) cria inbox (API)
        inbox = ChatwootService.create_api_inbox(account_id=account_id, name=inbox_display)

        # Alguns retornos vêm como {"id":..., "inbox_identifier":...}
        inbox_id = inbox.get("id") or (inbox.get("inbox") or {}).get("id")
        inbox_identifier = inbox.get("inbox_identifier") or (inbox.get("inbox") or {}).get("inbox_identifier")

        if not inbox_id:
            raise HTTPException(status_code=502, detail=f"Chatwoot inbox did not return id: {inbox}")

        # 3) persiste no banco
        integration.chatwoot_account_id = int(account_id)
        integration.chatwoot_inbox_id = int(inbox_id)
        integration.chatwoot_inbox_identifier = inbox_identifier

        db.commit()
        db.refresh(integration)
        return integration
