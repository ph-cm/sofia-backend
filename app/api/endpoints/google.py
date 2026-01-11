from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.services.google_service import GoogleAuthService
from app.api.services.user_service import UserService
from app.db.session import get_db
from app.api.services.google_token_service import GoogleTokenService
from app.core.security import get_current_user
from app.core.security import verify_n8n_api_key


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
def refresh_google_token(user_id: int, db: Session = Depends(get_db)):
    tokens = UserService.get_google_tokens(db, user_id)

    if not tokens:
        raise HTTPException(404, "Google not connected")

    refreshed = google_service.refresh_access_token(
        access_token=tokens.google_access_token,
        refresh_token=tokens.google_refresh_token
    )

    UserService.update_google_access_token(
        db=db,
        user_id=user_id,
        access=refreshed["access"],
        expiry=refreshed["expiry"]
    )

    return {"status": "refreshed"}

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


