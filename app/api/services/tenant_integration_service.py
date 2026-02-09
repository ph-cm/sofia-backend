from __future__ import annotations

from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.api.models.tenant_integration import TenantIntegration


class TenantIntegrationService:
    @staticmethod
    def bind_chatwoot(
        db: Session,
        user_id: int,
        chatwoot_account_id: int,
        chatwoot_inbox_id: int,
        chatwoot_inbox_identifier: str | None = None,
        evolution_instance_id: str | None = None,
        evolution_phone: str | None = None,
    ):
        """
        Cria/atualiza o vínculo do user (médico) com Chatwoot + Evolution.

        Regras corretas:
        - chatwoot_account_id NÃO é único (todos no mesmo workspace).
        - chatwoot_inbox_id é único (um inbox -> um médico).
        - evolution_instance_id é único (uma instância -> um médico).
        - user_id é único (um médico -> um registro de integração).
        """

        # pega ou cria integração por user_id
        integration = db.query(TenantIntegration).filter_by(user_id=user_id).first()
        if not integration:
            integration = TenantIntegration(user_id=user_id)
            db.add(integration)
            db.flush()  # garante id sem commit

        # 1) inbox não pode estar em outro user
        hijack_inbox = (
            db.query(TenantIntegration)
            .filter(
                TenantIntegration.chatwoot_inbox_id == chatwoot_inbox_id,
                TenantIntegration.user_id != user_id,
            )
            .first()
        )
        if hijack_inbox:
            raise HTTPException(
                status_code=409,
                detail="chatwoot_inbox_id already bound to another tenant",
            )

        # 2) evolution_instance_id não pode estar em outro user
        if evolution_instance_id:
            hijack_evo = (
                db.query(TenantIntegration)
                .filter(
                    TenantIntegration.evolution_instance_id == evolution_instance_id,
                    TenantIntegration.user_id != user_id,
                )
                .first()
            )
            if hijack_evo:
                raise HTTPException(
                    status_code=409,
                    detail="evolution_instance_id already bound to another tenant",
                )

        # aplica valores
        integration.chatwoot_account_id = chatwoot_account_id
        integration.chatwoot_inbox_id = chatwoot_inbox_id
        integration.chatwoot_inbox_identifier = chatwoot_inbox_identifier

        if evolution_instance_id:
            integration.evolution_instance_id = evolution_instance_id
        if evolution_phone:
            integration.evolution_phone = evolution_phone

        db.commit()
        db.refresh(integration)
        return integration

    @staticmethod
    def resolve_user_id(
        db: Session,
        chatwoot_account_id: int,
        chatwoot_inbox_id: int | None = None,
    ) -> int:
        # OBS: account_id sozinho NÃO resolve tenant, só serve como filtro.
        q = db.query(TenantIntegration).filter(
            TenantIntegration.chatwoot_account_id == chatwoot_account_id
        )
        if chatwoot_inbox_id is not None:
            q = q.filter(TenantIntegration.chatwoot_inbox_id == chatwoot_inbox_id)

        integration = q.first()
        if not integration:
            raise HTTPException(status_code=404, detail="tenant not found")
        return integration.user_id
