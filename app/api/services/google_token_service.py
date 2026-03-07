from datetime import datetime, timezone, timedelta
import requests
from sqlalchemy.orm import Session

from app.api.models.google_token import GoogleToken
from app.core.config import settings


class GoogleTokenNotFound(Exception):
    pass


class GoogleTokenRefreshFailed(Exception):
    pass


class GoogleTokenService:

    @staticmethod
    def get_by_user(db: Session, user_id: int) -> GoogleToken | None:
        return (
            db.query(GoogleToken)
            .filter(GoogleToken.user_id == user_id)
            .first()
        )

    @staticmethod
    def save_tokens(
        db: Session,
        user_id: int,
        access_token: str,
        refresh_token: str | None,
        expires_in: int | None = None,
        scope: str | None = None,
    ) -> GoogleToken:
        expiry = None
        if expires_in is not None:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

        token = GoogleTokenService.get_by_user(db, user_id)

        if token:
            token.google_access_token = access_token
            if refresh_token:
                token.google_refresh_token = refresh_token
            token.google_token_expiry = expiry
            token.scope = scope
        else:
            token = GoogleToken(
                user_id=user_id,
                google_access_token=access_token,
                google_refresh_token=refresh_token or "",
                google_token_expiry=expiry,
                scope=scope,
            )
            db.add(token)

        db.commit()
        db.refresh(token)
        return token

    # ===== LEGADO / COMPARTILHADO: NÃO MEXER =====
    @staticmethod
    def refresh_access_token(db: Session, token: GoogleToken) -> GoogleToken:
        """
        Método compartilhado por outros processos.
        Mantém comportamento antigo: tenta refresh e, se falhar, só lança erro.
        NÃO apaga token do banco.
        """
        if not token.google_refresh_token:
            raise GoogleTokenRefreshFailed("Refresh token não existe para este usuário.")

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": token.google_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise GoogleTokenRefreshFailed(
                f"Erro ao renovar token Google: {response.text}"
            )

        data = response.json()

        token.google_access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        token.google_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def get_valid_access_token(db: Session, user_id: int) -> str:
        """
        Método compartilhado por outros processos.
        """
        token = GoogleTokenService.get_by_user(db, user_id)
        if not token:
            raise GoogleTokenNotFound("Usuário não conectado ao Google")

        now = datetime.now(timezone.utc)

        if (not token.google_token_expiry) or (token.google_token_expiry <= now):
            token = GoogleTokenService.refresh_access_token(db, token)

        return token.google_access_token

    # ===== NOVO / ISOLADO: usar só na Agenda =====
    @staticmethod
    def refresh_access_token_agenda(db: Session, token: GoogleToken) -> GoogleToken:
        """
        Variante isolada para a Agenda.
        Não apaga token do banco. Só devolve erro marcado para o front reconectar.
        """
        if not token.google_refresh_token:
            raise GoogleTokenRefreshFailed(
                "google_reauth_required: Refresh token não existe para este usuário."
            )

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": token.google_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if response.status_code != 200:
            try:
                payload = response.json()
            except Exception:
                payload = None

            if isinstance(payload, dict) and payload.get("error") == "invalid_grant":
                raise GoogleTokenRefreshFailed(
                    "google_reauth_required: Token do Google expirou ou foi revogado. Reconecte sua conta."
                )

            raise GoogleTokenRefreshFailed(f"Erro ao renovar token Google: {response.text}")

        data = response.json()
        access = data.get("access_token")
        if not access:
            raise GoogleTokenRefreshFailed(
                f"Erro ao renovar token Google: resposta sem access_token ({data})"
            )

        token.google_access_token = access
        expires_in = int(data.get("expires_in", 3600))
        token.google_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def get_valid_access_token_agenda(db: Session, user_id: int) -> str:
        """
        Variante isolada para endpoints da Agenda.
        """
        token = GoogleTokenService.get_by_user(db, user_id)
        if not token:
            raise GoogleTokenNotFound("Usuário não conectado ao Google")

        now = datetime.now(timezone.utc)

        if (not token.google_token_expiry) or (token.google_token_expiry <= now):
            token = GoogleTokenService.refresh_access_token_agenda(db, token)

        return token.google_access_token