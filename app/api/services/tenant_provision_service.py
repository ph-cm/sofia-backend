import os
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.models.user import User
from app.api.models.tenant_integration import TenantIntegration
from app.api.services.chatwoot_service import ChatwootService
from app.api.models.tenant import Tenant

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
            db.flush()

        if inbox_name:
            integration.evolution_instance_id = inbox_name

        if integration.chatwoot_inbox_id:
            db.commit()
            db.refresh(integration)
            return integration

        base_url = os.getenv("CHATWOOT_BASE_URL")
        api_token = os.getenv("CHATWOOT_API_TOKEN")
        fixed_account_id = int(os.getenv("CHATWOOT_ACCOUNT_ID", 2))

        cw = ChatwootService(
            base_url=base_url,
            api_token=api_token,
            account_id=fixed_account_id
        )

        inbox_display = inbox_name or f"Inbox - {user.nome or user_id}"

        try:
            inbox_data = cw.create_api_inbox(name=inbox_display)
            inbox_id = cw._extract_id(inbox_data)

            if not inbox_id:
                raise HTTPException(status_code=502, detail=f"Falha ao extrair ID do inbox: {inbox_data}")

            # 🔹 SALVA NA TABELA tenant_integrations
            integration.chatwoot_account_id = fixed_account_id
            integration.chatwoot_inbox_id = int(inbox_id)

            if isinstance(inbox_data, dict):
                integration.chatwoot_inbox_identifier = inbox_data.get("inbox_identifier")

            # =====================================================
            # 🔥 PONTE: SINCRONIZA COM TENANT
            # =====================================================

            tenant = db.query(Tenant).filter(Tenant.user_id == user_id).first()

            if tenant:
                tenant.chatwoot_account_id = integration.chatwoot_account_id
                tenant.chatwoot_inbox_id = integration.chatwoot_inbox_id
                tenant.chatwoot_api_token = api_token
                tenant.evolution_instance_name = integration.evolution_instance_id

            # 🔥 Atualiza também o inbox_id no User
            user.inbox_id = integration.chatwoot_inbox_id

            db.commit()
            db.refresh(integration)
            return integration

        except Exception as e:
            db.rollback()
            print(f"❌ ERRO NO PROVISIONAMENTO: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
