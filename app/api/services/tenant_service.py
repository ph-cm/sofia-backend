# app/api/services/tenant_service.py

from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.models.tenant import Tenant
from app.api.models.user import User

from app.db.session import SessionLocal
from app.api.models.tenant_integration import TenantIntegration


class TenantService:
    @staticmethod
    def get_by_evolution_instance(instance_name: str):

        if not instance_name or not instance_name.strip():
            print("TENANT_LOOKUP_IGNORED: empty instance_name")
            return None

        db: Session = SessionLocal()
        try:
            instance_name = instance_name.strip()

            # 1️⃣ Buscar integração
            integration = db.execute(
                select(TenantIntegration)
                .where(TenantIntegration.evolution_instance_id == instance_name)
            ).scalar_one_or_none()

            if not integration:
                print(f"TENANT_LOOKUP_NOT_FOUND: instance_name={instance_name}")
                return None

            # 2️⃣ Buscar tenant real
            tenant = db.execute(
                select(Tenant).where(Tenant.user_id == integration.user_id)
            ).scalar_one_or_none()


            if not tenant:
                print(f"TENANT_AUTO_CREATE: user_id={integration.user_id}")

                tenant = Tenant(
                    user_id=integration.user_id,
                    name=f"Tenant {integration.user_id}"
                )
                db.add(tenant)
                db.commit()
                db.refresh(tenant)


            print(f"TENANT_LOOKUP_OK: instance_name={instance_name} tenant_id={tenant.id}")

            return {
                "tenant_id": tenant.id,
                "name": tenant.name,
                "chatwoot_account_id": tenant.chatwoot_account_id,
                "chatwoot_inbox_id": tenant.chatwoot_inbox_id,
                "chatwoot_api_token": tenant.chatwoot_api_token,
                "evolution_instance_name": tenant.evolution_instance_name,
            }

        finally:
            db.close()


    # ✅ NOVO: usado no fluxo de saída (Chatwoot -> Evolution)
    @staticmethod
    def get_by_chatwoot_inbox_id(inbox_id: int) -> Optional[Dict[str, Any]]:
        if not inbox_id:
            print("TENANT_LOOKUP_IGNORED: empty inbox_id")
            return None

        db: Session = SessionLocal()
        try:
            tenant = db.execute(
                select(Tenant).where(Tenant.chatwoot_inbox_id == int(inbox_id))
            ).scalar_one_or_none()

            if not tenant:
                print(f"TENANT_LOOKUP_NOT_FOUND_BY_INBOX: inbox_id={inbox_id}")
                return None

            print(f"TENANT_LOOKUP_OK_BY_INBOX: inbox_id={inbox_id} tenant_id={tenant.id}")
            return {
                "id": tenant.id,
                "name": tenant.name,
                "evolution_instance_name": tenant.evolution_instance_name,
                "chatwoot_account_id": tenant.chatwoot_account_id,
                "chatwoot_inbox_id": tenant.chatwoot_inbox_id,
                "chatwoot_api_token": tenant.chatwoot_api_token,
            }
        finally:
            db.close()

    @staticmethod
    def bind_evolution_instance(tenant_id: int, instance_name: str) -> Dict[str, Any]:
        if not instance_name or not instance_name.strip():
            raise ValueError("instance_name_empty")

        db: Session = SessionLocal()
        try:
            tenant = db.execute(
                select(Tenant).where(Tenant.user_id == tenant_id)
            ).scalar_one_or_none()

            if not tenant:
                tenant = Tenant(
                    user_id=tenant_id,
                    name=f"Tenant {tenant_id}"
                )
                db.add(tenant)
                db.commit()
                db.refresh(tenant)


            instance_name = instance_name.strip()

            # 🔎 Verifica se já existe integração para esse tenant
            integration = db.execute(
                select(TenantIntegration)
                .where(TenantIntegration.user_id == tenant_id)
            ).scalar_one_or_none()

            if integration:
                # Atualiza
                integration.evolution_instance_id = instance_name
            else:
                # Cria nova
                integration = TenantIntegration(
                    user_id=tenant_id,
                    evolution_instance_id=instance_name,
                )
                db.add(integration)

            db.commit()

            print(f"TENANT_BIND_OK: tenant_id={tenant_id} instance_name={instance_name}")

            return {
                "tenant_id": tenant_id,
                "evolution_instance_name": instance_name,
            }

        finally:
            db.close()


    @staticmethod
    def set_chatwoot_config(tenant_id: int, account_id: int, inbox_id: int, api_token: str) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            tenant = db.execute(
                select(Tenant).where(Tenant.user_id == tenant_id)
            ).scalar_one_or_none()

            if not tenant:
                tenant = Tenant(
                    user_id=tenant_id,
                    name=f"Tenant {tenant_id}"
                )
                db.add(tenant)
                db.commit()
                db.refresh(tenant)


            tenant.chatwoot_account_id = account_id
            tenant.chatwoot_inbox_id = inbox_id
            tenant.chatwoot_api_token = api_token

            
            
            user = db.get(User, tenant.user_id)
            if user:
                user.inbox_id = inbox_id
                db.add(user)

            db.add(tenant)
            db.commit()
            db.refresh(tenant)


            print(f"TENANT_CHATWOOT_OK: tenant_id={tenant.id} account_id={account_id} inbox_id={inbox_id}")
            return {
                "id": tenant.id,
                "chatwoot_account_id": tenant.chatwoot_account_id,
                "chatwoot_inbox_id": tenant.chatwoot_inbox_id,
            }
        finally:
            db.close()

    @staticmethod
    def is_duplicate_message(instance_name: str, message_id: str) -> bool:
        return False

    @staticmethod
    def mark_message_processed(instance_name: str, message_id: str) -> None:
        return None
