from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from urllib.parse import urlencode
from starlette.responses import RedirectResponse
from app.core.config import settings
from app.api.services.google_service import GoogleAuthService
from app.db.session import get_db

from app.api.services.google_token_service import (
    GoogleTokenService,
    GoogleTokenNotFound,
    GoogleTokenRefreshFailed,
)
from app.core.security import get_current_user, verify_n8n_api_key
from datetime import timezone


router = APIRouter(prefix="/google", tags=["Google"])
google_service = GoogleAuthService()


@router.get("/login")
def google_login(user_id: int):
    return {"auth_url": google_service.auth_url(user_id)}


@router.get("/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    user_id = int(state)

    tokens = google_service.exchange_code(code)

    GoogleTokenService.save_tokens(
        db=db,
        user_id=user_id,
        access_token=tokens["access"],
        refresh_token=tokens.get("refresh"),  # pode vir None
        expires_in=tokens.get("expires_in"),
        scope=tokens.get("scope"),
    )

    # return {"status": "connected", "user_id": user_id}
     # ✅ redireciona pro frontend após conectar
    qs = urlencode({"user_id": user_id, "connected": "1"})
    frontend_url = f"{settings.FRONTEND_BASE_URL}/oauth/google/callback?{qs}"
    return RedirectResponse(url=frontend_url, status_code=302)


@router.get("/refresh")
def refresh_google_token(user_id: int = Query(...), db: Session = Depends(get_db)):
    """
    Força refresh do access token e salva no banco com expiry UTC-aware.
    """
    token_row = GoogleTokenService.get_by_user(db, user_id)
    if not token_row:
        raise HTTPException(status_code=404, detail="Google not connected")

    try:
        token_row = GoogleTokenService.refresh_access_token(db, token_row)

        # garantia extra (mas seu service já define expiry)
        if token_row.google_token_expiry and token_row.google_token_expiry.tzinfo is None:
            token_row.google_token_expiry = token_row.google_token_expiry.replace(tzinfo=timezone.utc)
            db.commit()
            db.refresh(token_row)

        return {
            "status": "refreshed",
            "access_token_tail": token_row.google_access_token[-6:],
            "expiry": token_row.google_token_expiry,
        }

    except GoogleTokenRefreshFailed as e:
        raise HTTPException(status_code=401, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno no refresh: {str(e)}")


@router.get("/token")
def get_access_token(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retorna um access_token válido para o usuário autenticado.
    """
    try:
        token = GoogleTokenService.get_valid_access_token(db, user["id"])
        return {"access_token": token}
    except GoogleTokenNotFound:
        raise HTTPException(status_code=404, detail="Token não encontrado (Google não conectado)")
    except GoogleTokenRefreshFailed as e:
        raise HTTPException(status_code=401, detail=f"Falha ao renovar token Google: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao obter token: {str(e)}")


@router.get("/token/internal")
def get_access_token_for_n8n(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
    _: None = Depends(verify_n8n_api_key),
):
    """
    Endpoint para o n8n pegar um access_token válido via x-api-key.
    """
    try:
        token = GoogleTokenService.get_valid_access_token(db, user_id)
        return {"access_token": token}

    except GoogleTokenNotFound:
        raise HTTPException(status_code=404, detail="Token não encontrado")

    except GoogleTokenRefreshFailed as e:
        raise HTTPException(
            status_code=401,
            detail=f"Falha ao renovar token Google: {str(e)}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao obter token Google: {str(e)}",
        )

@router.get("/status")
def google_status(user_id: int = Query(...), db: Session = Depends(get_db)):
    token_row = GoogleTokenService.get_by_user(db, user_id)
    if not token_row:
        return {"connected": False}

    expiry = token_row.google_token_expiry
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    # “connected” = tem token. Se quiser, você pode incluir expiração
    return {
        "connected": True,
        "expiry": expiry.isoformat() if expiry else None,
    }