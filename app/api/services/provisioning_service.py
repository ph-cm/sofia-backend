# app/api/services/provisioning_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.services.evolution_service import EvolutionService
from app.api.services.chatwoot_service import ChatwootService
from app.api.services.tenant_integration_service import TenantIntegrationService


@dataclass
class ProvisionResult:
    user_id: int
    evolution_instance_id: str
    chatwoot_account_id: int
    chatwoot_inbox_id: int
    chatwoot_inbox_identifier: str


class ProvisioningService:
    @staticmethod
    def provision_doctor(
        db: Session,
        user_id: int,
        doctor_name: str,
        evolution_phone: str,
        instance_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Provisiona tudo para um médico:
          - cria instância no Evolution
          - configura webhook do Evolution apontando pro seu backend
          - cria inbox no Chatwoot
          - grava binding em tenant_integrations

        Retorna ids e dados necessários pro resto do sistema.
        """
        instance_name = (instance_name or f"tenant_{user_id}").strip()

        # 1) Evolution: cria instância
        evo = EvolutionService()
        evo.create_instance(
            instance_name=instance_name,
            number=evolution_phone,
            qrcode=True,
            integration="WHATSAPP-BAILEYS"  # ajuste se seu Evolution exigir outro
        )

        # 2) Evolution: seta webhook para seu backend
        # você já tem route: /webhooks/evolution/{event}
        webhook_url_base = settings.PUBLIC_BASE_URL.rstrip("/")  # ex: https://api.seudominio.com
        evo.set_webhook(
            instance_name=instance_name,
            url=f"{webhook_url_base}/webhooks/evolution",  # seu handler usa /{event}
            events=[
                "messages-upsert",
                "messages-update",
                "contacts-update",
                "presence-update",
                "chats-update",
            ],
            enabled=True,
            webhook_by_events=True,  # se seu Evolution separar por evento
            webhook_base64=False,
        )

        # 3) Chatwoot: cria inbox
        cw = ChatwootService(
            base_url=settings.CHATWOOT_BASE_URL,
            api_token=settings.CHATWOOT_API_TOKEN,  # token admin/integração
            account_id=int(settings.CHATWOOT_ACCOUNT_ID),
        )

        created = cw.create_inbox_api(name=f"{doctor_name} ({instance_name})")
        inbox_id = int(created["id"])
        inbox_identifier = str(created["inbox_identifier"])

        # 4) Grava binding (multi-tenant real)
        integration = TenantIntegrationService.bind_chatwoot(
            db=db,
            user_id=user_id,
            chatwoot_account_id=int(settings.CHATWOOT_ACCOUNT_ID),
            chatwoot_inbox_id=inbox_id,
            chatwoot_inbox_identifier=inbox_identifier,
            evolution_instance_id=instance_name,
            evolution_phone=evolution_phone,
        )

        return {
            "ok": True,
            "user_id": user_id,
            "evolution": {
                "instance_name": instance_name,
                "phone": evolution_phone,
            },
            "chatwoot": {
                "account_id": int(settings.CHATWOOT_ACCOUNT_ID),
                "inbox_id": inbox_id,
                "inbox_identifier": inbox_identifier,
            },
            "tenant_integration_id": getattr(integration, "id", None),
        }
