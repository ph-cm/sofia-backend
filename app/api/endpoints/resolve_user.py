from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.api.models.user import User

router = APIRouter()

class ResolveUserRequest(BaseModel):
    inbox_id: int
    
@router.post("/resolve-user")
def resolve_user(payload: ResolveUserRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.inbox_id == payload.inbox_id, User.ativo == True)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User not found for inbox_id={payload.inbox_id}"
        )

    return {
        "user_id": user.id,
        "nome": user.nome,
        "inbox_id": user.inbox_id,

        # ✅ dado informativo
        "phone_channel": user.phone_channel,

        # 🔽 dados operacionais
        "calendar_id": user.calendar_id,
        "duracao_consulta": user.duracao_consulta,
        "valor_consulta": user.valor_consulta,
        "timezone": user.timezone,
    }
