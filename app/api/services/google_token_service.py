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
        """
        Salva tokens do OAuth.
        IMPORTANTE:
        - Google pode NÃO retornar refresh_token em logins subsequentes.
          Então só atualize refresh_token se ele vier preenchido.
        - expiry deve ser tz-aware (UTC).
        """

        expiry = None
        if expires_in is not None:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

        token = GoogleTokenService.get_by_user(db, user_id)

        if token:
            token.google_access_token = access_token

            # Só sobrescreve refresh_token se vier um novo (não-vazio)
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

    @staticmethod
    def refresh_access_token(db: Session, token: GoogleToken) -> GoogleToken:
        """
        Faz refresh usando refresh_token salvo no banco e atualiza access + expiry.
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

        # garante expiry sempre preenchido e UTC-aware
        expires_in = int(data.get("expires_in", 3600))
        token.google_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def get_valid_access_token(db: Session, user_id: int) -> str:
        """
        Retorna access token válido.
        Se expiry estiver NULL, força refresh (pra não travar em token velho).
        """
        token = GoogleTokenService.get_by_user(db, user_id)
        if not token:
            raise GoogleTokenNotFound("Usuário não conectado ao Google")

        now = datetime.now(timezone.utc)

        # Se expiry é NULL -> força refresh (senão nunca renova)
        if (not token.google_token_expiry) or (token.google_token_expiry <= now):
            token = GoogleTokenService.refresh_access_token(db, token)

        return token.google_access_token
