from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TenantPaymentConfigBase(BaseModel):
    deposit_per_child: int
    card_link_1_child: Optional[str] = None
    card_link_2_children: Optional[str] = None
    pix_key: str
    pix_name: str


class TenantPaymentConfigCreate(TenantPaymentConfigBase):
    tenant_id: str


class TenantPaymentConfigResponse(TenantPaymentConfigBase):
    id: int
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentOptionsResponse(BaseModel):
    amount: int
    card_link: Optional[str]
    pix_key: str
    pix_name: str
    pix_amount: int
