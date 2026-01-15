from pydantic import BaseModel
from typing import Optional, Dict, Any

class TenantProfileOut(BaseModel):
    user_id: int
    nome: str
    inbox_id: Optional[int] = None
    phone_channel: Optional[str] = None
    calendar_id: str = "primary"
    duracao_consulta: int = 60
    valor_consulta: Optional[float] = None
    timezone: str = "America/Sao_Paulo"
    regras: Dict[str, Any] = {}

    class Config:
        orm_mode = True
