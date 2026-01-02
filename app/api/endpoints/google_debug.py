from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.services.google_token_service import GoogleTokenService


router = APIRouter(prefix="/google/debug", tags=["google-debug"])

@router.get("/calendars")
def list_calendars(user_id: int, db: Session = Depends(get_db)):
    token = GoogleTokenService.get_valid_access_token(db, user_id)

    if not token:
        raise HTTPException(
            status_code=404,
            detail="Usuário não conectado ao Google"
        )

    return {
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
        "scope": token.scope,
    }
