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


class GoogleEventUpdateIn(BaseModel):
    user_id: int = Field(..., ge=1)
    event_id: str = Field(..., min_length=1)

    # n8n manda "id_agenda"
    id_agenda: str = Field("primary", min_length=1)

    # n8n manda "titulo" e "descricao"
    titulo: str = Field(..., min_length=1)
    descricao: Optional[str] = ""

    # n8n manda "inicio" e "fim"
    inicio: str = Field(..., min_length=1)
    fim: str = Field(..., min_length=1)

    timezone: str = "America/Sao_Paulo"


class GoogleEventUpdateOut(BaseModel):
    status: str
    motivo: Optional[str] = None
    event: Optional[dict] = None
    detail: Optional[dict] = None