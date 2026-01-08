from pydantic import BaseModel
from typing import Dict, List

class Horario(BaseModel):
    inicio: str
    fim: str

class DisponibilidadePayload(BaseModel):
    user_id: int
    disponibilidade: Dict[str, List[Horario]]
