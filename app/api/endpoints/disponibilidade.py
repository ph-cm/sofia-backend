from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from models import ProfissionalDisponibilidade

router = APIRouter()

@router.get("/profissionais/{user_id}/disponibilidade")
def get_disponibilidade(user_id: int, db: Session = Depends(get_db)):
    rows = db.query(ProfissionalDisponibilidade)\
        .filter(
            ProfissionalDisponibilidade.user_id == user_id,
            ProfissionalDisponibilidade.ativo == True
        ).all()

    resultado = {}

    for r in rows:
        dia = str(r.dia_semana)
        if dia not in resultado:
            resultado[dia] = []
        resultado[dia].append({
            "inicio": str(r.hora_inicio),
            "fim": str(r.hora_fim)
        })

    return resultado
