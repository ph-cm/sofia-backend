import os
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.models.user import User
from app.api.models.tenant_integration import TenantIntegration
from app.api.services.chatwoot_service import ChatwootService

class TenantProvisionService:
    @staticmethod
    def provision_chatwoot(db: Session, user_id: int, account_name: str | None, inbox_name: str | None) -> TenantIntegration:
        # 1. Busca o usuário
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 2. Busca ou cria o registro de integração
        integration = db.query(TenantIntegration).filter(TenantIntegration.user_id == user_id).first()
        if not integration:
            integration = TenantIntegration(user_id=user_id)
            db.add(integration)
            db.flush()

        # ✅ VÍNCULO TÉCNICO: O inbox_name enviado (ex: go_33) vira o ID da instância
        if inbox_name:
            integration.evolution_instance_id = inbox_name

        # 3. Se já possui o Inbox ID, salva o vínculo da instância e retorna
        if integration.chatwoot_inbox_id:
            db.commit()
            db.refresh(integration)
            return integration

        # 4. CONFIGURAÇÃO CHATWOOT (Conta Fixa)
        # Certifique-se de ter essas variáveis no seu .env do backend
        base_url = os.getenv("CHATWOOT_BASE_URL")
        api_token = os.getenv("CHATWOOT_API_TOKEN")
        fixed_account_id = int(os.getenv("CHATWOOT_ACCOUNT_ID", 2))

        # 5. Instancia o serviço com a conta fixa
        cw = ChatwootService(
            base_url=base_url,
            api_token=api_token,
            account_id=fixed_account_id
        )

        # 6. Cria o Inbox (Canal API)
        inbox_display = inbox_name or f"Inbox - {user.nome or user_id}"
        
        try:
            # Chama o método de instância que você já tem no ChatwootService
            inbox_data = cw.create_api_inbox(name=inbox_display)
            
            # Usa o extrator de ID que você já tem no seu service
            inbox_id = cw._extract_id(inbox_data)
            
            if not inbox_id:
                raise HTTPException(status_code=502, detail=f"Falha ao extrair ID do inbox: {inbox_data}")

            # 7. Salva os IDs no banco
            integration.chatwoot_account_id = fixed_account_id
            integration.chatwoot_inbox_id = int(inbox_id)
            
            # Se o retorno tiver o identifier, salvamos também
            if isinstance(inbox_data, dict):
                integration.chatwoot_inbox_identifier = inbox_data.get("inbox_identifier")

            db.commit()
            db.refresh(integration)
            return integration

        except Exception as e:
            db.rollback()
            print(f"❌ ERRO NO PROVISIONAMENTO: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")