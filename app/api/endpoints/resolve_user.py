from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.models.user import User

router = APIRouter()

@router.post("/resolve-user")
def resolve_user(payload: dict, db: Session = Depends(get_db)):
    phone = payload.get("phone_channel")

    if not phone:
        raise HTTPException(status_code=400, detail="phone_channel is required")

    user = (
        db.query(User)
        .filter(User.phone_channel == phone, User.ativo == True)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found for this phone")

    return {
        "user_id": user.id,
        "nome": user.nome,
        "phone_channel": user.phone_channel,
        "calendar_id": user.calendar_id,
        "duracao_consulta": user.duracao_consulta,
        "valor_consulta": user.valor_consulta,
        "timezone": user.timezone,
    }
