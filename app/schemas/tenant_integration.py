from pydantic import BaseModel
from typing import Optional

class BindChatwootIn(BaseModel):
    user_id: int
    chatwoot_account_id: int
    chatwoot_inbox_id: int
    chatwoot_inbox_identifier: str
    evolution_instance_id: Optional[str] = None
    evolution_phone: Optional[str] = None

class BindChatwootOut(BaseModel):
    ok: bool
    user_id: int
    chatwoot_account_id: int
    chatwoot_inbox_id: int

class ResolveTenantIn(BaseModel):
    chatwoot_account_id: int
    chatwoot_inbox_id: Optional[int] = None

class ResolveTenantOut(BaseModel):
    user_id: int

from typing import Dict, Any

class TenantContextIn(BaseModel):
    chatwoot_account_id: int
    chatwoot_inbox_id: int

class TenantContextOut(BaseModel):
    ok: bool
    user_id: int
    chatwoot_account_id: int
    chatwoot_inbox_id: int
    tenant: Dict[str, Any]
