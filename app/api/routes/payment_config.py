from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.tenant_payment_config import PaymentOptionsResponse, TenantPaymentConfigBase, TenantPaymentConfigResponse
from app.api.services.payment_config_service import PaymentConfigService

router = APIRouter(prefix="/tenants", tags=["Payment Config"])


@router.post("/{tenant_id}/payment-config", response_model=TenantPaymentConfigResponse, status_code=201)
def save_payment_config(
    tenant_id: str,
    payload: TenantPaymentConfigBase,
    db: Session = Depends(get_db),
):
    return PaymentConfigService.upsert_payment_config(db, tenant_id, payload)


@router.get("/{tenant_id}/payment-options", response_model=PaymentOptionsResponse)
def get_payment_options(
    tenant_id: str,
    children: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    config = PaymentConfigService.get_payment_config_by_tenant(db, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Payment config not found for this tenant")

    return PaymentConfigService.calculate_payment_options(config, children)
