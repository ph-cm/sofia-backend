from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.models.disponibilidade import ProfissionalDisponibilidade
from app.schemas.disponibilidade import DisponibilidadePayload

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

@router.post("/profissionais/disponibilidade")
def salvar_disponibilidade(payload: DisponibilidadePayload, db: Session = Depends(get_db)):

    # remove antigas
    db.query(ProfissionalDisponibilidade)\
        .filter(ProfissionalDisponibilidade.user_id == payload.user_id)\
        .update({"ativo": False})

    for dia, horarios in payload.disponibilidade.items():
        for h in horarios:
            registro = ProfissionalDisponibilidade(
                user_id=payload.user_id,
                dia_semana=int(dia),
                hora_inicio=h.inicio,
                hora_fim=h.fim,
                ativo=True
            )
            db.add(registro)

    db.commit()

    return {"status": "ok"}

