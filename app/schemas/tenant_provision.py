from pydantic import BaseModel
from typing import Optional

class ProvisionChatwootIn(BaseModel):
    user_id: int
    account_name: Optional[str] = None
    inbox_name: Optional[str] = None
    evolution_instance_id: Optional[str] = None

class ProvisionChatwootOut(BaseModel):
    ok: bool
    user_id: int
    chatwoot_account_id: int
    chatwoot_inbox_id: int
    chatwoot_inbox_identifier: Optional[str] = None
