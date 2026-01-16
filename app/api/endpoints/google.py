from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.services.google_service import GoogleAuthService
from app.api.services.user_service import UserService
from app.db.session import get_db
from app.api.services.google_token_service import GoogleTokenService
from app.core.security import get_current_user
from app.core.security import verify_n8n_api_key
from datetime import datetime, timezone


router = APIRouter(prefix="/google", tags=["Google"])
google_service = GoogleAuthService()


@router.get("/login")
def google_login(user_id: int):
    return {"auth_url": google_service.auth_url(user_id)}


@router.get("/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    user_id = int(state)

    tokens = google_service.exchange_code(code)
    print("TOKENS RECEBIDOS DO GOOGLE:")
    print(tokens)
    
    GoogleTokenService.save_tokens(
        db=db,
        user_id=user_id,
        access_token=tokens["access"],
        refresh_token=tokens["refresh"],
        expires_in=tokens["expires_in"],
        scope=tokens.get("scope"),
    )

    return {"status": "connected", "user_id": user_id}


@router.get("/refresh")
def refresh_google_token(user_id: int = Query(...), db: Session = Depends(get_db)):
    token_row = GoogleTokenService.get_by_user(db, user_id)
    if not token_row:
        raise HTTPException(404, "Google not connected")

    refreshed = google_service.refresh_access_token(
        access_token=token_row.google_access_token,
        refresh_token=token_row.google_refresh_token,
    )

    # garante tz-aware UTC
    expiry = refreshed.get("expiry")
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    token_row.google_access_token = refreshed["access"]
    token_row.google_token_expiry = expiry

    db.commit()
    db.refresh(token_row)

    return {
        "status": "refreshed",
        "access_token_tail": token_row.google_access_token[-6:],
        "expiry": token_row.google_token_expiry,
    }
@router.get("/token")
def get_access_token(user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        token = GoogleTokenService.get_valid_access_token(db, user["id"])
        return {"access_token": token}
    except Exception as e:
        raise HTTPException(404, "Token não encontrado ou expirado")

from fastapi import status

@router.get("/token/internal")
def get_access_token_for_n8n(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
    _: None = Depends(verify_n8n_api_key)
):
    try:
        token = GoogleTokenService.get_valid_access_token(db, user_id)
        return {"access_token": token}

    except GoogleTokenService.TokenNotFound:
        raise HTTPException(status_code=404, detail="Token não encontrado")

    except GoogleTokenService.TokenRefreshFailed as e:
        raise HTTPException(
            status_code=401,
            detail=f"Falha ao renovar token Google: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao obter token Google: {str(e)}"
        )


