from typing import Optional
from sqlalchemy.orm import Session
from app.api.models.tenant_payment_config import TenantPaymentConfig
from app.schemas.tenant_payment_config import TenantPaymentConfigBase


class PaymentConfigService:
    @staticmethod
    def upsert_payment_config(db: Session, tenant_id: str, payload: TenantPaymentConfigBase) -> TenantPaymentConfig:
        config = (
            db.query(TenantPaymentConfig)
            .filter(TenantPaymentConfig.tenant_id == tenant_id)
            .first()
        )
        if config:
            config.deposit_per_child = payload.deposit_per_child
            config.card_link_1_child = payload.card_link_1_child
            config.card_link_2_children = payload.card_link_2_children
            config.pix_key = payload.pix_key
            config.pix_name = payload.pix_name
        else:
            config = TenantPaymentConfig(
                tenant_id=tenant_id,
                deposit_per_child=payload.deposit_per_child,
                card_link_1_child=payload.card_link_1_child,
                card_link_2_children=payload.card_link_2_children,
                pix_key=payload.pix_key,
                pix_name=payload.pix_name,
            )
            db.add(config)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def get_payment_config_by_tenant(db: Session, tenant_id: str) -> Optional[TenantPaymentConfig]:
        return (
            db.query(TenantPaymentConfig)
            .filter(TenantPaymentConfig.tenant_id == tenant_id)
            .first()
        )

    @staticmethod
    def calculate_payment_options(config: TenantPaymentConfig, children: int) -> dict:
        amount = children * config.deposit_per_child

        if children == 1:
            card_link = config.card_link_1_child
        elif children == 2:
            card_link = config.card_link_2_children
        else:
            card_link = None

        return {
            "amount": amount,
            "card_link": card_link,
            "pix_key": config.pix_key,
            "pix_name": config.pix_name,
            "pix_amount": amount,
        }
