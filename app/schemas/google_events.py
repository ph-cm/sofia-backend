from pydantic import BaseModel, Field
from typing import Optional

class GoogleEventCreateIn(BaseModel):
    user_id: int = Field(..., ge=1)
    calendar_id: str = "primary"
    start_datetime: str
    end_datetime: str
    summary: str
    description: Optional[str] = ""
    timezone: Optional[str] = "America/Sao_Paulo"

class GoogleEventCreateOut(BaseModel):
    status: str
    motivo: Optional[str] = None
    event: Optional[dict] = None
    detail: Optional[dict] = None


from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class GoogleEventUpdateIn(BaseModel):
    user_id: int = Field(..., ge=1)
    calendar_id: str = "primary"
    event_id: str
    start_datetime: str
    end_datetime: str
    summary: str
    description: Optional[str] = ""
    timezone: Optional[str] = "America/Sao_Paulo"

class GoogleEventUpdateOut(BaseModel):
    status: str
    motivo: Optional[str] = None
    event: Optional[Dict[str, Any]] = None
    detail: Optional[Dict[str, Any]] = None
