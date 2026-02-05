from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class TenantCreateIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)


class TenantOut(BaseModel):
    id: int
    name: str
    evolution_instance_name: Optional[str] = None
    chatwoot_account_id: Optional[int] = None
    chatwoot_inbox_id: Optional[int] = None

    class Config:
        from_attributes = True


class TenantBindEvolutionIn(BaseModel):
    instance_name: str = Field(..., min_length=2, max_length=64)


class TenantChatwootConfigIn(BaseModel):
    chatwoot_account_id: int
    chatwoot_inbox_id: int
    chatwoot_api_token: str = Field(..., min_length=10)
